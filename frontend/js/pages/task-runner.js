/**
 * Task Runner (Actions) Page
 *
 * Layout:
 *   ┌────────────────────────────────────────────────────┐
 *   │  [📱 Emulators] [🔴 Recorder] [🔍 Scan]  ← Tabs  │
 *   ├────────────────────────────────────────────────────┤
 *   │  Tab Content                                       │
 *   ├────────────────────────────────────────────────────┤
 *   │  Activity Feed (shared)                            │
 *   └────────────────────────────────────────────────────┘
 */
const TaskRunnerPage = {
    _selectedEmus: new Set(),
    _macros: [],
    _currentTab: 'emulators',
    _runningMacros: new Map(),  // key=`${index}-${filename}`, value={startTime, timer, duration}

    render() {
        return `
            <div class="page-enter">
                <div class="page-header">
                    <div class="page-header-info">
                        <h2>Actions</h2>
                        <p>Manage targets, run macros, and perform scans.</p>
                    </div>
                    <div class="page-actions">
                        <span class="text-sm text-muted" id="global-target-count">${this._selectedEmus.size} emulator(s) selected</span>
                    </div>
                </div>

                <!-- Tab Bar -->
                <div class="actions-tabbar">
                    <button class="actions-tab active" data-tab="emulators" onclick="TaskRunnerPage.switchTab('emulators')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                        <span>Target Emulators</span>
                        <span class="tab-count" id="tab-emu-count">${this._selectedEmus.size}</span>
                    </button>
                    <button class="actions-tab" data-tab="recorder" onclick="TaskRunnerPage.switchTab('recorder')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>
                        <span>Operation Recorder</span>
                    </button>
                    <button class="actions-tab" data-tab="scan" onclick="TaskRunnerPage.switchTab('scan')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        <span>Scan Operations</span>
                    </button>
                </div>

                <!-- Tab Content Area -->
                <div class="actions-tab-content" id="tab-content"></div>

                <!-- Shared Activity Feed -->
                <div class="section-header" style="margin-top:24px">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                    <h3>Activity Feed</h3>
                </div>
                <div class="card" style="padding:0;overflow:hidden">
                    <div class="live-feed" id="live-feed">
                        <div class="text-muted text-sm" style="padding:24px;text-align:center">
                            Select emulators → run actions to see progress here
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    // ── Tab Switching ──

    switchTab(tab) {
        this._currentTab = tab;
        document.querySelectorAll('.actions-tab').forEach(t =>
            t.classList.toggle('active', t.dataset.tab === tab)
        );
        this._renderTabContent(tab);
    },

    _renderTabContent(tab) {
        const el = document.getElementById('tab-content');
        if (!el) return;
        switch (tab) {
            case 'emulators': el.innerHTML = this._renderEmuTab(); this._loadEmuList(); break;
            case 'recorder': el.innerHTML = this._renderRecorderTab(); this.loadMacros(); break;
            case 'scan': el.innerHTML = this._renderScanTab(); break;
        }
    },

    // ═══════════════════════════════════════════
    // TAB 1: Target Emulators
    // ═══════════════════════════════════════════

    _renderEmuTab() {
        return `
            <div class="tab-panel">
                <div class="tab-panel-header">
                    <div>
                        <h3 class="tab-panel-title">Select Target Emulators</h3>
                        <p class="text-sm text-muted">Choose running instances to use as targets for Recorder and Scan tabs.</p>
                    </div>
                    <div class="tab-panel-actions">
                        <button class="btn btn-ghost btn-sm" onclick="TaskRunnerPage.toggleAll()">Select All</button>
                        <button class="btn btn-outline btn-sm" onclick="TaskRunnerPage._loadEmuList()">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Refresh
                        </button>
                    </div>
                </div>
                <div id="emu-checklist" class="emu-checklist"></div>
                <div class="tab-panel-footer">
                    <span class="text-xs text-muted" id="emu-selected-count">${this._selectedEmus.size} selected</span>
                </div>
            </div>
        `;
    },

    async _loadEmuList() {
        const list = document.getElementById('emu-checklist');
        if (!list) return;
        list.innerHTML = '<div class="text-muted text-sm" style="padding:24px;text-align:center"><span class="spinner"></span></div>';

        try {
            const instances = await API.getAllEmulators();
            const running = instances.filter(i => i.running);

            if (running.length === 0) {
                list.innerHTML = `
                    <div class="emu-empty">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:36px;height:36px;opacity:0.3;margin-bottom:8px"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                        <p class="font-medium">No running emulators</p>
                        <p class="text-xs text-muted">Start instances from the Emulators page first.</p>
                    </div>`;
                return;
            }

            list.innerHTML = running.map(emu => {
                const checked = this._selectedEmus.has(emu.index) ? 'checked' : '';
                const sel = checked ? 'selected' : '';
                return `
                    <label class="emu-check-item ${sel}" id="emu-item-${emu.index}">
                        <input type="checkbox" value="${emu.index}" ${checked}
                               onchange="TaskRunnerPage.toggleEmu(${emu.index}, this.checked)">
                        <div class="emu-check-icon">#${emu.index}</div>
                        <div class="emu-check-info">
                            <span class="emu-check-name">${emu.name}</span>
                            <span class="emu-check-meta">${emu.resolution} • DPI ${emu.dpi}</span>
                        </div>
                        <span class="badge badge-online" style="font-size:9px;padding:1px 6px">RUNNING</span>
                    </label>
                `;
            }).join('');
        } catch (e) {
            list.innerHTML = `<div class="text-muted text-sm" style="padding:24px;text-align:center">Failed to load emulators</div>`;
        }
    },

    toggleEmu(index, checked) {
        if (checked) this._selectedEmus.add(index);
        else this._selectedEmus.delete(index);
        const item = document.getElementById(`emu-item-${index}`);
        if (item) item.classList.toggle('selected', checked);
        this._syncCounts();
    },

    toggleAll() {
        const cbs = document.querySelectorAll('#emu-checklist input[type="checkbox"]');
        const allChecked = [...cbs].every(c => c.checked);
        cbs.forEach(cb => {
            cb.checked = !allChecked;
            const idx = parseInt(cb.value);
            if (!allChecked) this._selectedEmus.add(idx);
            else this._selectedEmus.delete(idx);
            const item = document.getElementById(`emu-item-${idx}`);
            if (item) item.classList.toggle('selected', !allChecked);
        });
        this._syncCounts();
    },

    _syncCounts() {
        const n = this._selectedEmus.size;
        const u = (id, t) => { const e = document.getElementById(id); if (e) e.textContent = t; };
        u('emu-selected-count', `${n} selected`);
        u('tab-emu-count', n);
        u('global-target-count', `${n} emulator(s) selected`);
    },

    _getSelectedIndices() { return [...this._selectedEmus]; },

    // ═══════════════════════════════════════════
    // TAB 2: Operation Recorder
    // ═══════════════════════════════════════════

    _renderRecorderTab() {
        const targetHtml = this._targetBadge();
        return `
            <div class="tab-panel">
                <div class="tab-panel-header">
                    <div>
                        <h3 class="tab-panel-title">Operation Recorder</h3>
                        <p class="text-sm text-muted">Run saved LDPlayer macro scripts (.record files) on selected emulators.</p>
                    </div>
                    <div class="tab-panel-actions">
                        <button class="btn btn-outline btn-sm" onclick="TaskRunnerPage.loadMacros()">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Reload
                        </button>
                    </div>
                </div>
                <div class="tab-panel-body">
                    ${targetHtml}
                    <div class="grid-3" id="macro-grid">
                        <div class="text-muted text-sm" style="padding:24px;text-align:center;grid-column:1/-1"><span class="spinner"></span></div>
                    </div>
                </div>
            </div>
        `;
    },

    async loadMacros() {
        const grid = document.getElementById('macro-grid');
        if (!grid) return;

        try {
            this._macros = await API.getMacros();

            if (!this._macros || this._macros.length === 0) {
                grid.innerHTML = `<div class="text-muted text-sm" style="padding:24px;text-align:center;grid-column:1/-1">No macro scripts found.</div>`;
                return;
            }

            grid.innerHTML = this._macros.map(m => {
                const sizeKb = (m.size_bytes / 1024).toFixed(1);
                const modified = new Date(m.modified * 1000).toLocaleDateString();
                const key = `macro-card-${m.filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
                return `
                    <div class="macro-card" id="${key}">
                        <div class="macro-card-header">
                            <div class="macro-card-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3" fill="currentColor"/>
                                </svg>
                            </div>
                            <div class="macro-card-info">
                                <div class="macro-card-name">${m.name}</div>
                                <div class="macro-card-meta">${sizeKb} KB • ${modified}</div>
                            </div>
                        </div>
                        <div class="macro-card-status" id="${key}-status"></div>
                        <div class="macro-card-footer">
                            <button class="btn btn-default btn-sm" style="width:100%;gap:6px" id="${key}-btn"
                                    onclick="TaskRunnerPage.runMacro('${m.filename}')">
                                <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                                Run Script
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            grid.innerHTML = `<div class="text-muted text-sm" style="padding:24px;text-align:center;grid-column:1/-1">Failed to load scripts.</div>`;
        }
    },

    async runMacro(filename) {
        const indices = this._getSelectedIndices();
        if (indices.length === 0) {
            Toast.warning('No Target', 'Select emulators in the Target Emulators tab first');
            return;
        }

        const macro = this._macros.find(m => m.filename === filename);
        const name = macro ? macro.name : filename;
        const cardKey = `macro-card-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const btn = document.getElementById(`${cardKey}-btn`);
        const statusEl = document.getElementById(`${cardKey}-status`);

        // Set running state
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Running...';
        }

        const startTime = Date.now();
        let totalDuration = 0;

        // Start elapsed timer
        if (statusEl) {
            statusEl.innerHTML = `
                <div class="macro-running-bar">
                    <span class="spinner" style="width:12px;height:12px"></span>
                    <span class="macro-running-text">Running on ${indices.length} emulator(s)...</span>
                    <span class="macro-elapsed" id="${cardKey}-elapsed">0s</span>
                </div>
            `;
        }

        const timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const m = Math.floor(elapsed / 60);
            const s = elapsed % 60;
            const elEl = document.getElementById(`${cardKey}-elapsed`);
            if (elEl) elEl.textContent = m > 0 ? `${m}m ${s}s` : `${s}s`;
        }, 1000);

        // Execute on all selected emulators
        let successCount = 0;
        for (const idx of indices) {
            try {
                const result = await API.runMacro(idx, filename);
                if (result.success) {
                    successCount++;
                    totalDuration = Math.max(totalDuration, result.duration_ms || 0);
                    this.addFeed('active', `▶ Macro "${name}" → Emulator #${idx}`);
                } else {
                    this.addFeed('fail', `✗ Failed #${idx}: ${result.error}`);
                }
            } catch (e) {
                this.addFeed('fail', `✗ Network error on #${idx}`);
            }
        }

        // Show estimated duration
        const durationSec = Math.round(totalDuration / 1000);
        const durationText = durationSec > 60
            ? `${Math.floor(durationSec / 60)}m ${durationSec % 60}s`
            : `${durationSec}s`;

        if (successCount > 0) {
            Toast.success('Macro Started', `"${name}" running on ${successCount} emulator(s)`);
            NotificationManager.add('info', 'Macro Running', `"${name}" on ${successCount} instance(s)`);

            // Keep timer running for estimated duration, then show "done"
            if (totalDuration > 0) {
                setTimeout(() => {
                    clearInterval(timerInterval);
                    if (statusEl) {
                        statusEl.innerHTML = `
                            <div class="macro-done-bar">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;color:var(--emerald-500)"><polyline points="20 6 9 17 4 12"/></svg>
                                <span>Completed • ${durationText}</span>
                            </div>
                        `;
                    }
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = '<svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Script';
                    }
                    this.addFeed('done', `✓ Macro "${name}" completed (≈${durationText})`);
                }, totalDuration);
            } else {
                // No duration info — reset after 3s
                setTimeout(() => {
                    clearInterval(timerInterval);
                    if (statusEl) statusEl.innerHTML = '';
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = '<svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Script';
                    }
                }, 3000);
            }
        } else {
            clearInterval(timerInterval);
            if (statusEl) statusEl.innerHTML = `<div class="macro-done-bar" style="color:var(--red-500)"><span>All executions failed</span></div>`;
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Script';
            }
        }
    },

    // ═══════════════════════════════════════════
    // TAB 3: Scan Operations
    // ═══════════════════════════════════════════

    _renderScanTab() {
        const targetHtml = this._targetBadge();
        return `
            <div class="tab-panel">
                <div class="tab-panel-header">
                    <div>
                        <h3 class="tab-panel-title">Scan Operations</h3>
                        <p class="text-sm text-muted">Run OCR-based scans on selected emulators.</p>
                    </div>
                </div>
                <div class="tab-panel-body">
                    ${targetHtml}
                    <div class="grid-4" id="scan-cards">
                        ${this._scanCard('Profile Scan', 'Player name + power level', 'profile',
            `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--indigo-500)"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`)}
                        ${this._scanCard('Resource Scan', 'Gold, wood, ore, mana', 'resources',
                `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--emerald-500)"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>`)}
                        ${this._scanCard('Hall Level', 'Town hall building level', 'hall',
                    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--orange-500)"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`)}
                        ${this._scanCard('Full Scan', 'All scans in sequence', 'full_scan',
                        `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--purple-500)"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`)}
                    </div>
                </div>
            </div>
        `;
    },

    _scanCard(title, desc, type, iconSvg) {
        return `
            <div class="action-card">
                <div class="action-card-header">
                    <span class="action-card-title">${title}</span>
                    <span class="action-card-icon">${iconSvg}</span>
                </div>
                <div class="action-card-content">
                    <p class="action-card-desc">${desc}</p>
                    <button class="btn btn-secondary btn-sm" style="width:100%;gap:6px" onclick="TaskRunnerPage.runScan('${type}')">
                        <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                        Run
                    </button>
                </div>
            </div>
        `;
    },

    async runScan(type) {
        if (this._selectedEmus.size === 0) {
            Toast.warning('No Target', 'Select emulators in the Target Emulators tab first');
            return;
        }
        try {
            const result = await API.runAllTasks(type);
            this.addFeed('active', `▶ Batch: ${result.count || 0} × ${type} queued`);
            Toast.success('Scan Started', `${type} scan on ${result.count || 0} devices`);
        } catch (e) {
            Toast.error('Error', 'Failed to run scan');
        }
    },

    // ── Shared Helpers ──

    _targetBadge() {
        const n = this._selectedEmus.size;
        if (n === 0) {
            return `<div class="emu-selected-badge"><span class="badge badge-outline" style="font-size:12px;padding:4px 12px">⚠ No emulators selected — go to Target Emulators tab</span></div>`;
        }
        return `<div class="emu-selected-badge"><span class="badge badge-online" style="font-size:12px;padding:4px 12px">✓ ${n} emulator(s) targeted</span></div>`;
    },

    addFeed(dotClass, text) {
        const feed = document.getElementById('live-feed');
        if (!feed) return;
        const placeholder = feed.querySelector('.text-muted');
        if (placeholder) placeholder.remove();

        const item = document.createElement('div');
        item.className = 'feed-item feed-item-enter';
        item.innerHTML = `
            <span class="feed-dot ${dotClass}"></span>
            <span class="text-xs text-muted" style="min-width:60px">${new Date().toLocaleTimeString()}</span>
            <span>${text}</span>
        `;
        feed.prepend(item);
        while (feed.children.length > 50) feed.lastChild.remove();
    },

    updateFromWS(event, data) {
        const dotMap = { task_started: 'active', task_progress: 'active', task_completed: 'done', task_failed: 'fail' };
        this.addFeed(dotMap[event] || 'active', `[${data.serial || '?'}] ${data.step || data.status || event}`);
    },

    // ── Lifecycle ──
    async init() { this._currentTab = 'emulators'; this.switchTab('emulators'); },
    destroy() { },
};
