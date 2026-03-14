/**
 * CarbPro — Notifications Push
 * NB: l'installation PWA est gérée par pwa.js — pas de deferredInstallPrompt ici
 */

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw     = atob(base64);
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

let pushSubscription = null;

async function getPushSubscription() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return null;
  const reg = await navigator.serviceWorker.ready;
  return await reg.pushManager.getSubscription();
}

async function initNotifications() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    hideNotifUI();
    return;
  }

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) ||
                (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
                       (window.navigator.standalone === true);

  if (isIOS && !isStandalone) {
    const btn  = document.getElementById('notif-btn');
    const icon = document.getElementById('notif-icon');
    if (btn) {
      btn.style.display = 'flex';
      btn.title   = "Installe l'app sur l'ecran d'accueil pour les notifications";
      btn.onclick = function() {
        showPushToast("iPhone : Partager puis Sur l'ecran d'accueil, puis ouvre l'app depuis l'icone.", 'warning');
      };
    }
    if (icon) icon.className = 'bi bi-bell-slash text-warning';
    return;
  }

  pushSubscription = await getPushSubscription();
  updateNotifUI(pushSubscription !== null);

  if (!isIOS && !pushSubscription && Notification.permission === 'default') {
    showNotifPromptBanner();
  }
}

async function subscribePush() {
  try {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      showPushToast('Permission refusee — notifications desactivees.', 'warning');
      return;
    }

    const resp = await fetch('/push/vapid-public-key/');
    const json = await resp.json();
    const publicKey = json.publicKey;

    if (!publicKey) {
      showPushToast('Cles VAPID non configurees.', 'warning');
      return;
    }

    const reg = await navigator.serviceWorker.ready;
    pushSubscription = await reg.pushManager.subscribe({
      userVisibleOnly:      true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });

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
      showPushToast('Notifications activees !', 'success');
    } else {
      showPushToast('Erreur lors de l enregistrement.', 'danger');
    }

  } catch (err) {
    console.error('[Push] Erreur abonnement:', err);
    showPushToast('Impossible d activer les notifications.', 'danger');
  }
}

async function unsubscribePush() {
  if (!pushSubscription) return;
  try {
    await fetch('/push/unsubscribe/', {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  getCsrfToken(),
      },
      body: JSON.stringify({ endpoint: pushSubscription.endpoint }),
    });
    await pushSubscription.unsubscribe();
    pushSubscription = null;
    updateNotifUI(false);
    showPushToast('Notifications desactivees.', 'info');
  } catch (err) {
    console.error('[Push] Erreur desabonnement:', err);
  }
}

function updateNotifUI(isSubscribed) {
  const btn  = document.getElementById('notif-btn');
  const icon = document.getElementById('notif-icon');
  const text = document.getElementById('notif-text');
  if (!btn) return;
  btn.style.display = 'flex';
  if (isSubscribed) {
    if (icon) icon.className = 'bi bi-bell-fill text-warning';
    if (text) text.textContent = 'Notifs ON';
    btn.title   = 'Desactiver les notifications';
    btn.onclick = unsubscribePush;
  } else {
    if (icon) icon.className = 'bi bi-bell-slash';
    if (text) text.textContent = 'Notifs OFF';
    btn.title   = 'Activer les notifications';
    btn.onclick = subscribePush;
  }
}

function hideNotifUI() {
  const btn = document.getElementById('notif-btn');
  if (btn) btn.style.display = 'none';
}

function showNotifPromptBanner() {
  if (sessionStorage.getItem('notif-banner-shown')) return;
  sessionStorage.setItem('notif-banner-shown', '1');

  const banner = document.createElement('div');
  banner.id = 'notif-invite-banner';
  banner.setAttribute('style', [
    'position:fixed', 'bottom:4.5rem', 'left:50%',
    'transform:translateX(-50%)', 'background:#1A3A6B',
    'color:white', 'padding:.8rem 1.2rem', 'border-radius:12px',
    'box-shadow:0 4px 20px rgba(0,0,0,.3)', 'z-index:9998',
    'display:flex', 'align-items:center', 'gap:.8rem',
    'max-width:90vw', 'font-size:.9rem',
  ].join(';'));

  const span = document.createElement('span');
  span.innerHTML = '<i class="bi bi-bell-fill text-warning fs-5 me-2"></i>Activer les notifications pour les alertes carburant ?';

  const btnYes = document.createElement('button');
  btnYes.textContent = 'Activer';
  btnYes.setAttribute('style', 'background:#FFC000;border:none;border-radius:8px;padding:.3rem .8rem;font-weight:700;color:#000;cursor:pointer;white-space:nowrap');
  btnYes.onclick = function() { subscribePush(); banner.remove(); };

  const btnNo = document.createElement('button');
  btnNo.textContent = 'x';
  btnNo.setAttribute('style', 'background:transparent;border:none;color:rgba(255,255,255,.7);cursor:pointer;font-size:1.2rem;padding:0 .3rem');
  btnNo.onclick = function() { banner.remove(); };

  banner.appendChild(span);
  banner.appendChild(btnYes);
  banner.appendChild(btnNo);
  document.body.appendChild(banner);

  setTimeout(function() { if (banner.parentNode) banner.remove(); }, 8000);
}

function showPushToast(msg, type) {
  if (typeof showToast === 'function') {
    showToast(msg, type || 'info');
  } else {
    console.log('[Push]', msg);
  }
}

function getCsrfToken() {
  const cookie = document.cookie.split(';').find(function(c) {
    return c.trim().startsWith('csrftoken=');
  });
  return cookie ? cookie.split('=')[1].trim() : '';
}

document.addEventListener('DOMContentLoaded', function() {
  setTimeout(initNotifications, 1500);
});
