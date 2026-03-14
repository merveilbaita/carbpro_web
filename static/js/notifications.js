/**
 * CarbPro — Gestion des notifications push
 * Demande la permission, s'abonne via VAPID, gère les préférences
 */

// ── Convertir clé VAPID base64 → Uint8Array ───────────────────
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw     = atob(base64);
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

// ── État abonnement ───────────────────────────────────────────
let pushSubscription = null;

async function getPushSubscription() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return null;
  const reg = await navigator.serviceWorker.ready;
  return await reg.pushManager.getSubscription();
}

async function initNotifications() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.log('[Push] Non supporté sur ce navigateur.');
    hideNotifUI();
    return;
  }

  // Détecter iOS non-standalone
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) ||
                (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
                       window.navigator.standalone === true;

  if (isIOS && !isStandalone) {
    // iOS en mode navigateur → push impossible, afficher info
    const btn = document.getElementById('notif-btn');
    if (btn) {
      btn.style.display = 'flex';
      btn.title = 'Installe l'app sur l'écran d'accueil pour activer les notifications';
      btn.onclick = () => showPushToast(
        '📲 Pour les notifications sur iPhone : installe l'app via ⬆️ Partager → Sur l'écran d'accueil, puis ouvre-la depuis l'icône.',
        'warning'
      );
      const icon = document.getElementById('notif-icon');
      if (icon) icon.className = 'bi bi-bell-slash text-warning';
    }
    return;
  }

  pushSubscription = await getPushSubscription();
  updateNotifUI(pushSubscription !== null);

  // Sur desktop : proposer les notifications si pas encore abonné
  if (!isIOS && !pushSubscription && Notification.permission === 'default') {
    showNotifPromptBanner();
  }
}

// ── Demander permission + s'abonner ──────────────────────────
async function subscribePush() {
  try {
    // Demander permission
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      showPushToast('❌ Permission refusée — notifications désactivées.', 'warning');
      return;
    }

    // Récupérer la clé publique VAPID
    const resp    = await fetch('/push/vapid-public-key/');
    const { publicKey } = await resp.json();

    if (!publicKey) {
      showPushToast('⚠️ Clés VAPID non configurées côté serveur.', 'warning');
      return;
    }

    // S'abonner via le Service Worker
    const reg = await navigator.serviceWorker.ready;
    pushSubscription = await reg.pushManager.subscribe({
      userVisibleOnly:      true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });

    // Envoyer l'abonnement au serveur Django
    const saveResp = await fetch('/push/subscribe/', {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  getCsrfToken(),
      },
      body: JSON.stringify(pushSubscription.toJSON()),
    });

    if (saveResp.ok) {
      updateNotifUI(true);
      showPushToast('🔔 Notifications activées !', 'success');
    } else {
      showPushToast('❌ Erreur lors de l\'enregistrement.', 'danger');
    }

  } catch (err) {
    console.error('[Push] Erreur abonnement:', err);
    showPushToast('❌ Impossible d\'activer les notifications.', 'danger');
  }
}

// ── Se désabonner ─────────────────────────────────────────────
async function unsubscribePush() {
  if (!pushSubscription) return;

  try {
    // Notifier le serveur
    await fetch('/push/unsubscribe/', {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  getCsrfToken(),
      },
      body: JSON.stringify({ endpoint: pushSubscription.endpoint }),
    });

    // Désabonner côté navigateur
    await pushSubscription.unsubscribe();
    pushSubscription = null;

    updateNotifUI(false);
    showPushToast('🔕 Notifications désactivées.', 'info');

  } catch (err) {
    console.error('[Push] Erreur désabonnement:', err);
  }
}

// ── UI : bouton dans la navbar ────────────────────────────────
function updateNotifUI(isSubscribed) {
  const btn  = document.getElementById('notif-btn');
  const icon = document.getElementById('notif-icon');
  const text = document.getElementById('notif-text');

  if (!btn) return;

  btn.style.display = 'flex';

  if (isSubscribed) {
    if (icon) icon.className = 'bi bi-bell-fill text-warning';
    if (text) text.textContent = 'Notifs ON';
    btn.title    = 'Désactiver les notifications';
    btn.onclick  = unsubscribePush;
  } else {
    if (icon) icon.className = 'bi bi-bell-slash';
    if (text) text.textContent = 'Notifs OFF';
    btn.title    = 'Activer les notifications';
    btn.onclick  = subscribePush;
  }
}

function hideNotifUI() {
  const btn = document.getElementById('notif-btn');
  if (btn) btn.style.display = 'none';
}

// ── Toast ─────────────────────────────────────────────────────
function showPushToast(msg, type = 'info') {
  // Réutilise la fonction showToast de pwa.js si disponible
  if (typeof showToast === 'function') {
    showToast(msg, type);
  } else {
    console.log('[Push]', msg);
  }
}

// ── Bannière invitation desktop ──────────────────────────────
function showNotifPromptBanner() {
  // Ne montrer qu'une fois par session
  if (sessionStorage.getItem('notif-banner-shown')) return;
  sessionStorage.setItem('notif-banner-shown', '1');

  const banner = document.createElement('div');
  banner.id = 'notif-invite-banner';
  banner.style.cssText = `
    position:fixed; bottom:4.5rem; left:50%; transform:translateX(-50%);
    background:#1A3A6B; color:white; padding:.8rem 1.2rem;
    border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,.3);
    z-index:9998; display:flex; align-items:center; gap:.8rem;
    max-width:90vw; font-size:.9rem;
  `;
  banner.innerHTML = `
    <i class="bi bi-bell-fill text-warning fs-5"></i>
    <span>Activer les notifications pour être alerté en temps réel ?</span>
    <button onclick="subscribePush(); document.getElementById('notif-invite-banner')?.remove()"
            style="background:#FFC000; border:none; border-radius:8px;
                   padding:.3rem .8rem; font-weight:700; color:#000; cursor:pointer; white-space:nowrap">
      Activer
    </button>
    <button onclick="document.getElementById('notif-invite-banner')?.remove()"
            style="background:transparent; border:none; color:rgba(255,255,255,.7);
                   cursor:pointer; font-size:1.2rem; padding:0 .2rem">
      ✕
    </button>
  `;
  document.body.appendChild(banner);
  // Auto-fermeture après 8 secondes
  setTimeout(() => banner?.remove(), 8000);
}

// ── CSRF Token ────────────────────────────────────────────────
function getCsrfToken() {
  const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
  return cookie ? cookie.split('=')[1].trim() : '';
}

// ── Init au chargement ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Délai pour laisser le SW s'enregistrer d'abord
  setTimeout(initNotifications, 1500);
});
