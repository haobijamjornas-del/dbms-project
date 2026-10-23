import { DataTable } from './components/datatable.js';
import { initRowActions } from './components/rowactions.js';
import { initLiveCheck } from './components/livecheck.js';
import { initPuzzle } from './components/puzzle.js';
import { initRescue } from './components/rescue.js';
import { esc, truncate, levelBadge, $, STATUS_LABELS, ALERT_LABELS } from './dom.js';

function riskColour(value) {
  if (value >= 50) return 'var(--high)';
  if (value >= 25) return 'var(--moderate)';
  return 'var(--low)';
}

function severityMix(row) {
  const total = row.total_assessments || 0;
  if (!total) return '<span class="tiny faint">no entries</span>';
  const pct = (n) => (n / total) * 100;
  return `<div class="bar-track" title="Low ${row.low_count} · Medium ${row.moderate_count} · High ${row.high_count}">
    <div class="bar-fill" style="width:${pct(row.low_count)}%;background:var(--low)"></div>
    <div class="bar-fill" style="width:${pct(row.moderate_count)}%;background:var(--moderate)"></div>
    <div class="bar-fill" style="width:${pct(row.high_count)}%;background:var(--high)"></div>
  </div>`;
}

function studentRow(row) {
  return `<tr>
    <td>
      <a href="/students/${row.student_id}"><b>${esc(row.full_name)}</b></a>
      <div class="tiny faint mono">${esc(row.enrollment_no)}</div>
    </td>
    <td><span class="badge b-grey">${esc(row.dept_code)}</span></td>
    <td class="num">${esc(row.year_of_study)}</td>
    <td class="num">${esc(row.total_assessments)}</td>
    <td>${severityMix(row)}</td>
    <td class="num">${row.avg_stress_score ?? '—'}</td>
    <td>${levelBadge(row.latest_level)}</td>
    <td class="num"><b style="color:${riskColour(row.risk_index)}">${row.risk_index}</b></td>
    <td><a class="btn btn-sm" href="/students/${row.student_id}">Open</a></td>
  </tr>`;
}

const PRIORITY_BADGE = {
  CRITICAL: '<span class="badge b-critical">Critical</span>',
  HIGH: '<span class="badge b-high">High</span>',
  MEDIUM: '<span class="badge b-moderate">Medium</span>',
  LOW: '<span class="badge b-grey">Low</span>',
};

function relative(timestamp) {
  if (!timestamp) return '—';
  const then = new Date(String(timestamp).replace(' ', 'T'));
  if (Number.isNaN(then.getTime())) return esc(timestamp);
  const mins = Math.round((Date.now() - then.getTime()) / 60000);
  if (mins < 60) return `${Math.max(1, mins)}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? 'yesterday' : `${days} days ago`;
}

function alertRow(row, currentFilter) {
  const type = ALERT_LABELS[row.alert_type] || String(row.alert_type || '');
  return `<tr>
    <td>${PRIORITY_BADGE[row.priority] || esc(row.priority)}
      ${row.alert_type !== 'HIGH_STRESS'
        ? `<div class="tiny faint" style="margin-top:3px">${esc(type)}</div>` : ''}</td>
    <td>
      <a href="/students/${row.student_id}"><b>${esc(row.student_name)}</b></a>
      <div class="tiny faint">${esc(row.dept_code)} · ${esc(row.phone || 'no phone')}</div>
    </td>
    <td class="small" style="max-width:280px">
      <a href="/assessment/${row.assessment_id}" style="color:var(--text)">${truncate(row.entry_text, 85)}</a>
    </td>
    <td class="small">${esc(row.theme_name || '—')}</td>
    <td class="num small">${row.confidence_pct}%</td>
    <td class="small">${esc(row.assigned_counsellor || '—')}</td>
    <td class="small muted" style="white-space:nowrap">${relative(row.raised_at)}</td>
    <td data-role="status"><span class="badge b-${
      row.status === 'OPEN' ? 'blue' : row.status === 'ACKNOWLEDGED' ? 'moderate' : 'low'
    }">${esc(STATUS_LABELS[row.status] || row.status)}</span></td>
    <td>
      <form data-api="/alerts/${row.alert_id}" data-current-filter="${esc(currentFilter)}"
            data-message="Alert #${row.alert_id} set to {status}." style="display:flex;gap:5px">
        <select name="status" style="width:auto;padding:4px 7px;font-size:.78rem">
          <option value="">Set…</option>
          <option value="ACKNOWLEDGED">Acknowledge</option>
          <option value="RESOLVED">Resolve</option>
          <option value="DISMISSED">Dismiss</option>
          <option value="OPEN">Reopen</option>
        </select>
        <button class="btn btn-sm btn-primary" type="submit">Go</button>
      </form>
    </td>
  </tr>`;
}

function boot() {
  initRowActions(document);

  const liveCheck = $('#live-check');
  if (liveCheck) initLiveCheck(liveCheck);

  const puzzle = $('[data-puzzle]');
  if (puzzle) initPuzzle(puzzle);

  const rescue = $('[data-rescue]');
  if (rescue) initRescue(rescue);

  const studentsRoot = $('#students-table');
  if (studentsRoot) {
    const params = new URLSearchParams(window.location.search);
    new DataTable({
      root: studentsRoot,
      endpoint: '/students',
      columns: 9,
      renderRow: studentRow,
      defaultSort: params.get('sort') || 'risk',
      defaultDir: params.get('dir') || 'desc',
      emptyText: 'No students match these filters.',
      initialState: {
        q: params.get('q') || '',
        dept: params.get('dept') || '',
        year: params.get('year') || '',
        risk: params.get('risk') || '',
        page: Number(params.get('page') || 1),
        per_page: 15,
      },
    });
    studentsRoot.classList.add('js-enhanced');
  }

  const alertsRoot = $('#alerts-table');
  if (alertsRoot) {
    const params = new URLSearchParams(window.location.search);
    const status = params.get('status') || 'OPEN';
    new DataTable({
      root: alertsRoot,
      endpoint: '/alerts',
      columns: 9,
      renderRow: (row) => alertRow(row, status),
      emptyText: 'Nothing in this queue.',
      initialState: {
        status,
        priority: params.get('priority') || '',
        mine: params.get('mine') || '',
        page: Number(params.get('page') || 1),
        per_page: 100,
      },
    });
    alertsRoot.classList.add('js-enhanced');
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
