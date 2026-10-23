export function initRescue(form) {
  const card = form.querySelector('[data-drag]');
  const places = [...form.querySelectorAll('[data-place]')];
  const timer = document.querySelector('[data-timer]');
  const limit = Number(timer?.dataset.limit || 0);
  const secondsLeft = Number(timer?.dataset.seconds || limit);
  const alreadyUsed = Math.max(0, (limit - secondsLeft) * 1000);
  const startedAt = performance.now();
  const msField = form.querySelector('input[name="response_ms"]');
  const text = timer?.querySelector('.timer-text');
  const fill = timer?.querySelector('.timer-fill');
  let sending = false;
  let frame = null;
  let ghost = null;
  let hover = null;
  let offset = { x: 0, y: 0 };

  form.classList.add('is-live');
  const elapsed = () => Math.round(alreadyUsed + performance.now() - startedAt);

  function stamp() {
    sending = true;
    cancelAnimationFrame(frame);
    msField.value = String(Math.min(elapsed(), limit * 1000));
    form.classList.add('is-sending');
  }

  function send(button) {
    if (sending) return;
    stamp();
    form.dataset.sent = '1';
    if (button && typeof form.requestSubmit === 'function') {
      form.requestSubmit(button);
      return;
    }
    if (button) {
      const hidden = document.createElement('input');
      hidden.type = 'hidden';
      hidden.name = button.name;
      hidden.value = button.value;
      form.appendChild(hidden);
    }
    form.submit();
  }

  form.addEventListener('submit', (event) => {
    if (form.dataset.sent === 'done') {
      event.preventDefault();
      return;
    }
    form.dataset.sent = 'done';
    if (!sending) stamp();
  });

  function placeAt(x, y) {
    const el = document.elementFromPoint(x, y);
    return el ? el.closest('[data-place]') : null;
  }

  function setHover(place) {
    if (hover === place) return;
    if (hover) hover.classList.remove('is-target');
    hover = place;
    if (hover) hover.classList.add('is-target');
  }

  function follow(event) {
    ghost.style.transform = `translate(${event.clientX - offset.x}px, ${event.clientY - offset.y}px) rotate(-3deg)`;
    setHover(placeAt(event.clientX, event.clientY));
  }

  function finish(target) {
    if (ghost) ghost.remove();
    ghost = null;
    card.classList.remove('is-lifted');
    setHover(null);
    if (target) {
      target.classList.add('is-dropped');
      send(target);
    } else {
      card.classList.remove('is-shaking');
      void card.offsetWidth;
      card.classList.add('is-shaking');
    }
  }

  if (card) {
    card.addEventListener('pointerdown', (event) => {
      if (sending || event.button > 0) return;
      event.preventDefault();
      const box = card.getBoundingClientRect();
      offset = { x: event.clientX - box.left, y: event.clientY - box.top };
      ghost = card.cloneNode(true);
      ghost.removeAttribute('data-drag');
      ghost.removeAttribute('tabindex');
      ghost.setAttribute('aria-hidden', 'true');
      ghost.classList.add('incident-ghost');
      ghost.style.width = `${box.width}px`;
      document.body.appendChild(ghost);
      card.classList.add('is-lifted');
      card.setPointerCapture(event.pointerId);
      follow(event);
    });
    card.addEventListener('pointermove', (event) => {
      if (ghost) follow(event);
    });
    card.addEventListener('pointerup', (event) => {
      if (ghost) finish(placeAt(event.clientX, event.clientY));
    });
    card.addEventListener('pointercancel', () => {
      if (ghost) finish(null);
    });
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        if (places[0]) places[0].focus();
      }
    });
  }

  function tick() {
    const remaining = Math.max(0, limit * 1000 - elapsed());
    if (text) text.textContent = `${Math.ceil(remaining / 1000)}s`;
    if (fill) fill.style.width = `${(remaining / (limit * 1000)) * 100}%`;
    if (timer) timer.classList.toggle('is-low', remaining <= Math.max(3000, limit * 250));
    if (remaining <= 0) {
      if (text) text.textContent = "Time's up";
      if (ghost) {
        ghost.remove();
        ghost = null;
      }
      send(null);
      return;
    }
    frame = requestAnimationFrame(tick);
  }

  if (limit > 0) frame = requestAnimationFrame(tick);

  document.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey || sending) return;
    const index = Number(event.key) - 1;
    if (Number.isInteger(index) && index >= 0 && index < places.length) {
      event.preventDefault();
      places[index].classList.add('is-dropped');
      send(places[index]);
    }
  });
}
