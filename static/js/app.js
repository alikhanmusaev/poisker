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
});

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
