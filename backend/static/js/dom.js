export function esc(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function truncate(value, length = 80) {
  const text = String(value ?? '');
  if (text.length <= length) return esc(text);
  return esc(text.slice(0, text.lastIndexOf(' ', length) || length)) + '…';
}

export function $(selector, root = document) {
  return root.querySelector(selector);
}

export function $$(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

export function debounce(fn, wait = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

export function notify(message, kind = 'success', timeout = 4000) {
  let host = $('#js-notices');
  if (!host) {
    host = document.createElement('div');
    host.id = 'js-notices';
    const content = $('.content');
    if (!content) return;
    content.prepend(host);
  }
  const note = document.createElement('div');
  note.className = `flash flash-${kind} js-notice`;
  note.setAttribute('role', kind === 'danger' ? 'alert' : 'status');
  note.textContent = message;
  host.appendChild(note);
  if (timeout) {
    setTimeout(() => {
      note.style.opacity = '0';
      setTimeout(() => note.remove(), 250);
    }, timeout);
  }
}

export function syncUrl(params) {
  const url = new URL(window.location.href);
  url.search = '';
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v);
  });
  window.history.replaceState({}, '', url);
}

export function badge(text, kind = 'grey') {
  return `<span class="badge b-${esc(kind)}">${esc(text)}</span>`;
}

export function levelBadge(name) {
  if (!name) return '<span class="badge b-grey">—</span>';
  return badge(name, String(name).toLowerCase());
}

export const STATUS_LABELS = {
  OPEN: 'Open', ACKNOWLEDGED: 'Acknowledged', RESOLVED: 'Resolved', DISMISSED: 'Dismissed',
  SCHEDULED: 'Scheduled', COMPLETED: 'Completed', CANCELLED: 'Cancelled', NO_SHOW: 'No-show',
};

export const ALERT_LABELS = {
  HIGH_STRESS: 'High stress in an entry', REPEATED_HIGH: 'Repeated high stress',
  CRISIS_KEYWORD: 'Crisis language', CRITICAL_ITEM: 'Self-harm question flagged',
  SUSTAINED_DECLINE: 'Getting steadily worse',
};
