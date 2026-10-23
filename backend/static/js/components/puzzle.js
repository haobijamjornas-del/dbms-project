export function initPuzzle(form) {
  const timer = document.querySelector('[data-timer]');
  const limit = Number(timer?.dataset.limit || 0);
  const secondsLeft = Number(timer?.dataset.seconds || limit);
  const alreadyUsed = Math.max(0, (limit - secondsLeft) * 1000);
  const startedAt = performance.now();
  const msField = form.querySelector('input[name="response_ms"]');
  const text = timer?.querySelector('.timer-text');
  const fill = timer?.querySelector('.timer-fill');
  const buttons = [...form.querySelectorAll('button.opt')];
  let sending = false;
  let frame = null;

  form.classList.add('is-live');

  const elapsed = () => Math.round(alreadyUsed + performance.now() - startedAt);

  function send(submitter) {
    if (sending) return;
    sending = true;
    cancelAnimationFrame(frame);
    msField.value = String(Math.min(elapsed(), limit * 1000));
    form.classList.add('is-sending');
    if (submitter && typeof form.requestSubmit === 'function') {
      form.requestSubmit(submitter);
    } else {
      form.submit();
    }
  }

  form.addEventListener('submit', (event) => {
    if (form.dataset.sent) {
      event.preventDefault();
      return;
    }
    form.dataset.sent = '1';
    sending = true;
    cancelAnimationFrame(frame);
    msField.value = String(Math.min(elapsed(), limit * 1000));
    form.classList.add('is-sending');
  });

  function tick() {
    const remaining = Math.max(0, limit * 1000 - elapsed());
    if (text) text.textContent = `${Math.ceil(remaining / 1000)}s`;
    if (fill) fill.style.width = `${(remaining / (limit * 1000)) * 100}%`;
    if (timer) timer.classList.toggle('is-low', remaining <= Math.max(3000, limit * 250));
    if (remaining <= 0) {
      if (text) text.textContent = "Time's up";
      send(null);
      return;
    }
    frame = requestAnimationFrame(tick);
  }

  if (limit > 0) frame = requestAnimationFrame(tick);

  document.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey || sending) return;
    const index = Number(event.key) - 1;
    if (Number.isInteger(index) && index >= 0 && index < buttons.length) {
      event.preventDefault();
      buttons[index].focus();
      send(buttons[index]);
    }
  });
}
