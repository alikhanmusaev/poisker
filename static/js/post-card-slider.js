(function () {
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

  function initSlider(root) {
    if (!root || root.dataset.sliderInit === '1') return;
    root.dataset.sliderInit = '1';

    const track = root.querySelector('[data-post-card-track]');
    const slides = Array.from(root.querySelectorAll('[data-post-card-slide]'));
    const dots = Array.from(root.querySelectorAll('[data-post-card-dot]'));
    if (!track || slides.length < 2) return;

    let index = 0;
    let suppressClick = false;
    let raf = 0;
    let drag = null;

    function setActive(next) {
      index = next;
      for (let i = 0; i < dots.length; i += 1) {
        dots[i].classList.toggle('is-active', i === index);
      }
      hydrateSlide(slides[index]);
      hydrateSlide(slides[index + 1]);
      hydrateSlide(slides[index - 1]);
    }

    function goTo(next, behavior) {
      const clamped = Math.max(0, Math.min(slides.length - 1, next));
      const slide = slides[clamped];
      if (!slide) return;
      hydrateSlide(slide);
      hydrateSlide(slides[clamped + 1]);
      hydrateSlide(slides[clamped - 1]);
      const left = slide.offsetLeft;
      if (behavior === 'auto' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        track.scrollLeft = left;
      } else {
        track.scrollTo({ left, behavior: 'smooth' });
      }
      setActive(clamped);
    }

    track.addEventListener(
      'scroll',
      () => {
        suppressClick = true;
        if (raf) return;
        raf = requestAnimationFrame(() => {
          raf = 0;
          setActive(nearestIndex(track, slides));
          window.clearTimeout(track._clickTimer);
          track._clickTimer = window.setTimeout(() => {
            suppressClick = false;
          }, 80);
        });
      },
      { passive: true }
    );

    // Desktop: drag to change photo without fighting native touch scroll.
    track.addEventListener('pointerdown', (event) => {
      if (event.pointerType !== 'mouse' || event.button !== 0) return;
      drag = {
        id: event.pointerId,
        x: event.clientX,
        scroll: track.scrollLeft,
        moved: false,
      };
    });

    track.addEventListener('pointermove', (event) => {
      if (!drag || drag.id !== event.pointerId) return;
      const dx = event.clientX - drag.x;
      if (!drag.moved && Math.abs(dx) < 4) return;
      drag.moved = true;
      suppressClick = true;
      track.scrollLeft = drag.scroll - dx;
    });

    function endMouseDrag(event) {
      if (!drag || drag.id !== event.pointerId) return;
      const moved = drag.moved;
      const dx = event.clientX - drag.x;
      drag = null;
      if (!moved) return;
      const next =
        Math.abs(dx) > 36
          ? dx < 0
            ? Math.min(slides.length - 1, index + 1)
            : Math.max(0, index - 1)
          : nearestIndex(track, slides);
      goTo(next);
      window.setTimeout(() => {
        suppressClick = false;
      }, 100);
    }

    track.addEventListener('pointerup', endMouseDrag);
    track.addEventListener('pointercancel', endMouseDrag);

    slides.forEach((slide) => {
      slide.addEventListener(
        'click',
        (event) => {
          if (!suppressClick) return;
          event.preventDefault();
          event.stopPropagation();
        },
        true
      );
    });

    setActive(0);
  }

  function initAll() {
    document.querySelectorAll('[data-post-card-slider]').forEach((root) => initSlider(root));
  }

  document.addEventListener('DOMContentLoaded', initAll);
  document.body.addEventListener('htmx:afterSettle', initAll);
})();
