if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const staticVersion = document.querySelector('meta[name="static-version"]')?.content;
    const swUrl = staticVersion ? `/sw.js?v=${encodeURIComponent(staticVersion)}` : '/sw.js';
    navigator.serviceWorker
      .register(swUrl)
      .then((reg) => {
        reg.addEventListener('updatefound', () => {
          const worker = reg.installing;
          if (!worker) return;
          worker.addEventListener('statechange', () => {
            if (worker.state === 'installed' && navigator.serviceWorker.controller) {
              worker.postMessage({ type: 'SKIP_WAITING' });
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
  initPostCardEditLinks(document);
});

document.body.addEventListener('htmx:afterSwap', () => {
  refreshIcons();
  if (window.initImagePickers) window.initImagePickers(document.body);
  initPostCardEditLinks(document.body);
});
document.body.addEventListener('htmx:afterSettle', () => {
  refreshIcons();
  if (window.initImagePickers) window.initImagePickers(document.body);
  initPostCardEditLinks(document.body);
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

const postCardEditChecks = new Map();

function hidePostCardEditLink(link) {
  link.hidden = true;
  link.removeAttribute('href');
  link.removeAttribute('aria-label');
}

function tokenFromEditUrl(editUrl) {
  try {
    return new URL(editUrl, window.location.origin).searchParams.get('token') || '';
  } catch (e) {
    return '';
  }
}

async function canEditPostCard(postId, editUrl) {
  const token = tokenFromEditUrl(editUrl);
  if (!postId || !token) return false;

  const cacheKey = `${postId}:${token}`;
  if (!postCardEditChecks.has(cacheKey)) {
    postCardEditChecks.set(
      cacheKey,
      fetch(`/posts/${encodeURIComponent(postId)}/meta?token=${encodeURIComponent(token)}`, {
        headers: { Accept: 'application/json' },
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => Boolean(data && data.ok && data.can_edit))
        .catch(() => false)
    );
  }
  return postCardEditChecks.get(cacheKey);
}

function initPostCardEditLinks(scope) {
  if (typeof window.editUrlForPostId !== 'function') return;

  (scope || document).querySelectorAll('[data-post-card-edit]').forEach((link) => {
    const postId = link.dataset.postId || '';
    const editUrl = window.editUrlForPostId(postId);
    hidePostCardEditLink(link);
    if (!editUrl) {
      return;
    }

    canEditPostCard(postId, editUrl).then((allowed) => {
      if (!allowed) {
        hidePostCardEditLink(link);
        return;
      }
      link.href = editUrl;
      link.hidden = false;
      link.setAttribute('aria-label', 'Редактировать объявление');
      refreshIcons();
    });
  });

  refreshIcons();
}
