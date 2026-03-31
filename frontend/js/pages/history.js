const HistoryPage = {
    state: {
        loading: false,
        error: null,
        items: [],
        activeTab: 'history',
        debugLogs: [],
        debugLoading: false,
        debugStatusFilter: 'active',
        debugFilter: 'all',
        debugResolveDraft: null,
        debugResolveSaving: false,
        debugDetailLog: null,
        debugDetailClosing: false,
        lightboxSrc: null,
        logsSummary: { serials: [], dates: [], files: [], grouped_files: {} },
        logsLoading: false,
        logsError: null,
        logsSelectedSerial: '',
        logsSelectedDate: '',
        logsSelectedPathToken: '',
        logsContentRaw: '',
        logsLineNumbers: [],
        logsSearch: '',
        logsSearchTimer: null,
        logsLevel: 'all',
        logsContextAnchorLine: null,
        logsContextRadius: 12,
        logsWrap: false,
        logsSidebarCollapsed: false,
        logsAutoRefresh: true,
        logsPollTimer: null,
        logsTail: 500,
        logsOffset: 0,
        logsHasMoreBefore: false,
        logsMeta: null,
        logsScrollState: null,
        filters: { search: '', date: 'all', device: 'all', status: 'all', task: 'all', quick: 'all' },
        expandedRowId: null,
        useMockData: false,
    },

    mockItems: [
        { id: 'mock-1', task_id: 'A1B2C3D4', task_type: 'resources', serial: 'emulator-5554', status: 'SUCCESS', data: { gold: { total: 1023000 }, wood: { total: 780000 } }, error: null, is_reliable: true, reliability: 97, started_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(), duration_ms: 8100, logs: ['Navigate resources page', 'OCR complete', 'Validation passed'] },
        { id: 'mock-2', task_id: 'E5F6G7H8', task_type: 'hall', serial: 'emulator-5556', status: 'FAILED', data: {}, error: 'OCR timeout while parsing hall level', is_reliable: false, reliability: 41, started_at: new Date(Date.now() - 40 * 60 * 1000).toISOString(), duration_ms: 35450, logs: ['Capture screenshot', 'OCR retry x3', 'Task failed'] },
        { id: 'mock-3', task_id: 'I9J0K1L2', task_type: 'manual', serial: 'emulator-5560', status: 'RUNNING', data: { step: 'processing market panel' }, error: null, is_reliable: true, reliability: 72, started_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(), duration_ms: 18400, logs: ['Task queued', 'Navigating', 'Processing OCR'] },
    ],

    render() {
        return `
            <div class="page-enter history-page" id="history-page-root">
                <div class="page-header">
                    <div class="page-header-info">
                        <h2>History & Logs</h2>
                        <p>Track execution history, debug screenshots, and workflow logs in one place.</p>
                    </div>
                    <div class="page-actions">
                        <div class="search-wrapper">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                            <input id="history-search" class="search-input" type="text" placeholder="Search task, device..." value="${this.state.filters.search}">
                        </div>
                        <button id="history-refresh-btn" class="btn btn-outline btn-sm" onclick="HistoryPage.refreshActiveTab()">
                            <svg class="refresh-icon" style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Refresh
                        </button>
                    </div>
                </div>
                <div class="history-tabs" id="history-tabs">
                    <button class="history-tab history-tab--active" id="tab-history" data-tab="history">History</button>
                    <button class="history-tab" id="tab-debug" data-tab="debug">Debug</button>
                    <button class="history-tab" id="tab-logs" data-tab="logs">Logs</button>
                </div>
                <div id="history-tab-content">
                    <div id="history-panel">
                        <div class="history-filter-bar" id="history-filter-bar"></div>
                        <div class="history-quick-filters" id="history-quick-filters"></div>
                        <div class="card history-table-card" id="history-state-area"></div>
                    </div>
                    <div id="debug-panel" style="display:none;"></div>
                    <div id="logs-panel" style="display:none;"></div>
                </div>
                <div class="history-footer" id="history-footer">Showing 0 results</div>
            </div>
            <div class="lightbox" id="debug-lightbox" onclick="HistoryPage.closeLightbox()">
                <img class="lightbox__image" id="debug-lightbox-img" />
            </div>
        `;
    },

    async init() {
        this.bindEvents();
        this.ensureDebugModalRoot();
        await this.load();
    },
    destroy() {
        this.stopLogsPolling();
        if (this.state.logsSearchTimer) {
            clearTimeout(this.state.logsSearchTimer);
            this.state.logsSearchTimer = null;
        }
        this._unlockDebugModalScroll();
        this._unbindDebugDetailKeyboard();
        clearTimeout(this._debugDetailCloseTimer);
        document.getElementById('history-debug-modal-root')?.remove();
    },

    bindEvents() {
        const search = document.getElementById('history-search');
        if (search) search.addEventListener('input', (event) => {
            this.state.filters.search = event.target.value || '';
            if (this.state.activeTab === 'history') this.renderContent();
        });
        document.querySelectorAll('#history-tabs [data-tab]').forEach(btn => btn.addEventListener('click', () => this.switchTab(btn.dataset.tab)));
    },

    ensureDebugModalRoot() {
        if (document.getElementById('history-debug-modal-root')) return;
        const host = document.createElement('div');
        host.id = 'history-debug-modal-root';
        document.body.appendChild(host);
    },

    async refreshActiveTab() {
        if (this.state.activeTab === 'debug') return this.loadDebugLogs();
        if (this.state.activeTab === 'logs') return this.refreshWorkflowLogs();
        return this.load();
    },

    async switchTab(tab) {
        this.state.activeTab = tab;
        const historyPanel = document.getElementById('history-panel');
        const debugPanel = document.getElementById('debug-panel');
        const logsPanel = document.getElementById('logs-panel');
        ['tab-history', 'tab-debug', 'tab-logs'].forEach((id) => document.getElementById(id)?.classList.remove('history-tab--active'));
        this.stopLogsPolling();
        if (historyPanel) historyPanel.style.display = tab === 'history' ? '' : 'none';
        if (debugPanel) debugPanel.style.display = tab === 'debug' ? '' : 'none';
        if (logsPanel) logsPanel.style.display = tab === 'logs' ? '' : 'none';
        if (tab === 'history') {
            document.getElementById('tab-history')?.classList.add('history-tab--active');
            this.renderContent();
            return;
        }
        if (tab === 'debug') {
            document.getElementById('tab-debug')?.classList.add('history-tab--active');
            await this.loadDebugLogs();
            return;
        }
        document.getElementById('tab-logs')?.classList.add('history-tab--active');
        await this.refreshWorkflowLogs();
        this.startLogsPolling();
    },

    async loadDebugLogs() {
        const panel = document.getElementById('debug-panel');
        if (!panel) return;
        this.state.debugLoading = true;
        panel.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted-foreground);">Loading debug logs...</div>';
        try {
            this.state.debugLogs = await API.getDebugLogs(null, 200, this.state.debugStatusFilter);
        } catch (e) {
            this.state.debugLogs = [];
            console.warn('[Debug] Failed to load logs:', e);
        } finally {
            this.state.debugLoading = false;
            this.renderDebugPanel();
        }
    },

    getVisibleDebugLogs() {
        if (this.state.debugFilter === 'all') return this.state.debugLogs;
        return this.state.debugLogs.filter((log) => log.serial === this.state.debugFilter);
    },

    renderDebugPanel() {
        const panel = document.getElementById('debug-panel');
        const footer = document.getElementById('history-footer');
        if (!panel) return;
        const devices = ['all', ...new Set(this.state.debugLogs.map(l => l.serial).filter(Boolean))];
        const visibleLogs = this.getVisibleDebugLogs();
        const isResolvedView = this.state.debugStatusFilter === 'resolved';
        const filterHtml = `
            <div class="debug-toolbar card">
                <div class="debug-toolbar__identity">
                    <div class="debug-toolbar__kicker">Issue Review Console</div>
                    <div class="debug-toolbar__title-row">
                        <h3 class="debug-toolbar__title">Debug</h3>
                        <span class="debug-toolbar__pill">${isResolvedView ? 'Resolved' : 'Active'}</span>
                        <span class="debug-toolbar__pill">${visibleLogs.length} item${visibleLogs.length === 1 ? '' : 's'}</span>
                    </div>
                    <p class="debug-toolbar__subtitle">Review failure screenshots, mark fixed issues, and keep active problems separated from resolved ones.</p>
                </div>
                <div class="debug-toolbar__controls">
                    <div class="debug-toolbar__group">
                        <label class="debug-toolbar__label">View</label>
                        <div class="debug-segmented">
                            <button class="debug-segmented__btn ${this.state.debugStatusFilter === 'active' ? 'is-active' : ''}" data-debug-status="active">Active</button>
                            <button class="debug-segmented__btn ${this.state.debugStatusFilter === 'resolved' ? 'is-active' : ''}" data-debug-status="resolved">Resolved</button>
                        </div>
                    </div>
                    <div class="debug-toolbar__group">
                        <label class="debug-toolbar__label">Device</label>
                        <select id="debug-device-filter" class="form-select debug-device-filter">
                            ${devices.map(d => `<option value="${d}" ${d === this.state.debugFilter ? 'selected' : ''}>${d === 'all' ? 'All devices' : d}</option>`).join('')}
                        </select>
                    </div>
                    <div class="debug-toolbar__actions">
                        <button class="btn btn-outline btn-sm" onclick="HistoryPage.loadDebugLogs()">Refresh</button>
                        <button class="btn btn-outline btn-sm" onclick="HistoryPage.exportDebugLogs()">Export</button>
                        <button class="btn btn-outline btn-sm" onclick="HistoryPage.clearDebugLogs()" style="color:var(--red-500);border-color:var(--red-300);">Clear</button>
                    </div>
                </div>
            </div>
        `;
        if (!visibleLogs.length) {
            const emptyTitle = isResolvedView ? 'No resolved issues' : 'No active issues';
            const emptyDesc = isResolvedView
                ? 'Resolved debug entries will appear here after you mark issues as fixed.'
                : 'Error screenshots will appear here when workflow functions fail.';
            panel.innerHTML = filterHtml + `<div class="card debug-empty"><div class="debug-empty__title">${emptyTitle}</div><p class="debug-empty__desc">${emptyDesc}</p></div>`;
            if (footer) footer.textContent = `0 ${this.state.debugStatusFilter} debug entries`;
            this._bindDebugFilter();
            return;
        }
        panel.innerHTML = filterHtml + `<div class="debug-grid">${visibleLogs.map(log => this._renderDebugCard(log)).join('')}</div>`;
        if (footer) footer.textContent = `${visibleLogs.length} ${this.state.debugStatusFilter} debug entr${visibleLogs.length === 1 ? 'y' : 'ies'}`;
        this._bindDebugFilter();
        this.renderDebugModalPortal();
    },

    _getErrorCodeClass(code) {
        if (code.startsWith('NAV_')) return 'debug-card__code--nav';
        if (code.startsWith('TEMPLATE_')) return 'debug-card__code--template';
        if (code.startsWith('ADB_')) return 'debug-card__code--adb';
        if (code.startsWith('TIMEOUT_')) return 'debug-card__code--timeout';
        if (code.startsWith('CONFIG_')) return 'debug-card__code--config';
        return 'debug-card__code--unknown';
    },

    _renderDebugCard(log) {
        const time = log.created_at ? this.formatVietnamDateTime(log.created_at) : '--';
        const code = log.error_code || 'UNKNOWN';
        const fn = log.function_name || '--';
        const serial = log.serial || '--';
        const isResolved = !!log.is_resolved;
        const screenshotPath = log.screenshot_path || '';
        const resolvedNote = log.resolved_note || '';
        let imgUrl = '';
        if (screenshotPath) {
            const parts = screenshotPath.replace(/\\/g, '/').split('debug_captures/');
            if (parts.length > 1) imgUrl = `/debug_captures/${parts[1]}`;
        }
        return `
            <div class="debug-card ${isResolved ? 'debug-card--resolved' : ''}">
                ${imgUrl ? `<div class="debug-card__image" onclick="HistoryPage.openLightbox('${imgUrl}')"><img src="${imgUrl}" onerror="this.parentElement.style.display='none'" /><button class="debug-card__copy-btn" onclick="event.stopPropagation(); HistoryPage.copyDebugImage('${imgUrl}', this)"><span>Copy</span></button></div>` : `<div class="debug-card__no-image">No screenshot</div>`}
                <div class="debug-card__body">
                    <div class="debug-card__header">
                        <span class="debug-card__code ${this._getErrorCodeClass(code)}">${code}</span>
                        ${isResolved ? '<span class="debug-card__status">Resolved</span>' : '<span class="debug-card__status debug-card__status--active">Active</span>'}
                        <span class="debug-card__time">${time}</span>
                    </div>
                    <div class="debug-card__message">${log.error_message || 'No message'}</div>
                    <div class="debug-card__meta"><span>${serial}</span><span>${fn}</span><span>${log.activity_id || '--'}</span></div>
                    ${isResolved ? `<div class="debug-card__resolved-note">${this.escapeHtml(resolvedNote)}</div>` : ''}
                    <div class="debug-card__actions">
                        ${isResolved
                            ? `<button class="btn btn-outline btn-sm" onclick="HistoryPage.unresolveDebugLog(${log.id})">Unresolve</button>`
                            : `<button class="btn btn-primary btn-sm" onclick="HistoryPage.openDebugResolve(${log.id})">Resolve</button>`}
                        <button class="btn btn-outline btn-sm" onclick="HistoryPage.openDebugDetails(${log.id})">View details</button>
                    </div>
                </div>
            </div>
        `;
    },

    _renderDebugResolveModal() {
        const draft = this.state.debugResolveDraft;
        if (!draft) return '';
        const time = draft.created_at ? this.formatVietnamDateTime(draft.created_at) : '--';
        const screenshotPath = draft.screenshot_path || '';
        let imgUrl = '';
        if (screenshotPath) {
            const parts = screenshotPath.replace(/\\/g, '/').split('debug_captures/');
            if (parts.length > 1) imgUrl = `/debug_captures/${parts[1]}`;
        }
        return `
            <div class="debug-detail-overlay" id="debug-resolve-overlay" role="presentation">
                <div class="debug-detail-modal debug-resolve-surface" id="debug-resolve-dialog" role="dialog" aria-modal="true" aria-labelledby="debug-resolve-title" onclick="event.stopPropagation()" tabindex="-1">
                    <div class="debug-detail-head">
                        <div class="debug-detail-head__copy">
                            <div class="debug-detail-kicker">Resolve Inspector</div>
                            <div class="confirm-modal-title" id="debug-resolve-title">Resolve debug issue</div>
                            <div class="debug-detail-subtitle">Capture what was fixed, who resolved it, and keep the original issue context attached to this entry.</div>
                        </div>
                        <div class="debug-detail-badges">
                            <span class="debug-card__status debug-card__status--active">Resolve</span>
                            <button class="debug-detail-close" id="debug-resolve-close-icon" aria-label="Close resolve dialog">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                            </button>
                        </div>
                    </div>
                    <div class="debug-detail-code-row">
                        <span class="debug-card__code ${this._getErrorCodeClass(draft.error_code || 'UNKNOWN')}">${this.escapeHtml(draft.error_code || 'UNKNOWN')}</span>
                        <span class="debug-detail-code-row__hint">${this.escapeHtml(draft.function_name || '--')}</span>
                    </div>
                    ${imgUrl ? `<button class="debug-detail-preview" onclick="HistoryPage.openLightbox('${imgUrl}')"><img src="${imgUrl}" alt="Debug screenshot preview"></button>` : ''}
                    <div class="debug-detail-meta-grid debug-resolve-meta-grid">
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Time</span><span class="debug-detail-stat__value">${this.escapeHtml(time)}</span></div>
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Serial</span><span class="debug-detail-stat__value">${this.escapeHtml(draft.serial || '--')}</span></div>
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Function</span><span class="debug-detail-stat__value">${this.escapeHtml(draft.function_name || '--')}</span></div>
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Activity</span><span class="debug-detail-stat__value">${this.escapeHtml(draft.activity_id || '--')}</span></div>
                    </div>
                    <div class="debug-resolve-form">
                        <label class="debug-resolve-field" for="debug-resolve-note">
                            <span class="debug-resolve-field__label">Resolve note</span>
                            <textarea id="debug-resolve-note" class="form-input debug-resolve-textarea" rows="5" placeholder="Describe what was fixed or why this issue is resolved...">${this.escapeHtml(draft.resolved_note || '')}</textarea>
                        </label>
                        <label class="debug-resolve-field" for="debug-resolve-by">
                            <span class="debug-resolve-field__label">Resolved by</span>
                            <input id="debug-resolve-by" class="form-input" type="text" placeholder="Name or alias" value="${this.escapeHtml(draft.resolved_by || '')}">
                        </label>
                    </div>
                    <section class="debug-detail-panel debug-detail-panel--message">
                        <div class="debug-detail-panel__title"><span class="debug-detail-panel__icon">!</span>Error message</div>
                        <div class="debug-detail-panel__body">${this.escapeHtml(draft.error_message || '--')}</div>
                    </section>
                    <div class="confirm-modal-actions debug-detail-actions">
                        <button class="btn btn-outline" id="debug-resolve-cancel">Cancel</button>
                        <button class="btn btn-primary" id="debug-resolve-save" ${this.state.debugResolveSaving ? 'disabled' : ''}>${this.state.debugResolveSaving ? 'Saving...' : 'Save resolve'}</button>
                    </div>
                </div>
            </div>
        `;
    },

    _renderDebugDetailModal() {
        const log = this.state.debugDetailLog;
        if (!log) return '';
        const time = log.created_at ? this.formatVietnamDateTime(log.created_at) : '--';
        const resolvedAt = log.resolved_at ? this.formatVietnamDateTime(log.resolved_at) : '--';
        const screenshotPath = log.screenshot_path || '';
        const isResolved = !!log.is_resolved;
        let imgUrl = '';
        if (screenshotPath) {
            const parts = screenshotPath.replace(/\\/g, '/').split('debug_captures/');
            if (parts.length > 1) imgUrl = `/debug_captures/${parts[1]}`;
        }
        return `
            <div class="debug-detail-overlay ${this.state.debugDetailClosing ? 'is-closing' : ''}" id="debug-detail-overlay" role="presentation">
                <div class="debug-detail-modal ${this.state.debugDetailClosing ? 'is-closing' : ''}" id="debug-detail-dialog" role="dialog" aria-modal="true" aria-labelledby="debug-detail-title" onclick="event.stopPropagation()" tabindex="-1">
                    <div class="debug-detail-head">
                        <div class="debug-detail-head__copy">
                            <div class="debug-detail-kicker">Issue Inspector</div>
                            <div class="confirm-modal-title" id="debug-detail-title">Debug issue details</div>
                            <div class="debug-detail-subtitle">Review the captured state, compare metadata, and copy the issue summary without leaving the viewport.</div>
                        </div>
                        <div class="debug-detail-badges">
                            <span class="debug-card__status ${isResolved ? '' : 'debug-card__status--active'}">${isResolved ? 'Resolved' : 'Active'}</span>
                            <button class="debug-detail-close" id="debug-detail-close-icon" aria-label="Close issue details">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                            </button>
                        </div>
                    </div>
                    <div class="debug-detail-code-row">
                        <span class="debug-card__code ${this._getErrorCodeClass(log.error_code || 'UNKNOWN')}">${this.escapeHtml(log.error_code || 'UNKNOWN')}</span>
                        <span class="debug-detail-code-row__hint">${this.escapeHtml(log.function_name || '--')}</span>
                    </div>
                    ${imgUrl ? `<button class="debug-detail-preview" onclick="HistoryPage.openLightbox('${imgUrl}')"><img src="${imgUrl}" alt="Debug screenshot preview"></button>` : ''}
                    <div class="debug-detail-meta-grid">
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Function</span><span class="debug-detail-stat__value">${this.escapeHtml(log.function_name || '--')}</span></div>
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Serial</span><span class="debug-detail-stat__value">${this.escapeHtml(log.serial || '--')}</span></div>
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Activity</span><span class="debug-detail-stat__value">${this.escapeHtml(log.activity_id || '--')}</span></div>
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Created</span><span class="debug-detail-stat__value">${this.escapeHtml(time)}</span></div>
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Resolved at</span><span class="debug-detail-stat__value">${this.escapeHtml(resolvedAt)}</span></div>
                        <div class="debug-detail-stat"><span class="debug-detail-stat__label">Resolved by</span><span class="debug-detail-stat__value">${this.escapeHtml(log.resolved_by || '--')}</span></div>
                    </div>
                    <div class="debug-detail-panels">
                        <section class="debug-detail-panel">
                            <div class="debug-detail-panel__title">Resolve note</div>
                            <div class="debug-detail-panel__body">${this.escapeHtml(log.resolved_note || '--')}</div>
                        </section>
                        <section class="debug-detail-panel debug-detail-panel--message">
                            <div class="debug-detail-panel__title"><span class="debug-detail-panel__icon">!</span>Error message</div>
                            <div class="debug-detail-panel__body">${this.escapeHtml(log.error_message || '--')}</div>
                        </section>
                    </div>
                    <div class="confirm-modal-actions debug-detail-actions">
                        <button class="btn btn-outline" id="debug-detail-copy">Copy details</button>
                        <button class="btn btn-primary" id="debug-detail-close">Close</button>
                    </div>
                </div>
            </div>
        `;
    },

    async copyDebugImage(imgUrl, btnEl) {
        try {
            const response = await fetch(imgUrl);
            const blob = await response.blob();
            const pngBlob = await this._convertToPng(blob);
            await navigator.clipboard.write([new ClipboardItem({ 'image/png': pngBlob })]);
            const label = btnEl?.querySelector('span');
            if (label) {
                label.textContent = 'Copied';
                setTimeout(() => { label.textContent = 'Copy'; }, 1200);
            }
        } catch (err) {
            console.warn('[Debug] Failed to copy image:', err);
            Toast.error('Copy failed', 'Could not copy image to clipboard');
        }
    },

    _convertToPng(blob) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                canvas.width = img.naturalWidth;
                canvas.height = img.naturalHeight;
                canvas.getContext('2d').drawImage(img, 0, 0);
                canvas.toBlob((pngBlob) => pngBlob ? resolve(pngBlob) : reject(new Error('Canvas toBlob returned null')), 'image/png');
            };
            img.onerror = () => reject(new Error('Failed to load image'));
            img.src = URL.createObjectURL(blob);
        });
    },

    openLightbox(src) {
        const lb = document.getElementById('debug-lightbox');
        const img = document.getElementById('debug-lightbox-img');
        if (lb && img) {
            img.src = src;
            lb.classList.add('lightbox--open');
        }
    },

    closeLightbox() { document.getElementById('debug-lightbox')?.classList.remove('lightbox--open'); },

    _bindDebugFilter() {
        const sel = document.getElementById('debug-device-filter');
        if (sel) sel.onchange = (e) => { this.state.debugFilter = e.target.value; this.loadDebugLogs(); };
        document.querySelectorAll('[data-debug-status]').forEach((btn) => {
            btn.onclick = () => {
                this.state.debugStatusFilter = btn.dataset.debugStatus || 'active';
                this.state.debugResolveDraft = null;
                this.closeDebugDetails(true);
                this.loadDebugLogs();
            };
        });
    },

    _bindDebugResolveModal() {
        const overlay = document.getElementById('debug-resolve-overlay');
        const cancelBtn = document.getElementById('debug-resolve-cancel');
        const saveBtn = document.getElementById('debug-resolve-save');
        const closeIconBtn = document.getElementById('debug-resolve-close-icon');
        if (overlay) overlay.onclick = (event) => { if (event.target === overlay) this.closeDebugResolve(); };
        if (cancelBtn) cancelBtn.onclick = () => this.closeDebugResolve();
        if (saveBtn) saveBtn.onclick = () => this.submitDebugResolve();
        if (closeIconBtn) closeIconBtn.onclick = () => this.closeDebugResolve();
    },

    renderDebugModalPortal() {
        this.ensureDebugModalRoot();
        const host = document.getElementById('history-debug-modal-root');
        if (!host) return;
        if (!this.state.debugDetailLog && !this.state.debugResolveDraft) {
            host.innerHTML = '';
            this._unlockDebugModalScroll();
            this._unbindDebugDetailKeyboard();
            return;
        }
        host.innerHTML = this.state.debugResolveDraft ? this._renderDebugResolveModal() : this._renderDebugDetailModal();
        this._lockDebugModalScroll();
        if (this.state.debugResolveDraft) {
            this._bindDebugResolveModal();
        } else {
            this._bindDebugDetailModal();
        }
        this._bindDebugDetailKeyboard();
        requestAnimationFrame(() => (document.getElementById('debug-resolve-dialog') || document.getElementById('debug-detail-dialog'))?.focus());
    },

    _bindDebugDetailModal() {
        const overlay = document.getElementById('debug-detail-overlay');
        const closeBtn = document.getElementById('debug-detail-close');
        const closeIconBtn = document.getElementById('debug-detail-close-icon');
        const copyBtn = document.getElementById('debug-detail-copy');
        if (overlay) overlay.onclick = (event) => { if (event.target === overlay) this.closeDebugDetails(); };
        if (closeBtn) closeBtn.onclick = () => this.closeDebugDetails();
        if (closeIconBtn) closeIconBtn.onclick = () => this.closeDebugDetails();
        if (copyBtn) copyBtn.onclick = () => this.copyDebugDetails();
    },

    _bindDebugDetailKeyboard() {
        this._unbindDebugDetailKeyboard();
        this._debugDetailKeyHandler = (event) => {
            if (!this.state.debugDetailLog && !this.state.debugResolveDraft) return;
            if (event.key === 'Escape') {
                event.preventDefault();
                if (this.state.debugResolveDraft) this.closeDebugResolve();
                else this.closeDebugDetails();
                return;
            }
            if (event.key !== 'Tab') return;
            const dialog = document.getElementById('debug-resolve-dialog') || document.getElementById('debug-detail-dialog');
            if (!dialog) return;
            const focusable = Array.from(dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter((el) => !el.hasAttribute('disabled'));
            if (!focusable.length) return;
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        };
        document.addEventListener('keydown', this._debugDetailKeyHandler);
    },

    _unbindDebugDetailKeyboard() {
        if (this._debugDetailKeyHandler) {
            document.removeEventListener('keydown', this._debugDetailKeyHandler);
            this._debugDetailKeyHandler = null;
        }
    },

    _lockDebugModalScroll() {
        if (this._debugModalScrollLocked) return;
        this._debugPreviousBodyOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        this._debugModalScrollLocked = true;
    },

    _unlockDebugModalScroll() {
        if (!this._debugModalScrollLocked) return;
        document.body.style.overflow = this._debugPreviousBodyOverflow || '';
        this._debugPreviousBodyOverflow = '';
        this._debugModalScrollLocked = false;
    },

    async copyDebugDetails() {
        const log = this.state.debugDetailLog;
        if (!log) return;
        const text = [
            `Error code: ${log.error_code || 'UNKNOWN'}`,
            `Function: ${log.function_name || '--'}`,
            `Activity: ${log.activity_id || '--'}`,
            `Serial: ${log.serial || '--'}`,
            `Created: ${log.created_at ? this.formatVietnamDateTime(log.created_at) : '--'}`,
            `Resolved at: ${log.resolved_at ? this.formatVietnamDateTime(log.resolved_at) : '--'}`,
            `Resolved by: ${log.resolved_by || '--'}`,
            `Resolve note: ${log.resolved_note || '--'}`,
            `Error message: ${log.error_message || '--'}`,
        ].join('\n');
        try {
            await navigator.clipboard.writeText(text);
            Toast.success('Copied', 'Issue details copied');
        } catch (e) {
            console.warn('[Debug] Copy details failed:', e);
            Toast.error('Copy failed', 'Could not copy issue details');
        }
    },

    openDebugResolve(logId) {
        const found = this.state.debugLogs.find((log) => String(log.id) === String(logId));
        if (!found) return;
        this.state.debugResolveDraft = { ...found };
        this.state.debugResolveSaving = false;
        this.renderDebugModalPortal();
        requestAnimationFrame(() => document.getElementById('debug-resolve-note')?.focus());
    },

    closeDebugResolve() {
        this.state.debugResolveDraft = null;
        this.state.debugResolveSaving = false;
        this.renderDebugModalPortal();
    },

    async submitDebugResolve() {
        const draft = this.state.debugResolveDraft;
        if (!draft) return;
        const noteEl = document.getElementById('debug-resolve-note');
        const byEl = document.getElementById('debug-resolve-by');
        const note = String(noteEl?.value || '').trim();
        const resolvedBy = String(byEl?.value || '').trim();
        if (!note) {
            Toast.error('Resolve note required', 'Please enter a short resolve note');
            noteEl?.focus();
            return;
        }
        this.state.debugResolveSaving = true;
        this.renderDebugModalPortal();
        try {
            await API.resolveDebugLog(draft.id, { resolved_note: note, resolved_by: resolvedBy });
            Toast.success('Resolved', 'Debug issue marked as resolved');
            this.state.debugResolveDraft = null;
            this.state.debugResolveSaving = false;
            await this.loadDebugLogs();
        } catch (e) {
            console.warn('[Debug] Resolve failed:', e);
            this.state.debugResolveSaving = false;
            Toast.error('Resolve failed', e.message || 'Could not resolve debug issue');
            this.renderDebugModalPortal();
        }
    },

    async unresolveDebugLog(logId) {
        try {
            await API.unresolveDebugLog(logId);
            Toast.success('Reopened', 'Debug issue moved back to active');
            if (this.state.debugDetailLog && String(this.state.debugDetailLog.id) === String(logId)) this.closeDebugDetails(true);
            await this.loadDebugLogs();
        } catch (e) {
            console.warn('[Debug] Unresolve failed:', e);
            Toast.error('Unresolve failed', e.message || 'Could not reopen debug issue');
        }
    },

    openDebugDetails(logId) {
        const found = this.state.debugLogs.find((log) => String(log.id) === String(logId));
        if (!found) return;
        this.state.debugDetailClosing = false;
        this.state.debugDetailLog = { ...found };
        this.renderDebugModalPortal();
    },

    closeDebugDetails(immediate = false) {
        if (!this.state.debugDetailLog) return;
        if (immediate) {
            this.state.debugDetailClosing = false;
            this.state.debugDetailLog = null;
            this.renderDebugModalPortal();
            return;
        }
        this.state.debugDetailClosing = true;
        this.renderDebugModalPortal();
        clearTimeout(this._debugDetailCloseTimer);
        this._debugDetailCloseTimer = setTimeout(() => {
            this.state.debugDetailClosing = false;
            this.state.debugDetailLog = null;
            this.renderDebugModalPortal();
        }, 180);
    },

    async clearDebugLogs() {
        const count = this.getVisibleDebugLogs().length;
        if (!count) return;
        const serial = this.state.debugFilter === 'all' ? null : this.state.debugFilter;
        const statusLabel = this.state.debugStatusFilter === 'resolved' ? 'resolved' : 'active';
        if (!confirm(`Clear ${count} ${statusLabel} debug log(s)${serial ? ` for ${serial}` : ''}? This also deletes screenshot files.`)) return;
        try {
            const res = await API.clearDebugLogs(serial, this.state.debugStatusFilter);
            Toast.success('Cleared', `${res.deleted} debug log(s) deleted`);
        } catch (e) {
            console.warn('[Debug] Clear failed:', e);
            Toast.error('Error', 'Failed to clear debug logs');
        }
        await this.loadDebugLogs();
    },

    exportDebugLogs() {
        const visibleLogs = this.getVisibleDebugLogs();
        if (!visibleLogs.length) return;
        const headers = ['time', 'serial', 'error_code', 'error_message', 'function_name', 'activity_id', 'is_resolved', 'resolved_at', 'resolved_note', 'resolved_by'];
        const rows = visibleLogs.map(log => [
            log.created_at || '',
            log.serial || '',
            log.error_code || '',
            (log.error_message || '').replace(/"/g, '""'),
            log.function_name || '',
            log.activity_id || '',
            log.is_resolved ? '1' : '0',
            log.resolved_at || '',
            (log.resolved_note || '').replace(/"/g, '""'),
            log.resolved_by || '',
        ]);
        const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `debug_logs_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    },

    async load() {
        this.state.loading = true;
        this.state.error = null;
        this.renderContent();
        document.getElementById('history-refresh-btn')?.classList.add('is-spinning');
        try {
            let items = [];
            try { items = this.normalizeHistoryPayload(await API.getHistory(200)); } catch (_) {}
            if (!items.length) { try { items = this.normalizeHistoryPayload(await API.getExecutionRuns()); } catch (_) {} }
            if (!items.length) { try { items = this.normalizeHistoryPayload(await API.getQueueHistory(200)); } catch (_) {} }
            if (items.length) {
                this.state.items = items.map((item) => this.normalizeHistoryItem(item));
                this.state.useMockData = false;
            } else {
                console.warn('[History] All APIs returned empty, using mock data.');
                this.state.items = [...this.mockItems];
                this.state.useMockData = true;
            }
        } catch (e) {
            console.warn('[History] Unexpected error, using mock:', e);
            this.state.error = null;
            this.state.items = [...this.mockItems];
            this.state.useMockData = true;
            Toast.error('Error', 'History API unavailable — using mock data for this version');
        } finally {
            this.state.loading = false;
            document.getElementById('history-refresh-btn')?.classList.remove('is-spinning');
            this.renderContent();
        }
    },

    normalizeHistoryPayload(payload) { if (Array.isArray(payload)) return payload; if (payload && Array.isArray(payload.data)) return payload.data; return []; },
    normalizeHistoryItem(item) {
        let parsedData = {};
        const metadataRaw = item?.metadata_json || item?.metadata;
        let metadata = {};
        if (metadataRaw) { try { metadata = typeof metadataRaw === 'string' ? JSON.parse(metadataRaw) : metadataRaw; } catch (_) { metadata = {}; } }
        const rawResult = item?.result_json ?? metadata?.result_json;
        if (rawResult) {
            try {
                parsedData = typeof rawResult === 'string' ? JSON.parse(rawResult) : rawResult;
                if (typeof parsedData === 'string') parsedData = JSON.parse(parsedData);
                if (parsedData && parsedData.data) parsedData = parsedData.data;
            } catch (_) { parsedData = { raw: rawResult }; }
        }
        const hasData = parsedData && Object.keys(parsedData).length > 0;
        const rawId = item?.id || item?.run_id || `${item?.serial || item?.emu_name || 'unknown'}-${item?.started_at || item?.created_at || Date.now()}`;
        return { id: String(rawId), task_id: String(rawId).slice(-8).toUpperCase(), task_type: item?.task_type || metadata?.task_type || item?.source_page || 'unknown', serial: item?.serial || metadata?.serial || '--', status: String(item?.status || metadata?.status || 'UNKNOWN').toUpperCase(), data: hasData ? parsedData : null, error: item?.error || metadata?.error || null, is_reliable: !(item?.error || metadata?.error), reliability: (item?.error || metadata?.error) ? 40 : 95, started_at: item?.started_at || item?.created_at || null, finished_at: item?.finished_at || item?.ended_at || null, duration_ms: Number(item?.duration_ms || 0), source: item?.source || item?.source_page || 'system', logs: Array.isArray(item?.logs) ? item.logs : [], emu_name: item?.emu_name || item?.emulator_name || metadata?.emu_name || '' };
    },
    getFilteredItems() {
        const { search, date, device, status, task, quick } = this.state.filters;
        const normalizedSearch = search.trim().toLowerCase();
        return this.state.items.filter((item) => {
            const dt = item.started_at || item.created_at ? new Date(item.started_at || item.created_at) : null;
            const statusValue = this.normalizeStatus(item.status);
            const taskType = item.task_type || 'unknown';
            const serial = item.serial || 'unknown';
            const durationMs = Number(item.duration_ms || 0);
            const source = `${serial} ${taskType} ${statusValue}`.toLowerCase();
            if (normalizedSearch && !source.includes(normalizedSearch)) return false;
            if (date === 'today' && (!dt || this.getVietnamDateKey(dt) !== this.getVietnamDateKey(new Date()))) return false;
            if (device !== 'all' && serial !== device) return false;
            if (status !== 'all' && statusValue !== status) return false;
            if (task !== 'all' && taskType !== task) return false;
            if (quick === 'failed' && statusValue !== 'FAILED') return false;
            if (quick === 'today' && (!dt || this.getVietnamDateKey(dt) !== this.getVietnamDateKey(new Date()))) return false;
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
        footer.textContent = `Showing ${filtered.length} result${filtered.length === 1 ? '' : 's'}${this.state.useMockData ? ' · mock data' : ''}`;
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
        container.innerHTML = `
            <div class="grid-4" style="margin-bottom: 0;">
                ${this.renderSelect('Date range', 'history-filter-date', this.state.filters.date, [{ value: 'all', label: 'All time' }, { value: 'today', label: 'Today' }])}
                ${this.renderSelect('Device', 'history-filter-device', this.state.filters.device, devices.map((value) => ({ value, label: value === 'all' ? 'All devices' : value })))}
                ${this.renderSelect('Status', 'history-filter-status', this.state.filters.status, [{ value: 'all', label: 'All status' }, { value: 'SUCCESS', label: 'Success' }, { value: 'FAILED', label: 'Failed' }, { value: 'RUNNING', label: 'Running' }])}
                ${this.renderSelect('Task type', 'history-filter-task', this.state.filters.task, tasks.map((value) => ({ value, label: value === 'all' ? 'All tasks' : value })))}
            </div>
        `;
    },

    renderSelect(label, id, selected, options) {
        return `<label class="form-group" style="margin:0;display:flex;flex-direction:column;gap:6px;"><span class="text-sm font-medium text-muted">${label}</span><select id="${id}" class="form-select">${options.map((opt) => `<option value="${opt.value}" ${opt.value === selected ? 'selected' : ''}>${opt.label}</option>`).join('')}</select></label>`;
    },

    renderQuickFilters() {
        const quicks = [{ value: 'today', label: 'Today' }, { value: 'failed', label: 'Failed' }, { value: 'long', label: 'Long runs' }, { value: 'manual', label: 'Manual tasks' }];
        return quicks.map((chip) => `<button class="history-quick-chip ${this.state.filters.quick === chip.value ? 'history-quick-chip--active' : ''}" data-quick="${chip.value}">${chip.label}</button>`).join('') + `<button class="history-quick-chip ${this.state.filters.quick === 'all' ? 'history-quick-chip--active' : ''}" data-quick="all">Reset</button>`;
    },

    renderSkeletonRows() {
        const cols = ['skeleton-cell--medium', 'skeleton-cell--short', 'skeleton-cell--badge', 'skeleton-cell--medium', 'skeleton-cell--short', 'skeleton-cell--short', 'skeleton-cell--short'];
        return `<table class="history-table"><thead><tr><th>Time</th><th>Task</th><th>Status</th><th>Device</th><th>Duration</th><th>Reliable</th><th>Details</th></tr></thead><tbody>${Array.from({ length: 6 }).map(() => `<tr>${cols.map(cls => `<td><div class="skeleton-cell ${cls}"></div></td>`).join('')}</tr>`).join('')}</tbody></table>`;
    },

    renderEmptyState() {
        return `<div class="empty-state card" style="margin:24px 0;"><div class="empty-state-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg></div><h3 style="font-size:16px;font-weight:600;color:var(--foreground);margin-top:8px;">No history yet</h3><p style="font-size:14px;margin-top:4px;max-width:320px;">Run your first scan to see execution logs and details here.</p><div style="display:flex;gap:12px;margin-top:24px;"><button class="btn btn-primary btn-sm" onclick="App.router.navigate('scan-operations')">Run scan</button><button class="btn btn-outline btn-sm" onclick="window.open('https://github.com/mlem16/COD_CHECK', '_blank')">Learn more</button></div></div>`;
    },

    renderErrorState() {
        return `<div class="empty-state card" style="margin:24px 0;border-color:var(--red-200);background:var(--red-50);"><div class="empty-state-icon" style="background:var(--red-100);color:var(--red-500);"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg></div><h3 style="font-size:16px;font-weight:600;color:var(--red-600);margin-top:8px;">Failed to load history</h3><p style="font-size:14px;color:var(--red-500);margin-top:4px;">Something went wrong while fetching logs from the database.</p><div style="margin-top:24px;"><button class="btn btn-primary btn-sm" onclick="HistoryPage.load()" style="background:var(--red-600);border-color:var(--red-600);">Retry loading</button></div></div>`;
    },

    renderDataTable(items) {
        return `<div style="overflow-x:auto"><table class="history-table" id="history-table"><thead><tr><th>Time</th><th>Task</th><th>Status</th><th>Device</th><th>Duration</th><th>Reliable</th><th>Details</th></tr></thead><tbody>${items.map((item, idx) => this.renderDataRow(item, idx)).join('')}</tbody></table></div>`;
    },

    renderDataRow(item, index) {
        const rowId = String(item.id || `${item.serial || 'device'}-${item.started_at || item.created_at || index}`);
        const status = this.normalizeStatus(item.status);
        const statusClass = status === 'SUCCESS' ? 'success' : status === 'FAILED' ? 'failed' : status === 'RUNNING' ? 'running' : 'neutral';
        const time = item.started_at ? this.formatVietnamDateTime(item.started_at) : (item.created_at ? this.formatVietnamDateTime(item.created_at) : '--');
        const duration = item.duration_ms ? `${(item.duration_ms / 1000).toFixed(2)}s` : '--';
        const reliability = this.getReliabilityInfo(item);
        const isExpanded = this.state.expandedRowId === rowId;
        const deviceLabel = item.emu_name ? `${item.emu_name} (${item.serial})` : (item.serial || '--');
        const sourceBadge = item.source === 'full_scan' ? '<span class="badge badge-outline" style="font-size:10px;margin-left:4px;">scan</span>' : '';
        return `<tr class="history-data-row ${isExpanded ? 'expanded' : ''}" data-row-id="${rowId}"><td class="text-sm text-mono">${time}</td><td><span class="badge badge-outline" style="text-transform:capitalize">${item.task_type || 'unknown'}</span>${sourceBadge}</td><td><span class="status-badge ${statusClass}">${status}</span></td><td class="text-mono">${deviceLabel}</td><td class="text-mono">${duration}</td><td><span class="reliability ${reliability.className}">${reliability.icon} ${reliability.value}</span></td><td><button class="btn btn-ghost btn-sm" data-toggle-row="${rowId}">${isExpanded ? 'Hide' : 'View'} details</button></td></tr><tr class="history-expand-row ${isExpanded ? 'open' : ''}"><td colspan="7"><div class="expand-panel"><div class="expand-title">Script output & execution details</div><div class="expand-grid"><div><strong>Output data</strong><pre>${item.data ? this.safeJson(item.data) : 'No data output'}</pre></div><div><strong>Status info</strong><pre>${this.safeJson({ task_type: item.task_type, status, source: item.source || 'system', duration, started: item.started_at, finished: item.finished_at || '--' })}</pre></div><div><strong>Errors</strong><pre>${item.error ? item.error : 'None'}</pre></div><div><strong>Logs</strong><pre>${item.logs && item.logs.length ? item.logs.join('\n') : 'No detailed logs'}</pre></div></div></div></td></tr>`;
    },

    safeJson(value) { try { if (typeof value === 'string') return value; return JSON.stringify(value, null, 2); } catch (e) { return '--'; } },
    toggleRow(rowId) { this.state.expandedRowId = this.state.expandedRowId === rowId ? null : rowId; this.renderContent(); },
    normalizeStatus(status) { const value = String(status || 'UNKNOWN').toUpperCase(); if (value === 'COMPLETED') return 'SUCCESS'; if (value === 'ERROR') return 'FAILED'; return value; },
    formatVietnamDateTime(value) {
        if (!value) return '--';
        const dt = value instanceof Date ? value : new Date(value);
        if (Number.isNaN(dt.getTime())) return String(value);
        return new Intl.DateTimeFormat('vi-VN', {
            timeZone: 'Asia/Ho_Chi_Minh',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
        }).format(dt);
    },
    getVietnamDateKey(value = new Date()) {
        const dt = value instanceof Date ? value : new Date(value);
        if (Number.isNaN(dt.getTime())) return '';
        return new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Asia/Ho_Chi_Minh',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        }).format(dt);
    },
    getReliabilityInfo(item) {
        if (typeof item.reliability === 'number') {
            if (item.reliability >= 80) return { value: `${item.reliability}%`, className: 'high', icon: '🟢' };
            if (item.reliability >= 50) return { value: `${item.reliability}%`, className: 'medium', icon: '🟡' };
            return { value: `${item.reliability}%`, className: 'low', icon: '🔴' };
        }
        return item.is_reliable ? { value: '100%', className: 'high', icon: '🟢' } : { value: '40%', className: 'low', icon: '🔴' };
    },

    async refreshWorkflowLogs() { await this.loadWorkflowLogSummary(true, false, 'preserve'); },
    startLogsPolling() {
        this.stopLogsPolling();
        if (!this.state.logsAutoRefresh || this.state.activeTab !== 'logs') return;
        this.state.logsPollTimer = setInterval(() => {
            if (this.state.activeTab === 'logs' && this.state.logsAutoRefresh) this.loadWorkflowLogSummary(true, true, 'preserve');
        }, 5000);
    },
    stopLogsPolling() { if (this.state.logsPollTimer) { clearInterval(this.state.logsPollTimer); this.state.logsPollTimer = null; } },
    _captureLogsScrollState(mode = 'preserve') {
        const consoleEl = document.querySelector('#logs-panel .logs-console');
        if (!consoleEl) { this.state.logsScrollState = { mode }; return; }
        const maxScrollTop = Math.max(0, consoleEl.scrollHeight - consoleEl.clientHeight);
        const distanceFromBottom = maxScrollTop - consoleEl.scrollTop;
        this.state.logsScrollState = { mode, scrollTop: consoleEl.scrollTop, scrollHeight: consoleEl.scrollHeight, clientHeight: consoleEl.clientHeight, wasNearBottom: distanceFromBottom <= 28 };
    },
    _restoreLogsScrollState() {
        const state = this.state.logsScrollState;
        const consoleEl = document.querySelector('#logs-panel .logs-console');
        this.state.logsScrollState = null;
        if (!state || !consoleEl) return;
        if (state.mode === 'bottom') { consoleEl.scrollTop = consoleEl.scrollHeight; return; }
        if (state.mode === 'prepend') {
            const delta = consoleEl.scrollHeight - (state.scrollHeight || 0);
            consoleEl.scrollTop = Math.max(0, (state.scrollTop || 0) + delta);
            return;
        }
        consoleEl.scrollTop = state.scrollTop || 0;
    },

    async loadWorkflowLogSummary(preserveSelection = true, silent = false, scrollMode = 'preserve') {
        const panel = document.getElementById('logs-panel');
        if (!panel) return;
        let contentRendered = false;
        if (!silent) {
            this.state.logsLoading = true;
            this.state.logsError = null;
            this.renderLogsPanel();
        }
        try {
            this.state.logsSummary = await API.getWorkflowLogSummary() || { serials: [], dates: [], files: [], grouped_files: {} };
            this._applyLogsSelection(preserveSelection);
            if (this.state.logsSelectedSerial && this.state.logsSelectedDate) {
                await this.loadWorkflowLogContent({ silent, scrollMode });
                contentRendered = true;
            }
            else {
                this.state.logsContentRaw = '';
                this.state.logsLineNumbers = [];
                this.state.logsMeta = null;
                this.state.logsHasMoreBefore = false;
            }
        } catch (e) {
            console.warn('[Logs] Failed to load summary:', e);
            this.state.logsError = e.message || 'Failed to load workflow logs';
        } finally {
            this.state.logsLoading = false;
            if (!contentRendered) this.renderLogsPanel();
        }
    },

    _applyLogsSelection(preserveSelection) {
        const files = this.state.logsSummary.files || [];
        let selectedFile = preserveSelection && this.state.logsSelectedPathToken ? files.find((file) => file.path_token === this.state.logsSelectedPathToken) : null;
        if (!selectedFile) {
            selectedFile = files[0] || null;
            this.state.logsOffset = 0;
        }
        if (!selectedFile) {
            this.state.logsSelectedSerial = '';
            this.state.logsSelectedDate = '';
            this.state.logsSelectedPathToken = '';
            return;
        }
        this.state.logsSelectedSerial = selectedFile.serial;
        this.state.logsSelectedDate = selectedFile.date;
        this.state.logsSelectedPathToken = selectedFile.path_token;
    },

    _getLogsFilesForSelection() {
        const files = this.state.logsSummary.files || [];
        if (!this.state.logsSelectedSerial) return files;
        return files.filter((file) => file.serial === this.state.logsSelectedSerial);
    },
    _getLogsDatesForSelection() { return [...new Set(this._getLogsFilesForSelection().map((file) => file.date))]; },
    _getSelectedLogFile() { return (this.state.logsSummary.files || []).find((file) => file.path_token === this.state.logsSelectedPathToken) || null; },

    async loadWorkflowLogContent({ silent = false, scrollMode = 'bottom' } = {}) {
        if (!this.state.logsSelectedSerial || !this.state.logsSelectedDate) return;
        this._captureLogsScrollState(scrollMode);
        if (!silent) {
            this.state.logsLoading = true;
            this.renderLogsPanel();
        }
        try {
            const payload = await API.getWorkflowLogContent({
                serial: this.state.logsSelectedSerial,
                date: this.state.logsSelectedDate,
                tail: this.state.logsTail,
                offset: this.state.logsOffset,
                search: this.state.logsContextAnchorLine ? undefined : (this.state.logsSearch.trim() || undefined),
                anchorLine: this.state.logsContextAnchorLine || undefined,
                context: this.state.logsContextAnchorLine ? this.state.logsContextRadius : undefined,
            });
            this.state.logsContentRaw = payload.content || '';
            this.state.logsLineNumbers = Array.isArray(payload.line_numbers) ? payload.line_numbers : [];
            this.state.logsHasMoreBefore = !!payload.has_more_before;
            this.state.logsMeta = payload;
            this.state.logsSelectedPathToken = `${payload.serial}:${payload.date}`;
            this.state.logsError = null;
        } catch (e) {
            console.warn('[Logs] Failed to load content:', e);
            this.state.logsError = e.message || 'Failed to load log file';
            this.state.logsContentRaw = '';
            this.state.logsLineNumbers = [];
            this.state.logsMeta = null;
            this.state.logsHasMoreBefore = false;
        } finally {
            this.state.logsLoading = false;
            this.renderLogsPanel();
        }
    },

    renderLogsPanel() {
        const panel = document.getElementById('logs-panel');
        const footer = document.getElementById('history-footer');
        if (!panel) return;
        const files = this._getLogsFilesForSelection();
        const dates = this._getLogsDatesForSelection();
        const selectedFile = this._getSelectedLogFile();
        const lines = this._getVisibleLogLines();
        const matchedLineCount = Number(this.state.logsMeta?.matched_lines || lines.length);
        const isContextMode = !!this.state.logsContextAnchorLine;
        const lineCountLabel = this.state.logsSearch.trim()
            ? `${lines.length}/${matchedLineCount} matched line${matchedLineCount === 1 ? '' : 's'}`
            : `${lines.length} visible line${lines.length === 1 ? '' : 's'}`;
        if (!this.state.logsSummary.files?.length && !this.state.logsLoading) {
            panel.innerHTML = `<div class="logs-empty card"><div class="logs-empty__title">No workflow logs yet</div><p class="logs-empty__desc">Workflow text logs will appear here after bot runs start writing to disk.</p></div>`;
            if (footer) footer.textContent = '0 workflow log files';
            return;
        }
        panel.innerHTML = `
            <div class="logs-shell">
                <div class="logs-hero">
                    <div>
                        <div class="logs-kicker">Workflow Log Console</div>
                        <div class="logs-title-row">
                            <h3 class="logs-title">Logs</h3>
                            <span class="logs-context-pill">${selectedFile ? this.escapeHtml(selectedFile.serial) : 'No file selected'}</span>
                            <span class="logs-context-pill">${selectedFile ? this.escapeHtml(selectedFile.date) : '--'}</span>
                        </div>
                        <p class="logs-subtitle">${isContextMode ? `Reviewing context around line ${this.state.logsContextAnchorLine}.` : 'Review workflow output by emulator and date without leaving History.'}</p>
                    </div>
                    <div class="logs-hero-actions">
                        <span class="logs-status ${this.state.logsAutoRefresh ? 'is-live' : ''}">${this.state.logsAutoRefresh ? 'Auto refresh on' : 'Auto refresh off'}</span>
                        ${isContextMode ? '<button class="btn btn-outline btn-sm" id="logs-exit-context-btn">Back to results</button>' : ''}
                        <button class="btn btn-outline btn-sm" id="logs-sidebar-toggle">${this.state.logsSidebarCollapsed ? 'Show list' : 'Hide list'}</button>
                        <button class="btn btn-outline btn-sm" id="logs-btn-refresh">Refresh</button>
                    </div>
                </div>
                <div class="logs-layout ${this.state.logsSidebarCollapsed ? 'is-collapsed' : ''}">
                    <aside class="logs-sidebar">
                        <div class="logs-filter-card">
                            <label class="logs-filter-field"><span>Emulator</span><select id="logs-serial-select" class="form-select">${(this.state.logsSummary.serials || []).map((serial) => `<option value="${this.escapeHtml(serial)}" ${serial === this.state.logsSelectedSerial ? 'selected' : ''}>${this.escapeHtml(serial)}</option>`).join('')}</select></label>
                            <label class="logs-filter-field"><span>Date</span><select id="logs-date-select" class="form-select">${dates.map((date) => `<option value="${this.escapeHtml(date)}" ${date === this.state.logsSelectedDate ? 'selected' : ''}>${this.escapeHtml(date)}</option>`).join('')}</select></label>
                        </div>
                        <div class="logs-file-list">${files.map((file) => `<button class="logs-file-item ${file.path_token === this.state.logsSelectedPathToken ? 'active' : ''}" data-log-token="${this.escapeHtml(file.path_token)}" data-log-serial="${this.escapeHtml(file.serial)}" data-log-date="${this.escapeHtml(file.date)}"><div class="logs-file-item__date">${this.escapeHtml(file.date)}</div><div class="logs-file-item__meta">${this.formatBytes(file.size_bytes)} · ${file.line_count_estimate} lines</div></button>`).join('')}</div>
                    </aside>
                    <section class="logs-viewer">
                        <div class="logs-toolbar">
                            <div class="logs-toolbar__search"><input id="logs-search-input" class="search-input logs-search-input" type="text" placeholder="Search entire selected log file..." value="${this.escapeHtml(this.state.logsSearch)}"></div>
                            <select id="logs-level-select" class="form-select logs-level-select">${this._getLogLevelOptions().map((opt) => `<option value="${opt.value}" ${opt.value === this.state.logsLevel ? 'selected' : ''}>${opt.label}</option>`).join('')}</select>
                            <label class="logs-toggle"><input type="checkbox" id="logs-wrap-toggle" ${this.state.logsWrap ? 'checked' : ''}><span>Wrap</span></label>
                            <label class="logs-toggle"><input type="checkbox" id="logs-autorefresh-toggle" ${this.state.logsAutoRefresh ? 'checked' : ''}><span>Auto</span></label>
                            <button class="btn btn-outline btn-sm" id="logs-copy-btn">Copy visible</button>
                            <button class="btn btn-outline btn-sm" id="logs-download-btn" ${selectedFile ? '' : 'disabled'}>Download</button>
                            <button class="btn btn-outline btn-sm logs-btn-danger" id="logs-delete-btn" ${selectedFile ? '' : 'disabled'}>Delete</button>
                        </div>
                        <div class="logs-meta-row"><span>${selectedFile ? this.escapeHtml(selectedFile.filename) : '--'}</span><span>${this.state.logsMeta?.last_modified ? this.formatVietnamDateTime(this.state.logsMeta.last_modified) : '--'}</span><span>${this.state.logsMeta?.size_bytes ? this.formatBytes(this.state.logsMeta.size_bytes) : '--'}</span><span>${isContextMode ? `Context line ${this.state.logsContextAnchorLine} (${this.state.logsMeta?.returned_lines || 0} lines shown)` : (this.state.logsSearch.trim() ? `${this.state.logsMeta?.returned_lines || 0}/${this.state.logsMeta?.matched_lines || 0} matches shown` : `${this.state.logsMeta?.returned_lines || 0}/${this.state.logsMeta?.total_lines || 0} lines loaded`)}</span></div>
                        <div class="logs-console ${this.state.logsWrap ? 'is-wrapped' : ''}">
                            ${this.state.logsLoading && !this.state.logsContentRaw ? `<div class="logs-console__empty">Loading workflow log...</div>` : ''}
                            ${this.state.logsError ? `<div class="logs-console__empty logs-console__empty--error">${this.escapeHtml(this.state.logsError)}</div>` : ''}
                            ${!this.state.logsLoading && !this.state.logsError && !lines.length ? `<div class="logs-console__empty">${this.state.logsSearch.trim() ? 'No matches found in the selected log file.' : 'No lines match the current filters.'}</div>` : ''}
                            ${!this.state.logsError ? lines.map((line) => this._renderLogLine(line)).join('') : ''}
                        </div>
                        <div class="logs-footer-row"><button class="btn btn-outline btn-sm" id="logs-load-older-btn" ${(this.state.logsHasMoreBefore && !isContextMode) ? '' : 'disabled'}>Load older lines</button><div class="logs-footer-meta">${isContextMode ? 'Click a line number any time to reopen context there.' : lineCountLabel}</div></div>
                    </section>
                </div>
            </div>
        `;
        if (footer) footer.textContent = `${this.state.logsSummary.files?.length || 0} workflow log file(s) · ${lineCountLabel}`;
        this.bindLogsEvents();
        this._restoreLogsScrollState();
    },

    _getLogLevelOptions() { return [{ value: 'all', label: 'All levels' }, { value: 'INFO', label: 'INFO' }, { value: 'WARNING', label: 'WARNING' }, { value: 'FAILED', label: 'FAILED' }, { value: 'TIMEOUT', label: 'TIMEOUT' }, { value: 'ERROR', label: 'ERROR' }, { value: 'FATAL', label: 'FATAL' }, { value: 'CRASH DETECTED', label: 'CRASH DETECTED' }]; },
    _parseLogLine(raw) {
        const match = /^\[([^\]]+)\]\s+\[([^\]]+)\]\s+\[([^\]]+)\]\s*(.*)$/.exec(raw || '');
        return match ? { raw, timestamp: match[1], serial: match[2], level: match[3], message: match[4] } : { raw, timestamp: '', serial: '', level: 'INFO', message: raw || '' };
    },
    _getVisibleLogLines() {
        const rawLines = (this.state.logsContentRaw || '').split('\n').filter((line) => line !== '');
        const levelNeedle = this.state.logsLevel;
        const fallbackTotal = Number(this.state.logsMeta?.total_lines || rawLines.length);
        const fallbackStartLine = Math.max(1, fallbackTotal - rawLines.length + 1);
        return rawLines.map((line, idx) => ({
            ...this._parseLogLine(line),
            lineNumber: this.state.logsLineNumbers[idx] || (fallbackStartLine + idx),
            isAnchor: this.state.logsContextAnchorLine === (this.state.logsLineNumbers[idx] || (fallbackStartLine + idx)),
        })).filter((entry) => {
            if (this.state.logsContextAnchorLine) return true;
            if (levelNeedle !== 'all' && entry.level !== levelNeedle) return false;
            return true;
        });
    },
    queueLogsSearch(nextValue) {
        this._captureLogsScrollState('preserve');
        this.state.logsSearch = nextValue || '';
        this.state.logsOffset = 0;
        this.state.logsContextAnchorLine = null;
        if (this.state.logsSearchTimer) clearTimeout(this.state.logsSearchTimer);
        this.state.logsSearchTimer = setTimeout(() => {
            this.state.logsSearchTimer = null;
            this.loadWorkflowLogContent({ silent: false, scrollMode: 'preserve' });
        }, 250);
        this.renderLogsPanel();
    },
    async openLogContext(lineNumber) {
        if (!lineNumber) return;
        this.state.logsOffset = 0;
        this.state.logsContextAnchorLine = Number(lineNumber);
        await this.loadWorkflowLogContent({ scrollMode: 'preserve' });
    },
    async exitLogContext() {
        this.state.logsContextAnchorLine = null;
        this.state.logsOffset = 0;
        await this.loadWorkflowLogContent({ scrollMode: 'preserve' });
    },
    _getLogLevelClass(level) { return `logs-level--${String(level || 'INFO').toLowerCase().replace(/\s+/g, '-')}`; },
    _renderLogLine(line) {
        return `<div class="logs-line ${this._getLogLevelClass(line.level)} ${line.isAnchor ? 'is-anchor' : ''}"><button class="logs-line__num logs-line__num-btn" data-log-line="${line.lineNumber}" title="View context around line ${line.lineNumber}">${line.lineNumber}</button><div class="logs-line__time">${this.escapeHtml(line.timestamp || '--')}</div><div class="logs-line__serial">${this.escapeHtml(line.serial || '--')}</div><div class="logs-line__level"><span class="logs-level-pill ${this._getLogLevelClass(line.level)}">${this.escapeHtml(line.level || 'INFO')}</span></div><div class="logs-line__msg">${this.escapeHtml(line.message || line.raw || '')}</div></div>`;
    },

    bindLogsEvents() {
        const serialSelect = document.getElementById('logs-serial-select');
        const dateSelect = document.getElementById('logs-date-select');
        const searchInput = document.getElementById('logs-search-input');
        const levelSelect = document.getElementById('logs-level-select');
        const wrapToggle = document.getElementById('logs-wrap-toggle');
        const autoToggle = document.getElementById('logs-autorefresh-toggle');
        const sidebarToggle = document.getElementById('logs-sidebar-toggle');
        const exitContextBtn = document.getElementById('logs-exit-context-btn');
        const refreshBtn = document.getElementById('logs-btn-refresh');
        const loadOlderBtn = document.getElementById('logs-load-older-btn');
        const copyBtn = document.getElementById('logs-copy-btn');
        const downloadBtn = document.getElementById('logs-download-btn');
        const deleteBtn = document.getElementById('logs-delete-btn');

        if (serialSelect) serialSelect.onchange = async (event) => {
            this.state.logsSelectedSerial = event.target.value;
            const nextFile = (this.state.logsSummary.files || []).filter((file) => file.serial === this.state.logsSelectedSerial)[0] || null;
            this.state.logsSelectedDate = nextFile ? nextFile.date : '';
            this.state.logsSelectedPathToken = nextFile ? nextFile.path_token : '';
            this.state.logsOffset = 0;
            this.state.logsContextAnchorLine = null;
            await this.loadWorkflowLogContent({ scrollMode: 'bottom' });
        };
        if (dateSelect) dateSelect.onchange = async (event) => {
            this.state.logsSelectedDate = event.target.value;
            const nextFile = (this._getLogsFilesForSelection() || []).find((file) => file.date === this.state.logsSelectedDate) || null;
            this.state.logsSelectedPathToken = nextFile ? nextFile.path_token : '';
            this.state.logsOffset = 0;
            this.state.logsContextAnchorLine = null;
            await this.loadWorkflowLogContent({ scrollMode: 'bottom' });
        };
        document.querySelectorAll('[data-log-token]').forEach((btn) => btn.onclick = async () => {
            this.state.logsSelectedPathToken = btn.dataset.logToken;
            this.state.logsSelectedSerial = btn.dataset.logSerial;
            this.state.logsSelectedDate = btn.dataset.logDate;
            this.state.logsOffset = 0;
            this.state.logsContextAnchorLine = null;
            await this.loadWorkflowLogContent({ scrollMode: 'bottom' });
        });
        if (searchInput) searchInput.oninput = (event) => { this.queueLogsSearch(event.target.value || ''); };
        if (levelSelect) levelSelect.onchange = (event) => { this._captureLogsScrollState('preserve'); this.state.logsLevel = event.target.value; this.state.logsContextAnchorLine = null; this.renderLogsPanel(); };
        if (wrapToggle) wrapToggle.onchange = (event) => { this._captureLogsScrollState('preserve'); this.state.logsWrap = !!event.target.checked; this.renderLogsPanel(); };
        if (autoToggle) autoToggle.onchange = (event) => {
            this._captureLogsScrollState('preserve');
            this.state.logsAutoRefresh = !!event.target.checked;
            if (this.state.logsAutoRefresh) this.startLogsPolling(); else this.stopLogsPolling();
            this.renderLogsPanel();
        };
        if (sidebarToggle) sidebarToggle.onclick = () => { this._captureLogsScrollState('preserve'); this.state.logsSidebarCollapsed = !this.state.logsSidebarCollapsed; this.renderLogsPanel(); };
        if (exitContextBtn) exitContextBtn.onclick = () => this.exitLogContext();
        if (refreshBtn) refreshBtn.onclick = () => this.refreshWorkflowLogs();
        if (loadOlderBtn) loadOlderBtn.onclick = async () => { this.state.logsOffset += this.state.logsTail; await this.loadWorkflowLogContent({ scrollMode: 'prepend' }); };
        document.querySelectorAll('[data-log-line]').forEach((btn) => btn.onclick = () => this.openLogContext(btn.dataset.logLine));
        if (copyBtn) copyBtn.onclick = async () => {
            const visible = this._getVisibleLogLines().map((line) => line.raw).join('\n');
            if (!visible) return;
            try {
                await navigator.clipboard.writeText(visible);
                Toast.success('Copied', 'Visible log lines copied');
            } catch (e) {
                console.warn('[Logs] Copy failed:', e);
                Toast.error('Copy failed', 'Could not copy visible log lines');
            }
        };
        if (downloadBtn) downloadBtn.onclick = async () => {
            if (!this.state.logsSelectedSerial || !this.state.logsSelectedDate) return;
            try {
                const totalLines = Number(this.state.logsMeta?.total_lines || this.state.logsTail);
                const payload = await API.getWorkflowLogContent({ serial: this.state.logsSelectedSerial, date: this.state.logsSelectedDate, tail: Math.max(totalLines, this.state.logsTail), offset: 0 });
                const blob = new Blob([payload.content || ''], { type: 'text/plain;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = payload.filename || `${this.state.logsSelectedDate}.log`;
                a.click();
                URL.revokeObjectURL(url);
            } catch (e) {
                console.warn('[Logs] Download failed:', e);
                Toast.error('Download failed', 'Could not download log file');
            }
        };
        if (deleteBtn) deleteBtn.onclick = async () => {
            if (!this.state.logsSelectedSerial || !this.state.logsSelectedDate) return;
            if (!confirm(`Delete workflow log ${this.state.logsSelectedDate} for ${this.state.logsSelectedSerial}?`)) return;
            try {
                await API.deleteWorkflowLogFile(this.state.logsSelectedSerial, this.state.logsSelectedDate);
                this.state.logsOffset = 0;
                Toast.success('Deleted', 'Workflow log file removed');
                await this.loadWorkflowLogSummary(false);
            } catch (e) {
                console.warn('[Logs] Delete failed:', e);
                Toast.error('Delete failed', e.message || 'Could not delete log file');
            }
        };
    },

    formatBytes(bytes) {
        const value = Number(bytes || 0);
        if (value < 1024) return `${value} B`;
        if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
        return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    },
    escapeHtml(value) { return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); },

    bindInlineEvents() {
        const filterDate = document.getElementById('history-filter-date');
        const filterDevice = document.getElementById('history-filter-device');
        const filterStatus = document.getElementById('history-filter-status');
        const filterTask = document.getElementById('history-filter-task');
        [[filterDate, 'date'], [filterDevice, 'device'], [filterStatus, 'status'], [filterTask, 'task']].forEach(([el, key]) => {
            if (!el) return;
            el.onchange = (event) => { this.state.filters[key] = event.target.value; this.renderContent(); };
        });
        document.querySelectorAll('[data-quick]').forEach((chip) => chip.onclick = () => { this.state.filters.quick = chip.dataset.quick; this.renderContent(); });
        const stateArea = document.getElementById('history-state-area');
        if (stateArea) stateArea.onclick = (e) => {
            const actionBtn = e.target.closest('[data-action]');
            if (actionBtn) {
                const action = actionBtn.dataset.action;
                if (action === 'retry-load') return this.load();
                if (action === 'run-scan') return App.router.navigate('scan-operations');
                if (action === 'learn-more') return window.open('https://github.com/mlem16/COD_CHECK', '_blank');
                return;
            }
            const toggleBtn = e.target.closest('[data-toggle-row]');
            if (toggleBtn) this.toggleRow(toggleBtn.dataset.toggleRow);
        };
    }
};
