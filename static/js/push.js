/**
 * PWA Web Push via Firebase Cloud Messaging.
 * Registers an FCM token for the logged-in user and shows a soft permission banner.
 */
(function () {
  const cfgEl = document.getElementById('firebase-web-config');
  if (!cfgEl) return;
  if (!('serviceWorker' in navigator) || !('Notification' in window) || !('PushManager' in window)) {
    return;
  }

  let cfg;
  try {
    cfg = JSON.parse(cfgEl.textContent || '{}');
  } catch (_) {
    return;
  }
  if (!cfg || !cfg.apiKey || !cfg.appId || !cfg.messagingSenderId || !cfg.projectId) {
    return;
  }

  const DEVICE_KEY = 'poisker-push-device-id';
  const DISMISS_KEY = 'poisker-push-banner-dismissed';
  const DISMISS_DAYS = 14;
  const REGISTER_URL = '/api/push/register/';
  const UNREGISTER_URL = '/api/push/unregister/';

  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
  }

  function getDeviceId() {
    try {
      let id = localStorage.getItem(DEVICE_KEY);
      if (id) return id;
      id =
        crypto.randomUUID?.() ||
        `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem(DEVICE_KEY, id);
      return id;
    } catch (_) {
      return `web-${Date.now().toString(36)}`;
    }
  }

  function isDismissed() {
    try {
      const raw = localStorage.getItem(DISMISS_KEY);
      if (!raw) return false;
      const until = Number(raw);
      if (!Number.isFinite(until)) return false;
      if (Date.now() < until) return true;
      localStorage.removeItem(DISMISS_KEY);
    } catch (_) {
      /* ignore */
    }
    return false;
  }

  function dismissForDays() {
    try {
      localStorage.setItem(
        DISMISS_KEY,
        String(Date.now() + DISMISS_DAYS * 24 * 60 * 60 * 1000)
      );
    } catch (_) {
      /* ignore */
    }
  }

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(body),
    });
    return res;
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error(`Failed to load ${src}`));
      document.head.appendChild(s);
    });
  }

  async function ensureFirebase() {
    if (!window.firebase?.messaging) {
      await loadScript('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
      await loadScript('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');
    }
    if (!firebase.apps.length) {
      firebase.initializeApp({
        apiKey: cfg.apiKey,
        authDomain: cfg.authDomain,
        projectId: cfg.projectId,
        messagingSenderId: cfg.messagingSenderId,
        appId: cfg.appId,
      });
    }
    return firebase.messaging();
  }

  async function registerToken() {
    const messaging = await ensureFirebase();
    const reg = await navigator.serviceWorker.ready;
    const tokenOpts = { serviceWorkerRegistration: reg };
    if (cfg.vapidKey) {
      tokenOpts.vapidKey = cfg.vapidKey;
    }
    const token = await messaging.getToken(tokenOpts);
    if (!token) return null;
    const deviceId = getDeviceId();
    await postJson(REGISTER_URL, {
      token,
      device_id: deviceId,
      platform: 'web',
      app_version: document.querySelector('meta[name="static-version"]')?.content || '',
    });
    return token;
  }

  async function unregisterToken() {
    try {
      const deviceId = localStorage.getItem(DEVICE_KEY);
      if (!deviceId) return;
      await postJson(UNREGISTER_URL, { device_id: deviceId });
    } catch (_) {
      /* ignore */
    }
  }

  function showBanner() {
    if (
      document.getElementById('push-enable-banner') ||
      document.getElementById('sw-update-banner') ||
      document.getElementById('pwa-install-banner')
    ) {
      return;
    }
    if (isDismissed()) return;

    const banner = document.createElement('div');
    banner.id = 'push-enable-banner';
    banner.className = 'pwa-install-banner';
    banner.setAttribute('role', 'dialog');
    banner.innerHTML =
      '<div class="pwa-install-banner-body">' +
      '<div class="pwa-install-banner-title">Уведомления</div>' +
      '<div class="pwa-install-banner-text">Получать сообщения и статусы объявлений на этом устройстве</div>' +
      '</div>' +
      '<button type="button" class="btn btn-primary btn-sm" data-push-enable>Включить</button>' +
      '<button type="button" class="sw-update-banner-dismiss" data-push-dismiss aria-label="Закрыть">×</button>';
    document.body.appendChild(banner);

    banner.querySelector('[data-push-enable]')?.addEventListener('click', async () => {
      const btn = banner.querySelector('[data-push-enable]');
      if (btn) {
        btn.disabled = true;
        btn.textContent = '…';
      }
      try {
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
          dismissForDays();
          banner.remove();
          return;
        }
        await registerToken();
        banner.remove();
      } catch (err) {
        console.warn('push enable failed', err);
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'Включить';
        }
      }
    });
    banner.querySelector('[data-push-dismiss]')?.addEventListener('click', () => {
      dismissForDays();
      banner.remove();
    });
  }

  async function init() {
    const permission = Notification.permission;
    if (permission === 'granted') {
      try {
        await registerToken();
      } catch (err) {
        console.warn('push register failed', err);
      }
      return;
    }
    if (permission === 'denied') return;
    // Soft prompt after a short delay so it does not fight install/update banners.
    window.setTimeout(showBanner, 2500);
  }

  document.querySelectorAll('form[action*="logout"]').forEach((form) => {
    form.addEventListener('submit', () => {
      unregisterToken();
    });
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
