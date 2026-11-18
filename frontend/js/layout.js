/* Page shell (sidebar + top bar), toasts, confirm dialog and formatting helpers. */
const ICONS = {
    logo: '<path d="M16 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm-8 0a3 3 0 1 0-3-3 3 3 0 0 0 3 3Zm0 2c-2.7 0-6 1.3-6 3.5V19h6v-2.5c0-1 .4-2 1.2-2.8A8 8 0 0 0 8 13Zm8 0c-3 0-7 1.5-7 4v2h14v-2c0-2.5-4-4-7-4Z" fill="currentColor"/>',
    dashboard: '<path d="M3 3h8v10H3zM13 3h8v6h-8zM13 11h8v10h-8zM3 15h8v6H3z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
    employees: '<path d="M16 19v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 17.5V19M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm10 8v-1.5a3.5 3.5 0 0 0-2.5-3.35M15.5 4.15a3.5 3.5 0 0 1 0 6.7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
    departments: '<path d="M12 3v5m0 0H6a2 2 0 0 0-2 2v3m8-5h6a2 2 0 0 1 2 2v3M12 8v5M2 16h4v5H2zm8 0h4v5h-4zm8 0h4v5h-4z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
    attendance: '<path d="M4 6h16v14H4zM4 10h16M8 3v4m8-4v4m-7 9 2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    leaves: '<path d="M3 12h4l3-8 4 16 3-8h4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    settings: '<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    logout: '<path d="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    plus: '<path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    search: '<circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path d="m20 20-3.5-3.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    edit: '<path d="M4 20h4L19 9l-4-4L4 16v4Zm9-13 4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
    trash: '<path d="M4 7h16M10 11v6m4-6v6M6 7l1 13h10l1-13M9 7V4h6v3" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    check: '<path d="m5 12 5 5L20 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    x: '<path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
    present: '<path d="m16 11 2 2 4-4M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 9v-1a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v1" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
    absent: '<path d="m17 8 5 5m0-5-5 5M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 9v-1a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v1" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
    clock: '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 7v5l3 2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
    shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Zm-3 9 2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>',
};

function icon(name) {
    return `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ''}</svg>`;
}

function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function money(value, currency = 'PKR') {
    return `${currency} ${Number(value).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
}

function formatDate(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function todayIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function initials(name) {
    return name.split(/\s+/).filter(Boolean).map(p => p[0]).slice(0, 2).join('').toUpperCase();
}

function statusBadge(status) {
    const tone = { Active: 'b-green', Present: 'b-green', Approved: 'b-green', Inactive: 'b-red', Absent: 'b-red',
        Rejected: 'b-red', Late: 'b-amber', Pending: 'b-amber', 'Half Day': 'b-sky' }[status] || 'b-grey';
    return `<span class="badge dot ${tone}">${esc(status)}</span>`;
}

/* ------------------------------------------------------------ toasts */
function toast(message, type = 'success') {
    let box = document.querySelector('.toasts');
    if (!box) {
        box = document.createElement('div');
        box.className = 'toasts';
        document.body.appendChild(box);
    }
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.setAttribute('role', 'status');
    el.dataset.type = type;
    el.textContent = message;
    box.appendChild(el);
    setTimeout(() => el.remove(), 6000);
}

/* Show a toast on the next page (after a redirect). */
function flash(message, type = 'success') {
    sessionStorage.setItem('flash', JSON.stringify({ message, type }));
}

/* ------------------------------------------------------------ dialogs */
function confirmDialog(title, message, confirmLabel = 'Delete') {
    return new Promise(resolve => {
        const wrap = document.createElement('div');
        wrap.className = 'modal-backdrop';
        wrap.innerHTML = `<div class="modal" role="dialog" aria-modal="true" id="confirmDialog">
            <h3>${esc(title)}</h3><p>${esc(message)}</p>
            <div class="form-actions">
              <button class="btn btn-light" id="confirmCancel">Cancel</button>
              <button class="btn btn-danger" id="confirmOk">${esc(confirmLabel)}</button>
            </div></div>`;
        document.body.appendChild(wrap);
        const done = value => { wrap.remove(); resolve(value); };
        wrap.querySelector('#confirmOk').onclick = () => done(true);
        wrap.querySelector('#confirmCancel').onclick = () => done(false);
        wrap.addEventListener('click', e => { if (e.target === wrap) done(false); });
        wrap.querySelector('#confirmOk').focus();
    });
}

/* Dialog containing a form; onSubmit returns true to close. */
function formDialog(title, innerHtml, submitLabel, onSubmit) {
    const wrap = document.createElement('div');
    wrap.className = 'modal-backdrop';
    wrap.innerHTML = `<div class="modal" role="dialog" aria-modal="true" id="formDialog">
        <h3>${esc(title)}</h3>
        <form novalidate>${innerHtml}
          <div class="form-actions">
            <button type="button" class="btn btn-light" id="dialogCancel">Cancel</button>
            <button type="submit" class="btn btn-primary" id="dialogSubmit">${esc(submitLabel)}</button>
          </div></form></div>`;
    document.body.appendChild(wrap);
    const form = wrap.querySelector('form');
    wrap.querySelector('#dialogCancel').onclick = () => wrap.remove();
    form.addEventListener('submit', async e => {
        e.preventDefault();
        if (await onSubmit(form)) wrap.remove();
    });
    const first = form.querySelector('input, select, textarea');
    if (first) first.focus();
    return wrap;
}

/* ------------------------------------------------------------ field errors */
function clearErrors(form) {
    form.querySelectorAll('.field.invalid').forEach(f => f.classList.remove('invalid'));
    form.querySelectorAll('[data-error-for]').forEach(e => { e.textContent = ''; });
}

function showErrors(form, errors) {
    clearErrors(form);
    let first = null;
    for (const [field, message] of Object.entries(errors || {})) {
        const slot = form.querySelector(`[data-error-for="${field}"]`);
        if (slot) slot.textContent = message;
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            input.closest('.field')?.classList.add('invalid');
            if (!first) first = input;
        }
    }
    if (first) first.focus();
}

function formData(form) {
    const data = {};
    new FormData(form).forEach((value, key) => { data[key] = typeof value === 'string' ? value.trim() : value; });
    return data;
}

/* ------------------------------------------------------------ shell */
const NAV = [
    ['dashboard', '/dashboard', 'Dashboard'],
    ['employees', '/employees', 'Employees'],
    ['departments', '/departments', 'Departments'],
    ['attendance', '/attendance', 'Attendance'],
    ['leaves', '/leaves', 'Leave Management'],
    ['settings', '/settings', 'Settings & Rules'],
];

async function initPage() {
    const body = document.body;
    const active = body.dataset.page;
    const content = document.getElementById('content');

    let user;
    try {
        user = (await api('GET', '/api/me')).user;
    } catch (e) {
        return null;   // redirected to /login by api()
    }

    const shell = document.createElement('div');
    shell.className = 'shell';
    shell.innerHTML = `
      <aside class="sidebar" id="sidebar">
        <a class="brand" href="/dashboard"><span class="brand-logo">${icon('logo')}</span> HRMS</a>
        <div class="nav-label">Menu</div>
        <nav class="nav">${NAV.map(([key, href, label]) =>
            `<a href="${href}" id="nav-${key}" class="${key === active ? 'active' : ''}">${icon(key)}<span>${label}</span>
             ${key === 'leaves' ? '<span class="badge hidden" id="pendingBadge"></span>' : ''}</a>`).join('')}
        </nav>
        <div class="sidebar-footer"><button class="btn btn-ghost" id="logoutBtn">${icon('logout')} Logout</button></div>
      </aside>
      <div class="backdrop" id="backdrop"></div>
      <div class="main">
        <header class="topbar">
          <button class="btn btn-light btn-icon menu-btn" id="menuBtn" aria-label="Menu">${icon('menu')}</button>
          <div><h1 id="pageTitle">${esc(body.dataset.title)}</h1>
               <p class="subtitle">${esc(body.dataset.subtitle || '')}</p></div>
          <div class="user">
            <div class="user-name" style="text-align:right"><div style="font-weight:600" id="userName">${esc(user.name)}</div>
              <div class="muted small">${esc(user.email)}</div></div>
            <span class="avatar">${initials(user.name)}</span>
            <button class="btn btn-light btn-sm" id="topLogoutBtn">${icon('logout')} Logout</button>
          </div>
        </header>
      </div>`;
    shell.querySelector('.main').appendChild(content);
    content.classList.add('content');
    body.prepend(shell);
    content.hidden = false;

    const logout = async () => { await api('POST', '/api/logout'); window.location.href = '/login'; };
    shell.querySelector('#logoutBtn').onclick = logout;
    shell.querySelector('#topLogoutBtn').onclick = logout;
    const sidebar = shell.querySelector('#sidebar');
    const backdrop = shell.querySelector('#backdrop');
    shell.querySelector('#menuBtn').onclick = () => { sidebar.classList.add('open'); backdrop.classList.add('show'); };
    backdrop.onclick = () => { sidebar.classList.remove('open'); backdrop.classList.remove('show'); };

    api('GET', '/api/leaves?status=Pending').then(list => {
        const badge = document.getElementById('pendingBadge');
        if (badge && list.length) { badge.textContent = list.length; badge.classList.remove('hidden'); }
    }).catch(() => {});

    const pending = sessionStorage.getItem('flash');
    if (pending) {
        sessionStorage.removeItem('flash');
        const { message, type } = JSON.parse(pending);
        toast(message, type);
    }
    return user;
}
