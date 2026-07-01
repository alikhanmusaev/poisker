function initPublishSuccess(root) {
  if (!root || root.dataset.publishInit === '1') return null;

  const editUrl = root.dataset.editUrl || '';
  const postId = root.dataset.postId || '';
  const postTitle = root.dataset.postTitle || 'Объявление';
  let viewUrl = root.dataset.viewUrl || '';
  if (!viewUrl && postId && typeof viewUrlForPostId === 'function') {
    viewUrl = viewUrlForPostId(postId);
  }

  if (!editUrl) return null;

  root.dataset.publishInit = '1';

  const hint = root.querySelector('#edit-url-hint');
  const copyBtn = root.querySelector('#copy-edit-btn');
  const shareBtn = root.querySelector('#share-edit-btn');
  const openBtn = root.querySelector('#open-post-btn');
  const autosaveMsg = root.querySelector('#autosave-msg');

  let savedConfirmed = false;

  if (typeof saveEditUrl === 'function') {
    saveEditUrl(editUrl, { postId, title: postTitle, viewUrl });
    if (autosaveMsg) autosaveMsg.hidden = false;
  }

  if (openBtn && viewUrl) {
    openBtn.href = viewUrl;
  }

  function showFeedback(text, ok = true) {
    if (!hint) return;
    hint.hidden = false;
    hint.textContent = text;
    hint.classList.toggle('is-success', ok);
    hint.classList.toggle('is-error', !ok);
  }

  function markComplete() {
    savedConfirmed = true;
    document.body.classList.add('publish-link-saved');
    if (openBtn) {
      openBtn.classList.remove('is-disabled');
      openBtn.removeAttribute('aria-disabled');
      openBtn.removeAttribute('tabindex');
    }
    if (window.refreshIcons) window.refreshIcons();
  }

  copyBtn?.addEventListener('click', async () => {
    await copyText(editUrl);
    const label = copyBtn.querySelector('span');
    if (label) label.textContent = 'Скопировано';
    copyBtn.classList.add('is-copied');
    showFeedback('Ссылка сохранена');
    markComplete();
  });

  shareBtn?.addEventListener('click', async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: postTitle, url: editUrl });
        showFeedback('Отправлено');
        markComplete();
        return;
      } catch (e) {
        if (e.name === 'AbortError') return;
      }
    }
    await copyText(editUrl);
    showFeedback('Ссылка скопирована');
    markComplete();
  });

  openBtn?.addEventListener('click', (e) => {
    if (!savedConfirmed) {
      e.preventDefault();
      showFeedback('Сначала скопируйте ссылку', false);
      copyBtn?.focus();
    }
  });

  const gatedLinks = document.querySelectorAll(
    '.publish-success-gate .header-nav a, .publish-success-gate .mobile-nav a, .publish-success-gate .footer-nav a, .publish-success-gate .brand'
  );
  gatedLinks.forEach((link) => {
    link.addEventListener('click', async (e) => {
      if (savedConfirmed) return;
      const ok = await confirmDialog({
        title: 'Сначала сохраните ссылку',
        message: 'Без неё нельзя будет изменить или удалить объявление.',
        confirmLabel: 'Уйти',
        danger: true,
      });
      if (!ok) e.preventDefault();
    });
  });

  window.addEventListener('beforeunload', (e) => {
    if (!savedConfirmed) {
      e.preventDefault();
      e.returnValue = '';
    }
  });

  if (window.refreshIcons) window.refreshIcons();

  return { markComplete };
}

window.initPublishSuccess = initPublishSuccess;

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.publish-success').forEach((root) => initPublishSuccess(root));
});
