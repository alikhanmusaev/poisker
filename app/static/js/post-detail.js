document.addEventListener('DOMContentLoaded', async () => {
  const root = document.querySelector('[data-post-detail]');
  if (!root) return;

  const postId = root.dataset.postId || '';
  const contactUrl = root.dataset.contactUrl || '';
  const metaUrl = root.dataset.metaUrl || '';
  const editLink = document.getElementById('owner-edit-link');
  const showPhone = document.getElementById('show-phone');
  const phoneDisplay = document.getElementById('phone-display');
  const phoneText = document.getElementById('phone-text');
  const phoneLink = document.getElementById('phone-link');
  const sharePost = document.getElementById('share-post');
  const contactError = document.getElementById('contact-error');

  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
  }

  async function requestContact() {
    const headers = {
      Accept: 'application/json',
      'X-CSRFToken': csrfToken(),
    };
    const res = await fetch(contactUrl, { method: 'POST', headers });
    let data = {};
    try {
      data = await res.json();
    } catch (e) {}
    return { res, data };
  }

  function showContactError(message) {
    if (!contactError || !message) return;
    contactError.textContent = message;
    contactError.hidden = false;
  }

  function clearContactError() {
    if (!contactError) return;
    contactError.textContent = '';
    contactError.hidden = true;
  }

  function showPhoneResult(phone, button) {
    clearContactError();
    if (phoneText) phoneText.textContent = phone;
    if (phoneLink) {
      const digits = phone.replace(/\D/g, '');
      phoneLink.href = digits ? `tel:+${digits}` : '#';
    }
    phoneDisplay?.classList.remove('hidden');
    if (button) button.hidden = true;
    if (window.refreshIcons) refreshIcons();
  }

  if (editLink && typeof findSavedPost === 'function') {
    const saved = findSavedPost(postId);
    if (saved?.url && metaUrl) {
      try {
        const token = new URL(saved.url, window.location.origin).searchParams.get('token');
        if (token) {
          const res = await fetch(`${metaUrl}?token=${encodeURIComponent(token)}`, {
            headers: { Accept: 'application/json' },
          });
          const data = await res.json();
          if (data.ok && data.can_edit) {
            editLink.href = saved.url;
            editLink.hidden = false;
          }
        }
      } catch (e) {}
    }
  }

  showPhone?.addEventListener('click', async function () {
    if (!contactUrl) return;
    clearContactError();
    const { res, data } = await requestContact();
    if (res.ok && data.phone) {
      showPhoneResult(data.phone, this);
      return;
    }
    if (res.status === 429) {
      showContactError(data.error || 'Слишком много запросов. Попробуйте через час.');
      return;
    }
    showContactError(data.error || 'Не удалось показать телефон. Попробуйте позже.');
  });

  sharePost?.addEventListener('click', async () => {
    const shareData = { title: document.title, url: window.location.href };
    if (navigator.share) {
      try {
        await navigator.share(shareData);
        return;
      } catch (e) {
        if (e.name === 'AbortError') return;
      }
    }
    await copyText(window.location.href);
  });

  if (window.refreshIcons) refreshIcons();
});
