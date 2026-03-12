function getLocalDateInputValue(date = new Date()) {
    const offsetMs = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offsetMs).toISOString().slice(0, 10);
}

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
    _loadError: '',

    _selectedDate: getLocalDateInputValue(),
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

    async _safeFetchJson(url, fallbackValue) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return { ok: true, data: await response.json() };
        } catch (error) {
            console.warn(`[TaskPage] Request failed for ${url}:`, error);
            return { ok: false, data: fallbackValue, error };
        }
    },

    _getGroupAccountIds(group) {
        const raw = group?.account_ids;
        if (Array.isArray(raw)) return raw.map(Number).filter(Boolean);
        if (typeof raw === 'string' && raw.trim()) {
            try {
                const parsed = JSON.parse(raw);
                return Array.isArray(parsed) ? parsed.map(Number).filter(Boolean) : [];
            } catch (error) {
                console.warn('[TaskPage] Failed to parse group account_ids:', error);
            }
        }
        return [];
    },
    _formatDateTime(value) {
        if (!value) return '--';
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
    },

    _formatDuration(ms) {
        const totalMs = Number(ms || 0);
        if (!totalMs) return '--';
        if (totalMs < 1000) return `${totalMs} ms`;
        const totalSeconds = Math.round(totalMs / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        if (!minutes) return `${seconds}s`;
        return `${minutes}m ${seconds}s`;
    },

    _escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    _closeHistoryPanel() {
        if (this._historyPanelEl) {
            this._historyPanelEl.remove();
            this._historyPanelEl = null;
        }
        if (this._historyOverlayEl) {
            this._historyOverlayEl.remove();
            this._historyOverlayEl = null;
        }
    },
    _renderHistoryPanelContent(account, payload = {}, loading = false, error = '') {
        const summary = payload.summary || {};
        const activityStats = Array.isArray(payload.activity_stats) ? payload.activity_stats : [];
        const items = Array.isArray(payload.items) ? payload.items : [];
        const visibleLatestError = summary.latest_error && summary.latest_error.toLowerCase() !== 'unknown execution failure'
            ? summary.latest_error
            : '';

        const summaryCards = [
            { label: 'Total runs', value: summary.total_runs || 0, cls: '' },
            { label: 'Success', value: summary.success_count || 0, cls: 'th-stat-success' },
            { label: 'Failed', value: summary.failed_count || 0, cls: 'th-stat-failed' },
            { label: 'Avg duration', value: this._formatDuration(summary.avg_duration_ms), cls: '' },
            { label: 'Last run', value: this._formatDateTime(summary.last_run), cls: 'th-stat-compact' }
        ];

        const summaryHtml = `
            <div class="th-stat-grid">
                ${summaryCards.map((c) => `
                    <div class="th-stat-card ${c.cls}">
                        <div class="th-stat-label">${this._escapeHtml(c.label)}</div>
                        <div class="th-stat-value">${this._escapeHtml(c.value)}</div>
                    </div>
                `).join('')}
            </div>`;

        const breakdownHtml = loading
            ? '<div class="th-empty-state"><span class="spinner"></span> Loading activity history...</div>'
            : error
                ? `<div class="th-error-inline">${this._escapeHtml(error)}</div>`
                : activityStats.length
                    ? `<div class="th-card-list">${activityStats.map((stat) => {
                        const statusCls = stat.last_status === 'FAILED' ? 'overdue' : stat.last_status === 'SUCCESS' ? 'on-track' : 'at-risk';
                        return `
                        <div class="th-breakdown-card">
                            <div class="th-breakdown-header">
                                <div>
                                    <div class="th-breakdown-name">${this._escapeHtml(stat.activity_name || stat.activity_id)}</div>
                                    <div class="th-breakdown-id">ID: ${this._escapeHtml(stat.activity_id || '--')}</div>
                                </div>
                                <span class="task-pill task-status-pill ${statusCls}">${this._escapeHtml(stat.last_status || '--')}</span>
                            </div>
                            <div class="th-mini-stats">
                                <div class="th-mini-stat"><div class="th-mini-stat-label">Runs</div><div class="th-mini-stat-value">${stat.total_runs || 0}</div></div>
                                <div class="th-mini-stat"><div class="th-mini-stat-label">Success</div><div class="th-mini-stat-value th-text-success">${stat.success_count || 0}</div></div>
                                <div class="th-mini-stat"><div class="th-mini-stat-label">Failed</div><div class="th-mini-stat-value th-text-failed">${stat.failed_count || 0}</div></div>
                                <div class="th-mini-stat"><div class="th-mini-stat-label">Avg duration</div><div class="th-mini-stat-value">${this._escapeHtml(this._formatDuration(stat.avg_duration_ms))}</div></div>
                                <div class="th-mini-stat"><div class="th-mini-stat-label">Last run</div><div class="th-mini-stat-value th-mini-stat-compact">${this._escapeHtml(this._formatDateTime(stat.last_run))}</div></div>
                            </div>
                        </div>`;
                    }).join('')}</div>`
                    : '<div class="th-empty-state">No activity history for the selected date.</div>';

        const timelineHtml = loading
            ? '<div class="th-empty-state"><span class="spinner"></span> Loading execution timeline...</div>'
            : error
                ? `<div class="th-error-inline">${this._escapeHtml(error)}</div>`
                : items.length
                    ? items.map((item) => {
                        const metadata = this._escapeHtml(JSON.stringify(item.metadata || {}, null, 2));
                        const result = this._escapeHtml(JSON.stringify(item.result || {}, null, 2));
                        const statusCls = item.status === 'FAILED' ? 'overdue' : item.status === 'SUCCESS' ? 'on-track' : 'at-risk';
                        const borderColor = item.status === 'FAILED' ? 'var(--red-500)' : item.status === 'SUCCESS' ? 'var(--emerald-500)' : 'var(--orange-500)';
                        return `
                            <div class="th-timeline-item" style="border-left-color:${borderColor};">
                                <div class="th-timeline-header">
                                    <div class="th-timeline-info">
                                        <div class="th-timeline-name">${this._escapeHtml(item.activity_name || item.activity_id)}</div>
                                        <div class="th-timeline-meta">${this._escapeHtml(item.run_id || '--')} · ${this._escapeHtml(item.source || '--')} · attempts ${item.attempts || 1}</div>
                                    </div>
                                    <span class="task-pill task-status-pill ${statusCls}">${this._escapeHtml(item.status || '--')}</span>
                                </div>
                                <div class="th-timeline-stats">
                                    <div class="th-mini-stat"><div class="th-mini-stat-label">Started</div><div class="th-mini-stat-value th-mini-stat-compact">${this._escapeHtml(this._formatDateTime(item.started_at))}</div></div>
                                    <div class="th-mini-stat"><div class="th-mini-stat-label">Finished</div><div class="th-mini-stat-value th-mini-stat-compact">${this._escapeHtml(this._formatDateTime(item.finished_at))}</div></div>
                                    <div class="th-mini-stat"><div class="th-mini-stat-label">Duration</div><div class="th-mini-stat-value th-mini-stat-compact">${this._escapeHtml(this._formatDuration(item.duration_ms))}</div></div>
                                </div>
                                ${item.error_message ? `<div class="th-error-banner"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> ${this._escapeHtml(item.error_message)}</div>` : ''}
                                <details class="th-details">
                                    <summary class="th-details-summary">
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="6 9 12 15 18 9"/></svg>
                                        Show metadata & result
                                    </summary>
                                    <div class="th-details-grid">
                                        <div>
                                            <div class="th-details-label">Metadata</div>
                                            <pre class="th-details-pre">${metadata}</pre>
                                        </div>
                                        <div>
                                            <div class="th-details-label">Result</div>
                                            <pre class="th-details-pre">${result}</pre>
                                        </div>
                                    </div>
                                </details>
                            </div>`;
                    }).join('')
                    : '<div class="th-empty-state">No activity runs for this account on the selected date.</div>';

        return `
            <div class="th-panel-header">
                <div class="th-panel-header-info">
                    <div class="th-panel-title">${this._escapeHtml(account.accountName || account.lord_name || 'Activity history')}</div>
                    <div class="th-panel-subtitle">${this._escapeHtml(account.gameId || account.game_id || '--')} · ${this._escapeHtml(account.emulator || account.emulator_name || '--')} · ${this._escapeHtml(this._selectedDate)}</div>
                </div>
                <button class="th-close-btn" id="task-history-close" title="Close panel">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <div class="th-panel-body">
                ${summaryHtml}
                ${visibleLatestError ? `<div class="th-error-banner"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> ${this._escapeHtml(visibleLatestError)}</div>` : ''}
                <div class="th-tab-bar">
                    <button class="th-tab active" data-history-tab="timeline">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                        Execution timeline
                    </button>
                    <button class="th-tab" data-history-tab="breakdown">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                        Activity breakdown
                    </button>
                </div>
                <section data-history-panel="timeline" class="th-tab-panel active">
                    <div class="th-card-list">${timelineHtml}</div>
                </section>
                <section data-history-panel="breakdown" class="th-tab-panel">
                    ${breakdownHtml}
                </section>
            </div>`;
    },

    _mountHistoryPanel(account, payload = {}, loading = false, error = '') {
        this._closeHistoryPanel();

        const overlay = document.createElement('div');
        overlay.id = 'task-history-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,.38);z-index:50;backdrop-filter:blur(4px);';
        overlay.addEventListener('click', () => this._closeHistoryPanel());

        const panel = document.createElement('aside');
        panel.id = 'task-history-panel';
        panel.style.cssText = 'position:fixed;top:0;right:0;width:min(980px,96vw);height:100vh;background:var(--background);z-index:51;box-shadow:-24px 0 60px rgba(15,23,42,.18);display:flex;flex-direction:column;border-left:1px solid var(--border);';
        panel.innerHTML = this._renderHistoryPanelContent(account, payload, loading, error);

        document.body.appendChild(overlay);
        document.body.appendChild(panel);

        this._historyOverlayEl = overlay;
        this._historyPanelEl = panel;

        const closeBtn = document.getElementById('task-history-close');
        if (closeBtn) closeBtn.addEventListener('click', () => this._closeHistoryPanel());

        const tabButtons = Array.from(panel.querySelectorAll('[data-history-tab]'));
        const tabPanels = Array.from(panel.querySelectorAll('[data-history-panel]'));
        tabButtons.forEach((button) => {
            button.addEventListener('click', () => {
                const nextTab = button.dataset.historyTab;
                tabButtons.forEach((btn) => btn.classList.toggle('active', btn.dataset.historyTab === nextTab));
                tabPanels.forEach((section) => section.classList.toggle('active', section.dataset.historyPanel === nextTab));
            });
        });
    },

    async _openHistoryPanel(accId) {
        const account = this._accounts.find(a => a.id === accId);
        if (!account) return;

        this._mountHistoryPanel(account, {}, true, '');

        try {
            const response = await fetch(`/api/task/account-history?account_id=${accId}&date=${this._selectedDate}&limit=100`);
            const payload = await response.json();
            if (!response.ok || payload.status === 'error') {
                throw new Error(payload.error || 'Failed to load activity history');
            }
            this._mountHistoryPanel({ ...account, ...(payload.account || {}) }, payload, false, '');
        } catch (fetchError) {
            console.error('[TaskPage] Failed to open history panel:', fetchError);
            this._mountHistoryPanel(account, {}, false, fetchError?.message || 'Failed to load activity history');
        }
    },

    async _loadRealData() {
        this._isLoading = true;
        this._loadError = '';
        try {
            const dateStr = this._selectedDate;
            const groupParam = this._selectedGroupId ? `&group_id=${this._selectedGroupId}` : '';
            const pagingParam = `&page=${this._page}&page_size=${this._pageSize}`;

            const [checklistResult, registryResult, accountsResult, groupsResult, templatesResult] = await Promise.all([
                this._safeFetchJson(`/api/task/checklist?date=${dateStr}${groupParam}${pagingParam}`, {}),
                this._safeFetchJson('/api/workflow/activity-registry', {}),
                this._safeFetchJson('/api/accounts', []),
                this._safeFetchJson('/api/groups', []),
                this._safeFetchJson('/api/task/checklist/templates', {})
            ]);

            const checklistRes = checklistResult.data || {};
            const registryRes = registryResult.data || {};
            const allAccounts = accountsResult.data || [];
            const groupsRes = groupsResult.data || [];
            const templatesRes = templatesResult.data || {};

            if (checklistRes.status === 'error') {
                throw new Error(checklistRes.error || 'Checklist API returned an error');
            }
            if (registryRes.status === 'error') {
                throw new Error(registryRes.error || 'Activity registry API returned an error');
            }

            this._activityRegistry = Array.isArray(registryRes.data) ? registryRes.data : [];
            this._groups = Array.isArray(groupsRes) ? groupsRes : Array.isArray(groupsRes.data) ? groupsRes.data : [];

            const items = templatesRes.items || [];
            if (items.length > 0) {
                const regMap = new Map(this._activityRegistry.map(a => [a.id, a.name]));
                this._checklistTemplates = items.map(t => ({
                    key: t.activity_id,
                    label: regMap.get(t.activity_id) || t.activity_id,
                    shortLabel: regMap.get(t.activity_id) || t.activity_id,
                    critical: t.is_critical === 1,
                    requiredRuns: t.required_runs || 1
                }));
            } else {
                this._checklistTemplates = this._activityRegistry.map(act => ({
                    key: act.id,
                    label: act.name || act.id,
                    shortLabel: act.name || act.id,
                    critical: !!act.is_critical,
                    requiredRuns: 1
                }));
            }

            const accountsArray = Array.isArray(allAccounts) ? allAccounts : [];
            const accountIds = accountsArray.map(a => Number(a.account_id || a.id)).filter(Boolean);
            const accountMetaMap = new Map(accountsArray.map(a => [Number(a.account_id || a.id), a]));
            const checklistAccounts = Array.isArray(checklistRes.accounts) ? checklistRes.accounts : [];
            const checklistIds = checklistAccounts.map(a => Number(a.account_id)).filter(Boolean);
            const checklistMap = new Map(checklistAccounts.map(a => [Number(a.account_id), a]));
            const allKnownIds = Array.from(new Set([...accountIds, ...checklistIds]));

            let visibleIds = allKnownIds;
            if (this._selectedGroupId) {
                const selectedGroup = this._groups.find(g => String(g.id) === String(this._selectedGroupId));
                const groupAccountIds = new Set(this._getGroupAccountIds(selectedGroup));
                visibleIds = allKnownIds.filter(id => groupAccountIds.has(id));
            }

            this._accounts = visibleIds
                .sort((a, b) => a - b)
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
            this._loadError = error?.message || 'Failed to load task checklist data';
            this._pagination = { page: this._page, page_size: this._pageSize, total_accounts: 0, total_pages: 0 };
            this._hasLoadedRealData = true;
        } finally {
            this._isLoading = false;
        }
    },

    _mapFromChecklist(account, checklistData, index) {
        const gameId = account?.game_id || '';
        const activities = checklistData?.activities || {};

        // Always derive totals from the checklist templates (the actual tracked activities).
        // Backend stats.total only counts activities with execution logs, which is 0
        // when no runs have occurred yet — causing the "0/0" dashboard bug.
        const totalCount = this._checklistTemplates.length;
        let doneCount = 0;
        let failedCount = 0;

        this._checklistTemplates.forEach(t => {
            const act = activities[t.key];
            if (!act) return;
            const runsToday = act.runs_today || (act.status === 'SUCCESS' ? 1 : 0);
            const needed = t.requiredRuns || 1;
            if (runsToday >= needed) doneCount++;
            if (act.status === 'FAILED') failedCount++;
        });

        let status = 'on-track';
        if (totalCount > 0) {
            if (doneCount === 0) status = 'overdue';
            else if (doneCount < totalCount || failedCount > 0) status = 'at-risk';
        }

        let priority = 'low';
        if (status === 'overdue') priority = 'high';
        else if (status === 'at-risk') priority = 'medium';

        return {
            id: Number(account?.account_id || account?.id || index + 1),
            accountName: account?.lord_name || gameId || `Account-${index + 1}`,
            gameId: gameId,
            emulator: account?.emulator_name || account?.emu_name || account?.serial || '--',
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

    _openSettingsModal() {
        if (document.getElementById('ts-modal-overlay')) return;

        const templateMap = new Map(this._checklistTemplates.map(t => [t.key, t]));

        const activityCards = this._activityRegistry.map((act, i) => {
            const tmpl = templateMap.get(act.id);
            const checked = !!tmpl;
            const runs = tmpl ? (tmpl.requiredRuns || 1) : 1;
            return `
                <div class="ts-activity-card">
                    <label class="ts-toggle-row">
                        <input type="checkbox" class="ts-act-check" value="${act.id}" ${checked ? 'checked' : ''} />
                        <div class="ts-act-info">
                            <div class="ts-act-name">${this._escapeHtml(act.name || act.id)}</div>
                            <div class="ts-act-id">${this._escapeHtml(act.id)}</div>
                        </div>
                    </label>
                    <div class="ts-runs-control">
                        <label class="ts-runs-label">Required runs</label>
                        <input type="number" class="ts-runs-input" data-act-id="${act.id}" value="${runs}" min="1" max="99" />
                    </div>
                </div>`;
        }).join('');

        const html = `
            <div id="ts-modal-overlay" class="ts-overlay">
                <div class="ts-modal">
                    <div class="ts-header">
                        <div>
                            <div class="ts-title">Task Checklist Settings</div>
                            <div class="ts-subtitle">Configure which activities to track and their KPI targets.</div>
                        </div>
                        <button class="th-close-btn" id="ts-modal-close" title="Close">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                        </button>
                    </div>
                    <div class="ts-note">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                        Per-group templates coming soon. Current settings apply to all accounts.
                    </div>
                    <div class="ts-body">
                        ${activityCards}
                    </div>
                    <div class="ts-footer">
                        <button class="btn btn-sm btn-ghost" id="ts-modal-cancel">Cancel</button>
                        <button class="btn btn-sm btn-default" id="ts-modal-save">Save Settings</button>
                    </div>
                </div>
            </div>`;

        document.body.insertAdjacentHTML('beforeend', html);

        document.getElementById('ts-modal-close')?.addEventListener('click', () => this._closeSettingsModal());
        document.getElementById('ts-modal-cancel')?.addEventListener('click', () => this._closeSettingsModal());
        document.getElementById('ts-modal-save')?.addEventListener('click', () => this._saveTemplate());
        document.getElementById('ts-modal-overlay')?.addEventListener('click', (e) => {
            if (e.target.id === 'ts-modal-overlay') this._closeSettingsModal();
        });
    },

    _closeSettingsModal() {
        document.getElementById('ts-modal-overlay')?.remove();
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

                /* ── History Panel (th- prefix) ── */
                .th-panel-header {
                    padding: 20px 24px 16px;
                    border-bottom: 1px solid var(--border);
                    display: flex;
                    justify-content: space-between;
                    gap: 16px;
                    align-items: flex-start;
                    background: var(--card);
                    flex-shrink: 0;
                }
                .th-panel-header-info { min-width: 0; }
                .th-panel-title { font-size: 22px; font-weight: 800; letter-spacing: -.03em; line-height: 1.2; word-break: break-word; }
                .th-panel-subtitle { font-size: 12px; color: var(--muted-foreground); margin-top: 6px; line-height: 1.6; word-break: break-word; }
                .th-close-btn {
                    flex: 0 0 auto;
                    width: 32px; height: 32px;
                    display: flex; align-items: center; justify-content: center;
                    border-radius: var(--radius-md);
                    border: 1px solid var(--border);
                    background: var(--card);
                    color: var(--muted-foreground);
                    cursor: pointer;
                    transition: all var(--duration-fast);
                }
                .th-close-btn:hover { background: var(--destructive); color: #fff; border-color: var(--destructive); }

                .th-panel-body {
                    padding: 18px 24px 28px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    background: var(--background);
                    flex: 1;
                }

                /* Stat cards */
                .th-stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; }
                .th-stat-card {
                    border: 1px solid var(--border);
                    border-radius: var(--radius-lg);
                    padding: 12px 14px;
                    background: var(--card);
                    transition: box-shadow var(--duration-fast);
                }
                .th-stat-card:hover { box-shadow: var(--shadow-sm); }
                .th-stat-label { font-size: 10px; color: var(--muted-foreground); text-transform: uppercase; letter-spacing: .08em; font-weight: 600; }
                .th-stat-value { font-size: 26px; font-weight: 800; line-height: 1.2; margin-top: 6px; color: var(--foreground); }
                .th-stat-success .th-stat-value { color: var(--emerald-500); }
                .th-stat-failed .th-stat-value { color: var(--red-500); }
                .th-stat-compact .th-stat-value { font-size: 13px; font-weight: 700; line-height: 1.5; }

                /* Tab bar */
                .th-tab-bar {
                    display: flex;
                    gap: 4px;
                    padding: 3px;
                    background: var(--muted);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-lg);
                    width: max-content;
                    max-width: 100%;
                }
                .th-tab {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 7px 14px;
                    border: none;
                    background: transparent;
                    color: var(--muted-foreground);
                    font-size: 12px;
                    font-weight: 600;
                    font-family: var(--font-sans);
                    border-radius: calc(var(--radius-lg) - 2px);
                    cursor: pointer;
                    white-space: nowrap;
                    transition: all var(--duration-fast);
                }
                .th-tab:hover { color: var(--foreground); }
                .th-tab.active {
                    background: var(--card);
                    color: var(--foreground);
                    box-shadow: var(--shadow-sm);
                }
                .th-tab svg { flex-shrink: 0; }

                .th-tab-panel { display: none; }
                .th-tab-panel.active { display: block; }

                /* Card list (shared) */
                .th-card-list { display: flex; flex-direction: column; gap: 10px; }
                .th-empty-state { padding: 24px 18px; color: var(--muted-foreground); font-size: 13px; text-align: center; }
                .th-error-inline { padding: 18px; color: var(--red-500); font-size: 13px; }

                /* Error banner */
                .th-error-banner {
                    display: flex;
                    align-items: flex-start;
                    gap: 8px;
                    border: 1px solid rgba(239,68,68,.18);
                    background: rgba(239,68,68,.05);
                    color: #991b1b;
                    border-radius: var(--radius-lg);
                    padding: 10px 14px;
                    font-size: 12px;
                    line-height: 1.5;
                }
                .th-error-banner svg { flex-shrink: 0; margin-top: 1px; }

                /* Timeline items */
                .th-timeline-item {
                    border: 1px solid var(--border);
                    border-left: 3px solid var(--border);
                    border-radius: var(--radius-lg);
                    padding: 14px 16px;
                    background: var(--card);
                    transition: box-shadow var(--duration-fast);
                }
                .th-timeline-item:hover { box-shadow: var(--shadow-sm); }
                .th-timeline-header { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; flex-wrap: wrap; }
                .th-timeline-info { min-width: 0; }
                .th-timeline-name { font-weight: 700; font-size: 13px; }
                .th-timeline-meta { font-size: 11px; color: var(--muted-foreground); margin-top: 4px; line-height: 1.6; word-break: break-word; font-family: var(--font-mono); }
                .th-timeline-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 12px; }

                /* Mini stats (shared between timeline and breakdown) */
                .th-mini-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; margin-top: 12px; }
                .th-mini-stat-label { font-size: 10px; color: var(--muted-foreground); text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }
                .th-mini-stat-value { font-size: 17px; font-weight: 800; margin-top: 3px; }
                .th-mini-stat-compact { font-size: 12px; font-weight: 700; line-height: 1.5; }
                .th-text-success { color: var(--emerald-500); }
                .th-text-failed { color: var(--red-500); }

                /* Breakdown cards */
                .th-breakdown-card {
                    border: 1px solid var(--border);
                    border-radius: var(--radius-lg);
                    background: var(--card);
                    padding: 14px 16px;
                    transition: box-shadow var(--duration-fast);
                }
                .th-breakdown-card:hover { box-shadow: var(--shadow-sm); }
                .th-breakdown-header { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; flex-wrap: wrap; }
                .th-breakdown-name { font-weight: 700; font-size: 13px; }
                .th-breakdown-id { font-size: 11px; color: var(--muted-foreground); margin-top: 3px; font-family: var(--font-mono); }

                /* Details accordion */
                .th-details { margin-top: 12px; }
                .th-details-summary {
                    cursor: pointer;
                    font-size: 12px;
                    color: var(--indigo-500);
                    font-weight: 700;
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    user-select: none;
                    transition: color var(--duration-fast);
                }
                .th-details-summary:hover { color: var(--indigo-600); }
                .th-details-summary svg { flex-shrink: 0; transition: transform var(--duration-fast); }
                details[open] > .th-details-summary svg { transform: rotate(180deg); }
                .th-details-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-top: 10px; }
                .th-details-label { font-size: 11px; font-weight: 700; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted-foreground); }
                .th-details-pre {
                    margin: 0;
                    white-space: pre-wrap;
                    word-break: break-word;
                    background: var(--muted);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-md);
                    padding: 10px;
                    font-family: var(--font-mono);
                    font-size: 11px;
                    max-height: 220px;
                    overflow: auto;
                    line-height: 1.5;
                }

                /* -- Settings Modal (ts- prefix) -- */
                .ts-overlay {
                    position: fixed; inset: 0;
                    background: rgba(15,23,42,.45);
                    backdrop-filter: blur(4px);
                    z-index: 60;
                    display: flex; align-items: center; justify-content: center;
                    animation: ts-fadeIn var(--duration-fast) ease-out;
                }
                @keyframes ts-fadeIn { from { opacity: 0; } to { opacity: 1; } }
                .ts-modal {
                    background: var(--card);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-xl);
                    width: min(640px, 92vw);
                    max-height: 85vh;
                    display: flex; flex-direction: column;
                    animation: ts-slideUp var(--duration-normal) ease-out;
                }
                @keyframes ts-slideUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
                .ts-header {
                    padding: 20px 24px 16px;
                    border-bottom: 1px solid var(--border);
                    display: flex; justify-content: space-between; gap: 16px; align-items: flex-start;
                    flex-shrink: 0;
                }
                .ts-title { font-size: 18px; font-weight: 800; letter-spacing: -.02em; }
                .ts-subtitle { font-size: 12px; color: var(--muted-foreground); margin-top: 4px; }
                .ts-note {
                    margin: 16px 24px 0;
                    display: flex; align-items: center; gap: 8px;
                    padding: 10px 14px;
                    background: rgba(59,130,246,.06);
                    border: 1px solid rgba(59,130,246,.15);
                    border-radius: var(--radius-md);
                    font-size: 12px; color: var(--info);
                    flex-shrink: 0;
                }
                .ts-note svg { flex-shrink: 0; }
                .ts-body {
                    padding: 16px 24px;
                    overflow-y: auto;
                    display: flex; flex-direction: column; gap: 8px;
                    flex: 1;
                }
                .ts-activity-card {
                    border: 1px solid var(--border);
                    border-radius: var(--radius-md);
                    padding: 10px 14px;
                    display: flex; justify-content: space-between; align-items: center; gap: 12px;
                    transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
                }
                .ts-activity-card:hover { border-color: var(--ring); box-shadow: var(--shadow-sm); }
                .ts-toggle-row {
                    display: flex; align-items: center; gap: 10px;
                    cursor: pointer; min-width: 0; flex: 1;
                }
                .ts-toggle-row input[type="checkbox"] {
                    width: 16px; height: 16px;
                    accent-color: var(--indigo-500);
                    flex-shrink: 0; cursor: pointer;
                }
                .ts-act-info { min-width: 0; }
                .ts-act-name { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
                .ts-act-id { font-size: 10px; color: var(--muted-foreground); font-family: var(--font-mono); margin-top: 1px; }
                .ts-runs-control {
                    display: flex; align-items: center; gap: 8px;
                    flex-shrink: 0;
                }
                .ts-runs-label { font-size: 10px; color: var(--muted-foreground); text-transform: uppercase; letter-spacing: .06em; white-space: nowrap; font-weight: 600; }
                .ts-runs-input {
                    width: 52px; height: 30px;
                    border: 1px solid var(--input);
                    border-radius: var(--radius-sm);
                    padding: 0 8px;
                    font-family: var(--font-mono);
                    font-size: 13px; font-weight: 700;
                    text-align: center;
                    background: var(--background);
                    color: var(--foreground);
                    transition: border-color var(--duration-fast);
                }
                .ts-runs-input:focus { outline: none; border-color: var(--ring); box-shadow: 0 0 0 2px rgba(99,102,241,.15); }
                .ts-footer {
                    padding: 14px 24px;
                    border-top: 1px solid var(--border);
                    display: flex; justify-content: flex-end; gap: 8px;
                    flex-shrink: 0;
                }
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

                <!-- Settings is now a modal popup -->

                <div class="task-main-grid">
                    <div class="task-table-wrap">
                        <div class="task-table-scroll" id="task-table-scroll">
                            <table class="task-table">
                                <thead>
                                    <tr id="task-thead-row">
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
                    <button class="task-account-open" data-account-open="${acc.id}" style="background:none;border:none;padding:0;color:inherit;font:inherit;font-weight:600;cursor:pointer;text-align:left;">${acc.accountName}</button>
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
        const totalColumns = this._checklistTemplates.length + 5;

        if (this._isLoading) {
            return `<tr><td colspan="${totalColumns}" style="text-align:center;color:var(--muted-foreground);padding:16px">Loading task checklist...</td></tr>`;
        }

        if (this._loadError && !this._filteredAccounts.length) {
            return `<tr><td colspan="${totalColumns}" style="text-align:center;color:#b91c1c;padding:16px">${this._loadError}</td></tr>`;
        }

        if (!this._filteredAccounts.length) {
            return `<tr><td colspan="${totalColumns}" style="text-align:center;color:var(--muted-foreground);padding:16px">No accounts match the current filters.</td></tr>`;
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

    _syncThead() {
        const theadRow = document.getElementById('task-thead-row');
        if (!theadRow) return;
        theadRow.innerHTML = `
            <th class="task-sticky-col"><span class="th-content">Account</span></th>
            <th><span class="th-content">Status</span></th>
            <th><span class="th-content">Priority</span></th>
            ${this._checklistTemplates.map((item) => `<th><span class="th-content">${item.shortLabel}</span></th>`).join('')}
            <th><span class="th-content">Progress</span></th>
            <th><span class="th-content">Note</span></th>
        `;
    },

    _renderBodyOnly() {
        this._applyFilters();
        this._syncThead();
        const tbody = document.getElementById('task-tbody');
        if (tbody) {
            tbody.innerHTML = this._renderGrid();
            tbody.addEventListener('click', (e) => {
                const accountTrigger = e.target.closest('.task-account-open');
                if (accountTrigger) {
                    const accId = Number(accountTrigger.dataset.accountOpen);
                    if (accId) this._openHistoryPanel(accId);
                    return;
                }

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

    async _toggleActivityStatus(accId, actId, currentStatus, gameId) {
        const newStatus = currentStatus === 'SUCCESS' ? 'UNDO' : 'SUCCESS';
        try {
            const res = await fetch('/api/task/checklist/mark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ account_id: accId, activity_id: actId, status: newStatus, game_id: gameId || '' }),
            });
            const result = await res.json();
            if (result.status === 'ok') {
                await this._reloadAndRender();
            } else {
                console.warn('[TaskPage] Mark failed:', result.error);
            }
        } catch (err) {
            console.error('[TaskPage] Toggle activity error:', err);
        }
    },

    async _reloadAndRender() {
        await this._loadRealData();
        this._renderBodyOnly();
        this._refreshStats();
    },

    _refreshStats() {
        const stats = this._computeStats();
        const root = document.querySelector('.task-stats-grid');
        if (!root) return;
        const values = root.querySelectorAll('.task-stat-value');
        if (values[0]) values[0].textContent = stats.totalAccounts;
        if (values[1]) values[1].textContent = `${stats.doneTasks}/${stats.totalTasks}`;
        if (values[2]) values[2].textContent = stats.overdue;
        if (values[3]) values[3].textContent = `${stats.coverage}%`;
        const subs = root.querySelectorAll('.task-stat-sub');
        if (subs[3]) subs[3].innerHTML = `Target: <b>${stats.target}%</b> · ${stats.gap}% remaining.`;
    },

    async _saveTemplate() {
        const checks = Array.from(document.querySelectorAll('.ts-act-check:checked')).map(cb => cb.value);
        const runsInputs = document.querySelectorAll('.ts-runs-input');
        const runsMap = new Map();
        runsInputs.forEach(inp => runsMap.set(inp.dataset.actId, Math.max(1, parseInt(inp.value) || 1)));
        const items = checks.map((id, i) => ({
            activity_id: id,
            sort_order: i,
            is_critical: 0,
            required_runs: runsMap.get(id) || 1
        }));
        try {
            await fetch('/api/task/checklist/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'Default Strategy', scope: 'org', scope_id: 0, items }),
            });
            this._closeSettingsModal();
            await this._reloadAndRender();
        } catch (err) {
            console.error('[TaskPage] Save template error:', err);
        }
    },

    async init() {
        await this._loadRealData();
        this._renderBodyOnly();
        this._refreshStats();

        // Date picker
        const datePicker = document.getElementById('task-date-picker');
        if (datePicker) datePicker.addEventListener('change', (e) => {
            this._selectedDate = e.target.value;
            this._page = 1;
            this._reloadAndRender();
        });

        // Group filter
        const groupFilter = document.getElementById('task-group-filter');
        if (groupFilter) groupFilter.addEventListener('change', (e) => {
            this._selectedGroupId = e.target.value;
            this._page = 1;
            this._reloadAndRender();
        });

        // Search
        const searchInput = document.getElementById('task-search');
        if (searchInput) searchInput.addEventListener('input', (e) => {
            this._search = e.target.value;
            this._renderBodyOnly();
        });

        // Status filter
        const statusFilter = document.getElementById('task-status-filter');
        if (statusFilter) statusFilter.addEventListener('change', (e) => {
            this._statusFilter = e.target.value;
            this._renderBodyOnly();
        });

        // Clear filters
        const resetBtn = document.getElementById('task-reset-view');
        if (resetBtn) resetBtn.addEventListener('click', () => {
            this._search = '';
            this._statusFilter = 'all';
            this._priorityFilter = 'all';
            if (searchInput) searchInput.value = '';
            if (statusFilter) statusFilter.value = 'all';
            this._renderBodyOnly();
        });

        // Pagination
        const prevBtn = document.getElementById('task-prev-page');
        const nextBtn = document.getElementById('task-next-page');
        if (prevBtn) prevBtn.addEventListener('click', () => {
            if (this._page > 1) { this._page--; this._reloadAndRender(); }
        });
        if (nextBtn) nextBtn.addEventListener('click', () => {
            if (this._page < (this._pagination.total_pages || 1)) { this._page++; this._reloadAndRender(); }
        });

        // Settings toggle -- open modal
        const settingsToggle = document.getElementById('task-settings-toggle');
        if (settingsToggle) settingsToggle.addEventListener('click', () => {
            const existing = document.getElementById('ts-modal-overlay');
            if (existing) { this._closeSettingsModal(); return; }
            this._openSettingsModal();
        });
    },

    destroy() {
        this._closeHistoryPanel();
    }
};
