(function () {
  'use strict';

  const P = () => window.Poisker || {};

  function shortenUrl(url, max = 42) {
    if (!url || url.length <= max) return url;
    const start = Math.ceil((max - 1) / 2);
    const end = Math.floor((max - 1) / 2);
    return `${url.slice(0, start)}…${url.slice(-end)}`;
  }

  function initPublishSuccess(root) {
    if (!root || root.dataset.publishInit === '1') return null;

    const editUrl = root.dataset.editUrl || '';
    const postId = root.dataset.postId || '';
    const postTitle = root.dataset.postTitle || 'Объявление';
    const moderationPending = root.dataset.moderationPending === '1';
    let viewUrl = root.dataset.viewUrl || '';

    if (!P().isAllowedEditUrl?.(editUrl)) return null;

    if (!viewUrl && postId && typeof viewUrlForPostId === 'function') {
      viewUrl = viewUrlForPostId(postId);
    }
    viewUrl = P().safeHref?.(viewUrl) || '';

    root.dataset.publishInit = '1';

    const hint = root.querySelector('#edit-url-hint');
    const copyBtn = root.querySelector('#copy-edit-btn');
    const shareBtn = root.querySelector('#share-edit-btn');
    const openBtn = root.querySelector('#open-post-btn');
    const editBtn = root.querySelector('#edit-post-btn');
    const urlEl = root.querySelector('#publish-success-url');

    if (typeof saveEditUrl === 'function') {
      saveEditUrl(editUrl, { postId, title: postTitle, viewUrl });
    }

    if (urlEl) {
      urlEl.textContent = shortenUrl(editUrl);
      urlEl.title = editUrl;
    }

    if (openBtn && viewUrl) {
      openBtn.href = viewUrl;
    }
    if (editBtn) {
      editBtn.href = editUrl;
    }

    function showFeedback(text, ok = true) {
      if (!hint) return;
      hint.hidden = false;
      hint.textContent = text;
      hint.classList.toggle('is-success', ok);
      hint.classList.toggle('is-error', !ok);
    }

    async function copyEditLink() {
      await copyText(editUrl);
      showFeedback('Ссылка скопирована');
      copyBtn?.classList.add('is-copied');
      if (window.refreshIcons) window.refreshIcons();
    }

    copyBtn?.addEventListener('click', copyEditLink);

    shareBtn?.addEventListener('click', async () => {
      const shareText = moderationPending
        ? 'Ссылка на объявление (на проверке)'
        : 'Моё объявление на Поискере';
      if (navigator.share) {
        try {
          await navigator.share({ title: postTitle, text: shareText, url: editUrl });
          showFeedback('Ссылка отправлена');
          return;
        } catch (e) {
          if (e.name === 'AbortError') return;
        }
      }
      await copyEditLink();
    });

    if (window.refreshIcons) window.refreshIcons();

    return { copyEditLink };
  }

  window.initPublishSuccess = initPublishSuccess;

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.publish-success').forEach((root) => initPublishSuccess(root));
  });
})();
