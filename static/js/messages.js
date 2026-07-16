document.addEventListener('DOMContentLoaded', () => {
  const thread = document.getElementById('message-thread');
  if (thread) {
    thread.scrollTop = thread.scrollHeight;
  }
  const input = document.querySelector('.message-compose-input');
  if (input) {
    input.focus();
  }

  const form = document.getElementById('message-compose-form');
  const fileInput = document.getElementById('id_image');
  const preview = document.getElementById('message-image-preview');
  const previewImg = document.getElementById('message-image-preview-img');
  const previewClear = document.getElementById('message-image-preview-clear');

  if (form) {
    form.addEventListener('submit', (event) => {
      const body = (input?.value || '').trim();
      const hasFile = Boolean(fileInput?.files && fileInput.files[0]);
      if (!body && !hasFile) {
        event.preventDefault();
        input?.focus();
      }
    });
  }

  if (!fileInput || !preview || !previewImg) {
    return;
  }

  let previewUrl = null;

  const hidePreview = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      previewUrl = null;
    }
    previewImg.removeAttribute('src');
    preview.hidden = true;
  };

  fileInput.addEventListener('change', () => {
    hidePreview();
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      return;
    }
    previewUrl = URL.createObjectURL(file);
    previewImg.src = previewUrl;
    preview.hidden = false;
    if (window.refreshIcons) {
      window.refreshIcons();
    }
  });

  previewClear?.addEventListener('click', () => {
    fileInput.value = '';
    hidePreview();
  });
});
