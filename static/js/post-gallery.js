(function () {
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 3;
  const ZOOM_STEP = 0.5;

  function initGallery(root) {
    const track = root.querySelector('[data-gallery-track]');
    const slides = [...root.querySelectorAll('[data-gallery-slide]')];
    if (!track || !slides.length) return null;

    const urls = slides
      .map((slide) => slide.querySelector('img')?.currentSrc || slide.querySelector('img')?.src)
      .filter(Boolean);

    const prevBtn = root.querySelector('[data-gallery-prev]');
    const nextBtn = root.querySelector('[data-gallery-next]');
    const dotsRoot = root.querySelector('[data-gallery-dots]');
    const counter = root.querySelector('[data-gallery-counter]');
    const dots = dotsRoot ? [...dotsRoot.querySelectorAll('button')] : [];

    let index = 0;
    let touchStartX = 0;
    let touchStartY = 0;

    function update() {
      track.style.transform = `translate3d(-${index * 100}%, 0, 0)`;
      if (counter) counter.textContent = `${index + 1} / ${slides.length}`;
      dots.forEach((dot, i) => {
        dot.classList.toggle('is-active', i === index);
        dot.setAttribute('aria-selected', i === index ? 'true' : 'false');
      });
      if (prevBtn) prevBtn.disabled = index === 0;
      if (nextBtn) nextBtn.disabled = index === slides.length - 1;
    }

    function goTo(nextIndex) {
      index = Math.max(0, Math.min(slides.length - 1, nextIndex));
      update();
    }

    prevBtn?.addEventListener('click', () => goTo(index - 1));
    nextBtn?.addEventListener('click', () => goTo(index + 1));
    dots.forEach((dot, i) => dot.addEventListener('click', () => goTo(i)));

    root.querySelector('[data-gallery-viewport]')?.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        goTo(index - 1);
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        goTo(index + 1);
      }
    });

    root.addEventListener(
      'touchstart',
      (event) => {
        if (event.touches.length !== 1) return;
        touchStartX = event.touches[0].clientX;
        touchStartY = event.touches[0].clientY;
      },
      { passive: true }
    );

    root.addEventListener(
      'touchend',
      (event) => {
        if (event.changedTouches.length !== 1 || slides.length < 2) return;
        const dx = event.changedTouches[0].clientX - touchStartX;
        const dy = event.changedTouches[0].clientY - touchStartY;
        if (Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy)) return;
        goTo(index + (dx < 0 ? 1 : -1));
      },
      { passive: true }
    );

    slides.forEach((slide, i) => {
      slide.querySelector('[data-gallery-open]')?.addEventListener('click', () => {
        openLightbox(urls, i, (next) => goTo(next));
      });
    });

    update();
    return { goTo, getIndex: () => index, urls };
  }

  function initLightbox() {
    const root = document.getElementById('post-lightbox');
    if (!root || root.dataset.lightboxInit === '1') return null;
    root.dataset.lightboxInit = '1';

    const img = root.querySelector('[data-lightbox-img]');
    const pan = root.querySelector('[data-lightbox-pan]');
    const counter = root.querySelector('[data-lightbox-counter]');
    const zoomLabel = root.querySelector('[data-lightbox-zoom-label]');
    const backdrop = root.querySelector('[data-lightbox-backdrop]');
    const lightboxPrev = root.querySelector('[data-lightbox-prev]');
    const lightboxNext = root.querySelector('[data-lightbox-next]');

    let urls = [];
    let index = 0;
    let zoom = 1;
    let panX = 0;
    let panY = 0;
    let onIndexChange = null;

    let dragStart = null;
    let pinchStart = null;

    function applyTransform() {
      if (!pan) return;
      pan.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
      if (zoomLabel) zoomLabel.textContent = `${Math.round(zoom * 100)}%`;
    }

    function resetZoom() {
      zoom = 1;
      panX = 0;
      panY = 0;
      applyTransform();
    }

    function setZoom(nextZoom) {
      zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, nextZoom));
      if (zoom === 1) {
        panX = 0;
        panY = 0;
      }
      applyTransform();
    }

    function render() {
      if (!img || !urls.length) return;
      img.src = urls[index];
      if (counter) counter.textContent = `${index + 1} / ${urls.length}`;
      const multi = urls.length > 1;
      if (lightboxPrev) lightboxPrev.hidden = !multi;
      if (lightboxNext) lightboxNext.hidden = !multi;
      resetZoom();
      onIndexChange?.(index);
    }

    function goTo(nextIndex) {
      index = Math.max(0, Math.min(urls.length - 1, nextIndex));
      render();
    }

    function close() {
      root.hidden = true;
      document.body.classList.remove('lightbox-open');
      resetZoom();
      onIndexChange = null;
    }

    function open(nextUrls, startIndex, onChange) {
      urls = nextUrls;
      index = startIndex;
      onIndexChange = onChange;
      root.hidden = false;
      document.body.classList.add('lightbox-open');
      render();
      root.querySelector('[data-lightbox-close]')?.focus();
      if (window.refreshIcons) window.refreshIcons();
    }

    root.querySelector('[data-lightbox-close]')?.addEventListener('click', close);
    backdrop?.addEventListener('click', close);
    root.querySelector('[data-lightbox-prev]')?.addEventListener('click', () => goTo(index - 1));
    root.querySelector('[data-lightbox-next]')?.addEventListener('click', () => goTo(index + 1));
    root.querySelector('[data-lightbox-zoom-in]')?.addEventListener('click', () => setZoom(zoom + ZOOM_STEP));
    root.querySelector('[data-lightbox-zoom-out]')?.addEventListener('click', () => setZoom(zoom - ZOOM_STEP));
    root.querySelector('[data-lightbox-zoom-reset]')?.addEventListener('click', resetZoom);

    img?.addEventListener('dblclick', () => {
      setZoom(zoom > 1 ? 1 : 2);
    });

    const stage = root.querySelector('[data-lightbox-stage]');
    stage?.addEventListener(
      'wheel',
      (event) => {
        event.preventDefault();
        setZoom(zoom + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP));
      },
      { passive: false }
    );

    stage?.addEventListener('pointerdown', (event) => {
      if (zoom <= 1) return;
      dragStart = { x: event.clientX - panX, y: event.clientY - panY };
      stage.setPointerCapture(event.pointerId);
    });

    stage?.addEventListener('pointermove', (event) => {
      if (!dragStart || zoom <= 1) return;
      panX = event.clientX - dragStart.x;
      panY = event.clientY - dragStart.y;
      applyTransform();
    });

    stage?.addEventListener('pointerup', () => {
      dragStart = null;
    });

    stage?.addEventListener(
      'touchstart',
      (event) => {
        if (event.touches.length === 2) {
          const [a, b] = event.touches;
          pinchStart = {
            distance: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY),
            zoom,
          };
        }
      },
      { passive: true }
    );

    stage?.addEventListener(
      'touchmove',
      (event) => {
        if (!pinchStart || event.touches.length !== 2) return;
        const [a, b] = event.touches;
        const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        const ratio = distance / pinchStart.distance;
        setZoom(pinchStart.zoom * ratio);
      },
      { passive: true }
    );

    stage?.addEventListener('touchend', () => {
      pinchStart = null;
    });

    document.addEventListener('keydown', (event) => {
      if (root.hidden) return;
      if (event.key === 'Escape') close();
      if (event.key === 'ArrowLeft') goTo(index - 1);
      if (event.key === 'ArrowRight') goTo(index + 1);
      if (event.key === '+' || event.key === '=') setZoom(zoom + ZOOM_STEP);
      if (event.key === '-') setZoom(zoom - ZOOM_STEP);
    });

    return { open, close };
  }

  let lightboxApi = null;

  function openLightbox(urls, index, onIndexChange) {
    if (!lightboxApi) lightboxApi = initLightbox();
    lightboxApi?.open(urls, index, onIndexChange);
  }

  function boot() {
    lightboxApi = initLightbox();
    document.querySelectorAll('[data-post-gallery]').forEach((root) => initGallery(root));
    if (window.refreshIcons) window.refreshIcons();
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
