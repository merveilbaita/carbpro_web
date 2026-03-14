"""
push_service.py — Service Web Push Notifications
Utilise pywebpush + clés VAPID pour envoyer des notifications
à tous les abonnés ou à un utilisateur spécifique.
"""
import json
import logging
import base64
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_vapid_private_key_pem():
    """Décode la clé privée VAPID depuis la variable d'env (base64 → PEM)."""
    b64 = settings.VAPID_PRIVATE_KEY
    if not b64:
        return None
    try:
        # Si déjà en PEM
        decoded = base64.urlsafe_b64decode(b64 + '==')
        if decoded.startswith(b'-----'):
            return decoded.decode()
        # Sinon retourner le base64 directement (pywebpush accepte les deux)
        return b64
    except Exception:
        return b64


def send_push(subscription_dict, title, body, icon="/static/icons/icon-192.png",
              badge="/static/icons/icon-72.png", data=None, tag=None):
    """
    Envoie une notification push à UN abonnement.
    subscription_dict : {"endpoint": ..., "keys": {"p256dh": ..., "auth": ...}}
    Retourne True si succès, False sinon.
    """
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        logger.warning("[Push] Clés VAPID non configurées — notification ignorée.")
        return False

    try:
        from pywebpush import webpush, WebPushException

        payload = json.dumps({
            "title":  title,
            "body":   body,
            "icon":   icon,
            "badge":  badge,
            "tag":    tag or title,
            "data":   data or {},
            "requireInteraction": False,
        })

        webpush(
            subscription_info    = subscription_dict,
            data                 = payload,
            vapid_private_key    = _get_vapid_private_key_pem(),
            vapid_claims         = {
                "sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}",
            },
        )
        return True

    except Exception as e:
        logger.error(f"[Push] Erreur envoi notification : {e}")
        return False


def notify_all(title, body, icon="/static/icons/icon-192.png",
               tag=None, data=None, exclude_user=None):
    """
    Envoie une notification à TOUS les abonnements actifs.
    exclude_user : exclure un utilisateur (ex: celui qui a fait l'action)
    """
    from .models import PushSubscription

    subs = PushSubscription.objects.all()
    if exclude_user:
        subs = subs.exclude(user=exclude_user)

    sent    = 0
    failed  = 0
    to_delete = []

    for sub in subs:
        ok = send_push(
            subscription_dict = sub.to_dict(),
            title = title,
            body  = body,
            icon  = icon,
            tag   = tag,
            data  = data,
        )
        if ok:
            sent += 1
        else:
            failed += 1
            # Si endpoint invalide (410 Gone), marquer pour suppression
            to_delete.append(sub.pk)

    # Supprimer les abonnements expirés
    if to_delete:
        PushSubscription.objects.filter(pk__in=to_delete).delete()
        logger.info(f"[Push] {len(to_delete)} abonnement(s) expiré(s) supprimé(s).")

    logger.info(f"[Push] Envoyé : {sent}, Échec : {failed}")
    return sent, failed


def notify_admins(title, body, tag=None, data=None):
    """Envoie une notification uniquement aux administrateurs."""
    from .models import PushSubscription

    subs = PushSubscription.objects.filter(user__profile__role="administrateur")
    sent = 0
    to_delete = []

    for sub in subs:
        ok = send_push(sub.to_dict(), title, body, tag=tag, data=data)
        if ok:
            sent += 1
        else:
            to_delete.append(sub.pk)

    if to_delete:
        PushSubscription.objects.filter(pk__in=to_delete).delete()

    return sent
