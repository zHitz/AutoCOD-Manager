const TaskPage = {
    _accounts: [],
    _filteredAccounts: [],
    _selectedIndex: 0,
    _search: '',
    _statusFilter: 'all',
    _priorityFilter: 'all',
    _showShortcutHelp: false,
    _boundKeydown: null,

    _checklistTemplates: [
        { key: 'login', label: 'Điểm danh', shortLabel: 'Điểm danh', critical: true },
        { key: 'collect', label: 'Thu tài nguyên', shortLabel: 'Thu tài nguyên', critical: true },
        { key: 'alliance', label: 'Donate liên minh', shortLabel: 'Donate LM', critical: false },
        { key: 'patrol', label: 'Tuần tra / Nhiệm vụ ngày', shortLabel: 'Tuần tra', critical: false },
        { key: 'shop', label: 'Làm mới cửa hàng', shortLabel: 'Shop', critical: false },
        { key: 'event', label: 'Nhận thưởng sự kiện', shortLabel: 'Sự kiện', critical: false },
    ],

    _generateMockData() {
        const priorities = ['high', 'medium', 'low'];
        const statuses = ['on-track', 'at-risk', 'overdue'];
        const regions = ['Global', 'Asia', 'EU'];
        const data = [];

        for (let i = 1; i <= 100; i += 1) {
            const checks = {
                login: Math.random() > 0.25,
                collect: Math.random() > 0.35,
                alliance: Math.random() > 0.45,
                patrol: Math.random() > 0.4,
                shop: Math.random() > 0.5,
                event: Math.random() > 0.55,
            };

            data.push({
                id: i,
                accountName: `ACC_${String(i).padStart(3, '0')}`,
                emulator: `LDPlayer-${String((i % 12) + 1).padStart(2, '0')}`,
                owner: `Nhóm ${String.fromCharCode(65 + (i % 6))}`,
                region: regions[i % regions.length],
                priority: priorities[i % priorities.length],
                status: statuses[i % statuses.length],
                checks,
                note: i % 4 === 0 ? 'Theo dõi event giờ vàng' : 'Ổn định',
                nextReset: `${String((i % 24)).padStart(2, '0')}:00`,
            });
        }

        return data;
    },

    _getProgress(account) {
        const done = Object.values(account.checks).filter(Boolean).length;
        const total = this._checklistTemplates.length;
        return {
            done,
            total,
            percent: Math.round((done / total) * 100),
        };
    },

    _computeStats() {
        const totalAccounts = this._accounts.length;
        let doneTasks = 0;
        let totalTasks = 0;
        let overdue = 0;

        this._accounts.forEach((acc) => {
            const progress = this._getProgress(acc);
            doneTasks += progress.done;
            totalTasks += progress.total;
            if (acc.status === 'overdue') overdue += 1;
        });

        const coverage = Math.round((doneTasks / totalTasks) * 100);
        const target = 85;

        return {
            totalAccounts,
            doneTasks,
            totalTasks,
            overdue,
            coverage,
            target,
            gap: Math.max(target - coverage, 0),
        };
    },

    _applyFilters() {
        const q = this._search.trim().toLowerCase();
        this._filteredAccounts = this._accounts.filter((acc) => {
            const matchSearch = !q
                || acc.accountName.toLowerCase().includes(q)
                || acc.emulator.toLowerCase().includes(q)
                || acc.owner.toLowerCase().includes(q);
            const matchStatus = this._statusFilter === 'all' || acc.status === this._statusFilter;
            const matchPriority = this._priorityFilter === 'all' || acc.priority === this._priorityFilter;
            return matchSearch && matchStatus && matchPriority;
        });

        if (this._selectedIndex >= this._filteredAccounts.length) {
            this._selectedIndex = Math.max(this._filteredAccounts.length - 1, 0);
        }
    },

    _renderPriorityBadge(priority) {
        const map = {
            high: 'Cao',
            medium: 'Trung bình',
            low: 'Thấp',
        };

        return `<span class="task-pill task-priority-pill ${priority}">${map[priority] || priority}</span>`;
    },

    render() {
        if (!this._accounts.length) {
            this._accounts = this._generateMockData();
        }

        this._applyFilters();
        const stats = this._computeStats();
        const selected = this._filteredAccounts[this._selectedIndex];

        return `
            <style>
                .task-page { display: flex; flex-direction: column; gap: 16px; }
                .task-stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
                .task-stat-card { border: 1px solid var(--border); background: var(--card); border-radius: 10px; padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; }
                .task-stat-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.7px; color: var(--muted-foreground); font-weight: 600; }
                .task-stat-value { font-size: 24px; font-weight: 700; letter-spacing: -0.02em; }
                .task-stat-sub { font-size: 12px; color: var(--muted-foreground); }
                .task-inline-link { font-size: 12px; color: var(--primary); font-weight: 600; background: none; border: none; padding: 0; text-align: left; cursor: pointer; width: fit-content; }

                .task-controls { border: 1px solid var(--border); background: var(--card); border-radius: 10px; padding: 12px; display: grid; grid-template-columns: minmax(260px,1fr) 150px 150px auto auto auto; gap: 10px; align-items: center; }
                .task-control-input, .task-control-select { height: 36px; border: 1px solid var(--input); border-radius: 8px; padding: 0 10px; background: var(--background); color: var(--foreground); font-family: inherit; }
                .task-control-input::placeholder { color: var(--muted-foreground); }
                .task-toolbar-note { font-size: 12px; color: var(--muted-foreground); justify-self: end; }
                .task-toolbar-note b { color: var(--foreground); }

                .task-main-grid { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 12px; min-height: 0; }
                .task-table-wrap { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: var(--card); position: relative; }
                .task-scroll-hint { position: absolute; right: 10px; bottom: 8px; font-size: 11px; color: var(--muted-foreground); background: rgba(255,255,255,.88); border: 1px solid var(--border); border-radius: 999px; padding: 3px 8px; pointer-events: none; }
                .task-table-scroll { overflow: auto; max-height: calc(100vh - 330px); }
                .task-table { width: 100%; min-width: 1120px; border-collapse: collapse; font-size: 13px; }
                .task-table th { position: sticky; top: 0; z-index: 3; background: var(--muted); color: var(--muted-foreground); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; border-bottom: 1px solid var(--border); padding: 10px; white-space: nowrap; }
                .task-table th .th-content { display: inline-flex; align-items: center; gap: 4px; }
                .task-table th .th-sort { opacity: .45; font-size: 10px; }
                .task-table td { border-bottom: 1px solid var(--border); padding: 9px 10px; white-space: nowrap; }
                .task-sticky-col { position: sticky; left: 0; z-index: 2; background: var(--card); box-shadow: 8px 0 10px -10px rgba(15,23,42,.2); }
                .task-row:hover td, .task-row.selected td { background: var(--accent); }
                .task-row:hover .task-sticky-col, .task-row.selected .task-sticky-col { background: var(--accent); }

                .task-account-name { font-weight: 600; }
                .task-account-meta { font-size: 11px; color: var(--muted-foreground); }
                .task-pill { display: inline-flex; align-items: center; justify-content: center; min-width: 74px; border-radius: 999px; font-size: 11px; padding: 4px 8px; font-weight: 700; text-transform: uppercase; letter-spacing: .3px; }
                .task-status-pill.on-track { background: rgba(16,185,129,.12); color: #047857; }
                .task-status-pill.at-risk { background: rgba(245,158,11,.14); color: #b45309; }
                .task-status-pill.overdue { background: rgba(239,68,68,.14); color: #b91c1c; }
                .task-priority-pill.high { background: rgba(239,68,68,.12); color: #b91c1c; }
                .task-priority-pill.medium { background: rgba(245,158,11,.14); color: #b45309; }
                .task-priority-pill.low { background: rgba(16,185,129,.12); color: #047857; }

                .task-check { width: 16px; height: 16px; accent-color: var(--primary); cursor: pointer; }
                .task-progress-wrap { min-width: 140px; }
                .task-progress-bar { height: 6px; background: var(--muted); border-radius: 99px; overflow: hidden; margin-bottom: 4px; }
                .task-progress-fill { height: 100%; background: var(--primary); border-radius: 99px; }
                .task-progress-label { font-size: 11px; color: var(--muted-foreground); }

                .task-side-col { display: flex; flex-direction: column; gap: 12px; }
                .task-panel { border: 1px solid var(--border); background: var(--card); border-radius: 10px; padding: 12px; }
                .task-panel-title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
                .task-panel-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .7px; color: var(--muted-foreground); }
                .task-focus-item { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px dashed var(--border); }
                .task-focus-item:last-child { border-bottom: 0; padding-bottom: 0; }
                .task-focus-cta { border: 1px solid var(--border); border-radius: 6px; background: var(--background); color: var(--foreground); padding: 3px 8px; font-size: 11px; cursor: pointer; }
                .task-focus-sub { color: var(--muted-foreground); font-size: 11px; }
                .task-util-btn { width: 100%; margin-bottom: 8px; }
                .task-shortcut-float { position: absolute; right: 12px; top: 10px; }
                .task-shortcut-pop { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border); }
                .task-shortcut-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 12px; }
                .task-kbd { border: 1px solid var(--border); background: var(--muted); border-radius: 6px; padding: 2px 6px; font-size: 11px; font-family: var(--font-mono); }
            </style>

            <div class="task-page">
                <div class="task-stats-grid">
                    <div class="task-stat-card">
                        <div class="task-stat-label">Tổng account</div>
                        <div class="task-stat-value">${stats.totalAccounts}</div>
                        <div class="task-stat-sub">Quản lý checklist cho cụm account quy mô lớn.</div>
                    </div>
                    <div class="task-stat-card">
                        <div class="task-stat-label">Tiến độ checklist</div>
                        <div class="task-stat-value">${stats.doneTasks}/${stats.totalTasks}</div>
                        <div class="task-stat-sub">Tổng task đã hoàn thành trong ngày.</div>
                    </div>
                    <div class="task-stat-card">
                        <div class="task-stat-label">Account quá hạn</div>
                        <div class="task-stat-value" style="color:#b91c1c">${stats.overdue}</div>
                        <div class="task-stat-sub">Nên xử lý trước mốc reset gần nhất.</div>
                        <button class="task-inline-link" id="task-cta-overdue">Lọc ngay danh sách quá hạn →</button>
                    </div>
                    <div class="task-stat-card">
                        <div class="task-stat-label">Độ phủ tự động</div>
                        <div class="task-stat-value">${stats.coverage}%</div>
                        <div class="task-stat-sub">Mục tiêu: <b>${stats.target}%</b> · thiếu ${stats.gap}% để đạt chuẩn.</div>
                        <button class="task-inline-link" id="task-cta-low-coverage">Lọc account ưu tiên cao →</button>
                    </div>
                </div>

                <div class="task-controls">
                    <input id="task-search" class="task-control-input" placeholder="Tìm theo Account / Emulator / Nhóm phụ trách..." value="${this._search}" />
                    <select id="task-status-filter" class="task-control-select">
                        <option value="all" ${this._statusFilter === 'all' ? 'selected' : ''}>Tất cả trạng thái</option>
                        <option value="on-track" ${this._statusFilter === 'on-track' ? 'selected' : ''}>Đúng tiến độ</option>
                        <option value="at-risk" ${this._statusFilter === 'at-risk' ? 'selected' : ''}>Nguy cơ trễ</option>
                        <option value="overdue" ${this._statusFilter === 'overdue' ? 'selected' : ''}>Quá hạn</option>
                    </select>
                    <select id="task-priority-filter" class="task-control-select">
                        <option value="all" ${this._priorityFilter === 'all' ? 'selected' : ''}>Tất cả độ ưu tiên</option>
                        <option value="high" ${this._priorityFilter === 'high' ? 'selected' : ''}>Cao</option>
                        <option value="medium" ${this._priorityFilter === 'medium' ? 'selected' : ''}>Trung bình</option>
                        <option value="low" ${this._priorityFilter === 'low' ? 'selected' : ''}>Thấp</option>
                    </select>
                    <button class="btn btn-sm btn-default" id="task-mark-selected" ${selected ? '' : 'disabled'}>
                        Hoàn tất account đang chọn ${selected ? `(${selected.accountName})` : ''}
                    </button>
                    <button class="btn btn-sm btn-ghost" id="task-shortcuts-toggle">?</button>
                    <button class="btn btn-sm btn-outline" id="task-reset-view">Xóa bộ lọc</button>
                </div>

                <div class="task-main-grid">
                    <div class="task-table-wrap">
                        <div class="task-table-scroll" id="task-table-scroll">
                            <table class="task-table">
                                <thead>
                                    <tr>
                                        <th class="task-sticky-col"><span class="th-content">Account <span class="th-sort">↕</span></span></th>
                                        <th><span class="th-content">Trạng thái <span class="th-sort">↕</span></span></th>
                                        <th><span class="th-content">Ưu tiên <span class="th-sort">↕</span></span></th>
                                        ${this._checklistTemplates.map((item) => `<th title="${item.label}"><span class="th-content">${item.shortLabel}<span class="th-sort">↕</span></span></th>`).join('')}
                                        <th><span class="th-content">Tiến độ <span class="th-sort">↕</span></span></th>
                                        <th><span class="th-content">Ghi chú <span class="th-sort">↕</span></span></th>
                                        <th><span class="th-content">Reset <span class="th-sort">↕</span></span></th>
                                    </tr>
                                </thead>
                                <tbody id="task-tbody">${this._renderRows()}</tbody>
                            </table>
                        </div>
                        <div class="task-scroll-hint" id="task-scroll-hint">← Cuộn ngang để xem thêm cột →</div>
                    </div>

                    <div class="task-side-col">
                        <div class="task-panel">
                            <div class="task-panel-title-row">
                                <div class="task-panel-title">Cần ưu tiên hôm nay</div>
                            </div>
                            ${this._renderFocusItems()}
                            <div class="task-focus-sub" style="margin-top:8px;">Tỷ lệ hiển thị dạng <b>x/y task</b> = số task đã xong / tổng task ngày.</div>
                        </div>

                        <div class="task-panel">
                            <div class="task-panel-title-row">
                                <div class="task-panel-title">Tiện ích</div>
                            </div>
                            <button class="btn btn-sm btn-outline task-util-btn">Gán checklist mẫu theo nhóm</button>
                            <button class="btn btn-sm btn-outline task-util-btn">Sắp xếp theo giờ reset gần nhất</button>
                            <button class="btn btn-sm btn-outline task-util-btn">Xuất báo cáo ngày</button>
                            <button class="btn btn-sm btn-outline task-util-btn">Đánh dấu thiếu task quan trọng</button>

                            ${this._showShortcutHelp ? `
                            <div class="task-shortcut-pop">
                                <div class="task-panel-title" style="margin-bottom:8px;">Phím tắt</div>
                                <div class="task-shortcut-row"><span>Focus ô tìm kiếm</span><span class="task-kbd">/</span></div>
                                <div class="task-shortcut-row"><span>Chọn dòng kế tiếp / trước</span><span class="task-kbd">J / K</span></div>
                                <div class="task-shortcut-row"><span>Toggle task pending đầu</span><span class="task-kbd">Space</span></div>
                                <div class="task-shortcut-row"><span>Đánh dấu xong account chọn</span><span class="task-kbd">Ctrl + Enter</span></div>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    _renderRows() {
        if (!this._filteredAccounts.length) {
            return '<tr><td colspan="13" style="text-align:center;color:var(--muted-foreground);padding:16px">Không có account phù hợp bộ lọc hiện tại.</td></tr>';
        }

        return this._filteredAccounts.map((acc, index) => {
            const progress = this._getProgress(acc);
            const statusLabel = acc.status === 'on-track'
                ? 'Đúng tiến độ'
                : acc.status === 'at-risk'
                    ? 'Nguy cơ trễ'
                    : 'Quá hạn';

            return `
                <tr class="task-row ${index === this._selectedIndex ? 'selected' : ''}" data-id="${acc.id}">
                    <td class="task-sticky-col">
                        <div class="task-account-name">${acc.accountName}</div>
                        <div class="task-account-meta">${acc.emulator} · ${acc.owner} · ${acc.region}</div>
                    </td>
                    <td><span class="task-pill task-status-pill ${acc.status}">${statusLabel}</span></td>
                    <td>${this._renderPriorityBadge(acc.priority)}</td>
                    ${this._checklistTemplates.map((item) => `
                        <td>
                            <input class="task-check" type="checkbox" data-account-id="${acc.id}" data-key="${item.key}" title="${item.label}" ${acc.checks[item.key] ? 'checked' : ''}/>
                        </td>
                    `).join('')}
                    <td class="task-progress-wrap">
                        <div class="task-progress-bar"><div class="task-progress-fill" style="width:${progress.percent}%"></div></div>
                        <div class="task-progress-label">${progress.done}/${progress.total} task · ${progress.percent}%</div>
                    </td>
                    <td>${acc.note}</td>
                    <td class="text-mono">${acc.nextReset}</td>
                </tr>
            `;
        }).join('');
    },

    _renderFocusItems() {
        const focus = this._accounts
            .filter((acc) => acc.status !== 'on-track' || acc.priority === 'high')
            .slice(0, 5);

        return focus.map((acc) => {
            const progress = this._getProgress(acc);
            return `
                <div class="task-focus-item">
                    <div>
                        <div class="font-semibold">${acc.accountName}</div>
                        <div class="task-focus-sub">${progress.done}/${progress.total} task đã xong</div>
                    </div>
                    <button class="task-focus-cta" data-focus-id="${acc.id}">Xem</button>
                </div>
            `;
        }).join('');
    },

    _syncScrollHint() {
        const scroller = document.getElementById('task-table-scroll');
        const hint = document.getElementById('task-scroll-hint');
        if (!scroller || !hint) return;
        const hasOverflow = scroller.scrollWidth > scroller.clientWidth + 8;
        hint.style.display = hasOverflow ? 'inline-flex' : 'none';
        if (!hasOverflow) return;
        if (scroller.scrollLeft + scroller.clientWidth >= scroller.scrollWidth - 4) {
            hint.textContent = '← Đã tới cột cuối';
        } else if (scroller.scrollLeft <= 2) {
            hint.textContent = '← Cuộn ngang để xem thêm cột →';
        } else {
            hint.textContent = '← Còn cột ở 2 phía →';
        }
    },

    _renderBodyOnly() {
        this._applyFilters();
        const tbody = document.getElementById('task-tbody');
        if (tbody) tbody.innerHTML = this._renderRows();

        const selected = this._filteredAccounts[this._selectedIndex];
        const markBtn = document.getElementById('task-mark-selected');
        if (markBtn) {
            markBtn.disabled = !selected;
            markBtn.textContent = selected
                ? `Hoàn tất account đang chọn (${selected.accountName})`
                : 'Hoàn tất account đang chọn';
        }
    },

    _selectByDelta(delta) {
        if (!this._filteredAccounts.length) return;
        this._selectedIndex = Math.max(0, Math.min(this._filteredAccounts.length - 1, this._selectedIndex + delta));
        this._renderBodyOnly();
    },

    _selectById(id) {
        const idx = this._filteredAccounts.findIndex((acc) => acc.id === id);
        if (idx >= 0) {
            this._selectedIndex = idx;
            this._renderBodyOnly();
        }
    },

    _toggleFirstPendingForSelected() {
        const selected = this._filteredAccounts[this._selectedIndex];
        if (!selected) return;
        const firstPending = this._checklistTemplates.find((item) => !selected.checks[item.key]);
        const key = firstPending ? firstPending.key : this._checklistTemplates[0].key;
        selected.checks[key] = !selected.checks[key];
        this._renderBodyOnly();
    },

    init() {
        const searchEl = document.getElementById('task-search');
        const statusEl = document.getElementById('task-status-filter');
        const priorityEl = document.getElementById('task-priority-filter');
        const tableScroll = document.getElementById('task-table-scroll');

        searchEl?.addEventListener('input', (e) => {
            this._search = e.target.value;
            this._selectedIndex = 0;
            this._renderBodyOnly();
        });

        statusEl?.addEventListener('change', (e) => {
            this._statusFilter = e.target.value;
            this._selectedIndex = 0;
            this._renderBodyOnly();
        });

        priorityEl?.addEventListener('change', (e) => {
            this._priorityFilter = e.target.value;
            this._selectedIndex = 0;
            this._renderBodyOnly();
        });

        document.getElementById('task-cta-overdue')?.addEventListener('click', () => {
            this._statusFilter = 'overdue';
            if (statusEl) statusEl.value = 'overdue';
            this._selectedIndex = 0;
            this._renderBodyOnly();
        });

        document.getElementById('task-cta-low-coverage')?.addEventListener('click', () => {
            this._priorityFilter = 'high';
            if (priorityEl) priorityEl.value = 'high';
            this._selectedIndex = 0;
            this._renderBodyOnly();
        });

        document.getElementById('task-shortcuts-toggle')?.addEventListener('click', () => {
            this._showShortcutHelp = !this._showShortcutHelp;
            router.navigate('task');
        });

        document.getElementById('task-tbody')?.addEventListener('click', (e) => {
            const row = e.target.closest('.task-row');
            if (!row) return;
            const id = Number(row.getAttribute('data-id'));
            this._selectById(id);
        });

        document.querySelectorAll('[data-focus-id]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const id = Number(btn.getAttribute('data-focus-id'));
                const idx = this._filteredAccounts.findIndex((acc) => acc.id === id);
                if (idx === -1) {
                    this._statusFilter = 'all';
                    if (statusEl) statusEl.value = 'all';
                    this._priorityFilter = 'all';
                    if (priorityEl) priorityEl.value = 'all';
                    this._renderBodyOnly();
                }
                this._selectById(id);
            });
        });

        document.getElementById('task-tbody')?.addEventListener('change', (e) => {
            const checkbox = e.target.closest('.task-check');
            if (!checkbox) return;
            const accountId = Number(checkbox.getAttribute('data-account-id'));
            const key = checkbox.getAttribute('data-key');
            const account = this._accounts.find((acc) => acc.id === accountId);
            if (account && key in account.checks) account.checks[key] = checkbox.checked;
            this._renderBodyOnly();
        });

        document.getElementById('task-mark-selected')?.addEventListener('click', () => {
            const selected = this._filteredAccounts[this._selectedIndex];
            if (!selected) return;
            this._checklistTemplates.forEach((item) => {
                selected.checks[item.key] = true;
            });
            this._renderBodyOnly();
        });

        document.getElementById('task-reset-view')?.addEventListener('click', () => {
            this._search = '';
            this._statusFilter = 'all';
            this._priorityFilter = 'all';
            this._selectedIndex = 0;
            if (searchEl) searchEl.value = '';
            if (statusEl) statusEl.value = 'all';
            if (priorityEl) priorityEl.value = 'all';
            this._renderBodyOnly();
        });

        tableScroll?.addEventListener('scroll', () => this._syncScrollHint());
        window.requestAnimationFrame(() => this._syncScrollHint());

        this._boundKeydown = (e) => {
            if (router._currentPage !== 'task') return;
            if (e.key === '/') {
                e.preventDefault();
                document.getElementById('task-search')?.focus();
            } else if (e.key.toLowerCase() === 'j') {
                e.preventDefault();
                this._selectByDelta(1);
            } else if (e.key.toLowerCase() === 'k') {
                e.preventDefault();
                this._selectByDelta(-1);
            } else if (e.code === 'Space') {
                e.preventDefault();
                this._toggleFirstPendingForSelected();
            } else if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('task-mark-selected')?.click();
            }
        };

        document.addEventListener('keydown', this._boundKeydown);
    },

    destroy() {
        if (this._boundKeydown) {
            document.removeEventListener('keydown', this._boundKeydown);
            this._boundKeydown = null;
        }
    },
};
