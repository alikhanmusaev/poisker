const CACHE_NAME = 'poisker-{{ static_version }}';
const STATIC_VERSION = '{{ static_version }}';

function staticAsset(path) {
  return `${path}?v=${STATIC_VERSION}`;
}

const PRECACHE = [
  '/offline',
  staticAsset('/static/css/style.css'),
  staticAsset('/static/fonts/inter/inter.css'),
  '/static/fonts/inter/inter-cyrillic-400-normal.woff2',
  '/static/fonts/inter/inter-latin-400-normal.woff2',
  staticAsset('/static/js/core.js'),
  staticAsset('/static/js/app.js'),
  staticAsset('/static/js/image-picker.js'),
  staticAsset('/static/js/messages.js'),
  staticAsset('/static/js/post-gallery.js'),
  staticAsset('/static/js/post-card-slider.js'),
  staticAsset('/static/vendor/htmx.min.js'),
  staticAsset('/static/vendor/lucide-subset.min.js'),
  staticAsset('/static/brand/logo.png'),
  staticAsset('/static/icons/favicon-32.png'),
  staticAsset('/static/icons/icon-180.png'),
  staticAsset('/static/icons/icon-192.png'),
  staticAsset('/static/icons/icon-512.png'),
  staticAsset('/static/icons/icon-maskable-192.png'),
];

const SENSITIVE_PREFIXES = [
  '/posts/',
  '/admin',
  '/reports',
  '/accounts/',
  '/messages/',
  '/moderation/',
  '/notifications/',
  '/bookmarks/',
  '/media/',
];

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      Promise.all(
        PRECACHE.map((url) =>
          cache.add(url).catch(() => undefined)
        )
      )
    )
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
  return SENSITIVE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(prefix)
  );
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (isSensitive(url.pathname)) return;

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((res) => res)
        .catch(() => caches.match('/offline').then((cached) => cached || Response.error()))
    );
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target =
    event.notification?.data?.url ||
    event.notification?.data?.FCM_MSG?.data?.url ||
    self.location.origin + '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) {
          client.navigate?.(target);
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(target);
      }
      return undefined;
    })
  );
});

{% if firebase_web_config.apiKey %}
/* Firebase Cloud Messaging — background pushes for the PWA */
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: '{{ firebase_web_config.apiKey|escapejs }}',
  authDomain: '{{ firebase_web_config.authDomain|escapejs }}',
  projectId: '{{ firebase_web_config.projectId|escapejs }}',
  messagingSenderId: '{{ firebase_web_config.messagingSenderId|escapejs }}',
  appId: '{{ firebase_web_config.appId|escapejs }}',
});

try {
  const messaging = firebase.messaging();
  messaging.onBackgroundMessage((payload) => {
    // If FCM already included a notification payload, the browser shows it.
    if (payload?.notification?.title) {
      return;
    }
    const data = payload?.data || {};
    const title = data.title || 'Поискер';
    const body = data.body || '';
    const url = data.url || self.location.origin + '/';
    return self.registration.showNotification(title, {
      body,
      icon: '/static/icons/icon-192.png',
      badge: '/static/icons/favicon-32.png',
      data: { url },
    });
  });
} catch (err) {
  console.warn('FCM background handler failed', err);
}
{% endif %}
