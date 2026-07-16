document.addEventListener('DOMContentLoaded', async () => {
  'use strict';

  const P = window.Poisker || {};
  const root = document.querySelector('[data-post-detail]');
  if (!root) return;

  const contactUrl = root.dataset.contactUrl || '';
  const showPhone = document.getElementById('show-phone');
  const phoneDisplay = document.getElementById('phone-display');
  const phoneText = document.getElementById('phone-text');
  const phoneLink = document.getElementById('phone-link');
  const sharePost = document.getElementById('share-post');
  const contactError = document.getElementById('contact-error');

  async function requestContact() {
    if (!contactUrl || !P.isSameOriginUrl?.(contactUrl)) {
      return { res: { ok: false, status: 0 }, data: {} };
    }
    const res = await fetch(contactUrl, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'X-CSRFToken': P.csrfToken?.() || '',
      },
      body: new URLSearchParams(),
      credentials: 'same-origin',
    });
    const data = (await P.parseJsonResponse?.(res)) || {};
    return { res, data };
  }

  function showContactError(message) {
    if (!contactError || !message) return;
    contactError.textContent = String(message);
    contactError.hidden = false;
  }

  function clearContactError() {
    if (!contactError) return;
    contactError.textContent = '';
    contactError.hidden = true;
  }

  function showPhoneResult(phone, button) {
    clearContactError();
    const safePhone = String(phone || '').slice(0, 24);
    if (phoneText) phoneText.textContent = safePhone;
    if (phoneLink) {
      const digits = (P.digitsOnly || ((v) => v.replace(/\D/g, '')))(safePhone);
      phoneLink.href = digits.length >= 10 ? `tel:+${digits}` : '#';
    }
    phoneDisplay?.classList.remove('hidden');
    if (button) button.hidden = true;
    if (window.refreshIcons) refreshIcons();
  }

  showPhone?.addEventListener('click', async function () {
    if (!contactUrl) return;
    clearContactError();
    const { res, data } = await requestContact();
    if (res.ok && data.phone) {
      showPhoneResult(data.phone, this);
      return;
    }
    if (res.status === 401 || data.login_required) {
      showContactError(data.error || 'Войдите, чтобы увидеть телефон.');
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
    if (typeof copyText === 'function') {
      await copyText(window.location.href);
    }
  });

  if (window.refreshIcons) refreshIcons();
});
