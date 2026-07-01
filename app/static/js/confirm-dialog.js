(function () {
  let activeResolve = null;

  function getDialog() {
    return document.getElementById('confirm-dialog');
  }

  function closeDialog(result) {
    const dialog = getDialog();
    if (!dialog) {
      if (activeResolve) {
        activeResolve(result);
        activeResolve = null;
      }
      return;
    }
    dialog.hidden = true;
    document.body.classList.remove('confirm-open');
    if (activeResolve) {
      activeResolve(result);
      activeResolve = null;
    }
  }

  function confirmDialog(options = {}) {
    const dialog = getDialog();
    if (!dialog) {
      return Promise.resolve(window.confirm(options.message || options.title || 'Продолжить?'));
    }

    const titleEl = dialog.querySelector('[data-confirm-title]');
    const messageEl = dialog.querySelector('[data-confirm-message]');
    const confirmBtn = dialog.querySelector('[data-confirm-ok]');
    const cancelBtn = dialog.querySelector('[data-confirm-cancel]');

    if (titleEl) titleEl.textContent = options.title || 'Подтвердите действие';
    if (messageEl) messageEl.textContent = options.message || '';
    if (messageEl) messageEl.hidden = !options.message;
    if (confirmBtn) confirmBtn.textContent = options.confirmLabel || 'Да';
    if (cancelBtn) cancelBtn.textContent = options.cancelLabel || 'Отмена';
    if (confirmBtn) {
      confirmBtn.classList.toggle('btn-danger', Boolean(options.danger));
      confirmBtn.classList.toggle('btn-primary', !options.danger);
    }

    dialog.hidden = false;
    document.body.classList.add('confirm-open');
    if (window.refreshIcons) window.refreshIcons();
    cancelBtn?.focus();

    return new Promise((resolve) => {
      activeResolve = resolve;
    });
  }

  function initConfirmDialog() {
    const dialog = getDialog();
    if (!dialog || dialog.dataset.confirmInit === '1') return;
    dialog.dataset.confirmInit = '1';

    dialog.querySelector('[data-confirm-ok]')?.addEventListener('click', () => closeDialog(true));
    dialog.querySelector('[data-confirm-cancel]')?.addEventListener('click', () => closeDialog(false));
    dialog.querySelector('[data-confirm-backdrop]')?.addEventListener('click', () => closeDialog(false));

    document.addEventListener('keydown', (event) => {
      if (dialog.hidden) return;
      if (event.key === 'Escape') closeDialog(false);
    });
  }

  window.confirmDialog = confirmDialog;

  document.addEventListener('DOMContentLoaded', initConfirmDialog);
})();
