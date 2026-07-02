document.addEventListener('DOMContentLoaded', () => {
  const editForm = document.getElementById('edit-post-form');
  const labelsNode = document.getElementById('edit-form-labels');
  let cities = {};
  if (labelsNode) {
    try {
      cities = JSON.parse(labelsNode.textContent).cities || {};
    } catch (e) {}
  }
  if (window.initCityAutocomplete) {
    window.initCityAutocomplete(
      document.getElementById('city-input'),
      document.getElementById('city'),
      document.getElementById('city-suggestions-edit'),
      cities
    );
  }
  if (window.initPriceInput) {
    window.initPriceInput(
      document.getElementById('price-display'),
      document.getElementById('price'),
      document.getElementById('price-hint')
    );
  }

  if (editForm && typeof saveEditUrl === 'function') {
    saveEditUrl(window.location.href, {
      postId: editForm.dataset.postId || '',
      title: editForm.dataset.postTitle || 'Объявление',
      viewUrl: editForm.dataset.viewUrl || '',
    });
  }

  const coverField = document.getElementById('cover-index-field');
  const imagesRoot = document.getElementById('edit-current-images');

  function visibleImageItems() {
    if (!imagesRoot) return [];
    return Array.from(imagesRoot.querySelectorAll('.current-image-item')).filter(
      (item) => !item.classList.contains('is-marked-remove')
    );
  }

  function syncImageOrder() {
    if (!imagesRoot) return;
    visibleImageItems().forEach((item) => {
      const url = item.dataset.imageUrl;
      let input = item.querySelector('input[name="image_order"]');
      if (!input) {
        input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'image_order';
        item.appendChild(input);
      }
      input.value = url;
    });
  }

  function setCoverIndex(index) {
    if (!coverField) return;
    coverField.value = String(Math.max(0, index));
    visibleImageItems().forEach((item, i) => {
      const active = i === index;
      item.classList.toggle('is-cover', active);
      const btn = item.querySelector('[data-cover-select]');
      if (btn) {
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      }
    });
  }

  imagesRoot?.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-cover-select]');
    if (!btn) return;
    const item = btn.closest('.current-image-item');
    const items = visibleImageItems();
    const index = items.indexOf(item);
    if (index >= 0) setCoverIndex(index);
  });

  editForm?.querySelectorAll('input[name="remove_images"]').forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      window.setTimeout(() => {
        syncImageOrder();
        const items = visibleImageItems();
        const current = parseInt(coverField?.value || '0', 10);
        if (!items.length) {
          setCoverIndex(0);
        } else if (current >= items.length) {
          setCoverIndex(0);
        } else {
          setCoverIndex(current);
        }
      }, 0);
    });
  });

  syncImageOrder();

  function readLimits() {
    return {
      titleMin: parseInt(editForm?.dataset.titleMin || '5', 10),
      titleMax: parseInt(editForm?.dataset.titleMax || '100', 10),
      bodyMin: parseInt(editForm?.dataset.bodyMin || '20', 10),
      bodyMax: parseInt(editForm?.dataset.bodyMax || '3000', 10),
    };
  }

  function validateEditForm() {
    if (!editForm) return true;
    const cityInput = document.getElementById('city-input');
    if (!editForm.querySelector('#city')?.value) {
      window.alert('Выберите город из подсказок');
      cityInput?.focus();
      return false;
    }
    const { titleMin, titleMax, bodyMin, bodyMax } = readLimits();
    const title = editForm.querySelector('[name="title"]');
    const body = editForm.querySelector('[name="body"]');
    const titleVal = title?.value.trim() || '';
    const bodyVal = body?.value.trim() || '';
    if (titleVal.length < titleMin) {
      window.alert(`Заголовок — минимум ${titleMin} символов`);
      title?.focus();
      return false;
    }
    if (titleVal.length > titleMax) {
      window.alert(`Заголовок — максимум ${titleMax} символов`);
      title?.focus();
      return false;
    }
    if (bodyVal.length < bodyMin) {
      window.alert(`Описание — минимум ${bodyMin} символов`);
      body?.focus();
      return false;
    }
    if (bodyVal.length > bodyMax) {
      window.alert(`Описание — максимум ${bodyMax} символов`);
      body?.focus();
      return false;
    }
    return true;
  }

  editForm?.addEventListener('submit', async (event) => {
    syncImageOrder();
    if (editForm.dataset.confirmed === '1') {
      editForm.dataset.confirmed = '';
      return;
    }
    event.preventDefault();
    if (!validateEditForm()) return;
    const ok = await confirmDialog({
      title: 'Сохранить изменения?',
      message: 'Изменения заголовка, описания или фото отправятся на проверку. Остальные поля применятся сразу.',
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
      const postId = editForm?.dataset.postId || '';
      if (typeof removeSavedPostById === 'function') {
        removeSavedPostById(postId, window.location.href);
      } else if (typeof removeSavedPost === 'function') {
        removeSavedPost(window.location.href);
      }
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
