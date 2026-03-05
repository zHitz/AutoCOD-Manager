/**
 * History Page — Production dashboard with full state machine.
 */
const HistoryPage = {
    state: {
        loading: false,
        error: null,
        items: [],
        filters: {
            search: '',
            date: 'all',
            device: 'all',
            status: 'all',
            task: 'all',
            quick: 'all',
        },
        expandedRowId: null,
        useMockData: false,
    },

    mockItems: [
        {
            id: 'mock-1',
            task_id: 'A1B2C3D4',
            task_type: 'resources',
            serial: 'emulator-5554',
            status: 'SUCCESS',
            data: { gold: { total: 1023000 }, wood: { total: 780000 } },
            error: null,
            is_reliable: true,
            reliability: 97,
            started_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
            duration_ms: 8100,
            logs: ['Navigate resources page', 'OCR complete', 'Validation passed'],
        },
        {
            id: 'mock-2',
            task_id: 'E5F6G7H8',
            task_type: 'hall',
            serial: 'emulator-5556',
            status: 'FAILED',
            data: {},
            error: 'OCR timeout while parsing hall level',
            is_reliable: false,
            reliability: 41,
            started_at: new Date(Date.now() - 40 * 60 * 1000).toISOString(),
            duration_ms: 35450,
            logs: ['Capture screenshot', 'OCR retry x3', 'Task failed'],
        },
        {
            id: 'mock-3',
            task_id: 'I9J0K1L2',
            task_type: 'manual',
            serial: 'emulator-5560',
            status: 'RUNNING',
            data: { step: 'processing market panel' },
            error: null,
            is_reliable: true,
            reliability: 72,
            started_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
            duration_ms: 18400,
            logs: ['Task queued', 'Navigating', 'Processing OCR'],
        },
    ],

    render() {
        return `
            <div class="page-enter history-page" id="history-page-root">
                <div class="page-header">
                    <div class="page-header-info">
                        <h2>History & Logs</h2>
                        <p>Track task execution, reliability, and scan output over time.</p>
                    </div>
                    <div class="page-actions">
                        <div class="search-wrapper">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                            <input id="history-search" class="search-input" type="text" placeholder="Search task, device..." value="${this.state.filters.search}">
                        </div>
                        <button id="history-refresh-btn" class="btn btn-outline btn-sm" onclick="HistoryPage.load()">
                            <svg class="refresh-icon" style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Refresh
                        </button>
                    </div>
                </div>

                <div class="card history-filter-bar" id="history-filter-bar"></div>
                <div class="history-quick-filters" id="history-quick-filters"></div>

                <div class="card history-table-card" id="history-state-area"></div>

                <div class="history-footer" id="history-footer" style="padding: 16px 0; text-align: center; color: var(--muted-foreground); font-size: 13px;">Showing 0 results</div>
            </div>
        `;
    },

    async init() {
        this.bindEvents();
        await this.load();
    },

    destroy() { },

    bindEvents() {
        const search = document.getElementById('history-search');
        if (search) {
            search.addEventListener('input', (event) => {
                this.state.filters.search = event.target.value || '';
                this.renderContent();
            });
        }
    },

    async load() {
        this.state.loading = true;
        this.state.error = null;
        this.renderContent();

        const refreshBtn = document.getElementById('history-refresh-btn');
        if (refreshBtn) refreshBtn.classList.add('is-spinning');

        try {
            let items = [];

            try {
                const history = await API.getHistory(200);
                items = this.normalizeHistoryPayload(history);
            } catch (_) {
                // Fallback chain below handles this.
            }

            if (!items.length) {
                try {
                    const executionRuns = await API.getExecutionRuns();
                    items = this.normalizeHistoryPayload(executionRuns);
                } catch (_) {
                    // Continue to next fallback.
                }
            }

            if (!items.length) {
                try {
                    const queueHistory = await API.getQueueHistory(200);
                    items = this.normalizeHistoryPayload(queueHistory);
                } catch (_) {
                    // Continue to mock fallback in catch below.
                }
            }

            this.state.items = items.map((item) => this.normalizeHistoryItem(item));
            this.state.useMockData = false;
        } catch (e) {
            console.warn('[History] API failed, using mock:', e);
            this.state.error = null;
            this.state.items = [...this.mockItems];
            this.state.useMockData = true;
            Toast.error('Error', 'History API unavailable — using mock data for this version');
        } finally {
            this.state.loading = false;
            if (refreshBtn) refreshBtn.classList.remove('is-spinning');
            this.renderContent();
        }
    },

    normalizeHistoryPayload(payload) {
        if (Array.isArray(payload)) return payload;
        if (payload && Array.isArray(payload.data)) return payload.data;
        return [];
    },

    normalizeHistoryItem(item) {
        let parsedData = {};
        const metadataRaw = item?.metadata_json || item?.metadata;
        let metadata = {};

        if (metadataRaw) {
            try {
                metadata = typeof metadataRaw === 'string' ? JSON.parse(metadataRaw) : metadataRaw;
            } catch (_) {
                metadata = {};
            }
        }

        const rawResult = item?.result_json ?? metadata?.result_json;
        if (rawResult) {
            try {
                parsedData = typeof rawResult === 'string' ? JSON.parse(rawResult) : rawResult;
                if (typeof parsedData === 'string') parsedData = JSON.parse(parsedData);
                if (parsedData && parsedData.data) parsedData = parsedData.data;
            } catch (_) {
                parsedData = { raw: rawResult };
            }
        }

        const hasData = parsedData && Object.keys(parsedData).length > 0;
        const rawId = item?.id || item?.run_id || `${item?.serial || item?.emu_name || 'unknown'}-${item?.started_at || item?.created_at || Date.now()}`;

        return {
            id: String(rawId),
            task_id: String(rawId).slice(-8).toUpperCase(),
            task_type: item?.task_type || metadata?.task_type || item?.source_page || 'unknown',
            serial: item?.serial || metadata?.serial || '--',
            status: String(item?.status || metadata?.status || 'UNKNOWN').toUpperCase(),
            data: hasData ? parsedData : null,
            error: item?.error || metadata?.error || null,
            is_reliable: !(item?.error || metadata?.error),
            reliability: (item?.error || metadata?.error) ? 40 : 95,
            started_at: item?.started_at || item?.created_at || null,
            finished_at: item?.finished_at || item?.ended_at || null,
            duration_ms: Number(item?.duration_ms || 0),
            source: item?.source || item?.source_page || 'system',
            logs: Array.isArray(item?.logs) ? item.logs : [],
            emu_name: item?.emu_name || item?.emulator_name || metadata?.emu_name || '',
        };
    },
    getFilteredItems() {
        const { search, date, device, status, task, quick } = this.state.filters;
        const normalizedSearch = search.trim().toLowerCase();

        return this.state.items.filter((item) => {
            const rawTime = item.started_at || item.created_at;
            const dt = rawTime ? new Date(rawTime) : null;
            const statusValue = this.normalizeStatus(item.status);
            const taskType = item.task_type || 'unknown';
            const serial = item.serial || 'unknown';
            const durationMs = Number(item.duration_ms || 0);
            const source = `${serial} ${taskType} ${statusValue}`.toLowerCase();

            if (normalizedSearch && !source.includes(normalizedSearch)) return false;
            if (date === 'today' && (!dt || dt.toDateString() !== new Date().toDateString())) return false;
            if (device !== 'all' && serial !== device) return false;
            if (status !== 'all' && statusValue !== status) return false;
            if (task !== 'all' && taskType !== task) return false;

            if (quick === 'failed' && statusValue !== 'FAILED') return false;
            if (quick === 'today' && (!dt || dt.toDateString() !== new Date().toDateString())) return false;
            if (quick === 'long' && durationMs < 30000) return false;
            if (quick === 'manual' && taskType !== 'manual') return false;

            return true;
        });
    },

    renderContent() {
        const stateArea = document.getElementById('history-state-area');
        const filterBar = document.getElementById('history-filter-bar');
        const quickFilters = document.getElementById('history-quick-filters');
        const footer = document.getElementById('history-footer');

        if (!stateArea || !filterBar || !quickFilters || !footer) return;

        this.renderFilterBar(filterBar);

        if (this.state.loading) {
            quickFilters.innerHTML = '';
            stateArea.innerHTML = this.renderSkeletonRows();
            footer.textContent = 'Loading history...';
            return;
        }

        if (this.state.error) {
            quickFilters.innerHTML = '';
            stateArea.innerHTML = this.renderErrorState();
            footer.textContent = 'Could not load history';
            this.bindInlineEvents();
            return;
        }

        const filtered = this.getFilteredItems();
        footer.textContent = `Showing ${filtered.length} result${filtered.length === 1 ? '' : 's'}${this.state.useMockData ? ' • mock data' : ''}`;

        // Always render quick filters so user can reset them if they lead to 0 results
        quickFilters.innerHTML = this.renderQuickFilters();

        if (!filtered.length) {
            stateArea.innerHTML = this.renderEmptyState();
            this.bindInlineEvents();
            return;
        }

        stateArea.innerHTML = this.renderDataTable(filtered);
        this.bindInlineEvents();
    },

    renderFilterBar(container) {
        const devices = ['all', ...new Set(this.state.items.map((item) => item.serial).filter(Boolean))];
        const tasks = ['all', ...new Set(this.state.items.map((item) => item.task_type).filter(Boolean))];

        container.style.padding = '16px';
        container.style.marginBottom = '16px';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '12px';

        container.innerHTML = `
            <div class="grid-4" style="margin-bottom: 0;">
                ${this.renderSelect('Date Range', 'history-filter-date', this.state.filters.date, [
            { value: 'all', label: 'All time' },
            { value: 'today', label: 'Today' },
        ])}
                ${this.renderSelect('Device', 'history-filter-device', this.state.filters.device, devices.map((value) => ({ value, label: value === 'all' ? 'All devices' : value })))}
                ${this.renderSelect('Status', 'history-filter-status', this.state.filters.status, [
            { value: 'all', label: 'All status' },
            { value: 'SUCCESS', label: 'Success' },
            { value: 'FAILED', label: 'Failed' },
            { value: 'RUNNING', label: 'Running' },
        ])}
                ${this.renderSelect('Task Type', 'history-filter-task', this.state.filters.task, tasks.map((value) => ({ value, label: value === 'all' ? 'All tasks' : value })))}
            </div>
        `;
    },

    renderSelect(label, id, selected, options) {
        return `
            <label class="form-group" style="margin: 0; display: flex; flex-direction: column; gap: 6px;">
                <span class="text-sm font-medium text-muted">${label}</span>
                <select id="${id}" class="form-select">
                    ${options.map((opt) => `<option value="${opt.value}" ${opt.value === selected ? 'selected' : ''}>${opt.label}</option>`).join('')}
                </select>
            </label>
        `;
    },

    renderQuickFilters() {
        const quicks = [
            { value: 'today', label: 'Today' },
            { value: 'failed', label: 'Failed' },
            { value: 'long', label: 'Long Runs' },
            { value: 'manual', label: 'Manual Tasks' },
        ];

        return `
            <div style="display: flex; gap: 8px; margin-bottom: 24px;">
                ${quicks.map((chip) => `
                    <button class="badge badge-outline ${this.state.filters.quick === chip.value ? 'active bg-primary text-white' : ''}" data-quick="${chip.value}" style="cursor: pointer;">${chip.label}</button>
                `).join('')}
                <button class="badge badge-outline ${this.state.filters.quick === 'all' ? 'active bg-primary text-white' : ''}" data-quick="all" style="cursor: pointer;">Reset</button>
            </div>
        `;
    },

    renderSkeletonRows() {
        return `
            <table class="history-table">
                <thead>
                    <tr>
                        <th>Time</th><th>Task</th><th>Status</th><th>Device</th><th>Duration</th><th>Reliable</th><th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    ${Array.from({ length: 6 }).map(() => `
                        <tr>
                            <td colspan="7"><div class="skeleton-row"></div></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    },

    renderEmptyState() {
        return `
            <div class="empty-state card" style="margin: 24px 0;">
                <div class="empty-state-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                </div>
                <h3 style="font-size: 16px; font-weight: 600; color: var(--foreground); margin-top: 8px;">No history yet</h3>
                <p style="font-size: 14px; margin-top: 4px; max-width: 320px;">Run your first scan to see execution logs and details here.</p>
                <div style="display: flex; gap: 12px; margin-top: 24px;">
                    <button class="btn btn-primary btn-sm" onclick="App.router.navigate('scan-operations')">Run Scan</button>
                    <button class="btn btn-outline btn-sm" onclick="window.open('https://github.com/mlem16/COD_CHECK', '_blank')">Learn More</button>
                </div>
            </div>
        `;
    },

    renderErrorState() {
        return `
            <div class="empty-state card" style="margin: 24px 0; border-color: var(--red-200); background: var(--red-50);">
                <div class="empty-state-icon" style="background: var(--red-100); color: var(--red-500);">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                </div>
                <h3 style="font-size: 16px; font-weight: 600; color: var(--red-600); margin-top: 8px;">Failed to load history</h3>
                <p style="font-size: 14px; color: var(--red-500); margin-top: 4px;">Something went wrong while fetching logs from the database.</p>
                <div style="margin-top: 24px;">
                    <button class="btn btn-primary btn-sm" onclick="HistoryPage.load()" style="background: var(--red-600); border-color: var(--red-600);">Retry Loading</button>
                </div>
            </div>
        `;
    },

    renderDataTable(items) {
        return `
            <div style="overflow-x:auto">
                <table class="history-table" id="history-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Task</th>
                            <th>Status</th>
                            <th>Device</th>
                            <th>Duration</th>
                            <th>Reliable</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${items.map((item, idx) => this.renderDataRow(item, idx)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    },

    renderDataRow(item, index) {
        const rowId = String(item.id || `${item.serial || 'device'}-${item.started_at || item.created_at || index}`);
        const status = this.normalizeStatus(item.status);
        const statusClass = status === 'SUCCESS' ? 'success' : status === 'FAILED' ? 'failed' : status === 'RUNNING' ? 'running' : 'neutral';
        const time = item.started_at ? new Date(item.started_at).toLocaleString() : (item.created_at || '--');
        const duration = item.duration_ms ? `${(item.duration_ms / 1000).toFixed(2)}s` : '--';
        const reliability = this.getReliabilityInfo(item);
        const isExpanded = this.state.expandedRowId === rowId;
        const deviceLabel = item.emu_name ? `${item.emu_name} (${item.serial})` : (item.serial || '--');
        const sourceBadge = item.source === 'full_scan'
            ? '<span class="badge badge-outline" style="font-size:10px;margin-left:4px;">scan</span>'
            : '';

        return `
            <tr class="history-data-row ${isExpanded ? 'expanded' : ''}" data-row-id="${rowId}">
                <td class="text-sm text-mono">${time}</td>
                <td><span class="badge badge-outline" style="text-transform:capitalize">${item.task_type || 'unknown'}</span>${sourceBadge}</td>
                <td><span class="status-badge ${statusClass}">${status}</span></td>
                <td class="text-mono">${deviceLabel}</td>
                <td class="text-mono">${duration}</td>
                <td><span class="reliability ${reliability.className}">${reliability.icon} ${reliability.value}</span></td>
                <td><button class="btn btn-ghost btn-sm" data-toggle-row="${rowId}">${isExpanded ? 'Hide' : 'View'} details</button></td>
            </tr>
            <tr class="history-expand-row ${isExpanded ? 'open' : ''}">
                <td colspan="7">
                    <div class="expand-panel">
                        <div class="expand-title">Script Output & Execution Details</div>
                        <div class="expand-grid">
                            <div>
                                <strong>📋 Output Data</strong>
                                <pre>${item.data ? this.safeJson(item.data) : 'No data output'}</pre>
                            </div>
                            <div>
                                <strong>📊 Status Info</strong>
                                <pre>${this.safeJson({
            task_type: item.task_type,
            status: status,
            source: item.source || 'system',
            duration: duration,
            started: item.started_at,
            finished: item.finished_at || '--',
        })}</pre>
                            </div>
                            <div>
                                <strong>❌ Errors</strong>
                                <pre>${item.error ? item.error : 'None'}</pre>
                            </div>
                            <div>
                                <strong>📝 Logs</strong>
                                <pre>${item.logs && item.logs.length ? item.logs.join('\n') : 'No detailed logs'}</pre>
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    },

    safeJson(value) {
        try {
            if (typeof value === 'string') return value;
            return JSON.stringify(value, null, 2);
        } catch (e) {
            return '--';
        }
    },

    toggleRow(rowId) {
        this.state.expandedRowId = this.state.expandedRowId === rowId ? null : rowId;
        this.renderContent();
    },

    normalizeStatus(status) {
        const value = String(status || 'UNKNOWN').toUpperCase();
        if (value === 'COMPLETED') return 'SUCCESS';
        if (value === 'ERROR') return 'FAILED';
        return value;
    },

    getReliabilityInfo(item) {
        if (typeof item.reliability === 'number') {
            if (item.reliability >= 80) return { value: `${item.reliability}%`, className: 'high', icon: '🟢' };
            if (item.reliability >= 50) return { value: `${item.reliability}%`, className: 'medium', icon: '🟡' };
            return { value: `${item.reliability}%`, className: 'low', icon: '🔴' };
        }

        if (item.is_reliable) return { value: '100%', className: 'high', icon: '🟢' };
        return { value: '40%', className: 'low', icon: '🔴' };
    },

    bindInlineEvents() {
        // ... (existing filter bindings)
        const filterDate = document.getElementById('history-filter-date');
        const filterDevice = document.getElementById('history-filter-device');
        const filterStatus = document.getElementById('history-filter-status');
        const filterTask = document.getElementById('history-filter-task');

        [
            [filterDate, 'date'],
            [filterDevice, 'device'],
            [filterStatus, 'status'],
            [filterTask, 'task'],
        ].forEach(([el, key]) => {
            if (!el) return;
            el.onchange = (event) => {
                this.state.filters[key] = event.target.value;
                this.renderContent();
            };
        });

        document.querySelectorAll('[data-quick]').forEach((chip) => {
            chip.onclick = () => {
                this.state.filters.quick = chip.dataset.quick;
                this.renderContent();
            };
        });

        const stateArea = document.getElementById('history-state-area');
        if (stateArea) {
            stateArea.onclick = (e) => {
                const btn = e.target.closest('[data-toggle-row]');
                if (btn) {
                    const rowId = btn.dataset.toggleRow;
                    this.toggleRow(rowId);

                    const actionBtn = e.target.closest('[data-action]');
                    if (actionBtn) {
                        const action = actionBtn.dataset.action;
                        if (action === 'retry-load') return this.load();
                        if (action === 'run-scan') return App.router.navigate('scan-operations');
                        if (action === 'learn-more') return window.open('https://github.com/mlem16/COD_CHECK', '_blank');
                    }
                } else {
                    const actionBtn = e.target.closest('[data-action]');
                    if (actionBtn) {
                        const action = actionBtn.dataset.action;
                        if (action === 'retry-load') return this.load();
                        if (action === 'run-scan') return App.router.navigate('scan-operations');
                        if (action === 'learn-more') return window.open('https://github.com/mlem16/COD_CHECK', '_blank');
                    }
                }
            };
        }
    }
};
