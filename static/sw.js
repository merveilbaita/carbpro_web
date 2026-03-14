/**
 * CarbPro Service Worker
 * - Cache des pages et assets pour fonctionnement offline
 * - File d'attente des soumissions de formulaires (IndexedDB)
 * - Synchronisation automatique au retour de la connexion
 */

const CACHE_NAME    = 'carbpro-v1';
const SYNC_TAG      = 'carbpro-sync';
const DB_NAME       = 'carbpro-offline';
const DB_VERSION    = 1;
const STORE_NAME    = 'pending-requests';

// ── Assets à mettre en cache immédiatement ─────────────────────
const STATIC_ASSETS = [
  '/',
  '/ravitaillement/',
  '/appro-engin/',
  '/consommation-diverse/',
  '/historique/',
  '/offline/',
  '/static/manifest.json',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
];

// ── Installation : mise en cache initiale ──────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[SW] Cache initial des assets');
      // On essaie chaque asset individuellement pour éviter un échec total
      return Promise.allSettled(
        STATIC_ASSETS.map(url =>
          cache.add(url).catch(err =>
            console.warn(`[SW] Cache raté pour ${url}:`, err)
          )
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// ── Activation : nettoyage des anciens caches ──────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch : stratégie Network First avec fallback cache ────────
self.addEventListener('fetch', event => {
  const req = event.request;

  // Ignorer les requêtes non-GET (POST, etc.) → géré par la sync
  if (req.method !== 'GET') return;

  // Ignorer les URLs chrome-extension ou non-http
  if (!req.url.startsWith('http')) return;

  event.respondWith(
    fetch(req)
      .then(response => {
        // Mettre en cache si réponse valide
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, clone));
        }
        return response;
      })
      .catch(() => {
        // Offline → servir depuis le cache
        return caches.match(req).then(cached => {
          if (cached) return cached;
          // Pas en cache → page offline
          if (req.headers.get('accept')?.includes('text/html')) {
            return caches.match('/offline/');
          }
          return new Response('Offline', { status: 503 });
        });
      })
  );
});

// ── Background Sync ────────────────────────────────────────────
self.addEventListener('sync', event => {
  if (event.tag === SYNC_TAG) {
    console.log('[SW] Sync déclenchée — envoi des requêtes en attente');
    event.waitUntil(syncPendingRequests());
  }
});

// ── Message depuis la page ─────────────────────────────────────
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (event.data?.type === 'SYNC_NOW') {
    syncPendingRequests().then(() => {
      event.ports[0]?.postMessage({ type: 'SYNC_DONE' });
    });
  }
});

// ── IndexedDB helpers ──────────────────────────────────────────
function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = e => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      }
    };
    req.onsuccess = e => resolve(e.target.result);
    req.onerror   = e => reject(e.target.error);
  });
}

function getAllPending(db) {
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const req   = store.getAll();
    req.onsuccess = e => resolve(e.target.result);
    req.onerror   = e => reject(e.target.error);
  });
}

function deletePending(db, id) {
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req   = store.delete(id);
    req.onsuccess = () => resolve();
    req.onerror   = e => reject(e.target.error);
  });
}

// ── Envoi des requêtes en attente ──────────────────────────────
async function syncPendingRequests() {
  let db;
  try {
    db = await openDB();
    const pending = await getAllPending(db);

    console.log(`[SW] ${pending.length} requête(s) en attente`);

    for (const item of pending) {
      try {
        const response = await fetch(item.url, {
          method:  item.method,
          headers: item.headers,
          body:    item.body,
        });

        if (response.ok || response.redirected) {
          await deletePending(db, item.id);
          console.log(`[SW] ✓ Sync réussie : ${item.url} (${item.label})`);

          // Notifier toutes les fenêtres ouvertes
          const clients = await self.clients.matchAll();
          clients.forEach(client => client.postMessage({
            type:  'SYNC_SUCCESS',
            label: item.label,
            count: pending.length,
          }));
        } else {
          console.warn(`[SW] Réponse non-OK (${response.status}) pour ${item.url}`);
        }
      } catch (err) {
        console.warn(`[SW] Échec sync item ${item.id}:`, err);
        // On ne supprime pas — sera réessayé à la prochaine sync
      }
    }
  } catch (err) {
    console.error('[SW] Erreur syncPendingRequests:', err);
  }
}


// ── Web Push : affichage notification reçue ───────────────────
self.addEventListener('push', event => {
  if (!event.data) return;

  let payload;
  try {
    payload = event.data.json();
  } catch {
    payload = { title: 'CarbPro', body: event.data.text() };
  }

  const options = {
    body:    payload.body  || '',
    icon:    payload.icon  || '/static/icons/icon-192.png',
    badge:   payload.badge || '/static/icons/icon-72.png',
    tag:     payload.tag   || 'carbpro',
    data:    payload.data  || {},
    vibrate: [200, 100, 200],
    requireInteraction: payload.requireInteraction || false,
    actions: [
      { action: 'open',    title: 'Voir',   icon: '/static/icons/icon-72.png' },
      { action: 'dismiss', title: 'Fermer' },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(payload.title || 'CarbPro', options)
  );
});

// ── Clic sur notification ─────────────────────────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'dismiss') return;

  const url = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      // Si une fenêtre est déjà ouverte → focus + navigate
      for (const client of list) {
        if (client.url.includes(self.location.origin)) {
          client.focus();
          client.navigate(url);
          return;
        }
      }
      // Sinon ouvrir une nouvelle fenêtre
      return clients.openWindow(url);
    })
  );
});
