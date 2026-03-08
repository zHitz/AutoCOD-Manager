const TaskPage = {
    _accounts: [],
    _filteredAccounts: [],
    _selectedIndex: 0,
    _search: '',
    _statusFilter: 'all',
    _priorityFilter: 'all',
    _showShortcutHelp: false,
    _boundKeydown: null,
    _isLoading: false,
    _hasLoadedRealData: false,
    _wsSetup: false,

    _selectedDate: new Date().toISOString().slice(0, 10),
    _selectedGroupId: '',
    _groups: [],
    _activityRegistry: [],
    _checklistTemplates: [],
    _summary: {},
    _showSettingsPanel: false,
    _page: 1,
    _pageSize: 50,
    _pagination: { page: 1, page_size: 50, total_accounts: 0, total_pages: 0 },
    _wsPatchQueue: new Map(),
    _wsPatchTimer: null,

    async _loadRealData() {
        this._isLoading = true;
        try {
            const dateStr = this._selectedDate;
            const groupParam = this._selectedGroupId ? `&group_id=${this._selectedGroupId}` : '';
            const pagingParam = `&page=${this._page}&page_size=${this._pageSize}`;

            const [checklistRes, registryRes, allAccounts, groupsRes, templatesRes] = await Promise.all([
                fetch(`/api/task/checklist?date=${dateStr}${groupParam}${pagingParam}`).then((res) => (res.ok ? res.json() : {})),
                fetch('/api/workflow/activity-registry').then((res) => (res.ok ? res.json() : {})),
                fetch('/api/accounts').then((res) => (res.ok ? res.json() : [])),
                fetch('/api/groups').then((res) => (res.ok ? res.json() : {})),
                fetch('/api/task/checklist/templates').then((res) => (res.ok ? res.json() : {}))
            ]);

            this._activityRegistry = Array.isArray(registryRes.data) ? registryRes.data : [];
            this._groups = Array.isArray(groupsRes.data) ? groupsRes.data : [];

            // Extract templates
            const items = templatesRes.items || [];
            if (items.length > 0) {
                const regMap = new Map(this._activityRegistry.map(a => [a.id, a.name]));
                this._checklistTemplates = items.map(t => ({
                    key: t.activity_id,
                    label: regMap.get(t.activity_id) || t.activity_id,
                    shortLabel: regMap.get(t.activity_id) || t.activity_id,
                    critical: t.is_critical === 1
                }));
            } else {
                // Fallback default
                this._checklistTemplates = [
                    { key: 'login', label: 'Daily login', shortLabel: 'Daily login', critical: true },
                    { key: 'collect', label: 'Collect resources', shortLabel: 'Collect resources', critical: true },
                    { key: 'alliance', label: 'Alliance donation', shortLabel: 'Alliance', critical: false },
                    { key: 'patrol', label: 'Patrol', shortLabel: 'Patrol', critical: false },
                    { key: 'full_scan', label: 'Full Scan', shortLabel: 'Full Scan', critical: true },
                ];
            }

            const accountsArray = Array.isArray(allAccounts) ? allAccounts : [];
            const accountMetaMap = new Map(accountsArray.map(a => [Number(a.account_id || a.id), a]));

            const checklistMap = new Map(
                (checklistRes.accounts || []).map(a => [a.account_id, a])
            );

            const pagedAccountIds = (checklistRes.accounts || []).map(a => Number(a.account_id));

            this._accounts = pagedAccountIds
                .map((id, index) => {
                    const checklistAcc = checklistMap.get(id) || {};
                    const metaAcc = accountMetaMap.get(id) || {};
                    return this._mapFromChecklist({ ...metaAcc, ...checklistAcc, account_id: id }, checklistAcc, index);
                });

            this._summary = checklistRes.summary || {};
            this._pagination = checklistRes.pagination || this._pagination;
            this._page = Number(this._pagination.page || this._page);
            this._pageSize = Number(this._pagination.page_size || this._pageSize);
            this._hasLoadedRealData = true;
        } catch (error) {
            console.warn('[TaskPage] Failed to load data:', error);
            this._accounts = [];
            this._pagination = { page: this._page, page_size: this._pageSize, total_accounts: 0, total_pages: 0 };
            this._hasLoadedRealData = true;
        } finally {
            this._isLoading = false;
        }
    },

    _mapFromChecklist(account, checklistData, index) {
        const gameId = account?.game_id || '';
        const activities = checklistData?.activities || {};

        // Derive progress from template items only
        let doneCount = 0;
        let totalCount = this._checklistTemplates.length;

        this._checklistTemplates.forEach(t => {
            const act = activities[t.key];
            if (act && act.status === 'SUCCESS') doneCount++;
        });

        // Derive generic status
        let status = 'on-track';
        if (doneCount === 0 && totalCount > 0) status = 'overdue';
        else if (doneCount < totalCount) status = 'at-risk';

        let priority = 'low';
        if (status === 'overdue') priority = 'high';
        else if (status === 'at-risk') priority = 'medium';

        return {
            id: Number(account?.account_id || account?.id || index + 1),
            accountName: account?.lord_name || gameId || `Account-${index + 1}`,
            gameId: gameId,
            emulator: account?.emu_name || account?.serial || '--',
            owner: account?.alliance || 'Unassigned team',
            region: account?.provider || 'Global',
            priority,
            status,
            activities,
            progress: { done: doneCount, total: totalCount },
            note: account?.note || 'Loaded from API',
            nextReset: this._deriveResetTime(account?.provider),
        };
    },

    _deriveResetTime(provider) {
        const regionMap = { Asia: '00:00', EU: '07:00', Global: '05:00' };
        return regionMap[provider] || '05:00';
    },

    _computeStats() {
        const totalAccounts = this._accounts.length;
        let doneTasks = 0;
        let totalTasks = 0;
        let overdue = 0;

        this._accounts.forEach((acc) => {
            doneTasks += acc.progress.done;
            totalTasks += acc.progress.total;
            if (acc.status === 'overdue') overdue += 1;
        });

        const coverage = totalTasks ? Math.round((doneTasks / totalTasks) * 100) : 0;
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
        const map = { high: 'High', medium: 'Medium', low: 'Low' };
        return `<span class="task-pill task-priority-pill ${priority}">${map[priority] || priority}</span>`;
    },

    _renderCellStatus(status) {
        if (!status) return `<span style="opacity:0.3;font-size:14px;">☐</span>`;
        if (status === 'SUCCESS') return `<span style="color:var(--primary);font-size:14px;">✅</span>`;
        if (status === 'RUNNING' || status === 'PENDING') return `<span style="color:var(--accent-foreground);font-size:14px;" class="spinner-inline">⏳</span>`;
        if (status === 'FAILED') return `<span style="color:#b91c1c;font-size:14px;">❌</span>`;
        return `<span style="opacity:0.3;font-size:14px;">☐</span>`;
    },

    _renderSettingsPanel() {
        if (!this._showSettingsPanel) return '';

        const templateSet = new Set(this._checklistTemplates.map(t => t.key));
        const checkboxes = this._activityRegistry.map(act => `
            <label class="setting-row" style="margin:0;padding:6px;border:1px solid var(--border);border-radius:6px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;width:100%;">
                <input type="checkbox" class="task-setting-checkbox" value="${act.id}" ${templateSet.has(act.id) ? 'checked' : ''}/>
                <span class="form-label" style="margin:0;font-size:11px;">${act.name || act.id}</span>
            </label>
        `).join('');

        return `
            <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:16px;">
                <div style="font-weight:600;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
                    <span>⚙️ Configure Column Templates</span>
                    <button class="btn btn-sm btn-ghost" id="task-settings-close">✕</button>
                </div>
                <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(180px, 1fr));gap:8px;">
                    ${checkboxes}
                </div>
                <div style="margin-top:16px;display:flex;justify-content:flex-end;">
                    <button class="btn btn-sm btn-default" id="task-settings-save">Save Template</button>
                </div>
            </div>
        `;
    },

    render() {
        this._applyFilters();
        const stats = this._computeStats();

        return `
            <style>
                .task-page { display: flex; flex-direction: column; gap: 16px; }
                .task-stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
                .task-stat-card { border: 1px solid var(--border); background: var(--card); border-radius: 10px; padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; }
                .task-stat-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.7px; color: var(--muted-foreground); font-weight: 600; }
                .task-stat-value { font-size: 24px; font-weight: 700; letter-spacing: -0.02em; }
                .task-stat-sub { font-size: 12px; color: var(--muted-foreground); }
                .task-inline-link { font-size: 12px; color: var(--primary); font-weight: 600; background: none; border: none; padding: 0; text-align: left; cursor: pointer; width: fit-content; }

                .task-controls { border: 1px solid var(--border); background: var(--card); border-radius: 10px; padding: 12px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
                .task-control-input, .task-control-select { height: 36px; border: 1px solid var(--input); border-radius: 8px; padding: 0 10px; background: var(--background); color: var(--foreground); font-family: inherit; font-size: 13px; }
                .task-control-input::placeholder { color: var(--muted-foreground); }

                .task-main-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; min-height: 0; }
                .task-table-wrap { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: var(--card); position: relative; }
                .task-scroll-hint { position: absolute; right: 10px; bottom: 8px; font-size: 11px; color: var(--muted-foreground); background: rgba(255,255,255,.88); border: 1px solid var(--border); border-radius: 999px; padding: 3px 8px; pointer-events: none; }
                .task-table-scroll { overflow: auto; max-height: calc(100vh - 330px); }
                .task-table { width: 100%; min-width: 1120px; border-collapse: collapse; font-size: 13px; }
                .task-table th { position: sticky; top: 0; z-index: 3; background: var(--muted); color: var(--muted-foreground); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; border-bottom: 1px solid var(--border); padding: 10px; white-space: nowrap; }
                .task-table th .th-content { display: inline-flex; align-items: center; gap: 4px; }
                .task-table td { border-bottom: 1px solid var(--border); padding: 9px 10px; white-space: nowrap; text-align: center;}
                .task-table td:nth-child(1), .task-table td:nth-child(2), .task-table td:nth-child(3) { text-align: left; }
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

                .task-clickable-cell { cursor: pointer; user-select: none; }
                .task-clickable-cell:hover { opacity: 0.7; }
                
                .spinner-inline { display: inline-block; animation: spin 1s linear infinite; }
                @keyframes spin { 100% { transform: rotate(360deg); } }
            </style>

            <div class="task-page">
                <div class="task-stats-grid">
                    <div class="task-stat-card">
                        <div class="task-stat-label">Total accounts</div>
                        <div class="task-stat-value">${stats.totalAccounts}</div>
                        <div class="task-stat-sub">Checklist tracking across your account fleet.</div>
                    </div>
                    <div class="task-stat-card">
                        <div class="task-stat-label">Checklist progress</div>
                        <div class="task-stat-value">${stats.doneTasks}/${stats.totalTasks}</div>
                        <div class="task-stat-sub">Total completed tasks for today.</div>
                    </div>
                    <div class="task-stat-card">
                        <div class="task-stat-label">Overdue accounts</div>
                        <div class="task-stat-value" style="color:#b91c1c">${stats.overdue}</div>
                        <div class="task-stat-sub">Handle these before the next reset window.</div>
                    </div>
                    <div class="task-stat-card">
                        <div class="task-stat-label">Automation coverage</div>
                        <div class="task-stat-value">${stats.coverage}%</div>
                        <div class="task-stat-sub">Target: <b>${stats.target}%</b> · ${stats.gap}% remaining.</div>
                    </div>
                </div>

                <div class="task-controls">
                    <input type="date" id="task-date-picker" class="task-control-input" value="${this._selectedDate}" title="Select Date" />
                    
                    <select id="task-group-filter" class="task-control-select">
                        <option value="">All Groups</option>
                        ${this._groups.map(g => `<option value="${g.id}" ${this._selectedGroupId == g.id ? 'selected' : ''}>${g.name}</option>`).join('')}
                    </select>

                    <input id="task-search" class="task-control-input" placeholder="Search by Account / Emulator / Owner..." value="${this._search}" style="flex:1" />
                    <select id="task-status-filter" class="task-control-select">
                        <option value="all" ${this._statusFilter === 'all' ? 'selected' : ''}>All statuses</option>
                        <option value="on-track" ${this._statusFilter === 'on-track' ? 'selected' : ''}>On track</option>
                        <option value="at-risk" ${this._statusFilter === 'at-risk' ? 'selected' : ''}>At risk</option>
                        <option value="overdue" ${this._statusFilter === 'overdue' ? 'selected' : ''}>Overdue</option>
                    </select>
                    
                    <button class="btn btn-sm btn-ghost" id="task-settings-toggle" title="Configure Columns">⚙️</button>
                    <button class="btn btn-sm btn-outline" id="task-reset-view">Clear filters</button>
                    <div style="display:flex;align-items:center;gap:6px;margin-left:auto;">
                        <button class="btn btn-sm btn-ghost" id="task-prev-page" ${this._page <= 1 ? 'disabled' : ''}>← Prev</button>
                        <span style="font-size:12px;color:var(--muted-foreground);">Page ${this._page}/${Math.max(this._pagination.total_pages || 1, 1)}</span>
                        <button class="btn btn-sm btn-ghost" id="task-next-page" ${this._page >= (this._pagination.total_pages || 1) ? 'disabled' : ''}>Next →</button>
                    </div>
                </div>

                ${this._renderSettingsPanel()}

                <div class="task-main-grid">
                    <div class="task-table-wrap">
                        <div class="task-table-scroll" id="task-table-scroll">
                            <table class="task-table">
                                <thead>
                                    <tr>
                                        <th class="task-sticky-col"><span class="th-content">Account</span></th>
                                        <th><span class="th-content">Status</span></th>
                                        <th><span class="th-content">Priority</span></th>
                                        ${this._checklistTemplates.map((item) => `<th><span class="th-content">${item.shortLabel}</span></th>`).join('')}
                                        <th><span class="th-content">Progress</span></th>
                                        <th><span class="th-content">Note</span></th>
                                    </tr>
                                </thead>
                                <tbody id="task-tbody">${this._renderGrid()}</tbody>
                            </table>
                        </div>
                        <div class="task-scroll-hint" id="task-scroll-hint">← Scroll horizontally to see more columns →</div>
                    </div>
                </div>
            </div>
        `;
    },

    _normalizeDomPart(value) {
        return String(value).replace(/[^a-zA-Z0-9_-]/g, '_');
    },

    _rowId(accountId) {
        return `row-account-${this._normalizeDomPart(accountId)}`;
    },

    _cellId(accountId, activityId) {
        return `cell-${this._normalizeDomPart(accountId)}-${this._normalizeDomPart(activityId)}`;
    },

    _renderCell(accountId, activityId, state = '') {
        return `
            <td
                id="${this._cellId(accountId, activityId)}"
                class="task-clickable-cell"
                data-acc-id="${accountId}"
                data-act-id="${activityId}"
                data-status="${state}"
                title="Click to mark done/undo"
            >
                ${this._renderCellStatus(state)}
            </td>`;
    },

    _renderRow(acc, index) {
        const progress = acc.progress;
        const percent = progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0;
        const statusLabel = acc.status === 'on-track' ? 'On track' : acc.status === 'at-risk' ? 'At risk' : 'Overdue';

        return `
            <tr id="${this._rowId(acc.id)}" class="task-row ${index === this._selectedIndex ? 'selected' : ''}" data-id="${acc.id}">
                <td class="task-sticky-col">
                    <div class="task-account-name">${acc.accountName}</div>
                    <div class="task-account-meta">${acc.emulator} · ${acc.owner} · ${acc.region}</div>
                </td>
                <td><span id="row-status-${this._normalizeDomPart(acc.id)}" class="task-pill task-status-pill ${acc.status}">${statusLabel}</span></td>
                <td id="row-priority-${this._normalizeDomPart(acc.id)}">${this._renderPriorityBadge(acc.priority)}</td>
                ${this._checklistTemplates.map((item) => {
                    const actStatus = acc.activities[item.key]?.status || '';
                    return this._renderCell(acc.id, item.key, actStatus);
                }).join('')}
                <td id="row-progress-${this._normalizeDomPart(acc.id)}" class="task-progress-wrap" style="text-align:left;">
                    <div style="height:6px;background:var(--muted);border-radius:99px;margin-bottom:4px;"><div style="height:100%;background:var(--primary);border-radius:99px;width:${percent}%"></div></div>
                    <div style="font-size:11px;color:var(--muted-foreground);">${progress.done}/${progress.total} tasks · ${percent}%</div>
                </td>
                <td style="text-align:left;">${acc.note}</td>
            </tr>
        `;
    },

    _renderGrid() {
        if (!this._filteredAccounts.length) {
            return '<tr><td colspan="15" style="text-align:center;color:var(--muted-foreground);padding:16px">No accounts match the current filters.</td></tr>';
        }

        return this._filteredAccounts.map((acc, index) => this._renderRow(acc, index)).join('');
    },

    _syncScrollHint() {
        const scroller = document.getElementById('task-table-scroll');
        const hint = document.getElementById('task-scroll-hint');
        if (!scroller || !hint) return;
        const hasOverflow = scroller.scrollWidth > scroller.clientWidth + 8;
        hint.style.display = hasOverflow ? 'inline-flex' : 'none';
        if (!hasOverflow) return;
        if (scroller.scrollLeft + scroller.clientWidth >= scroller.scrollWidth - 4) {
            hint.textContent = '← Reached last column';
        } else if (scroller.scrollLeft <= 2) {
            hint.textContent = '← Scroll horizontally to see more columns →';
        } else {
            hint.textContent = '← More columns on both sides →';
        }
    },

    _renderBodyOnly() {
        this._applyFilters();
        const tbody = document.getElementById('task-tbody');
        const t0 = performance.now();
        const html = this._renderGrid();
        if (tbody) tbody.innerHTML = html;
        console.log('TASK_GRID_RENDER ms=', Math.round((performance.now() - t0) * 100) / 100);
        setTimeout(() => this._syncScrollHint(), 50);
    },

    _patchCell(accId, actId, newState) {
        const cell = document.getElementById(this._cellId(accId, actId));
        if (!cell) return false;
        const normalized = newState || '';
        if ((cell.dataset.status || '') === normalized) return false;
        cell.dataset.status = normalized;
        cell.innerHTML = this._renderCellStatus(normalized);
        return true;
    },

    _updateRowStats(accId) {
        const acc = this._accounts.find(a => a.id === accId);
        if (!acc) return;

        const total = this._checklistTemplates.length;
        let done = 0;
        let failed = 0;

        this._checklistTemplates.forEach(t => {
            const s = acc.activities[t.key]?.status || '';
            if (s === 'SUCCESS') done += 1;
            if (s === 'FAILED') failed += 1;
        });

        acc.progress = { done, total };
        acc.failed = failed;

        let status = 'on-track';
        if (done === 0 && total > 0) status = 'overdue';
        else if (done < total) status = 'at-risk';
        acc.status = status;

        let priority = 'low';
        if (status === 'overdue') priority = 'high';
        else if (status === 'at-risk') priority = 'medium';
        acc.priority = priority;

        const percent = total > 0 ? Math.round((done / total) * 100) : 0;
        const statusEl = document.getElementById(`row-status-${this._normalizeDomPart(accId)}`);
        if (statusEl) {
            const statusLabel = status === 'on-track' ? 'On track' : status === 'at-risk' ? 'At risk' : 'Overdue';
            statusEl.className = `task-pill task-status-pill ${status}`;
            statusEl.textContent = statusLabel;
        }

        const priorityEl = document.getElementById(`row-priority-${this._normalizeDomPart(accId)}`);
        if (priorityEl) priorityEl.innerHTML = this._renderPriorityBadge(priority);

        const progressEl = document.getElementById(`row-progress-${this._normalizeDomPart(accId)}`);
        if (progressEl) {
            progressEl.innerHTML = `
                <div style="height:6px;background:var(--muted);border-radius:99px;margin-bottom:4px;"><div style="height:100%;background:var(--primary);border-radius:99px;width:${percent}%"></div></div>
                <div style="font-size:11px;color:var(--muted-foreground);">${done}/${total} tasks · ${percent}%</div>
            `;
        }
    },

    _enqueuePatch(payload) {
        if (!payload || !payload.account_id || !payload.activity_id) return;
        const key = `${payload.account_id}::${payload.activity_id}`;
        this._wsPatchQueue.set(key, payload);

        if (this._wsPatchTimer) return;
        this._wsPatchTimer = setTimeout(() => this._flushPatchQueue(), 100);
    },

    _flushPatchQueue() {
        const pending = Array.from(this._wsPatchQueue.values());
        this._wsPatchQueue.clear();
        this._wsPatchTimer = null;
        if (!pending.length) return;

        console.log(`TASK_GRID_PATCH batch=${pending.length}`);

        pending.forEach((p) => {
            const accId = Number(p.account_id);
            const actId = p.activity_id;
            const status = p.status || '';

            const acc = this._accounts.find(a => a.id === accId);
            if (acc) {
                if (!acc.activities[actId]) acc.activities[actId] = {};
                acc.activities[actId].status = status;
                if (typeof p.runs_today !== 'undefined') acc.activities[actId].runs_today = p.runs_today;
                if (typeof p.last_run !== 'undefined') acc.activities[actId].last_run = p.last_run;
                if (typeof p.error !== 'undefined') acc.activities[actId].error = p.error || '';
            }

            const changed = this._patchCell(accId, actId, status);
            if (changed) this._updateRowStats(accId);
        });
    },

    _setupWebSockets() {
        if (this._wsSetup || !window.EventBus) return;

        window.EventBus.on('task_state_update', (data) => {
            if (router._currentPage !== 'task') return;
            this._enqueuePatch(data);
        });

        ['activity_started', 'activity_completed', 'activity_failed'].forEach(evt => {
            window.EventBus.on(evt, (data) => {
                if (router._currentPage !== 'task') return; // only process when active
                let mappedStatus = 'SUCCESS';
                if (evt === 'activity_started') mappedStatus = 'RUNNING';
                else if (evt === 'activity_failed') mappedStatus = 'FAILED';

                const accId = data.account_id ? Number(data.account_id) : null;
                const actId = data.activity_id;

                if (accId && actId) {
                    this._enqueuePatch({
                        account_id: accId,
                        activity_id: actId,
                        status: mappedStatus,
                        runs_today: data.runs_today,
                        last_run: data.last_run,
                        error: data.error
                    });
                }
            });
        });
        this._wsSetup = true;
    },

    async _toggleActivityStatus(accId, actId, currentStatus, gameId) {
        const newStatus = currentStatus === 'SUCCESS' ? 'UNDO' : 'SUCCESS';

        // Optimistic UI update
        const acc = this._accounts.find(a => a.id === accId);
        if (acc) {
            if (!acc.activities[actId]) acc.activities[actId] = {};
            acc.activities[actId].status = newStatus === 'UNDO' ? '' : 'SUCCESS';
            this._renderBodyOnly();
        }

        try {
            const res = await fetch('/api/task/checklist/mark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    account_id: accId,
                    activity_id: actId,
                    status: newStatus,
                    game_id: gameId
                })
            });
            if (!res.ok) throw new Error('Failed to mark');
        } catch (e) {
            console.error(e);
            if (window.Toast) Toast.error('Error', 'Failed to update activity status');
            // Revert changes
            if (acc) {
                acc.activities[actId].status = currentStatus;
                this._renderBodyOnly();
            }
        }
    },

    async _saveTemplate() {
        const checked = Array.from(document.querySelectorAll('.task-setting-checkbox:checked')).map(el => el.value);
        try {
            await fetch('/api/task/checklist/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: 'Default Template',
                    scope: 'org',
                    scope_id: 0,
                    items: checked.map((id, idx) => ({ activity_id: id, sort_order: idx, is_critical: 0 }))
                })
            });
            if (window.Toast) Toast.success('Saved', 'Template saved successfully');
            this._showSettingsPanel = false;
            await this._loadRealData();
            router.navigate('task');
        } catch (e) {
            console.error(e);
            if (window.Toast) Toast.error('Error', 'Failed to save template');
        }
    },

    async init() {
        await this._loadRealData();
        this._setupWebSockets();

        if (!this._hasLoadedRealData) {
            router.navigate('task');
            return;
        }

        const addListener = (id, event, handler) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener(event, handler);
        };

        addListener('task-date-picker', 'change', async (e) => {
            this._selectedDate = e.target.value;
            this._page = 1;
            await this._loadRealData();
            router.navigate('task');
        });

        addListener('task-group-filter', 'change', async (e) => {
            this._selectedGroupId = e.target.value;
            this._page = 1;
            await this._loadRealData();
            router.navigate('task');
        });

        addListener('task-search', 'input', (e) => {
            this._search = e.target.value;
            this._selectedIndex = 0;
            this._renderBodyOnly();
        });

        addListener('task-status-filter', 'change', (e) => {
            this._statusFilter = e.target.value;
            this._selectedIndex = 0;
            this._renderBodyOnly();
        });

        addListener('task-priority-filter', 'change', (e) => {
            this._priorityFilter = e.target.value;
            this._selectedIndex = 0;
            this._renderBodyOnly();
        });

        addListener('task-reset-view', 'click', () => {
            this._search = '';
            this._statusFilter = 'all';
            this._priorityFilter = 'all';
            this._selectedIndex = 0;

            const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
            setVal('task-search', '');
            setVal('task-status-filter', 'all');
            setVal('task-priority-filter', 'all');
            this._renderBodyOnly();
        });

        addListener('task-prev-page', 'click', async () => {
            if (this._page <= 1) return;
            this._page -= 1;
            await this._loadRealData();
            router.navigate('task');
        });

        addListener('task-next-page', 'click', async () => {
            const totalPages = this._pagination?.total_pages || 1;
            if (this._page >= totalPages) return;
            this._page += 1;
            await this._loadRealData();
            router.navigate('task');
        });

        addListener('task-settings-toggle', 'click', () => {
            this._showSettingsPanel = !this._showSettingsPanel;
            router.navigate('task');
        });

        addListener('task-settings-close', 'click', () => {
            this._showSettingsPanel = false;
            router.navigate('task');
        });

        addListener('task-settings-save', 'click', () => {
            this._saveTemplate();
        });

        const tbody = document.getElementById('task-tbody');
        if (tbody) {
            tbody.addEventListener('click', (e) => {
                const cell = e.target.closest('.task-clickable-cell');
                if (cell) {
                    const accId = Number(cell.dataset.accId);
                    const actId = cell.dataset.actId;
                    const status = cell.dataset.status;
                    const gameId = (this._accounts.find(a => a.id === accId) || {}).gameId;
                    if (accId && actId) {
                        this._toggleActivityStatus(accId, actId, status, gameId);
                    }
                }
            });
        }

        const tableScroll = document.getElementById('task-table-scroll');
        if (tableScroll) tableScroll.addEventListener('scroll', () => this._syncScrollHint());
        window.requestAnimationFrame(() => this._syncScrollHint());
    },

    destroy() { }
};
