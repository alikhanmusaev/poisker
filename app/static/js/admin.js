(function () {
  const sidebar = document.getElementById('admin-sidebar');
  const toggle = document.getElementById('admin-menu-toggle');
  const overlay = document.getElementById('admin-overlay');

  function closeMenu() {
    sidebar?.classList.remove('is-open');
    toggle?.setAttribute('aria-expanded', 'false');
    if (overlay) overlay.hidden = true;
  }

  function openMenu() {
    sidebar?.classList.add('is-open');
    toggle?.setAttribute('aria-expanded', 'true');
    if (overlay) overlay.hidden = false;
  }

  toggle?.addEventListener('click', () => {
    if (sidebar?.classList.contains('is-open')) closeMenu();
    else openMenu();
  });
  overlay?.addEventListener('click', closeMenu);

  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.getAttribute('data-confirm');
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
})();
