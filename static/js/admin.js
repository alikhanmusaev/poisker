(function () {
  const sidebar = document.getElementById('admin-sidebar');
  const toggle = document.getElementById('admin-menu-toggle');
  const mobileMenuBtn = document.getElementById('admin-mobile-menu-btn');
  const overlay = document.getElementById('admin-overlay');

  function setExpanded(expanded) {
    toggle?.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    mobileMenuBtn?.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }

  function closeMenu() {
    sidebar?.classList.remove('is-open');
    setExpanded(false);
    if (overlay) overlay.hidden = true;
  }

  function openMenu() {
    sidebar?.classList.add('is-open');
    setExpanded(true);
    if (overlay) overlay.hidden = false;
  }

  function toggleMenu() {
    if (sidebar?.classList.contains('is-open')) closeMenu();
    else openMenu();
  }

  toggle?.addEventListener('click', toggleMenu);
  mobileMenuBtn?.addEventListener('click', toggleMenu);
  overlay?.addEventListener('click', closeMenu);
  sidebar?.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', closeMenu);
  });

  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.getAttribute('data-confirm');
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll('form[data-prompt-reason]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const label = form.getAttribute('data-prompt-reason') || 'Причина';
      const reason = window.prompt(label);
      if (reason === null) {
        event.preventDefault();
        return;
      }
      const trimmed = reason.trim();
      if (!trimmed) {
        event.preventDefault();
        window.alert('Укажите причину для продавца.');
        return;
      }
      let input = form.querySelector('input[name="reason"]');
      if (!input) {
        input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'reason';
        form.appendChild(input);
      }
      input.value = trimmed.slice(0, 400);
    });
  });

  document.querySelectorAll('[data-reason-chip][data-reason-target]').forEach((chip) => {
    chip.addEventListener('click', () => {
      const target = document.querySelector(chip.getAttribute('data-reason-target'));
      const value = chip.getAttribute('data-reason-chip') || '';
      if (!target) return;
      target.value = value;
      target.focus();
      chip.closest('.admin-reason-chips')
        ?.querySelectorAll('[data-reason-chip]')
        .forEach((el) => el.classList.toggle('is-active', el === chip));
    });
  });
})();
