(function () {
  const STEP_TITLES = {
    1: 'Описание',
    2: 'Категория',
    3: 'Контакты',
    4: 'Фото',
    5: 'Проверка данных',
  };

  const TOTAL_STEPS = 5;

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

  function validateStep(step, form) {
    clearFieldErrors(form);

    if (step === 1) {
      const title = document.getElementById('title');
      const body = document.getElementById('body');
      const titleVal = fieldValue('title');
      const bodyVal = fieldValue('body');
      if (titleVal.length < 5) {
        showFieldError(title, 'Заголовок — минимум 5 символов');
        return false;
      }
      if (bodyVal.length < 20) {
        showFieldError(body, 'Описание — минимум 20 символов');
        return false;
      }
      return true;
    }

    if (step === 2) {
      const category = document.getElementById('category');
      const city = document.getElementById('city');
      const price = document.getElementById('price');
      if (!fieldValue('category')) {
        showFieldError(category, 'Выберите категорию');
        return false;
      }
      if (!fieldValue('city')) {
        showFieldError(city, 'Выберите город');
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

  function buildPreviewHtml(labels) {
    const title = fieldValue('title');
    const body = fieldValue('body');
    const city = selectLabel(labels.cities, fieldValue('city'));
    const category = selectLabel(labels.categories, fieldValue('category'));
    const sellerName = fieldValue('seller_name');
    const phone = fieldValue('phone');
    const price = formatPrice(fieldValue('price'));
    const images = collectPreviewImages();

    const gallery = images.length
      ? `<div class="post-submit-preview-gallery">${images
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
    panel.dataset.viewUrl = data.view_url;
    delete panel.dataset.publishInit;

    const pageTitle = document.getElementById('wizard-page-title');
    const stepLabel = document.getElementById('wizard-step-label');
    const progressBar = document.getElementById('wizard-progress-bar');
    if (pageTitle) pageTitle.textContent = 'Готово';
    if (stepLabel) stepLabel.textContent = 'Опубликовано';
    if (progressBar) progressBar.style.width = '100%';

    document.body.classList.add('publish-success-gate');

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
          showSuccessStep(data);
          return;
        }

        showSubmitErrors(data.errors || ['Не удалось опубликовать']);
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
  }

  document.addEventListener('DOMContentLoaded', initWizard);
})();
