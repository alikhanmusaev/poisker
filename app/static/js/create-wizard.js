(function () {
  const STEP_TITLES = {
    1: 'Описание',
    2: 'Категория',
    3: 'Контакты',
    4: 'Фото',
    5: 'Проверка данных',
  };

  const TOTAL_STEPS = 5;
  const DRAFT_KEY = 'poisker_create_draft_v1';
  const DRAFT_FIELDS = ['title', 'body', 'category', 'city', 'price', 'seller_name', 'phone'];

  function readLabels() {
    const node = document.getElementById('create-wizard-labels');
    if (!node) return { cities: {}, categories: {} };
    try {
      return JSON.parse(node.textContent);
    } catch (e) {
      return { cities: {}, categories: {} };
    }
  }

  function formatPrice(value) {
    const digits = String(value || '').replace(/\D/g, '');
    if (!digits) return null;
    const amount = parseInt(digits, 10);
    if (Number.isNaN(amount) || amount < 0) return null;
    return `${amount.toLocaleString('ru-RU')} ₽`;
  }

  function fieldValue(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  }

  function selectLabel(map, key) {
    return map[key] || key || '—';
  }

  function showFieldError(field, message) {
    if (!field) return;
    field.setCustomValidity(message || '');
    field.reportValidity();
    field.focus();
  }

  function clearFieldErrors(form) {
    form.querySelectorAll('input, textarea, select').forEach((field) => field.setCustomValidity(''));
  }

  function limits() {
    const form = document.getElementById('create-post-form');
    return {
      titleMin: parseInt(form?.dataset.titleMin || '5', 10),
      titleMax: parseInt(form?.dataset.titleMax || '70', 10),
      bodyMin: parseInt(form?.dataset.bodyMin || '20', 10),
      bodyMax: parseInt(form?.dataset.bodyMax || '3000', 10),
    };
  }

  function validateStep(step, form) {
    clearFieldErrors(form);

    if (step === 1) {
      const { titleMin, titleMax, bodyMin, bodyMax } = limits();
      const title = document.getElementById('title');
      const body = document.getElementById('body');
      const titleVal = fieldValue('title');
      const bodyVal = fieldValue('body');
      if (titleVal.length < titleMin) {
        showFieldError(title, `Заголовок — минимум ${titleMin} символов`);
        return false;
      }
      if (titleVal.length > titleMax) {
        showFieldError(title, `Заголовок — максимум ${titleMax} символов`);
        return false;
      }
      if (bodyVal.length < bodyMin) {
        showFieldError(body, `Описание — минимум ${bodyMin} символов`);
        return false;
      }
      if (bodyVal.length > bodyMax) {
        showFieldError(body, `Описание — максимум ${bodyMax} символов`);
        return false;
      }
      return true;
    }

    if (step === 2) {
      const cityInput = document.getElementById('city-input');
      const price = document.getElementById('price-display');
      if (!fieldValue('category')) {
        showFieldError(document.getElementById('category'), 'Выберите категорию');
        return false;
      }
      if (!fieldValue('city')) {
        showFieldError(cityInput, 'Выберите город из подсказок');
        return false;
      }
      const priceRaw = fieldValue('price');
      if (priceRaw && (parseInt(priceRaw, 10) < 0 || Number.isNaN(parseInt(priceRaw, 10)))) {
        showFieldError(price, 'Укажите корректную цену');
        return false;
      }
      return true;
    }

    if (step === 3) {
      const sellerName = document.getElementById('seller_name');
      const phone = document.getElementById('phone');
      const nameVal = fieldValue('seller_name');
      const phoneVal = fieldValue('phone');
      if (nameVal.length < 2) {
        showFieldError(sellerName, 'Укажите имя');
        return false;
      }
      const phoneDigits = phoneVal.replace(/\D/g, '');
      if (phoneDigits.length < 11) {
        showFieldError(phone, 'Укажите номер полностью');
        return false;
      }
      return true;
    }

    return true;
  }

  function collectPreviewImages() {
    const preview = document.querySelector('.image-picker-preview');
    if (!preview) return [];
    return Array.from(preview.querySelectorAll('img'))
      .map((img) => img.src)
      .filter(Boolean);
  }

  function readCoverIndex() {
    const field = document.getElementById('cover-index-field');
    return field ? parseInt(field.value || '0', 10) : 0;
  }

  function setCoverIndex(index) {
    const field = document.getElementById('cover-index-field');
    const preview = document.querySelector('.image-picker-preview');
    if (!field || !preview) return;
    const items = Array.from(preview.querySelectorAll('.image-preview-item'));
    const safe = Math.min(Math.max(index, 0), Math.max(items.length - 1, 0));
    field.value = String(safe);
    items.forEach((item, i) => {
      item.classList.toggle('is-cover', i === safe);
      let badge = item.querySelector('.image-preview-cover');
      if (i === safe && !badge) {
        badge = document.createElement('span');
        badge.className = 'image-preview-cover';
        badge.textContent = 'Обложка';
        item.appendChild(badge);
      } else if (i !== safe && badge) {
        badge.remove();
      }
    });
  }

  function initCoverPicker() {
    const preview = document.querySelector('.image-picker-preview');
    if (!preview || preview.dataset.coverInit === '1') return;
    preview.dataset.coverInit = '1';
    preview.addEventListener('click', (event) => {
      const item = event.target.closest('.image-preview-item');
      if (!item) return;
      const items = Array.from(preview.querySelectorAll('.image-preview-item'));
      const index = items.indexOf(item);
      if (index >= 0) setCoverIndex(index);
    });
    setCoverIndex(readCoverIndex());
  }

  function readDraft() {
    try {
      const raw = localStorage.getItem(DRAFT_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function draftHasContent(data) {
    if (!data) return false;
    return DRAFT_FIELDS.some((id) => {
      const value = data[id];
      return value != null && String(value).trim() !== '';
    });
  }

  function writeDraft() {
    const form = document.getElementById('create-post-form');
    if (!form) return;
    const data = { step: 1 };
    DRAFT_FIELDS.forEach((id) => {
      const el = document.getElementById(id);
      if (el) data[id] = el.value;
    });
    const active = form.querySelector('.post-wizard-step.is-active');
    if (active) data.step = parseInt(active.dataset.step || '1', 10);
    if (!draftHasContent(data)) {
      clearDraft();
      return;
    }
    localStorage.setItem(DRAFT_KEY, JSON.stringify(data));
  }

  function clearDraft() {
    localStorage.removeItem(DRAFT_KEY);
  }

  function applyDraft(draft) {
    if (!draft) return;
    const labels = readLabels();
    DRAFT_FIELDS.forEach((id) => {
      if (id === 'city') {
        const hidden = document.getElementById('city');
        const input = document.getElementById('city-input');
        if (hidden && draft[id] != null) hidden.value = draft[id];
        if (input && draft[id]) input.value = labels.cities[draft[id]] || draft[id];
        return;
      }
      if (id === 'price') {
        const hidden = document.getElementById('price');
        const display = document.getElementById('price-display');
        const hint = document.getElementById('price-hint');
        if (hidden && draft[id] != null) hidden.value = draft[id];
        if (display && draft[id] && window.formatPriceDisplay) {
          display.value = window.formatPriceDisplay(String(draft[id]));
        }
        if (hint && draft[id] && window.priceVerbalHint) {
          hint.textContent = window.priceVerbalHint(parseInt(draft[id], 10));
          hint.classList.remove('is-empty');
        }
        return;
      }
      const el = document.getElementById(id);
      if (el && draft[id] != null) el.value = draft[id];
    });
  }

  function initDraftStorage(goToStep) {
    const banner = document.getElementById('wizard-draft-banner');
    const restoreBtn = document.getElementById('wizard-draft-restore');
    const discardBtn = document.getElementById('wizard-draft-discard');
    const form = document.getElementById('create-post-form');
    if (!form) return;

    const existing = readDraft();
    if (existing && !draftHasContent(existing)) {
      clearDraft();
    } else if (existing && draftHasContent(existing) && banner) {
      banner.hidden = false;
    }

    restoreBtn?.addEventListener('click', () => {
      const draft = readDraft();
      applyDraft(draft);
      if (draft?.step) goToStep(draft.step, { skipValidate: true, focus: false });
      if (banner) banner.hidden = true;
    });

    discardBtn?.addEventListener('click', () => {
      clearDraft();
      if (banner) banner.hidden = true;
    });

    let timer = null;
    const scheduleSave = () => {
      clearTimeout(timer);
      timer = setTimeout(writeDraft, 400);
    };
    DRAFT_FIELDS.forEach((id) => {
      document.getElementById(id)?.addEventListener('input', scheduleSave);
      document.getElementById(id)?.addEventListener('change', scheduleSave);
    });
    document.getElementById('city-input')?.addEventListener('input', scheduleSave);
    document.getElementById('price-display')?.addEventListener('input', scheduleSave);
    form.addEventListener('change', scheduleSave);
  }

  function buildPreviewHtml(labels) {
    const title = fieldValue('title');
    const body = fieldValue('body');
    const city = selectLabel(labels.cities, fieldValue('city'));
    const category = selectLabel(labels.categories, fieldValue('category'));
    const sellerName = fieldValue('seller_name');
    const phone = fieldValue('phone');
    const price = formatPrice(fieldValue('price'));
    const images = collectPreviewImages();
    const coverIdx = readCoverIndex();
    const ordered = images.length
      ? [images[coverIdx] || images[0], ...images.filter((_, i) => i !== coverIdx)]
      : [];

    const gallery = ordered.length
      ? `<div class="post-submit-preview-gallery">${ordered
          .map((src) => `<img src="${src}" alt="">`)
          .join('')}</div>`
      : `<div class="post-submit-preview-placeholder"><i data-lucide="image" class="icon icon-xl" aria-hidden="true"></i><span>Без фото</span></div>`;

    const priceHtml = price
      ? `<p class="post-submit-preview-price">${price}</p>`
      : '<p class="post-submit-preview-price post-submit-preview-price-muted">Цена не указана</p>';

    return `
      <article class="post-submit-preview-card">
        ${gallery}
        ${priceHtml}
        <h3 class="post-submit-preview-title">${escapeHtml(title)}</h3>
        <p class="post-submit-preview-meta">
          <i data-lucide="user" class="icon icon-xs" aria-hidden="true"></i>
          <span>${escapeHtml(sellerName)}</span>
          <span class="meta-dot">·</span>
          <i data-lucide="map-pin" class="icon icon-xs" aria-hidden="true"></i>
          <span>${escapeHtml(city)}</span>
          <span class="meta-dot">·</span>
          <i data-lucide="tag" class="icon icon-xs" aria-hidden="true"></i>
          <span>${escapeHtml(category)}</span>
        </p>
        <p class="post-submit-preview-body">${escapeHtml(body)}</p>
        <p class="post-submit-preview-phone">
          <i data-lucide="phone" class="icon icon-sm" aria-hidden="true"></i>
          <span>Телефон: ${escapeHtml(phone)}</span>
        </p>
      </article>
    `;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function updateCaptchaWidget(meta) {
    if (!meta) return;
    const question = document.querySelector('.captcha-question');
    const prompt = document.querySelector('.captcha-prompt');
    if (question && meta.captcha_question) question.textContent = meta.captcha_question;
    if (prompt && meta.captcha_prompt) prompt.textContent = meta.captcha_prompt;
    const answer = document.querySelector('.captcha-answer-input');
    if (answer) answer.value = '';
  }

  function showSubmitErrors(errors) {
    const box = document.getElementById('wizard-submit-errors');
    if (!box || !errors?.length) return;
    box.innerHTML = errors
      .map(
        (error) =>
          `<p class="error"><i data-lucide="alert-circle" class="icon icon-sm" aria-hidden="true"></i>${escapeHtml(error)}</p>`
      )
      .join('');
    box.hidden = false;
    if (window.refreshIcons) window.refreshIcons();
  }

  function showSuccessStep(data) {
    const form = document.getElementById('create-post-form');
    const successSection = document.getElementById('wizard-publish-success');
    const panel = successSection?.querySelector('.publish-success');
    if (!form || !successSection || !panel) return;

    form.hidden = true;
    successSection.hidden = false;

    panel.dataset.editUrl = data.edit_url;
    panel.dataset.postId = data.post_id;
    panel.dataset.postTitle = data.title;
    panel.dataset.viewUrl = data.view_url || '';
    panel.dataset.moderationPending = data.moderation_pending ? '1' : '0';
    delete panel.dataset.publishInit;

    const pageTitle = document.getElementById('wizard-page-title');
    const stepLabel = document.getElementById('wizard-step-label');
    const progressBar = document.getElementById('wizard-progress-bar');
    const moderationPending = Boolean(data.moderation_pending);
    if (pageTitle) pageTitle.textContent = 'Готово';
    if (stepLabel) {
      stepLabel.textContent = moderationPending ? 'На проверке' : 'Опубликовано';
    }
    if (progressBar) progressBar.style.width = '100%';

    const headline = panel.querySelector('[data-success-headline]');
    const lead = panel.querySelector('[data-success-lead]');
    const openBtn = panel.querySelector('#open-post-btn');
    const openLabel = openBtn?.querySelector('span');
    const openIcon = openBtn?.querySelector('.icon');
    const editBtn = panel.querySelector('#edit-post-btn');

    if (headline) {
      headline.textContent = moderationPending
        ? 'Отправлено на проверку'
        : 'Объявление опубликовано';
    }
    if (lead) {
      lead.textContent = moderationPending
        ? 'Сейчас объявление видите только вы. После одобрения оно появится в каталоге.'
        : 'Объявление уже в каталоге. Сохраните ссылку — без неё редактировать не получится.';
    }
    if (openBtn && data.view_url) {
      openBtn.href = data.view_url;
      openBtn.hidden = false;
    }
    if (openLabel) {
      openLabel.textContent = moderationPending ? 'Посмотреть объявление' : 'Открыть объявление';
    }
    if (openIcon) {
      openIcon.setAttribute('data-lucide', moderationPending ? 'eye' : 'external-link');
    }
    if (editBtn && data.edit_url) {
      editBtn.href = data.edit_url;
    }

    const iconWrap = panel.querySelector('.publish-success-icon');
    const heroIcon = panel.querySelector('.publish-success-icon .icon');
    if (iconWrap) {
      iconWrap.classList.toggle('publish-success-icon--pending', moderationPending);
      iconWrap.classList.toggle('publish-success-icon--published', !moderationPending);
    }
    if (heroIcon) {
      heroIcon.setAttribute('data-lucide', moderationPending ? 'clock' : 'check-circle-2');
    }

    if (window.initPublishSuccess) window.initPublishSuccess(panel);
    if (window.refreshIcons) window.refreshIcons();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function initWizard() {
    const form = document.getElementById('create-post-form');
    if (!form) return;

    const labels = readLabels();
    const steps = Array.from(form.querySelectorAll('.post-wizard-step'));
    const progressBar = document.getElementById('wizard-progress-bar');
    const stepLabel = document.getElementById('wizard-step-label');
    const previewRoot = document.getElementById('post-submit-preview');
    const submitBtn = document.getElementById('wizard-submit-btn');
    let currentStep = parseInt(form.dataset.initialStep || '1', 10);

    function goToStep(step, options = {}) {
      const target = Math.min(Math.max(step, 1), TOTAL_STEPS);
      if (!options.skipValidate && target > currentStep) {
        for (let i = currentStep; i < target; i += 1) {
          if (!validateStep(i, form)) {
            goToStep(i, { skipValidate: true });
            return;
          }
        }
      }

      currentStep = target;
      steps.forEach((section) => {
        const active = parseInt(section.dataset.step, 10) === currentStep;
        section.hidden = !active;
        section.classList.toggle('is-active', active);
      });

      if (progressBar) {
        progressBar.style.width = `${(currentStep / TOTAL_STEPS) * 100}%`;
      }
      if (stepLabel) {
        stepLabel.textContent = `Шаг ${currentStep} из ${TOTAL_STEPS} · ${STEP_TITLES[currentStep]}`;
      }

      if (currentStep === TOTAL_STEPS && previewRoot) {
        previewRoot.innerHTML = buildPreviewHtml(labels);
        if (window.refreshIcons) window.refreshIcons();
      }

      if (currentStep === 4) {
        window.requestAnimationFrame(() => {
          initCoverPicker();
          setCoverIndex(readCoverIndex());
        });
      }

      const activeSection = steps.find((section) => parseInt(section.dataset.step, 10) === currentStep);
      const focusTarget = activeSection?.querySelector('input, textarea, select, button');
      if (focusTarget && options.focus !== false) {
        focusTarget.focus({ preventScroll: true });
      }

      if (options.scroll !== false) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }

    form.querySelectorAll('.wizard-next').forEach((btn) => {
      btn.addEventListener('click', () => {
        const next = parseInt(btn.dataset.next, 10);
        if (validateStep(currentStep, form)) {
          goToStep(next, { skipValidate: true });
        }
      });
    });

    form.querySelectorAll('.wizard-back').forEach((btn) => {
      btn.addEventListener('click', () => {
        goToStep(parseInt(btn.dataset.back, 10), { skipValidate: true, focus: false });
      });
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      for (let step = 1; step <= 3; step += 1) {
        if (!validateStep(step, form)) {
          goToStep(step, { skipValidate: true });
          return;
        }
      }
      if (currentStep !== TOTAL_STEPS) {
        goToStep(TOTAL_STEPS, { skipValidate: true });
        return;
      }

      const errorBox = document.getElementById('wizard-submit-errors');
      if (errorBox) errorBox.hidden = true;

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.setAttribute('aria-busy', 'true');
      }

      if (window.syncFormImagePickers) window.syncFormImagePickers(form);

      try {
        const response = await fetch(form.action || window.location.pathname, {
          method: 'POST',
          body: new FormData(form),
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            Accept: 'application/json',
          },
        });

        const data = await response.json();
        if (data.ok) {
          clearDraft();
          showSuccessStep(data);
          return;
        }

        showSubmitErrors(data.errors || ['Не удалось опубликовать']);
        if (data.captcha_question || data.captcha_prompt) {
          updateCaptchaWidget(data);
          document.querySelector('.captcha-answer-input')?.focus();
        }
        goToStep(TOTAL_STEPS, { skipValidate: true, scroll: false });
      } catch (e) {
        showSubmitErrors(['Ошибка сети. Попробуйте ещё раз.']);
        goToStep(TOTAL_STEPS, { skipValidate: true, scroll: false });
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.removeAttribute('aria-busy');
        }
      }
    });

    goToStep(currentStep, { skipValidate: true, focus: false });
    initDraftStorage(goToStep);

    if (window.initCityAutocomplete) {
      window.initCityAutocomplete(
        document.getElementById('city-input'),
        document.getElementById('city'),
        document.getElementById('city-suggestions'),
        labels.cities
      );
    }
    if (window.initPriceInput) {
      window.initPriceInput(
        document.getElementById('price-display'),
        document.getElementById('price'),
        document.getElementById('price-hint')
      );
    }

    const previewRootEl = document.querySelector('.image-picker-preview');
    if (previewRootEl && typeof MutationObserver !== 'undefined') {
      new MutationObserver(() => {
        initCoverPicker();
        const count = previewRootEl.querySelectorAll('.image-preview-item').length;
        const cover = readCoverIndex();
        if (cover >= count) setCoverIndex(0);
        else setCoverIndex(cover);
      }).observe(previewRootEl, { childList: true });
    }
  }

  document.addEventListener('DOMContentLoaded', initWizard);
})();
