/**
 * City / settlement autocomplete — remote search via /api/locations/search/
 * Falls back to local citiesMap when provided (legacy).
 */
(function () {
  const SEARCH_URL = '/api/locations/search/';
  const POPULAR_URL = '/api/locations/popular/';
  const MIN_LEN = 2;
  const DEBOUNCE_MS = 300;

  function debounce(fn, wait) {
    let t = null;
    return function debounced(...args) {
      window.clearTimeout(t);
      t = window.setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function matchCitiesLocal(query, citiesMap, limit = 12) {
    const entries = Object.entries(citiesMap || {});
    const q = String(query || '').trim().toLowerCase();
    if (!q) return [];
    const starts = [];
    const contains = [];
    for (const [slug, label] of entries) {
      const name = String(label).toLowerCase();
      const slugLower = slug.toLowerCase();
      if (name.startsWith(q) || slugLower.startsWith(q)) {
        starts.push({ slug, label, id: null, display: label });
      } else if (name.includes(q) || slugLower.includes(q)) {
        contains.push({ slug, label, id: null, display: label });
      }
    }
    return starts.concat(contains).slice(0, limit);
  }

  function initCityAutocomplete(input, hiddenInput, listEl, citiesMap, options = {}) {
    if (!input || !hiddenInput || !listEl) return;

    let activeIndex = -1;
    let abortController = null;
    let loading = false;
    const useRemote = options.remote !== false;
    const onSelect = typeof options.onSelect === 'function' ? options.onSelect : null;
    const valueMode = options.valueMode || 'slug'; // slug | id
    const regionParam = options.region || '';

    function closeList() {
      listEl.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      activeIndex = -1;
    }

    function setLoading(on) {
      loading = on;
      input.classList.toggle('is-loading', on);
    }

    function renderList(items) {
      listEl.innerHTML = '';
      if (!items.length) {
        const li = document.createElement('li');
        li.className = 'suggest-empty';
        li.textContent = loading ? 'Поиск…' : 'Ничего не найдено';
        listEl.appendChild(li);
        listEl.hidden = false;
        input.setAttribute('aria-expanded', 'true');
        return;
      }
      items.forEach((item, index) => {
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'suggest-item';
        btn.setAttribute('role', 'option');
        btn.dataset.citySlug = item.slug || '';
        btn.dataset.cityId = item.id != null ? String(item.id) : '';
        btn.dataset.cityLabel = item.label || item.name || '';
        btn.dataset.cityDisplay = item.display || item.display_name || item.label || '';
        btn.innerHTML = window.Poisker
          ? `${window.Poisker.escapeHtml(item.label || item.name || '')}<span class="suggest-meta">${window.Poisker.escapeHtml(item.regionName || '')}</span>`
          : (item.display || item.label);
        if (index === activeIndex) btn.setAttribute('aria-selected', 'true');
        btn.addEventListener('mousedown', (event) => event.preventDefault());
        btn.addEventListener('click', () =>
          selectCity({
            slug: item.slug,
            id: item.id,
            label: item.label || item.name,
            display: item.display || item.display_name || item.label,
            regionSlug: item.regionSlug,
            region: item.region,
          })
        );
        li.appendChild(btn);
        listEl.appendChild(li);
      });
      listEl.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    function selectCity(item) {
      const P = window.Poisker;
      const slug = item.slug || '';
      if (valueMode === 'id') {
        if (!item.id) return;
        hiddenInput.value = String(item.id);
      } else {
        if (!slug || (P?.isSafeSlug && !P.isSafeSlug(slug))) return;
        hiddenInput.value = slug;
      }
        input.value = item.display || item.label || item.name || slug || '';
      hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
      closeList();
      if (onSelect) onSelect(hiddenInput.value, item.label || item.display, item);
    }

    async function fetchRemote(query) {
      if (abortController) abortController.abort();
      abortController = new AbortController();
      const params = new URLSearchParams({ q: query, limit: '20' });
      if (regionParam) params.set('region', regionParam);
      setLoading(true);
      try {
        const res = await fetch(`${SEARCH_URL}?${params}`, {
          signal: abortController.signal,
          headers: { Accept: 'application/json' },
        });
        if (!res.ok) throw new Error('search failed');
        const data = await res.json();
        return (data.results || []).map((row) => ({
          id: row.id,
          slug: row.slug,
          label: row.name,
          name: row.name,
          display: row.display_name,
          display_name: row.display_name,
          regionName: row.region?.name || '',
          regionSlug: row.region?.slug || '',
          region: row.region || null,
        }));
      } catch (err) {
        if (err?.name === 'AbortError') return null;
        return matchCitiesLocal(query, citiesMap);
      } finally {
        setLoading(false);
      }
    }

    async function fetchPopular() {
      try {
        const res = await fetch(`${POPULAR_URL}?limit=12`, {
          headers: { Accept: 'application/json' },
        });
        if (!res.ok) return [];
        const data = await res.json();
        return (data.results || []).map((row) => ({
          id: row.id,
          slug: row.slug,
          label: row.name,
          name: row.name,
          display: row.display_name,
          regionName: row.region?.name || '',
          regionSlug: row.region?.slug || '',
          region: row.region || null,
        }));
      } catch (_e) {
        return [];
      }
    }

    const runSearch = debounce(async () => {
      const query = String(input.value || '').trim();
      if (!query) {
        if (useRemote) {
          const popular = await fetchPopular();
          activeIndex = -1;
          renderList(popular);
        } else {
          closeList();
        }
        return;
      }
      if (query.length < MIN_LEN) {
        listEl.innerHTML = '';
        const li = document.createElement('li');
        li.className = 'suggest-empty';
        li.textContent = 'Введите минимум 2 символа';
        listEl.appendChild(li);
        listEl.hidden = false;
        return;
      }
      let items;
      if (useRemote) {
        items = await fetchRemote(query);
        if (items === null) return; // aborted
      } else {
        items = matchCitiesLocal(query, citiesMap);
      }
      activeIndex = -1;
      renderList(items || []);
    }, DEBOUNCE_MS);

    input.addEventListener('input', () => {
      hiddenInput.value = '';
      runSearch();
    });
    input.addEventListener('focus', () => runSearch());
    input.addEventListener('blur', () => {
      window.setTimeout(() => closeList(), 150);
    });
    input.addEventListener('keydown', (event) => {
      const optionsEls = Array.from(listEl.querySelectorAll('.suggest-item'));
      if (!optionsEls.length && event.key !== 'Escape') return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        activeIndex = Math.min(activeIndex + 1, optionsEls.length - 1);
        optionsEls.forEach((btn, i) =>
          btn.setAttribute('aria-selected', i === activeIndex ? 'true' : 'false')
        );
        optionsEls[activeIndex]?.scrollIntoView({ block: 'nearest' });
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
        optionsEls.forEach((btn, i) =>
          btn.setAttribute('aria-selected', i === activeIndex ? 'true' : 'false')
        );
        optionsEls[activeIndex]?.scrollIntoView({ block: 'nearest' });
      } else if (event.key === 'Enter' && activeIndex >= 0) {
        event.preventDefault();
        const btn = optionsEls[activeIndex];
        if (btn) {
          selectCity({
            slug: btn.dataset.citySlug,
            id: btn.dataset.cityId ? Number(btn.dataset.cityId) : null,
            label: btn.dataset.cityLabel,
            display: btn.dataset.cityDisplay,
          });
        }
      } else if (event.key === 'Escape') {
        closeList();
      }
    });

    return { selectCity, closeList };
  }

  window.initCityAutocomplete = initCityAutocomplete;
  window.matchCities = function (query, citiesMap, limit) {
    return matchCitiesLocal(query, citiesMap, limit).map((i) => [i.slug, i.label]);
  };
})();
