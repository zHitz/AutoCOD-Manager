/**
 * Settings Page — SAMPLE Settings-inspired with Switch toggles.
 */
const SettingsPage = {
    render() {
        return `
            <div class="page-enter">
                <div class="page-header">
                    <div class="page-header-info">
                        <h2>Settings</h2>
                        <p>Manage global application preferences and paths.</p>
                    </div>
                </div>

                <div class="settings-stack">

                    <!-- General -->
                    <div class="settings-card">
                        <div class="settings-card-header">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                            <h3>General</h3>
                        </div>
                        <div class="settings-card-body">
                            <div class="setting-row">
                                <div class="setting-info">
                                    <span class="form-label" style="margin-bottom:0">Auto-Refresh Devices</span>
                                    <p class="form-desc">Automatically poll for device status updates.</p>
                                </div>
                                <button class="switch" role="switch" aria-checked="true" onclick="this.setAttribute('aria-checked', this.getAttribute('aria-checked')==='true'?'false':'true')">
                                    <span class="switch-thumb"></span>
                                </button>
                            </div>
                            <div class="setting-row">
                                <div class="setting-info">
                                    <span class="form-label" style="margin-bottom:0">Debug Screenshots</span>
                                    <p class="form-desc">Save OCR screenshots for debugging.</p>
                                </div>
                                <button class="switch" role="switch" aria-checked="true" onclick="this.setAttribute('aria-checked', this.getAttribute('aria-checked')==='true'?'false':'true')" id="cfg-debug-switch">
                                    <span class="switch-thumb"></span>
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Paths -->
                    <div class="settings-card">
                        <div class="settings-card-header">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                            <h3>Paths</h3>
                        </div>
                        <div class="settings-card-body">
                            <div class="form-group" style="margin-bottom:16px">
                                <label class="form-label">ADB Executable</label>
                                <div style="display:flex;gap:8px">
                                    <input type="text" class="form-input" id="cfg-adb-path" readonly>
                                    <button class="btn btn-outline btn-icon"><svg style="width:16px;height:16px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg></button>
                                </div>
                            </div>
                            <div class="form-group" style="margin-bottom:16px">
                                <label class="form-label">Tesseract OCR Path</label>
                                <div style="display:flex;gap:8px">
                                    <input type="text" class="form-input" id="cfg-tesseract-path" readonly>
                                    <button class="btn btn-outline btn-icon"><svg style="width:16px;height:16px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg></button>
                                </div>
                            </div>
                            <div class="form-group" style="margin-bottom:0">
                                <label class="form-label">Working Directory</label>
                                <div style="display:flex;gap:8px">
                                    <input type="text" class="form-input" id="cfg-work-dir" readonly>
                                    <button class="btn btn-outline btn-icon"><svg style="width:16px;height:16px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg></button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Performance -->
                    <div class="settings-card">
                        <div class="settings-card-header">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                            <h3>Performance</h3>
                        </div>
                        <div class="settings-card-body">
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                                <div>
                                    <label class="form-label">Resolution</label>
                                    <select class="form-select" id="cfg-resolution">
                                        <option>960x540</option>
                                        <option>1280x720</option>
                                        <option>1920x1080</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="form-label">Coordinate Map</label>
                                    <select class="form-select" id="cfg-coord-map">
                                        <option>960x540_v1</option>
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label class="form-label">Server Port</label>
                                <input type="text" class="form-input" id="cfg-port" style="max-width:200px" readonly>
                            </div>
                        </div>
                    </div>

                    <!-- Account -->
                    <div class="settings-card">
                        <div class="settings-card-header">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                            <h3>About</h3>
                        </div>
                        <div class="settings-card-body">
                            <div style="display:flex;align-items:center;gap:16px">
                                <div style="width:48px;height:48px;border-radius:50%;background:var(--indigo-500);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:18px;flex-shrink:0">A</div>
                                <div>
                                    <h4 class="font-semibold">COD Game Automation Manager</h4>
                                    <p class="text-sm text-muted">v1.0.0 • pywebview + FastAPI + SQLite</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="display:flex;justify-content:flex-end;padding-top:8px">
                        <button class="btn btn-default btn-md" style="gap:8px">
                            <svg style="width:16px;height:16px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                            Save Changes
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    async init() { await this.loadConfig(); },
    destroy() { },

    async loadConfig() {
        try {
            const cfg = await API.getConfig();
            const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
            set('cfg-adb-path', cfg.adb_path);
            set('cfg-tesseract-path', cfg.tesseract_path);
            set('cfg-work-dir', cfg.work_dir);
            set('cfg-resolution', cfg.resolution);
            set('cfg-coord-map', cfg.coordinate_map);
            set('cfg-port', cfg.server_port);

            const debugSwitch = document.getElementById('cfg-debug-switch');
            if (debugSwitch) debugSwitch.setAttribute('aria-checked', cfg.debug_screenshots ? 'true' : 'false');
        } catch (e) {
            Toast.error('Error', 'Failed to load config');
        }
    },
};
