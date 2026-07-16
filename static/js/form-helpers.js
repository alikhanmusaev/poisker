(function () {
  function matchCities(query, citiesMap, limit = 12) {
    const entries = Object.entries(citiesMap || {});
    const q = String(query || '').trim().toLowerCase();
    if (!q) return [];
    const starts = [];
    const contains = [];
    for (const [slug, label] of entries) {
      const name = String(label).toLowerCase();
      const slugLower = slug.toLowerCase();
      if (name.startsWith(q) || slugLower.startsWith(q)) {
        starts.push([slug, label]);
      } else if (name.includes(q) || slugLower.includes(q)) {
        contains.push([slug, label]);
      }
    }
    return starts.concat(contains).slice(0, limit);
  }

  function initCityAutocomplete(input, hiddenInput, listEl, citiesMap, options = {}) {
    if (!input || !hiddenInput || !listEl) return;

    let activeIndex = -1;
    const popularSlugs = Array.isArray(options.popular) ? options.popular : [];
    const onSelect = typeof options.onSelect === 'function' ? options.onSelect : null;

    function closeList() {
      listEl.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      activeIndex = -1;
    }

    function popularItems() {
      return popularSlugs
        .map((slug) => [slug, citiesMap[slug]])
        .filter(([, label]) => Boolean(label));
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
      const P = window.Poisker;
      if (!P?.isSafeSlug?.(slug) || !citiesMap[slug]) return;
      hiddenInput.value = slug;
      input.value = label;
      hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
      closeList();
      if (onSelect) onSelect(slug, label);
    }

    function openList() {
      const query = String(input.value || '').trim();
      if (!query) {
        const popular = popularItems();
        if (popular.length) {
          activeIndex = -1;
          renderList(popular);
        } else {
          closeList();
        }
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
    input.addEventListener('focus', openList);
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
      const optionsEls = Array.from(listEl.querySelectorAll('.suggest-item'));
      if (!optionsEls.length && event.key !== 'Escape') return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        activeIndex = Math.min(activeIndex + 1, optionsEls.length - 1);
        optionsEls.forEach((btn, i) => btn.setAttribute('aria-selected', i === activeIndex ? 'true' : 'false'));
        optionsEls[activeIndex]?.scrollIntoView({ block: 'nearest' });
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
        optionsEls.forEach((btn, i) => btn.setAttribute('aria-selected', i === activeIndex ? 'true' : 'false'));
        optionsEls[activeIndex]?.scrollIntoView({ block: 'nearest' });
      } else if (event.key === 'Enter' && activeIndex >= 0) {
        event.preventDefault();
        const btn = optionsEls[activeIndex];
        if (btn?.dataset.citySlug && btn.dataset.cityLabel) {
          selectCity(btn.dataset.citySlug, btn.dataset.cityLabel);
        }
      } else if (event.key === 'Escape') {
        closeList();
      }
    });

    if (hiddenInput.value && citiesMap[hiddenInput.value]) {
      input.value = citiesMap[hiddenInput.value];
    }

    return { selectCity, openList, closeList };
  }

  window.initCityAutocomplete = initCityAutocomplete;
  window.matchCities = matchCities;
})();
