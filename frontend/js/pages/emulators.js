/**
 * Emulators Page — Full PC Discovery + Start/Stop.
 * Lists ALL LDPlayer instances via ldconsole list2.
 */
const EmulatorsPage = {
    _pollInterval: null,

    render() {
        return `
            <div class="page-enter">
                <div class="page-header">
                    <div class="page-header-info">
                        <h2>Emulator Instances</h2>
                        <p>Manage all LDPlayer instances — start, stop, and monitor status.</p>
                    </div>
                    <div class="page-actions">
                        <button class="btn btn-outline btn-sm" onclick="EmulatorsPage.refresh()">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Refresh All
                        </button>
                    </div>
                </div>

                <!-- Summary Stats -->
                <div class="stats-row" id="emu-stats">
                    <div class="card stat-card-indigo">
                        <div class="card-header-row">
                            <span class="card-title">Total Instances</span>
                            <span class="card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></span>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="emu-stat-total">0</div>
                            <p class="card-subtitle">All LDPlayer instances</p>
                        </div>
                    </div>
                    <div class="card stat-card-emerald">
                        <div class="card-header-row">
                            <span class="card-title">Running</span>
                            <span class="card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg></span>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="emu-stat-running">0</div>
                            <p class="card-subtitle">Active right now</p>
                        </div>
                    </div>
                    <div class="card stat-card-orange">
                        <div class="card-header-row">
                            <span class="card-title">Stopped</span>
                            <span class="card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="2"/></svg></span>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="emu-stat-stopped">0</div>
                            <p class="card-subtitle">Ready to launch</p>
                        </div>
                    </div>
                </div>

                <!-- Instance List -->
                <div class="grid-1" id="emu-list">
                    <div class="empty-state">
                        <div class="empty-state-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></div>
                        <span class="font-medium">Loading instances...</span>
                        <span class="spinner"></span>
                    </div>
                </div>
            </div>
        `;
    },

    async init() {
        await this.refresh();
        this._pollInterval = setInterval(() => this.refresh(), 5000);
    },

    destroy() {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
            this._pollInterval = null;
        }
    },

    async refresh() {
        try {
            const instances = await API.getAllEmulators();
            this.renderList(instances);
            this.updateStats(instances);
        } catch (e) {
            Toast.error('Error', 'Failed to fetch LDPlayer instances');
        }
    },

    updateStats(instances) {
        if (!instances) return;
        const total = instances.length;
        const running = instances.filter(i => i.running).length;
        const stopped = total - running;
        const u = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        u('emu-stat-total', total);
        u('emu-stat-running', running);
        u('emu-stat-stopped', stopped);
    },

    renderList(instances) {
        const list = document.getElementById('emu-list');
        if (!list) return;

        if (!instances || instances.length === 0) {
            list.innerHTML = `
                <div class="card" style="border-style:dashed;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:48px;color:var(--muted-foreground)">
                    <svg style="width:48px;height:48px;opacity:0.5;margin-bottom:16px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                    <h3 style="font-size:18px;font-weight:500">No LDPlayer Instances Found</h3>
                    <p class="text-sm">Install LDPlayer or check ldconsole.exe path.</p>
                </div>
            `;
            return;
        }

        list.innerHTML = instances.map((inst, i) => {
            const statusBadge = inst.running
                ? `<span class="badge badge-online">RUNNING</span>`
                : `<span class="badge badge-offline">STOPPED</span>`;

            const actionBtn = inst.running
                ? `<button class="btn btn-destructive btn-sm" style="min-width:80px;gap:4px" onclick="EmulatorsPage.stopInstance(${inst.index})" id="emu-btn-${inst.index}">
                       <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
                       Stop
                   </button>`
                : `<button class="btn btn-default btn-sm" style="min-width:80px;gap:4px" onclick="EmulatorsPage.startInstance(${inst.index})" id="emu-btn-${inst.index}">
                       <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                       Start
                   </button>`;

            const pidInfo = inst.running && inst.pid
                ? `PID: ${inst.pid} • `
                : '';

            return `
                <div class="device-card" style="animation-delay:${i * 40}ms" id="emu-row-${inst.index}">
                    <div class="device-icon-box" style="font-size:12px;${inst.running ? 'background:hsla(152,69%,31%,0.1);color:var(--emerald-600);border-color:hsla(152,69%,31%,0.2)' : ''}">
                        #${inst.index}
                    </div>
                    <div class="device-info">
                        <div class="device-name-row">
                            <span class="device-name">${inst.name}</span>
                            ${statusBadge}
                        </div>
                        <span class="device-meta">
                            ${pidInfo}${inst.resolution} • DPI: ${inst.dpi}
                        </span>
                    </div>
                    <div class="device-actions">
                        ${actionBtn}
                    </div>
                </div>
            `;
        }).join('');
    },

    async startInstance(index) {
        const btn = document.getElementById(`emu-btn-${index}`);
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Starting...';
        }

        try {
            await API.launchEmulator(index);
            Toast.success('Launching', `Starting emulator #${index}...`);
            NotificationManager.add('info', 'Emulator Launch', `Instance #${index} starting...`);
            // Delay refresh to allow LDPlayer to start
            setTimeout(() => this.refresh(), 3000);
        } catch (e) {
            Toast.error('Error', 'Failed to launch emulator');
            if (btn) btn.disabled = false;
        }
    },

    async stopInstance(index) {
        const btn = document.getElementById(`emu-btn-${index}`);
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Stopping...';
        }

        try {
            await API.quitEmulator(index);
            Toast.info('Stopping', `Stopping emulator #${index}...`);
            NotificationManager.add('info', 'Emulator Stop', `Instance #${index} shutting down...`);
            setTimeout(() => this.refresh(), 2000);
        } catch (e) {
            Toast.error('Error', 'Failed to stop emulator');
            if (btn) btn.disabled = false;
        }
    },
};
