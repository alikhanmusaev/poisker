(function () {
  const form = document.getElementById('home-search-form');
  const categoryField = document.getElementById('category-field');
  const cityField = document.getElementById('city-field');
  const sortField = document.getElementById('sort-field');
  const photoField = document.getElementById('with-photo-field');
  const priceField = document.getElementById('with-price-field');

  if (!form) return;

  function submitFeed() {
    if (window.htmx) htmx.trigger(form, 'submit');
  }

  function syncControlsFromUrl() {
    if (window.refreshIcons) refreshIcons();
    const params = new URLSearchParams(window.location.search);
    const cat = params.get('category') || '';
    document.querySelectorAll('.category-chip').forEach((chip) => {
      const active = (chip.dataset.category || '') === cat;
      chip.classList.toggle('is-active', active);
      chip.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    const sort = params.get('sort') || (params.get('q') ? 'relevance' : 'rank');
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) sortSelect.value = sort;
    if (sortField) sortField.value = sort;
    if (categoryField) categoryField.value = cat;

    const city = params.get('city') || '';
    const citySelect = document.getElementById('city-select');
    if (citySelect) citySelect.value = city;
    if (cityField) cityField.value = city;

    const photo = params.get('with_photo') === '1';
    const price = params.get('with_price') === '1';
    if (photoField) photoField.value = photo ? '1' : '';
    if (priceField) priceField.value = price ? '1' : '';
    document.querySelectorAll('.feed-filter-toggle').forEach((btn) => {
      const active = btn.dataset.filter === 'with_photo' ? photo : price;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }

  document.querySelectorAll('.category-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      categoryField.value = chip.dataset.category || '';
      document.querySelectorAll('.category-chip').forEach((item) => {
        const active = item === chip;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      submitFeed();
    });
  });

  document.querySelectorAll('.feed-filter-toggle').forEach((btn) => {
    btn.addEventListener('click', () => {
      const field = btn.dataset.filter === 'with_photo' ? photoField : priceField;
      const active = !btn.classList.contains('is-active');
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      if (field) field.value = active ? '1' : '';
      submitFeed();
    });
  });

  document.body.addEventListener('change', (event) => {
    if (event.target?.id === 'sort-select') {
      sortField.value = event.target.value;
      submitFeed();
      return;
    }
    if (event.target?.id === 'city-select') {
      if (cityField) cityField.value = event.target.value;
      submitFeed();
    }
  });

  document.body.addEventListener('htmx:afterSettle', syncControlsFromUrl);
})();
