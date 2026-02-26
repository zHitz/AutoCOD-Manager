/**
 * Device Card Component — List-row style (SAMPLE-inspired)
 */
const DeviceCard = {
    formatNum(val) {
        if (typeof val !== 'number') return val || '--';
        if (val >= 1_000_000_000) return (val / 1_000_000_000).toFixed(1) + 'B';
        if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M';
        if (val >= 1_000) return (val / 1_000).toFixed(1) + 'K';
        return val.toString();
    },

    /**
     * Create a device card element (list row style).
     */
    create(device) {
        const div = document.createElement('div');
        div.className = 'device-card';
        div.id = `card-${device.serial}`;
        div.setAttribute('data-serial', device.serial);

        const statusClass = `badge-${device.status.toLowerCase()}`;
        const initials = device.serial.replace('emulator-', 'E').substring(0, 4).toUpperCase();

        div.innerHTML = `
            <div class="device-icon-box">${initials}</div>
            <div class="device-info">
                <div class="device-name-row">
                    <span class="device-name">${device.serial}</span>
                    <span class="badge ${statusClass}" id="badge-${device.serial}">${device.status}</span>
                </div>
                <span class="device-meta">
                    <span id="meta-name-${device.serial}">Name: --</span> •
                    <span id="meta-power-${device.serial}">Power: --</span>
                </span>
            </div>
            <div class="device-actions" id="actions-${device.serial}">
                <button class="btn btn-outline btn-sm" onclick="DashboardPage.scanDevice('${device.serial}', 'profile')">Scan</button>
                <button class="btn btn-default btn-sm" style="width:88px;gap:4px" onclick="DashboardPage.showDeviceDetail('${device.serial}')">
                    <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    Details
                </button>
            </div>

            <!-- Hidden progress section -->
            <div id="task-progress-${device.serial}" style="display:none;width:100%;margin-top:8px;padding-left:64px">
                <div class="progress-text">
                    <span class="spinner"></span>
                    <span id="progress-label-${device.serial}">Processing...</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-bar-fill" id="progress-fill-${device.serial}" style="width:0%"></div>
                </div>
            </div>
        `;

        return div;
    },

    /**
     * Create expanded detail view for a device.
     */
    createDetail(device) {
        const containerEl = document.getElementById('device-detail-area');
        if (!containerEl) return;

        containerEl.innerHTML = `
            <div class="data-card" style="animation: fadeSlideUp 200ms ease-out">
                <div class="data-card-header">
                    <svg style="width:16px;height:16px;color:var(--primary)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                    <h3>${device.serial}</h3>
                    <span class="badge badge-${device.status.toLowerCase()}" style="margin-left:auto">${device.status}</span>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                    <div>
                        <div style="font-size:11px;color:var(--muted-foreground);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;font-weight:600">Profile</div>
                        <div class="data-row">
                            <span class="data-label">Name</span>
                            <span class="data-value" id="det-name-${device.serial}">--</span>
                        </div>
                        <div class="data-row">
                            <span class="data-label">Power</span>
                            <span class="data-value" id="det-power-${device.serial}">--</span>
                        </div>
                        <div class="data-row">
                            <span class="data-label">Hall Level</span>
                            <span class="data-value" id="det-hall-${device.serial}">--</span>
                        </div>
                        <div class="data-row">
                            <span class="data-label">Market Level</span>
                            <span class="data-value" id="det-market-${device.serial}">--</span>
                        </div>
                        <div class="data-row">
                            <span class="data-label">Pet Token</span>
                            <span class="data-value" id="det-pet-${device.serial}">--</span>
                        </div>
                    </div>
                    <div>
                        <div style="font-size:11px;color:var(--muted-foreground);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;font-weight:600">Resources</div>
                        <table class="res-table">
                            <tr><th>Type</th><th style="text-align:right">Bag</th><th style="text-align:right">Total</th></tr>
                            <tr><td>Gold</td><td class="num" id="det-gold-bag-${device.serial}">--</td><td class="num" id="det-gold-total-${device.serial}">--</td></tr>
                            <tr><td>Wood</td><td class="num" id="det-wood-bag-${device.serial}">--</td><td class="num" id="det-wood-total-${device.serial}">--</td></tr>
                            <tr><td>Ore</td><td class="num" id="det-ore-bag-${device.serial}">--</td><td class="num" id="det-ore-total-${device.serial}">--</td></tr>
                            <tr><td>Mana</td><td class="num" id="det-mana-bag-${device.serial}">--</td><td class="num" id="det-mana-total-${device.serial}">--</td></tr>
                        </table>
                    </div>
                </div>

                <div style="display:flex;gap:8px;margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
                    <button class="btn btn-outline btn-sm" onclick="DashboardPage.scanDevice('${device.serial}','profile')">👤 Profile</button>
                    <button class="btn btn-outline btn-sm" onclick="DashboardPage.scanDevice('${device.serial}','resources')">🎒 Resources</button>
                    <button class="btn btn-outline btn-sm" onclick="DashboardPage.scanDevice('${device.serial}','hall')">🏰 Hall</button>
                    <button class="btn btn-outline btn-sm" onclick="DashboardPage.scanDevice('${device.serial}','pet')">🐾 Pet</button>
                    <button class="btn btn-outline btn-sm" onclick="DashboardPage.scanDevice('${device.serial}','full_scan')">🔄 Full Scan</button>
                </div>
            </div>
        `;
    },

    updateStatus(serial, status) {
        const badge = document.getElementById(`badge-${serial}`);
        if (!badge) return;
        badge.className = `badge badge-${status.toLowerCase()}`;
        badge.textContent = status;
    },

    showProgress(serial, step, percent) {
        const section = document.getElementById(`task-progress-${serial}`);
        const label = document.getElementById(`progress-label-${serial}`);
        const fill = document.getElementById(`progress-fill-${serial}`);
        const card = document.getElementById(`card-${serial}`);

        if (section) section.style.display = 'block';
        if (label) label.textContent = step;
        if (fill) fill.style.width = `${percent}%`;
        if (card) card.style.flexWrap = 'wrap';
    },

    hideProgress(serial) {
        const section = document.getElementById(`task-progress-${serial}`);
        const card = document.getElementById(`card-${serial}`);
        if (section) section.style.display = 'none';
        if (card) card.style.flexWrap = '';
    },

    updateData(serial, taskType, data) {
        if (!data) return;

        if (taskType === 'profile') {
            const nameEl = document.getElementById(`meta-name-${serial}`);
            const powerEl = document.getElementById(`meta-power-${serial}`);
            if (nameEl) nameEl.textContent = `Name: ${data.name || '--'}`;
            if (powerEl) powerEl.textContent = `Power: ${this.formatNum(data.power)}`;
            // Also update detail view if open
            const detName = document.getElementById(`det-name-${serial}`);
            const detPower = document.getElementById(`det-power-${serial}`);
            if (detName) detName.textContent = data.name || '--';
            if (detPower) detPower.textContent = this.formatNum(data.power) || '--';
        }

        if (taskType === 'resources') {
            for (const res of ['gold', 'wood', 'ore', 'mana']) {
                if (data[res]) {
                    const bag = document.getElementById(`det-${res}-bag-${serial}`);
                    const total = document.getElementById(`det-${res}-total-${serial}`);
                    if (bag) bag.textContent = this.formatNum(data[res].bag);
                    if (total) total.textContent = this.formatNum(data[res].total);
                }
            }
        }

        if ((taskType === 'hall' || taskType === 'building') && data.level !== undefined) {
            const el = document.getElementById(`det-hall-${serial}`);
            if (el) el.textContent = data.level || '--';
        }

        if (taskType === 'pet' && data.token !== undefined) {
            const el = document.getElementById(`det-pet-${serial}`);
            if (el) el.textContent = data.token || '--';
        }
    },
};
