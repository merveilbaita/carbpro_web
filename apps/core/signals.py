"""
signals.py — Signaux Django pour les notifications push
Déclenché après chaque création d'opération importante.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
import threading


def _send_async(func, *args, **kwargs):
    """Lance l'envoi de notification dans un thread séparé pour ne pas bloquer la requête."""
    t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    t.start()


# ── Entrée carburant ──────────────────────────────────────────
@receiver(post_save, sender='core.OperationStock')
def on_operation_stock(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.type != "entree":
        return

    def _notify():
        try:
            from .push_service import notify_all
            stock = instance.stock_apres
            stock_txt = f"{stock:,.0f} L".replace(",", " ")
            qte_txt   = f"{instance.quantite:,.0f} L".replace(",", " ")

            notify_all(
                title = "⛽ Entrée carburant",
                body  = f"{qte_txt} reçus • Stock actuel : {stock_txt}",
                tag   = "entree-stock",
                data  = {"url": "/historique/"},
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[Signal] Notification entrée stock : {e}")

    _send_async(_notify)


# ── Ravitaillement engin ───────────────────────────────────────
@receiver(post_save, sender='core.RavitaillementEngin')
def on_ravitaillement_engin(sender, instance, created, **kwargs):
    if not created:
        return

    def _notify():
        try:
            from .push_service import notify_all
            qte_txt = f"{instance.qte_donnee:,.0f} L".replace(",", " ")
            statut  = ""
            if instance.statut == "anomalie":
                statut = " ⚠️ Anomalie détectée"
            elif instance.statut == "panne_index":
                statut = " 🔧 Panne d'index"

            notify_all(
                title = f"🚛 Appro {instance.engin_id}",
                body  = f"{qte_txt} servis{statut}",
                tag   = f"appro-{instance.engin_id}",
                data  = {"url": "/historique/"},
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[Signal] Notification appro engin : {e}")

    _send_async(_notify)


# ── Stock bas / négatif ───────────────────────────────────────
@receiver(post_save, sender='core.OperationStock')
def on_stock_bas(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.type != "sortie":
        return

    def _notify():
        try:
            from .push_service import notify_admins
            from django.conf import settings

            seuil = getattr(settings, 'STOCK_SEUIL_ALERTE', 500)
            stock = instance.stock_apres
            stock_txt = f"{stock:,.0f} L".replace(",", " ")

            if stock < 0:
                notify_admins(
                    title = "🔴 Stock négatif !",
                    body  = f"Stock : {stock_txt} — Débit fournisseur en attente",
                    tag   = "stock-negatif",
                    data  = {"url": "/", "urgent": True},
                )
            elif stock <= seuil:
                notify_admins(
                    title = f"⚠️ Stock bas",
                    body  = f"Stock : {stock_txt} — Sous le seuil d'alerte ({seuil} L)",
                    tag   = "stock-bas",
                    data  = {"url": "/"},
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[Signal] Notification stock bas : {e}")

    _send_async(_notify)
