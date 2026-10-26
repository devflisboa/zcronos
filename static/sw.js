/* ── AUTOVIU Service Worker v6 ──
 * Servido em /sw.js (rota main.service_worker) para ter escopo "/".
 * - Páginas HTML: sempre rede (dados por usuário nunca vão para o cache);
 *   sem conexão → /static/offline.html
 * - CSS/JS próprios: rede primeiro, cache como fallback offline
 * - Imagens e CDNs com versão fixa (lucide@x.y.z): cache primeiro
 * Ao alterar este arquivo, incrementar VERSION para descartar caches antigos.
 */
const VERSION = 'autoviu-v6';
const CACHE = VERSION + '-static';
const OFFLINE_URL = '/static/offline.html';
const PRECACHE = [
  OFFLINE_URL,
  '/static/css/automotive.css',
  '/static/js/automotive.js',
  '/static/js/manutencao.js',
  '/static/image/favicon.ico',
  '/static/image/icons/icon-192.png',
];
const CDN_HOSTS = ['unpkg.com', 'cdn.jsdelivr.net', 'cdnjs.cloudflare.com'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const resp = await fetch(request);
    if (resp.ok) cache.put(request, resp.clone());
    return resp;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw err;
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const resp = await fetch(request);
  if (resp.ok || resp.type === 'opaque') cache.put(request, resp.clone());
  return resp;
}

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  if (req.mode === 'navigate') {
    event.respondWith(fetch(req).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  if (url.origin === self.location.origin && url.pathname.startsWith('/static/')) {
    const isAsset = /\.(css|js)$/.test(url.pathname);
    event.respondWith(isAsset ? networkFirst(req) : cacheFirst(req));
    return;
  }

  if (CDN_HOSTS.includes(url.hostname) && /@\d/.test(url.pathname)) {
    event.respondWith(cacheFirst(req));
  }
});

self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(self.registration.showNotification(data.title || 'ΛUTOVIU', {
    body: data.body || 'Você tem alertas para revisar no aplicativo.',
    icon: '/static/image/icons/icon-192.png',
    tag: data.tag || 'autoviu-alertas',
    data: {url: data.url || '/alertas/'}
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const dest = (event.notification.data && event.notification.data.url) || '/alertas/';
  event.waitUntil(clients.openWindow(dest));
});
