if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const staticVersion = document.querySelector('meta[name="static-version"]')?.content;
    const swUrl = staticVersion ? `/sw.js?v=${encodeURIComponent(staticVersion)}` : '/sw.js';
    navigator.serviceWorker
      .register(swUrl)
      .then((reg) => {
        const promptUpdate = (worker) => {
          if (!worker || document.getElementById('sw-update-banner')) return;
          dismissInstallBanner();
          const banner = document.createElement('div');
          banner.id = 'sw-update-banner';
          banner.className = 'sw-update-banner';
          banner.setAttribute('role', 'status');
          banner.innerHTML =
            '<span class="sw-update-banner-text">Доступно обновление приложения</span>' +
            '<button type="button" class="btn btn-primary btn-sm" data-sw-update>Обновить</button>' +
            '<button type="button" class="sw-update-banner-dismiss" data-sw-dismiss aria-label="Закрыть">×</button>';
          document.body.appendChild(banner);
          banner.querySelector('[data-sw-update]')?.addEventListener('click', () => {
            worker.postMessage({ type: 'SKIP_WAITING' });
          });
          banner.querySelector('[data-sw-dismiss]')?.addEventListener('click', () => {
            banner.remove();
          });
        };

        if (reg.waiting) {
          promptUpdate(reg.waiting);
        }

        reg.addEventListener('updatefound', () => {
          const worker = reg.installing;
          if (!worker) return;
          worker.addEventListener('statechange', () => {
            if (worker.state === 'installed' && navigator.serviceWorker.controller) {
              promptUpdate(worker);
            }
          });
        });
      })
      .catch(() => {});
  });

  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (window.__swReloading) return;
    window.__swReloading = true;
    window.location.reload();
  });
}

const PWA_INSTALL_DISMISS_KEY = 'poisker-pwa-install-dismissed';
const PWA_INSTALL_DISMISS_DAYS = 14;
let deferredInstallPrompt = null;

function isStandaloneDisplay() {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true
  );
}

function isIosDevice() {
  const ua = window.navigator.userAgent || '';
  const iOS = /iPad|iPhone|iPod/.test(ua);
  const iPadOs = window.navigator.platform === 'MacIntel' && window.navigator.maxTouchPoints > 1;
  return iOS || iPadOs;
}

function isInstallDismissed() {
  try {
    const raw = localStorage.getItem(PWA_INSTALL_DISMISS_KEY);
    if (!raw) return false;
    const until = Number(raw);
    if (!Number.isFinite(until)) return false;
    if (Date.now() < until) return true;
    localStorage.removeItem(PWA_INSTALL_DISMISS_KEY);
  } catch (_) {
    /* ignore */
  }
  return false;
}

function dismissInstallForDays() {
  try {
    const until = Date.now() + PWA_INSTALL_DISMISS_DAYS * 24 * 60 * 60 * 1000;
    localStorage.setItem(PWA_INSTALL_DISMISS_KEY, String(until));
  } catch (_) {
    /* ignore */
  }
}

function dismissInstallBanner() {
  document.getElementById('pwa-install-banner')?.remove();
}

function showInstallBanner({ mode, onInstall }) {
  if (document.getElementById('pwa-install-banner') || document.getElementById('sw-update-banner')) {
    return;
  }
  if (isStandaloneDisplay() || isInstallDismissed()) return;

  const banner = document.createElement('div');
  banner.id = 'pwa-install-banner';
  banner.className = 'pwa-install-banner';
  banner.setAttribute('role', 'dialog');
  banner.setAttribute('aria-label', 'Установить приложение');

  if (mode === 'android') {
    banner.innerHTML =
      '<div class="pwa-install-banner-body">' +
      '<strong class="pwa-install-banner-title">Установить Поискер</strong>' +
      '<span class="pwa-install-banner-text">Быстрый доступ с экрана телефона, как приложение</span>' +
      '</div>' +
      '<button type="button" class="btn btn-primary btn-sm" data-pwa-install>Установить</button>' +
      '<button type="button" class="sw-update-banner-dismiss" data-pwa-dismiss aria-label="Закрыть">×</button>';
  } else {
    banner.innerHTML =
      '<div class="pwa-install-banner-body">' +
      '<strong class="pwa-install-banner-title">На экран «Домой»</strong>' +
      '<span class="pwa-install-banner-text">Откройте «Поделиться», затем «На экран „Домой“»</span>' +
      '</div>' +
      '<button type="button" class="sw-update-banner-dismiss" data-pwa-dismiss aria-label="Закрыть">×</button>';
  }

  document.body.appendChild(banner);

  banner.querySelector('[data-pwa-dismiss]')?.addEventListener('click', () => {
    dismissInstallForDays();
    banner.remove();
  });

  banner.querySelector('[data-pwa-install]')?.addEventListener('click', async () => {
    if (typeof onInstall === 'function') {
      await onInstall();
    }
  });
}

function initPwaInstallPrompt() {
  if (isStandaloneDisplay()) return;

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    showInstallBanner({
      mode: 'android',
      onInstall: async () => {
        const promptEvent = deferredInstallPrompt;
        if (!promptEvent) return;
        deferredInstallPrompt = null;
        promptEvent.prompt();
        try {
          const choice = await promptEvent.userChoice;
          if (choice?.outcome !== 'accepted') {
            dismissInstallForDays();
          }
        } catch (_) {
          dismissInstallForDays();
        }
        dismissInstallBanner();
      },
    });
  });

  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null;
    dismissInstallForDays();
    dismissInstallBanner();
  });

  // iOS has no beforeinstallprompt — show a short Share hint on mobile Safari.
  if (isIosDevice() && !isInstallDismissed()) {
    const isSafari =
      /Safari/.test(window.navigator.userAgent || '') &&
      !/CriOS|FxiOS|EdgiOS|OPiOS|Chrome/.test(window.navigator.userAgent || '');
    if (isSafari) {
      window.setTimeout(() => {
        showInstallBanner({ mode: 'ios' });
      }, 2500);
    }
  }
}

function refreshIcons() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons({
      attrs: {
        'stroke-width': 2,
      },
    });
  }
}

window.refreshIcons = refreshIcons;

document.addEventListener('DOMContentLoaded', () => {
  refreshIcons();
  initHtmxIndicator();
  initSuggestItems();
  initBookmarkToggles();
  initMobileNav();
  initAuthForms();
  initPwaInstallPrompt();
});

function initAuthForms() {
  document.querySelectorAll('form.auth-form').forEach((form) => {
    form.addEventListener('submit', () => {
      const button = form.querySelector('button[type="submit"]');
      if (!button || button.disabled) return;
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      window.setTimeout(() => {
        button.disabled = false;
        button.removeAttribute('aria-busy');
      }, 15000);
    });
  });
}

function initMobileNav() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/';
  document.querySelectorAll('.mobile-nav-item').forEach((item) => {
    const href = item.getAttribute('href');
    if (!href) return;
    const target = href.replace(/\/+$/, '') || '/';
    const isHome = target === '/' && (path === '/' || path.startsWith('/search'));
    const isProfile = target.includes('/accounts/profile') && path.startsWith('/accounts/profile');
    const isMessages = target.includes('/messages') && path.startsWith('/messages');
    const isBookmarks = target.includes('/bookmarks') && path.startsWith('/bookmarks');
    const isCreate = (target.includes('/posts/new') || target.endsWith('/new')) && (path.includes('/posts/new') || path.endsWith('/new'));
    const isLogin = target.includes('/accounts/login') && path.startsWith('/accounts/login');
    const isRegister = target.includes('/accounts/register') && path.startsWith('/accounts/register');
    const isMatch =
      isHome ||
      isProfile ||
      isMessages ||
      isBookmarks ||
      isCreate ||
      isLogin ||
      isRegister ||
      (target !== '/' && !target.includes('/accounts/') && (path === target || path.startsWith(`${target}/`)));
    item.classList.toggle('is-active', isMatch);
    if (isMatch) item.setAttribute('aria-current', 'page');
    else item.removeAttribute('aria-current');
  });
}

document.body.addEventListener('htmx:afterSettle', (event) => {
  const root = event.detail?.target || document.body;
  refreshIcons();
  if (window.initImagePickers) window.initImagePickers(root);
});

function initHtmxIndicator() {
  const indicator = document.getElementById('htmx-indicator');
  if (!indicator || !document.body) return;

  document.body.addEventListener('htmx:beforeRequest', () => {
    indicator.classList.add('is-visible');
  });
  document.body.addEventListener('htmx:afterRequest', () => {
    indicator.classList.remove('is-visible');
  });
}

function initBookmarkToggles() {
  document.body.addEventListener('submit', async (event) => {
    const form = event.target.closest('[data-bookmark-toggle]');
    if (!form) return;
    event.preventDefault();

    const button = form.querySelector('.post-card-bookmark-btn, button[type="submit"]');
    if (button?.disabled) return;
    if (button) button.disabled = true;

    try {
      const res = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
        },
        credentials: 'same-origin',
      });
      if (res.status === 401 || res.status === 403) {
        window.location.href = form.querySelector('[name="next"]')
          ? `/accounts/login/?next=${encodeURIComponent(form.querySelector('[name="next"]').value || '/')}`
          : '/accounts/login/';
        return;
      }
      if (!res.ok) throw new Error('bookmark toggle failed');
      const data = await res.json();
      const active = Boolean(data.bookmarked);
      if (button) {
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
        button.setAttribute('aria-label', active ? 'Убрать из закладок' : 'Добавить в закладки');
        button.setAttribute('title', active ? 'Убрать из закладок' : 'В закладки');
        const icon = button.querySelector('[data-lucide]');
        if (icon) {
          icon.setAttribute('data-lucide', active ? 'bookmark-check' : 'bookmark');
          refreshIcons();
        }
      }
    } catch (err) {
      form.submit();
    } finally {
      if (button) button.disabled = false;
    }
  });
}

function initSuggestItems() {
  document.body.addEventListener('click', (event) => {
    const reloadButton = event.target.closest('[data-reload-page]');
    if (reloadButton) {
      window.location.reload();
      return;
    }

    const item = event.target.closest('.suggest-item[data-suggest-value]');
    if (!item) return;

    const input = document.querySelector('[name="q"]');
    const suggestBox = document.getElementById('suggest-box');
    const form = document.getElementById('home-search-form');

    if (input) input.value = item.dataset.suggestValue || '';
    if (suggestBox) suggestBox.textContent = '';
    if (form && window.htmx) htmx.trigger(form, 'submit');
    refreshIcons();
  });
}
