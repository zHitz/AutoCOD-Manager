/**
 * Workflow V3 — Recipe Builder (Two-Layer UI)
 * Layer 1: Recipe List — gallery of all saved workflows + templates
 * Layer 2: Recipe Editor — step-by-step builder (opens on click/new)
 */

const WorkflowPage = {
    render() {
        return `
    <div class="wf-page">
      <!-- LAYER 1: Recipe List -->
      <div id="wf-list-view" class="wf-list-view">
        <div class="wf-list-topbar">
          <div class="wf-list-topbar-left">
            <h2>Recipe Builder</h2>
            <span class="wf-badge">V3</span>
          </div>
          <div style="display:flex;gap:8px;">
            <button class="btn btn-outline btn-sm" style="display:flex;align-items:center;gap:6px;" onclick="WF3.refreshList()">
              <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary btn-sm" style="display:flex;align-items:center;gap:6px;" onclick="WF3.createNewRecipe()">
              <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Create New
            </button>
          </div>
        </div>

        <div class="wf-list-body">
          <!-- Templates Section -->
          <div class="wf-list-section">
            <div class="wf-list-section-header">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
              <span>Templates</span>
              <span class="wf-list-count" id="wf-tpl-count">0</span>
            </div>
            <div id="wf-list-templates" class="wf-list-grid"></div>
          </div>

          <!-- My Recipes Section -->
          <div class="wf-list-section">
            <div class="wf-list-section-header">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/></svg>
              <span>My Recipes</span>
              <span class="wf-list-count" id="wf-recipe-count">0</span>
            </div>
            <div id="wf-list-recipes" class="wf-list-grid"></div>
          </div>
        </div>
      </div>

      <!-- LAYER 2: Recipe Editor (hidden by default) -->
      <div id="wf-editor-view" class="wf-editor-view" style="display:none">
        <div class="wf-topbar">
          <button class="btn btn-ghost btn-sm" onclick="WF3.backToList()" style="padding:6px 10px;display:flex;align-items:center;gap:4px;">
            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg> Back
          </button>
          <div class="wf-topbar-sep"></div>
          <input id="wf-name-input" class="wf-name-input" type="text" value="Untitled Recipe" spellcheck="false" />
          <div class="wf-topbar-sep"></div>
          <button class="btn btn-outline btn-sm" onclick="WF3.saveRecipe()" style="display:flex;align-items:center;gap:5px;">
            <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Save
          </button>
          <div class="wf-topbar-right">
            <span id="wf-status" class="wf-status">IDLE</span>
            <button class="btn btn-primary btn-sm" id="wf-btn-run" onclick="WF3.runWorkflow()" style="display:flex;align-items:center;gap:5px;">
              <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run
            </button>
          </div>
        </div>

        <div class="wf-main">
          <!-- LEFT: Function Library -->
          <div class="wf-sidebar">
            <div class="wf-sidebar-section">
              <div class="wf-sidebar-title">⚡ Functions</div>
              <input id="wf-sidebar-search" class="wf-sidebar-search" placeholder="Search..." oninput="WF3.renderSidebarFunctions(this.value)" />
              <div id="wf-sidebar-fn-list" class="wf-sidebar-list"></div>
            </div>
          </div>

          <!-- CENTER: Step Editor -->
          <div class="wf-editor-center">
            <div id="wf-step-editor" class="wf-step-editor"></div>
            <button class="wf-add-step-btn" onclick="WF3.openFunctionPicker()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Add Step
            </button>
          </div>

          <!-- Execution Panel -->
          <div id="wf-exec-panel" class="wf-exec-panel">
            <div class="wf-exec-header">
              <span class="wf-exec-title">Execution</span>
              <div id="wf-exec-progress" class="wf-exec-progress">
                <div id="wf-exec-progress-fill" class="wf-exec-progress-fill"></div>
              </div>
              <span id="wf-exec-pct" class="wf-exec-pct">0%</span>
              <button class="wf-exec-close" onclick="document.getElementById('wf-exec-panel').classList.remove('visible')">✕</button>
            </div>
            <div id="wf-exec-log" class="wf-exec-log"></div>
          </div>
        </div>
      </div>

      <!-- Function Picker Modal -->
      <div id="wf-fn-picker-overlay" class="wf-fn-overlay" onclick="WF3.closeFunctionPicker()">
        <div class="wf-fn-picker" onclick="event.stopPropagation()">
          <div class="wf-fn-picker-header">
            <h3>Add Step</h3>
            <input id="wf-fn-search" class="wf-fn-search" placeholder="Search functions..." oninput="WF3.filterFunctions(this.value)" />
            <button class="wf-fn-close" onclick="WF3.closeFunctionPicker()">✕</button>
          </div>
          <div id="wf-fn-list" class="wf-fn-list"></div>
        </div>
      </div>

      <div id="wf-toast-zone" class="wf-toast-zone"></div>
    </div>`;
    },

    init() { WF3.init(); },
    destroy() { WF3.cleanup(); },
};

// ═══════════════════════════════════════════════
//  TOAST
// ═══════════════════════════════════════════════
const WfToast = {
    show(type, title, msg) {
        const zone = document.getElementById('wf-toast-zone');
        if (!zone) return;
        const el = document.createElement('div');
        el.className = `wf-toast ${type}`;
        el.innerHTML = `<div class="wf-t-dot"></div><span><strong>${title}</strong> — ${msg}</span>`;
        zone.appendChild(el);
        setTimeout(() => { el.classList.add('wf-toast-out'); setTimeout(() => el.remove(), 280); }, 2800);
    }
};

// ═══════════════════════════════════════════════
//  RECIPE BUILDER ENGINE V3
// ═══════════════════════════════════════════════
const WF3 = {
    steps: [],
    functions: [],
    templates: [],
    recipes: [],
    currentRecipeId: null,
    isRunning: false,
    insertIndex: -1,
    activeView: 'list', // 'list' or 'editor'

    async init() {
        this.steps = [];
        this.isRunning = false;
        this.currentRecipeId = null;
        this.activeView = 'list';

        await Promise.all([
            this.fetchFunctions(),
            this.fetchTemplates(),
            this.fetchRecipes(),
        ]);

        this.renderListView();
    },

    cleanup() {
        this.steps = [];
        this.functions = [];
    },

    async refreshList() {
        await Promise.all([this.fetchTemplates(), this.fetchRecipes()]);
        this.renderListView();
        WfToast.show('s', 'Refreshed', 'List updated');
    },

    // ── VIEW SWITCHING ──
    showListView() {
        this.activeView = 'list';
        const listView = document.getElementById('wf-list-view');
        const editorView = document.getElementById('wf-editor-view');
        if (listView) listView.style.display = '';
        if (editorView) editorView.style.display = 'none';
    },

    showEditorView() {
        this.activeView = 'editor';
        const listView = document.getElementById('wf-list-view');
        const editorView = document.getElementById('wf-editor-view');
        if (listView) listView.style.display = 'none';
        if (editorView) editorView.style.display = '';
    },

    backToList() {
        if (this.isRunning) {
            WfToast.show('w', 'Running', 'Cannot go back while workflow is executing.');
            return;
        }
        this.showListView();
        this.fetchRecipes().then(() => this.renderListView());
    },

    // ── DATA FETCHING ──
    async fetchFunctions() {
        try {
            const res = await fetch('/api/workflow/functions');
            this.functions = await res.json();
        } catch (e) {
            console.error('Failed to fetch functions:', e);
            this.functions = [];
        }
    },

    async fetchTemplates() {
        try {
            const res = await fetch('/api/workflow/templates');
            this.templates = await res.json();
        } catch (e) {
            console.error('Failed to fetch templates:', e);
            this.templates = [];
        }
    },

    async fetchRecipes() {
        try {
            const res = await fetch('/api/workflow/recipes');
            this.recipes = await res.json();
        } catch (e) {
            console.error('Failed to fetch recipes:', e);
            this.recipes = [];
        }
    },

    // ═══════════════════════════════════════════
    //  LAYER 1: LIST VIEW
    // ═══════════════════════════════════════════
    renderListView() {
        // Templates
        const tplGrid = document.getElementById('wf-list-templates');
        const tplCount = document.getElementById('wf-tpl-count');
        if (tplCount) tplCount.textContent = this.templates.length;

        if (tplGrid) {
            tplGrid.innerHTML = this.templates.map(t => `
                <div class="wf-recipe-card wf-tpl-card" onclick="WF3.openTemplateInEditor('${t.id}')">
                    <div class="wf-rc-icon">${t.icon}</div>
                    <div class="wf-rc-info">
                        <div class="wf-rc-name">${t.name}</div>
                        <div class="wf-rc-desc">${t.description}</div>
                    </div>
                    <div class="wf-rc-meta">
                        <span class="wf-rc-steps">${t.steps.length} steps</span>
                        <span class="wf-rc-badge tpl">Template</span>
                    </div>
                </div>
            `).join('');
        }

        // Recipes
        const recGrid = document.getElementById('wf-list-recipes');
        const recCount = document.getElementById('wf-recipe-count');
        if (recCount) recCount.textContent = this.recipes.length;

        if (recGrid) {
            if (this.recipes.length === 0) {
                recGrid.innerHTML = `
                    <div class="wf-list-empty">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
                            <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
                        </svg>
                        <p>No saved recipes yet.<br>Click <strong>Create New</strong> or use a template to get started.</p>
                    </div>`;
            } else {
                recGrid.innerHTML = this.recipes.map(r => `
                    <div class="wf-recipe-card" onclick="WF3.openRecipeInEditor('${r.id}')">
                        <div class="wf-rc-icon">${r.icon || '📝'}</div>
                        <div class="wf-rc-info">
                            <div class="wf-rc-name">${r.name}</div>
                            <div class="wf-rc-desc">${r.description || (r.steps || []).length + ' steps'}</div>
                        </div>
                        <div class="wf-rc-meta">
                            <span class="wf-rc-steps">${(r.steps || []).length} steps</span>
                        </div>
                        <button class="wf-rc-delete" onclick="event.stopPropagation(); WF3.deleteRecipeFromList('${r.id}')" title="Delete">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                        </button>
                    </div>
                `).join('');
            }
        }
    },

    // ── LIST ACTIONS ──
    createNewRecipe() {
        this.currentRecipeId = null;
        this.steps = [];
        this.showEditorView();
        document.getElementById('wf-name-input').value = 'Untitled Recipe';
        this.renderSidebarFunctions();
        this.renderSteps();
        const s = document.getElementById('wf-status');
        if (s) { s.textContent = 'IDLE'; s.className = 'wf-status'; }
    },

    openTemplateInEditor(id) {
        const tpl = this.templates.find(t => t.id === id);
        if (!tpl) return;
        this.currentRecipeId = null;
        this.steps = JSON.parse(JSON.stringify(tpl.steps));
        this.showEditorView();
        document.getElementById('wf-name-input').value = tpl.name + ' (Copy)';
        this.renderSidebarFunctions();
        this.renderSteps();
        WfToast.show('i', 'Template', `Loaded "${tpl.name}"`);
    },

    openRecipeInEditor(id) {
        const recipe = this.recipes.find(r => r.id === id);
        if (!recipe) return;
        this.currentRecipeId = recipe.id;
        this.steps = JSON.parse(JSON.stringify(recipe.steps || []));
        this.showEditorView();
        document.getElementById('wf-name-input').value = recipe.name;
        this.renderSidebarFunctions();
        this.renderSteps();
        WfToast.show('s', 'Loaded', `"${recipe.name}"`);
    },

    async deleteRecipeFromList(id) {
        if (!confirm('Delete this recipe?')) return;
        try {
            await fetch(`/api/workflow/recipes/${id}`, { method: 'DELETE' });
            await this.fetchRecipes();
            this.renderListView();
            WfToast.show('s', 'Deleted', 'Recipe removed');
        } catch (e) {
            WfToast.show('e', 'Error', 'Failed to delete');
        }
    },

    // ═══════════════════════════════════════════
    //  LAYER 2: EDITOR VIEW
    // ═══════════════════════════════════════════

    // ── SIDEBAR FUNCTION LIBRARY ──
    renderSidebarFunctions(filter = '') {
        const list = document.getElementById('wf-sidebar-fn-list');
        if (!list) return;

        const q = (filter || '').toLowerCase();
        const categories = {};
        this.functions.forEach(fn => {
            if (q && !fn.label.toLowerCase().includes(q) && !fn.description.toLowerCase().includes(q)) return;
            if (!categories[fn.category]) categories[fn.category] = [];
            categories[fn.category].push(fn);
        });

        if (Object.keys(categories).length === 0) {
            list.innerHTML = '<div class="wf-sidebar-empty">No matches</div>';
            return;
        }

        list.innerHTML = Object.entries(categories).map(([cat, fns]) => `
            <div class="wf-sidebar-cat">${cat}</div>
            ${fns.map(fn => `
                <div class="wf-sidebar-fn" onclick="WF3.addStepFromSidebar('${fn.id}')">
                    <span class="wf-sidebar-fn-icon" style="color:${fn.color}">${fn.icon}</span>
                    <div>
                        <div class="wf-sidebar-fn-name">${fn.label}</div>
                        <div class="wf-sidebar-fn-desc">${fn.description}</div>
                    </div>
                </div>
            `).join('')}
        `).join('');
    },

    addStepFromSidebar(functionId) {
        const fn = this.functions.find(f => f.id === functionId);
        if (!fn || this.isRunning) return;
        const config = {};
        (fn.params || []).forEach(p => { config[p.key] = p.default; });
        this.steps.push({ function_id: functionId, config });
        this.renderSteps();
        WfToast.show('s', 'Added', fn.label);
        setTimeout(() => {
            const editor = document.querySelector('.wf-editor-center');
            if (editor) editor.scrollTop = editor.scrollHeight;
        }, 50);
    },

    // ── SAVE / DELETE ──
    async saveRecipe() {
        if (this.isRunning) return;
        const name = document.getElementById('wf-name-input')?.value || 'Untitled';
        const payload = {
            name,
            steps: this.steps,
            icon: '📝',
            description: `${this.steps.length} steps`
        };
        if (this.currentRecipeId) payload.id = this.currentRecipeId;

        try {
            const res = await fetch('/api/workflow/recipes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'ok') {
                this.currentRecipeId = data.id;
                await this.fetchRecipes();
                WfToast.show('s', 'Saved', `"${name}" ${data.action}`);
            }
        } catch (e) {
            WfToast.show('e', 'Error', 'Failed to save recipe');
        }
    },

    // ── FUNCTION PICKER MODAL ──
    openFunctionPicker(insertAt) {
        this.insertIndex = insertAt !== undefined ? insertAt : -1;
        const overlay = document.getElementById('wf-fn-picker-overlay');
        if (overlay) overlay.classList.add('visible');
        this.renderFunctionList();
        const searchInput = document.getElementById('wf-fn-search');
        if (searchInput) { searchInput.value = ''; searchInput.focus(); }
    },

    closeFunctionPicker() {
        const overlay = document.getElementById('wf-fn-picker-overlay');
        if (overlay) overlay.classList.remove('visible');
    },

    filterFunctions(query) {
        this.renderFunctionList(query.toLowerCase());
    },

    renderFunctionList(filter = '') {
        const list = document.getElementById('wf-fn-list');
        if (!list) return;

        const categories = {};
        this.functions.forEach(fn => {
            if (filter && !fn.label.toLowerCase().includes(filter) && !fn.description.toLowerCase().includes(filter)) return;
            if (!categories[fn.category]) categories[fn.category] = [];
            categories[fn.category].push(fn);
        });

        if (Object.keys(categories).length === 0) {
            list.innerHTML = '<div class="wf-fn-empty">No functions match your search</div>';
            return;
        }

        list.innerHTML = Object.entries(categories).map(([cat, fns]) => `
            <div class="wf-fn-category">${cat}</div>
            ${fns.map(fn => `
                <div class="wf-fn-item" onclick="WF3.addStepFromPicker('${fn.id}')">
                    <div class="wf-fn-icon" style="color:${fn.color}">${fn.icon}</div>
                    <div>
                        <div class="wf-fn-label">${fn.label}</div>
                        <div class="wf-fn-desc">${fn.description}</div>
                    </div>
                </div>
            `).join('')}
        `).join('');
    },

    addStepFromPicker(functionId) {
        const fn = this.functions.find(f => f.id === functionId);
        if (!fn) return;

        const config = {};
        (fn.params || []).forEach(p => { config[p.key] = p.default; });
        const step = { function_id: functionId, config };

        if (this.insertIndex >= 0 && this.insertIndex <= this.steps.length) {
            this.steps.splice(this.insertIndex, 0, step);
        } else {
            this.steps.push(step);
        }

        this.closeFunctionPicker();
        this.renderSteps();
        WfToast.show('s', 'Added', fn.label);
    },

    // ── STEP MANAGEMENT ──
    removeStep(index) {
        if (this.isRunning) return;
        this.steps.splice(index, 1);
        this.renderSteps();
    },

    moveStepUp(index) {
        if (this.isRunning || index === 0) return;
        [this.steps[index], this.steps[index - 1]] = [this.steps[index - 1], this.steps[index]];
        this.renderSteps();
    },

    moveStepDown(index) {
        if (this.isRunning || index === this.steps.length - 1) return;
        [this.steps[index], this.steps[index + 1]] = [this.steps[index + 1], this.steps[index]];
        this.renderSteps();
    },

    updateStepConfig(index, key, val) {
        if (this.steps[index]) {
            this.steps[index].config[key] = val;
        }
    },

    getFnDef(functionId) {
        return this.functions.find(f => f.id === functionId) || {
            id: functionId, label: functionId, icon: '?', color: '#999',
            description: 'Unknown function', params: [], category: 'Unknown'
        };
    },

    // ── STEP RENDERING ──
    renderSteps() {
        const container = document.getElementById('wf-step-editor');
        if (!container) return;

        if (this.steps.length === 0) {
            container.innerHTML = `
                <div class="wf-empty-hint">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
                        <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
                    </svg>
                    <h3>No steps yet</h3>
                    <p>Pick a function from the left panel,<br>or click <strong>Add Step</strong> below.</p>
                </div>`;
            return;
        }

        let html = '';
        this.steps.forEach((step, index) => {
            const fn = this.getFnDef(step.function_id);
            const configHtml = this.renderConfigFields(step, fn, index);

            html += `
                <div class="wf-step-card" id="wf-step-${index}">
                    <div class="wf-step-number">${index + 1}</div>
                    <div class="wf-step-body">
                        <div class="wf-step-header">
                            <div class="wf-step-icon" style="color:${fn.color}">${fn.icon}</div>
                            <div>
                                <div class="wf-step-title">${fn.label}</div>
                                <div class="wf-step-subtitle">${fn.description}</div>
                            </div>
                        </div>
                        ${configHtml}
                    </div>
                    <div class="wf-step-status" id="wf-step-status-${index}"></div>
                    <div class="wf-step-actions">
                        <button class="wf-icon-btn" onclick="WF3.moveStepUp(${index})" ${index === 0 ? 'disabled' : ''}>▲</button>
                        <button class="wf-icon-btn" onclick="WF3.moveStepDown(${index})" ${index === this.steps.length - 1 ? 'disabled' : ''}>▼</button>
                        <div style="flex:1"></div>
                        <button class="wf-icon-btn danger" onclick="WF3.removeStep(${index})">✕</button>
                    </div>
                </div>

                <button class="wf-insert-btn" onclick="WF3.openFunctionPicker(${index + 1})" title="Insert step here">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>
            `;
        });

        container.innerHTML = html;
    },

    renderConfigFields(step, fn, index) {
        if (!fn.params || fn.params.length === 0) return '';

        const fields = fn.params.map(p => {
            const val = step.config[p.key] !== undefined ? step.config[p.key] : p.default;

            if (p.type === 'select') {
                const opts = (p.options || []).map(o =>
                    `<option value="${o}" ${val === o ? 'selected' : ''}>${o}</option>`
                ).join('');
                return `<div class="wf-cf-field">
                    <span class="wf-cf-label">${p.label}</span>
                    <select class="wf-cf-select" onchange="WF3.updateStepConfig(${index},'${p.key}',this.value)">${opts}</select>
                </div>`;
            }

            if (p.type === 'number') {
                return `<div class="wf-cf-field">
                    <span class="wf-cf-label">${p.label}</span>
                    <input class="wf-cf-input" type="number" value="${val}" ${p.min !== undefined ? `min="${p.min}"` : ''} ${p.max !== undefined ? `max="${p.max}"` : ''} onchange="WF3.updateStepConfig(${index},'${p.key}',+this.value)" style="width:80px;" />
                </div>`;
            }

            return `<div class="wf-cf-field">
                <span class="wf-cf-label">${p.label}</span>
                <input class="wf-cf-input" type="text" value="${val}" onchange="WF3.updateStepConfig(${index},'${p.key}',this.value)" />
            </div>`;
        }).join('');

        return `<div class="wf-step-configs">${fields}</div>`;
    },

    // ── EXECUTION ──
    async runWorkflow() {
        if (this.isRunning) return;
        if (this.steps.length === 0) {
            WfToast.show('e', 'Error', 'No steps to run.');
            return;
        }

        this.isRunning = true;

        const btn = document.getElementById('wf-btn-run');
        if (btn) { btn.classList.add('running'); btn.innerHTML = '<span class="wf-spinner"></span> Running...'; }

        const statusEl = document.getElementById('wf-status');
        if (statusEl) { statusEl.textContent = 'RUNNING'; statusEl.className = 'wf-status status-running'; }

        const execPanel = document.getElementById('wf-exec-panel');
        const logEl = document.getElementById('wf-exec-log');
        if (execPanel) execPanel.classList.add('visible');
        if (logEl) logEl.innerHTML = '';

        const addLog = (type, msg) => {
            if (!logEl) return;
            const ts = new Date().toLocaleTimeString('en-GB', { hour12: false });
            const line = document.createElement('div');
            line.className = `wf-log-line log-${type}`;
            line.innerHTML = `<span class="log-time">${ts}</span><span>${msg}</span>`;
            logEl.appendChild(line);
            logEl.scrollTop = logEl.scrollHeight;
        };

        const updateProgress = (current, total) => {
            const pct = Math.round((current / total) * 100);
            const fill = document.getElementById('wf-exec-progress-fill');
            const pctEl = document.getElementById('wf-exec-pct');
            if (fill) fill.style.width = pct + '%';
            if (pctEl) pctEl.textContent = pct + '%';
        };

        document.querySelectorAll('.wf-step-card').forEach(el => el.classList.remove('running', 'success', 'error'));

        addLog('info', '▶ Workflow execution started');
        let allOk = true;

        for (let i = 0; i < this.steps.length; i++) {
            const step = this.steps[i];
            const fn = this.getFnDef(step.function_id);
            const cardEl = document.getElementById(`wf-step-${i}`);
            const statusIndicator = document.getElementById(`wf-step-status-${i}`);

            if (cardEl) {
                cardEl.classList.add('running');
                cardEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            if (statusIndicator) statusIndicator.innerHTML = '<span class="wf-spinner"></span> Running...';

            addLog('run', `[${i + 1}/${this.steps.length}] ${fn.label}...`);
            updateProgress(i, this.steps.length);

            const execTime = step.function_id === 'flow_delay' ? (step.config.seconds || 10) * 100 : 800 + Math.random() * 1200;
            await this.delay(execTime);

            const ok = Math.random() > 0.05;

            if (ok) {
                if (cardEl) { cardEl.classList.remove('running'); cardEl.classList.add('success'); }
                if (statusIndicator) statusIndicator.innerHTML = '<span style="color:#22c55e">✓ Done</span>';
                addLog('ok', `  ✓ ${fn.label} complete`);
            } else {
                if (cardEl) { cardEl.classList.remove('running'); cardEl.classList.add('error'); }
                if (statusIndicator) statusIndicator.innerHTML = '<span style="color:#ef4444">✕ Failed</span>';
                addLog('err', `  ✕ ${fn.label} failed`);
                allOk = false;
                break;
            }
        }

        updateProgress(this.steps.length, this.steps.length);
        this.isRunning = false;

        if (btn) { btn.classList.remove('running'); btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run'; }

        if (allOk) {
            if (statusEl) { statusEl.textContent = 'SUCCESS'; statusEl.className = 'wf-status status-success'; }
            addLog('ok', '✅ Workflow completed successfully');
            WfToast.show('s', 'Done', 'Workflow finished!');
        } else {
            if (statusEl) { statusEl.textContent = 'ERROR'; statusEl.className = 'wf-status status-error'; }
            addLog('err', '❌ Workflow aborted');
            WfToast.show('e', 'Error', 'Execution stopped.');
        }
    },

    delay(ms) { return new Promise(r => setTimeout(r, ms)); },
};
