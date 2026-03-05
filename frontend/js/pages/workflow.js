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
        <button class="wf-main-tab active" data-view="activity" onclick="WF3.switchMainTab('activity')">Activity (Bot)</button>
        <button class="wf-main-tab" data-view="builder" onclick="WF3.switchMainTab('builder')">Recipe Builder</button>
        <button class="wf-main-tab" data-view="group" onclick="WF3.switchMainTab('group')">Account Groups</button>
      </div>

      <!-- ============================================== 
           SECTION A: RECIPE BUILDER (Existing V3)
           ============================================== -->
      <div id="wf-section-builder" class="wf-section-container" style="display:none">
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
      <div id="wf-section-activity" class="wf-section-container active" style="display:flex;flex-direction:column">

        <!-- 3-COLUMN LAYOUT: Groups Sidebar | Activities | Log/Config -->
        <div class="acv-layout">

          <!-- COL 1: Target Groups Sidebar -->
          <div class="acv-groups-sidebar">
            <div class="acv-groups-sidebar-header">
              <div class="acv-groups-sidebar-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                Target Groups
              </div>
            </div>
            <div id="wf-activity-group-list" class="acv-groups-sidebar-list">
              <div class="acv-chip-skeleton">Loading...</div>
            </div>
          </div>

          <!-- COL 2: Activities + Misc -->
          <div class="acv-center">
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
                  <div class="acv-empty-hint">Select a group to configure its activities.</div>
                </div>
              </div>

              <!-- Misc tab -->
              <div id="wf-act-tab-misc" class="acv-panel-body" style="display:none">
                <div class="acv-misc-list" id="wf-act-dynamic-misc-list">
                  <div class="acv-empty-hint">Select a group to configure its Misc settings.</div>
                </div>
              </div>
            </div>
          </div>

          <!-- COL 3: Log + Config -->
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
                  <button class="acv-tab" id="acv-rtab-btn-status" onclick="WF3.switchRightTab('status')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    Live Status
                  </button>
                </div>
                <!-- Action buttons -->
                <div style="display:flex; gap:8px;">
                  <button onclick="WF3.stopBotActivities()" style="
                      display:inline-flex; align-items:center; gap:5px;
                      padding:5px 12px; font-size:12px; font-weight:700;
                      background: #ef4444; color:white; border:none;
                      border-radius:var(--radius-md); cursor:pointer;
                      transition: all var(--duration-fast);
                      box-shadow:0 1px 4px rgba(239, 68, 68, 0.3);
                  " onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>
                    Stop Bot
                  </button>
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

              <!-- Live Status pane -->
              <div id="acv-rtab-status" class="acv-panel-body" style="display:none; padding: 16px; overflow-y: auto;">
                <div style="display: flex; flex-direction: column; gap: 16px;">
                  <div style="background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px; display: flex; align-items: center; justify-content: space-between;">
                    <div>
                      <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 4px;">Session Time</div>
                      <div id="wf-live-session-time" style="font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums;">00:00:00</div>
                    </div>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--emerald-500)" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                  </div>
                  
                  <div style="background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
                    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 4px;">Current Status</div>
                    <div id="wf-live-status-text" style="font-size: 18px; font-weight: 600; color: var(--text);">Idle</div>
                    <div id="wf-live-activity-name" style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">Waiting for bot to start...</div>
                  </div>
                  
                  <div style="background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
                    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 4px;">Cooldown Countdown</div>
                    <div id="wf-live-cooldown" style="font-size: 16px; font-weight: 500; color: var(--text);">--:--</div>
                  </div>
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

    // ── NEW: Dynamic Registry & Config Cache ──
    _systemActivities: [],   // Loaded from /api/workflow/activity-registry
    _groupConfigs: {},       // Cache for loaded group configs (v2 schema)

    /**
     * Dynamically loads ES Module architecture (Strangler pattern)
     * Paths are relative to frontend/js/pages/workflow.js -> ../
     */
    async _initDI() {
        if (this.di) return;

        try {
            const { HttpClient } = await import('../shared/http/HttpClient.js');

            const { WorkflowRepository } = await import('../infrastructure/workflow/repositories/WorkflowRepository.js');
            const { EmulatorRepository } = await import('../infrastructure/workflow/repositories/EmulatorRepository.js');
            const { GroupRepository } = await import('../infrastructure/workflow/repositories/GroupRepository.js');
            const { AccountRepository } = await import('../infrastructure/workflow/repositories/AccountRepository.js');
            const { ActivityConfigRepository } = await import('../infrastructure/workflow/repositories/ActivityConfigRepository.js');
            const { BotRepository } = await import('../infrastructure/workflow/repositories/BotRepository.js');
            const { ExecutionRepository } = await import('../infrastructure/workflow/repositories/ExecutionRepository.js');

            const { LoadWorkflowScreenService } = await import('../application/workflow/services/LoadWorkflowScreenService.js');
            const { SaveRecipeService } = await import('../application/workflow/services/SaveRecipeService.js');
            const { RunWorkflowService } = await import('../application/workflow/services/RunWorkflowService.js');
            const { RunBotActivitiesService } = await import('../application/workflow/services/RunBotActivitiesService.js');
            const { StopBotService } = await import('../application/workflow/services/StopBotService.js');
            const { SaveActivityConfigService } = await import('../application/workflow/services/SaveActivityConfigService.js');

            const http = new HttpClient();
            const configRepo = new ActivityConfigRepository(http);
            const botRepo = new BotRepository(http);
            const groupRepo = new GroupRepository(http);
            const workflowRepo = new WorkflowRepository(http);
            const emuRepo = new EmulatorRepository(http);
            const accountRepo = new AccountRepository(http);
            const executionRepo = new ExecutionRepository(http);

            this.di = {
                workflowRepo, emuRepo, groupRepo, accountRepo, configRepo, botRepo, executionRepo,

                loadScreen: new LoadWorkflowScreenService({ workflowRepo, emuRepo, groupRepo, accountRepo, configRepo }),
                saveRecipe: new SaveRecipeService({ workflowRepo }),
                runWorkflow: new RunWorkflowService({ executionRepo }),
                runBot: new RunBotActivitiesService({ botRepo, configRepo, groupRepo, accountRepo }),
                stopBot: new StopBotService({ botRepo }),
                saveConfig: new SaveActivityConfigService({ configRepo })
            };
            console.log("✅ Workflow DI Container Initialized");
        } catch (error) {
            console.error("❌ Failed to initialize DI container:", error);
        }
    },

    async init() {
        await this._initDI();

        this.steps = [];
        // Removed resetting isRunning to false here, we'll restore it from API
        this.currentRecipeId = null;
        this.activeView = 'list';
        this.activeMainTab = 'activity';

        // ── BUG 2 FIX: Load central registry first ──
        await this.loadRegistry();

        // ── BUG 1 & 3 FIX: Restore saved selection and init log memory ──
        const savedGroupId = localStorage.getItem('wf_selected_group_id');
        if (savedGroupId) {
            this.activitySelectedGroupId = parseInt(savedGroupId);
        }
        if (!this._botLogs) {
            this._botLogs = []; // Initialize in-memory logs 
        }

        await Promise.all([
            this.fetchFunctions(),
            this.fetchTemplates(),
            this.fetchRecipes(),
            this.fetchEmulators(),
        ]);

        this.setupWebSocket();
        this.renderListView();
        // Activity is the default tab, load groups data immediately
        await this.loadGroupsData();

        // Restore logs to DOM
        this._replayLogs();

        // Check orchestrator status if we have a selected group
        if (this.activitySelectedGroupId) {
            try {
                if (!this.di) await this._initDI();
                const res = await this.di.botRepo.getStatus(this.activitySelectedGroupId);
                if (res.ok && res.data && res.data.is_running) {
                    this.isRunning = true;
                    this.renderAccountQueue(res.data);
                    // Badge DOM exists now (renderActivitiesForGroup was called in loadGroupsData)
                    this._updateActivityStatuses(res.data);
                } else {
                    this.isRunning = false;
                }
            } catch (e) { console.error("Error fetching bot status", e); }
        }
    },

    // setupWebSocket is handled by the real implementation further down in this object.
    // The real setupWebSocket() at ~L1947 registers all wsClient.on() listeners.

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
        const stsPane = document.getElementById('acv-rtab-status');

        const btnLog = document.getElementById('acv-rtab-btn-log');
        const btnCfg = document.getElementById('acv-rtab-btn-config');
        const btnSts = document.getElementById('acv-rtab-btn-status');

        if (logPane) logPane.style.display = (tab === 'log') ? '' : 'none';
        if (cfgPane) cfgPane.style.display = (tab === 'config') ? '' : 'none';
        if (stsPane) stsPane.style.display = (tab === 'status') ? '' : 'none';

        if (btnLog) btnLog.classList.toggle('active', tab === 'log');
        if (btnCfg) btnCfg.classList.toggle('active', tab === 'config');
        if (btnSts) btnSts.classList.toggle('active', tab === 'status');
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
        if (!this.di) await this._initDI();
        const res = await this.di.workflowRepo.getFunctions();
        this.functions = res.ok ? res.data : [];
        if (!res.ok) console.error('Failed to fetch functions:', res.error);
    },

    async fetchTemplates() {
        if (!this.di) await this._initDI();
        const res = await this.di.workflowRepo.getTemplates();
        this.templates = res.ok ? res.data : [];
        if (!res.ok) console.error('Failed to fetch templates:', res.error);
    },

    async fetchRecipes() {
        if (!this.di) await this._initDI();
        const res = await this.di.workflowRepo.getRecipes();
        this.recipes = res.ok ? res.data : [];
        if (!res.ok) console.error('Failed to fetch recipes:', res.error);
    },

    async fetchEmulators() {
        if (!this.di) await this._initDI();
        const res = await this.di.emuRepo.getAll();

        if (!res.ok) {
            console.error('Failed to fetch emulators:', res.error);
            return;
        }

        const select = document.getElementById('wf-emu-select');
        if (select) {
            const online = res.data.filter(e => e.running === true || e.is_running === true);
            if (online.length === 0) {
                select.innerHTML = '<option value="">(No devices online)</option>';
            } else {
                select.innerHTML = '<option value="">Select Emulator...</option>' +
                    online.map(e => `<option value="${e.index}">${e.name} (Idx ${e.index})</option>`).join('');
            }
        }
    },

    // ── ACCOUNT GROUPS LOGIC ──
    groupsData: [],
    accountsData: [],
    currentGroupId: null,

    // ── ACTIVITY TAB STATE ──
    activitySelectedGroupId: null,

    async loadGroupsData() {
        if (!this.di) await this._initDI();
        const res = await this.di.groupRepo.getAll();

        if (res.ok) {
            this.groupsData = res.data;
            this.renderGroupList();
            await this.updateActivityGroupList();

            if (!this.accountsData || this.accountsData.length === 0) {
                await this.loadAccountsData();
            }
        } else {
            console.error('Failed to load groups:', res.error);
        }
    },

    async loadRegistry() {
        if (!this.di) await this._initDI();
        const res = await this.di.configRepo.getRegistry();

        if (res.ok) {
            this._systemActivities = res.data;
        } else {
            console.error('Failed to load activity registry:', res.error);
            // Fallback for offline UI testing
            this._systemActivities = [
                { id: 'gather_rss_center', name: 'Gather Resource Center', defaults: {} },
                { id: 'gather_resource', name: 'Gather Resource', defaults: {}, config_fields: [{ key: 'resource_type', default: 'wood' }] },
                { id: 'full_scan', name: 'Full Scan', defaults: {} },
                { id: 'catch_pet', name: 'Catch Pet', defaults: {} }
            ];
        }
    },

    async loadAccountsData() {
        if (!this.di) await this._initDI();
        const res = await this.di.accountRepo.getAll();

        if (res.ok) {
            this.accountsData = res.data;
        } else {
            console.error('Failed to load accounts:', res.error);
            this.accountsData = [];
        }
    },

    async updateActivityGroupList() {
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
                <div class="acv-group-item ${isSelected ? 'active' : ''}" onclick="WF3.toggleActivityGroup(${g.id}, true)">
                    <span class="acv-group-status-dot" id="grp-status-${g.id}" data-status="idle" title="Idle">⚪</span>
                    <span class="acv-group-item-name">${g.name}</span>
                    <span class="acv-chip-count">${accs.length}</span>
                </div>
            `;
        }).join('');

        // Fetch and render group statuses
        this._pollGroupStatuses();

        // Force trigger toggle to load backend config + render properties (Fix: even if loaded from localStorage)
        if (this.groupsData.length > 0) {
            // Verify the cached ID actually exists, fallback to first index if deleted
            let targetId = this.activitySelectedGroupId;
            if (!this.groupsData.find(g => g.id === targetId)) {
                targetId = this.groupsData[0].id;
            }
            await this.toggleActivityGroup(targetId, true);
        }
    },

    async toggleActivityGroup(groupId, checked) {
        if (checked) {
            this.activitySelectedGroupId = groupId;
            localStorage.setItem('wf_selected_group_id', groupId); // BUG 3 FIX: Persist selection

            // Deselect all, then activate clicked one
            document.querySelectorAll('.acv-group-item').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.acv-group-item').forEach(el => {
                if (el.getAttribute('onclick')?.includes(`(${groupId},`)) {
                    el.classList.add('active');
                }
            });
            // Load saved config from backend (syncs to localStorage)
            await this._loadConfigFromBackend(groupId);
            // Reset config panel to avoid stale groupId bindings
            const cfgPanel = document.getElementById('acv-config-panel');
            if (cfgPanel) cfgPanel.innerHTML = '<div class="acv-empty-hint">Select an activity to view its config.</div>';
        } else {
            this.activitySelectedGroupId = null;
            localStorage.removeItem('wf_selected_group_id');
            document.querySelectorAll('.acv-group-item').forEach(el => el.classList.remove('active'));
        }
        this.renderActivitiesForGroup(this.activitySelectedGroupId);
        this.renderMiscForGroup(this.activitySelectedGroupId);

        // Fetch status for this group in case it's running
        if (this.activitySelectedGroupId) {
            try {
                if (!this.di) await this._initDI();
                const res = await this.di.botRepo.getStatus(this.activitySelectedGroupId);
                if (res.ok && res.data && res.data.is_running) {
                    this.isRunning = true;
                    this.renderAccountQueue(res.data);
                } else {
                    this.isRunning = false;
                }
            } catch (e) { }
        }
    },

    // ── Unified Config Handling (v2 Schema) ──

    getActivityConfig(groupId) {
        if (!groupId) return [];
        // Extract basic enabled flag state for dynamic list render from v2 schema
        const conf = this._groupConfigs[groupId] || { activities: {} };

        return this._systemActivities.map(sys => {
            const actConf = conf.activities[sys.id] || {};
            return {
                id: sys.id,
                name: sys.name,
                description: sys.description,
                enabled: !!actConf.enabled
            };
        });
    },

    saveActivityConfig(groupId) {
        if (!groupId) return;
        const items = document.querySelectorAll('#wf-act-dynamic-list .wf-act-group-cb');

        // Update local memory cache first
        if (!this._groupConfigs[groupId]) this._groupConfigs[groupId] = { version: 2, activities: {}, misc: { cooldown_min: 30, limit_min: 45 } };

        items.forEach(cb => {
            const id = cb.dataset.id;
            if (!this._groupConfigs[groupId].activities[id]) {
                this._groupConfigs[groupId].activities[id] = { enabled: false, config: {}, cooldown_enabled: false, cooldown_minutes: 60 };
            }
            this._groupConfigs[groupId].activities[id].enabled = cb.checked;
        });

        // Save to backend (async, non-blocking)
        this._saveConfigToBackend(groupId);
    },

    getMiscConfig(groupId) {
        const defaultMisc = { cooldown_min: 30, limit_min: 45, choose_start_account: false };
        if (!groupId) return defaultMisc;
        const conf = this._groupConfigs[groupId];
        if (conf && conf.misc) {
            return { ...defaultMisc, ...conf.misc };
        }
        return defaultMisc;
    },

    saveMiscConfig(groupId) {
        if (!groupId) return;
        const cdEl = document.getElementById('misc-cooldown-min');
        const limitEl = document.getElementById('misc-limit-min');
        const chooseStartEl = document.getElementById('misc-choose-start-account');

        if (!this._groupConfigs[groupId]) this._groupConfigs[groupId] = { version: 2, activities: {}, misc: {} };

        this._groupConfigs[groupId].misc = {
            cooldown_min: cdEl ? parseInt(cdEl.value) || 0 : 30,
            limit_min: limitEl ? parseInt(limitEl.value) || 0 : 45,
            choose_start_account: chooseStartEl ? chooseStartEl.checked : false
        };

        this._saveConfigToBackend(groupId);
    },

    async _saveConfigToBackend(groupId) {
        if (!this.di) await this._initDI();
        if (!this._groupConfigs[groupId]) return;

        const payload = this._groupConfigs[groupId];
        const result = await this.di.saveConfig.execute(groupId, payload);

        if (!result.ok) {
            console.warn('Failed to save config to backend:', result.error);
        }
    },

    async _loadConfigFromBackend(groupId) {
        if (!this.di) await this._initDI();

        const result = await this.di.configRepo.loadConfig(groupId);
        if (result.ok) {
            this._groupConfigs[groupId] = result.data;
        } else {
            console.warn('Failed to load config from backend:', result.error);
        }

        // Fallback default
        if (!this._groupConfigs[groupId]) {
            this._groupConfigs[groupId] = { version: 2, activities: {}, misc: { cooldown_min: 30, limit_min: 45 } };
        }
        return this._groupConfigs[groupId];
    },

    // ── Cooldown helpers ──
    _getLastRun(activityId, groupId) {
        const conf = this._groupConfigs[groupId];
        if (conf && conf.activities && conf.activities[activityId]) {
            const lastRun = conf.activities[activityId].last_run;
            return lastRun ? new Date(lastRun).getTime() : 0;
        }
        return 0;
    },
    _setLastRun(activityId, groupId) {
        if (!this._groupConfigs[groupId]) return;
        if (!this._groupConfigs[groupId].activities[activityId]) {
            this._groupConfigs[groupId].activities[activityId] = {};
        }
        this._groupConfigs[groupId].activities[activityId].last_run = new Date().toISOString();
        this._saveConfigToBackend(groupId); // Save immediately
    },
    _isOnCooldown(activityId, groupId) {
        const cfg = this.getPerActivityConfig(activityId, groupId);
        if (!cfg.cooldown_enabled) return false;
        const cdMinutes = cfg.cooldown_minutes || 0;
        if (cdMinutes <= 0) return false;
        const lastRun = this._getLastRun(activityId, groupId);
        if (!lastRun) return false;
        const elapsedMs = Date.now() - lastRun;
        return elapsedMs < cdMinutes * 60 * 1000;
    },
    _formatCooldownRemaining(activityId, groupId) {
        const cfg = this.getPerActivityConfig(activityId, groupId);
        const cdMinutes = cfg.cooldown_minutes || 0;
        const lastRun = this._getLastRun(activityId, groupId);
        if (!lastRun || cdMinutes <= 0) return '';
        const remainMs = (cdMinutes * 60 * 1000) - (Date.now() - lastRun);
        if (remainMs <= 0) return '';
        const h = Math.floor(remainMs / 3600000);
        const m = Math.floor((remainMs % 3600000) / 60000);
        return h > 0 ? `${h}h ${m}m remaining` : `${m}m remaining`;
    },

    // ── Session timer ──
    _botSessionStart: null,
    _sessionTimerInterval: null,
    _startSessionTimer() {
        this._botSessionStart = Date.now();
        localStorage.setItem('wf_session_start', this._botSessionStart.toString());
        this._updateSessionTimerDisplay();
        if (this._sessionTimerInterval) clearInterval(this._sessionTimerInterval);
        this._sessionTimerInterval = setInterval(() => this._updateSessionTimerDisplay(), 10000);
    },
    _updateSessionTimerDisplay() {
        const el = document.getElementById('misc-session-timer');
        const liveSessionEl = document.getElementById('wf-live-session-time');
        const liveCooldownEl = document.getElementById('wf-live-cooldown');

        // ── Session Time ──
        if (this._botSessionStart) {
            const elapsed = Date.now() - this._botSessionStart;
            const h = Math.floor(elapsed / 3600000);
            const m = Math.floor((elapsed % 3600000) / 60000);
            const s = Math.floor((elapsed % 60000) / 1000);

            const mStr = m.toString().padStart(2, '0');
            const sStr = s.toString().padStart(2, '0');
            const hrStr = h > 0 ? h.toString().padStart(2, '0') + ':' : '00:';

            if (liveSessionEl) liveSessionEl.textContent = `${hrStr}${mStr}:${sStr}`;
            if (el) el.textContent = `⏱ Session: ${m}m ${s}s elapsed`;
        } else {
            if (liveSessionEl) liveSessionEl.textContent = '00:00:00';
            if (el) el.textContent = '';
        }

        // ── Cooldown Display ──
        if (liveCooldownEl && this.activitySelectedGroupId) {
            const config = this.getActivityConfig(this.activitySelectedGroupId);
            let cdTexts = [];
            config.forEach(act => {
                if (act.enabled) {
                    const cdFormat = this._formatCooldownRemaining(act.id, this.activitySelectedGroupId);
                    if (cdFormat) cdTexts.push(`<div><span style="color:var(--text-muted)">${act.name}:</span> ${cdFormat}</div>`);
                }
            });
            if (cdTexts.length > 0) {
                liveCooldownEl.innerHTML = cdTexts.join('');
            } else {
                liveCooldownEl.textContent = '--:--';
            }
        }
    },

    // Run enabled activities for selected group via bot API
    async runBotActivities() {
        if (!this.di) await this._initDI();

        const groupId = this.activitySelectedGroupId;
        if (!groupId) {
            WfToast.show('w', 'No Group', 'Select a target group first.');
            return;
        }

        const misc = this.getMiscConfig(groupId);
        if (misc.choose_start_account) {
            await this.showAccountSelectionModal(groupId);
            return; // Execution will continue after user selection
        }

        this._executeRunBotActivities(groupId, null);
    },

    async showAccountSelectionModal(groupId) {
        if (!this.di) await this._initDI();

        const groupResult = await this.di.groupRepo.getById(groupId);
        if (!groupResult.ok) return;
        const group = groupResult.data;

        let accountIds = [];
        try { accountIds = JSON.parse(group.account_ids || '[]'); } catch (e) { }

        // Fetch all accounts dynamically since workflow.js might not have loaded them
        let allAccounts = [];
        const accountsResult = await this.di.accountRepo.getAll();
        if (accountsResult.ok) {
            allAccounts = accountsResult.data;
        }

        const accountsInGroup = accountIds
            .map(id => allAccounts.find(a => a.account_id == id))
            .filter(a => a != null);

        // Sort matching orchestrator queue (emu_index ascending)
        accountsInGroup.sort((a, b) => (a.emu_index || 999) - (b.emu_index || 999));

        let modal = document.getElementById('wf-account-start-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'wf-account-start-modal';
            modal.className = 'wf-fn-overlay';
            document.body.appendChild(modal);
        }

        let accountHtml = accountsInGroup.map(a => `
            <div class="wf-sidebar-fn" style="border: 1px solid var(--border); margin-bottom: 8px; border-radius: 6px; padding: 12px; cursor: pointer; transition: all 0.2s;" 
                 onmouseover="this.style.borderColor='var(--indigo-500)'; this.style.backgroundColor='var(--accent)'"
                 onmouseout="this.style.borderColor='var(--border)'; this.style.backgroundColor='transparent'"
                 onclick="WF3._executeRunBotActivities(${groupId}, ${a.account_id}); document.getElementById('wf-account-start-modal').classList.remove('visible');">
                <div class="wf-sidebar-fn-icon" style="font-size: 18px;">👤</div>
                <div style="flex:1;">
                    <div class="wf-sidebar-fn-name" style="font-size: 14px; margin-bottom: 4px;">${a.lord_name || 'Unknown'} <span style="color:var(--muted-foreground); font-size:11px;">(ID: ${a.account_id})</span></div>
                    <div class="wf-sidebar-fn-desc" style="font-size: 12px;">🖥 Emu index: ${a.emu_index != null ? a.emu_index : '--'} | 🕒 Last Run: N/A</div>
                </div>
                <button style="padding: 6px 14px; font-size: 12px; font-weight: 600; border: 1px solid var(--indigo-500); background: transparent; color: var(--indigo-500); border-radius: 4px; flex-shrink:0; cursor:pointer;" 
                        onmouseover="this.style.background='rgba(99,102,241,0.1)'" onmouseout="this.style.background='transparent'">
                    Run First
                </button>
            </div>
        `).join('');

        modal.innerHTML = `
            <div class="wf-fn-picker" style="width: 520px; padding: 24px;">
                <div style="display:flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h3 style="margin:0; font-size: 16px; font-weight: 700;">Select Starting Account</h3>
                    <button onclick="document.getElementById('wf-account-start-modal').classList.remove('visible')" 
                            style="background:none; border:none; cursor:pointer; font-size:16px; color:var(--muted-foreground); padding: 4px; border-radius: 4px;">✕</button>
                </div>
                <div style="font-size: 13px; color: var(--muted-foreground); margin-bottom: 20px; line-height: 1.5;">
                    The queue is ordered by Emulator to minimize switching. Choosing an account starts the loop from that position in the queue.
                </div>
                <div style="max-height: 50vh; overflow-y: auto; padding-right: 6px;">
                    ${accountHtml || '<div style="text-align:center; padding: 30px; color:var(--muted-foreground); border: 1px dashed var(--border); border-radius: 8px;">No accounts found in this group.</div>'}
                </div>
            </div>
        `;

        modal.classList.add('visible');
    },

    async _executeRunBotActivities(groupId, startAccountId) {
        // Switch to Log tab to show output
        this.switchRightTab('log');
        this._startSessionTimer();
        this.addBotLog('info', `Starting activities for group '${groupId}'...`);

        // Execute via Application Service
        const result = await this.di.runBot.execute(groupId, this._systemActivities, startAccountId);

        if (!result.ok) {
            const err = result.error.message;
            if (err === 'NO_ACTIVITIES') {
                WfToast.show('w', 'No Activities', 'Enable at least one activity first.');
            } else if (err === 'ALL_ON_COOLDOWN') {
                WfToast.show('w', 'All on Cooldown', 'All enabled activities are still on cooldown.');
                this.addBotLog('warn', '⏳ No activities ready. All on cooldown.');
            } else if (err === 'ALREADY_RUNNING') {
                this.addBotLog('warn', '⚠ Bot is already running for this group.');
                WfToast.show('w', 'Already Running', 'Bot is already running for this group.');
            } else {
                this.addBotLog('err', `✕ Error: ${err}`);
                WfToast.show('e', 'Error', err);
            }
            return;
        }

        // Handle success response
        const { response, skippedLogs, readyActivities } = result.data;

        // Print skipped logs
        skippedLogs.forEach(log => this.addBotLog('warn', log));

        if (response.status === 'started') {
            this.addBotLog('ok', `✓ Sequential Bot started for Group ${groupId} (${response.accounts_queued} accounts)`);
            WfToast.show('s', 'Bot Started', `Queued ${response.accounts_queued} accounts`);
            // Record last_run for all activities that were sent
            for (const act of readyActivities) {
                this._setLastRun(act.id, groupId);
            }
        }
    },

    // Optional: Stop the bot
    async stopBotActivities() {
        if (!this.di) await this._initDI();

        const groupId = this.activitySelectedGroupId;
        if (!groupId) return;

        const result = await this.di.stopBot.execute(groupId);
        if (result.ok) {
            this.addBotLog('warn', `🛑 Stop requested. Bot will halt after current account finishes.`);
            WfToast.show('i', 'Stopping', 'Bot will stop soon.');
        } else {
            console.error("Failed to stop bot", result.error);
        }
    },

    // Render the account queue sent by WS `bot_queue_update`
    renderAccountQueue(queueData) {
        // Find or create queue container in the right panel
        let container = document.getElementById('wf-account-queue-container');
        if (!container) {
            const logPane = document.getElementById('acv-rtab-log');
            if (!logPane) return;

            container = document.createElement('div');
            container.id = 'wf-account-queue-container';
            container.className = 'acv-queue-container';
            logPane.insertBefore(container, logPane.firstChild);
        }

        if (!queueData.is_running && !queueData.stop_requested) {
            container.innerHTML = `<div class="acv-queue-header">Bot Stopped</div>`;
            return;
        }

        let html = `<div class="acv-queue-header">
            Sequential Execution Queue (Cycle ${queueData.cycle})
            ${queueData.stop_requested ? '<span style="color:red; font-size:12px;">(Stopping...)</span>' : ''}
        </div>
        <div class="acv-queue-list">`;

        queueData.accounts.forEach((acc, i) => {
            const isCurrent = parseInt(queueData.current_idx) === i;
            // status can be pending, running, done, error
            let statusIcon = '⏳';
            let statusClass = 'pending';
            if (acc.status === 'running') { statusIcon = '🔄'; statusClass = 'running'; }
            if (acc.status === 'done') { statusIcon = '✅'; statusClass = 'done'; }
            if (acc.status === 'error') { statusIcon = '❌'; statusClass = 'error'; }

            html += `
                <div class="acv-queue-item ${isCurrent ? 'active' : ''} status-${statusClass}">
                    <span class="acv-q-icon">${statusIcon}</span>
                    <span class="acv-q-name">${acc.lord_name} (Emu ${acc.emu_index})</span>
                </div>
            `;
        });

        html += `</div>`;
        container.innerHTML = html;

        // BUG 2 FIX: Update individual activity statuses
        this._updateActivityStatuses(queueData);
    },

    // ── Per-Activity Status Updates ──
    _latestActivityStatuses: null,

    _updateActivityStatuses(queueData) {
        if (!queueData) return;

        // BUG 1 FIX: Server now sends per-activity breakdown in activity_statuses
        const statuses = queueData.activity_statuses || {};
        this._latestActivityStatuses = statuses;

        // We only update badges for the currently selected group's list
        const config = this.getActivityConfig(this.activitySelectedGroupId);
        const enabledIds = config.filter(c => c.enabled).map(c => c.id);

        enabledIds.forEach(id => {
            const badge = document.getElementById(`acv-status-${id}`);
            if (badge) {
                // If bot is fully stopped, default back to N/A, else fallback to pending
                let statusVal = 'na';
                if (queueData.is_running || queueData.stop_requested) {
                    statusVal = statuses[id] || 'pending';
                }

                let text = 'N/A';
                if (statusVal === 'pending') text = 'Queued';
                if (statusVal === 'running') text = 'Running';
                if (statusVal === 'done') text = 'Done';
                if (statusVal === 'error') text = 'Error';
                if (statusVal === 'skipped') text = 'Skipped';

                // Allow "stopping" override if it was running
                if (queueData.stop_requested && statusVal === 'running') {
                    text = 'Stopping';
                }

                badge.textContent = text;
                badge.setAttribute('data-status', statusVal);
                badge.className = 'acv-activity-status';
                badge.classList.add(`status-${statusVal}`);
            }
        });

        // ── BUG 3 FIX: Update Live Status pane metrics ──
        const liveStatusEl = document.getElementById('wf-live-status-text');
        const liveActivityEl = document.getElementById('wf-live-activity-name');

        if (liveStatusEl && liveActivityEl) {
            if (!queueData.is_running && !queueData.stop_requested) {
                liveStatusEl.textContent = 'Idle';
                liveStatusEl.style.color = 'var(--text)';
                liveActivityEl.textContent = 'Waiting for bot to start...';
            } else if (queueData.stop_requested) {
                liveStatusEl.textContent = 'Stopping';
                liveStatusEl.style.color = 'var(--red-500)';
                liveActivityEl.textContent = 'Finishing current step...';
            } else {
                liveStatusEl.textContent = 'Running Emulator';
                liveStatusEl.style.color = 'var(--emerald-500)';
                const currAct = queueData.current_activity;
                if (currAct && currAct.name) {
                    liveActivityEl.textContent = `${currAct.name} (${currAct.status || 'running'})`;
                } else {
                    liveActivityEl.textContent = 'Executing workflow...';
                }
            }
        }
    },

    // Polls /api/bot/status (no group_id) to get all group statuses
    async _pollGroupStatuses() {
        try {
            if (!this.di) await this._initDI();
            const res = await this.di.botRepo.getStatus();
            if (res.ok && res.data) {
                for (const [gid, info] of Object.entries(res.data)) {
                    this._updateGroupStatusBadge(parseInt(gid), info);
                }
            }
        } catch (e) { console.warn('Failed to poll group statuses:', e); }
    },

    // Updates a single group's status dot in the Target Group list
    _updateGroupStatusBadge(groupId, statusInfo) {
        const dot = document.getElementById(`grp-status-${groupId}`);
        if (!dot) return;

        if (statusInfo.is_running && statusInfo.all_on_cooldown) {
            dot.textContent = '🟡';
            dot.setAttribute('data-status', 'cooldown');
            dot.title = 'Cooldown';
        } else if (statusInfo.is_running) {
            dot.textContent = '🟢';
            dot.setAttribute('data-status', 'running');
            dot.title = 'Running';
        } else {
            dot.textContent = '⚪';
            dot.setAttribute('data-status', 'idle');
            dot.title = 'Idle';
        }
    },

    // Add a log line to Activity Log console
    addBotLog(type, message) {
        const ts = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

        // Persist to memory
        if (!this._botLogs) this._botLogs = [];
        this._botLogs.push({ ts, type, message });

        // Keep memory bounded to last 500 logs
        if (this._botLogs.length > 500) this._botLogs.shift();

        const consoleEl = document.getElementById('wf-activity-console');
        if (!consoleEl) return;

        const line = document.createElement('div');
        line.className = `acv-log-line acv-log-${type}`;
        line.innerHTML = `<span class="acv-log-ts">[${ts}]</span> ${message}`;
        consoleEl.appendChild(line);
        consoleEl.scrollTop = consoleEl.scrollHeight;
    },

    // Restores logs to DOM after UI reset
    _replayLogs() {
        const consoleEl = document.getElementById('wf-activity-console');
        if (!consoleEl || !this._botLogs) return;

        // Clear container completely to avoid duplicates if called multiple times
        consoleEl.innerHTML = '';

        const frag = document.createDocumentFragment();
        this._botLogs.forEach(log => {
            const line = document.createElement('div');
            line.className = `acv-log-line acv-log-${log.type}`;
            line.innerHTML = `<span class="acv-log-ts">[${log.ts}]</span> ${log.message}`;
            frag.appendChild(line);
        });

        consoleEl.appendChild(frag);
        consoleEl.scrollTop = consoleEl.scrollHeight;
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
            container.innerHTML = '<div class="acv-empty-hint">Select a group to configure its activities.</div>';
            return;
        }

        const config = this.getActivityConfig(groupId);
        container.innerHTML = config.map((item, idx) => {
            // Restore status from memory cache if active, else NA
            let statusVal = 'na';
            let statusText = 'N/A';

            if (this.isRunning && this._latestActivityStatuses && item.enabled) {
                statusVal = this._latestActivityStatuses[item.id] || 'pending';
                if (statusVal === 'pending') statusText = 'Queued';
                if (statusVal === 'running') statusText = 'Running';
                if (statusVal === 'done') statusText = 'Done';
                if (statusVal === 'error') statusText = 'Error';
                if (statusVal === 'skipped') statusText = 'Skipped';
            }

            return `
            <div class="acv-activity-row ${item.enabled ? 'enabled' : ''}" id="acv-row-${idx}">
                <label class="acv-check-label" style="cursor:pointer;" onclick="event.stopPropagation()">
                    <input type="checkbox" class="wf-act-group-cb" data-name="${item.name.replace(/'/g, "\\'")}" data-id="${item.id}" data-idx="${idx}" ${item.enabled ? 'checked' : ''}
                        onchange="WF3.saveActivityConfig(${groupId}); this.closest('.acv-activity-row').classList.toggle('enabled', this.checked)">
                    <span class="acv-check-box"></span>
                </label>
                <div class="acv-activity-info" style="flex:1; cursor:pointer; padding:4px 0;" onclick="WF3.selectActivity('${item.id}', ${groupId}, this)">
                    <span class="acv-activity-name">${item.name}</span>
                    <span class="acv-activity-desc" style="display:block; font-size:11px; color:var(--muted-foreground); margin-top:2px;">${item.description || ''}</span>
                </div>
                <span class="acv-activity-status status-${statusVal}" id="acv-status-${item.id}" data-status="${statusVal}">${statusText}</span>
                <button class="acv-cfg-btn" title="Configure" onclick="WF3.showActivityConfig('${item.id}', ${groupId})">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 0-14.14 0M3.51 9a10 10 0 0 0 0 6M20.49 9a10 10 0 0 0 0 6M4.93 19.07a10 10 0 0 0 14.14 0"/></svg>
                </button>
            </div>
            `;
        }).join('');
    },

    renderMiscForGroup(groupId) {
        const container = document.getElementById('wf-act-dynamic-misc-list');
        if (!container) return;

        if (!groupId) {
            container.innerHTML = '<div class="acv-empty-hint">Select a group to configure its Misc settings.</div>';
            return;
        }

        const misc = this.getMiscConfig(groupId);

        container.innerHTML = `
            <div class="acv-misc-item" style="border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 16px;">
                <div style="font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                    <span>⏳</span> Account Cooldown
                </div>
                <div style="font-size: 13px; color: var(--muted-foreground); margin-bottom: 12px; line-height: 1.4;">
                    Wait before re-running an account that recently finished (prevents rapid re-logins).
                </div>
                <div>
                    <input type="number" class="acv-input-num" id="misc-cooldown-min" value="${misc.cooldown_min}" onchange="WF3.saveMiscConfig(${groupId})" style="width: 60px;"> minute(s)
                </div>
            </div>
            
            <div class="acv-misc-item" style="border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 16px;">
                <div style="font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                    <span>⏱</span> Time Limit
                </div>
                <div style="font-size: 13px; color: var(--muted-foreground); margin-bottom: 12px; line-height: 1.4;">
                    Force swap to next account after this much time total, whether activities are finished or not.
                </div>
                <div>
                    <input type="number" class="acv-input-num" id="misc-limit-min" value="${misc.limit_min}" onchange="WF3.saveMiscConfig(${groupId})" style="width: 60px;"> minute(s)
                </div>
            </div>
            
            <div class="acv-misc-item">
                <label style="display: flex; align-items: flex-start; gap: 10px; cursor: pointer;">
                    <input type="checkbox" id="misc-choose-start-account" onchange="WF3.saveMiscConfig(${groupId})" ${misc.choose_start_account ? 'checked' : ''} style="margin-top: 3px;">
                    <div>
                        <div style="font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 8px;">
                            <span>🎯</span> Choose Account to Run First
                        </div>
                        <div style="font-size: 13px; color: var(--muted-foreground); line-height: 1.4;">
                            When starting the bot, prompt to select which account should be executed first.
                        </div>
                    </div>
                </label>
            </div>
        `;
    },

    // Update status badge for a specific activity
    updateActivityStatus(activityId, status) {
        const el = document.getElementById(`acv-status-${activityId}`);
        if (!el) return;
        el.dataset.status = status;
        const labels = { running: 'Running', done: 'Done', error: 'Error', na: 'N/A' };
        el.textContent = labels[status] || 'N/A';
    },

    getPerActivityConfig(activityId, groupId) {
        const sys = this._systemActivities.find(a => a.id === activityId);
        if (!sys) return {};

        const conf = this._groupConfigs[groupId] || { activities: {} };
        const actConf = conf.activities[activityId] || {};

        // Start with system defaults from registry
        const defaults = { ...sys.defaults };
        if (sys.config_fields) {
            sys.config_fields.forEach(f => {
                if (f.default !== undefined) defaults[f.key] = f.default;
            });
        }

        // Merge with saved config payload
        const userPayload = actConf.config || {};

        return {
            ...defaults,
            ...userPayload,
            cooldown_enabled: actConf.cooldown_enabled ?? defaults.cooldown_enabled,
            cooldown_minutes: actConf.cooldown_minutes ?? defaults.cooldown_minutes,
            last_run: actConf.last_run || null
        };
    },

    savePerActivityConfig(activityId, groupId) {
        const panel = document.getElementById('acv-config-panel');
        if (!panel) return;

        if (!this._groupConfigs[groupId]) this._groupConfigs[groupId] = { version: 2, activities: {}, misc: {} };
        if (!this._groupConfigs[groupId].activities[activityId]) {
            this._groupConfigs[groupId].activities[activityId] = { enabled: false, config: {}, cooldown_enabled: false, cooldown_minutes: 60 };
        }

        const actConf = this._groupConfigs[groupId].activities[activityId];
        actConf.config = actConf.config || {};

        panel.querySelectorAll('[data-cfgkey]').forEach(el => {
            const key = el.dataset.cfgkey;
            const val = el.type === 'checkbox' ? el.checked : (el.type === 'number' ? +el.value : el.value);

            // Map top-level cooldown fields to their proper places
            if (key === 'cooldown_enabled' || key === 'cooldown_minutes') {
                actConf[key] = val;
            } else {
                actConf.config[key] = val;
            }
        });

        this._saveConfigToBackend(groupId);
        WfToast.show('s', 'Saved', 'Configuration saved.');
    },

    // Click on activity name → highlight row + open config
    selectActivity(activityId, groupId, el) {
        // Remove 'selected' from all rows, add to clicked one
        document.querySelectorAll('.acv-activity-row').forEach(r => r.classList.remove('selected'));
        const row = el.closest('.acv-activity-row');
        if (row) row.classList.add('selected');
        // Open config panel for this activity
        this.showActivityConfig(activityId, groupId);
    },

    showActivityConfig(activityId, groupId) {
        // Switch to config tab
        this.switchRightTab('config');

        const panel = document.getElementById('acv-config-panel');
        if (!panel) return;

        const sys = this._systemActivities.find(a => a.id === activityId);
        if (!sys) return;

        const activityName = sys.name;
        const defs = sys.config_fields || [];
        const saved = this.getPerActivityConfig(activityId, groupId);

        // Build activity-specific fields
        const fieldsHtml = defs.map(d => {
            const val = saved[d.key] !== undefined ? saved[d.key] : d.default;
            if (d.type === 'checkbox') {
                return `
                <div class="acv-cfg-field">
                    <label class="acv-check-label" style="gap:10px;">
                        <input type="checkbox" data-cfgkey="${d.key}" ${val ? 'checked' : ''} onchange="WF3.savePerActivityConfig('${activityId}',${groupId})">
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
                    <select class="acv-cfg-select" data-cfgkey="${d.key}" onchange="WF3.savePerActivityConfig('${activityId}',${groupId})">${opts}</select>
                </div>`;
            }
            return `
            <div class="acv-cfg-field">
                <label class="acv-cfg-label">${d.label}</label>
                <input type="number" class="acv-cfg-input" data-cfgkey="${d.key}" value="${val}" ${d.min !== undefined ? 'min="' + d.min + '"' : ''} ${d.max !== undefined ? 'max="' + d.max + '"' : ''} onchange="WF3.savePerActivityConfig('${activityId}',${groupId})">
            </div>`;
        }).join('');

        // Cooldown section (always shown)
        const cdEnabled = saved.cooldown_enabled || false;
        const cdMinutes = saved.cooldown_minutes !== undefined ? saved.cooldown_minutes : 60;
        const lastRun = this._getLastRun(activityId, groupId);
        const lastRunStr = lastRun ? new Date(lastRun).toLocaleString() : 'Never';
        const cooldownStatus = this._isOnCooldown(activityId, groupId)
            ? `<span style="color:var(--amber-500)">⏳ ${this._formatCooldownRemaining(activityId, groupId)}</span>`
            : (lastRun ? '<span style="color:var(--emerald-500)">✓ Ready</span>' : '');

        const cooldownHtml = `
            <div class="acv-cfg-divider"></div>
            <div class="acv-cfg-section-title">Cooldown</div>
            <div class="acv-cfg-field">
                <label class="acv-check-label" style="gap:10px;">
                    <input type="checkbox" data-cfgkey="cooldown_enabled" ${cdEnabled ? 'checked' : ''} onchange="WF3.savePerActivityConfig('${activityId}',${groupId})">
                    <span class="acv-check-box"></span>
                    <span>After script completing put it on cooldown</span>
                </label>
            </div>
            <div class="acv-cfg-field" style="flex-direction:row; align-items:center; gap:10px;">
                <label class="acv-cfg-label" style="margin:0; white-space:nowrap;">Put on cooldown for</label>
                <input type="number" class="acv-cfg-input" data-cfgkey="cooldown_minutes" value="${cdMinutes}" min="1" max="9999" style="width:80px;" onchange="WF3.savePerActivityConfig('${activityId}',${groupId})">
                <span style="font-size:12px; color:var(--muted-foreground);">Minutes</span>
            </div>
            <div class="acv-cfg-field" style="flex-direction:row; align-items:center; gap:8px; font-size:11px; color:var(--muted-foreground);">
                <span>Last run: ${lastRunStr}</span>
                ${cooldownStatus}
            </div>
        `;

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
            <div class="acv-cfg-fields">
                ${fieldsHtml}
                ${cooldownHtml}
            </div>
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
        const wasInEdit = editMode && editMode.style.display !== 'none';

        if (viewMode) viewMode.style.display = 'flex';
        if (editMode) editMode.style.display = 'none';

        if (wasInEdit) {
            const cbs = document.querySelectorAll('.wf-group-account-cb:checked');
            if (cbs.length > 0 || document.querySelectorAll('.wf-group-account-cb').length > 0) {
                this._currentGroupAccountIds = Array.from(cbs).map(cb => parseInt(cb.value));
            }
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

        let selectedIds = [];
        const editMode = document.getElementById('wf-group-edit-mode');
        if (editMode && editMode.style.display !== 'none') {
            selectedIds = Array.from(document.querySelectorAll('.wf-group-account-cb:checked'))
                .map(cb => parseInt(cb.value));
            this._currentGroupAccountIds = selectedIds;
        } else {
            selectedIds = this._currentGroupAccountIds || [];
        }

        try {
            if (!this.di) await this._initDI();

            if (this.currentGroupId) {
                // Update
                const res = await this.di.groupRepo.update(this.currentGroupId, { name, account_ids: selectedIds });
                if (!res.ok) throw new Error(res.error.message || res.error);
                WfToast.show('s', 'Saved', 'Group updated successfully.');
            } else {
                // Create
                const res = await this.di.groupRepo.create({ name, account_ids: selectedIds });
                if (!res.ok) throw new Error(res.error.message || res.error);
                this.currentGroupId = res.data.id;
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
            if (!this.di) await this._initDI();

            const res = await this.di.groupRepo.delete(this.currentGroupId);
            if (!res.ok) throw new Error(res.error.message || res.error);

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

        // ── NEW: Sequential Bot Queue ──
        wsClient.on('bot_queue_update', (data) => {
            console.log('[WF3 WS] bot_queue_update received:', data.group_id, 'selected:', WF3?.activitySelectedGroupId);
            if (!WF3) return;

            // Always update group status dot (regardless of selected group)
            const groupId = data.group_id;
            const allPending = data.accounts ? data.accounts.every(a => a.status === 'pending') : false;
            WF3._updateGroupStatusBadge(groupId, {
                is_running: data.is_running,
                all_on_cooldown: data.is_running && allPending,
            });

            // Use loose equality to handle int/string mismatch
            // eslint-disable-next-line eqeqeq
            if (groupId != WF3.activitySelectedGroupId) return;

            // Update activity badges DIRECTLY (works even if queue panel isn't visible)
            WF3._updateActivityStatuses(data);

            // Also render the account queue UI if the log panel exists
            if (typeof WF3.renderAccountQueue === 'function') {
                WF3.renderAccountQueue(data);
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
