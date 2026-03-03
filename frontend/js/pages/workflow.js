/**
 * Workflow V3 — Recipe Builder (Two-Layer UI)
 * Layer 1: Recipe List — gallery of all saved workflows + templates
 * Layer 2: Recipe Editor — step-by-step builder (opens on click/new)
 */

const WorkflowPage = {
    render() {
        return `
    <div class="wf-page">
      <!-- MAIN TABS to switch between Builder and Activities -->
      <div class="wf-main-tabs">
        <button class="wf-main-tab active" data-view="builder" onclick="WF3.switchMainTab('builder')">Recipe Builder</button>
        <button class="wf-main-tab" data-view="activity" onclick="WF3.switchMainTab('activity')">Activity (Bot)</button>
        <button class="wf-main-tab" data-view="group" onclick="WF3.switchMainTab('group')">Account Groups</button>
      </div>

      <!-- ============================================== 
           SECTION A: RECIPE BUILDER (Existing V3)
           ============================================== -->
      <div id="wf-section-builder" class="wf-section-container active">
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
            <select id="wf-emu-select" class="wf-cf-select" style="max-width: 150px; border: 1px solid var(--border); padding: 4px 8px; border-radius: var(--radius-sm); font-size: 13px;">
                <option value="">Select Emulator...</option>
            </select>
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
      </div> <!-- End Editor View -->
      </div> <!-- End Section Builder -->

      <!-- ============================================== 
           SECTION B: ACTIVITY (Light Theme Layout)
           ============================================== -->
      <!-- ============================================== 
           SECTION B: ACTIVITY (Bot) — PREMIUM REDESIGN
           ============================================== -->
      <div id="wf-section-activity" class="wf-section-container" style="display:none">

        <!-- TARGET GROUPS — Checkbox List -->
        <div class="acv-groups-bar">
          <div class="acv-groups-bar-label">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            TARGET GROUPS
          </div>
          <div id="wf-activity-group-list" class="acv-groups-list">
            <div class="acv-chip-skeleton">Loading...</div>
          </div>
        </div>

        <!-- MAIN TWO-COLUMN LAYOUT -->
        <div class="acv-layout">

          <!-- LEFT: Activities + Misc -->
          <div class="acv-left">
            <div class="acv-panel">
              <!-- Panel header with tabs -->
              <div class="acv-panel-header">
                <div class="acv-panel-tabs">
                  <button class="acv-tab active" id="acv-tab-btn-tasks" onclick="WF3.switchActivityTab('tasks')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                    Activities
                  </button>
                  <button class="acv-tab" id="acv-tab-btn-misc" onclick="WF3.switchActivityTab('misc')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 0-14.14 0M20.49 9A10 10 0 0 1 3.51 9M3.51 15a10 10 0 0 0 16.98 0"/></svg>
                    Misc
                  </button>
                </div>
                <span id="wf-act-group-badge" class="acv-group-badge">No group</span>
              </div>

              <!-- Activities list -->
              <div id="wf-act-tab-tasks" class="acv-panel-body">
                <div id="wf-act-dynamic-list" class="acv-activities-list">
                  <div class="acv-empty-hint">Select a group above to configure its activities.</div>
                </div>
              </div>

              <!-- Misc tab -->
              <div id="wf-act-tab-misc" class="acv-panel-body" style="display:none">
                <div class="acv-misc-list">
                  <div class="acv-misc-item">
                    <label class="acv-check-label">
                      <input type="checkbox" checked>
                      <span class="acv-check-box"></span>
                      <span>Re-login if logged in from another device</span>
                    </label>
                    <div class="acv-misc-sub">after <input type="number" class="acv-input-num" value="1"> minute(s)</div>
                  </div>
                  <div class="acv-misc-item">
                    <label class="acv-check-label">
                      <input type="checkbox">
                      <span class="acv-check-box"></span>
                      <span>Ultra mode: Stop graphics (GPU), reduce CPU</span>
                    </label>
                    <div class="acv-misc-hint">Applies to all instances</div>
                  </div>
                  <div class="acv-misc-item">
                    <label class="acv-check-label">
                      <input type="checkbox" checked>
                      <span class="acv-check-box"></span>
                      <span>Close after <input type="number" class="acv-input-num" value="28"> ~ <input type="number" class="acv-input-num" value="28"> min</span>
                    </label>
                    <div class="acv-misc-sub">
                      <label class="acv-check-label" style="gap:6px">
                        <input type="checkbox"><span class="acv-check-box"></span>
                        <span>Re-open after <input type="number" class="acv-input-num" value="60"> ~ <input type="number" class="acv-input-num" value="90"> min</span>
                      </label>
                    </div>
                    <div class="acv-misc-sub">
                      <label class="acv-check-label" style="gap:6px">
                        <input type="checkbox" checked><span class="acv-check-box"></span>
                        <span>Open next emulator on bot's list</span>
                      </label>
                    </div>
                  </div>
                  <div class="acv-misc-item">
                    <label class="acv-check-label">
                      <input type="checkbox" checked>
                      <span class="acv-check-box"></span>
                      <span>Pause when manual interactions detected</span>
                    </label>
                    <div class="acv-misc-sub">stop for <input type="number" class="acv-input-num" value="15"> second(s)</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- RIGHT: Log + Config -->
          <div class="acv-right">
            <div class="acv-panel">
              <!-- Right panel tabs: Activity Log | Config -->
              <div class="acv-panel-header">
                <div class="acv-panel-tabs">
                  <button class="acv-tab active" id="acv-rtab-btn-log" onclick="WF3.switchRightTab('log')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
                    Activity Log
                  </button>
                  <button class="acv-tab" id="acv-rtab-btn-config" onclick="WF3.switchRightTab('config')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 0-14.14 0M3.51 9a10 10 0 0 0 0 6M20.49 9a10 10 0 0 0 0 6M4.93 19.07a10 10 0 0 0 14.14 0"/></svg>
                    Config
                  </button>
                </div>
                <!-- Start Bot action button -->
                <button onclick="WF3.runBotActivities()" style="
                    display:inline-flex; align-items:center; gap:5px;
                    padding:5px 12px; font-size:12px; font-weight:700;
                    background: #22c55e; color:white; border:none;
                    border-radius:var(--radius-md); cursor:pointer;
                    transition: all var(--duration-fast);
                    box-shadow:0 1px 4px rgba(34,197,94,.3);
                " onmouseover="this.style.background='#16a34a'" onmouseout="this.style.background='#22c55e'">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                  Start Bot
                </button>
              </div>

              <!-- Activity Log pane -->
              <div id="acv-rtab-log" class="acv-panel-body acv-log-pane">
                <div id="wf-activity-console" class="acv-console">
                  <div class="acv-log-line acv-log-info"><span class="acv-log-ts">[06:04:31]</span> Call of Dragons Bot v1.0.2.0 — Ready</div>
                  <div class="acv-log-line acv-log-muted"><span class="acv-log-ts">[06:04:31]</span> Activities run top to bottom. Check/Uncheck to enable/disable.</div>
                </div>
              </div>

              <!-- Config pane -->
              <div id="acv-rtab-config" class="acv-panel-body" style="display:none">
                <div id="acv-config-panel" class="acv-config-panel">
                  <div class="acv-empty-hint">Select an activity from the left to view its config.</div>
                </div>
              </div>

            </div>
          </div>

        </div>
      </div> <!-- End Section Activity -->

      <!-- ============================================== 
           SECTION C: ACCOUNT GROUPS — PREMIUM REDESIGN
           ============================================== -->
      <div id="wf-section-group" class="wf-section-container" style="display:none">
        <div class="grp-layout">

          <!-- LEFT: Group sidebar -->
          <div class="grp-sidebar">
            <div class="grp-sidebar-header">
              <div class="grp-sidebar-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                Account Groups
              </div>
              <button class="grp-new-btn" onclick="WF3.createNewGroup()">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                New
              </button>
            </div>
            <div id="wf-group-list" class="grp-sidebar-list"></div>
          </div>

          <!-- RIGHT: Editor / Empty state -->
          <div class="grp-content">

            <!-- Editor -->
            <div id="wf-group-editor" class="grp-editor" style="display:none">
              <div class="grp-editor-topbar">
                <div>
                  <p class="grp-editor-eyebrow">Account Group</p>
                  <h2 id="wf-group-editor-title" class="grp-editor-title">Create Group</h2>
                </div>
                <div class="grp-editor-actions">
                  <button class="grp-btn-danger" id="wf-group-btn-delete" style="display:none" onclick="WF3.deleteCurrentGroup()">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                    Delete
                  </button>
                  <button class="grp-btn-primary" onclick="WF3.saveCurrentGroup()">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                    Save Group
                  </button>
                </div>
              </div>

              <div class="grp-editor-body">
                <div class="grp-field">
                  <label class="grp-label">Group Name</label>
                  <input type="text" id="wf-group-name" class="grp-input" placeholder="e.g. Farm Bots — Alpha Team">
                </div>

                <!-- View Mode: shows only selected accounts -->
                <div id="wf-group-view-mode" class="grp-field" style="flex:1; min-height:0; display:flex; flex-direction:column;">
                  <div class="grp-label-row">
                    <label class="grp-label">Members</label>
                    <span id="wf-group-member-count" class="grp-count-badge">0 accounts</span>
                    <button class="grp-btn-edit" onclick="WF3.enterGroupEditMode()">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      Edit
                    </button>
                  </div>
                  <div id="wf-group-members-list" class="grp-members-list">
                    <div class="grp-table-empty">No accounts selected.</div>
                  </div>
                </div>

                <!-- Edit Mode: full account table with checkboxes (hidden by default) -->
                <div id="wf-group-edit-mode" class="grp-field" style="flex:1; min-height:0; display:flex; flex-direction:column; display:none;">
                  <div class="grp-label-row">
                    <label class="grp-label">Select Accounts</label>
                    <span id="wf-group-selected-count" class="grp-count-badge">0 selected</span>
                    <button class="grp-btn-edit" onclick="WF3.exitGroupEditMode()">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                      Done
                    </button>
                  </div>
                  <div class="grp-table-wrap">
                    <table class="grp-table">
                      <thead>
                        <tr>
                          <th style="width:44px; text-align:center;">
                            <input type="checkbox" id="wf-group-select-all" onclick="WF3.toggleAllGroupAccounts(this.checked)">
                          </th>
                          <th>Lord Name</th>
                          <th>Emulator</th>
                          <th>Game ID</th>
                        </tr>
                      </thead>
                      <tbody id="wf-group-accounts-list">
                        <tr><td colspan="4" class="grp-table-empty">Loading accounts...</td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div id="wf-group-empty" class="grp-empty">
              <div class="grp-empty-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              </div>
              <p class="grp-empty-title">No group selected</p>
              <p class="grp-empty-sub">Select a group from the sidebar or create a new one to get started.</p>
              <button class="grp-btn-primary" onclick="WF3.createNewGroup()">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Create New Group
              </button>
            </div>

          </div>
        </div>
      </div>

      <div id="wf-toast-zone" class="wf-toast-zone"></div>
    </div>`;
    },

    renderActivityItem(name) {
        return `
            <div class="wf-act-list-item">
                <label class="wf-checkbox-label">
                    <input type="checkbox">
                    <span class="wf-checkbox-custom"></span>
                    <span>${name}</span>
                </label>
                <div class="wf-act-status">N/A</div>
            </div>
        `;
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
        this.activeMainTab = 'builder';

        await Promise.all([
            this.fetchFunctions(),
            this.fetchTemplates(),
            this.fetchRecipes(),
            this.fetchEmulators(),
        ]);

        this.setupWebSocket();
        this.renderListView();
    },

    // setupWebSocket is handled globally in app.js (wsClient.on('workflow_log', ...))
    setupWebSocket() { },

    cleanup() {
        this.steps = [];
        this.functions = [];
        // Optional: remove ws client listeners if navigation handles it strictly
        // wsClient.off('workflow_log');
        // wsClient.off('workflow_progress');
        // wsClient.off('workflow_status');
    },

    async refreshList() {
        await Promise.all([this.fetchTemplates(), this.fetchRecipes()]);
        this.renderListView();
        WfToast.show('s', 'Refreshed', 'List updated');
    },

    // ── MAIN TAB SWITCHING ──
    switchMainTab(tab) {
        this.activeMainTab = tab;
        document.querySelectorAll('.wf-main-tab').forEach(el => {
            el.classList.toggle('active', el.dataset.view === tab);
        });

        const builderSec = document.getElementById('wf-section-builder');
        const activitySec = document.getElementById('wf-section-activity');
        const groupSec = document.getElementById('wf-section-group');

        if (builderSec) builderSec.style.display = 'none';
        if (activitySec) activitySec.style.display = 'none';
        if (groupSec) groupSec.style.display = 'none';

        if (tab === 'builder') {
            if (builderSec) builderSec.style.display = 'block';
        } else if (tab === 'activity') {
            if (activitySec) { activitySec.style.display = 'flex'; activitySec.style.flexDirection = 'column'; }
            this.loadGroupsData();
        } else if (tab === 'group') {
            if (groupSec) groupSec.style.display = 'block';
            this.loadGroupsData();
        }
    },

    // ── ACTIVITY SUB-TAB SWITCHING ──
    switchActivityTab(tab) {
        const tasks = document.getElementById('wf-act-tab-tasks');
        const misc = document.getElementById('wf-act-tab-misc');
        const btnTasks = document.getElementById('acv-tab-btn-tasks');
        const btnMisc = document.getElementById('acv-tab-btn-misc');
        if (tasks) tasks.style.display = (tab === 'tasks') ? '' : 'none';
        if (misc) misc.style.display = (tab === 'misc') ? '' : 'none';
        if (btnTasks) btnTasks.classList.toggle('active', tab === 'tasks');
        if (btnMisc) btnMisc.classList.toggle('active', tab === 'misc');
    },

    // ── RIGHT PANEL TAB SWITCHING ──
    switchRightTab(tab) {
        const logPane = document.getElementById('acv-rtab-log');
        const cfgPane = document.getElementById('acv-rtab-config');
        const btnLog = document.getElementById('acv-rtab-btn-log');
        const btnCfg = document.getElementById('acv-rtab-btn-config');
        if (logPane) logPane.style.display = (tab === 'log') ? '' : 'none';
        if (cfgPane) cfgPane.style.display = (tab === 'config') ? '' : 'none';
        if (btnLog) btnLog.classList.toggle('active', tab === 'log');
        if (btnCfg) btnCfg.classList.toggle('active', tab === 'config');
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

    async fetchEmulators() {
        try {
            const res = await fetch('/api/emulators/all');
            const data = await res.json();
            const select = document.getElementById('wf-emu-select');
            if (select) {
                const online = data.filter(e => e.running === true);
                if (online.length === 0) {
                    select.innerHTML = '<option value="">(No devices online)</option>';
                } else {
                    select.innerHTML = '<option value="">Select Emulator...</option>' +
                        online.map(e => `<option value="${e.index}">${e.name} (Idx ${e.index})</option>`).join('');
                }
            }
        } catch (e) {
            console.error('Failed to fetch emulators:', e);
        }
    },

    // ── ACCOUNT GROUPS LOGIC ──
    groupsData: [],
    accountsData: [],
    currentGroupId: null,

    // ── ACTIVITY TAB STATE ──
    activitySelectedGroupId: null,

    async loadGroupsData() {
        try {
            this.groupsData = await API.getGroups();
            this.renderGroupList();
            this.updateActivityGroupList();

            if (this.accountsData.length === 0) {
                await this.loadAccountsData();
            }
        } catch (e) {
            console.error('Failed to load groups:', e);
        }
    },

    async loadAccountsData() {
        try {
            const res = await fetch('/api/accounts');
            this.accountsData = await res.json();
        } catch (e) {
            console.error('Failed to load accounts:', e);
            this.accountsData = [];
        }
    },

    updateActivityGroupList() {
        const listDiv = document.getElementById('wf-activity-group-list');
        if (!listDiv) return;

        if (this.groupsData.length === 0) {
            listDiv.innerHTML = '<div class="acv-chip-empty">No groups. Create one in Account Groups tab.</div>';
            this.activitySelectedGroupId = null;
            this.renderActivitiesForGroup(null);
            return;
        }

        listDiv.innerHTML = this.groupsData.map(g => {
            const accs = JSON.parse(g.account_ids || '[]');
            const isSelected = this.activitySelectedGroupId === g.id;
            return `
                <label class="acv-group-item ${isSelected ? 'active' : ''}">
                    <input type="checkbox" class="acv-group-cb" value="${g.id}" ${isSelected ? 'checked' : ''}
                        onchange="WF3.toggleActivityGroup(${g.id}, this.checked)">
                    <span class="acv-check-box"></span>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                    <span class="acv-group-item-name">${g.name}</span>
                    <span class="acv-chip-count">${accs.length}</span>
                </label>
            `;
        }).join('');

        // Auto-select first group if none selected
        if (!this.activitySelectedGroupId && this.groupsData.length > 0) {
            this.toggleActivityGroup(this.groupsData[0].id, true);
        }
    },

    toggleActivityGroup(groupId, checked) {
        if (checked) {
            this.activitySelectedGroupId = groupId;
            // Uncheck other checkboxes (single-select for now, activities render per one group)
            document.querySelectorAll('.acv-group-cb').forEach(cb => {
                if (parseInt(cb.value) !== groupId) cb.checked = false;
            });
            document.querySelectorAll('.acv-group-item').forEach(el => el.classList.remove('active'));
            const activeCb = document.querySelector(`.acv-group-cb[value="${groupId}"]`);
            if (activeCb) activeCb.closest('.acv-group-item').classList.add('active');
        } else {
            this.activitySelectedGroupId = null;
        }
        this.renderActivitiesForGroup(this.activitySelectedGroupId);
    },

    getActivityConfig(groupId) {
        try {
            const raw = localStorage.getItem(`wf_activities_${groupId}`);
            if (raw) {
                const parsed = JSON.parse(raw);
                // Migrate old string format to object format if needed
                const validParsed = parsed.map(item => typeof item === 'string'
                    ? { id: item, name: item, enabled: false, desc: '' }
                    : item
                );
                // Still need to make sure fresh backend functions exist in the mapping, but this is a simple local storage return
            }
        } catch (e) { }

        // Return default config (all unchecked) from matching backend functions.
        return this.functions.map(fn => (
            { id: fn.id, name: fn.label, enabled: false, desc: fn.description || '' }
        ));
    },

    saveActivityConfig(groupId) {
        if (!groupId) return;
        const items = document.querySelectorAll('#wf-act-dynamic-list .wf-act-group-cb');
        const config = Array.from(items).map(cb => ({ name: cb.dataset.name, enabled: cb.checked }));
        localStorage.setItem(`wf_activities_${groupId}`, JSON.stringify(config));
        WfToast.show('s', 'Saved', 'Activities config saved for this group.');
    },

    // Run enabled activities for selected group via bot API
    async runBotActivities() {
        const groupId = this.activitySelectedGroupId;
        if (!groupId) {
            WfToast.show('w', 'No Group', 'Select a target group first.');
            return;
        }
        const config = this.getActivityConfig(groupId);
        const enabled = config.filter(a => a.enabled).map(a => a.name);
        if (enabled.length === 0) {
            WfToast.show('w', 'No Activities', 'Enable at least one activity first.');
            return;
        }

        // Switch to Log tab to show output
        this.switchRightTab('log');

        // Find group data and resolving emulators
        const group = this.groupsData.find(g => g.id === groupId);
        let emulatorIndices = [];
        if (group && group.account_ids) {
            try {
                const accIds = JSON.parse(group.account_ids);
                // this.accountsData has all accounts, loaded by WorkflowApp init
                const accs = this.accountsData.filter(a => accIds.includes(a.account_id));
                // Extract emulator indices (filter out nulls)
                emulatorIndices = accs.map(a => a.emu_index).filter(idx => idx != null);
                // Remove duplicates
                emulatorIndices = [...new Set(emulatorIndices)];
            } catch (e) {
                console.error("Failed to parse accounts for group", e);
            }
        }

        this.addBotLog('info', `Starting ${enabled.length} activities for group '${group ? group.name : groupId}'...`);

        try {
            const payload = {
                group_id: groupId,
                activities: enabled
            };
            if (emulatorIndices.length > 0) {
                payload.emulator_indices = emulatorIndices;
                this.addBotLog('info', `Found ${emulatorIndices.length} emulators: ${emulatorIndices.join(', ')}`);
            } else {
                this.addBotLog('warn', `Warning: Frontend couldn't find emulator indices. Requesting backend to resolve.`);
            }

            const res = await fetch('/api/bot/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'accepted') {
                const names = (data.emulators || []).map(e => e.name).join(', ');
                this.addBotLog('ok', `✓ Bot started on: ${names || 'emulators'}`);
                WfToast.show('s', 'Bot Started', `Running on ${data.emulators?.length || '?'} emulators`);
            } else {
                this.addBotLog('err', `✕ Error: ${data.error || 'Unknown error'}`);
                WfToast.show('e', 'Error', data.error || 'Failed to start bot');
            }
        } catch (e) {
            this.addBotLog('err', `✕ Network error: ${e.message}`);
            WfToast.show('e', 'Network Error', e.message);
        }
    },

    // Add a log line to Activity Log console
    addBotLog(type, message) {
        const console = document.getElementById('wf-activity-console');
        if (!console) return;
        const ts = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const line = document.createElement('div');
        line.className = `acv-log-line acv-log-${type}`;
        line.innerHTML = `<span class="acv-log-ts">[${ts}]</span> ${message}`;
        console.appendChild(line);
        console.scrollTop = console.scrollHeight;
    },

    renderActivitiesForGroup(groupId) {
        const container = document.getElementById('wf-act-dynamic-list');
        if (!container) return;

        // Update badge
        const badge = document.getElementById('wf-act-group-badge');
        if (badge) {
            const grp = this.groupsData.find(g => g.id === groupId);
            badge.textContent = grp ? grp.name : 'No group';
            badge.style.display = grp ? '' : 'none';
        }

        if (!groupId) {
            container.innerHTML = '<div class="acv-empty-hint">Select a group above to configure its activities.</div>';
            return;
        }

        const config = this.getActivityConfig(groupId);
        container.innerHTML = config.map((item, idx) => `
            <div class="acv-activity-row ${item.enabled ? 'enabled' : ''}" id="acv-row-${idx}">
                <label class="acv-check-label" style="flex:1; cursor:pointer;">
                    <input type="checkbox" class="wf-act-group-cb" data-name="${item.name}" data-idx="${idx}" ${item.enabled ? 'checked' : ''}
                        onchange="WF3.saveActivityConfig(${groupId}); this.closest('.acv-activity-row').classList.toggle('enabled', this.checked)">
                    <span class="acv-check-box"></span>
                    <span class="acv-activity-name">${item.name}</span>
                </label>
                <button class="acv-cfg-btn" title="Configure" onclick="WF3.showActivityConfig('${item.name}', ${groupId})">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 0-14.14 0M3.51 9a10 10 0 0 0 0 6M20.49 9a10 10 0 0 0 0 6M4.93 19.07a10 10 0 0 0 14.14 0"/></svg>
                </button>
            </div>
        `).join('');
    },

    // Per-activity config definitions
    _activityConfigDefs: {
        'Technology Research': [{ key: 'max_slots', label: 'Max Research Slots', type: 'number', default: 2, min: 1, max: 4 }],
        'Train Troops': [{ key: 'troop_type', label: 'Troop Type', type: 'select', options: ['Infantry', 'Cavalry', 'Ranged', 'Siege'], default: 'Infantry' }, { key: 'max_queues', label: 'Max Queues', type: 'number', default: 2, min: 1, max: 5 }],
        'Alliance Donation': [{ key: 'donate_gold', label: 'Donate Gold', type: 'checkbox', default: true }],
        'Gather Resources': [{ key: 'resource_type', label: 'Priority Resource', type: 'select', options: ['Food', 'Wood', 'Stone', 'Gold', 'Any'], default: 'Any' }, { key: 'troop_count', label: 'Marches', type: 'number', default: 3, min: 1, max: 6 }],
        'Attack Darkling Patrols': [{ key: 'patrol_level', label: 'Max Level', type: 'number', default: 5, min: 1, max: 10 }, { key: 'marches', label: 'Marches', type: 'number', default: 2, min: 1, max: 4 }],
        'Join Rally': [{ key: 'min_power', label: 'Min Alliance Power', type: 'number', default: 0, min: 0 }],
        'City Upgrade': [{ key: 'auto_resource', label: 'Auto use resources', type: 'checkbox', default: true }],
        'Goblin Market': [{ key: 'buy_speed_ups', label: 'Buy Speed Ups', type: 'checkbox', default: false }, { key: 'buy_resources', label: 'Buy Resources', type: 'checkbox', default: true }],
        'Claim quest rewards': [{ key: 'claim_daily', label: 'Claim Daily Quests', type: 'checkbox', default: true }, { key: 'claim_main', label: 'Claim Main Quests', type: 'checkbox', default: true }],
        'Explore Fog': [{ key: 'max_marches', label: 'Max Marches', type: 'number', default: 2, min: 1, max: 5 }],
    },

    getPerActivityConfig(activityName, groupId) {
        try {
            const raw = localStorage.getItem(`wf_acfg_${groupId}_${activityName}`);
            if (raw) return JSON.parse(raw);
        } catch (e) { }
        const defs = this._activityConfigDefs[activityName] || [];
        const defaults = {};
        defs.forEach(d => defaults[d.key] = d.default);
        return defaults;
    },

    savePerActivityConfig(activityName, groupId) {
        const panel = document.getElementById('acv-config-panel');
        if (!panel) return;
        const vals = {};
        panel.querySelectorAll('[data-cfgkey]').forEach(el => {
            vals[el.dataset.cfgkey] = el.type === 'checkbox' ? el.checked : (el.type === 'number' ? +el.value : el.value);
        });
        localStorage.setItem(`wf_acfg_${groupId}_${activityName}`, JSON.stringify(vals));
        WfToast.show('s', 'Config Saved', `${activityName}`);
    },

    showActivityConfig(activityName, groupId) {
        // Switch to config tab
        this.switchRightTab('config');

        const panel = document.getElementById('acv-config-panel');
        if (!panel) return;

        const defs = this._activityConfigDefs[activityName] || [];
        const saved = this.getPerActivityConfig(activityName, groupId);

        if (defs.length === 0) {
            panel.innerHTML = `
                <div class="acv-cfg-header">
                    <div class="acv-cfg-title">${activityName}</div>
                    <div class="acv-cfg-sub">No configurable options for this activity.</div>
                </div>
            `;
            return;
        }

        const fieldsHtml = defs.map(d => {
            const val = saved[d.key] !== undefined ? saved[d.key] : d.default;
            if (d.type === 'checkbox') {
                return `
                <div class="acv-cfg-field">
                    <label class="acv-check-label" style="gap:10px;">
                        <input type="checkbox" data-cfgkey="${d.key}" ${val ? 'checked' : ''} onchange="WF3.savePerActivityConfig('${activityName.replace(/'/g, "\\'")}',${groupId})">
                        <span class="acv-check-box"></span>
                        <span>${d.label}</span>
                    </label>
                </div>`;
            }
            if (d.type === 'select') {
                const opts = d.options.map(o => `<option value="${o}" ${val === o ? 'selected' : ''}>${o}</option>`).join('');
                return `
                <div class="acv-cfg-field">
                    <label class="acv-cfg-label">${d.label}</label>
                    <select class="acv-cfg-select" data-cfgkey="${d.key}" onchange="WF3.savePerActivityConfig('${activityName.replace(/'/g, "\\'")}',${groupId})">${opts}</select>
                </div>`;
            }
            return `
            <div class="acv-cfg-field">
                <label class="acv-cfg-label">${d.label}</label>
                <input type="number" class="acv-cfg-input" data-cfgkey="${d.key}" value="${val}" ${d.min !== undefined ? 'min="' + d.min + '"' : ''} ${d.max !== undefined ? 'max="' + d.max + '"' : ''} onchange="WF3.savePerActivityConfig('${activityName.replace(/'/g, "\\'")}',${groupId})">
            </div>`;
        }).join('');

        panel.innerHTML = `
            <div class="acv-cfg-header">
                <div class="acv-cfg-back-row">
                    <button class="acv-cfg-back" onclick="document.getElementById('acv-rtab-config').innerHTML='<div class=acv-empty-hint>Select an activity from the left to view its config.</div>'">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
                        Back
                    </button>
                </div>
                <div class="acv-cfg-title">${activityName}</div>
                <div class="acv-cfg-sub">Configuration for this group's activity</div>
            </div>
            <div class="acv-cfg-fields">${fieldsHtml}</div>
        `;
    },

    renderGroupList() {
        const listObj = document.getElementById('wf-group-list');
        if (!listObj) return;

        if (this.groupsData.length === 0) {
            listObj.innerHTML = '<div class="grp-list-empty">No groups yet. Click <strong>New</strong> to create one.</div>';
            return;
        }

        listObj.innerHTML = this.groupsData.map(g => {
            const count = JSON.parse(g.account_ids || '[]').length;
            const isActive = this.currentGroupId === g.id;
            return `
                <div class="grp-list-item ${isActive ? 'active' : ''}" onclick="WF3.editGroup(${g.id})">
                    <div class="grp-list-item-icon">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                    </div>
                    <div class="grp-list-item-body">
                        <div class="grp-list-item-name">${g.name}</div>
                        <div class="grp-list-item-meta">${count} account${count !== 1 ? 's' : ''}</div>
                    </div>
                    <div class="grp-list-item-arrow">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                </div>
            `;
        }).join('');
    },

    createNewGroup() {
        this.currentGroupId = null;
        this._currentGroupAccountIds = [];
        document.getElementById('wf-group-editor-title').textContent = 'Create New Group';
        document.getElementById('wf-group-name').value = '';
        document.getElementById('wf-group-btn-delete').style.display = 'none';

        this.renderGroupAccounts([]);
        this.enterGroupEditMode();
        this.showGroupEditor();
        this.renderGroupList();
    },

    editGroup(id) {
        const group = this.groupsData.find(g => g.id === id);
        if (!group) return;

        this.currentGroupId = id;
        document.getElementById('wf-group-editor-title').textContent = 'Edit Group';
        document.getElementById('wf-group-name').value = group.name;
        document.getElementById('wf-group-btn-delete').style.display = '';

        const accountIds = JSON.parse(group.account_ids || '[]');
        this._currentGroupAccountIds = accountIds;
        this.renderGroupMembersView(accountIds);
        this.exitGroupEditMode();
        this.showGroupEditor();
        this.renderGroupList();
    },

    showGroupEditor() {
        document.getElementById('wf-group-empty').style.display = 'none';
        document.getElementById('wf-group-editor').style.display = 'flex';
    },

    // ── View / Edit Mode for Account Groups ──
    _currentGroupAccountIds: [],

    renderGroupMembersView(accountIds) {
        const container = document.getElementById('wf-group-members-list');
        const countEl = document.getElementById('wf-group-member-count');
        if (!container) return;

        if (!accountIds || accountIds.length === 0) {
            container.innerHTML = '<div class="grp-table-empty">No accounts selected. Click <strong>Edit</strong> to add accounts.</div>';
            if (countEl) countEl.textContent = '0 accounts';
            return;
        }

        // Resolve account data
        const members = this.accountsData.filter(a => accountIds.includes(a.account_id));
        if (countEl) countEl.textContent = `${members.length} account${members.length !== 1 ? 's' : ''}`;

        container.innerHTML = members.map(acc => `
            <div class="grp-member-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                <div class="grp-member-info">
                    <span class="grp-member-name">${acc.lord_name || 'Unknown'}</span>
                    <span class="grp-member-meta">${acc.emu_name || (acc.emu_index != null ? 'Emu ' + acc.emu_index : '?')} · ${acc.game_id}</span>
                </div>
            </div>
        `).join('');
    },

    enterGroupEditMode() {
        const viewMode = document.getElementById('wf-group-view-mode');
        const editMode = document.getElementById('wf-group-edit-mode');
        if (viewMode) viewMode.style.display = 'none';
        if (editMode) editMode.style.display = 'flex';

        // Load full account table with current selections
        this.renderGroupAccounts(this._currentGroupAccountIds || []);
    },

    exitGroupEditMode() {
        const viewMode = document.getElementById('wf-group-view-mode');
        const editMode = document.getElementById('wf-group-edit-mode');
        if (viewMode) viewMode.style.display = 'flex';
        if (editMode) editMode.style.display = 'none';

        // Update _currentGroupAccountIds from checkboxes if edit mode was active
        const cbs = document.querySelectorAll('.wf-group-account-cb:checked');
        if (cbs.length > 0 || document.querySelectorAll('.wf-group-account-cb').length > 0) {
            this._currentGroupAccountIds = Array.from(cbs).map(cb => parseInt(cb.value));
        }
        this.renderGroupMembersView(this._currentGroupAccountIds);
    },

    renderGroupAccounts(selectedIds = []) {
        const tbody = document.getElementById('wf-group-accounts-list');
        const countSpan = document.getElementById('wf-group-selected-count');

        if (this.accountsData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="padding: 20px; text-align: center; color: var(--text-muted);">No accounts found. Create them in the Accounts page first.</td></tr>';
            countSpan.textContent = '(0 selected)';
            return;
        }

        tbody.innerHTML = this.accountsData.map(acc => {
            const isSelected = selectedIds.includes(acc.account_id) ? 'checked' : '';
            return `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 10px 14px; text-align: center;">
                        <input type="checkbox" class="wf-group-account-cb" value="${acc.account_id}" ${isSelected} onchange="WF3.updateGroupCount()">
                    </td>
                    <td style="padding: 10px 14px;">
                        <div style="font-weight: 600;">${acc.lord_name || 'Unknown'}</div>
                    </td>
                    <td style="padding: 10px 14px; color: var(--muted-foreground);">${acc.emu_name || (acc.emu_index != null ? `Emulator ${acc.emu_index}` : '?')}</td>
                    <td style="padding: 10px 14px; font-family: var(--font-mono); font-size: 12px; color: var(--muted-foreground);">${acc.game_id}</td>
                </tr>
            `;
        }).join('');
        this.updateGroupCount();
    },

    toggleAllGroupAccounts(checked) {
        document.querySelectorAll('.wf-group-account-cb').forEach(cb => {
            cb.checked = checked;
        });
        this.updateGroupCount();
    },

    updateGroupCount() {
        const count = document.querySelectorAll('.wf-group-account-cb:checked').length;
        document.getElementById('wf-group-selected-count').textContent = `${count} selected`;

        // Update master checkbox state
        const total = document.querySelectorAll('.wf-group-account-cb').length;
        const master = document.getElementById('wf-group-select-all');
        if (master) {
            master.checked = count === total && total > 0;
            master.indeterminate = count > 0 && count < total;
        }
    },

    async saveCurrentGroup() {
        const nameInput = document.getElementById('wf-group-name');
        const name = nameInput.value.trim();

        if (!name) {
            WfToast.show('e', 'Validation', 'Group name is required.');
            nameInput.focus();
            return;
        }

        const selectedIds = Array.from(document.querySelectorAll('.wf-group-account-cb:checked'))
            .map(cb => parseInt(cb.value));

        try {
            if (this.currentGroupId) {
                // Update
                const res = await API.updateGroup(this.currentGroupId, { name, account_ids: selectedIds });
                if (res.error) throw new Error(res.error);
                WfToast.show('s', 'Saved', 'Group updated successfully.');
            } else {
                // Create
                const res = await API.createGroup({ name, account_ids: selectedIds });
                if (res.error) throw new Error(res.error);
                this.currentGroupId = res.id;
                WfToast.show('s', 'Created', 'Group created successfully.');
            }
            // Refresh
            await this.loadGroupsData();
            this.editGroup(this.currentGroupId); // Re-select to update UI state properly
        } catch (e) {
            WfToast.show('e', 'Error', e.message);
        }
    },

    async deleteCurrentGroup() {
        if (!this.currentGroupId) return;

        if (!confirm('Are you sure you want to delete this group?')) return;

        try {
            const res = await API.deleteGroup(this.currentGroupId);
            if (res.error) throw new Error(res.error);

            WfToast.show('s', 'Deleted', 'Group removed.');
            this.currentGroupId = null;
            document.getElementById('wf-group-editor').style.display = 'none';
            document.getElementById('wf-group-empty').style.display = 'flex';

            await this.loadGroupsData();
        } catch (e) {
            WfToast.show('e', 'Error', e.message);
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

    // ── WebSocket Log & Progress Receivers ──
    setupWebSocket() {
        if (!window.wsClient) return;

        wsClient.on('workflow_log', (data) => {
            const logEl = document.getElementById('wf-exec-log');
            if (!logEl) return;
            const ts = new Date().toLocaleTimeString('en-GB', { hour12: false });
            const line = document.createElement('div');
            line.className = `wf-log-line log-${data.log_type}`;
            line.innerHTML = `<span class="log-time">${ts}</span><span>${data.message}</span>`;
            logEl.appendChild(line);
            logEl.scrollTop = logEl.scrollHeight;

            if (data.log_type === 'run') {
                document.querySelectorAll('.wf-step-card').forEach(el => el.classList.remove('running'));
                // Extract step idx from "[<n>/<total>]" strings
                const match = data.message.match(/\[(\d+)\//);
                if (match) {
                    const idx = parseInt(match[1]) - 1;
                    const card = document.getElementById(`wf-step-${idx}`);
                    if (card) {
                        card.classList.add('running');
                        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }
        });

        wsClient.on('workflow_progress', (data) => {
            const pct = Math.round((data.current / data.total) * 100);
            const fill = document.getElementById('wf-exec-progress-fill');
            const pctEl = document.getElementById('wf-exec-pct');
            if (fill) fill.style.width = pct + '%';
            if (pctEl) pctEl.textContent = pct + '%';
        });

        wsClient.on('workflow_status', (data) => {
            const statusEl = document.getElementById('wf-status');
            const btn = document.getElementById('wf-btn-run');

            if (data.status === 'RUNNING') {
                if (statusEl) { statusEl.textContent = 'RUNNING'; statusEl.className = 'wf-status status-running'; }
                if (btn) { btn.classList.add('running'); btn.innerHTML = '<span class="wf-spinner"></span> Running...'; }
            } else {
                this.isRunning = false;
                if (btn) { btn.classList.remove('running'); btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run'; }
                document.querySelectorAll('.wf-step-card').forEach(el => el.classList.remove('running'));

                if (data.status === 'SUCCESS') {
                    if (statusEl) { statusEl.textContent = 'SUCCESS'; statusEl.className = 'wf-status status-success'; }
                    WfToast.show('s', 'Done', 'Workflow finished!');
                } else if (data.status === 'ERROR') {
                    if (statusEl) { statusEl.textContent = 'ERROR'; statusEl.className = 'wf-status status-error'; }
                    WfToast.show('e', 'Error', 'Workflow execution failed.');
                }
            }
        });
    },

    // ── EXECUTION ──
    async runWorkflow() {
        if (this.isRunning) return;
        if (this.steps.length === 0) {
            WfToast.show('e', 'Error', 'No steps to run.');
            return;
        }

        const emuSelect = document.getElementById('wf-emu-select');
        const emulatorIndex = emuSelect ? emuSelect.value : '';

        if (!emulatorIndex) {
            WfToast.show('w', 'Select Emulator', 'Please choose an emulator first.');
            return;
        }

        this.isRunning = true;

        const execPanel = document.getElementById('wf-exec-panel');
        const logEl = document.getElementById('wf-exec-log');
        if (execPanel) execPanel.classList.add('visible');
        if (logEl) {
            logEl.innerHTML = `
                <div class="wf-log-line log-info">
                    <span class="log-time">${new Date().toLocaleTimeString('en-GB', { hour12: false })}</span>
                    <span>▶ Sending execution request to backend...</span>
                </div>
            `;
        }

        try {
            const res = await fetch('/api/workflow/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    emulator_index: emulatorIndex,
                    steps: this.steps
                })
            });
            const data = await res.json();

            if (data.status !== 'accepted') {
                this.isRunning = false;
                WfToast.show('e', 'Failed', data.error || 'Server rejected request');
            }
        } catch (e) {
            this.isRunning = false;
            WfToast.show('e', 'Error', 'Failed to communicate with server');
        }
    },

    delay(ms) { return new Promise(r => setTimeout(r, ms)); },
};
