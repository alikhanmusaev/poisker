document.addEventListener('DOMContentLoaded', async () => {
  'use strict';

  const P = window.Poisker || {};
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
  const contactCaptcha = document.getElementById('contact-captcha');

  function captchaAnswerValue() {
    const input = contactCaptcha?.querySelector('.captcha-answer-input');
    return input?.value.trim() || '';
  }

  function showCaptchaBlock(question, prompt) {
    if (!contactCaptcha) return;
    contactCaptcha.hidden = false;
    const questionEl = contactCaptcha.querySelector('.captcha-question');
    const promptEl = contactCaptcha.querySelector('.captcha-prompt');
    if (questionEl && question) questionEl.textContent = String(question);
    if (promptEl && prompt) promptEl.textContent = String(prompt);
    contactCaptcha.querySelector('.captcha-answer-input')?.focus();
    if (window.refreshIcons) refreshIcons();
  }

  async function requestContact() {
    if (!contactUrl || !P.isSameOriginUrl?.(contactUrl)) {
      return { res: { ok: false, status: 0 }, data: {} };
    }
    const headers = {
      Accept: 'application/json',
      'X-CSRFToken': P.csrfToken?.() || '',
    };
    const answer = captchaAnswerValue();
    const body = new URLSearchParams();
    if (answer) body.set('captcha_answer', answer);
    const res = await fetch(contactUrl, {
      method: 'POST',
      headers,
      body,
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
    if (contactCaptcha) contactCaptcha.hidden = true;
    if (window.refreshIcons) refreshIcons();
  }

  if (editLink && typeof findSavedPost === 'function' && P.isPostId?.(postId) && metaUrl && P.isSameOriginUrl?.(metaUrl)) {
    const saved = findSavedPost(postId);
    if (saved?.url && P.isAllowedEditUrl?.(saved.url)) {
      try {
        const token = new URL(saved.url, window.location.origin).searchParams.get('token');
        if (token) {
          const res = await fetch(`${metaUrl}?token=${encodeURIComponent(token)}`, {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
          });
          const data = (await P.parseJsonResponse?.(res)) || {};
          if (data.ok && data.can_edit) {
            editLink.href = saved.url;
            editLink.hidden = false;
          }
        }
      } catch (_e) {
        /* ignore */
      }
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
    if (data.captcha_required) {
      showCaptchaBlock(data.captcha_question, data.captcha_prompt || 'Сколько будет');
      showContactError(data.error || 'Подтвердите, что вы не робот');
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
