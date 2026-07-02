/**
 * Mobile photo slider for post cards (touch swipe).
 */
(function () {
  const SWIPE_THRESHOLD = 40;

  function setSlide(media, index) {
    const slides = media.querySelectorAll('.post-card-slide');
    const dots = media.querySelectorAll('.post-card-slider-dot');
    if (!slides.length) return;

    const total = slides.length;
    const next = ((index % total) + total) % total;

    slides.forEach((slide, i) => {
      const active = i === next;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', active ? 'false' : 'true');
    });
    dots.forEach((dot, i) => dot.classList.toggle('is-active', i === next));
    media.dataset.slideIndex = String(next);
  }

  function initCardSlider(media) {
    if (media.dataset.sliderInit === '1') return;
    media.dataset.sliderInit = '1';
    media.dataset.slideIndex = '0';
    setSlide(media, 0);

    let startX = 0;
    let startY = 0;
    let tracking = false;
    let swiped = false;

    media.addEventListener(
      'touchstart',
      (event) => {
        if (event.touches.length !== 1) return;
        startX = event.touches[0].clientX;
        startY = event.touches[0].clientY;
        tracking = true;
        swiped = false;
      },
      { passive: true }
    );

    media.addEventListener(
      'touchmove',
      (event) => {
        if (!tracking || event.touches.length !== 1) return;
        const dx = event.touches[0].clientX - startX;
        const dy = event.touches[0].clientY - startY;
        if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 10) {
          event.preventDefault();
        }
      },
      { passive: false }
    );

    media.addEventListener(
      'touchend',
      (event) => {
        if (!tracking) return;
        tracking = false;
        const touch = event.changedTouches[0];
        const dx = touch.clientX - startX;
        const dy = touch.clientY - startY;
        if (Math.abs(dx) < SWIPE_THRESHOLD || Math.abs(dx) < Math.abs(dy)) return;
        swiped = true;
        const current = parseInt(media.dataset.slideIndex || '0', 10);
        setSlide(media, dx < 0 ? current + 1 : current - 1);
      },
      { passive: true }
    );

    media.addEventListener(
      'click',
      (event) => {
        if (swiped) {
          event.preventDefault();
          event.stopPropagation();
          swiped = false;
        }
      },
      true
    );
  }

  function initCardSliders(scope) {
    (scope || document).querySelectorAll('[data-card-slider]').forEach(initCardSlider);
  }

  window.initCardSliders = initCardSliders;
  document.addEventListener('DOMContentLoaded', () => initCardSliders());
  document.body.addEventListener('htmx:afterSettle', () => initCardSliders());
})();
