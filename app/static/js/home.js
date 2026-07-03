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

    function scrollChipIntoView(chip, behavior = 'smooth') {
      if (!chip) return;
      const chipLeft = chip.offsetLeft;
      const chipRight = chipLeft + chip.offsetWidth;
      const viewLeft = carousel.scrollLeft;
      const viewRight = viewLeft + carousel.clientWidth;
      const padding = 12;

      if (chipLeft < viewLeft + padding) {
        carousel.scrollTo({ left: Math.max(chipLeft - padding, 0), behavior });
      } else if (chipRight > viewRight - padding) {
        carousel.scrollTo({
          left: chipRight - carousel.clientWidth + padding,
          behavior,
        });
      }
      window.requestAnimationFrame(updateCarouselState);
    }

    prevBtn?.addEventListener('click', () => {
      carousel.scrollBy({ left: -scrollStep(), behavior: 'smooth' });
    });

    nextBtn?.addEventListener('click', () => {
      carousel.scrollBy({ left: scrollStep(), behavior: 'smooth' });
    });

    carousel.addEventListener('scroll', updateCarouselState, { passive: true });

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
        scrollChipIntoView(activeChip(), 'auto');
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
  initMobileHomeToolbar();

  function initMobileHomeToolbar() {
    const toolbar = document.getElementById('home-mobile-toolbar');
    const spacer = document.getElementById('home-mobile-toolbar-spacer');
    if (!toolbar || !spacer) return;

    const mq = window.matchMedia('(max-width: 767px)');
    let stickThreshold = 0;

    function resetToolbar() {
      toolbar.classList.remove('is-compact');
      spacer.hidden = true;
      spacer.style.height = '0';
    }

    function measure() {
      if (!mq.matches) {
        resetToolbar();
        return;
      }
      resetToolbar();
      stickThreshold = toolbar.getBoundingClientRect().top + window.scrollY;
    }

    function updateToolbar() {
      if (!mq.matches) return;
      const stuck = window.scrollY >= stickThreshold;
      toolbar.classList.toggle('is-compact', stuck);
      if (stuck) {
        spacer.hidden = false;
        spacer.style.height = `${toolbar.offsetHeight}px`;
      } else {
        spacer.hidden = true;
        spacer.style.height = '0';
      }
    }

    measure();
    updateToolbar();

    window.addEventListener('scroll', updateToolbar, { passive: true });
    window.addEventListener('resize', () => {
      measure();
      updateToolbar();
    });
    mq.addEventListener('change', () => {
      measure();
      updateToolbar();
    });

    if (typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(() => {
        if (toolbar.classList.contains('is-compact')) {
          spacer.style.height = `${toolbar.offsetHeight}px`;
        }
      }).observe(toolbar);
    }
  }

  function categoryFromPath() {
    const parts = window.location.pathname.split('/').filter(Boolean);
    if (!parts.length) return '';
    if (parts[0] === 'kategoriya') return parts[1] || '';
    if (parts[0] === 'gorod') return parts[2] || '';
    if (parts.length >= 2) return parts[1];
    const slug = parts[0];
    const catChip = document.querySelector(`.category-chip[data-category="${slug}"]`);
    return catChip ? slug : '';
  }

  function syncControlsFromUrl() {
    if (window.refreshIcons) refreshIcons();
    const params = new URLSearchParams(window.location.search);
    const cat = params.get('category') || categoryFromPath() || '';
    document.querySelectorAll('.category-chip').forEach((chip) => {
      const active = (chip.dataset.category || '') === cat;
      chip.classList.toggle('is-active', active);
      if (active) {
        chip.setAttribute('aria-current', 'page');
      } else {
        chip.removeAttribute('aria-current');
      }
    });

    const sort = params.get('sort') || (params.get('q') ? 'relevance' : 'rank');
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) sortSelect.value = sort;
    if (sortField) sortField.value = sort;
    if (categoryField) categoryField.value = cat;

    carouselApi?.scrollChipIntoView(
      document.querySelector('.category-chip.is-active'),
      'smooth'
    );
    carouselApi?.updateCarouselState();
  }

  document.body.addEventListener('change', (event) => {
    if (event.target?.id === 'sort-select') {
      sortField.value = event.target.value;
      submitFeed();
    }
  });

  document.body.addEventListener('htmx:afterSettle', syncControlsFromUrl);
})();
