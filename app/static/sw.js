const CACHE_NAME = 'poisker-v15';
const PRECACHE = [
  '/offline',
  '/static/css/style.css',
  '/static/fonts/inter/inter.css',
  '/static/fonts/inter/inter-cyrillic-400-normal.woff2',
  '/static/fonts/inter/inter-latin-400-normal.woff2',
  '/static/js/app.js',
  '/static/js/image-picker.js',
  '/static/vendor/htmx.min.js',
  '/static/vendor/lucide.min.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-maskable-192.png',
];

const SENSITIVE_PREFIXES = [
  '/edit',
  '/posts/new',
  '/admin',
  '/reports',
];

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

function isSensitive(pathname) {
  return SENSITIVE_PREFIXES.some((prefix) => pathname.startsWith(prefix) || pathname.includes(prefix));
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (isSensitive(url.pathname)) return;

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return res;
      }))
    );
    return;
  }

  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((res) => res)
        .catch(() => caches.match('/offline'))
    );
  }
});
