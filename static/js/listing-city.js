document.addEventListener('DOMContentLoaded', () => {
  const labelsNode = document.getElementById('listing-cities');
  let cities = {};
  if (labelsNode) {
    try {
      cities = JSON.parse(labelsNode.textContent) || {};
    } catch (e) {
      cities = {};
    }
  }

  const input = document.getElementById('city-input');
  const hidden = document.getElementById('settlement_id');
  const list =
    document.getElementById('city-suggestions') ||
    document.getElementById('city-suggestions-edit');

  if (window.initCityAutocomplete && input && hidden && list) {
    window.initCityAutocomplete(input, hidden, list, cities, { valueMode: 'id' });
  }

  const form = document.getElementById('create-post-form') || document.getElementById('edit-post-form');
  if (!form) return;

  let lastSubmitter = null;
  form.querySelectorAll('button[type="submit"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      lastSubmitter = btn;
    });
  });

  form.addEventListener('submit', (event) => {
    const submitter = event.submitter || lastSubmitter;
    const isDraft = submitter && submitter.name === 'action' && submitter.value === 'draft';
    if (isDraft) {
      input?.setCustomValidity('');
      form.querySelectorAll('input, textarea, select').forEach((field) => {
        field.setCustomValidity('');
      });
      return;
    }
    if (!hidden?.value) {
      event.preventDefault();
      input?.setCustomValidity('Выберите город из подсказок');
      input?.reportValidity();
      input?.focus();
      return;
    }
    input?.setCustomValidity('');
  });
});
