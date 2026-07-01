document.addEventListener('DOMContentLoaded', () => {
  const editForm = document.getElementById('edit-post-form');
  if (editForm && typeof saveEditUrl === 'function') {
    saveEditUrl(window.location.href, {
      postId: editForm.dataset.postId || '',
      title: editForm.dataset.postTitle || 'Объявление',
      viewUrl: editForm.dataset.viewUrl || '',
    });
  }

  editForm?.addEventListener('submit', async (event) => {
    if (editForm.dataset.confirmed === '1') {
      editForm.dataset.confirmed = '';
      return;
    }
    event.preventDefault();
    const ok = await confirmDialog({
      title: 'Сохранить изменения?',
      message: 'Новые данные заменят текущее объявление.',
      confirmLabel: 'Сохранить',
    });
    if (ok) {
      editForm.dataset.confirmed = '1';
      editForm.requestSubmit();
    }
  });

  const deleteTrigger = document.getElementById('delete-post-trigger');
  const deletePanel = document.getElementById('delete-confirm-panel');
  const deleteCancel = document.getElementById('delete-post-cancel');
  const deleteForm = document.getElementById('delete-post-form');

  function closeDeletePanel() {
    if (!deletePanel || !deleteTrigger) return;
    deletePanel.hidden = true;
    deleteTrigger.hidden = false;
  }

  deleteTrigger?.addEventListener('click', () => {
    if (!deletePanel || !deleteTrigger) return;
    deleteTrigger.hidden = true;
    deletePanel.hidden = false;
    deleteCancel?.focus();
  });

  deleteCancel?.addEventListener('click', closeDeletePanel);

  deleteForm?.addEventListener('submit', async (event) => {
    if (deleteForm.dataset.confirmed === '1') {
      deleteForm.dataset.confirmed = '';
      return;
    }
    event.preventDefault();
    const ok = await confirmDialog({
      title: 'Удалить объявление?',
      message: 'Восстановить его будет нельзя.',
      confirmLabel: 'Удалить',
      danger: true,
    });
    if (ok) {
      deleteForm.dataset.confirmed = '1';
      deleteForm.requestSubmit();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && deletePanel && !deletePanel.hidden) {
      closeDeletePanel();
    }
  });
});
