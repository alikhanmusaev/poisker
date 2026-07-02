(function () {
  function pluralRu(n, one, few, many) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return one;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
    return many;
  }

  function priceDigits(value) {
    return String(value || '').replace(/\D/g, '');
  }

  function formatPriceDisplay(digits) {
    if (!digits) return '';
    const amount = parseInt(digits, 10);
    if (Number.isNaN(amount)) return '';
    return amount.toLocaleString('ru-RU');
  }

  function priceVerbalHint(amount) {
    if (!amount) return 'Например: 1 500 или 25 000';
    const formatted = `${amount.toLocaleString('ru-RU')} ₽`;
    if (amount < 1000) {
      return `${formatted} — до тысячи рублей`;
    }

    const parts = [];
    let rest = amount;
    const millions = Math.floor(rest / 1_000_000);
    if (millions) {
      parts.push(`${millions} ${pluralRu(millions, 'миллион', 'миллиона', 'миллионов')}`);
      rest %= 1_000_000;
    }
    const thousands = Math.floor(rest / 1000);
    if (thousands) {
      parts.push(`${thousands} ${pluralRu(thousands, 'тысяча', 'тысячи', 'тысяч')}`);
      rest %= 1000;
    }
    if (rest) {
      parts.push(`${rest}`);
    }
    return `${formatted} — ${parts.join(' ')} руб.`;
  }

  function initPriceInput(displayInput, hiddenInput, hintEl) {
    if (!displayInput || !hiddenInput) return;

    function sync() {
      const digits = priceDigits(displayInput.value).slice(0, 9);
      hiddenInput.value = digits;
      const caretFromEnd = displayInput.value.length - (displayInput.selectionStart ?? displayInput.value.length);
      displayInput.value = formatPriceDisplay(digits);
      if (displayInput === document.activeElement && displayInput.setSelectionRange) {
        const pos = Math.max(0, displayInput.value.length - caretFromEnd);
        displayInput.setSelectionRange(pos, pos);
      }
      const amount = digits ? parseInt(digits, 10) : 0;
      if (hintEl) {
        hintEl.textContent = priceVerbalHint(amount);
        hintEl.classList.toggle('is-empty', !digits);
      }
      hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    displayInput.addEventListener('input', sync);
    displayInput.addEventListener('blur', sync);

    if (hiddenInput.value) {
      displayInput.value = formatPriceDisplay(hiddenInput.value);
    }
    sync();
  }

  function matchCities(query, citiesMap, limit = 8) {
    const entries = Object.entries(citiesMap || {});
    const q = String(query || '').trim().toLowerCase();
    if (!q) return [];
    return entries
      .filter(([slug, label]) => {
        const name = String(label).toLowerCase();
        return name.includes(q) || slug.toLowerCase().includes(q);
      })
      .slice(0, limit);
  }

  function initCityAutocomplete(input, hiddenInput, listEl, citiesMap) {
    if (!input || !hiddenInput || !listEl) return;

    let activeIndex = -1;

    function closeList() {
      listEl.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      activeIndex = -1;
    }

    function renderList(items) {
      listEl.innerHTML = '';
      if (!items.length) {
        listEl.hidden = true;
        input.setAttribute('aria-expanded', 'false');
        return;
      }
      items.forEach(([slug, label], index) => {
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'suggest-item';
        btn.setAttribute('role', 'option');
        btn.dataset.citySlug = slug;
        btn.dataset.cityLabel = label;
        btn.textContent = label;
        if (index === activeIndex) btn.setAttribute('aria-selected', 'true');
        btn.addEventListener('mousedown', (event) => event.preventDefault());
        btn.addEventListener('click', () => selectCity(slug, label));
        li.appendChild(btn);
        listEl.appendChild(li);
      });
      listEl.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    function selectCity(slug, label) {
      hiddenInput.value = slug;
      input.value = label;
      hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
      closeList();
    }

    function openList() {
      const query = String(input.value || '').trim();
      if (!query) {
        closeList();
        return;
      }
      const items = matchCities(query, citiesMap);
      activeIndex = -1;
      renderList(items);
    }

    input.addEventListener('input', () => {
      hiddenInput.value = '';
      openList();
    });
    input.addEventListener('blur', () => {
      window.setTimeout(() => {
        closeList();
        const slug = hiddenInput.value;
        if (slug && citiesMap[slug]) {
          input.value = citiesMap[slug];
        }
      }, 120);
    });
    input.addEventListener('keydown', (event) => {
      const options = Array.from(listEl.querySelectorAll('.suggest-item'));
      if (!options.length && event.key !== 'Escape') return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        activeIndex = Math.min(activeIndex + 1, options.length - 1);
        options.forEach((btn, i) => btn.setAttribute('aria-selected', i === activeIndex ? 'true' : 'false'));
        options[activeIndex]?.scrollIntoView({ block: 'nearest' });
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
        options.forEach((btn, i) => btn.setAttribute('aria-selected', i === activeIndex ? 'true' : 'false'));
        options[activeIndex]?.scrollIntoView({ block: 'nearest' });
      } else if (event.key === 'Enter' && activeIndex >= 0) {
        event.preventDefault();
        const btn = options[activeIndex];
        selectCity(btn.dataset.citySlug, btn.dataset.cityLabel);
      } else if (event.key === 'Escape') {
        closeList();
      }
    });

    if (hiddenInput.value && citiesMap[hiddenInput.value]) {
      input.value = citiesMap[hiddenInput.value];
    }
  }

  window.priceDigits = priceDigits;
  window.formatPriceDisplay = formatPriceDisplay;
  window.priceVerbalHint = priceVerbalHint;
  window.initPriceInput = initPriceInput;
  window.initCityAutocomplete = initCityAutocomplete;
  window.matchCities = matchCities;
})();
