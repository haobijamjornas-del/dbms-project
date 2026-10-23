import { api, ApiError } from '../api.js';
import { $, debounce, esc } from '../dom.js';

const MIN_CHARS = 12;

const COPY = {
  Low: {
    tone: 'low',
    headline: 'Sounds steady',
    blurb: 'Nothing in this reads as distress. Keep doing what is working.',
  },
  Medium: {
    tone: 'moderate',
    headline: 'Some strain showing',
    blurb: 'There are early warning signs here. Worth keeping an eye on, and worth talking about.',
  },
  High: {
    tone: 'high',
    headline: 'This sounds heavy',
    blurb: 'Strong distress signals. Please consider speaking to a counsellor — you do not have to sit with this alone.',
  },
};

export function initLiveCheck(root) {
  const textarea = $('[data-role="entry-text"]', root);
  const panel = $('[data-role="live-result"]', root);
  const counter = $('[data-role="char-count"]', root);
  const submit = $('[data-role="submit"]', root);
  if (!textarea || !panel) return;

  let inFlight = null;

  function setHint(message) {
    panel.className = 'live-result is-idle';
    panel.innerHTML = `<div class="live-hint">${esc(message)}</div>`;
  }

  function setBusy() {
    panel.classList.add('is-checking');
  }

  function render(result) {
    const copy = COPY[result.level_name] || COPY.Medium;
    const pct = Math.round(result.confidence * 100);
    const bars = result.probabilities.map((p, i) => {
      const name = ['Low', 'Medium', 'High'][i];
      const tone = ['low', 'moderate', 'high'][i];
      const width = Math.round(p * 100);
      return `<div class="live-bar-row">
        <span class="live-bar-label">${name}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${width}%;
              background:var(--${tone})"></span></span>
        <span class="live-bar-val">${width}%</span>
      </div>`;
    }).join('');

    panel.className = `live-result is-${copy.tone}`;
    panel.innerHTML = `
      <div class="live-head">
        <span class="live-level">${esc(result.level_name)}</span>
        <div class="live-copy">
          <b>${esc(copy.headline)}</b>
          <span>${esc(copy.blurb)}</span>
        </div>
      </div>
      ${result.crisis_flagged ? `
        <div class="live-crisis">
          <b>Please reach out now.</b> Tele-MANAS <b>14416</b> is free and answers
          24×7. A counsellor will also be notified when you save this.
        </div>` : ''}
      <div class="live-bars">${bars}</div>
      <div class="live-foot">
        <span>Model confidence <b>${pct}%</b></span>
        ${result.theme_code ? `<span>Looks related to
          <b>${esc(result.theme_code.replace(/_/g, ' '))}</b></span>` : ''}
      </div>
      <div class="live-note">This is a preview. Save it to see coping techniques, advice and helplines for your level.</div>`;
  }

  async function check() {
    const text = textarea.value.trim();
    if (text.length < MIN_CHARS) {
      setHint(`Write a little more and the stress level will appear here — ${
        MIN_CHARS - text.length} more character${
        MIN_CHARS - text.length === 1 ? '' : 's'}.`);
      return;
    }
    setBusy();
    const token = Symbol('check');
    inFlight = token;
    try {
      const result = await api.post('/assessments/analyse', { entry_text: text });
      if (inFlight !== token) return;
      render(result.data);
    } catch (err) {
      if (inFlight !== token) return;
      setHint(err instanceof ApiError && err.status === 401
        ? 'Your session expired — please sign in again.'
        : 'Could not check that just now. You can still save it.');
    } finally {
      if (inFlight === token) panel.classList.remove('is-checking');
    }
  }

  const debouncedCheck = debounce(check, 550);

  textarea.addEventListener('input', () => {
    const n = textarea.value.trim().length;
    if (counter) counter.textContent = `${n} character${n === 1 ? '' : 's'}`;
    if (submit) submit.disabled = n < 10;
    debouncedCheck();
  });

  textarea.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      const form = textarea.closest('form');
      if (form) form.requestSubmit();
    }
  });

  root.classList.add('js-enhanced');
  setHint('Write a sentence or two, and your stress level will appear here as you type.');
  if (submit) submit.disabled = textarea.value.trim().length < 10;
  if (textarea.value.trim().length >= MIN_CHARS) check();
}
