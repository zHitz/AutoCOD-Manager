/**
 * Dashboard Page — Gradient stat cards + device list + detail panel.
 * Inspired by SAMPLE EmulatorDashboard.
 */
const DashboardPage = {
    _pollInterval: null,

    render() {
        return `
            <div class="page-enter">
                <!-- Stats Row -->
                <div class="stats-row" id="stats-row">
                    <div class="card stat-card-indigo">
                        <div class="card-header-row">
                            <span class="card-title">Total Devices</span>
                            <span class="card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></span>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="stat-total">0</div>
                            <p class="card-subtitle">Connected emulators</p>
                        </div>
                    </div>
                    <div class="card stat-card-emerald">
                        <div class="card-header-row">
                            <span class="card-title">Online</span>
                            <span class="card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></span>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="stat-online">0</div>
                            <p class="card-subtitle">Ready for tasks</p>
                        </div>
                    </div>
                    <div class="card stat-card-orange">
                        <div class="card-header-row">
                            <span class="card-title">Busy</span>
                            <span class="card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></span>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="stat-busy">0</div>
                            <p class="card-subtitle">Running tasks</p>
                        </div>
                    </div>
                    <div class="card stat-card-red">
                        <div class="card-header-row">
                            <span class="card-title">Error</span>
                            <span class="card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></span>
                        </div>
                        <div class="card-content">
                            <div class="card-value" id="stat-error">0</div>
                            <p class="card-subtitle">Need attention</p>
                        </div>
                    </div>
                </div>

                <!-- Devices Section -->
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
                    <h2 class="tracking-tight" style="font-size:18px">Connected Emulators</h2>
                    <div style="display:flex;gap:8px">
                        <button class="btn btn-outline btn-sm" onclick="DashboardPage.refresh()">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Refresh
                        </button>
                        <button class="btn btn-default btn-sm" onclick="DashboardPage.scanAll()">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                            Scan All
                        </button>
                    </div>
                </div>

                <div class="grid-1" id="device-list">
                    <div class="empty-state">
                        <div class="empty-state-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></div>
                        <span class="font-medium">Loading devices...</span>
                        <span class="spinner"></span>
                    </div>
                </div>

                <!-- Detail Panel -->
                <div id="device-detail-area" style="margin-top:24px"></div>
            </div>
        `;
    },

    async init() {
        await this.refresh();
        this._pollInterval = setInterval(() => this.pollDevices(), 3000);
    },

    destroy() {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
            this._pollInterval = null;
        }
    },

    async refresh() {
        try {
            const result = await API.refreshDevices();
            this.renderDevices(result.devices || []);
            this.updateStats(result.devices || []);
        } catch (e) {
            Toast.error('Connection Error', 'Could not reach backend server');
        }
    },

    async pollDevices() {
        try {
            const devices = await API.getDevices();
            this.updateStats(devices);
            devices.forEach(d => DeviceCard.updateStatus(d.serial, d.status));
        } catch (e) { /* silent */ }
    },

    renderDevices(devices) {
        const list = document.getElementById('device-list');
        if (!list) return;

        if (!devices || devices.length === 0) {
            list.innerHTML = `
                <div class="card" style="border-style:dashed;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:48px;color:var(--muted-foreground)">
                    <svg style="width:48px;height:48px;opacity:0.5;margin-bottom:16px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                    <h3 style="font-size:18px;font-weight:500">No Active Emulators</h3>
                    <p class="text-sm">Start LDPlayer and click Refresh to detect devices.</p>
                </div>
            `;
            return;
        }

        list.innerHTML = '';
        devices.forEach(device => {
            list.appendChild(DeviceCard.create(device));
        });
    },

    updateStats(devices) {
        if (!devices) return;
        const c = { total: devices.length, online: 0, busy: 0, error: 0 };
        devices.forEach(d => {
            if (d.status === 'ONLINE') c.online++;
            else if (d.status === 'BUSY') c.busy++;
            else if (d.status === 'ERROR') c.error++;
        });
        const u = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        u('stat-total', c.total);
        u('stat-online', c.online);
        u('stat-busy', c.busy);
        u('stat-error', c.error);
    },

    showDeviceDetail(serial) {
        // Build a mock device object
        const device = { serial, status: 'ONLINE' };
        // Try to get current status from badge
        const badge = document.getElementById(`badge-${serial}`);
        if (badge) device.status = badge.textContent;
        DeviceCard.createDetail(device);
    },

    async scanDevice(serial, type) {
        try {
            DeviceCard.showProgress(serial, 'Starting...', 10);
            const result = await API.runTask(serial, type);
            if (result.status === 'accepted') {
                Toast.info('Task Queued', `${type} scan on ${serial}`);
            } else {
                Toast.error('Error', result.msg || 'Failed to queue task');
                DeviceCard.hideProgress(serial);
            }
        } catch (e) {
            Toast.error('Network Error', 'Could not reach server');
            DeviceCard.hideProgress(serial);
        }
    },

    async scanAll() {
        try {
            const result = await API.runAllTasks('profile');
            if (result.status === 'accepted') {
                Toast.success('Scan All', `Queued ${result.count} tasks`);
            }
        } catch (e) {
            Toast.error('Error', 'Failed to start scan all');
        }
    },
};
