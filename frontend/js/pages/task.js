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
            { label: 'Total runs', value: summary.total_runs || 0, tone: 'var(--foreground)' },
            { label: 'Success', value: summary.success_count || 0, tone: '#047857' },
            { label: 'Failed', value: summary.failed_count || 0, tone: '#b91c1c' },
            { label: 'Avg duration', value: this._formatDuration(summary.avg_duration_ms), tone: 'var(--foreground)' },
            { label: 'Last run', value: this._formatDateTime(summary.last_run), tone: 'var(--foreground)', compact: true }
        ];

        const summaryHtml = `
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;">
                ${summaryCards.map((card) => `
                    <div style="border:1px solid var(--border);border-radius:16px;padding:14px 16px;background:linear-gradient(180deg,var(--card),rgba(148,163,184,.04));min-height:92px;">
                        <div style="font-size:11px;color:var(--muted-foreground);text-transform:uppercase;letter-spacing:.08em;">${this._escapeHtml(card.label)}</div>
                        <div style="font-size:${card.compact ? '13px' : '28px'};font-weight:800;line-height:${card.compact ? '1.5' : '1.2'};margin-top:8px;color:${card.tone};word-break:break-word;">${this._escapeHtml(card.value)}</div>
                    </div>
                `).join('')}
            </div>
        `;

        const breakdownHtml = loading
            ? '<div style="padding:18px;color:var(--muted-foreground);">Loading activity history...</div>'
            : error
                ? `<div style="padding:18px;color:#b91c1c;">${this._escapeHtml(error)}</div>`
                : activityStats.length
                    ? `<div style="display:flex;flex-direction:column;gap:10px;">${activityStats.map((stat) => `
                        <div style="border:1px solid var(--border);border-radius:14px;background:var(--card);padding:14px 16px;">
                            <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap;">
                                <div>
                                    <div style="font-weight:800;font-size:14px;">${this._escapeHtml(stat.activity_name || stat.activity_id)}</div>
                                    <div style="font-size:11px;color:var(--muted-foreground);margin-top:4px;">ID: ${this._escapeHtml(stat.activity_id || '--')}</div>
                                </div>
                                <span class="task-pill task-status-pill ${stat.last_status === 'FAILED' ? 'overdue' : stat.last_status === 'SUCCESS' ? 'on-track' : 'at-risk'}">${this._escapeHtml(stat.last_status || '--')}</span>
                            </div>
                            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin-top:12px;">
                                <div><div style="font-size:11px;color:var(--muted-foreground);">Runs</div><div style="font-size:18px;font-weight:800;margin-top:4px;">${stat.total_runs || 0}</div></div>
                                <div><div style="font-size:11px;color:var(--muted-foreground);">Success</div><div style="font-size:18px;font-weight:800;margin-top:4px;color:#047857;">${stat.success_count || 0}</div></div>
                                <div><div style="font-size:11px;color:var(--muted-foreground);">Failed</div><div style="font-size:18px;font-weight:800;margin-top:4px;color:#b91c1c;">${stat.failed_count || 0}</div></div>
                                <div><div style="font-size:11px;color:var(--muted-foreground);">Avg duration</div><div style="font-size:18px;font-weight:800;margin-top:4px;">${this._escapeHtml(this._formatDuration(stat.avg_duration_ms))}</div></div>
                                <div><div style="font-size:11px;color:var(--muted-foreground);">Last run</div><div style="font-size:12px;font-weight:700;line-height:1.5;margin-top:4px;">${this._escapeHtml(this._formatDateTime(stat.last_run))}</div></div>
                            </div>
                        </div>
                    `).join('')}</div>`
                    : '<div style="padding:18px;color:var(--muted-foreground);">No activity history for the selected date.</div>';

        const timelineHtml = loading
            ? '<div style="padding:18px;color:var(--muted-foreground);">Loading execution timeline...</div>'
            : error
                ? `<div style="padding:18px;color:#b91c1c;">${this._escapeHtml(error)}</div>`
                : items.length
                    ? items.map((item) => {
                        const metadata = this._escapeHtml(JSON.stringify(item.metadata || {}, null, 2));
                        const result = this._escapeHtml(JSON.stringify(item.result || {}, null, 2));
                        const errorHtml = item.error_message
                            ? `<div style="margin-top:10px;padding:10px 12px;border-radius:12px;background:rgba(185,28,28,.06);border:1px solid rgba(185,28,28,.14);color:#991b1b;font-size:12px;line-height:1.5;"><b>Error:</b> ${this._escapeHtml(item.error_message)}</div>`
                            : '';
                        const statusClass = item.status === 'FAILED' ? 'overdue' : item.status === 'SUCCESS' ? 'on-track' : 'at-risk';
                        return `
                            <div style="border:1px solid var(--border);border-radius:16px;padding:14px 16px;background:linear-gradient(180deg,var(--card),rgba(148,163,184,.03));">
                                <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap;">
                                    <div>
                                        <div style="font-weight:800;font-size:14px;">${this._escapeHtml(item.activity_name || item.activity_id)}</div>
                                        <div style="font-size:11px;color:var(--muted-foreground);margin-top:5px;line-height:1.6;word-break:break-word;">Run ${this._escapeHtml(item.run_id || '--')} | ${this._escapeHtml(item.source || '--')} | attempts ${item.attempts || 1}</div>
                                    </div>
                                    <span class="task-pill task-status-pill ${statusClass}">${this._escapeHtml(item.status || '--')}</span>
                                </div>
                                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:12px;font-size:12px;">
                                    <div><div style="font-size:11px;color:var(--muted-foreground);margin-bottom:4px;">Started</div><div style="font-weight:700;line-height:1.5;">${this._escapeHtml(this._formatDateTime(item.started_at))}</div></div>
                                    <div><div style="font-size:11px;color:var(--muted-foreground);margin-bottom:4px;">Finished</div><div style="font-weight:700;line-height:1.5;">${this._escapeHtml(this._formatDateTime(item.finished_at))}</div></div>
                                    <div><div style="font-size:11px;color:var(--muted-foreground);margin-bottom:4px;">Duration</div><div style="font-weight:700;line-height:1.5;">${this._escapeHtml(this._formatDuration(item.duration_ms))}</div></div>
                                </div>
                                ${errorHtml}
                                <details style="margin-top:12px;">
                                    <summary style="cursor:pointer;font-size:12px;color:var(--primary);font-weight:700;">Show metadata and result</summary>
                                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-top:10px;">
                                        <div>
                                            <div style="font-size:11px;font-weight:700;margin-bottom:6px;">Metadata</div>
                                            <pre style="margin:0;white-space:pre-wrap;word-break:break-word;background:var(--background);border:1px solid var(--border);border-radius:10px;padding:10px;font-size:11px;max-height:220px;overflow:auto;">${metadata}</pre>
                                        </div>
                                        <div>
                                            <div style="font-size:11px;font-weight:700;margin-bottom:6px;">Result</div>
                                            <pre style="margin:0;white-space:pre-wrap;word-break:break-word;background:var(--background);border:1px solid var(--border);border-radius:10px;padding:10px;font-size:11px;max-height:220px;overflow:auto;">${result}</pre>
                                        </div>
                                    </div>
                                </details>
                            </div>
                        `;
                    }).join('')
                    : '<div style="padding:18px;color:var(--muted-foreground);">No activity runs for this account on the selected date.</div>';

        return `
            <div style="padding:22px 24px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;gap:16px;align-items:flex-start;background:linear-gradient(180deg,var(--card),rgba(148,163,184,.05));">
                <div style="min-width:0;">
                    <div style="font-size:28px;font-weight:900;letter-spacing:-.03em;line-height:1.2;word-break:break-word;">${this._escapeHtml(account.accountName || account.lord_name || 'Activity history')}</div>
                    <div style="font-size:12px;color:var(--muted-foreground);margin-top:8px;line-height:1.6;word-break:break-word;">${this._escapeHtml(account.gameId || account.game_id || '--')} | ${this._escapeHtml(account.emulator || account.emulator_name || '--')} | ${this._escapeHtml(this._selectedDate)}</div>
                </div>
                <button class="btn btn-sm btn-ghost" id="task-history-close" style="flex:0 0 auto;">Close</button>
            </div>
            <div style="padding:18px 22px 22px;overflow:auto;display:flex;flex-direction:column;gap:16px;background:var(--background);">
                ${summaryHtml}
                ${visibleLatestError ? `<div style="border:1px solid rgba(185,28,28,.18);background:linear-gradient(180deg,rgba(185,28,28,.08),rgba(185,28,28,.03));color:#991b1b;border-radius:14px;padding:12px 14px;font-size:12px;line-height:1.5;"><b>Latest error:</b> ${this._escapeHtml(visibleLatestError)}</div>` : ''}
                <div style="display:flex;gap:8px;padding:4px;background:var(--card);border:1px solid var(--border);border-radius:14px;width:max-content;max-width:100%;overflow:auto;">
                    <button class="task-history-tab-btn btn btn-sm" data-history-tab="timeline" style="border:none;background:var(--foreground);color:var(--background);white-space:nowrap;">Execution timeline</button>
                    <button class="task-history-tab-btn btn btn-sm btn-ghost" data-history-tab="breakdown" style="border:none;white-space:nowrap;">Activity breakdown</button>
                </div>
                <section data-history-panel="timeline" style="display:block;">
                    <div style="display:flex;flex-direction:column;gap:12px;">${timelineHtml}</div>
                </section>
                <section data-history-panel="breakdown" style="display:none;">
                    ${breakdownHtml}
                </section>
            </div>
        `;
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
                tabButtons.forEach((btn) => {
                    const isActive = btn.dataset.historyTab === nextTab;
                    btn.style.background = isActive ? 'var(--foreground)' : 'transparent';
                    btn.style.color = isActive ? 'var(--background)' : 'var(--foreground)';
                });
                tabPanels.forEach((section) => {
                    section.style.display = section.dataset.historyPanel === nextTab ? 'block' : 'none';
                });
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
                    critical: t.is_critical === 1
                }));
            } else {
                this._checklistTemplates = this._activityRegistry.map(act => ({
                    key: act.id,
                    label: act.name || act.id,
                    shortLabel: act.name || act.id,
                    critical: !!act.is_critical
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
        const backendStats = checklistData?.stats || null;

        let doneCount = Number(backendStats?.done ?? 0);
        let totalCount = Number(backendStats?.total ?? this._checklistTemplates.length);
        let failedCount = Number(backendStats?.failed ?? 0);

        if (!backendStats) {
            doneCount = 0;
            totalCount = this._checklistTemplates.length;
            failedCount = 0;

            this._checklistTemplates.forEach(t => {
                const act = activities[t.key];
                if (!act) return;
                if (act.status === 'SUCCESS') doneCount++;
                if (act.status === 'FAILED') failedCount++;
            });
        }

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

    _renderBodyOnly() {
        this._applyFilters();
        const tbody = document.getElementById('task-tbody');
        if (tbody) {
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

    destroy() {
        this._closeHistoryPanel();
    }
};
