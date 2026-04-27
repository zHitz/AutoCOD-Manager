/**
 * Scheduled Page
 * List + Detail panel for scheduling macro scripts on emulators.
 * Includes RSS Center rebuild debug tab.
 */
const ScheduledPage = {
    _schedules: [],
    _macros: [],
    _emulators: [],
    _rssRequests: [],
    _rssBuilders: [],
    _isLoading: true,
    _isRssLoading: true,
    _editingId: null,
    _activeTab: 'schedules',
    _rssLimit: 100,
    _rssActionSummary: '',

    _typeBadge(type) {
        const map = {
            once: { bg: 'rgba(99,102,241,0.1)', color: '#6366f1', label: 'Once' },
            interval: { bg: 'rgba(16,185,129,0.1)', color: '#10b981', label: 'Interval' },
            daily: { bg: 'rgba(245,158,11,0.1)', color: '#d97706', label: 'Daily' },
            cron: { bg: 'rgba(168,85,247,0.1)', color: '#a855f7', label: 'Cron' },
        };
        const badge = map[type] || map.once;
        return `<span style="background:${badge.bg};color:${badge.color};padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;">${badge.label}</span>`;
    },

    _requestStatusBadge(status) {
        const map = {
            pending: { bg: 'rgba(245,158,11,0.12)', color: '#d97706' },
            claimed: { bg: 'rgba(59,130,246,0.12)', color: '#2563eb' },
            done: { bg: 'rgba(16,185,129,0.12)', color: '#059669' },
            failed: { bg: 'rgba(239,68,68,0.12)', color: '#dc2626' },
            canceled: { bg: 'rgba(107,114,128,0.12)', color: '#6b7280' },
        };
        const badge = map[status] || map.pending;
        return `<span style="background:${badge.bg};color:${badge.color};padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;">${this._escapeHtml(status || 'unknown')}</span>`;
    },

    _boolBadge(value, yes = 'Yes', no = 'No') {
        return value
            ? `<span style="color:#059669;font-weight:700;">${yes}</span>`
            : `<span style="color:var(--muted-foreground);font-weight:600;">${no}</span>`;
    },

    _formatTime(iso, withSeconds = false) {
        if (!iso) return '-';
        try {
            const d = new Date(iso);
            return d.toLocaleString('en-GB', {
                day: '2-digit',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
                ...(withSeconds ? { second: '2-digit', year: 'numeric' } : {}),
            });
        } catch {
            return iso;
        }
    },

    _escapeHtml(value) {
        return String(value ?? '-')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    _renderTabs() {
        const tabs = [
            { key: 'schedules', label: 'Schedules' },
            { key: 'rss-center', label: 'RSS Center Rebuild' },
        ];
        return `
        <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
            ${tabs.map(tab => {
                const active = this._activeTab === tab.key;
                return `<button class="btn btn-sm ${active ? 'btn-primary' : 'btn-outline'}" style="${active ? '' : 'color:var(--muted-foreground);'}" onclick="ScheduledPage.switchTab('${tab.key}')">${tab.label}</button>`;
            }).join('')}
        </div>`;
    },

    render() {
        if (this._editingId !== null) return this._renderDetail();
        if (this._activeTab === 'rss-center') return this._renderRssCenterPanel();
        return this._renderList();
    },

    _renderList() {
        const rows = this._schedules.map((s, i) => {
            const enabled = s.is_enabled;
            const toggleLabel = enabled ? 'Pause' : 'Resume';
            const statusDot = enabled
                ? '<span style="width:8px;height:8px;border-radius:50%;background:#10b981;display:inline-block;"></span>'
                : '<span style="width:8px;height:8px;border-radius:50%;background:var(--muted-foreground);display:inline-block;"></span>';
            return `
            <tr class="account-row" style="animation:fadeInSlideUp 0.3s ease ${i * 40}ms both;" onclick="ScheduledPage.openDetail(${s.id})">
                <td style="padding:12px 14px;">${statusDot}</td>
                <td style="padding:12px 14px;font-weight:600;">${this._escapeHtml(s.name)}</td>
                <td style="padding:12px 14px;font-family:var(--font-mono);font-size:12px;color:var(--muted-foreground);">${this._escapeHtml(s.macro_filename)}</td>
                <td style="padding:12px 14px;text-align:center;">${this._typeBadge(s.schedule_type)}</td>
                <td style="padding:12px 14px;font-size:12px;">${this._escapeHtml(s.schedule_value || '-')}</td>
                <td style="padding:12px 14px;font-size:12px;">${s.target_mode === 'all_online' ? 'All Online' : 'Specific'}</td>
                <td style="padding:12px 14px;font-size:12px;color:var(--muted-foreground);">${this._formatTime(s.next_run_at)}</td>
                <td style="padding:12px 14px;font-size:12px;color:var(--muted-foreground);">${this._formatTime(s.last_run_at)}</td>
                <td style="padding:12px 14px;text-align:center;font-size:12px;font-weight:600;">${s.run_count || 0}</td>
                <td style="padding:12px 14px;text-align:right;" onclick="event.stopPropagation()">
                    <div style="display:flex;gap:4px;justify-content:flex-end;">
                        <button class="btn btn-sm btn-outline" style="padding:4px 10px;font-size:11px;" onclick="ScheduledPage.executeNow(${s.id})" title="Execute Now">
                            <svg style="width:12px;height:12px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                        </button>
                        <button class="btn btn-sm btn-ghost" style="padding:4px 10px;font-size:11px;color:var(--muted-foreground);" onclick="ScheduledPage.toggleEnable(${s.id}, ${enabled ? 0 : 1})" title="${toggleLabel}">
                            ${enabled ? '<svg style="width:12px;height:12px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>' : '<svg style="width:12px;height:12px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>'}
                        </button>
                        <button class="btn btn-sm btn-ghost" style="padding:4px 10px;font-size:11px;color:var(--destructive);" onclick="ScheduledPage.deleteSchedule(${s.id})" title="Delete">
                            <svg style="width:12px;height:12px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        </button>
                    </div>
                </td>
            </tr>`;
        }).join('');

        const emptyState = this._schedules.length === 0 && !this._isLoading
            ? '<tr><td colspan="10" style="text-align:center;padding:48px 20px;color:var(--muted-foreground);font-size:14px;">No schedules yet. Create one to automate your macros.</td></tr>'
            : '';

        return `
        <style>
            @keyframes fadeInSlideUp {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
        <div style="position:relative;height:100%;display:flex;flex-direction:column;">
            ${this._renderTabs()}
            <div class="page-header" style="justify-content:space-between;flex-shrink:0;align-items:center;margin-bottom:20px;">
                <div>
                    <h2 style="margin:0 0 4px;">Scheduled Tasks</h2>
                    <p style="margin:0;color:var(--muted-foreground);font-size:13px;">${this._isLoading ? 'Loading...' : `${this._schedules.length} schedule(s) configured`}</p>
                </div>
                <div style="display:flex;gap:8px;">
                    <button class="btn btn-outline btn-sm" style="display:flex;align-items:center;gap:6px;" onclick="ScheduledPage.fetchData()">
                        <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Refresh
                    </button>
                    <button class="btn btn-primary btn-sm" style="display:flex;align-items:center;gap:6px;" onclick="ScheduledPage.openCreate()">
                        <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                        Create Schedule
                    </button>
                </div>
            </div>
            <div class="card" style="overflow:auto;flex:1;padding:0;">
                <table style="border-collapse:collapse;width:100%;">
                    <thead>
                        <tr style="background:var(--muted);border-bottom:1px solid var(--border);">
                            <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;width:40px;"></th>
                            <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Name</th>
                            <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Macro</th>
                            <th style="padding:10px 14px;text-align:center;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Type</th>
                            <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Value</th>
                            <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Target</th>
                            <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Next Run</th>
                            <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Last Run</th>
                            <th style="padding:10px 14px;text-align:center;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Runs</th>
                            <th style="padding:10px 14px;text-align:right;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;width:120px;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>${this._isLoading ? '<tr><td colspan="10" style="text-align:center;padding:32px;color:var(--muted-foreground);">Loading schedules...</td></tr>' : rows + emptyState}</tbody>
                </table>
            </div>
        </div>`;
    },

    _renderRssCenterPanel() {
        const builders = this._rssBuilders.map((builder, index) => `
            <tr style="animation:fadeInSlideUp 0.3s ease ${index * 40}ms both;">
                <td style="padding:12px 14px;font-weight:600;">${this._escapeHtml(builder.lord_name || '-')}</td>
                <td style="padding:12px 14px;font-family:var(--font-mono);font-size:12px;">${this._escapeHtml(builder.game_id || '-')}</td>
                <td style="padding:12px 14px;">${this._escapeHtml(builder.role || 'farmer')}</td>
                <td style="padding:12px 14px;">${this._boolBadge(!!builder.rss_center_builder_enabled, 'Enabled', 'Disabled')}</td>
                <td style="padding:12px 14px;">${this._boolBadge(!!builder.safe_to_boot, 'Safe', 'Unsafe')}</td>
                <td style="padding:12px 14px;text-align:center;font-weight:700;">${builder.builder_priority ?? '-'}</td>
                <td style="padding:12px 14px;">${this._escapeHtml(builder.builder_resource_policy || 'random')}</td>
                <td style="padding:12px 14px;">${this._escapeHtml(builder.emu_name || builder.serial || '-')}</td>
                <td style="padding:12px 14px;color:var(--muted-foreground);font-size:12px;">${this._formatTime(builder.last_builder_run_at, true)}</td>
            </tr>
        `).join('');

        const requests = this._rssRequests.map((request, index) => {
            const canRetry = request.status === 'failed';
            const canCancel = request.status === 'pending' || request.status === 'claimed';
            return `
            <tr style="vertical-align:top;animation:fadeInSlideUp 0.3s ease ${index * 30}ms both;">
                <td style="padding:12px 14px;font-weight:700;">#${request.id}</td>
                <td style="padding:12px 14px;">${this._requestStatusBadge(request.status)}</td>
                <td style="padding:12px 14px;font-size:12px;">
                    <div style="font-weight:700;">${this._escapeHtml(request.reason_code)}</div>
                    <div style="color:var(--muted-foreground);margin-top:4px;">${this._escapeHtml(request.reason_message || '-')}</div>
                </td>
                <td style="padding:12px 14px;font-size:12px;">
                    <div style="font-family:var(--font-mono);">${this._escapeHtml(request.source_game_id || '-')}</div>
                    <div style="color:var(--muted-foreground);margin-top:4px;">${this._escapeHtml(request.source_serial || '-')}</div>
                </td>
                <td style="padding:12px 14px;font-size:12px;">
                    <div style="font-family:var(--font-mono);">${this._escapeHtml(request.claimed_by_game_id || '-')}</div>
                    <div style="color:var(--muted-foreground);margin-top:4px;">${this._escapeHtml(request.run_mode || '-')}</div>
                </td>
                <td style="padding:12px 14px;font-size:12px;color:var(--muted-foreground);">
                    <div>Requested: ${this._formatTime(request.requested_at, true)}</div>
                    <div style="margin-top:4px;">Claimed: ${this._formatTime(request.claimed_at, true)}</div>
                    <div style="margin-top:4px;">Finished: ${this._formatTime(request.finished_at, true)}</div>
                </td>
                <td style="padding:12px 14px;font-size:12px;">
                    <div style="font-weight:700;">${this._escapeHtml(request.result_status || '-')}</div>
                    <div style="color:var(--muted-foreground);margin-top:4px;max-width:280px;white-space:normal;word-break:break-word;">${this._escapeHtml(request.result_message || '-')}</div>
                    <div style="color:var(--destructive);margin-top:4px;max-width:280px;white-space:normal;word-break:break-word;">${this._escapeHtml(request.last_error || '')}</div>
                </td>
                <td style="padding:12px 14px;text-align:center;font-size:12px;font-weight:700;">${request.retry_count || 0}</td>
                <td style="padding:12px 14px;text-align:right;">
                    <div style="display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap;">
                        <button class="btn btn-outline btn-sm" style="padding:4px 10px;font-size:11px;" onclick="ScheduledPage.retryRssRequest(${request.id})" ${canRetry ? '' : 'disabled'}>Retry</button>
                        <button class="btn btn-ghost btn-sm" style="padding:4px 10px;font-size:11px;color:var(--destructive);" onclick="ScheduledPage.cancelRssRequest(${request.id})" ${canCancel ? '' : 'disabled'}>Cancel</button>
                    </div>
                </td>
            </tr>`;
        }).join('');

        return `
        <style>
            @keyframes fadeInSlideUp {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
        <div style="position:relative;height:100%;display:flex;flex-direction:column;">
            ${this._renderTabs()}
            <div class="page-header" style="justify-content:space-between;flex-shrink:0;align-items:flex-start;margin-bottom:20px;gap:16px;">
                <div>
                    <h2 style="margin:0 0 4px;">RSS Center Rebuild</h2>
                    <p style="margin:0;color:var(--muted-foreground);font-size:13px;">${this._isRssLoading ? 'Loading rebuild requests...' : `${this._rssRequests.length} request(s), ${this._rssBuilders.length} safe builder candidate(s)`}</p>
                    ${this._rssActionSummary ? `<p style="margin:8px 0 0;color:var(--muted-foreground);font-size:12px;">${this._escapeHtml(this._rssActionSummary)}</p>` : ''}
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <button class="btn btn-outline btn-sm" style="display:flex;align-items:center;gap:6px;" onclick="ScheduledPage.refreshRssCenterData()">
                        <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Refresh
                    </button>
                    <button class="btn btn-primary btn-sm" style="display:flex;align-items:center;gap:6px;" onclick="ScheduledPage.runRssDispatchOnce()">
                        <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                        Run Once
                    </button>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:minmax(300px, 1fr);gap:16px;overflow:auto;flex:1;">
                <div class="card" style="padding:0;overflow:auto;">
                    <div style="padding:16px 18px;border-bottom:1px solid var(--border);">
                        <div style="font-weight:700;">Builder Candidates</div>
                        <div style="font-size:12px;color:var(--muted-foreground);margin-top:4px;">Accounts currently eligible for safe RSS Center rebuild dispatch.</div>
                    </div>
                    <table style="border-collapse:collapse;width:100%;">
                        <thead>
                            <tr style="background:var(--muted);border-bottom:1px solid var(--border);">
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Lord</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Game ID</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Role</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Builder</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Safe</th>
                                <th style="padding:10px 14px;text-align:center;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Priority</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Policy</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Emulator</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Last Run</th>
                            </tr>
                        </thead>
                        <tbody>${this._isRssLoading ? '<tr><td colspan="9" style="text-align:center;padding:24px;color:var(--muted-foreground);">Loading builder candidates...</td></tr>' : (builders || '<tr><td colspan="9" style="text-align:center;padding:24px;color:var(--muted-foreground);">No safe builder candidates configured yet.</td></tr>')}</tbody>
                    </table>
                </div>
                <div class="card" style="padding:0;overflow:auto;">
                    <div style="padding:16px 18px;border-bottom:1px solid var(--border);">
                        <div style="font-weight:700;">Request History</div>
                        <div style="font-size:12px;color:var(--muted-foreground);margin-top:4px;">Full request timeline for debug, including raw result and last error messages.</div>
                    </div>
                    <table style="border-collapse:collapse;width:100%;">
                        <thead>
                            <tr style="background:var(--muted);border-bottom:1px solid var(--border);">
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">ID</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Status</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Reason</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Source</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Claimed By</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Timeline</th>
                                <th style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Result / Error</th>
                                <th style="padding:10px 14px;text-align:center;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Retries</th>
                                <th style="padding:10px 14px;text-align:right;font-size:11px;font-weight:700;color:var(--muted-foreground);text-transform:uppercase;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>${this._isRssLoading ? '<tr><td colspan="9" style="text-align:center;padding:24px;color:var(--muted-foreground);">Loading rebuild requests...</td></tr>' : (requests || '<tr><td colspan="9" style="text-align:center;padding:24px;color:var(--muted-foreground);">No rebuild requests recorded yet.</td></tr>')}</tbody>
                    </table>
                </div>
            </div>
        </div>`;
    },

    _renderDetail() {
        const isNew = this._editingId === 'new';
        const sched = isNew ? {} : this._schedules.find(s => s.id === this._editingId) || {};
        const title = isNew ? 'Create Schedule' : `Edit: ${sched.name || 'Schedule'}`;
        const macroOptions = this._macros.map(m => `<option value="${m.filename}" ${sched.macro_filename === m.filename ? 'selected' : ''}>${m.name || m.filename}</option>`).join('');
        const typeOptions = ['once', 'interval', 'daily', 'cron'].map(t => `<option value="${t}" ${(sched.schedule_type || 'once') === t ? 'selected' : ''}>${t.charAt(0).toUpperCase() + t.slice(1)}</option>`).join('');
        let targetIndices = [];
        try { targetIndices = JSON.parse(sched.target_indices || '[]'); } catch { targetIndices = []; }
        const emuCheckboxes = this._emulators.map(e => {
            const checked = targetIndices.includes(e.index) ? 'checked' : '';
            const status = e.status === 'ONLINE' ? 'ON' : 'OFF';
            return `<label style="display:flex;align-items:center;gap:6px;padding:4px 0;font-size:13px;cursor:pointer;"><input type="checkbox" class="sched-emu-cb" value="${e.index}" ${checked} />${status} ${this._escapeHtml(e.name || `LDP-${e.index}`)}</label>`;
        }).join('');

        return `
        <div style="position:relative;height:100%;display:flex;flex-direction:column;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
                <button class="btn btn-ghost btn-sm" onclick="ScheduledPage.backToList()" style="padding:6px 10px;">
                    <svg style="width:16px;height:16px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
                </button>
                <h2 style="margin:0;">${title}</h2>
            </div>
            <div class="card" style="flex:1;overflow:auto;padding:24px;">
                <div style="max-width:640px;">
                    <div style="margin-bottom:18px;">
                        <label style="display:block;font-size:12px;font-weight:700;color:var(--muted-foreground);margin-bottom:6px;">Schedule Name</label>
                        <input type="text" id="sched-name" value="${this._escapeHtml(sched.name || '')}" placeholder="e.g. Daily Gather Resources" style="width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground);font-size:14px;" />
                    </div>
                    <div style="margin-bottom:18px;">
                        <label style="display:block;font-size:12px;font-weight:700;color:var(--muted-foreground);margin-bottom:6px;">Macro Script</label>
                        <select id="sched-macro" style="width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground);font-size:13px;">
                            <option value="">-- Select Macro --</option>
                            ${macroOptions}
                        </select>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px;">
                        <div>
                            <label style="display:block;font-size:12px;font-weight:700;color:var(--muted-foreground);margin-bottom:6px;">Schedule Type</label>
                            <select id="sched-type" style="width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground);font-size:13px;" onchange="ScheduledPage.onTypeChange()">
                                ${typeOptions}
                            </select>
                        </div>
                        <div>
                            <label style="display:block;font-size:12px;font-weight:700;color:var(--muted-foreground);margin-bottom:6px;" id="sched-value-label">Value</label>
                            <input type="text" id="sched-value" value="${this._escapeHtml(sched.schedule_value || '')}" placeholder="" style="width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground);font-size:13px;" />
                        </div>
                    </div>
                    <div id="sched-value-hint" style="font-size:11px;color:var(--muted-foreground);margin-top:-12px;margin-bottom:18px;"></div>
                    <div style="margin-bottom:18px;">
                        <label style="display:block;font-size:12px;font-weight:700;color:var(--muted-foreground);margin-bottom:6px;">Target Emulators</label>
                        <div style="display:flex;gap:16px;margin-bottom:10px;">
                            <label style="display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;"><input type="radio" name="sched-target" value="all_online" ${(sched.target_mode || 'all_online') === 'all_online' ? 'checked' : ''} onchange="ScheduledPage.onTargetChange()" /> All Online</label>
                            <label style="display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;"><input type="radio" name="sched-target" value="specific" ${sched.target_mode === 'specific' ? 'checked' : ''} onchange="ScheduledPage.onTargetChange()" /> Specific</label>
                        </div>
                        <div id="sched-emu-list" style="display:${sched.target_mode === 'specific' ? 'block' : 'none'};background:var(--muted);border-radius:8px;padding:10px 14px;max-height:180px;overflow-y:auto;">
                            ${emuCheckboxes || '<div style="color:var(--muted-foreground);font-size:12px;">No emulators found</div>'}
                        </div>
                    </div>
                    <div style="margin-bottom:24px;">
                        <label style="display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;">
                            <input type="checkbox" id="sched-enabled" ${(sched.is_enabled ?? 1) ? 'checked' : ''} />
                            <span style="font-weight:600;">Enabled</span>
                            <span style="color:var(--muted-foreground);font-size:12px;">- Schedule will auto-run when enabled</span>
                        </label>
                    </div>
                    <div style="display:flex;gap:8px;justify-content:flex-end;border-top:1px solid var(--border);padding-top:18px;">
                        ${!isNew ? `<button class="btn btn-ghost btn-sm" style="color:var(--destructive);margin-right:auto;" onclick="ScheduledPage.deleteSchedule(${sched.id})">Delete</button>` : ''}
                        <button class="btn btn-outline btn-sm" onclick="ScheduledPage.backToList()">Cancel</button>
                        <button class="btn btn-primary btn-sm" onclick="ScheduledPage.saveSchedule()">${isNew ? 'Create' : 'Save Changes'}</button>
                    </div>
                </div>
            </div>
        </div>`;
    },

    onTypeChange() {
        const type = document.getElementById('sched-type')?.value;
        const label = document.getElementById('sched-value-label');
        const input = document.getElementById('sched-value');
        const hint = document.getElementById('sched-value-hint');
        if (!label || !input || !hint) return;
        const config = {
            once: { label: 'Run At (datetime)', placeholder: '2026-03-02T14:00', hint: 'ISO datetime - runs once then disables.' },
            interval: { label: 'Interval', placeholder: '30m', hint: 'Format: 30m (minutes), 2h (hours), 1d (days).' },
            daily: { label: 'Time (HH:MM)', placeholder: '14:00', hint: '24-hour format - runs every day at this time.' },
            cron: { label: 'Cron Expression', placeholder: '0 */2 * * *', hint: 'Standard cron syntax (simplified, runs hourly for now).' },
        };
        const item = config[type] || config.once;
        label.textContent = item.label;
        input.placeholder = item.placeholder;
        hint.textContent = item.hint;
    },

    onTargetChange() {
        const mode = document.querySelector('input[name="sched-target"]:checked')?.value;
        const list = document.getElementById('sched-emu-list');
        if (list) list.style.display = mode === 'specific' ? 'block' : 'none';
    },

    switchTab(tabKey) {
        if (this._editingId !== null) return;
        this._activeTab = tabKey;
        this._rerender();
    },

    openCreate() {
        this._editingId = 'new';
        this._rerender();
        setTimeout(() => this.onTypeChange(), 50);
    },

    openDetail(id) {
        this._editingId = id;
        this._rerender();
        setTimeout(() => this.onTypeChange(), 50);
    },

    backToList() {
        this._editingId = null;
        this._rerender();
    },

    _rerender() {
        if (typeof router !== 'undefined' && router._currentPage === 'scheduled') {
            const root = document.getElementById('page-root');
            if (root) root.innerHTML = this.render();
        }
    },

    async saveSchedule() {
        const name = document.getElementById('sched-name')?.value?.trim();
        const macro = document.getElementById('sched-macro')?.value;
        const type = document.getElementById('sched-type')?.value;
        const value = document.getElementById('sched-value')?.value?.trim();
        const targetMode = document.querySelector('input[name="sched-target"]:checked')?.value || 'all_online';
        const enabled = document.getElementById('sched-enabled')?.checked ?? true;
        if (!name) return Toast?.error?.('Error', 'Schedule name is required') || alert('Name required');
        if (!macro) return Toast?.error?.('Error', 'Select a macro script') || alert('Macro required');
        const indices = [...document.querySelectorAll('.sched-emu-cb:checked')].map(cb => parseInt(cb.value, 10));
        const data = { name, macro_filename: macro, schedule_type: type, schedule_value: value, target_mode: targetMode, target_indices: indices, is_enabled: enabled };
        try {
            if (this._editingId === 'new') await API.createSchedule(data);
            else await API.updateSchedule(this._editingId, data);
            this._editingId = null;
            await this.fetchData();
        } catch (e) {
            alert(`Error saving: ${e.message}`);
        }
    },

    async toggleEnable(id, newVal) {
        try {
            await API.updateSchedule(id, { is_enabled: !!newVal });
            await this.fetchData();
        } catch (e) {
            console.error('Toggle failed:', e);
        }
    },

    async executeNow(id) {
        try {
            const res = await API.executeSchedule(id);
            if (res.status === 'executing') {
                if (window.Toast) Toast.success('Executing', `Schedule "${res.name}" started.`);
            } else if (window.Toast) {
                Toast.error('Error', res.error || 'Unknown');
            }
        } catch (e) {
            alert(`Execute failed: ${e.message}`);
        }
    },

    async deleteSchedule(id) {
        if (!confirm('Delete this schedule?')) return;
        try {
            await API.deleteSchedule(id);
            this._editingId = null;
            await this.fetchData();
        } catch (e) {
            alert(`Delete failed: ${e.message}`);
        }
    },

    async refreshRssCenterData() {
        this._isRssLoading = true;
        this._rerender();
        try {
            const [requestRes, builderRes] = await Promise.all([
                API.getRssCenterRebuildRequests(this._rssLimit),
                API.getRssCenterRebuildBuilders(),
            ]);
            this._rssRequests = Array.isArray(requestRes) ? requestRes : [];
            this._rssBuilders = Array.isArray(builderRes) ? builderRes : [];
        } catch (e) {
            console.error('Failed to fetch RSS Center rebuild data:', e);
            this._rssActionSummary = `Failed to load RSS Center rebuild data: ${e.message}`;
        } finally {
            this._isRssLoading = false;
            this._rerender();
        }
    },

    async runRssDispatchOnce() {
        try {
            const res = await API.runRssCenterRebuildDispatchOnce();
            const summary = res?.summary || {};
            this._rssActionSummary = `Run once finished. Pending=${summary.pending ?? 0}, claimed=${summary.claimed ?? 0}, unavailable=${summary.no_builder ?? 0}, failed=${summary.failed ?? 0}.`;
            if (window.Toast) Toast.success('RSS Center Dispatcher', 'Run-once cycle completed.');
            await this.refreshRssCenterData();
        } catch (e) {
            this._rssActionSummary = `Run once failed: ${e.message}`;
            if (window.Toast) Toast.error('RSS Center Dispatcher', e.message);
            this._rerender();
        }
    },

    async retryRssRequest(id) {
        try {
            const res = await API.retryRssCenterRebuildRequest(id);
            if (res.status !== 'ok') throw new Error(res.error || 'Retry failed');
            this._rssActionSummary = `Request #${id} moved back to pending.`;
            if (window.Toast) Toast.success('RSS Center Rebuild', `Request #${id} queued again.`);
            await this.refreshRssCenterData();
        } catch (e) {
            this._rssActionSummary = `Retry failed for request #${id}: ${e.message}`;
            if (window.Toast) Toast.error('RSS Center Rebuild', e.message);
            this._rerender();
        }
    },

    async cancelRssRequest(id) {
        if (!confirm(`Cancel rebuild request #${id}?`)) return;
        try {
            const res = await API.cancelRssCenterRebuildRequest(id);
            if (res.status !== 'ok') throw new Error(res.error || 'Cancel failed');
            this._rssActionSummary = `Request #${id} canceled.`;
            if (window.Toast) Toast.success('RSS Center Rebuild', `Request #${id} canceled.`);
            await this.refreshRssCenterData();
        } catch (e) {
            this._rssActionSummary = `Cancel failed for request #${id}: ${e.message}`;
            if (window.Toast) Toast.error('RSS Center Rebuild', e.message);
            this._rerender();
        }
    },

    async fetchData() {
        this._isLoading = true;
        this._isRssLoading = true;
        this._rerender();
        try {
            const [schedRes, macroRes, emuRes, rssReqRes, rssBuilderRes] = await Promise.all([
                API.getSchedules(),
                API.getMacros(),
                API.getAllEmulators(),
                API.getRssCenterRebuildRequests(this._rssLimit),
                API.getRssCenterRebuildBuilders(),
            ]);
            this._schedules = Array.isArray(schedRes) ? schedRes : [];
            this._macros = Array.isArray(macroRes) ? macroRes : [];
            this._emulators = Array.isArray(emuRes) ? emuRes : [];
            this._rssRequests = Array.isArray(rssReqRes) ? rssReqRes : [];
            this._rssBuilders = Array.isArray(rssBuilderRes) ? rssBuilderRes : [];
        } catch (e) {
            console.error('Failed to fetch scheduled page data:', e);
            this._schedules = [];
            this._rssRequests = [];
            this._rssBuilders = [];
            this._rssActionSummary = `Load failed: ${e.message}`;
        } finally {
            this._isLoading = false;
            this._isRssLoading = false;
            this._rerender();
        }
    },

    init() {
        this.fetchData();
    },

    destroy() {
        this._editingId = null;
        this._activeTab = 'schedules';
    },
};
