document.querySelectorAll('[data-toggle-password]').forEach((button) => {
  const input = document.getElementById(button.dataset.togglePassword);
  if (!input) return;
  button.hidden = false;
  button.addEventListener('click', () => {
    const reveal = input.type === 'password';
    input.type = reveal ? 'text' : 'password';
    button.textContent = reveal ? 'Hide' : 'Show';
    button.setAttribute('aria-pressed', String(reveal));
    button.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
  });
});

const password = document.getElementById('password');
const confirmPassword = document.getElementById('confirm_password');
const lengthHint = document.querySelector('[data-hint="length"]');
const matchHint = document.querySelector('[data-hint="match"]');

function refreshHints() {
  if (password && lengthHint) {
    const longEnough = password.value.length >= 6;
    lengthHint.classList.toggle('is-ok', longEnough);
    lengthHint.textContent = longEnough ? 'Good length' : 'At least 6 characters';
  }
  if (password && confirmPassword && matchHint) {
    if (!confirmPassword.value) {
      matchHint.textContent = '';
      matchHint.className = 'field-hint';
      confirmPassword.setCustomValidity('');
      return;
    }
    const same = password.value === confirmPassword.value;
    matchHint.textContent = same ? 'Passwords match' : 'Passwords do not match yet';
    matchHint.className = `field-hint ${same ? 'is-ok' : 'is-bad'}`;
    confirmPassword.setCustomValidity(same ? '' : 'Passwords do not match');
  }
}

[password, confirmPassword].forEach((field) => {
  if (field) field.addEventListener('input', refreshHints);
});
