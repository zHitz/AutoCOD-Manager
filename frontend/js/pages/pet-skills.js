const PetSkillsPage = {
    _data: null,
    _accounts: [],
    _releases: [],
    _selectedAccountId: '',
    _selectedReleaseId: '',
    _activeTab: 'analytics',
    _skillTemplates: [],
    _loading: false,

    render() {
        return `
            <div class="report-shell pet-skill-shell page-enter">
                <section class="panel hero">
                    <div class="hero-head">
                        <div>
                            <h2 class="hero-title">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l2.2 4.5 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5-3.6-3.5 5-.7L12 3z"/><path d="M5 21h14"/></svg>
                                Pet Skill Command Center
                            </h2>
                            <p class="hero-subtitle">Inspect pet release outcomes by account, compare before and after captures, and audit the analyzer result without opening raw files.</p>
                        </div>
                        <div class="button-row">
                            <button class="btn" type="button" onclick="PetSkillsPage.load()">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Refresh
                            </button>
                            <button class="btn" id="pet-skill-run-btn" type="button" onclick="PetSkillsPage.runAnalysis()">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                            Analyze
                            </button>
                        </div>
                    </div>

                    <div class="toolbar-grid">
                        <div class="field span-5">
                            <div class="field-label">Account</div>
                            <select id="pet-skill-account-select" class="select" onchange="PetSkillsPage.selectAccount(this.value)"></select>
                        </div>
                        <div class="field span-4">
                            <div class="field-label">Data Source</div>
                            <div class="pet-source-chip" id="pet-skill-data-file">Waiting for data</div>
                        </div>
                        <div class="field span-3">
                            <div class="field-label">Current Selection</div>
                            <div class="pet-source-chip" id="pet-skill-selection-chip">No account selected</div>
                        </div>
                    </div>
                </section>

                <div class="pet-skill-tabs" role="tablist">
                    <button class="pet-skill-tab ${this._activeTab === 'analytics' ? 'active' : ''}" type="button" onclick="PetSkillsPage.switchTab('analytics')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/></svg>
                        Release Analytics
                    </button>
                    <button class="pet-skill-tab ${this._activeTab === 'database' ? 'active' : ''}" type="button" onclick="PetSkillsPage.switchTab('database')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/></svg>
                        Skill Database
                    </button>
                </div>

                <div id="pet-skill-analytics-tab" class="${this._activeTab === 'analytics' ? '' : 'hidden'}">
                    <section class="summary-grid" id="pet-skill-stats">
                        ${this._statSkeleton('Releases')}
                        ${this._statSkeleton('Image Pairs')}
                        ${this._statSkeleton('Accounts')}
                        ${this._statSkeleton('Top Slot')}
                        ${this._statSkeleton('Pool Health')}
                    </section>

                    <section class="panel">
                        <div class="panel-header">
                            <div class="panel-heading">
                                <div class="panel-title">Drop Distribution</div>
                                <div class="panel-subtitle">Slot frequency across the analyzed release set. This helps spot capture bias or bad ROI alignment.</div>
                            </div>
                            <div class="legend" id="pet-skill-distribution-meta"></div>
                        </div>
                        <div class="pet-distribution-grid" id="pet-skill-distribution"></div>
                    </section>

                    <section class="insight-grid pet-skill-workspace">
                        <section class="panel">
                            <div class="panel-header">
                                <div class="panel-heading">
                                    <div class="panel-title">Release Results</div>
                                    <div class="panel-subtitle" id="pet-skill-release-count">0 result(s)</div>
                                </div>
                            </div>
                            <div class="pet-release-feed" id="pet-skill-release-list"></div>
                        </section>

                        <section class="panel pet-detail-panel">
                            <div class="panel-header">
                                <div class="panel-heading">
                                    <div class="panel-title">Release Drilldown</div>
                                    <div class="panel-subtitle" id="pet-skill-detail-id">Select a result</div>
                                </div>
                            </div>
                            <div id="pet-skill-detail"></div>
                        </section>
                    </section>
                </div>

                <section id="pet-skill-database-tab" class="${this._activeTab === 'database' ? '' : 'hidden'}">
                    <section class="panel pet-db-panel">
                        <div class="panel-header">
                            <div class="panel-heading">
                                <div class="panel-title">Skill Template Database</div>
                                <div class="panel-subtitle">Mock database for template image, skill name, and buy/sell prices by 0-3 stars.</div>
                            </div>
                            <button class="btn" type="button" onclick="PetSkillsPage.openSkillEditor()">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
                                Add Skill
                            </button>
                        </div>
                        <div class="pet-db-grid" id="pet-skill-db-grid"></div>
                    </section>
                    <div id="pet-skill-editor-host"></div>
                </section>
            </div>
        `;
    },

    async init() {
        this.loadSkillTemplates();
        await this.load();
        this.paintSkillDatabase();
    },

    destroy() {},

    switchTab(tab) {
        this._activeTab = tab === 'database' ? 'database' : 'analytics';
        const analytics = document.getElementById('pet-skill-analytics-tab');
        const database = document.getElementById('pet-skill-database-tab');
        if (analytics) analytics.classList.toggle('hidden', this._activeTab !== 'analytics');
        if (database) database.classList.toggle('hidden', this._activeTab !== 'database');
        document.querySelectorAll('.pet-skill-tab').forEach(btn => {
            btn.classList.toggle('active', btn.textContent.includes(this._activeTab === 'database' ? 'Database' : 'Analytics'));
        });
        if (this._activeTab === 'database') this.paintSkillDatabase();
    },

    loadSkillTemplates() {
        const stored = localStorage.getItem('pet_skill_templates_mock');
        if (stored) {
            try {
                this._skillTemplates = JSON.parse(stored);
                return;
            } catch (error) {
                console.warn('Failed to parse pet skill template mock data', error);
            }
        }
        this._skillTemplates = [
            {
                id: 'skill_gold_paw',
                name: 'Gold Paw',
                image: '',
                note: 'Template placeholder',
                prices: {
                    0: { buy: 0, sell: 0 },
                    1: { buy: 1200, sell: 850 },
                    2: { buy: 4800, sell: 3600 },
                    3: { buy: 16000, sell: 12500 },
                },
            },
            {
                id: 'skill_green_leaf',
                name: 'Green Leaf',
                image: '',
                note: 'Waiting for template crop',
                prices: {
                    0: { buy: 0, sell: 0 },
                    1: { buy: 900, sell: 650 },
                    2: { buy: 3900, sell: 2800 },
                    3: { buy: 13000, sell: 10000 },
                },
            },
        ];
        this.saveSkillTemplates();
    },

    saveSkillTemplates() {
        localStorage.setItem('pet_skill_templates_mock', JSON.stringify(this._skillTemplates));
    },

    paintSkillDatabase() {
        const host = document.getElementById('pet-skill-db-grid');
        if (!host) return;
        if (!this._skillTemplates.length) {
            host.innerHTML = '<div class="pet-empty-state">No skill templates yet.</div>';
            return;
        }
        host.innerHTML = this._skillTemplates.map(skill => `
            <article class="pet-db-card">
                <div class="pet-db-card-top">
                    <div class="pet-template-preview">
                        ${skill.image ? `<img src="${this._esc(skill.image)}" alt="${this._esc(skill.name)}">` : `<span>${this._esc((skill.name || skill.id || '?').slice(0, 2).toUpperCase())}</span>`}
                    </div>
                    <div class="pet-db-main">
                        <div class="pet-db-name">${this._esc(skill.name || 'Unnamed Skill')}</div>
                        <div class="pet-db-id">${this._esc(skill.id || 'new_skill')}</div>
                        <div class="pet-db-note">${this._esc(skill.note || 'No note')}</div>
                    </div>
                    <button class="pet-edit-btn" type="button" onclick="PetSkillsPage.openSkillEditor('${this._escJs(skill.id)}')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>
                        Edit
                    </button>
                </div>
                <div class="pet-price-grid">
                    ${[0, 1, 2, 3].map(star => this._priceCell(star, skill.prices?.[star])).join('')}
                </div>
            </article>
        `).join('');
    },

    _priceCell(star, price = {}) {
        return `
            <div class="pet-price-cell">
                <div class="pet-price-star">${star} star</div>
                <div><span>Buy</span><strong>${this._fmt(price.buy || 0)}</strong></div>
                <div><span>Sell</span><strong>${this._fmt(price.sell || 0)}</strong></div>
            </div>
        `;
    },

    openSkillEditor(skillId = '') {
        const existing = this._skillTemplates.find(skill => skill.id === skillId);
        const skill = existing || {
            id: `skill_${Date.now()}`,
            name: '',
            image: '',
            note: '',
            prices: {
                0: { buy: 0, sell: 0 },
                1: { buy: 0, sell: 0 },
                2: { buy: 0, sell: 0 },
                3: { buy: 0, sell: 0 },
            },
        };
        const host = document.getElementById('pet-skill-editor-host');
        if (!host) return;
        host.innerHTML = `
            <div class="pet-db-modal-backdrop">
                <div class="pet-db-modal">
                    <div class="pet-db-modal-head">
                        <div>
                            <div class="edit-modal-kicker">Skill Database</div>
                            <h3>${existing ? 'Edit Skill Template' : 'Add Skill Template'}</h3>
                        </div>
                        <button class="pet-icon-btn" type="button" onclick="PetSkillsPage.closeSkillEditor()">x</button>
                    </div>
                    <div class="pet-db-modal-body">
                        <label class="field">
                            <div class="field-label">Skill ID</div>
                            <input class="input" id="pet-edit-skill-id" value="${this._esc(skill.id)}" ${existing ? 'readonly' : ''}>
                        </label>
                        <label class="field">
                            <div class="field-label">Skill Name</div>
                            <input class="input" id="pet-edit-skill-name" value="${this._esc(skill.name || '')}" placeholder="Gold Paw">
                        </label>
                        <label class="field">
                            <div class="field-label">Template Image URL / Path</div>
                            <input class="input" id="pet-edit-skill-image" value="${this._esc(skill.image || '')}" placeholder="/pet_skill_templates/skill_gold_paw.png">
                        </label>
                        <label class="field">
                            <div class="field-label">Note</div>
                            <input class="input" id="pet-edit-skill-note" value="${this._esc(skill.note || '')}" placeholder="Template source, crop note, market note...">
                        </label>
                        <div class="pet-edit-price-grid">
                            ${[0, 1, 2, 3].map(star => this._priceEditor(star, skill.prices?.[star])).join('')}
                        </div>
                    </div>
                    <div class="pet-db-modal-footer">
                        ${existing ? `<button class="btn btn-destructive" type="button" onclick="PetSkillsPage.deleteSkillTemplate('${this._escJs(skill.id)}')">Delete</button>` : ''}
                        <button class="btn" type="button" onclick="PetSkillsPage.closeSkillEditor()">Cancel</button>
                        <button class="btn primary" type="button" onclick="PetSkillsPage.saveSkillEditor('${this._escJs(skill.id)}')">Save</button>
                    </div>
                </div>
            </div>
        `;
    },

    _priceEditor(star, price = {}) {
        return `
            <div class="pet-edit-price-card">
                <div>${star} star</div>
                <label>
                    <span>Buy</span>
                    <input class="input" id="pet-price-${star}-buy" type="number" min="0" value="${Number(price.buy || 0)}">
                </label>
                <label>
                    <span>Sell</span>
                    <input class="input" id="pet-price-${star}-sell" type="number" min="0" value="${Number(price.sell || 0)}">
                </label>
            </div>
        `;
    },

    saveSkillEditor(originalId) {
        const id = document.getElementById('pet-edit-skill-id')?.value?.trim();
        if (!id) {
            Toast.error('Skill Database', 'Skill ID is required');
            return;
        }
        const skill = {
            id,
            name: document.getElementById('pet-edit-skill-name')?.value?.trim() || id,
            image: document.getElementById('pet-edit-skill-image')?.value?.trim() || '',
            note: document.getElementById('pet-edit-skill-note')?.value?.trim() || '',
            prices: {},
        };
        [0, 1, 2, 3].forEach(star => {
            skill.prices[star] = {
                buy: Number(document.getElementById(`pet-price-${star}-buy`)?.value || 0),
                sell: Number(document.getElementById(`pet-price-${star}-sell`)?.value || 0),
            };
        });
        const index = this._skillTemplates.findIndex(item => item.id === originalId);
        if (index >= 0) this._skillTemplates[index] = skill;
        else this._skillTemplates.push(skill);
        this.saveSkillTemplates();
        this.closeSkillEditor();
        this.paintSkillDatabase();
        Toast.success('Skill Database', 'Saved template data');
    },

    deleteSkillTemplate(skillId) {
        this._skillTemplates = this._skillTemplates.filter(skill => skill.id !== skillId);
        this.saveSkillTemplates();
        this.closeSkillEditor();
        this.paintSkillDatabase();
        Toast.success('Skill Database', 'Deleted template data');
    },

    closeSkillEditor() {
        const host = document.getElementById('pet-skill-editor-host');
        if (host) host.innerHTML = '';
    },

    async load() {
        try {
            this._data = await API.getPetSkillSummary();
            this._accounts = this._data.accounts || [];
            if (!this._selectedAccountId && this._accounts.length) {
                this._selectedAccountId = String(this._accounts[0].account_id);
            }
            this.paintShell();
            await this.loadReleases();
        } catch (error) {
            Toast.error('Pet Skills', error.message || 'Failed to load pet skill analytics');
            this.showReleaseEmpty(error.message || 'Failed to load');
        }
    },

    async runAnalysis() {
        if (this._loading) return;
        this._loading = true;
        const btn = document.getElementById('pet-skill-run-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Analyzing';
        }
        try {
            this._data = await API.analyzePetSkills();
            this._accounts = this._data.accounts || [];
            if (!this._selectedAccountId && this._accounts.length) {
                this._selectedAccountId = String(this._accounts[0].account_id);
            }
            Toast.success('Analysis Complete', `${this._data.total_releases || 0} releases indexed`);
            this.paintShell();
            await this.loadReleases();
        } catch (error) {
            Toast.error('Analysis Failed', error.message || 'Could not run analyzer');
        } finally {
            this._loading = false;
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> Analyze';
            }
        }
    },

    async selectAccount(accountId) {
        this._selectedAccountId = accountId;
        this._selectedReleaseId = '';
        await this.loadReleases();
    },

    async loadReleases() {
        const list = document.getElementById('pet-skill-release-list');
        if (list) list.innerHTML = '<div class="text-sm text-muted" style="padding:12px">Loading releases...</div>';
        try {
            const result = await API.getPetSkillReleases(this._selectedAccountId, 500);
            this._releases = result.items || [];
            if (!this._selectedReleaseId && this._releases.length) {
                this._selectedReleaseId = this._releases[0].release_id;
            }
            this.paintReleases();
            if (this._selectedReleaseId) await this.showDetail(this._selectedReleaseId);
            else this.paintDetail(null);
        } catch (error) {
            Toast.error('Pet Releases', error.message || 'Failed to load releases');
            this.showReleaseEmpty(error.message || 'Failed to load releases');
        }
    },

    async showDetail(releaseId) {
        this._selectedReleaseId = releaseId;
        this.paintReleases();
        const item = this._releases.find(row => row.release_id === releaseId);
        this.paintDetail(item || null, item ? '' : 'Release detail not found in current list');
    },

    paintShell() {
        const data = this._data || {};
        const fileCounts = data.file_counts || {};
        const topSlot = this._topEntry(data.by_slot || {});
        const poolHealth = this._poolHealth(data.by_pool_size || {});
        const stats = document.getElementById('pet-skill-stats');
        if (stats) {
            stats.innerHTML = `
                ${this._statCard('Releases', this._fmt(data.total_releases), 'Analyzed release pairs')}
                ${this._statCard('Image Pairs', this._fmt(fileCounts.pairs), `${this._fmt(fileCounts.available)} available / ${this._fmt(fileCounts.get)} obtained`)}
                ${this._statCard('Accounts', this._fmt((data.accounts || []).length), 'Resolved from catch_pet logs')}
                ${this._statCard('Top Slot', topSlot ? `#${topSlot[0]}` : '-', topSlot ? `${this._pct(topSlot[1], data.total_releases)} of drops` : 'No analyzed rows')}
                ${this._statCard('Pool Health', poolHealth.value, poolHealth.note)}
            `;
        }

        const select = document.getElementById('pet-skill-account-select');
        if (select) {
            if (!this._accounts.length) {
                select.innerHTML = '<option value="">No analyzed accounts</option>';
            } else {
                select.innerHTML = this._accounts.map(acc => `
                    <option value="${this._esc(acc.account_id)}" ${String(acc.account_id) === String(this._selectedAccountId) ? 'selected' : ''}>
                        ${this._esc(acc.name || acc.game_id || acc.account_id)}${acc.game_id ? ` - ${this._esc(acc.game_id)}` : ''} (${this._fmt(acc.release_count)})
                    </option>
                `).join('');
            }
        }

        const fileEl = document.getElementById('pet-skill-data-file');
        if (fileEl) fileEl.textContent = data.data_file ? data.data_file.split(/[\\/]/).slice(-2).join('/') : 'No skill_data.json';

        const selected = this._accounts.find(acc => String(acc.account_id) === String(this._selectedAccountId));
        const chip = document.getElementById('pet-skill-selection-chip');
        if (chip) chip.textContent = selected ? `${selected.name || selected.game_id} - ${this._fmt(selected.release_count)} result(s)` : 'No account selected';

        this.paintDistribution();
    },

    paintReleases() {
        const count = document.getElementById('pet-skill-release-count');
        if (count) count.textContent = `${this._fmt(this._releases.length)} result(s)`;
        const list = document.getElementById('pet-skill-release-list');
        if (!list) return;
        if (!this._releases.length) {
            list.innerHTML = '<div class="pet-empty-state">No releases for this account.</div>';
            return;
        }
        list.innerHTML = this._releases.map(item => {
            const active = item.release_id === this._selectedReleaseId;
            return `
                <div class="pet-release-item ${active ? 'active' : ''}" role="button" tabindex="0"
                    onclick="PetSkillsPage.showDetail('${this._escJs(item.release_id)}')"
                    onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();PetSkillsPage.showDetail('${this._escJs(item.release_id)}')}">
                    <span class="pet-release-main">
                        <span class="pet-release-time">${this._esc(item.datetime || item.release_id)}</span>
                        <span class="pet-release-id">${this._esc(item.release_id)}</span>
                    </span>
                    <span class="pet-release-badges">
                        <span class="pet-slot-badge">Slot #${this._esc(item.get_slot_position || '-')}</span>
                        <span class="pet-pool-badge">${this._fmt(item.pool_filled_count)}/${this._fmt(item.pool_total_slots)}</span>
                    </span>
                    <span class="pet-release-actions">
                        <button class="pet-delete-btn" type="button" title="Delete release" aria-label="Delete release"
                            onclick="PetSkillsPage.deleteRelease('${this._escJs(item.release_id)}', event)">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                        </button>
                    </span>
                </div>
            `;
        }).join('');
    },

    async deleteRelease(releaseId, event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        const ok = typeof ConfirmModal !== 'undefined'
            ? await ConfirmModal.show({
                title: 'Delete Release',
                message: 'This will permanently delete the analyzed row and both release images.',
                icon: 'danger',
                confirmText: 'Delete',
                cancelText: 'Cancel',
                variant: 'danger',
            })
            : window.confirm('Delete this release permanently?');
        if (!ok) return;

        try {
            await API.deletePetSkillRelease(releaseId);
            Toast.success('Release Deleted', releaseId);
            if (this._selectedReleaseId === releaseId) this._selectedReleaseId = '';
            await this.load();
        } catch (error) {
            Toast.error('Delete Failed', error.message || 'Could not delete release');
        }
    },

    paintDetail(item, error) {
        const idEl = document.getElementById('pet-skill-detail-id');
        if (idEl) idEl.textContent = item?.release_id || '';
        const host = document.getElementById('pet-skill-detail');
        if (!host) return;
        if (error) {
            host.innerHTML = `<div class="text-sm" style="color:var(--destructive)">${this._esc(error)}</div>`;
            return;
        }
        if (!item) {
            host.innerHTML = '<div class="text-sm text-muted">Select a release result to view details.</div>';
            return;
        }

        const images = item.images || {};
        host.innerHTML = `
            <div class="pet-image-grid pet-skill-images">
                ${this._imagePanel('Before Release', images.available, images.available_filename)}
                ${this._imagePanel('After Release', images.obtained, images.obtained_filename)}
            </div>
            <div class="pet-kpi-grid pet-skill-metrics">
                ${this._miniMetric('Pool Slots', `${this._fmt(item.pool_filled_count)} / ${this._fmt(item.pool_total_slots)}`)}
                ${this._miniMetric('Obtained Slot', item.get_slot_position ? `#${item.get_slot_position}` : '-')}
                ${this._miniMetric('Emulator', item.emulator || '-')}
                ${this._miniMetric('Account', item.account_name || item.game_id || 'Unmatched')}
            </div>
            <div class="pet-facts-panel">
                <div class="pet-facts-title">Analyzed Data</div>
                <div class="pet-facts-grid pet-skill-facts">
                    ${this._factRow('Release Time', item.datetime || '-')}
                    ${this._factRow('Release ID', item.release_id || '-')}
                    ${this._factRow('Skill Pool', `${this._fmt(item.pool_filled_count)} skill(s) in ${this._fmt(item.pool_total_slots)} slot(s)`)}
                    ${this._factRow('Obtained From', item.get_slot_position ? `Slot #${item.get_slot_position}` : '-')}
                    ${this._factRow('Source Emulator', item.emulator || '-')}
                    ${this._skillStarsRow(item.skill_stars, item.pool_total_slots, item.get_slot_position)}
                </div>
            </div>
        `;
    },

    _imagePanel(label, url, filename) {
        return `
            <div class="pet-image-panel">
                <div class="pet-image-head">
                    <span class="font-medium">${this._esc(label)}</span>
                    <span class="text-xs text-muted truncate">${this._esc(filename || '')}</span>
                </div>
                <div class="pet-image-stage">
                    ${url ? `<img src="${this._esc(url)}" alt="${this._esc(label)}">` : '<span class="text-sm text-muted">Image not found</span>'}
                </div>
            </div>
        `;
    },

    _miniMetric(label, value) {
        return `
            <div class="pet-mini-metric">
                <div>${this._esc(label)}</div>
                <strong>${this._esc(value)}</strong>
            </div>
        `;
    },

    _factRow(label, value) {
        return `
            <div class="pet-fact-row">
                <div>${this._esc(label)}</div>
                <strong title="${this._esc(value)}">${this._esc(value)}</strong>
            </div>
        `;
    },

    _skillStarsRow(stars, totalSlots, obtainedSlot) {
        const slotCount = Math.max(
            Number(totalSlots) || 0,
            Array.isArray(stars) ? stars.length : 0,
            Number(obtainedSlot) || 0
        );
        if (!slotCount) {
            return this._factRow('Skill Stars By Slot', '-');
        }
        const slots = Array.from({ length: slotCount }, (_, index) => {
            const slot = index + 1;
            const rawStars = Array.isArray(stars) ? Number(stars[index] || 0) : 0;
            const starCount = Math.max(0, Math.min(3, rawStars));
            const isObtained = Number(obtainedSlot) === slot;
            const visual = Array.from({ length: 3 }, (_, starIndex) => (
                `<span class="pet-star ${starIndex < starCount ? 'filled' : ''}"></span>`
            )).join('');
            const value = rawStars > 0 ? `${rawStars} star${rawStars > 1 ? 's' : ''}` : '0 star';
            return `
                <div class="pet-slot-star ${isObtained ? 'obtained' : ''}">
                    <div class="pet-slot-star-head">
                        <span>Slot #${slot}</span>
                        ${isObtained ? '<b>Obtained</b>' : ''}
                    </div>
                    <div class="pet-star-track" aria-label="Slot ${slot}: ${this._esc(value)}">${visual}</div>
                    <strong>${this._esc(value)}</strong>
                </div>
            `;
        });
        return `
            <div class="pet-fact-row pet-skill-stars-row">
                <div>Skill Stars By Slot</div>
                <div class="pet-slot-stars-grid">${slots.join('')}</div>
            </div>
        `;
    },

    showReleaseEmpty(message) {
        const list = document.getElementById('pet-skill-release-list');
        if (list) list.innerHTML = `<div class="pet-empty-state">${this._esc(message || 'No data')}</div>`;
    },

    _statSkeleton(label) {
        return `
            <div class="summary-card is-loading">
                <div class="summary-label">${this._esc(label)}</div>
                <div class="summary-value">--</div>
                <div class="summary-note">Waiting for data</div>
            </div>
        `;
    },

    _statCard(label, value, subtitle) {
        return `
            <div class="summary-card">
                <div class="summary-label">${this._esc(label)}</div>
                <div class="summary-value">${this._esc(value)}</div>
                <div class="summary-note">${this._esc(subtitle)}</div>
            </div>
        `;
    },

    paintDistribution() {
        const host = document.getElementById('pet-skill-distribution');
        const meta = document.getElementById('pet-skill-distribution-meta');
        const data = this._data || {};
        const slots = data.by_slot || {};
        const total = Number(data.total_releases || 0);
        if (meta) meta.innerHTML = total ? `<span class="legend-item">Total ${this._fmt(total)} release(s)</span>` : '';
        if (!host) return;
        const entries = Object.entries(slots)
            .filter(([key]) => key !== 'unknown')
            .sort((a, b) => Number(a[0]) - Number(b[0]));
        if (!entries.length) {
            host.innerHTML = '<div class="pet-empty-state">No slot distribution available.</div>';
            return;
        }
        host.innerHTML = entries.map(([slot, count]) => {
            const pct = total ? Math.round((Number(count) / total) * 100) : 0;
            return `
                <div class="pet-dist-tile">
                    <div class="pet-dist-head"><span>Slot #${this._esc(slot)}</span><strong>${pct}%</strong></div>
                    <div class="pet-dist-bar"><span style="width:${pct}%"></span></div>
                    <div class="pet-dist-note">${this._fmt(count)} release(s)</div>
                </div>
            `;
        }).join('');
    },

    _poolHealth(values) {
        const entries = Object.entries(values || {});
        if (!entries.length) return { value: '--', note: 'No pool data' };
        const top = entries.sort((a, b) => Number(b[1]) - Number(a[1]))[0];
        const total = entries.reduce((sum, [, count]) => sum + Number(count || 0), 0);
        const pct = total ? Math.round((Number(top[1]) / total) * 100) : 0;
        return { value: `${top[0]} slots`, note: `${pct}% most common pool size` };
    },

    _topEntry(values) {
        return Object.entries(values).filter(([key]) => key !== 'unknown').sort((a, b) => b[1] - a[1])[0] || null;
    },

    _pct(value, total) {
        return total ? `${Math.round((value / total) * 100)}%` : '0%';
    },

    _fmt(value) {
        if (value === null || value === undefined || value === '') return '-';
        const number = Number(value);
        return Number.isFinite(number) ? number.toLocaleString() : String(value);
    },

    _esc(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    _escJs(value) {
        return String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    },
};
