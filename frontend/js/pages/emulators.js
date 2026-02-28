/**
 * Emulators Page — Infrastructure Control Panel
 * Full LDPlayer instance management via ldconsole list2.
 *
 * Fixes:
 *  - getElementById space bug in btn IDs (`emu-btn-s-${index}` not `emu - btn - s - ${index}`)
 *  - Mock RAM/CPU regenerated randomly on every render (removed — only set once per instance lifecycle)
 *
 * New Features:
 *  - ADB serial display + one-click copy per card
 *  - "Start All" / "Stop All" convenience buttons
 *  - Manual Refresh button with last-updated timestamp
 *  - Auto-refresh countdown ring
 *  - Right-click context menu (Copy Name / Copy ADB Serial / Copy Index)
 *  - Staggered card entrance animation
 *  - Inline rename via double-click
 *  - Confirm dialog before Stop All / Stop Selected bulk actions
 */
// ── TAB COLORS ─────────────────────────────────────
const TAB_COLORS = ['#4f9eff', '#22c55e', '#f59e0b', '#a78bfa', '#f472b6', '#34d399'];

const EmulatorsPage = {
    _pollInterval: null,
    _countdownInterval: null,
    _instances: [],
    _selectedInstances: new Set(),
    _filter: 'all',        // 'all' | 'running' | 'stopped'
    _searchQuery: '',
    _autoRefresh: true,
    _lastRefresh: null,
    _refreshSeconds: 5,    // polling interval in seconds
    _contextMenu: null,    // active context menu element
    _renamingIndex: null,  // index currently being renamed

    // Tab State
    _tabs: [
        { id: 'all', label: 'All Instances', color: '#4f9eff', indices: null }
    ],
    _activeTabId: 'all',
    _tabCounter: 0,
    _renamingTabId: null,

    // ─────────────────────────────────────────────
    //  RENDER
    // ─────────────────────────────────────────────
    render() {
        return `
        <div class="page-enter">

            <!-- Page Header -->
            <div class="page-header emu-dashboard-header">
                <div class="page-header-info">
                    <h2>Emulator Instances</h2>
                    <p>Infrastructure control panel — start, stop, restart and inspect all LDPlayer instances.</p>
                </div>
            </div>

            <!-- Stats + Primary Actions -->
            <div class="emu-header-summary" id="emu-stats">
                <div class="emu-stats-inline" role="status" aria-label="Emulator instance summary">
                    <span class="emu-stat-inline emu-stat-total">Total <strong id="emu-stat-total">0</strong></span>
                    <span class="emu-stat-separator" aria-hidden="true">|</span>
                    <span class="emu-stat-inline emu-stat-running">Running <strong id="emu-stat-running">0</strong></span>
                    <span class="emu-stat-separator" aria-hidden="true">|</span>
                    <span class="emu-stat-inline emu-stat-stopped">Stopped <strong id="emu-stat-stopped">0</strong></span>
                </div>

                <div class="emu-primary-actions">
                    <button class="btn btn-default btn-sm emu-btn-priority" onclick="EmulatorsPage.startAll()" id="btn-start-all">
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                        Start All
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="EmulatorsPage.stopAll()" id="btn-stop-all">
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
                        Stop All
                    </button>
                </div>
            </div>

            <!-- Control Toolbar -->
            <div class="toolbar emu-toolbar">
                <div class="emu-toolbar-search">

                    <!-- Search -->
                    <div class="search-wrapper" style="max-width:280px; width:100%;">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="11" cy="11" r="8"/>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                        <input type="text" class="form-input search-input emu-search-input" placeholder="Search by name or index…"
                               oninput="EmulatorsPage.setSearch(this.value)"
                               style="height:36px;" id="emu-search-input" />
                    </div>

                    <!-- Filter tabs -->
                    <div class="tabs emu-filter-group" style="display:flex; background:var(--card); border:1px solid var(--border); border-radius:var(--radius-md); padding:2px; gap:1px;">
                        <button class="tab-btn active" id="filter-btn-all"
                                onclick="EmulatorsPage.setFilter('all')"
                                style="padding:6px 12px; font-size:13px; font-weight:500; border-radius:var(--radius-sm); border:none; background:transparent; cursor:pointer;">
                            All
                        </button>
                        <button class="tab-btn" id="filter-btn-running"
                                onclick="EmulatorsPage.setFilter('running')"
                                style="padding:6px 12px; font-size:13px; font-weight:500; border-radius:var(--radius-sm); border:none; background:transparent; cursor:pointer;">
                            Running
                        </button>
                        <button class="tab-btn" id="filter-btn-stopped"
                                onclick="EmulatorsPage.setFilter('stopped')"
                                style="padding:6px 12px; font-size:13px; font-weight:500; border-radius:var(--radius-sm); border:none; background:transparent; cursor:pointer;">
                            Stopped
                        </button>
                    </div>
                </div>

                <div class="emu-system-controls">
                    <!-- Manual refresh + last-refresh time -->
                    <div style="display:flex; align-items:center; gap:8px;">
                        <button class="btn btn-secondary btn-sm" onclick="EmulatorsPage.manualRefresh()" title="Refresh now" id="btn-manual-refresh">
                            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                            Refresh
                        </button>
                        <span id="emu-last-refresh" style="font-size:11px; color:var(--muted-foreground); white-space:nowrap; display:none;">—</span>
                    </div>

                    <div class="emu-system-divider"></div>

                    <!-- Auto Refresh toggle + countdown -->
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:13px; font-weight:500; color:var(--muted-foreground); white-space:nowrap;">Auto</span>
                        <!-- Countdown ring wrapping the switch -->
                        <div style="position:relative; display:flex; align-items:center; justify-content:center;">
                            <svg id="emu-countdown-ring" width="32" height="32" viewBox="0 0 32 32"
                                 style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); pointer-events:none; opacity:0.55;">
                                <circle cx="16" cy="16" r="13" fill="none" stroke="var(--border)" stroke-width="2"/>
                                <circle id="emu-countdown-arc" cx="16" cy="16" r="13" fill="none"
                                        stroke="var(--emerald-600)" stroke-width="2"
                                        stroke-dasharray="81.68" stroke-dashoffset="0"
                                        stroke-linecap="round"
                                        style="transform:rotate(-90deg); transform-origin:center; transition:stroke-dashoffset 1s linear;"/>
                            </svg>
                            <button class="switch" id="auto-refresh-switch" role="switch" aria-checked="true"
                                    onclick="EmulatorsPage.toggleAutoRefresh()" style="position:relative; z-index:1;">
                                <span class="switch-thumb"></span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ══════════════════════════════════════════
                 CHROME TABS
            ══════════════════════════════════════════ -->
            <div class="chrome-tabbar-wrap">
                <div class="chrome-tabbar" id="chrome-tabbar">
                    <!-- tabs rendered by JS -->
                </div>
            </div>

            <!-- Content Area -->
            <div class="tab-content-area">
                <!-- Select-all row -->
                <div style="display:flex; align-items:center; justify-content:space-between; padding:10px 16px 8px 16px; gap:12px; flex-wrap:wrap;">
                    <div style="display:flex; align-items:center; gap:12px;">
                    <input type="checkbox" id="select-all-cb" onchange="EmulatorsPage.toggleSelectAll(this.checked)"
                           style="margin-right:4px; cursor:pointer;" />
                    <label for="select-all-cb" style="font-size:13px; font-weight:500; color:var(--muted-foreground); cursor:pointer;">
                        Select All
                    </label>
                    <span id="emu-selection-hint" style="font-size:12px; color:var(--muted-foreground); display:none;">
                        — <strong id="emu-selected-label">0</strong> selected
                    </span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <button class="btn btn-default btn-sm" id="btn-start-selected" onclick="EmulatorsPage.startSelected()" disabled>
                            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                            Start (<span id="selected-count-start">0</span>)
                        </button>
                        <button class="btn btn-outline btn-sm" style="color:var(--destructive);" id="btn-stop-selected" onclick="EmulatorsPage.stopSelected()" disabled>
                            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
                            Stop (<span id="selected-count-stop">0</span>)
                        </button>
                    </div>
                </div>

                <!-- Instance list -->
                <div class="grid-1" id="emu-list" style="gap:8px; padding: 0 12px 4px;">
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="2" y="3" width="20" height="14" rx="2"/>
                                <line x1="8" y1="21" x2="16" y2="21"/>
                                <line x1="12" y1="17" x2="12" y2="21"/>
                            </svg>
                        </div>
                        <span class="font-medium">No emulator data yet</span>
                        <span style="font-size:13px; color:var(--muted-foreground);">Fetch the latest status to start managing instances.</span>
                        <div style="display:flex; gap:8px; margin-top:4px;">
                            <button class="btn btn-default btn-sm" onclick="EmulatorsPage.manualRefresh()">Refresh now</button>
                        </div>
                    </div>
                </div>
            </div>

        </div>

        <!-- Context Menu (hidden, appended to body in JS) -->
        `;
    },

    // ─────────────────────────────────────────────
    //  LIFECYCLE
    // ─────────────────────────────────────────────
    async init() {
        this._selectedInstances.clear();
        this._filter = 'all';
        this._searchQuery = '';
        this._autoRefresh = true;
        this._lastRefresh = null;

        // Global click → dismiss context menu
        document.addEventListener('click', this._dismissContextMenu.bind(this), true);

        this.renderTabs();
        await this.refresh();
        this._setupPolling();
        this._startCountdown();
    },

    destroy() {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
            this._pollInterval = null;
        }
        if (this._countdownInterval) {
            clearInterval(this._countdownInterval);
            this._countdownInterval = null;
        }
        this._dismissContextMenu();
        document.removeEventListener('click', this._dismissContextMenu.bind(this), true);
    },

    // ─────────────────────────────────────────────
    //  POLLING & COUNTDOWN
    // ─────────────────────────────────────────────
    _setupPolling() {
        if (this._pollInterval) clearInterval(this._pollInterval);
        if (this._autoRefresh) {
            this._pollInterval = setInterval(() => this.refresh(true), this._refreshSeconds * 1000);
        }
    },

    _startCountdown() {
        if (this._countdownInterval) clearInterval(this._countdownInterval);
        const circumference = 2 * Math.PI * 13; // r=13 → ≈81.68
        let elapsed = 0;

        this._countdownInterval = setInterval(() => {
            if (!this._autoRefresh) return;
            elapsed = (elapsed + 1) % this._refreshSeconds;
            const arc = document.getElementById('emu-countdown-arc');
            if (!arc) return;
            const progress = elapsed / this._refreshSeconds;
            arc.style.strokeDashoffset = circumference * progress;
        }, 1000);
    },

    toggleAutoRefresh() {
        this._autoRefresh = !this._autoRefresh;
        const sw = document.getElementById('auto-refresh-switch');
        const ring = document.getElementById('emu-countdown-ring');
        if (sw) sw.setAttribute('aria-checked', this._autoRefresh ? 'true' : 'false');
        if (ring) ring.style.opacity = this._autoRefresh ? '0.55' : '0.15';
        this._setupPolling();
    },

    async manualRefresh() {
        const btn = document.getElementById('btn-manual-refresh');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner" style="width:12px;height:12px;border-width:2px;border-top-color:currentColor;"></span> Refreshing…';
        }
        await this.refresh();
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Refresh';
        }
    },

    // ─────────────────────────────────────────────
    //  DATA
    // ─────────────────────────────────────────────
    async refresh(isSilent = false) {
        try {
            this._instances = await API.getAllEmulators();
            this._lastRefresh = new Date();
            this._updateLastRefreshLabel();
            this.updateStats();
            this.renderList();
        } catch (e) {
            if (!isSilent) Toast.error('Error', 'Failed to fetch LDPlayer instances');
        }
    },

    _updateLastRefreshLabel() {
        const el = document.getElementById('emu-last-refresh');
        if (!el || !this._lastRefresh) return;
        el.style.display = 'inline';
        const h = String(this._lastRefresh.getHours()).padStart(2, '0');
        const m = String(this._lastRefresh.getMinutes()).padStart(2, '0');
        const s = String(this._lastRefresh.getSeconds()).padStart(2, '0');
        el.textContent = `Updated ${h}:${m}:${s}`;
    },

    updateStats() {
        if (!this._instances) return;
        const total = this._instances.length;
        const running = this._instances.filter(i => i.running).length;
        const stopped = total - running;
        const u = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        u('emu-stat-total', total);
        u('emu-stat-running', running);
        u('emu-stat-stopped', stopped);
    },

    /** Derive ADB serial from LDPlayer index */
    _adbSerial(index) {
        return `emulator-${5554 + index * 2}`;
    },

    // ─────────────────────────────────────────────
    //  TABS
    // ─────────────────────────────────────────────
    renderTabs() {
        const bar = document.getElementById('chrome-tabbar');
        if (!bar) return;
        bar.innerHTML = '';

        this._tabs.forEach((tab, i) => {
            const isActive = tab.id === this._activeTabId;
            const count = tab.indices === null
                ? this._instances.length
                : tab.indices.size;

            const el = document.createElement('div');
            el.className = `chrome-tab tab-color-${i % TAB_COLORS.length} ${isActive ? 'active-tab' : ''} ${tab.id === 'all' ? 'tab-all' : ''}`;
            el.style.setProperty('--tc', tab.color);
            el.dataset.tabId = tab.id;

            // Double-click to rename
            el.ondblclick = (e) => { e.stopPropagation(); this.startTabRename(tab.id); };
            el.onclick = (e) => {
                if (e.target.closest('.tab-close') || e.target.closest('.tab-label-input')) return;
                this.switchTab(tab.id);
            };

            // Label (normal or renaming)
            const labelHtml = (this._renamingTabId === tab.id)
                ? `<input type="text" class="tab-label-input" id="tab-rename-input"
                       value="${this._escapeHtml(tab.label)}"
                       onkeydown="EmulatorsPage.handleTabRenameKey(event,'${tab.id}')"
                       onblur="EmulatorsPage.commitTabRename('${tab.id}',this.value)"
                       onclick="event.stopPropagation()" />`
                : `<span class="tab-label">${this._escapeHtml(tab.label)}</span>`;

            el.innerHTML = `
                <div class="tab-favicon" style="background:${tab.color};opacity:${isActive ? '1' : '.4'};"></div>
                ${labelHtml}
                <span class="tab-count-pill">${count}</span>
                ${tab.id !== 'all' ? `<button class="tab-close" title="Close tab" onclick="EmulatorsPage.closeTab('${tab.id}',event)">
                  <svg width="8" height="8" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.8">
                    <line x1="1" y1="1" x2="9" y2="9"/><line x1="9" y1="1" x2="1" y2="9"/>
                  </svg>
                </button>` : ''}
            `;
            bar.appendChild(el);

            // Focus rename input
            if (this._renamingTabId === tab.id) {
                requestAnimationFrame(() => {
                    const inp = document.getElementById('tab-rename-input');
                    if (inp) { inp.focus(); inp.select(); }
                });
            }
        });

        // New tab button
        const newBtn = document.createElement('button');
        newBtn.className = 'new-tab-btn';
        newBtn.title = 'New tab';
        newBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`;
        newBtn.onclick = () => this.newTab();
        bar.appendChild(newBtn);
    },

    switchTab(id) {
        this._activeTabId = id;
        this._selectedInstances.clear();
        this.renderTabs();
        this.renderList();
        this.updateSelectionUI();
    },

    newTab() {
        this._tabCounter++;
        const id = `tab-${this._tabCounter}`;
        const color = TAB_COLORS[(this._tabs.length) % TAB_COLORS.length];
        this._tabs.push({ id, label: `Tab ${this._tabCounter}`, color, indices: new Set() });
        this.switchTab(id);
        // Auto-start rename on new tab
        this.startTabRename(id);
    },

    closeTab(id, e) {
        e.stopPropagation();
        const idx = this._tabs.findIndex(t => t.id === id);
        if (idx === -1) return;

        // Remove tab, items conceptually return to "All" since All ignores indices
        this._tabs.splice(idx, 1);
        if (this._activeTabId === id) {
            this._activeTabId = 'all';
        }
        this.renderTabs();
        this.renderList();
    },

    startTabRename(id) {
        this._renamingTabId = id;
        this.renderTabs();
    },

    handleTabRenameKey(e, id) {
        if (e.key === 'Enter') {
            e.preventDefault();
            this.commitTabRename(id, e.target.value.trim());
        } else if (e.key === 'Escape') {
            this._renamingTabId = null;
            this.renderTabs();
        }
    },

    commitTabRename(id, name) {
        this._renamingTabId = null;
        const tab = this._tabs.find(t => t.id === id);
        if (tab && name) tab.label = name;
        this.renderTabs();
    },

    /** Assign an instance to a tab */
    moveToTab(instIndex, tabId) {
        // Remove from all other non-all tabs
        this._tabs.forEach(tab => {
            if (tab.id !== 'all' && tab.indices) tab.indices.delete(instIndex);
        });
        if (tabId !== 'all') {
            const tab = this._tabs.find(t => t.id === tabId);
            if (tab && tab.indices) tab.indices.add(instIndex);
        }
        this.renderTabs();
        this.renderList();
        const tabName = tabId === 'all' ? 'All Instances' : (this._tabs.find(t => t.id === tabId)?.label || tabId);
        Toast.success('Moved', `Emulator #${instIndex} → "${tabName}"`);
    },

    getTabForInstance(instIndex) {
        for (const tab of this._tabs) {
            if (tab.id !== 'all' && tab.indices && tab.indices.has(instIndex)) return tab.id;
        }
        return 'all';
    },

    // ─────────────────────────────────────────────
    //  FILTER / SEARCH
    // ─────────────────────────────────────────────
    setSearch(query) {
        this._searchQuery = query.toLowerCase().trim();
        this.renderList();
    },


    clearFilters() {
        this._searchQuery = '';
        this._filter = 'all';

        const input = document.getElementById('emu-search-input');
        if (input) input.value = '';

        ['all', 'running', 'stopped'].forEach((f) => {
            const btn = document.getElementById(`filter-btn-${f}`);
            if (!btn) return;
            btn.classList.toggle('active', f === 'all');
            btn.style.background = f === 'all' ? 'var(--accent)' : 'transparent';
            btn.style.color = f === 'all' ? 'var(--foreground)' : 'var(--muted-foreground)';
        });

        this.renderInstances();
    },

    setFilter(filterMode) {
        this._filter = filterMode;
        ['all', 'running', 'stopped'].forEach(f => {
            const btn = document.getElementById(`filter-btn-${f}`);
            if (!btn) return;
            if (f === filterMode) {
                btn.classList.add('active');
                btn.style.background = 'var(--background)';
                btn.style.boxShadow = 'var(--shadow-sm)';
            } else {
                btn.classList.remove('active');
                btn.style.background = 'transparent';
                btn.style.boxShadow = 'none';
            }
        });
        this.renderList();
    },

    getActiveTabInstances() {
        const activeTab = this._tabs.find(t => t.id === this._activeTabId);
        if (!activeTab || activeTab.indices === null) return this._instances;
        return this._instances.filter(i => activeTab.indices.has(i.index));
    },

    getFilteredInstances() {
        return this.getActiveTabInstances().filter(inst => {
            if (this._searchQuery) {
                const needle = this._searchQuery;
                const haystack = `${inst.name} ${inst.index} ${this._adbSerial(inst.index)}`.toLowerCase();
                if (!haystack.includes(needle)) return false;
            }
            if (this._filter === 'running' && !inst.running) return false;
            if (this._filter === 'stopped' && inst.running) return false;
            return true;
        });
    },

    // ─────────────────────────────────────────────
    //  SELECTION
    // ─────────────────────────────────────────────
    toggleSelection(index, checked) {
        if (checked) {
            this._selectedInstances.add(index);
        } else {
            this._selectedInstances.delete(index);
        }
        this.updateSelectionUI();
    },

    toggleSelectAll(checked) {
        const filtered = this.getFilteredInstances();
        filtered.forEach(inst => {
            if (checked) {
                this._selectedInstances.add(inst.index);
            } else {
                this._selectedInstances.delete(inst.index);
            }
            const cb = document.getElementById(`emu-sel-${inst.index}`);
            if (cb) cb.checked = checked;
        });
        this.updateSelectionUI();
    },

    updateSelectionUI() {
        const count = this._selectedInstances.size;

        const btnStart = document.getElementById('btn-start-selected');
        const btnStop = document.getElementById('btn-stop-selected');
        const cStart = document.getElementById('selected-count-start');
        const cStop = document.getElementById('selected-count-stop');
        const hint = document.getElementById('emu-selection-hint');
        const label = document.getElementById('emu-selected-label');

        if (btnStart) btnStart.disabled = count === 0;
        if (btnStop) btnStop.disabled = count === 0;
        if (cStart) cStart.textContent = count;
        if (cStop) cStop.textContent = count;
        if (hint) hint.style.display = count > 0 ? 'inline' : 'none';
        if (label) label.textContent = count;

        const selectAllCb = document.getElementById('select-all-cb');
        const filtered = this.getFilteredInstances();
        if (selectAllCb) {
            selectAllCb.checked = filtered.length > 0 && filtered.every(i => this._selectedInstances.has(i.index));
            selectAllCb.indeterminate = count > 0 && !selectAllCb.checked;
        }
    },

    // ─────────────────────────────────────────────
    //  RENDER LIST
    // ─────────────────────────────────────────────
    renderList() {
        const list = document.getElementById('emu-list');
        if (!list) return;

        try {
            const filtered = this.getFilteredInstances();

            if (this._instances.length === 0) {
                list.innerHTML = `
                <div class="card" style="border-style:dashed; display:flex; flex-direction:column; align-items:center;
                    justify-content:center; padding:48px; color:var(--muted-foreground);">
                    <svg style="width:48px;height:48px;opacity:.4;margin-bottom:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="2" y="3" width="20" height="14" rx="2"/>
                        <line x1="8" y1="21" x2="16" y2="21"/>
                        <line x1="12" y1="17" x2="12" y2="21"/>
                    </svg>
                    <h3 style="font-size:16px;font-weight:500;margin-bottom:6px;">No LDPlayer Instances Found</h3>
                    <p class="text-sm">Install LDPlayer or check the <code>ldconsole.exe</code> path in <code>config.yaml</code>.</p>
                </div>`;
                return;
            }

            if (filtered.length === 0) {
                list.innerHTML = `
                <div class="empty-state">
                    <svg style="width:32px;height:32px;opacity:.4;margin-bottom:12px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    <p style="font-size:14px;">No instances match <em>"${this._escapeHtml(this._searchQuery || this._filter)}"</em>.</p>
                    <div style="display:flex; gap:8px; margin-top:4px;">
                        <button class="btn btn-outline btn-sm" onclick="EmulatorsPage.clearFilters()">Clear filters</button>
                        <button class="btn btn-default btn-sm" onclick="EmulatorsPage.manualRefresh()">Refresh now</button>
                    </div>
                </div>`;
                return;
            }

            list.innerHTML = filtered.map((inst, i) => this._renderCard(inst, i)).join('');

            this.updateSelectionUI();
        } catch (error) {
            console.error(error);
            list.innerHTML = `<div style="color: red; padding: 20px;">UI Render Error: ${error.message}</div>`;
        }
    },

    _renderCard(inst, animIndex) {
        const isSelected = this._selectedInstances.has(inst.index);
        const serial = this._adbSerial(inst.index);
        const isRenaming = this._renamingIndex === inst.index;

        const statusBadge = inst.running
            ? `<span class="badge badge-success" style="font-size:10px; letter-spacing:.04em;">RUNNING</span>`
            : `<span class="badge" style="background:var(--secondary);color:var(--muted-foreground);font-size:10px;letter-spacing:.04em;">STOPPED</span>`;

        const pidInfo = inst.running && inst.pid ? `PID ${inst.pid}` : `PID —`;

        // Running-only indicator bar (left accent)
        const accentBar = inst.running
            ? `position:relative; border-left: 3px solid var(--emerald-600);`
            : `position:relative; border-left: 3px solid transparent;`;

        // Stagger animation via style attribute
        const animDelay = `animation-delay:${animIndex * 40}ms;`;

        // Action buttons
        const actionBtns = inst.running
            ? `
            <button class="btn btn-outline btn-icon-sm" title="Stop emulator #${inst.index}"
                    onclick="EmulatorsPage.stopInstance(${inst.index})"
                    id="emu-btn-stop-${inst.index}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="6" y="6" width="12" height="12" rx="2"/>
                </svg>
            </button>
            <button class="btn btn-outline btn-icon-sm" title="Restart emulator #${inst.index}"
                    onclick="EmulatorsPage.restartInstance(${inst.index})"
                    id="emu-btn-restart-${inst.index}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                    <path d="M3 3v5h5"/>
                </svg>
            </button>`
            : `
            <button class="btn btn-outline btn-icon-sm" title="Start emulator #${inst.index}"
                    onclick="EmulatorsPage.startInstance(${inst.index})"
                    id="emu-btn-start-${inst.index}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
            </button>`;

        // Name cell: normal vs rename mode
        const nameCell = isRenaming
            ? `<input type="text" id="rename-input-${inst.index}"
                       value="${this._escapeHtml(inst.name)}"
                       class="form-input"
                       style="font-size:13px;font-weight:600;height:28px;padding:0 6px;width:160px;"
                       onkeydown="EmulatorsPage.handleRenameKey(event, ${inst.index})"
                       onblur="EmulatorsPage.cancelRename(${inst.index})"
                       onclick="event.stopPropagation()" />`
            : `<span class="device-name" style="font-size:13px; font-weight:600;"
                     title="Double-click to rename"
                     ondblclick="EmulatorsPage.startRename(${inst.index})">${this._escapeHtml(inst.name)}</span>`;

        return `
        <div class="device-card hover-bg hover-actions-container page-enter"
             style="padding:10px 14px; gap:12px; ${accentBar} ${animDelay} cursor:default;"
             id="emu-row-${inst.index}"
             oncontextmenu="EmulatorsPage.showContextMenu(event, ${inst.index})">

            <!-- Checkbox -->
            <input type="checkbox" id="emu-sel-${inst.index}"
                   ${isSelected ? 'checked' : ''}
                   onchange="EmulatorsPage.toggleSelection(${inst.index}, this.checked)"
                   onclick="event.stopPropagation()"
                   style="cursor:pointer; width:15px; height:15px; flex-shrink:0;" />

            <!-- Index badge -->
            <div class="device-icon-box"
                 style="width:34px; height:34px; font-size:11px; font-weight:700; flex-shrink:0;
                        ${inst.running ? 'background:hsla(152,69%,31%,0.12);color:var(--emerald-600);border-color:hsla(152,69%,31%,0.25)' : ''}">
                #${inst.index}
            </div>

            <!-- Info block -->
            <div class="device-info" style="display:flex; flex-direction:column; gap:3px; min-width:0; flex:1;">
                <div class="device-name-row" style="display:flex; align-items:center; gap:8px;">
                    ${nameCell}
                </div>
                <!-- Meta: PID | Resolution | DPI | ADB serial -->
                <span class="device-meta" style="font-size:11px; font-family:var(--font-mono); display:flex; gap:6px; align-items:center; flex-wrap:wrap; color:var(--muted-foreground);">
                    <span>${pidInfo}</span>
                    <span style="opacity:.3">|</span>
                    <span>${this._escapeHtml(inst.resolution || '—')}</span>
                    <span style="opacity:.3">|</span>
                    <span>DPI ${inst.dpi || '—'}</span>
                    <span style="opacity:.3">|</span>
                    <!-- ADB Serial with copy button -->
                    <span style="display:inline-flex; align-items:center; gap:4px;">
                        <span id="emu-serial-${inst.index}" style="color:var(--primary); opacity:.8;">${serial}</span>
                        <button onclick="EmulatorsPage.copySerial(${inst.index})" title="Copy ADB serial"
                                id="emu-copy-btn-${inst.index}"
                                style="background:none; border:none; cursor:pointer; padding:0 2px; color:var(--muted-foreground); display:inline-flex; align-items:center; line-height:1;">
                            <svg id="emu-copy-icon-${inst.index}" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2"/>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                            </svg>
                        </button>
                    </span>
                </span>
            </div>

            <!-- Right side: badge + actions -->
            <div style="margin-left:auto; display:flex; align-items:center; gap:14px; flex-shrink:0;">
                ${statusBadge}
                <div class="device-hover-actions" style="display:flex; gap:6px;">
                    ${actionBtns}
                    <!-- ··· menu button -->
                    <button class="btn btn-outline btn-icon-sm" title="More actions"
                            onclick="EmulatorsPage.showContextMenu(event, ${inst.index})" id="emu-btn-more-${inst.index}"
                            style="font-size:14px; letter-spacing:1px; font-weight:700; color:var(--muted-foreground);">
                        ···
                    </button>
                </div>
            </div>
        </div>`;
    },

    // ─────────────────────────────────────────────
    //  COPY ADB SERIAL
    // ─────────────────────────────────────────────
    async copySerial(index) {
        const serial = this._adbSerial(index);
        try {
            await navigator.clipboard.writeText(serial);
        } catch {
            // Fallback for pywebview
            const ta = document.createElement('textarea');
            ta.value = serial;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
        // Swap icon to checkmark briefly
        const icon = document.getElementById(`emu-copy-icon-${index}`);
        if (icon) {
            icon.outerHTML = `<svg id="emu-copy-icon-${index}" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="var(--emerald-600)" stroke-width="2.5">
                <polyline points="20 6 9 17 4 12"/>
            </svg>`;
            setTimeout(() => {
                const ic = document.getElementById(`emu-copy-icon-${index}`);
                if (ic) ic.outerHTML = `<svg id="emu-copy-icon-${index}" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>`;
            }, 1500);
        }
        Toast.success('Copied', `ADB serial "${serial}" copied to clipboard.`);
    },

    // ─────────────────────────────────────────────
    //  RENAME
    // ─────────────────────────────────────────────
    startRename(index) {
        this._renamingIndex = index;
        this.renderList();
        // Focus the input after render
        requestAnimationFrame(() => {
            const input = document.getElementById(`rename-input-${index}`);
            if (input) {
                input.focus();
                input.select();
            }
        });
    },

    handleRenameKey(event, index) {
        if (event.key === 'Enter') {
            event.preventDefault();
            this.commitRename(index, event.target.value.trim());
        } else if (event.key === 'Escape') {
            this.cancelRename(index);
        }
    },

    cancelRename(index) {
        if (this._renamingIndex === index) {
            this._renamingIndex = null;
            this.renderList();
        }
    },

    async commitRename(index, newName) {
        this._renamingIndex = null;
        if (!newName) { this.renderList(); return; }

        // Optimistically update local state
        const inst = this._instances.find(i => i.index === index);
        if (inst) inst.name = newName;
        this.renderList();

        try {
            await API.renameEmulator(index, newName);
            Toast.success('Renamed', `Instance #${index} renamed to "${newName}".`);
        } catch (e) {
            Toast.error('Rename Failed', 'Could not rename instance via API. Change shown locally only.');
        }
    },

    // ─────────────────────────────────────────────
    //  CONTEXT MENU
    // ─────────────────────────────────────────────
    showContextMenu(event, index) {
        event.preventDefault();
        event.stopPropagation();
        this._dismissContextMenu();

        const inst = this._instances.find(i => i.index === index);
        const currentTabId = this.getTabForInstance(index);

        let btnRect;
        // Check if triggered from the ··· button or right-click
        if (event.currentTarget && event.currentTarget.tagName === 'BUTTON') {
            btnRect = event.currentTarget.getBoundingClientRect();
        } else {
            btnRect = { right: event.clientX + 180, bottom: event.clientY - 4 }; // fallback for normal right-click on row
        }

        const menu = document.createElement('div');
        menu.className = 'dropdown-menu';
        menu.id = 'emu-context-menu';

        // ── Static items
        const items = [
            {
                icon: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
                label: 'Rename',
                action: () => this.startRename(index),
            },
            {
                icon: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
                label: 'Copy ADB Serial',
                action: () => this.copySerial(index),
            }
        ];

        items.forEach(item => {
            const btn = document.createElement('button');
            btn.className = 'dd-item';
            btn.innerHTML = `<span class="dd-icon">${item.icon}</span><span>${item.label}</span>`;
            btn.onclick = () => { item.action(); this._dismissContextMenu(); };
            menu.appendChild(btn);
        });

        // ── "Move to Tab" section
        const sep = document.createElement('div'); sep.className = 'dd-sep'; menu.appendChild(sep);
        const subLabel = document.createElement('div'); subLabel.className = 'dd-sub-label'; subLabel.textContent = 'Move to Tab'; menu.appendChild(subLabel);

        this._tabs.forEach(tab => {
            const isCurrent = tab.id === currentTabId;
            const btn = document.createElement('button');
            btn.className = `dd-item tab-option${isCurrent ? ' disabled' : ''}`;
            btn.innerHTML = `
                <span class="tab-dot" style="background:${tab.color};"></span>
                <span style="flex:1;">${this._escapeHtml(tab.label)}</span>
                ${isCurrent ? `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>` : ''}
            `;
            if (!isCurrent) btn.onclick = (e) => { e.stopPropagation(); this.moveToTab(index, tab.id); this._dismissContextMenu(); };
            menu.appendChild(btn);
        });

        // Add start/stop depending on state (at the end for convenience)
        const sep2 = document.createElement('div'); sep2.className = 'dd-sep'; menu.appendChild(sep2);
        if (inst && inst.running) {
            const btn = document.createElement('button');
            btn.className = 'dd-item danger';
            btn.innerHTML = `<span class="dd-icon"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="2"/></svg></span><span>Stop Instance</span>`;
            btn.onclick = (e) => { e.stopPropagation(); this.stopInstance(index); this._dismissContextMenu(); };
            menu.appendChild(btn);
        } else {
            const btn = document.createElement('button');
            btn.className = 'dd-item';
            btn.innerHTML = `<span class="dd-icon" style="color:var(--emerald-600);"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg></span><span>Start Instance</span>`;
            btn.onclick = (e) => { e.stopPropagation(); this.startInstance(index); this._dismissContextMenu(); };
            menu.appendChild(btn);
        }

        // Position below the ··· button or right-click coords
        menu.style.left = `${Math.min(btnRect.right - 180, window.innerWidth - 200)}px`;
        menu.style.top = `${Math.min(btnRect.bottom + 4, window.innerHeight - 300)}px`;

        document.body.appendChild(menu);
        this._contextMenu = menu;
    },

    _dismissContextMenu() {
        if (this._contextMenu) {
            this._contextMenu.remove();
            this._contextMenu = null;
        }
    },

    async _copyText(text, successMsg) {
        try {
            await navigator.clipboard.writeText(text);
        } catch {
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
        Toast.success('Copied', `${successMsg}: "${text}"`);
    },

    // ─────────────────────────────────────────────
    //  INSTANCE ACTIONS
    // ─────────────────────────────────────────────
    async startInstance(index) {
        const btnId = `emu-btn-start-${index}`;
        this._setSpinner(btnId);
        try {
            await API.launchEmulator(index);
            Toast.success('Launching', `Starting emulator #${index}…`);
            await this.refresh(true);
        } catch (e) {
            Toast.error('Error', `Failed to launch emulator #${index}.`);
            await this.refresh(true);
        }
    },

    async stopInstance(index) {
        const btnId = `emu-btn-stop-${index}`;
        this._setSpinner(btnId);
        try {
            await API.quitEmulator(index);
            Toast.info('Stopping', `Stopping emulator #${index}…`);
            await this.refresh(true);
        } catch (e) {
            Toast.error('Error', `Failed to stop emulator #${index}.`);
            await this.refresh(true);
        }
    },

    async restartInstance(index) {
        const btnId = `emu-btn-restart-${index}`;
        this._setSpinner(btnId);
        try {
            await API.quitEmulator(index);
            Toast.info('Restarting', `Stopping emulator #${index}…`);
            setTimeout(async () => {
                try {
                    await API.launchEmulator(index);
                    Toast.success('Restarted', `Emulator #${index} is coming up.`);
                    this.refresh(true);
                } catch { }
            }, 3000);
        } catch (e) {
            Toast.error('Error', `Failed to restart emulator #${index}.`);
            await this.refresh(true);
        }
    },

    /** NEW: Start all stopped instances */
    async startAll() {
        const stopped = this._instances.filter(i => !i.running);
        if (stopped.length === 0) { Toast.info('Start All', 'No stopped instances to start.'); return; }
        Toast.info('Start All', `Starting ${stopped.length} stopped instance(s)…`);
        for (const inst of stopped) {
            try { API.launchEmulator(inst.index); } catch { }
        }
        setTimeout(() => this.refresh(true), 2000);
    },

    /** NEW: Stop all running instances (with confirmation) */
    async stopAll() {
        const running = this._instances.filter(i => i.running);
        if (running.length === 0) { Toast.info('Stop All', 'No running instances to stop.'); return; }
        if (!confirm(`Stop all ${running.length} running instance(s)?`)) return;
        Toast.info('Stop All', `Stopping ${running.length} running instance(s)…`);
        for (const inst of running) {
            try { API.quitEmulator(inst.index); } catch { }
        }
        setTimeout(() => this.refresh(true), 2000);
    },

    // ─────────────────────────────────────────────
    //  BULK SELECTED ACTIONS
    // ─────────────────────────────────────────────
    async startSelected() {
        const indices = Array.from(this._selectedInstances);
        if (indices.length === 0) return;
        Toast.info('Batch Start', `Starting ${indices.length} emulator(s)…`);
        this._selectedInstances.clear();
        this.updateSelectionUI();
        for (const index of indices) {
            try { API.launchEmulator(index); } catch { }
        }
        setTimeout(() => this.refresh(true), 1500);
    },

    async stopSelected() {
        const indices = Array.from(this._selectedInstances);
        if (indices.length === 0) return;
        if (!confirm(`Stop ${indices.length} selected emulator(s)?`)) return;
        Toast.info('Batch Stop', `Stopping ${indices.length} emulator(s)…`);
        this._selectedInstances.clear();
        this.updateSelectionUI();
        for (const index of indices) {
            try { API.quitEmulator(index); } catch { }
        }
        setTimeout(() => this.refresh(true), 1500);
    },

    // ─────────────────────────────────────────────
    //  UTILITIES
    // ─────────────────────────────────────────────
    _setSpinner(btnId) {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.innerHTML = '<span class="spinner" style="width:12px;height:12px;border-width:2px;border-top-color:currentColor;"></span>';
            btn.disabled = true;
        }
    },

    _escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    },

    updateFromWS(event, data) {
        // Handle device_update for real-time status changes
        if (event === 'device_update') {
            const serial = data.serial;
            // Parse index from serial (emulator-XXXX)
            const match = serial && serial.match(/emulator-(\d+)/);
            if (match) {
                const port = parseInt(match[1]);
                const index = (port - 5554) / 2;
                const inst = this._instances.find(i => i.index === index);
                if (inst) {
                    inst.running = data.status === 'online';
                    this.updateStats();
                    this.renderList();
                }
            }
        }
    }
};
