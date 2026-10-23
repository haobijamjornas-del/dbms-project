import { api, ApiError } from '../api.js';
import { $, notify, STATUS_LABELS } from '../dom.js';

const BADGE_KIND = {
  OPEN: 'blue', SCHEDULED: 'blue',
  ACKNOWLEDGED: 'moderate',
  RESOLVED: 'low', COMPLETED: 'low',
  DISMISSED: 'grey', CANCELLED: 'grey', NO_SHOW: 'grey',
};

function paintStatus(row, status) {
  const cell = $('[data-role="status"]', row);
  if (!cell) return null;
  const previous = cell.innerHTML;
  cell.innerHTML =
    `<span class="badge b-${BADGE_KIND[status] || 'grey'}">${STATUS_LABELS[status] || status}</span>`;
  return previous;
}

export function initRowActions(scope = document) {
  scope.addEventListener('submit', async (event) => {
    const form = event.target.closest('form[data-api]');
    if (!form) return;

    const row = form.closest('tr');
    const submitter = event.submitter;
    const status = (submitter && submitter.value) || (form.elements.status
      && form.elements.status.value);
    if (!status) return;

    event.preventDefault();
    form.classList.add('is-busy');
    const rollback = row ? paintStatus(row, status) : null;

    try {
      await api.patch(form.dataset.api, { status });
      notify(form.dataset.message
        ? form.dataset.message.replace('{status}', status)
        : `Updated to ${(STATUS_LABELS[status] || status).toLowerCase()}.`, 'success');

      const filter = form.dataset.currentFilter;
      if (row && filter && filter !== 'ALL' && filter !== status) {
        row.classList.add('is-leaving');
        setTimeout(() => {
          const tbody = row.parentElement;
          row.remove();
          if (tbody && !tbody.querySelector('tr')) {
            tbody.innerHTML =
              '<tr><td colspan="9" class="empty">Nothing left in this queue.</td></tr>';
          }
        }, 260);
      } else if (row) {
        row.classList.add('is-updated');
        setTimeout(() => row.classList.remove('is-updated'), 1200);
      }
    } catch (err) {
      if (row && rollback !== null) {
        const cell = $('[data-role="status"]', row);
        if (cell) cell.innerHTML = rollback;
      }
      notify(err instanceof ApiError ? err.message : 'Update failed.', 'danger');
      if (err.status === 401) window.location.href = '/login';
    } finally {
      form.classList.remove('is-busy');
    }
  });
}
