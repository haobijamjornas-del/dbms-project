import { getPage, ApiError } from '../api.js';
import { $, $$, debounce, notify, syncUrl } from '../dom.js';

export class DataTable {
  constructor(config) {
    this.cfg = config;
    this.root = config.root;
    this.tbody = $('tbody', this.root);
    this.state = {
      q: '', page: 1, sort: config.defaultSort || '', dir: config.defaultDir || 'desc',
      ...config.initialState,
    };
    this.inFlight = null;
    this.attach();
  }

  attach() {
    const search = $('[data-role="search"]', this.root);
    if (search) {
      search.addEventListener('input', debounce(() => {
        this.state.q = search.value.trim();
        this.state.page = 1;
        this.load();
      }, 280));
    }

    $$('[data-filter]', this.root).forEach((el) => {
      el.addEventListener('change', () => {
        this.state[el.dataset.filter] = el.value;
        this.state.page = 1;
        this.load();
      });
    });

    $$('[data-sort]', this.root).forEach((th) => {
      th.classList.add('sortable');
      th.setAttribute('tabindex', '0');
      th.setAttribute('role', 'button');
      const activate = () => {
        const key = th.dataset.sort;
        if (this.state.sort === key) {
          this.state.dir = this.state.dir === 'asc' ? 'desc' : 'asc';
        } else {
          this.state.sort = key;
          this.state.dir = 'desc';
        }
        this.state.page = 1;
        this.load();
      };
      th.addEventListener('click', activate);
      th.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); }
      });
    });

    this.root.addEventListener('click', (e) => {
      const pageBtn = e.target.closest('[data-page]');
      if (pageBtn) {
        e.preventDefault();
        this.state.page = Number(pageBtn.dataset.page);
        this.load();
        this.root.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });

    const reset = $('[data-role="reset"]', this.root);
    if (reset) {
      reset.addEventListener('click', (e) => {
        e.preventDefault();
        const search = $('[data-role="search"]', this.root);
        if (search) search.value = '';
        $$('[data-filter]', this.root).forEach((el) => {
          el.value = '';
          delete this.state[el.dataset.filter];
        });
        this.state.q = '';
        this.state.page = 1;
        this.load();
      });
    }

    this.markSortIndicators();
  }

  markSortIndicators() {
    $$('[data-sort]', this.root).forEach((th) => {
      th.classList.toggle('sorted', th.dataset.sort === this.state.sort);
      th.dataset.dir = th.dataset.sort === this.state.sort ? this.state.dir : '';
    });
  }

  setBusy(busy) {
    this.root.classList.toggle('is-loading', busy);
    if (this.tbody) this.tbody.setAttribute('aria-busy', busy ? 'true' : 'false');
  }

  async load() {
    this.setBusy(true);
    this.markSortIndicators();
    const token = Symbol('request');
    this.inFlight = token;

    try {
      const payload = await getPage(this.cfg.endpoint, this.state);
      if (this.inFlight !== token) return;
      this.render(payload.data, payload.meta);
      syncUrl(this.state);
    } catch (err) {
      if (this.inFlight !== token) return;
      const message = err instanceof ApiError ? err.message : 'Something went wrong.';
      notify(message, 'danger');
      if (err.status === 401) window.location.href = '/login';
    } finally {
      if (this.inFlight === token) this.setBusy(false);
    }
  }

  render(rows, meta) {
    if (!this.tbody) return;
    const cols = this.cfg.columns || 8;

    if (!rows.length) {
      this.tbody.innerHTML =
        `<tr><td colspan="${cols}" class="empty">${this.cfg.emptyText
          || 'Nothing matches these filters.'}</td></tr>`;
    } else {
      this.tbody.innerHTML = rows.map(this.cfg.renderRow).join('');
    }

    const count = $('[data-role="count"]', this.root);
    if (count && meta) {
      count.textContent = `${meta.total} record${meta.total === 1 ? '' : 's'}`;
    }
    this.renderPager(meta);
    if (this.cfg.onRender) this.cfg.onRender(rows, meta);
  }

  renderPager(meta) {
    const pager = $('[data-role="pager"]', this.root);
    if (!pager || !meta) return;
    if (meta.pages <= 1) { pager.innerHTML = ''; return; }

    const parts = [];
    if (meta.has_prev) parts.push(`<a href="#" data-page="${meta.page - 1}">← Prev</a>`);
    for (let p = 1; p <= meta.pages; p += 1) {
      if (p === meta.page) {
        parts.push(`<span class="cur">${p}</span>`);
      } else if (p <= 2 || p > meta.pages - 2 || Math.abs(p - meta.page) <= 1) {
        parts.push(`<a href="#" data-page="${p}">${p}</a>`);
      } else if (p === 3 || p === meta.pages - 2) {
        parts.push('<span class="faint">…</span>');
      }
    }
    if (meta.has_next) parts.push(`<a href="#" data-page="${meta.page + 1}">Next →</a>`);
    pager.innerHTML = parts.join('');
  }
}
