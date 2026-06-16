/* ═══════════════════════════════════════════════════════════
   Enterprise Org Chart - Main JavaScript
   Vanilla JS | No jQuery | RTL Persian UI
   ═══════════════════════════════════════════════════════════ */

'use strict';

/* ─── Utility ──────────────────────────────────────────────── */
const API = window.ORG_CONFIG?.apiBase || '/org/api/';
const CSRF = window.ORG_CONFIG?.csrfToken || '';

async function apiFetch(url, options = {}) {
    const defaults = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CSRF,
        },
    };
    const res = await fetch(url, { ...defaults, ...options });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || err.message || `HTTP ${res.status}`);
    }
    return res.json();
}

function debounce(fn, delay) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

function el(tag, cls, html = '') {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html) e.innerHTML = html;
    return e;
}

function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(' ');
    return parts.length >= 2
        ? parts[0][0] + parts[parts.length - 1][0]
        : name[0];
}

const NODE_LABELS = {
    company: 'شرکت',
    department: 'واحد سازمانی',
    position: 'پست سازمانی',
    employee: 'پرسنل',
};

const ACTION_ICONS = {
    create: 'plus-circle-fill',
    update: 'pencil-fill',
    delete: 'trash-fill',
    assign: 'person-check-fill',
    move:   'arrows-move',
};

/* ─── ContextMenu ──────────────────────────────────────────── */
class ContextMenu {
    constructor() {
        this.el = document.getElementById('contextMenu');
        this.listEl = document.getElementById('contextMenuList');
        this._currentNode = null;
        this._bound_hide = this._hide.bind(this);
        document.addEventListener('click', this._bound_hide);
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') this._hide(); });
    }

    show(x, y, nodeType, nodeId, nodeName, companyId) {
        this._currentNode = { nodeType, nodeId, nodeName, companyId };
        const items = this._buildItems(nodeType, nodeId, nodeName, companyId);
        this.listEl.innerHTML = items;
        this.el.classList.add('show');

        // Position — keep within viewport
        const vw = window.innerWidth, vh = window.innerHeight;
        let left = x, top = y;
        this.el.style.left = '0'; this.el.style.top = '0';
        const rect = this.el.getBoundingClientRect();
        if (left + rect.width > vw) left = vw - rect.width - 10;
        if (top + rect.height > vh) top = vh - rect.height - 10;
        this.el.style.left = left + 'px';
        this.el.style.top = top + 'px';
    }

    _hide() {
        this.el.classList.remove('show');
    }

    _buildItems(nodeType, nodeId, nodeName, companyId) {
        const n = { nodeType, nodeId, nodeName, companyId };
        let items = '';

        const btn = (icon, label, action, extra = '', cls = '') =>
            `<li class="${cls}"><button onclick="app.contextAction('${action}',${JSON.stringify(n)})" ${extra}>
                <i class="bi bi-${icon}"></i>${label}
             </button></li>`;
        const divider = () => '<li class="menu-divider"></li>';

        if (nodeType === 'company') {
            items += btn('building-add', 'افزودن واحد', 'add_dept');
            items += divider();
            items += btn('arrow-clockwise', 'بارگذاری مجدد', 'refresh');
        }
        if (nodeType === 'department') {
            items += btn('building-add', 'افزودن زیرواحد', 'add_dept');
            items += btn('person-badge', 'افزودن پست', 'add_pos');
            items += divider();
            items += btn('pencil', 'تغییر نام', 'rename');
            items += btn('arrows-move', 'جابجایی', 'move');
            items += divider();
            items += btn('trash', 'حذف', 'delete', '', 'danger');
        }
        if (nodeType === 'position') {
            items += btn('person-plus', 'تخصیص پرسنل', 'assign_user');
            items += btn('shield-plus', 'تخصیص نقش', 'assign_role');
            items += btn('shield-lock', 'مدیریت دسترسی‌ها', 'manage_perms');
            items += divider();
            items += btn('node-plus', 'افزودن پست زیرمجموعه', 'add_child_pos');
            items += btn('pencil', 'تغییر نام', 'rename');
            items += btn('arrows-move', 'جابجایی', 'move');
            items += divider();
            items += btn('clock-history', 'تاریخچه', 'history');
            items += divider();
            items += btn('trash', 'حذف', 'delete', '', 'danger');
        }
        return items;
    }
}

/* ─── DetailPanel ──────────────────────────────────────────── */
class DetailPanel {
    constructor() {
        this.emptyEl   = document.getElementById('detailEmpty');
        this.contentEl = document.getElementById('detailContent');
        this.headerEl  = document.getElementById('detailNodeHeader');
        this.infoEl    = document.getElementById('detailInfoBody');
        this.actionsEl = document.getElementById('detailActions');
        this.permsEl   = document.getElementById('detailPermissionsBody');
        this.historyEl = document.getElementById('detailHistoryBody');
        this._currentType = null;
        this._currentId   = null;

        // Lazy-load permissions/history on tab click
        document.querySelector('[data-bs-target="#tabPermissions"]')
            ?.addEventListener('shown.bs.tab', () => this._loadPermissions());
        document.querySelector('[data-bs-target="#tabHistory"]')
            ?.addEventListener('shown.bs.tab', () => this._loadHistory());
    }

    async show(nodeType, nodeId) {
        this._currentType = nodeType;
        this._currentId   = nodeId;

        // Show permissions tab only for positions
        document.getElementById('tabPermissionsLi').style.display =
            nodeType === 'position' ? '' : 'none';

        // Reset tabs to info
        document.querySelector('[data-bs-target="#tabInfo"]')?.click();

        try {
            const data = await apiFetch(`${API}node/${nodeType}/${nodeId}/`);
            const d = data.data;
            this._renderHeader(nodeType, d);
            this._renderInfo(nodeType, d);
            this._renderActions(nodeType, d);
            this.emptyEl.style.display = 'none';
            this.contentEl.classList.remove('d-none');
        } catch (e) {
            showToast('خطا در بارگذاری جزئیات: ' + e.message, 'error');
        }
    }

    hide() {
        this.emptyEl.style.display = '';
        this.contentEl.classList.add('d-none');
    }

    _renderHeader(type, d) {
        const colors  = { company: '#1a73e8', department: '#7c3aed', position: '#475569', employee: '#d97706' };
        const icons   = { company: 'building-fill', department: 'grid-fill', position: 'person-badge-fill', employee: 'person-fill' };
        const labels  = NODE_LABELS;
        const color = colors[type] || '#475569';
        const name = d.name || d.title || d.full_name;
        this.headerEl.innerHTML = `
            <div class="detail-node-icon" style="background:linear-gradient(135deg,${color},${color}cc)">
                <i class="bi bi-${icons[type]}"></i>
            </div>
            <div class="flex-1" style="min-width:0">
                <div class="detail-node-title">${name}</div>
                <div class="detail-node-type">
                    <span class="badge-node-type badge-${type}">${labels[type]}</span>
                    ${d.is_active !== undefined
                        ? `<span class="ms-2"><span class="status-dot ${d.is_active ? 'active' : 'inactive'}"></span> ${d.is_active ? 'فعال' : 'غیرفعال'}</span>`
                        : ''}
                </div>
            </div>`;
    }

    _row(label, value) {
        if (!value && value !== 0) return '';
        return `<div class="detail-row">
            <div class="detail-label">${label}</div>
            <div class="detail-value">${value}</div>
        </div>`;
    }

    _section(title) {
        return `<div class="detail-section-title"><i class="bi bi-chevron-left"></i>${title}</div>`;
    }

    _renderInfo(type, d) {
        let html = '';
        if (type === 'company') {
            html = this._section('اطلاعات شرکت') +
                this._row('نام شرکت', d.name) +
                this._row('نام انگلیسی', d.name_en) +
                this._row('شماره ثبت', d.registration_number) +
                this._row('وب‌سایت', d.website ? `<a href="${d.website}" target="_blank">${d.website}</a>` : '') +
                this._row('تعداد واحدها', d.department_count) +
                this._row('تعداد پرسنل', d.employee_count) +
                this._row('توضیحات', d.description) +
                this._section('تاریخ‌ها') +
                this._row('ایجاد', d.created_at) +
                this._row('آخرین ویرایش', d.updated_at);
        } else if (type === 'department') {
            html = this._section('اطلاعات واحد') +
                this._row('نام واحد', d.name) +
                this._row('کد واحد', `<code>${d.code}</code>`) +
                this._row('شرکت', d.company) +
                this._row('واحد والد', d.parent || 'ندارد') +
                this._row('مدیر', d.manager_name || '—') +
                this._row('تعداد پرسنل', d.employee_count) +
                this._row('تعداد پست‌ها', d.position_count) +
                this._row('توضیحات', d.description) +
                this._section('تاریخ‌ها') +
                this._row('ایجاد', d.created_at) +
                this._row('آخرین ویرایش', d.updated_at);
        } else if (type === 'position') {
            const employeeHtml = d.employee
                ? `<div class="d-flex align-items-center gap-2">
                    <div class="emp-avatar" style="width:28px;height:28px;font-size:11px">
                        ${d.employee.avatar_url
                            ? `<img src="${d.employee.avatar_url}" alt="">`
                            : getInitials(d.employee.name)}
                    </div>
                    <div><div style="font-size:.82rem;font-weight:600">${d.employee.name}</div>
                    <div style="font-size:.7rem;color:var(--text-muted)">${d.employee.personnel_number}</div></div>
                   </div>`
                : '<span class="text-muted fst-italic">خالی (تخصیص نیافته)</span>';

            const rolesHtml = d.roles.length
                ? d.roles.map(r => `<span class="role-chip">${r.name}</span>`).join('')
                : '<span class="text-muted fst-italic">ندارد</span>';

            html = this._section('اطلاعات پست') +
                this._row('عنوان پست', d.title) +
                this._row('کد پست', `<code>${d.code}</code>`) +
                this._row('واحد', d.department) +
                this._row('شرکت', d.company) +
                this._row('پست والد', d.parent || 'ندارد') +
                this._row('تعداد زیرمجموعه', d.subordinate_count) +
                this._section('پرسنل و نقش') +
                this._row('پرسنل تخصیص‌یافته', employeeHtml) +
                this._row('نقش‌ها', rolesHtml) +
                this._section('دسترسی') +
                this._row('تعداد دسترسی‌ها',
                    `<span class="perm-badge"><i class="bi bi-shield-check"></i> ${d.permission_count}</span>`) +
                this._row('استثناهای کاربر', d.user_override_count) +
                this._section('تاریخ‌ها') +
                this._row('ایجاد', d.created_at) +
                this._row('آخرین ویرایش', d.updated_at);
        } else if (type === 'employee') {
            const posHtml = d.positions.map(p =>
                `<div class="badge bg-light text-dark border me-1 mb-1" style="font-size:.72rem;font-weight:500">
                    ${p.is_primary ? '<i class="bi bi-star-fill text-warning me-1" title="اصلی"></i>' : ''}
                    ${p.title} / ${p.department}
                </div>`
            ).join('') || '<span class="text-muted fst-italic">ندارد</span>';

            html = this._section('اطلاعات پرسنلی') +
                this._row('نام کامل', d.full_name) +
                this._row('شماره پرسنلی', `<code>${d.personnel_number}</code>`) +
                this._row('کد ملی', d.national_id || '—') +
                this._row('ایمیل', d.email ? `<a href="mailto:${d.email}">${d.email}</a>` : '—') +
                this._row('تلفن', d.phone || '—') +
                this._row('تاریخ استخدام', d.hire_date || '—') +
                this._section('پست‌های سازمانی') +
                `<div class="py-2">${posHtml}</div>` +
                this._section('دسترسی') +
                this._row('استثناهای دسترسی', d.permission_override_count);
        }
        this.infoEl.innerHTML = html;
    }

    _renderActions(type, d) {
        let html = '';
        const btnPrimary = (icon, label, action, extra = '') =>
            `<button class="btn btn-outline-primary btn-sm" onclick="app.nodeAction('${action}',${JSON.stringify({ nodeType: type, nodeId: d.id, nodeName: d.name || d.title || d.full_name })})" ${extra}>
                <i class="bi bi-${icon}"></i>${label}
             </button>`;
        const btnDanger = (icon, label, action) =>
            `<button class="btn btn-outline-danger btn-sm" onclick="app.nodeAction('${action}',${JSON.stringify({ nodeType: type, nodeId: d.id, nodeName: d.name || d.title || d.full_name })})">
                <i class="bi bi-${icon}"></i>${label}
             </button>`;

        if (type === 'company') {
            html = btnPrimary('building-add', 'افزودن واحد', 'add_dept');
        } else if (type === 'department') {
            html = btnPrimary('person-badge', 'افزودن پست', 'add_pos') +
                   btnPrimary('pencil', 'تغییر نام', 'rename') +
                   btnDanger('trash', 'حذف', 'delete');
        } else if (type === 'position') {
            html = btnPrimary('person-plus', 'تخصیص پرسنل', 'assign_user') +
                   btnPrimary('shield-plus', 'مدیریت نقش‌ها', 'assign_role') +
                   btnPrimary('shield-lock', 'مدیریت دسترسی', 'manage_perms') +
                   btnPrimary('node-plus', 'افزودن زیرپست', 'add_child_pos') +
                   btnPrimary('pencil', 'تغییر نام', 'rename') +
                   btnDanger('trash', 'حذف', 'delete');
        }
        this.actionsEl.innerHTML = html;
    }

    async _loadPermissions() {
        if (this._currentType !== 'position') return;
        this.permsEl.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm"></div></div>';
        try {
            const data = await apiFetch(`${API}permissions/${this._currentId}/`);
            const d = data.data;
            let html = '';
            const cats = { hr: 'منابع انسانی', finance: 'مالی', it: 'فناوری اطلاعات', admin: 'مدیریتی', report: 'گزارش', other: 'سایر' };
            for (const [roleName, perms] of Object.entries(d.role_permissions)) {
                html += `<div class="perm-category-title"><i class="bi bi-shield me-1"></i>نقش: ${roleName}</div>`;
                perms.forEach(p => {
                    html += `<div class="perm-item">
                        <i class="bi bi-check-circle-fill"></i>
                        <span>${p.name}</span>
                        <code class="ms-auto" style="font-size:.68rem">${p.codename}</code>
                    </div>`;
                });
            }
            if (d.user_overrides.length) {
                html += `<div class="perm-category-title mt-2"><i class="bi bi-person-lock me-1"></i>استثناهای کاربر</div>`;
                d.user_overrides.forEach(o => {
                    const badge = o.override_type === 'grant'
                        ? '<span class="override-grant">اعطا</span>'
                        : '<span class="override-deny">سلب</span>';
                    html += `<div class="perm-item">${badge} <span>${o.name}</span></div>`;
                });
            }
            if (!html) html = '<div class="text-muted text-center py-3 small">دسترسی‌ای تعریف نشده</div>';
            this.permsEl.innerHTML = html;
        } catch (e) {
            this.permsEl.innerHTML = `<div class="text-danger small py-3 text-center">خطا: ${e.message}</div>`;
        }
    }

    async _loadHistory() {
        if (!this._currentType || !this._currentId) return;
        this.historyEl.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm"></div></div>';
        try {
            const data = await apiFetch(`${API}history/${this._currentType}/${this._currentId}/`);
            const items = data.history;
            if (!items.length) {
                this.historyEl.innerHTML = '<div class="text-muted text-center py-3 small">تاریخچه‌ای وجود ندارد</div>';
                return;
            }
            let html = '';
            items.forEach(item => {
                const icon = ACTION_ICONS[item.action] || 'info-circle-fill';
                html += `<div class="history-item">
                    <div class="history-icon ${item.action}"><i class="bi bi-${icon}"></i></div>
                    <div>
                        <div class="history-desc">${item.description}</div>
                        <div class="d-flex gap-3 mt-1">
                            <span class="history-by"><i class="bi bi-person me-1"></i>${item.performed_by}</span>
                            <span class="history-time"><i class="bi bi-clock me-1"></i>${item.created_at}</span>
                        </div>
                    </div>
                </div>`;
            });
            this.historyEl.innerHTML = html;
        } catch (e) {
            this.historyEl.innerHTML = `<div class="text-danger small py-3 text-center">خطا: ${e.message}</div>`;
        }
    }
}

/* ─── OrgChart ─────────────────────────────────────────────── */
class OrgChart {
    constructor(container) {
        this.container  = container;
        this.zoomWrap   = document.getElementById('treeZoomWrap');
        this.zoomScale  = 1;
        this.selectedId = null;
        this.treeData   = null;
        this._expandedIds = new Set();
    }

    render(data) {
        this.treeData = data;
        this.container.innerHTML = '';

        if (!data) {
            this.container.innerHTML = '<div class="text-muted text-center py-5">داده‌ای یافت نشد</div>';
            return;
        }

        const rootNode = this._buildNodeEl(data, true);
        this.container.appendChild(rootNode);
        this._expandedIds = new Set(); // reset
    }

    _buildNodeEl(node, isRoot = false) {
        const wrap = el('div', 'org-node-wrap');

        // The card
        const card = this._createCard(node);
        wrap.appendChild(card);

        // Children
        if (node.children && node.children.length > 0) {
            const childrenWrap = el('div', 'org-children-wrap');
            const connDown = el('div', '', '');
            connDown.style.cssText = `width:2px;height:20px;background:var(--connector-color);margin:0 auto`;
            childrenWrap.appendChild(connDown);

            const childrenRow = el('div', 'org-children');
            const childIds = node.children.map(c => c.id);

            node.children.forEach((child, idx) => {
                const childWrap = el('div', 'org-child-connector');
                const childNode = this._buildNodeEl(child);
                childWrap.appendChild(childNode);
                childrenRow.appendChild(childWrap);
            });

            // Horizontal line above children
            const hLineWrap = el('div', 'position-relative');
            hLineWrap.style.cssText = 'width:100%;';

            childrenWrap.appendChild(childrenRow);
            wrap.appendChild(childrenWrap);

            // Collapse toggle on card
            if (!isRoot) {
                const toggle = el('div', 'node-toggle', '<i class="bi bi-dash"></i>');
                toggle.title = 'بستن/باز کردن زیرمجموعه‌ها';
                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._toggleChildren(node.id, childrenWrap, toggle);
                });
                card.appendChild(toggle);
            }
        }

        return wrap;
    }

    _createCard(node) {
        let cardHtml = '';
        let cardClass = 'org-node ';

        if (node.type === 'company') {
            cardClass += 'node-company';
            cardHtml = `
                <div class="node-body d-flex align-items-center gap-2">
                    <div class="node-icon"><i class="bi bi-building-fill"></i></div>
                    <div>
                        <div class="node-name">${node.name}</div>
                        <div class="node-meta">${node.name_en || ''}</div>
                    </div>
                </div>`;
        } else if (node.type === 'department') {
            cardClass += 'node-department';
            cardHtml = `
                <div class="node-body d-flex align-items-center gap-2">
                    <div class="node-icon"><i class="bi bi-grid-fill"></i></div>
                    <div>
                        <div class="node-name">${node.name}</div>
                        <span class="emp-badge"><i class="bi bi-people-fill me-1"></i>${node.employee_count || 0} نفر</span>
                    </div>
                </div>`;
        } else if (node.type === 'position') {
            const hasEmployee = !!node.employee;
            cardClass += 'node-position' + (hasEmployee ? ' has-employee' : ' vacant');
            const empHtml = hasEmployee
                ? `<div class="pos-employee">
                    <div class="emp-avatar" style="width:22px;height:22px;font-size:10px;border-radius:50%;background:linear-gradient(135deg,#d97706,#fbbf24);display:flex;align-items:center;justify-content:center;color:#fff">
                        ${node.employee.avatar_url
                            ? `<img src="${node.employee.avatar_url}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%">`
                            : getInitials(node.employee.name)}
                    </div>
                    <span>${node.employee.name}</span>
                   </div>`
                : `<div class="pos-employee" style="opacity:.5"><i class="bi bi-person-dash me-1"></i><span class="fst-italic">خالی</span></div>`;

            const roleHtml = node.role_name
                ? `<span class="pos-role"><i class="bi bi-shield me-1"></i>${node.role_name}</span>`
                : '';

            const permHtml = node.permission_count > 0
                ? `<span class="perm-badge mt-1"><i class="bi bi-shield-check"></i>${node.permission_count} دسترسی</span>`
                : '';

            cardHtml = `
                <div class="node-actions">
                    <button class="btn-node-action" title="تخصیص پرسنل" onclick="event.stopPropagation();app.nodeAction('assign_user',{nodeType:'position',nodeId:${node.db_id},nodeName:'${node.title}'})">
                        <i class="bi bi-person-plus"></i>
                    </button>
                    <button class="btn-node-action" title="مدیریت نقش" onclick="event.stopPropagation();app.nodeAction('assign_role',{nodeType:'position',nodeId:${node.db_id},nodeName:'${node.title}'})">
                        <i class="bi bi-shield"></i>
                    </button>
                    <button class="btn-node-action danger" title="حذف" onclick="event.stopPropagation();app.nodeAction('delete',{nodeType:'position',nodeId:${node.db_id},nodeName:'${node.title}'})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
                <div class="node-body">
                    <div class="pos-title">${node.title}</div>
                    <div class="pos-employee-wrap">${empHtml}</div>
                    ${roleHtml}
                    <div class="d-flex align-items-center gap-2 mt-1 flex-wrap">
                        ${permHtml}
                        ${node.subordinate_count > 0
                            ? `<span class="badge bg-light text-secondary" style="font-size:.65rem">${node.subordinate_count} زیرمجموعه</span>`
                            : ''}
                    </div>
                </div>`;
        }

        const card = el('div', cardClass);
        card.setAttribute('data-node-id', node.id);
        card.setAttribute('data-node-type', node.type);
        card.setAttribute('data-db-id', node.db_id);
        card.setAttribute('draggable', node.type !== 'company' ? 'true' : 'false');
        card.innerHTML = cardHtml;

        card.addEventListener('click', () => this._onNodeClick(node));
        card.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this._onNodeRightClick(e, node);
        });
        card.addEventListener('dragstart', (e) => this._onDragStart(e, node));
        card.addEventListener('dragover', (e) => this._onDragOver(e, node));
        card.addEventListener('dragleave', (e) => { card.classList.remove('drag-over'); });
        card.addEventListener('drop', (e) => this._onDrop(e, node));

        return card;
    }

    _onNodeClick(node) {
        // Deselect current
        document.querySelectorAll('.org-node.selected').forEach(n => n.classList.remove('selected'));
        const el = document.querySelector(`[data-node-id="${node.id}"]`);
        if (el) el.classList.add('selected');
        this.selectedId = node.id;
        app.detailPanel.show(node.type, node.db_id);

        // Update breadcrumb
        this._updateBreadcrumb(node);
    }

    _onNodeRightClick(e, node) {
        app.contextMenu.show(
            e.clientX, e.clientY,
            node.type, node.db_id,
            node.name || node.title,
            window.ORG_CONFIG.initialCompanyId
        );
    }

    _updateBreadcrumb(node) {
        const bc = document.getElementById('breadcrumb');
        const label = node.name || node.title;
        bc.innerHTML = `<li class="breadcrumb-item"><a href="#">نمای کلی</a></li>
                        <li class="breadcrumb-item active">${label}</li>`;
    }

    _toggleChildren(nodeId, childrenWrap, toggle) {
        const collapsed = childrenWrap.classList.toggle('collapsed');
        toggle.innerHTML = collapsed
            ? '<i class="bi bi-plus"></i>'
            : '<i class="bi bi-dash"></i>';
        toggle.title = collapsed ? 'باز کردن زیرمجموعه‌ها' : 'بستن زیرمجموعه‌ها';
    }

    expandAll() {
        document.querySelectorAll('.org-children-wrap.collapsed').forEach(w => {
            w.classList.remove('collapsed');
            const toggle = w.previousElementSibling?.querySelector?.('.node-toggle');
            if (toggle) toggle.innerHTML = '<i class="bi bi-dash"></i>';
        });
    }

    collapseAll() {
        document.querySelectorAll('.org-children-wrap').forEach(w => {
            w.classList.add('collapsed');
            const card = w.closest('.org-node-wrap')?.querySelector('.org-node');
            const toggle = card?.querySelector('.node-toggle');
            if (toggle) toggle.innerHTML = '<i class="bi bi-plus"></i>';
        });
    }

    zoomIn() {
        this.zoomScale = Math.min(2, this.zoomScale + 0.1);
        this._applyZoom();
    }
    zoomOut() {
        this.zoomScale = Math.max(0.3, this.zoomScale - 0.1);
        this._applyZoom();
    }
    resetZoom() {
        this.zoomScale = 1;
        this._applyZoom();
    }
    _applyZoom() {
        this.zoomWrap.style.transform = `scale(${this.zoomScale})`;
        document.getElementById('zoomLevel').textContent =
            Math.round(this.zoomScale * 100) + '%';
    }

    toggleFullscreen() {
        const panel = document.getElementById('treePanel');
        if (!document.fullscreenElement) {
            panel.requestFullscreen?.();
        } else {
            document.exitFullscreen?.();
        }
    }

    highlightNodes(nodeIds) {
        document.querySelectorAll('.org-node.highlighted').forEach(n => n.classList.remove('highlighted'));
        nodeIds.forEach(id => {
            const card = document.querySelector(`[data-node-id="${id}"]`);
            if (card) {
                card.classList.add('highlighted');
                // Auto-expand parent chain
                let wrap = card.closest('.org-children-wrap');
                while (wrap) {
                    wrap.classList.remove('collapsed');
                    wrap = wrap.parentElement?.closest('.org-children-wrap');
                }
                // Scroll into view
                card.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
            }
        });
    }

    clearHighlight() {
        document.querySelectorAll('.org-node.highlighted').forEach(n => n.classList.remove('highlighted'));
    }

    // Drag & Drop
    _onDragStart(e, node) {
        if (node.type === 'company') { e.preventDefault(); return; }
        e.dataTransfer.setData('application/json', JSON.stringify({
            nodeType: node.type,
            nodeId: node.db_id,
            nodeName: node.name || node.title,
        }));
        e.currentTarget.classList.add('dragging');
        setTimeout(() => e.currentTarget.classList.remove('dragging'), 300);
    }

    _onDragOver(e, targetNode) {
        e.preventDefault();
        const card = e.currentTarget;
        // Only allow valid drop targets
        if (targetNode.type === 'company' || targetNode.type === 'department' || targetNode.type === 'position') {
            card.classList.add('drag-over');
        }
    }

    _onDrop(e, targetNode) {
        e.preventDefault();
        const card = e.currentTarget;
        card.classList.remove('drag-over');
        try {
            const dragged = JSON.parse(e.dataTransfer.getData('application/json'));
            if (dragged.nodeId === targetNode.db_id) return;
            app.showDragConfirm(dragged, targetNode);
        } catch {}
    }
}

/* ─── App Controller ───────────────────────────────────────── */
class App {
    constructor() {
        this.chart       = null;
        this.detailPanel = new DetailPanel();
        this.contextMenu = new ContextMenu();
        this._companyId  = window.ORG_CONFIG?.initialCompanyId;
        this._selectedEmployee = null;
    }

    async init() {
        this.chart = new OrgChart(document.getElementById('treeInner'));
        this._bindToolbar();
        this._bindSearch();
        this._bindCompanySelector();
        this._bindModals();
        this._bindKeyboard();

        if (this._companyId) {
            await this.loadTree(this._companyId);
        }
    }

    async loadTree(companyId) {
        document.getElementById('treeLoading').style.display = '';
        document.getElementById('treeInner').innerHTML = '';
        document.getElementById('treeInner').appendChild(document.getElementById('treeLoading'));

        try {
            const data = await apiFetch(`${API}tree/${companyId}/`);
            document.getElementById('treeLoading').style.display = 'none';
            this.chart.render(data.data);
        } catch (e) {
            document.getElementById('treeLoading').style.display = 'none';
            document.getElementById('treeInner').innerHTML =
                `<div class="text-danger text-center py-5"><i class="bi bi-exclamation-triangle fs-2 d-block mb-2"></i>خطا: ${e.message}</div>`;
        }
    }

    _bindCompanySelector() {
        document.getElementById('companySelector')?.addEventListener('change', (e) => {
            this._companyId = parseInt(e.target.value);
            window.ORG_CONFIG.initialCompanyId = this._companyId;
            this.loadTree(this._companyId);
            this.detailPanel.hide();
        });
    }

    _bindToolbar() {
        document.getElementById('expandAllBtn')?.addEventListener('click', () => this.chart.expandAll());
        document.getElementById('collapseAllBtn')?.addEventListener('click', () => this.chart.collapseAll());
        document.getElementById('zoomInBtn')?.addEventListener('click', () => this.chart.zoomIn());
        document.getElementById('zoomOutBtn')?.addEventListener('click', () => this.chart.zoomOut());
        document.getElementById('zoomResetBtn')?.addEventListener('click', () => this.chart.resetZoom());
        document.getElementById('fullscreenBtn')?.addEventListener('click', () => this.chart.toggleFullscreen());
        document.getElementById('refreshBtn')?.addEventListener('click', () => {
            if (this._companyId) this.loadTree(this._companyId);
        });
        document.getElementById('clearSearchBtn')?.addEventListener('click', () => this._clearSearch());
        document.getElementById('clearSearchInline')?.addEventListener('click', () => this._clearSearch());
    }

    _bindSearch() {
        const searchFn = debounce(async (q) => {
            if (!q || q.length < 2) { this._clearSearch(); return; }
            try {
                const data = await apiFetch(`${API}search/?q=${encodeURIComponent(q)}&company_id=${this._companyId || ''}`);
                const results = data.results;
                const bar = document.getElementById('searchResultsBar');
                const text = document.getElementById('searchResultsText');
                bar.classList.remove('d-none');
                text.textContent = `${results.length} نتیجه یافت شد`;
                this.chart.highlightNodes(results.map(r => r.id));
            } catch {}
        }, 350);

        document.getElementById('searchInput')?.addEventListener('input', (e) => {
            searchFn(e.target.value.trim());
        });
    }

    _clearSearch() {
        document.getElementById('searchInput').value = '';
        document.getElementById('searchResultsBar').classList.add('d-none');
        this.chart.clearHighlight();
    }

    _bindKeyboard() {
        document.addEventListener('keydown', (e) => {
            if (e.key === '+' || e.key === '=') { e.preventDefault(); this.chart.zoomIn(); }
            if (e.key === '-') { e.preventDefault(); this.chart.zoomOut(); }
            if (e.key === '0') { e.preventDefault(); this.chart.resetZoom(); }
        });
    }

    _bindModals() {
        // Add Node
        document.getElementById('addNodeSubmitBtn')?.addEventListener('click', () => this._submitAddNode());

        // Assign User
        document.getElementById('assignUserSubmitBtn')?.addEventListener('click', () => this._submitAssignUser());
        document.getElementById('employeeSearchInput')?.addEventListener('input', debounce((e) => {
            this._loadEmployeeList(e.target.value);
        }, 300));

        // Confirm Delete
        document.getElementById('confirmDeleteBtn')?.addEventListener('click', () => this._submitDelete());

        // Rename
        document.getElementById('renameSubmitBtn')?.addEventListener('click', () => this._submitRename());

        // Drag confirm
        document.getElementById('dragConfirmBtn')?.addEventListener('click', () => this._submitDragMove());

        // Reset state on modal open
        document.getElementById('assignUserModal')?.addEventListener('show.bs.modal', () => {
            this._selectedEmployee = null;
            document.getElementById('assignUserSubmitBtn').disabled = true;
            this._loadEmployeeList('');
        });

        document.getElementById('assignRoleModal')?.addEventListener('show.bs.modal', () => {
            this._loadRoleList();
        });
    }

    /* ── Context Menu / Node Actions ── */
    contextAction(action, node) {
        this.nodeAction(action, node);
    }

    nodeAction(action, node) {
        const { nodeType, nodeId, nodeName, companyId } = node;
        switch (action) {
            case 'add_dept':
                this._showAddNodeModal('department', nodeId, nodeType, companyId || this._companyId);
                break;
            case 'add_pos':
            case 'add_child_pos':
                this._showAddNodeModal('position', nodeId, nodeType, companyId || this._companyId);
                break;
            case 'assign_user':
                document.getElementById('assignUserPositionId').value = nodeId;
                new bootstrap.Modal(document.getElementById('assignUserModal')).show();
                break;
            case 'assign_role':
                document.getElementById('assignRolePositionId').value = nodeId;
                new bootstrap.Modal(document.getElementById('assignRoleModal')).show();
                break;
            case 'manage_perms':
                this._showPermissionsModal(nodeId);
                break;
            case 'rename':
                document.getElementById('renameNodeId').value = nodeId;
                document.getElementById('renameNodeType').value = nodeType;
                document.getElementById('renameInput').value = nodeName || '';
                new bootstrap.Modal(document.getElementById('renameModal')).show();
                break;
            case 'delete':
                document.getElementById('deleteNodeId').value = nodeId;
                document.getElementById('deleteNodeType').value = nodeType;
                document.getElementById('deleteNodeName').textContent = nodeName || '';
                new bootstrap.Modal(document.getElementById('confirmDeleteModal')).show();
                break;
            case 'history':
                this._showHistoryModal(nodeType, nodeId);
                break;
            case 'refresh':
                this.loadTree(this._companyId);
                break;
        }
    }

    /* ── Add Node Modal ── */
    _showAddNodeModal(defaultType, parentId, parentType, companyId) {
        document.getElementById('addNodeParentId').value = parentId;
        document.getElementById('addNodeParentType').value = parentType;
        document.getElementById('addNodeCompanyId').value = companyId || this._companyId;
        document.getElementById('addNodeName').value = '';
        document.getElementById('addNodeCode').value = '';
        document.querySelector(`input[name="newNodeType"][value="${defaultType}"]`).checked = true;
        const title = defaultType === 'department' ? 'افزودن واحد سازمانی' : 'افزودن پست سازمانی';
        document.getElementById('addNodeModalTitle').textContent = title;
        new bootstrap.Modal(document.getElementById('addNodeModal')).show();
    }

    async _submitAddNode() {
        const nodeType    = document.querySelector('input[name="newNodeType"]:checked')?.value;
        const name        = document.getElementById('addNodeName').value.trim();
        const code        = document.getElementById('addNodeCode').value.trim();
        const parentId    = document.getElementById('addNodeParentId').value;
        const parentType  = document.getElementById('addNodeParentType').value;
        const companyId   = document.getElementById('addNodeCompanyId').value;

        if (!name || !code) { showToast('نام و کد الزامی است', 'warning'); return; }

        try {
            const data = await apiFetch(`${API}add-node/`, {
                method: 'POST',
                body: JSON.stringify({ node_type: nodeType, name, code, parent_id: parentId, parent_type: parentType, company_id: companyId }),
            });
            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('addNodeModal'))?.hide();
                showToast(data.message, 'success');
                await this.loadTree(this._companyId);
            } else {
                showToast(data.error || 'خطا', 'error');
            }
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    /* ── Assign User ── */
    async _loadEmployeeList(q = '') {
        const container = document.getElementById('employeeListContainer');
        container.innerHTML = '<div class="text-center text-muted py-3 small"><div class="spinner-border spinner-border-sm me-1"></div>بارگذاری...</div>';
        try {
            const data = await apiFetch(`${API}employees/?q=${encodeURIComponent(q)}`);
            const employees = data.employees;
            if (!employees.length) {
                container.innerHTML = '<div class="text-muted text-center py-3 small">پرسنلی یافت نشد</div>';
                return;
            }
            container.innerHTML = employees.map(e => `
                <div class="employee-item" data-emp-id="${e.id}" onclick="app._selectEmployee(${e.id}, this)">
                    <div class="emp-avatar-sm">${e.avatar_url ? `<img src="${e.avatar_url}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%">` : getInitials(e.name)}</div>
                    <div class="emp-info">
                        <div class="emp-fname">${e.name}</div>
                        <div class="emp-fpnum"><i class="bi bi-hash"></i>${e.personnel_number}</div>
                    </div>
                </div>`).join('');
        } catch (e) {
            container.innerHTML = `<div class="text-danger text-center py-3 small">خطا: ${e.message}</div>`;
        }
    }

    _selectEmployee(empId, rowEl) {
        document.querySelectorAll('.employee-item.selected').forEach(r => r.classList.remove('selected'));
        rowEl.classList.add('selected');
        this._selectedEmployee = empId;
        document.getElementById('assignUserSubmitBtn').disabled = false;
    }

    async _submitAssignUser() {
        const positionId = document.getElementById('assignUserPositionId').value;
        if (!this._selectedEmployee) return;
        try {
            const data = await apiFetch(`${API}assign-user/`, {
                method: 'POST',
                body: JSON.stringify({ position_id: positionId, employee_id: this._selectedEmployee }),
            });
            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('assignUserModal'))?.hide();
                showToast(data.message, 'success');
                await this.loadTree(this._companyId);
                this.detailPanel.show('position', positionId);
            } else {
                showToast(data.error || 'خطا', 'error');
            }
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    /* ── Assign Role ── */
    async _loadRoleList() {
        const positionId = document.getElementById('assignRolePositionId').value;
        const container  = document.getElementById('roleListContainer');
        const current    = document.getElementById('currentRolesList');
        container.innerHTML = '<div class="text-center py-3 small"><div class="spinner-border spinner-border-sm"></div></div>';
        try {
            const [rolesData, detailData] = await Promise.all([
                apiFetch(`${API}roles/`),
                apiFetch(`${API}node/position/${positionId}/`),
            ]);
            const allRoles = rolesData.roles;
            const assignedRoles = detailData.data.roles || [];
            const assignedIds = new Set(assignedRoles.map(r => r.id));

            current.innerHTML = assignedRoles.length
                ? assignedRoles.map(r => `
                    <span class="role-chip">
                        ${r.name}
                        <button class="remove-role" onclick="app._removeRole(${positionId},${r.id})" title="حذف نقش">
                            <i class="bi bi-x"></i>
                        </button>
                    </span>`).join('')
                : '<span class="text-muted fst-italic small">نقشی تخصیص نیافته</span>';

            container.innerHTML = allRoles.map(r => `
                <div class="role-item">
                    <div class="role-info">
                        <div class="role-fname">${r.name}</div>
                        <div class="role-pcount"><i class="bi bi-shield me-1"></i>${r.permission_count} دسترسی</div>
                    </div>
                    ${assignedIds.has(r.id)
                        ? '<span class="badge bg-success-subtle text-success"><i class="bi bi-check"></i> تخصیص‌یافته</span>'
                        : `<button class="btn btn-sm btn-outline-primary" onclick="app._assignRole(${positionId},${r.id})">افزودن</button>`}
                </div>`).join('');
        } catch (e) {
            container.innerHTML = `<div class="text-danger text-center py-3 small">خطا: ${e.message}</div>`;
        }
    }

    async _assignRole(positionId, roleId) {
        try {
            await apiFetch(`${API}assign-role/`, {
                method: 'POST',
                body: JSON.stringify({ position_id: positionId, role_id: roleId, action: 'assign' }),
            });
            showToast('نقش تخصیص یافت', 'success');
            this._loadRoleList();
            this.loadTree(this._companyId);
        } catch (e) { showToast(e.message, 'error'); }
    }

    async _removeRole(positionId, roleId) {
        try {
            await apiFetch(`${API}assign-role/`, {
                method: 'POST',
                body: JSON.stringify({ position_id: positionId, role_id: roleId, action: 'remove' }),
            });
            showToast('نقش حذف شد', 'success');
            this._loadRoleList();
            this.loadTree(this._companyId);
        } catch (e) { showToast(e.message, 'error'); }
    }

    /* ── Permissions Modal ── */
    async _showPermissionsModal(positionId) {
        const body = document.getElementById('permissionsModalBody');
        body.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div></div>';
        new bootstrap.Modal(document.getElementById('permissionsModal')).show();
        try {
            const data = await apiFetch(`${API}permissions/${positionId}/`);
            const d = data.data;
            let html = `<h6 class="mb-3"><i class="bi bi-shield-lock me-2"></i>دسترسی‌های پست: <strong>${d.position_title}</strong></h6>`;

            if (!Object.keys(d.role_permissions).length && !d.user_overrides.length) {
                html += '<div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>هیچ دسترسی‌ای تعریف نشده است.</div>';
            }

            for (const [roleName, perms] of Object.entries(d.role_permissions)) {
                html += `<div class="perm-category-title"><i class="bi bi-shield me-1"></i>نقش: ${roleName} <span class="badge bg-primary-subtle text-primary ms-2">${perms.length} دسترسی</span></div>`;
                html += '<div class="row g-1 mb-3">';
                perms.forEach(p => {
                    html += `<div class="col-md-6">
                        <div class="perm-item">
                            <i class="bi bi-check-circle-fill text-success"></i>
                            <div><div style="font-size:.8rem;font-weight:500">${p.name}</div>
                            <code style="font-size:.65rem">${p.codename}</code></div>
                        </div>
                    </div>`;
                });
                html += '</div>';
            }

            if (d.user_overrides.length) {
                html += `<div class="perm-category-title"><i class="bi bi-person-lock me-1"></i>استثناهای کاربری</div>`;
                html += '<div class="row g-1">';
                d.user_overrides.forEach(o => {
                    const badge = o.override_type === 'grant'
                        ? '<span class="override-grant">اعطا</span>'
                        : '<span class="override-deny">سلب</span>';
                    html += `<div class="col-md-6"><div class="perm-item">${badge}<span>${o.name}</span></div></div>`;
                });
                html += '</div>';
            }

            body.innerHTML = html;
        } catch (e) {
            body.innerHTML = `<div class="text-danger">خطا: ${e.message}</div>`;
        }
    }

    /* ── Delete ── */
    async _submitDelete() {
        const nodeId   = document.getElementById('deleteNodeId').value;
        const nodeType = document.getElementById('deleteNodeType').value;
        try {
            const data = await apiFetch(`${API}delete-node/`, {
                method: 'POST',
                body: JSON.stringify({ node_type: nodeType, node_id: nodeId }),
            });
            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('confirmDeleteModal'))?.hide();
                showToast(data.message, 'success');
                this.detailPanel.hide();
                await this.loadTree(this._companyId);
            } else {
                showToast(data.error || 'خطا', 'error');
            }
        } catch (e) { showToast(e.message, 'error'); }
    }

    /* ── Rename ── */
    async _submitRename() {
        const nodeId   = document.getElementById('renameNodeId').value;
        const nodeType = document.getElementById('renameNodeType').value;
        const newName  = document.getElementById('renameInput').value.trim();
        if (!newName) { showToast('نام نمی‌تواند خالی باشد', 'warning'); return; }
        try {
            const data = await apiFetch(`${API}rename-node/`, {
                method: 'POST',
                body: JSON.stringify({ node_type: nodeType, node_id: nodeId, new_name: newName }),
            });
            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('renameModal'))?.hide();
                showToast(data.message, 'success');
                await this.loadTree(this._companyId);
            } else {
                showToast(data.error || 'خطا', 'error');
            }
        } catch (e) { showToast(e.message, 'error'); }
    }

    /* ── History Modal ── */
    async _showHistoryModal(nodeType, nodeId) {
        const body = document.getElementById('historyModalBody');
        body.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div></div>';
        new bootstrap.Modal(document.getElementById('historyModal')).show();
        try {
            const data = await apiFetch(`${API}history/${nodeType}/${nodeId}/`);
            const items = data.history;
            if (!items.length) {
                body.innerHTML = '<div class="text-muted text-center py-4">تاریخچه‌ای موجود نیست</div>';
                return;
            }
            body.innerHTML = items.map(item => {
                const icon = ACTION_ICONS[item.action] || 'info-circle-fill';
                return `<div class="history-item">
                    <div class="history-icon ${item.action}"><i class="bi bi-${icon}"></i></div>
                    <div>
                        <div class="history-desc">${item.description}</div>
                        <div class="d-flex gap-3 mt-1">
                            <span class="history-by"><i class="bi bi-person me-1"></i>${item.performed_by}</span>
                            <span class="history-time"><i class="bi bi-clock me-1"></i>${item.created_at}</span>
                        </div>
                    </div>
                </div>`;
            }).join('');
        } catch (e) {
            body.innerHTML = `<div class="text-danger text-center">خطا: ${e.message}</div>`;
        }
    }

    /* ── Drag & Drop ── */
    _dragPending = null;

    showDragConfirm(dragged, target) {
        this._dragPending = { dragged, target };
        const text = document.getElementById('dragConfirmText');
        text.innerHTML = `آیا می‌خواهید <strong>${dragged.nodeName}</strong> را به <strong>${target.name || target.title}</strong> منتقل کنید؟`;
        new bootstrap.Modal(document.getElementById('dragConfirmModal')).show();
    }

    async _submitDragMove() {
        if (!this._dragPending) return;
        const { dragged, target } = this._dragPending;
        bootstrap.Modal.getInstance(document.getElementById('dragConfirmModal'))?.hide();
        try {
            const data = await apiFetch(`${API}move/`, {
                method: 'POST',
                body: JSON.stringify({
                    node_type: dragged.nodeType,
                    node_id: dragged.nodeId,
                    new_parent_id: target.db_id,
                    new_parent_type: target.type,
                }),
            });
            if (data.success) {
                showToast(data.message, 'success');
                await this.loadTree(this._companyId);
            } else {
                showToast(data.message || data.error, 'error');
            }
        } catch (e) {
            showToast(e.message, 'error');
        }
        this._dragPending = null;
    }
}

/* ─── Bootstrap ─────────────────────────────────────────────── */
let app;

document.addEventListener('DOMContentLoaded', function () {
    app = new App();
    app.init().catch(console.error);
});
