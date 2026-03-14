/**
 * CarbPro PWA — support Android + iOS
 */

const DB_NAME    = 'carbpro-offline';
const DB_VERSION = 1;
const STORE_NAME = 'pending-requests';
const SYNC_TAG   = 'carbpro-sync';

const IS_IOS = /iphone|ipad|ipod/i.test(navigator.userAgent) ||
               (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
const IS_STANDALONE = window.matchMedia('(display-mode: standalone)').matches ||
                      window.navigator.standalone === true;

let swRegistration = null;

async function registerSW() {
  if (!('serviceWorker' in navigator)) return;
  try {
    swRegistration = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
    navigator.serviceWorker.addEventListener('message', onSWMessage);
    updatePendingBadge();
  } catch (err) { console.error('[PWA] Erreur SW:', err); }
}

function onSWMessage(event) {
  const data = event.data;
  if (!data) return;
  if (data.type === 'SYNC_SUCCESS') {
    showToast('✅ Synchronisé : ' + data.label, 'success');
    updatePendingBadge();
  }
}

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = e => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME))
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
    };
    req.onsuccess = e => resolve(e.target.result);
    req.onerror   = e => reject(e.target.error);
  });
}

async function savePending(item) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).add(item).onsuccess = e => resolve(e.target.result);
    tx.onerror = e => reject(e.target.error);
  });
}

async function countPending() {
  const db = await openDB();
  return new Promise(resolve => {
    const req = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).count();
    req.onsuccess = e => resolve(e.target.result);
    req.onerror   = () => resolve(0);
  });
}

async function getAllPending() {
  const db = await openDB();
  return new Promise(resolve => {
    const req = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).getAll();
    req.onsuccess = e => resolve(e.target.result);
    req.onerror   = () => resolve([]);
  });
}

async function deletePendingById(id) {
  const db = await openDB();
  return new Promise(resolve => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).delete(id);
    tx.oncomplete = resolve;
  });
}

async function updatePendingBadge() {
  const count = await countPending();
  const badge = document.getElementById('pending-badge');
  const btn   = document.getElementById('sync-btn');
  if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline-block' : 'none'; }
  if (btn)   btn.style.display = count > 0 ? 'flex' : 'none';
}

function interceptForms() {
  document.querySelectorAll('form[method="post"]').forEach(form => {
    form.addEventListener('submit', async function(e) {
      if (navigator.onLine) return;
      e.preventDefault();
      const params = new URLSearchParams();
      for (const [k, v] of new FormData(form).entries()) params.append(k, v);
      const label = document.title.split('|')[0].trim();
      try {
        await savePending({
          url: form.action || window.location.href, method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: params.toString(), label, savedAt: new Date().toISOString(),
        });
        updatePendingBadge();
        showOfflineConfirm(label);
        if (!IS_IOS && swRegistration && 'sync' in swRegistration)
          await swRegistration.sync.register(SYNC_TAG);
      } catch (err) { showToast('❌ Erreur de sauvegarde', 'danger'); }
    });
  });
}

// iOS : sync au retour de visibilité (remplace BackgroundSync)
document.addEventListener('visibilitychange', async () => {
  if (document.visibilityState === 'visible' && navigator.onLine) {
    const count = await countPending();
    if (count > 0) await syncManually(true);
  }
});

window.addEventListener('online', async () => {
  updateOnlineIndicator(true);
  const count = await countPending();
  if (count > 0) {
    showToast('🔄 Connexion retrouvée — envoi de ' + count + ' saisie(s)...', 'info');
    setTimeout(() => syncManually(false), 1000);
  }
});

function showOfflineConfirm(label) {
  const main = document.querySelector('.main-content');
  if (!main) return;
  main.innerHTML = `
    <div class="row justify-content-center mt-5">
      <div class="col-12 col-md-6 text-center">
        <div class="mb-3" style="font-size:4rem">📶</div>
        <h4 class="fw-bold text-warning mb-2">Saisie sauvegardée hors-ligne</h4>
        <p class="text-muted mb-3">
          <strong>${label}</strong> enregistré localement.<br>
          ${IS_IOS ? "Appuie sur 🔄 <strong>Sync</strong> quand tu as la 4G."
                   : "Envoi automatique dès le retour de la connexion."}
        </p>
        ${IS_IOS ? `<div class="alert alert-warning text-start small mb-3">
          <i class="bi bi-apple"></i> <strong>iPhone/iPad :</strong>
          Reviens sur l'app avec la 4G puis appuie sur le bouton <strong>🔄 Sync</strong>.
        </div>` : ''}
        <a href="/" class="btn btn-primary"><i class="bi bi-house"></i> Tableau de bord</a>
        <a href="javascript:history.back()" class="btn btn-outline-secondary ms-2">
          <i class="bi bi-plus-circle"></i> Nouvelle saisie
        </a>
      </div>
    </div>`;
}

async function syncManually(silent = false) {
  const btn = document.getElementById('sync-btn');
  if (!navigator.onLine) {
    if (!silent) showToast('❌ Toujours hors-ligne', 'danger');
    return;
  }
  if (!silent && btn) { btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; btn.disabled = true; }

  if (!IS_IOS && swRegistration && 'sync' in swRegistration) {
    await swRegistration.sync.register(SYNC_TAG);
    setTimeout(async () => {
      await updatePendingBadge();
      if (btn) { btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> <span>Sync</span>'; btn.disabled = false; }
    }, 3000);
    return;
  }

  const pending = await getAllPending();
  let success = 0;
  for (const item of pending) {
    try {
      const resp = await fetch(item.url, { method: item.method, headers: item.headers, body: item.body });
      if (resp.ok || resp.redirected) { await deletePendingById(item.id); success++; }
    } catch (err) { console.warn('[PWA] Échec sync item', item.id); }
  }

  await updatePendingBadge();
  if (btn) { btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> <span>Sync</span>'; btn.disabled = false; }

  if (!silent) {
    if (success > 0) { showToast('✅ ' + success + ' saisie(s) synchronisée(s)', 'success'); setTimeout(() => location.reload(), 1500); }
    else if (pending.length === 0) showToast('✅ Tout est à jour', 'success');
    else showToast("⚠️ Certaines saisies n'ont pas pu être envoyées", 'warning');
  } else if (success > 0) {
    showToast('✅ ' + success + ' saisie(s) synchronisée(s) automatiquement', 'success');
  }
}

function updateOnlineIndicator(isOnline) {
  const bar = document.getElementById('offline-bar');
  if (bar) bar.style.display = isOnline ? 'none' : 'flex';
}

function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const id    = 'toast-' + Date.now();
  const color = { success: 'bg-success', danger: 'bg-danger', warning: 'bg-warning text-dark', info: 'bg-info text-dark' }[type] || 'bg-info';
  container.insertAdjacentHTML('beforeend', `
    <div id="${id}" class="toast align-items-center text-white ${color} border-0 show" role="alert" style="min-width:280px">
      <div class="d-flex">
        <div class="toast-body fw-semibold">${msg}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`);
  setTimeout(() => document.getElementById(id)?.remove(), 5000);
}

// Bannière install iOS (instructions manuelles)
function showIOSInstallBanner() {
  if (!IS_IOS || IS_STANDALONE) return;
  if (localStorage.getItem('ios-banner-dismissed')) return;
  const banner = document.getElementById('install-banner');
  if (!banner) return;
  banner.style.display = 'flex';
  banner.innerHTML = `
    <div class="d-flex align-items-start gap-2 w-100 small">
      <span style="font-size:1.3rem">🍎</span>
      <div class="flex-grow-1">
        <strong>Installer CarbPro :</strong>
        appuie sur <strong>⬆️ Partager</strong> → <strong>« Sur l'écran d'accueil »</strong>
      </div>
      <button onclick="localStorage.setItem('ios-banner-dismissed','1'); this.closest('#install-banner').style.display='none'"
              class="btn btn-sm btn-outline-light flex-shrink-0">✕</button>
    </div>`;
}

// Bannière install Android
let deferredInstallPrompt = null;
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  deferredInstallPrompt = e;
  const banner = document.getElementById('install-banner');
  if (!banner) return;
  banner.style.display = 'flex';
  banner.innerHTML = `
    <span><i class="bi bi-download"></i> Installer CarbPro sur cet appareil</span>
    <button id="install-btn" class="btn btn-warning btn-sm fw-bold">Installer</button>`;
  document.getElementById('install-btn')?.addEventListener('click', async () => {
    deferredInstallPrompt.prompt();
    const { outcome } = await deferredInstallPrompt.userChoice;
    if (outcome === 'accepted') banner.style.display = 'none';
    deferredInstallPrompt = null;
  });
});

document.addEventListener('DOMContentLoaded', () => {
  registerSW();
  interceptForms();
  updateOnlineIndicator(navigator.onLine);
  updatePendingBadge();
  window.addEventListener('offline', () => updateOnlineIndicator(false));
  document.getElementById('sync-btn')?.addEventListener('click', () => syncManually(false));
  showIOSInstallBanner();
});
