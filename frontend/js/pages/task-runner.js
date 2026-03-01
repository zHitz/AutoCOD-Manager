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

    _macros: [],
    _currentTab: 'emulators',
    _apkLibrary: [
        { id: 'codm-v1', name: 'Call of Duty Mobile', package: 'com.activision.callofduty.shooter', version: '1.0.51', size: '2.6 GB', note: 'Stable global build', queued: false },
        { id: 'zarchiver-v1', name: 'ZArchiver', package: 'ru.zdevs.zarchiver', version: '1.0.10', size: '5.4 MB', note: 'Extract files inside emulator', queued: false },
        { id: 'gspace-v1', name: 'GSpace', package: 'com.gspace.android', version: '2.2.9', size: '18.2 MB', note: 'Google services helper', queued: false },
        { id: 'quicktouch-v1', name: 'QuickTouch Auto Clicker', package: 'simplehat.clicker', version: '4.8.3', size: '9.1 MB', note: 'Optional auto-tap support', queued: false },
    ],
    // key=`${index}-${filename}`, value={startTime, timer, duration}

    render() {
        return `
            <div class="page-enter">
                <div class="page-header">
                    <div class="page-header-info">
                        <h2>Actions</h2>
                        <p>Manage targets, run macros, and perform scans.</p>
                    </div>
                    <div class="page-actions">
                        <span class="text-sm text-muted" id="global-target-count">${GlobalStore.state.selectedEmus.length} emulator(s) selected</span>
                    </div>
                </div>

                <!-- Tab Bar -->
                <div class="actions-tabbar">
                    <button class="actions-tab active" data-tab="emulators" onclick="TaskRunnerPage.switchTab('emulators')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                        <span>Target Emulators</span>
                        <span class="tab-count" id="tab-emu-count">${GlobalStore.state.selectedEmus.length}</span>
                    </button>
                    <button class="actions-tab" data-tab="recorder" onclick="TaskRunnerPage.switchTab('recorder')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>
                        <span>Operation Recorder</span>
                    </button>
                    <button class="actions-tab" data-tab="scan" onclick="TaskRunnerPage.switchTab('scan')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        <span>Scan Operations</span>
                    </button>
                    <button class="actions-tab" data-tab="install-apps" onclick="TaskRunnerPage.switchTab('install-apps')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        <span>Install Apps</span>
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
                        ${GlobalStore.state.activityLogs.map(log => `
                            <div class="feed-item">
                                <span class="feed-dot ${log.dotClass}"></span>
                                <span class="text-xs text-muted" style="min-width:60px">${log.timeStr}</span>
                                <span>${log.message}</span>
                            </div>
                        `).join('')}
                    </div>
                    </div>
                </div>
            </div>
        `;
    },

    // ── Tab Switching ──

    switchTab(tab) {
        this._currentTab = tab;
        GlobalStore.setCurrentTab(tab);   // ★ Persist tab choice
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
            case 'install-apps': el.innerHTML = this._renderInstallAppsTab(); break;
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
                <div class="tab-panel-body" style="padding: 0;">
                    <div id="emu-checklist" class="emu-checklist"></div>
                </div>
                <div class="tab-panel-footer">
                    <span class="text-xs text-muted" id="emu-selected-count">${GlobalStore.state.selectedEmus.length} selected</span>
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
                const checked = GlobalStore.state.selectedEmus.includes(emu.index) ? 'checked' : '';
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
        if (checked) (GlobalStore.state.selectedEmus.includes(index) ? null : GlobalStore.state.selectedEmus.push(index));
        else GlobalStore.state.selectedEmus.splice(GlobalStore.state.selectedEmus.indexOf(index), 1);
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
            if (!allChecked) (GlobalStore.state.selectedEmus.includes(idx) ? null : GlobalStore.state.selectedEmus.push(idx));
            else GlobalStore.state.selectedEmus.splice(GlobalStore.state.selectedEmus.indexOf(idx), 1);
            const item = document.getElementById(`emu-item-${idx}`);
            if (item) item.classList.toggle('selected', !allChecked);
        });
        this._syncCounts();
    },

    _syncCounts() {
        const n = GlobalStore.state.selectedEmus.length;
        const u = (id, t) => { const e = document.getElementById(id); if (e) e.textContent = t; };
        u('emu-selected-count', `${n} selected`);
        u('tab-emu-count', n);
        u('global-target-count', `${n} emulator(s) selected`);
    },

    _getSelectedIndices() { return GlobalStore.state.selectedEmus; },

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

                // ★ CHECK GlobalStore for running state
                const runData = GlobalStore.state.runningMacros[m.filename];
                const isRunning = !!runData;

                const statusHtml = isRunning ? `
                    <div class="macro-running-bar">
                        <span class="spinner" style="width:12px;height:12px"></span>
                        <span class="macro-running-text">Running on ${runData.emulatorCount || '?'} emulator(s)...</span>
                        <span class="macro-elapsed" id="${key}-elapsed"></span>
                    </div>` : '';

                const btnHtml = isRunning
                    ? `<button class="btn btn-default btn-sm" style="width:100%;gap:6px" id="${key}-btn" disabled>
                           <span class="spinner"></span> Running...
                       </button>`
                    : `<button class="btn btn-default btn-sm" style="width:100%;gap:6px" id="${key}-btn"
                               onclick="TaskRunnerPage.runMacro('${m.filename}')">
                           <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                           Run Script
                       </button>`;

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
                        <div class="macro-card-status" id="${key}-status">${statusHtml}</div>
                        <div class="macro-card-footer">${btnHtml}</div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            grid.innerHTML = `<div class="text-muted text-sm" style="padding:24px;text-align:center;grid-column:1/-1">Failed to load scripts.</div>`;
        }
    },

    async runMacro(filename) {
        const indices = GlobalStore.state.selectedEmus;
        if (indices.length === 0) {
            Toast.warning('No Target', 'Select emulators in the Target Emulators tab first');
            return;
        }

        const macro = this._macros.find(m => m.filename === filename);
        const name = macro ? macro.name : filename;
        const cardKey = `macro-card-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const btn = document.getElementById(`${cardKey}-btn`);
        const statusEl = document.getElementById(`${cardKey}-status`);

        // Set local running UI state on action
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Running...';
        }
        if (statusEl) {
            statusEl.innerHTML = `
                <div class="macro-running-bar">
                    <span class="spinner" style="width:12px;height:12px"></span>
                    <span class="macro-running-text">Running on ${indices.length} emulator(s)...</span>
                    <span class="macro-elapsed" id="${cardKey}-elapsed">0s</span>
                </div>
            `;
        }

        // Set state in the serializable GlobalStore
        GlobalStore.setMacroRunning(filename, indices.length, 0);

        // Execute on all selected emulators
        let successCount = 0;
        let totalDuration = 0;
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
                this.addFeed('fail', `✗ Network error on #${idx}: ${e.message}`);
            }
        }

        // Success flow
        if (successCount > 0) {
            GlobalStore.setMacroRunning(filename, successCount, totalDuration); // update true duration

            Toast.success('Macro Started', `"${name}" running on ${successCount} emulator(s)`);
            NotificationManager.add('info', 'Macro Running', `"${name}" on ${successCount} instance(s)`);

            const cleanUpHook = () => {
                GlobalStore.removeMacroRunning(filename);
                if (statusEl) {
                    const durationSec = Math.round(totalDuration / 1000);
                    const durationText = durationSec > 60 ? `${Math.floor(durationSec / 60)}m ${durationSec % 60}s` : `${durationSec}s`;
                    statusEl.innerHTML = `
                        <div class="macro-done-bar">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;color:var(--emerald-500)"><polyline points="20 6 9 17 4 12"/></svg>
                            <span>Completed • ${totalDuration > 0 ? durationText : 'Done'}</span>
                        </div>
                    `;
                }
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Script';
                }
                for (const idx of indices) {
                    this.addFeed('done', `✓ Macro "${name}" completed on Emulator #${idx}`);
                }
            };

            if (totalDuration > 0) setTimeout(cleanUpHook, totalDuration);
            else setTimeout(cleanUpHook, 3000);

        } else {
            // Failure flow
            GlobalStore.removeMacroRunning(filename);
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
        if (GlobalStore.state.selectedEmus.length === 0) {
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

    // ═══════════════════════════════════════════
    // TAB 4: Install Apps
    // ═══════════════════════════════════════════

    _renderInstallAppsTab() {
        const targetHtml = this._targetBadge();
        return `
            <div class="tab-panel">
                <div class="tab-panel-header">
                    <div>
                        <h3 class="tab-panel-title">Install Apps</h3>
                        <p class="text-sm text-muted">Preloaded APK library ready for you to install on target emulators.</p>
                    </div>
                </div>
                <div class="tab-panel-body">
                    ${targetHtml}
                    <div class="apk-library" id="apk-library-grid">
                        ${this._renderApkCards()}
                    </div>
                </div>
            </div>
        `;
    },

    _renderApkCards() {
        return this._apkLibrary.map(app => `
            <div class="apk-card">
                <div class="apk-card-header">
                    <div>
                        <div class="apk-card-name">${app.name}</div>
                        <div class="apk-card-package">${app.package}</div>
                    </div>
                    ${this._installStatusBadge(app.queued)}
                </div>
                <div class="apk-card-meta">
                    <span>Version ${app.version}</span>
                    <span>•</span>
                    <span>${app.size}</span>
                </div>
                <p class="apk-card-note">${app.note}</p>
                <button class="btn ${app.queued ? 'btn-outline' : 'btn-default'} btn-sm" style="width:100%"
                    onclick="TaskRunnerPage.queueInstall('${app.id}')">
                    ${app.queued ? 'Waiting for install' : 'Install on selected emulators'}
                </button>
            </div>
        `).join('');
    },

    _installStatusBadge(isQueued) {
        if (isQueued) {
            return '<span class="badge badge-busy">WAITING</span>';
        }
        return '<span class="badge badge-online">READY</span>';
    },

    queueInstall(appId) {
        const app = this._apkLibrary.find(item => item.id === appId);
        if (!app) return;

        if (GlobalStore.state.selectedEmus.length === 0) {
            Toast.warning('No emulator selected', 'Please select at least one emulator before installing apps.');
            return;
        }

        app.queued = true;
        this.addFeed('active', `📦 App "${app.name}" queued for installation on ${GlobalStore.state.selectedEmus.length} emulator(s)`);
        Toast.success('Added to install queue', `${app.name} is waiting for your install confirmation.`);

        const grid = document.getElementById('apk-library-grid');
        if (grid) grid.innerHTML = this._renderApkCards();
    },

    // ── Shared Helpers ──

    _targetBadge() {
        const n = GlobalStore.state.selectedEmus.length;
        if (n === 0) {
            return `<div class="emu-selected-badge"><span class="badge badge-outline" style="font-size:12px;padding:4px 12px">⚠ No emulators selected — go to Target Emulators tab</span></div>`;
        }
        return `<div class="emu-selected-badge"><span class="badge badge-online" style="font-size:12px;padding:4px 12px">✓ ${n} emulator(s) targeted</span></div>`;
    },

    addFeed(dotClass, text) {
        // ★ CRITICAL FIX: Write to GlobalStore so logs survive page navigation
        GlobalStore.addActivityLog(text, dotClass);
    },

    updateFromWS(event, data) {
        const dotMap = {
            task_started: 'active', task_progress: 'active', task_completed: 'done', task_failed: 'fail',
            macro_started: 'active', macro_progress: 'active', macro_completed: 'done', macro_failed: 'fail'
        };

        let msg = `[${data.serial || '?'}] `;
        if (event.startsWith('macro_')) {
            msg += `Macro "${data.filename}": `;
            if (event === 'macro_started') msg += 'Started';
            else if (event === 'macro_progress') msg += `Progress ${data.completed}/${data.total}`;
            else if (event === 'macro_completed') msg += `Completed in ${data.elapsed_ms}ms`;
            else if (event === 'macro_failed') msg += `Failed: ${data.error}`;
        } else {
            msg += (data.step || data.status || event);
        }

        this.addFeed(dotMap[event] || 'active', msg);
    },

    // ── Lifecycle ──

    _unsubscribeStore: null,
    _uiTimer: null,

    // Render ONLY the live-feed from GlobalStore (no full page re-render)
    _renderLiveFeed() {
        const liveFeed = document.getElementById('live-feed');
        if (liveFeed) {
            liveFeed.innerHTML = GlobalStore.state.activityLogs.map(log => `
                <div class="feed-item">
                    <span class="feed-dot ${log.dotClass}"></span>
                    <span class="text-xs text-muted" style="min-width:60px">${log.timeStr}</span>
                    <span>${log.message}</span>
                </div>
            `).join('');
        }
    },

    _syncCountsFromStore() {
        const n = GlobalStore.state.selectedEmus.length;
        const u = (id, t) => { const e = document.getElementById(id); if (e) e.textContent = t; };
        u('emu-selected-count', `${n} selected`);
        u('tab-emu-count', n);
        u('global-target-count', `${n} emulator(s) selected`);
    },

    // Re-apply running state to macro cards already in the DOM
    _reconcileMacroCards() {
        if (this._currentTab !== 'recorder') return;
        if (!this._macros || this._macros.length === 0) return;

        for (const m of this._macros) {
            const cardKey = `macro-card-${m.filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
            const btn = document.getElementById(`${cardKey}-btn`);
            const statusEl = document.getElementById(`${cardKey}-status`);
            const isRunning = !!GlobalStore.state.runningMacros[m.filename];

            if (isRunning) {
                const data = GlobalStore.state.runningMacros[m.filename];
                if (btn) {
                    btn.disabled = true;
                    btn.innerHTML = '<span class="spinner"></span> Running...';
                }
                if (statusEl && !statusEl.querySelector('.macro-running-bar')) {
                    statusEl.innerHTML = `
                        <div class="macro-running-bar">
                            <span class="spinner" style="width:12px;height:12px"></span>
                            <span class="macro-running-text">Running on ${data.emulatorCount || '?'} emulator(s)...</span>
                            <span class="macro-elapsed" id="${cardKey}-elapsed"></span>
                        </div>
                    `;
                }
            } else {
                if (btn && btn.disabled) {
                    btn.disabled = false;
                    btn.innerHTML = '<svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Script';
                }
            }
        }
    },

    // Tick elapsed timers purely from startTime in store
    _startUIChecks() {
        if (this._uiTimer) clearInterval(this._uiTimer);
        this._uiTimer = setInterval(() => {
            for (const [filename, data] of Object.entries(GlobalStore.state.runningMacros)) {
                if (!data) continue;
                const elapsed = Math.floor((Date.now() - data.startTime) / 1000);
                const m = Math.floor(elapsed / 60);
                const s = elapsed % 60;
                const cardKey = `macro-card-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
                const elEl = document.getElementById(`${cardKey}-elapsed`);
                if (elEl) elEl.textContent = m > 0 ? `${m}m ${s}s` : `${s}s`;
            }
        }, 1000);
    },

    init() {
        // Subscribe to store — update ONLY live parts, never full re-render
        this._unsubscribeStore = GlobalStore.subscribe(() => {
            if (router && router._currentPage === 'runner') {
                this._renderLiveFeed();
                this._syncCountsFromStore();
                this._reconcileMacroCards();
            }
        });
        this._startUIChecks();

        // ★ CRITICAL FIX: Restore persisted tab from GlobalStore, NOT always 'emulators'
        this._currentTab = GlobalStore.state.currentTab || 'emulators';
        this.switchTab(this._currentTab);
    },

    destroy() {
        if (this._unsubscribeStore) this._unsubscribeStore();
        if (this._uiTimer) clearInterval(this._uiTimer);
    }
};
