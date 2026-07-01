function digitsOnly(value) {
  return (value || '').replace(/\D/g, '');
}

function formatRuPhoneInput(raw) {
  let digits = digitsOnly(raw);
  if (!digits.length) return '';
  if (digits[0] === '8') digits = '7' + digits.slice(1);
  if (digits[0] !== '7') digits = '7' + digits;
  digits = digits.slice(0, 11);

  let out = '+7';
  const rest = digits.slice(1);
  if (!rest.length) return out;

  out += ' (' + rest.slice(0, 3);
  if (rest.length < 3) return out;

  out += ')';
  if (rest.length <= 3) return out;

  out += ' ' + rest.slice(3, 6);
  if (rest.length <= 6) return out;

  out += '-' + rest.slice(6, 8);
  if (rest.length <= 8) return out;

  out += '-' + rest.slice(8, 10);
  return out;
}

function bindPhoneMask(input) {
  if (!input || input.dataset.phoneMask === '1') return;
  input.dataset.phoneMask = '1';
  input.setAttribute('inputmode', 'tel');
  input.setAttribute('autocomplete', 'tel');

  input.addEventListener('focus', () => {
    if (!input.value.trim()) input.value = '+7 ';
  });

  input.addEventListener('blur', () => {
    if (digitsOnly(input.value).length <= 1) input.value = '';
  });

  input.addEventListener('input', () => {
    const formatted = formatRuPhoneInput(input.value);
    input.value = formatted;
  });

  input.addEventListener('paste', (event) => {
    event.preventDefault();
    const text = (event.clipboardData || window.clipboardData).getData('text');
    input.value = formatRuPhoneInput(text);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[type="tel"], #phone').forEach(bindPhoneMask);
});

window.formatRuPhoneInput = formatRuPhoneInput;
window.bindPhoneMask = bindPhoneMask;
