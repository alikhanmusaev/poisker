(function () {
  const form = document.getElementById('home-search-form');
  const categoryField = document.getElementById('category-field');
  const sortField = document.getElementById('sort-field');

  if (!form) return;

  function submitFeed() {
    if (window.htmx) htmx.trigger(form, 'submit');
  }

  function initCategoryCarousel() {
    const carousel = document.getElementById('category-carousel');
    const shell = document.getElementById('category-carousel-shell');
    const prevBtn = document.getElementById('category-carousel-prev');
    const nextBtn = document.getElementById('category-carousel-next');
    if (!carousel || !shell) return;

    let scrollRaf = 0;

    const scrollStep = () => Math.max(carousel.clientWidth * 0.75, 180);

    function activeChip() {
      return carousel.querySelector('.category-chip.is-active');
    }

    function updateCarouselState() {
      const maxScroll = carousel.scrollWidth - carousel.clientWidth;
      const hasOverflow = maxScroll > 4;
      const atStart = carousel.scrollLeft <= 4;
      const atEnd = carousel.scrollLeft >= maxScroll - 4;

      shell.toggleAttribute('data-fade-left', hasOverflow && !atStart);
      shell.toggleAttribute('data-fade-right', hasOverflow && !atEnd);

      if (prevBtn) {
        prevBtn.hidden = !hasOverflow;
        prevBtn.disabled = atStart;
      }
      if (nextBtn) {
        nextBtn.hidden = !hasOverflow;
        nextBtn.disabled = atEnd;
      }
    }

    function scrollChipIntoView(chip, behavior = 'auto') {
      if (!chip) return;
      const chipLeft = chip.offsetLeft;
      const chipRight = chipLeft + chip.offsetWidth;
      const viewLeft = carousel.scrollLeft;
      const viewRight = viewLeft + carousel.clientWidth;
      const padding = 12;

      let targetLeft = null;
      if (chipLeft < viewLeft + padding) {
        targetLeft = Math.max(chipLeft - padding, 0);
      } else if (chipRight > viewRight - padding) {
        targetLeft = chipRight - carousel.clientWidth + padding;
      }

      if (targetLeft === null) {
        window.requestAnimationFrame(updateCarouselState);
        return;
      }

      if (behavior === 'auto') {
        const prevSnap = carousel.style.scrollSnapType;
        carousel.style.scrollSnapType = 'none';
        carousel.scrollLeft = targetLeft;
        carousel.style.scrollSnapType = prevSnap;
      } else {
        carousel.scrollTo({ left: targetLeft, behavior });
      }
      window.requestAnimationFrame(updateCarouselState);
    }

    prevBtn?.addEventListener('click', () => {
      carousel.scrollBy({ left: -scrollStep(), behavior: 'smooth' });
    });

    nextBtn?.addEventListener('click', () => {
      carousel.scrollBy({ left: scrollStep(), behavior: 'smooth' });
    });

    carousel.addEventListener('scroll', () => {
      if (scrollRaf) return;
      scrollRaf = window.requestAnimationFrame(() => {
        scrollRaf = 0;
        updateCarouselState();
      });
    }, { passive: true });

    carousel.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        carousel.scrollBy({ left: -scrollStep(), behavior: 'smooth' });
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        carousel.scrollBy({ left: scrollStep(), behavior: 'smooth' });
      }
    });

    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(() => {
        updateCarouselState();
      });
      observer.observe(carousel);
    } else {
      window.addEventListener('resize', updateCarouselState);
    }

    window.requestAnimationFrame(() => {
      updateCarouselState();
      scrollChipIntoView(activeChip(), 'auto');
      if (window.refreshIcons) refreshIcons();
    });

    return { scrollChipIntoView, updateCarouselState };
  }

  const carouselApi = initCategoryCarousel();

  function cssEsc(slug) {
    const P = window.Poisker;
    return P?.cssEscape ? P.cssEscape(slug) : String(slug).replace(/["\\]/g, '\\$&');
  }

  function citiesMap() {
    return window.Poisker?.readJsonScript?.('listing-cities', {}) || {};
  }

  function cityFromPath() {
    const parts = window.location.pathname.split('/').filter(Boolean);
    if (!parts.length) return '';
    const cities = citiesMap();
    return cities[parts[0]] ? parts[0] : '';
  }

  function categoryFromPath() {
    const parts = window.location.pathname.split('/').filter(Boolean);
    if (!parts.length) return '';
    const last = parts[parts.length - 1];
    if (document.querySelector(`.category-chip[data-category="${cssEsc(last)}"]`)) {
      return last;
    }
    return '';
  }

  function listingPath(city, category) {
    const P = window.Poisker;
    if (city && !P?.isSafeSlug?.(city)) return '/';
    if (category && !P?.isSafeSlug?.(category)) category = '';
    if (city && category) return `/${city}/${category}/`;
    if (city) return `/${city}/`;
    if (category) return `/${category}/`;
    return '/';
  }

  function clearPreferredCityCookie() {
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `poisker_city=; Max-Age=0; Path=/; SameSite=Lax${secure}`;
    document.cookie = `poisker_settlement_id=; Max-Age=0; Path=/; SameSite=Lax${secure}`;
    document.cookie = `poisker_region_id=; Max-Age=0; Path=/; SameSite=Lax${secure}`;
    document.cookie = `poisker_geo_scope=; Max-Age=0; Path=/; SameSite=Lax${secure}`;
  }

  function listingPathFromGeo({ regionSlug, settlementSlug, category }) {
    const P = window.Poisker;
    if (regionSlug && !P?.isSafeSlug?.(regionSlug)) regionSlug = '';
    if (settlementSlug && !P?.isSafeSlug?.(settlementSlug)) settlementSlug = '';
    if (category && !P?.isSafeSlug?.(category)) category = '';
    if (regionSlug && settlementSlug && category) {
      return `/${regionSlug}/${settlementSlug}/${category}/`;
    }
    if (regionSlug && settlementSlug) return `/${regionSlug}/${settlementSlug}/`;
    if (regionSlug && category) return `/${regionSlug}/${category}/`;
    if (regionSlug) return `/${regionSlug}/`;
    if (settlementSlug && category) return `/${settlementSlug}/${category}/`;
    if (settlementSlug) return `/${settlementSlug}/`;
    if (category) return `/${category}/`;
    return '/';
  }

  function navigateToGeo({ regionSlug, settlementSlug, russia, category }) {
    const params = new URLSearchParams(window.location.search);
    params.delete('city');
    params.delete('category');
    params.delete('settlement');
    params.delete('region');
    params.delete('geo');
    const cat = category || categoryField?.value || '';
    if (russia) {
      clearPreferredCityCookie();
      params.set('all', '1');
      const path = cat ? `/${cat}/` : '/';
      const qs = params.toString();
      window.location.assign(qs ? `${path}?${qs}` : path);
      return;
    }
    params.delete('all');
    const path = listingPathFromGeo({
      regionSlug,
      settlementSlug,
      category: cat,
    });
    const qs = params.toString();
    window.location.assign(qs ? `${path}?${qs}` : path);
  }

  function initHomeCityPicker() {
    const wrap = document.getElementById('home-city-wrap');
    const toggle = document.getElementById('home-city-toggle');
    const panel = document.getElementById('home-city-panel');
    const input = document.getElementById('home-city-input');
    const hidden = document.getElementById('home-city-slug');
    const settlementIdInput = document.getElementById('home-settlement-id');
    const list = document.getElementById('home-city-suggestions');
    const clearBtn = document.getElementById('home-city-clear');
    const label = document.getElementById('home-city-label');
    const regionPick = document.getElementById('home-region-pick');
    const russiaPick = document.getElementById('home-russia-pick');
    const headerGeo = document.getElementById('header-geo-btn');
    if (!wrap || !toggle || !panel || !input || !hidden || !list || !window.initCityAutocomplete) {
      return;
    }

    function setOpen(open) {
      panel.hidden = !open;
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) {
        window.requestAnimationFrame(() => {
          input.focus();
          input.select?.();
        });
      }
    }

    window.initCityAutocomplete(input, settlementIdInput || hidden, list, {}, {
      valueMode: 'id',
      onSelect(_id, _label, item) {
        navigateToGeo({
          regionSlug: item?.regionSlug || item?.region?.slug || '',
          settlementSlug: item?.slug || hidden.value,
        });
      },
    });

    toggle.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      setOpen(panel.hidden);
    });

    headerGeo?.addEventListener('click', (event) => {
      event.preventDefault();
      setOpen(true);
      panel.scrollIntoView?.({ block: 'nearest' });
    });

    function goRussia() {
      hidden.value = '';
      if (settlementIdInput) settlementIdInput.value = '';
      input.value = '';
      if (label) label.textContent = 'Вся Россия';
      toggle.classList.remove('is-active');
      navigateToGeo({ russia: true });
    }

    clearBtn?.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      goRussia();
    });
    russiaPick?.addEventListener('click', (event) => {
      event.preventDefault();
      goRussia();
    });
    regionPick?.addEventListener('click', (event) => {
      event.preventDefault();
      const regionSlug = regionPick.dataset.regionSlug || '';
      if (regionSlug) navigateToGeo({ regionSlug });
    });

    document.querySelectorAll('.home-popular-city').forEach((btn) => {
      btn.addEventListener('click', (event) => {
        event.preventDefault();
        navigateToGeo({
          regionSlug: btn.dataset.regionSlug || '',
          settlementSlug: btn.dataset.settlementSlug || '',
        });
      });
    });

    document.addEventListener('click', (event) => {
      if (!panel.hidden && !wrap.contains(event.target) && event.target !== headerGeo) {
        setOpen(false);
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !panel.hidden) {
        setOpen(false);
        toggle.focus();
      }
    });

    clearBtn && (clearBtn.hidden = !hidden.value && !settlementIdInput?.value);
  }

  initHomeCityPicker();

  function syncListingFormPath() {
    form.action = window.location.pathname;
    form.setAttribute('hx-get', window.location.pathname);
  }

  function setActiveCategoryChip(cat) {
    document.querySelectorAll('.category-chip').forEach((chip) => {
      const active = (chip.dataset.category || '') === cat;
      chip.classList.toggle('is-active', active);
      if (active) {
        chip.setAttribute('aria-current', 'page');
      } else {
        chip.removeAttribute('aria-current');
      }
    });
  }

  function syncControlsFromUrl() {
    if (window.refreshIcons) refreshIcons();
    syncListingFormPath();
    const params = new URLSearchParams(window.location.search);
    const cat = params.get('category') || categoryFromPath() || '';
    setActiveCategoryChip(cat);

    const rawSort = params.get('sort') || '';
    const sortSelect = document.getElementById('sort-select');
    const uiSort = sortSelect && [...sortSelect.options].some((o) => o.value === rawSort)
      ? rawSort
      : '';
    if (sortSelect) sortSelect.value = uiSort;
    if (sortField) sortField.value = uiSort;
    if (categoryField) categoryField.value = cat;

    carouselApi?.scrollChipIntoView(
      document.querySelector('.category-chip.is-active'),
      'auto'
    );
    carouselApi?.updateCarouselState();
  }

  document.body.addEventListener('change', (event) => {
    if (event.target?.id === 'sort-select') {
      sortField.value = event.target.value;
      submitFeed();
    }
  });

  document.body.addEventListener('click', (event) => {
    const chip = event.target.closest('.category-chip[data-category]');
    if (!chip || chip.classList.contains('is-active')) return;
    setActiveCategoryChip(chip.dataset.category || '');
    carouselApi?.scrollChipIntoView(chip, 'auto');
  });

  document.body.addEventListener('htmx:afterSettle', syncControlsFromUrl);
})();
