(function () {
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 3;
  const ZOOM_STEP = 0.5;
  const REDUCE = window.matchMedia('(prefers-reduced-motion: reduce)');

  function hydrateSlide(slide) {
    if (!slide) return;
    slide.querySelectorAll('source[data-srcset]').forEach((source) => {
      source.setAttribute('srcset', source.dataset.srcset);
      delete source.dataset.srcset;
    });
    slide.querySelectorAll('img[data-src]').forEach((img) => {
      if (img.dataset.srcset) {
        img.setAttribute('srcset', img.dataset.srcset);
        delete img.dataset.srcset;
      }
      if (img.dataset.sizes) {
        img.setAttribute('sizes', img.dataset.sizes);
        delete img.dataset.sizes;
      }
      img.setAttribute('src', img.dataset.src);
      delete img.dataset.src;
    });
  }

  function slideUrl(slide) {
    const img = slide.querySelector('img');
    if (!img) return '';
    return img.getAttribute('data-full-src') || img.currentSrc || img.src || img.getAttribute('data-src') || '';
  }

  function nearestIndex(track, slides) {
    const left = track.scrollLeft;
    let best = 0;
    let bestDist = Infinity;
    for (let i = 0; i < slides.length; i += 1) {
      const dist = Math.abs(slides[i].offsetLeft - left);
      if (dist < bestDist) {
        bestDist = dist;
        best = i;
      }
    }
    return best;
  }

  function initGallery(root) {
    const track = root.querySelector('[data-gallery-track]');
    const viewport = root.querySelector('[data-gallery-viewport]');
    const slides = [...root.querySelectorAll('[data-gallery-slide]')];
    if (!track || !slides.length) return null;

    const prevBtn = root.querySelector('[data-gallery-prev]');
    const nextBtn = root.querySelector('[data-gallery-next]');
    const dots = [...root.querySelectorAll('[data-gallery-dot]')];
    const multi = slides.length > 1;

    let index = 0;
    let raf = 0;

    function setActive(next) {
      index = next;
      root.setAttribute('data-slide', String(index + 1));
      if (viewport) {
        viewport.setAttribute('aria-label', `${index + 1} / ${slides.length}`);
      }
      for (let i = 0; i < dots.length; i += 1) {
        dots[i].classList.toggle('is-active', i === index);
      }
      for (let i = 0; i < slides.length; i += 1) {
        slides[i].setAttribute('aria-hidden', i === index ? 'false' : 'true');
      }
      if (prevBtn) prevBtn.hidden = index === 0;
      if (nextBtn) nextBtn.hidden = index === slides.length - 1;
      hydrateSlide(slides[index]);
      hydrateSlide(slides[index + 1]);
      hydrateSlide(slides[index - 1]);
    }

    function goTo(nextIndex, behavior) {
      const clamped = Math.max(0, Math.min(slides.length - 1, nextIndex));
      const slide = slides[clamped];
      if (!slide) return;
      hydrateSlide(slide);
      hydrateSlide(slides[clamped + 1]);
      hydrateSlide(slides[clamped - 1]);
      const left = slide.offsetLeft;
      if (behavior === 'auto' || REDUCE.matches) {
        track.scrollLeft = left;
      } else {
        track.scrollTo({ left, behavior: behavior || 'smooth' });
      }
      setActive(clamped);
    }

    prevBtn?.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      goTo(index - 1);
    });
    nextBtn?.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      goTo(index + 1);
    });

    viewport?.addEventListener('keydown', (event) => {
      if (!multi) return;
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        goTo(index - 1);
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        goTo(index + 1);
      }
    });

    if (multi) {
      track.addEventListener(
        'scroll',
        () => {
          if (raf) return;
          raf = requestAnimationFrame(() => {
            raf = 0;
            setActive(nearestIndex(track, slides));
          });
        },
        { passive: true }
      );
    }

    slides.forEach((slide, i) => {
      slide.querySelector('[data-gallery-open]')?.addEventListener('click', () => {
        const urls = slides.map(slideUrl).filter(Boolean);
        openLightbox(urls, i, (next) => goTo(next, 'auto'));
      });
    });

    setActive(0);
    return { goTo, getIndex: () => index };
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
        setZoom(pinchStart.zoom * (distance / pinchStart.distance));
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

  window.PoiskerLightbox = { open: openLightbox };

  function boot() {
    lightboxApi = initLightbox();
    document.querySelectorAll('[data-post-gallery]').forEach((root) => initGallery(root));
    if (window.refreshIcons) window.refreshIcons();
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
