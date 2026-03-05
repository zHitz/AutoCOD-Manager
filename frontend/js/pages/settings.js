/**
 * Settings Page — SAMPLE Settings-inspired with Switch toggles.
 */
const SettingsPage = {
    _taskActivityRegistry: [],
    _taskActivitySelectionKey: 'task_selected_activities_v1',
    _taskActivityRegistryKey: 'task_activity_registry_v1',

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

                    <!-- OCR API -->
                    <div class="settings-card">
                        <div class="settings-card-header" style="display:flex;align-items:center;justify-content:space-between;gap:12px">
                            <div style="display:flex;align-items:center;gap:10px">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M12 4h9"/><path d="M4 9h16"/><path d="M4 15h16"/><path d="M4 4h.01"/><path d="M4 20h.01"/></svg>
                                <h3>OCR API Keys</h3>
                            </div>
                            <button class="btn btn-outline btn-sm" id="cfg-ocr-edit-btn" type="button">Edit</button>
                        </div>
                        <div class="settings-card-body">
                            <div id="cfg-ocr-preview" class="form-desc" style="margin-bottom:0">No API keys configured.</div>
                            <div class="form-group" id="cfg-ocr-editor" style="display:none;margin-top:12px;margin-bottom:0">
                                <label class="form-label" for="cfg-ocr-keys">API keys (one key per line)</label>
                                <textarea id="cfg-ocr-keys" class="form-input" style="min-height:120px;resize:vertical;font-family:monospace" placeholder="ocr_key_1
ocr_key_2"></textarea>
                                <p class="form-desc">Lines that start with <code>#</code> are treated as comments.</p>
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
                            <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px">
                                <div style="width:48px;height:48px;border-radius:50%;background:var(--indigo-500);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:18px;flex-shrink:0">A</div>
                                <div>
                                    <h4 class="font-semibold">COD Game Automation Manager</h4>
                                    <p class="text-sm text-muted">v1.0.0 • pywebview + FastAPI + SQLite</p>
                                </div>
                            </div>
                            <div class="setting-row" style="padding:0;border:none">
                                <div class="setting-info">
                                    <span class="form-label" style="margin-bottom:0">Release Notes</span>
                                    <p class="form-desc">Track the latest changes in this build.</p>
                                </div>
                                <button class="btn btn-outline btn-sm" id="cfg-release-notes-btn" type="button">View</button>
                            </div>
                            <div id="cfg-release-notes-panel" style="display:none;margin-top:12px;padding:12px;border:1px solid var(--gray-200);border-radius:10px;background:var(--gray-50)">
                                <p class="form-desc" style="margin-bottom:8px"><strong>v1.0.0</strong></p>
                                <ul class="form-desc" style="margin:0;padding-left:18px;display:grid;gap:4px">
                                    <li>Initial dashboard and task management workflow.</li>
                                    <li>Added OCR API key management in Settings.</li>
                                    <li>Improved Settings UX with secured OCR key editor toggle.</li>
                                </ul>
                            </div>
                        </div>
                    </div>


                    <!-- Task Activities -->
                    <div class="settings-card">
                        <div class="settings-card-header">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                            <h3>Task Activities</h3>
                        </div>
                        <div class="settings-card-body">
                            <p class="form-desc" style="margin-bottom:10px">Select workflow activities that should appear as tasks on the Task page.</p>
                            <div id="cfg-task-activities-list" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px"></div>
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;gap:10px;flex-wrap:wrap">
                                <p class="form-desc" id="cfg-task-activities-summary" style="margin:0">0 activities selected</p>
                                <button class="btn btn-outline btn-sm" id="cfg-task-activities-apply">Apply to Task Page</button>
                            </div>
                        </div>
                    </div>

                    <div style="display:flex;justify-content:flex-end;padding-top:8px">
                        <button class="btn btn-default btn-md" style="gap:8px" id="cfg-save-btn">
                            <svg style="width:16px;height:16px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                            Save Changes
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    async init() {
        const saveBtn = document.getElementById('cfg-save-btn');
        if (saveBtn) saveBtn.addEventListener('click', () => this.saveConfig());

        const editBtn = document.getElementById('cfg-ocr-edit-btn');
        if (editBtn) editBtn.addEventListener('click', () => this.toggleOcrEditor());

        const releaseNotesBtn = document.getElementById('cfg-release-notes-btn');
        if (releaseNotesBtn) releaseNotesBtn.addEventListener('click', () => this.toggleReleaseNotes());

        const applyActivitiesBtn = document.getElementById('cfg-task-activities-apply');
        if (applyActivitiesBtn) applyActivitiesBtn.addEventListener('click', () => this.saveTaskActivitiesSelection());

        await this.loadConfig();
        await this.loadOcrKeys();
        await this.loadTaskActivitiesSettings();
        this.setOcrEditorVisible(false);
    },
    destroy() { },

    setOcrEditorVisible(isVisible) {
        const editor = document.getElementById('cfg-ocr-editor');
        const editBtn = document.getElementById('cfg-ocr-edit-btn');
        if (editor) editor.style.display = isVisible ? 'block' : 'none';
        if (editBtn) editBtn.textContent = isVisible ? 'Close' : 'Edit';
    },

    toggleOcrEditor() {
        const editor = document.getElementById('cfg-ocr-editor');
        if (!editor) return;
        const isVisible = editor.style.display !== 'none';
        this.setOcrEditorVisible(!isVisible);
    },

    toggleReleaseNotes() {
        const panel = document.getElementById('cfg-release-notes-panel');
        const btn = document.getElementById('cfg-release-notes-btn');
        if (!panel || !btn) return;

        const isVisible = panel.style.display !== 'none';
        panel.style.display = isVisible ? 'none' : 'block';
        btn.textContent = isVisible ? 'View' : 'Hide';
    },

    updateOcrPreview(keysText) {
        const preview = document.getElementById('cfg-ocr-preview');
        if (!preview) return;

        const lines = (keysText || '')
            .split('\n')
            .map(line => line.trim())
            .filter(line => line && !line.startsWith('#'));

        if (!lines.length) {
            preview.textContent = 'No API keys configured.';
            return;
        }

        preview.textContent = `${lines.length} API key(s) configured.`;
    },

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

    async loadOcrKeys() {
        try {
            const data = await API.getOcrKeys();
            const keysValue = data.keys || '';
            const ocrKeys = document.getElementById('cfg-ocr-keys');
            if (ocrKeys) ocrKeys.value = keysValue;
            this.updateOcrPreview(keysValue);
        } catch (e) {
            Toast.error('Error', 'Failed to load OCR API keys');
        }
    },

    async saveConfig() {
        try {
            const ocrKeys = document.getElementById('cfg-ocr-keys');
            const keysValue = ocrKeys ? ocrKeys.value : '';
            await API.saveOcrKeys(keysValue);
            this.updateOcrPreview(keysValue);
            this.setOcrEditorVisible(false);
            Toast.success('Saved', 'OCR API keys updated');
        } catch (e) {
            Toast.error('Error', e.message || 'Failed to save settings');
        }
    },

    _getSelectedTaskActivityIds() {
        try {
            const raw = localStorage.getItem(this._taskActivitySelectionKey);
            const parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
        } catch (_) {
            return [];
        }
    },

    _updateTaskActivitiesSummary(selectedCount) {
        const summary = document.getElementById('cfg-task-activities-summary');
        if (!summary) return;
        summary.textContent = `${selectedCount} activit${selectedCount === 1 ? 'y' : 'ies'} selected`;
    },

    async loadTaskActivitiesSettings() {
        const listEl = document.getElementById('cfg-task-activities-list');
        if (!listEl) return;

        let activities = [];
        try {
            const res = await fetch('/api/workflow/activity-registry');
            if (res.ok) {
                const payload = await res.json();
                activities = Array.isArray(payload?.data) ? payload.data : [];
            }
        } catch (_) {}

        if (!activities.length) {
            activities = [
                { id: 'login', name: 'Daily login' },
                { id: 'collect', name: 'Collect resources' },
                { id: 'alliance', name: 'Alliance donation' },
                { id: 'patrol', name: 'Patrol / Daily missions' },
                { id: 'shop', name: 'Refresh shop' },
                { id: 'event', name: 'Claim event rewards' },
                { id: 'full_scan', name: 'Full Scan' },
            ];
        }

        this._taskActivityRegistry = activities.map((item) => ({ id: String(item.id), name: item.name || item.id }));
        localStorage.setItem(this._taskActivityRegistryKey, JSON.stringify(this._taskActivityRegistry));

        const selected = new Set(this._getSelectedTaskActivityIds());
        listEl.innerHTML = this._taskActivityRegistry.map((item) => `
            <label class="setting-row" style="margin:0;padding:8px 10px;border:1px solid var(--border);border-radius:10px;cursor:pointer">
                <div class="setting-info" style="display:flex;align-items:center;gap:8px">
                    <input type="checkbox" class="cfg-task-activity-checkbox" value="${item.id}" ${selected.has(item.id) ? 'checked' : ''}/>
                    <span class="form-label" style="margin:0;text-transform:none;letter-spacing:0">${item.name}</span>
                </div>
            </label>
        `).join('');

        listEl.querySelectorAll('.cfg-task-activity-checkbox').forEach((el) => {
            el.addEventListener('change', () => {
                const count = listEl.querySelectorAll('.cfg-task-activity-checkbox:checked').length;
                this._updateTaskActivitiesSummary(count);
            });
        });

        this._updateTaskActivitiesSummary(selected.size);
    },

    saveTaskActivitiesSelection() {
        const selectedIds = Array.from(document.querySelectorAll('.cfg-task-activity-checkbox:checked'))
            .map((el) => el.value)
            .filter(Boolean);

        localStorage.setItem(this._taskActivitySelectionKey, JSON.stringify(selectedIds));
        this._updateTaskActivitiesSummary(selectedIds.length);
        Toast.success('Saved', 'Task activities updated. Open Task page to see the new checklist.');
    },


};
