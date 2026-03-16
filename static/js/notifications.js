/**
 * CarbPro — Notifications Push (version simplifiée et fiable)
 */

(function() {
  'use strict';

  var NOTIF_SUPPORTED = ('serviceWorker' in navigator) && ('PushManager' in window) && ('Notification' in window);

  // ── Cache busting : forcer rechargement si SW mis à jour ──
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(function() {});
  }

  // ── Cacher la bannière dashboard ──────────────────────────
  function cacherBanniere() {
    var card = document.getElementById('notif-dashboard-card');
    if (card) card.style.display = 'none';
  }

  // ── Bouton Plus tard ──────────────────────────────────────
  var btnPlusTard = document.getElementById('notif-plus-tard');
  if (btnPlusTard) {
    btnPlusTard.addEventListener('click', function(e) {
      e.preventDefault();
      sessionStorage.setItem('notif-plus-tard', '1');
      cacherBanniere();
    });
  }

  // ── Initialisation après chargement ──────────────────────
  document.addEventListener('DOMContentLoaded', function() {

    // Cacher bannière si déjà refusée
    if (sessionStorage.getItem('notif-plus-tard') ||
        (typeof Notification !== 'undefined' && Notification.permission === 'denied')) {
      cacherBanniere();
      return;
    }

    if (!NOTIF_SUPPORTED) {
      cacherBanniere();
      updateBoutonNotif(false, true); // unsupported
      return;
    }

    // Vérifier si déjà abonné
    navigator.serviceWorker.ready.then(function(reg) {
      return reg.pushManager.getSubscription();
    }).then(function(sub) {
      if (sub) {
        cacherBanniere();
        updateBoutonNotif(true, false);
      } else if (Notification.permission === 'granted') {
        // Permission accordée mais pas encore abonné
        doSubscribe();
      } else {
        // Montrer la bannière seulement sur desktop ou iOS installé
        var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
        var isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
                           window.navigator.standalone === true;
        if (!isIOS || isStandalone) {
          setTimeout(function() {
            var card = document.getElementById('notif-dashboard-card');
            if (card && !sessionStorage.getItem('notif-plus-tard')) {
              card.style.display = 'flex';
            }
          }, 2000);
        } else {
          cacherBanniere();
        }
        updateBoutonNotif(false, false);
      }
    }).catch(function() {
      cacherBanniere();
    });
  });

  // ── Bouton navbar notification ────────────────────────────
  function updateBoutonNotif(actif, unsupported) {
    var btn  = document.getElementById('notif-btn');
    var icon = document.getElementById('notif-icon');
    var text = document.getElementById('notif-text');
    if (!btn) return;

    if (unsupported) {
      btn.style.display = 'none';
      return;
    }

    btn.style.display = 'flex';
    if (actif) {
      if (icon) icon.className = 'bi bi-bell-fill text-warning';
      if (text) text.textContent = 'ON';
      btn.title = 'Désactiver les notifications';
      btn.onclick = doUnsubscribe;
    } else {
      if (icon) icon.className = 'bi bi-bell-slash text-white-50';
      if (text) text.textContent = 'OFF';
      btn.title = 'Activer les notifications';
      btn.onclick = doSubscribe;
    }
  }

  // ── S'abonner ─────────────────────────────────────────────
  window.subscribePush = function() { doSubscribe(); };

  function doSubscribe() {
    if (!NOTIF_SUPPORTED) {
      alert('Les notifications ne sont pas supportées sur cet appareil.');
      return;
    }

    Notification.requestPermission().then(function(perm) {
      if (perm !== 'granted') {
        showMsg('Permission refusée.', 'warning');
        cacherBanniere();
        return;
      }

      fetch('/push/vapid-public-key/')
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (!data.publicKey) {
            showMsg('Clés VAPID non configurées.', 'warning');
            return;
          }

          navigator.serviceWorker.ready.then(function(reg) {
            return reg.pushManager.subscribe({
              userVisibleOnly: true,
              applicationServerKey: urlB64ToUint8(data.publicKey),
            });
          }).then(function(sub) {
            return fetch('/push/subscribe/', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrf(),
              },
              body: JSON.stringify(sub.toJSON()),
            });
          }).then(function(r) {
            if (r.ok) {
              updateBoutonNotif(true, false);
              cacherBanniere();
              showMsg('Notifications activées !', 'success');
            }
          }).catch(function(err) {
            console.error('[Push]', err);
            showMsg('Erreur activation notifications.', 'danger');
          });
        });
    });
  }

  // ── Se désabonner ─────────────────────────────────────────
  function doUnsubscribe() {
    navigator.serviceWorker.ready.then(function(reg) {
      return reg.pushManager.getSubscription();
    }).then(function(sub) {
      if (!sub) return;
      return fetch('/push/unsubscribe/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      }).then(function() { return sub.unsubscribe(); });
    }).then(function() {
      updateBoutonNotif(false, false);
      showMsg('Notifications désactivées.', 'info');
    });
  }

  // ── Helpers ───────────────────────────────────────────────
  function urlB64ToUint8(b64) {
    var padding = '='.repeat((4 - b64.length % 4) % 4);
    var base64  = (b64 + padding).replace(/-/g, '+').replace(/_/g, '/');
    var raw     = atob(base64);
    var arr     = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
    return arr;
  }

  function getCsrf() {
    var c = document.cookie.split(';').find(function(s) {
      return s.trim().startsWith('csrftoken=');
    });
    return c ? c.split('=')[1].trim() : '';
  }

  function showMsg(msg, type) {
    if (typeof showToast === 'function') {
      showToast(msg, type);
    }
  }

})();
