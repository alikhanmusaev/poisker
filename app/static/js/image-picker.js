/**
 * Image picker: incremental uploads, preview, validation.
 * Mount on .image-picker roots (create + edit post forms).
 */
(function () {
  const ALLOWED_EXT = /\.(jpe?g|png|webp)$/i;
  const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/pjpeg']);

  function isAllowedImage(file) {
    if (!file) return false;
    const type = (file.type || '').toLowerCase();
    if (ALLOWED_TYPES.has(type) || type === 'image/jpg') return true;
    return ALLOWED_EXT.test(file.name || '');
  }

  function fileKey(file) {
    return `${file.name}:${file.size}:${file.lastModified}`;
  }

  function formatBytes(bytes) {
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} КБ`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
  }

  function syncInputFiles(input, files) {
    if (typeof DataTransfer === 'undefined') {
      return false;
    }
    try {
      const transfer = new DataTransfer();
      files.forEach((file) => transfer.items.add(file));
      input.files = transfer.files;
      return true;
    } catch (_err) {
      return false;
    }
  }

  class ImagePicker {
    constructor(root) {
      this.root = root;
      this.input = root.querySelector('.image-picker-input');
      this.addBtn = root.querySelector('.image-picker-add');
      this.statusEl = root.querySelector('.image-picker-status');
      this.errorEl = root.querySelector('.image-picker-error');
      this.previewEl = root.querySelector('.image-picker-preview');
      this.form = root.closest('form');

      this.totalMax = Math.max(parseInt(root.dataset.totalMax || '5', 10), 0);
      this.maxBytes = Math.max(parseInt(root.dataset.maxBytes || String(5 * 1024 * 1024), 10), 1);
      this.baseExisting = Math.max(parseInt(root.dataset.existingCount || '0', 10), 0);

      this.files = [];
      this.objectUrls = [];
      this.errorTimer = null;

      this.onChange = this.onChange.bind(this);
      this.onAddClick = this.onAddClick.bind(this);
      this.onFormSubmit = this.onFormSubmit.bind(this);
      this.onExistingToggle = this.onExistingToggle.bind(this);
    }

    init() {
      if (!this.input || this.root.dataset.pickerInit === '1') return;
      this.root.dataset.pickerInit = '1';

      this.input.addEventListener('change', this.onChange);
      this.addBtn?.addEventListener('click', this.onAddClick);
      this.form?.addEventListener('submit', this.onFormSubmit);

      this.form
        ?.querySelectorAll('input[name="remove_images"]')
        .forEach((checkbox) => checkbox.addEventListener('change', this.onExistingToggle));

      this.onExistingToggle();
      this.render();
    }

    destroy() {
      this.clearObjectUrls();
      this.input?.removeEventListener('change', this.onChange);
      this.addBtn?.removeEventListener('click', this.onAddClick);
      this.form?.removeEventListener('submit', this.onFormSubmit);
      this.form
        ?.querySelectorAll('input[name="remove_images"]')
        .forEach((checkbox) => checkbox.removeEventListener('change', this.onExistingToggle));
    }

    existingCount() {
      const removed = this.form
        ? this.form.querySelectorAll('input[name="remove_images"]:checked').length
        : 0;
      return Math.max(0, this.baseExisting - removed);
    }

    maxNewFiles() {
      return Math.max(0, this.totalMax - this.existingCount());
    }

    onExistingToggle(event) {
      const checkbox = event?.target;
      const apply = () => {
        this.form?.querySelectorAll('input[name="remove_images"]').forEach((item) => {
          item.closest('.current-image-item')?.classList.toggle('is-marked-remove', item.checked);
        });
        const allowed = this.maxNewFiles();
        if (this.files.length > allowed) {
          this.files = this.files.slice(0, allowed);
          this.showError(`Можно добавить не больше ${allowed} новых фото.`);
        }
        this.syncInput();
        this.render();
      };

      if (checkbox?.name === 'remove_images' && checkbox.checked) {
        const ask = typeof confirmDialog === 'function'
          ? confirmDialog({
              title: 'Удалить фото?',
              message: 'Фото исчезнет после сохранения объявления.',
              confirmLabel: 'Пометить',
              danger: true,
            })
          : Promise.resolve(window.confirm('Удалить это фото при сохранении?'));
        ask.then((ok) => {
          if (!ok) checkbox.checked = false;
          apply();
        });
        return;
      }

      apply();
    }

    onAddClick() {
      if (this.files.length >= this.maxNewFiles()) return;
      this.input.click();
    }

    onFormSubmit() {
      this.syncInput();
    }

    onChange() {
      const selected = Array.from(this.input.files || []);
      const seen = new Set(this.files.map(fileKey));
      const limit = this.maxNewFiles();
      const rejected = [];
      let trimmed = false;

      for (const file of selected) {
        if (!isAllowedImage(file)) {
          rejected.push('поддерживаются только JPG, PNG и WebP');
          continue;
        }
        if (file.size > this.maxBytes) {
          rejected.push(`${file.name || 'Файл'} — больше ${formatBytes(this.maxBytes)}`);
          continue;
        }
        const key = fileKey(file);
        if (seen.has(key)) continue;
        if (this.files.length >= limit) {
          trimmed = true;
          break;
        }
        seen.add(key);
        this.files.push(file);
      }

      if (trimmed) {
        this.showError(`Можно добавить ещё не больше ${limit} фото.`);
      } else if (rejected.length) {
        this.showError(rejected[0]);
      } else {
        this.hideError();
      }

      this.input.value = '';
      this.syncInput();
      this.render();
    }

    syncInput() {
      const ok = syncInputFiles(this.input, this.files);
      if (!ok && this.files.length) {
        this.showError('Браузер не поддерживает выбор нескольких фото. Попробуйте другой браузер.');
      }
    }

    showError(message) {
      if (!this.errorEl) return;
      this.errorEl.textContent = message;
      this.errorEl.hidden = false;
      clearTimeout(this.errorTimer);
      this.errorTimer = setTimeout(() => this.hideError(), 5000);
    }

    hideError() {
      if (!this.errorEl) return;
      this.errorEl.hidden = true;
      this.errorEl.textContent = '';
    }

    clearObjectUrls() {
      this.objectUrls.forEach((url) => URL.revokeObjectURL(url));
      this.objectUrls = [];
    }

    updateControls() {
      const limit = this.maxNewFiles();
      const canAdd = this.files.length < limit && limit > 0;

      if (this.addBtn) {
        this.addBtn.disabled = !canAdd;
        this.addBtn.classList.toggle('is-disabled', !canAdd);
        this.addBtn.setAttribute('aria-disabled', canAdd ? 'false' : 'true');
        const label = this.addBtn.querySelector('.image-picker-button-label');
        if (label) {
          label.textContent = this.files.length === 0 ? 'Добавить фото' : 'Добавить ещё';
        }
      }

      if (this.statusEl) {
        const existing = this.existingCount();
        const totalAfter = existing + this.files.length;
        if (limit === 0) {
          this.statusEl.textContent = 'Достигнут лимит 5 фото';
        } else if (this.files.length === 0) {
          this.statusEl.textContent = existing
            ? `Новых фото нет · уже ${existing} из ${this.totalMax}`
            : 'Фото не выбраны';
        } else {
          const remaining = limit - this.files.length;
          this.statusEl.textContent = remaining
            ? `Выбрано ${this.files.length} · всего будет ${totalAfter} из ${this.totalMax}`
            : `Выбрано ${this.files.length} · лимит достигнут`;
        }
      }
    }

    render() {
      this.updateControls();
      if (!this.previewEl) return;

      this.clearObjectUrls();
      this.previewEl.innerHTML = '';
      this.previewEl.hidden = this.files.length === 0;

      this.files.forEach((file, index) => {
        const url = URL.createObjectURL(file);
        this.objectUrls.push(url);

        const item = document.createElement('div');
        item.className = 'image-preview-item';

        const img = document.createElement('img');
        img.src = url;
        img.alt = '';
        img.decoding = 'async';

        const meta = document.createElement('span');
        meta.className = 'image-preview-name';
        meta.textContent = file.name;

        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'image-preview-remove';
        remove.setAttribute('aria-label', `Удалить фото ${file.name}`);
        remove.innerHTML = '<i data-lucide="x" class="icon icon-xs" aria-hidden="true"></i>';
        remove.addEventListener('click', () => {
          this.files.splice(index, 1);
          this.hideError();
          this.syncInput();
          this.render();
          if (window.refreshIcons) window.refreshIcons();
        });

        item.append(img, meta, remove);
        this.previewEl.appendChild(item);
      });

      if (window.refreshIcons) window.refreshIcons();
    }
  }

  function initImagePickers(scope) {
    (scope || document).querySelectorAll('.image-picker').forEach((root) => {
      new ImagePicker(root).init();
    });
  }

  window.initImagePickers = initImagePickers;
  document.addEventListener('DOMContentLoaded', () => initImagePickers());
})();
