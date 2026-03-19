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
        <button class="wf-main-tab" data-view="monitor" onclick="WF3.switchMainTab('monitor')">Monitor</button>
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
        <div style="display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:10px; padding:10px 12px; border:1px solid var(--border); border-radius:var(--radius-md); background:linear-gradient(180deg, var(--surface), var(--card));">
          <div style="display:flex; flex-direction:column; gap:2px;">
            <div style="font-size:12px; color:var(--muted-foreground); font-weight:600; letter-spacing:.03em; text-transform:uppercase;">Bot Controls</div>
            <div style="font-size:13px; color:var(--foreground);">Run or stop sequential workflow for selected group</div>
          </div>
          <div style="display:flex; gap:8px;">
            <button onclick="WF3.stopBotActivities()" style="
                display:inline-flex; align-items:center; gap:5px;
                padding:7px 14px; font-size:12px; font-weight:700;
                background:#ef4444; color:white; border:none;
                border-radius:var(--radius-md); cursor:pointer;
                transition: all var(--duration-fast);
                box-shadow:0 1px 4px rgba(239, 68, 68, 0.3);
            " onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>
              Stop Bot
            </button>
            <button onclick="WF3.runBotActivities()" style="
                display:inline-flex; align-items:center; gap:5px;
                padding:7px 14px; font-size:12px; font-weight:700;
                background:#22c55e; color:white; border:none;
                border-radius:var(--radius-md); cursor:pointer;
                transition: all var(--duration-fast);
                box-shadow:0 1px 4px rgba(34,197,94,.3);
            " onmouseover="this.style.background='#16a34a'" onmouseout="this.style.background='#22c55e'">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              Start Bot
            </button>
          </div>
        </div>

        <!-- KPI SUMMARY BAR -->
        <div id="kpi-summary-bar" class="kpi-bar" style="display:none">
          <div class="kpi-card" id="kpi-fairness">
            <div class="kpi-icon">⚖️</div>
            <div class="kpi-body">
              <div class="kpi-label">Fairness</div>
              <div class="kpi-value" id="kpi-val-fairness">—</div>
            </div>
          </div>
          <div class="kpi-card" id="kpi-success">
            <div class="kpi-icon">✅</div>
            <div class="kpi-body">
              <div class="kpi-label">Success Rate</div>
              <div class="kpi-value" id="kpi-val-success">—</div>
            </div>
          </div>
          <div class="kpi-card" id="kpi-pingpong">
            <div class="kpi-icon">🔄</div>
            <div class="kpi-body">
              <div class="kpi-label">Ping-pong</div>
              <div class="kpi-value" id="kpi-val-pingpong">—</div>
            </div>
          </div>
          <div class="kpi-card" id="kpi-exectime">
            <div class="kpi-icon">⏱️</div>
            <div class="kpi-body">
              <div class="kpi-label">Execute Time</div>
              <div class="kpi-value" id="kpi-val-exectime">—</div>
            </div>
          </div>
          <div class="kpi-card" id="kpi-coverage">
            <div class="kpi-icon">📊</div>
            <div class="kpi-body">
              <div class="kpi-label">Coverage</div>
              <div class="kpi-value" id="kpi-val-coverage">—</div>
            </div>
          </div>
        </div>

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
                  <button class="acv-tab" id="acv-rtab-btn-queue" onclick="WF3.switchRightTab('queue')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></svg>
                    Queue
                  </button>
                  <button class="acv-tab" id="acv-rtab-btn-status" onclick="WF3.switchRightTab('status')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    Live Status
                  </button>
                </div>
              </div>

              <!-- Activity Log pane -->
              <div id="acv-rtab-log" class="acv-panel-body acv-log-pane">
                <div id="wf-activity-console" class="acv-console">
                  <div class="acv-log-line acv-log-info"><span class="acv-log-ts">[06:04:31]</span> Call of Dragons Bot — Ready</div>
                  <div class="acv-log-line acv-log-muted"><span class="acv-log-ts">[06:04:31]</span> Activities run top to bottom. Check/Uncheck to enable/disable.</div>
                </div>
              </div>

              <!-- Config pane -->
              <div id="acv-rtab-config" class="acv-panel-body" style="display:none">
                <div id="acv-config-panel" class="acv-config-panel">
                  <div class="acv-empty-hint">Select an activity from the left to view its config.</div>
                </div>
              </div>

              <!-- Queue pane -->
              <div id="acv-rtab-queue" class="acv-panel-body" style="display:none; padding:12px; overflow-y:auto;">
                <div id="wf-account-queue-container" class="acv-queue-container" style="background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-md); padding:10px;">
                  <div class="acv-queue-header" style="font-weight:700; color:var(--foreground); margin-bottom:8px;">Sequential Execution Queue</div>
                  <div style="font-size:12px; color:var(--muted-foreground); line-height:1.5;">Queue will appear when bot starts.</div>
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

      <!-- ==============================================================
           SECTION D: MONITOR TAB (Standalone — Real-time Bot Overview)
           ============================================================== -->
      <div id="wf-section-monitor" class="wf-section-container" style="display:none">
        <!-- MONITOR HEADER -->
        <div class="mon-header">
          <div class="mon-header-left">
            <h2 style="margin:0;font-size:16px;">Workflow Monitor</h2>
            <span id="mon-status-badge" class="mon-badge mon-badge-idle">IDLE</span>
            <span id="mon-progress" class="mon-progress" style="display:none"></span>
            <span id="mon-smart-wait" class="mon-smart-wait-badge" style="display:none"></span>
          </div>
          <div class="mon-header-right">
            <select id="mon-group-filter" class="mon-select" onchange="WF3._onMonitorGroupChange(this.value)">
              <option value="">Select Group...</option>
            </select>
            <button class="btn btn-outline btn-sm" onclick="WF3._refreshMonitor()" style="display:flex;align-items:center;gap:5px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
          </div>
        </div>

        <!-- MONITOR KPI BAR -->
        <div id="mon-kpi-bar" class="kpi-bar" style="display:none">
          <div class="kpi-card"><div class="kpi-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><path d="m8 8 4-5 4 5"/><path d="M4 14h4"/><path d="M16 14h4"/><path d="m9 18 3 3 3-3"/></svg></div><div class="kpi-body"><div class="kpi-label">Fairness</div><div class="kpi-value" id="mon-kpi-fairness">—</div></div></div>
          <div class="kpi-card"><div class="kpi-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--emerald-500)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div><div class="kpi-body"><div class="kpi-label">Success Rate</div><div class="kpi-value" id="mon-kpi-success">—</div></div></div>
          <div class="kpi-card"><div class="kpi-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--orange-500)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg></div><div class="kpi-body"><div class="kpi-label">Ping-pong</div><div class="kpi-value" id="mon-kpi-pingpong">—</div></div></div>
          <div class="kpi-card"><div class="kpi-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--blue-500)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div><div class="kpi-body"><div class="kpi-label">Exec Time</div><div class="kpi-value" id="mon-kpi-exectime">—</div></div></div>
          <div class="kpi-card"><div class="kpi-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--indigo-500)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div><div class="kpi-body"><div class="kpi-label">Coverage</div><div class="kpi-value" id="mon-kpi-coverage">—</div></div></div>
        </div>

        <!-- MONITOR 2-PANEL LAYOUT -->
        <div class="mon-layout">
          <!-- LEFT: Account Queue -->
          <div class="mon-queue-panel">
            <div class="mon-panel-title">Account Queue</div>
            <div id="mon-queue-list" class="mon-queue-list">
              <div class="mon-empty">Select a group to view accounts</div>
            </div>
          </div>
          <!-- RIGHT: Activity Detail (Tabbed) -->
          <div class="mon-detail-panel">
            <div class="mon-detail-tabs">
              <button class="mon-dtab active" data-tab="activities" onclick="WF3._switchDetailTab('activities')">Activities</button>
              <button class="mon-dtab" data-tab="logs" onclick="WF3._switchDetailTab('logs')">Recent Logs</button>
            </div>
            <div id="mon-detail-activities" class="mon-detail-content">
              <div class="mon-empty">Click an account to view activities</div>
            </div>
            <div id="mon-detail-logs" class="mon-detail-content" style="display:none">
              <div class="mon-empty">Click an account to view logs</div>
            </div>
          </div>
        </div>

        <!-- MONITOR BOTTOM TIMELINE (Collapsible) -->
        <div class="mon-timeline-wrapper">
          <button class="mon-timeline-toggle" onclick="WF3._toggleTimeline()">
            <span id="mon-tl-toggle-text">Show Timeline ▼</span>
          </button>
          <div id="mon-timeline" class="mon-timeline" style="display:none">
            <div id="mon-timeline-list" class="mon-timeline-list"></div>
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
    _currentConfigActivityId: null, // Currently open activity in right panel
    _statusPollInterval: null,
    _isStatusPollInFlight: false,

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
        this._startLiveStatusPolling();

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
        if (this._statusPollInterval) {
            clearInterval(this._statusPollInterval);
            this._statusPollInterval = null;
        }
        this._isStatusPollInFlight = false;
        if (this._sessionTimerInterval) {
            clearInterval(this._sessionTimerInterval);
            this._sessionTimerInterval = null;
        }
    },

    // ── KPI SUMMARY ──
    _kpiThrottleTimer: null,

    async _fetchKpi(groupId) {
        if (!groupId) {
            const bar = document.getElementById('kpi-summary-bar');
            if (bar) bar.style.display = 'none';
            return;
        }
        try {
            const res = await fetch(`/api/monitor/kpi-summary?group_id=${groupId}`);
            if (!res.ok) return;
            const json = await res.json();
            if (json.status === 'ok' && json.data) {
                this._renderKpi(json.data);
            }
        } catch (e) {
            console.warn('[KPI] Fetch failed:', e);
        }
    },

    _renderKpi(d) {
        const bar = document.getElementById('kpi-summary-bar');
        if (!bar) return;
        bar.style.display = '';

        const set = (id, val, colorClass) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.textContent = val;
            el.className = 'kpi-value' + (colorClass ? ' ' + colorClass : '');
        };

        // Fairness Index
        if (d.fairness_index != null) {
            const f = d.fairness_index;
            const cls = f >= 0.85 ? 'kpi-good' : f >= 0.7 ? 'kpi-warn' : 'kpi-bad';
            set('kpi-val-fairness', f.toFixed(2), cls);
        } else {
            set('kpi-val-fairness', '—');
        }

        // Success Rate
        if (d.success_rate != null) {
            const cls = d.success_rate >= 95 ? 'kpi-good' : d.success_rate >= 85 ? 'kpi-warn' : 'kpi-bad';
            set('kpi-val-success', d.success_rate.toFixed(1) + '%', cls);
        } else {
            set('kpi-val-success', '—');
        }

        // Ping-pong
        const ppCls = d.ping_pong_count === 0 ? 'kpi-good' : 'kpi-bad';
        set('kpi-val-pingpong', String(d.ping_pong_count), ppCls);

        // Execute Time %
        if (d.execute_time_pct != null) {
            const cls = d.execute_time_pct >= 65 ? 'kpi-good' : d.execute_time_pct >= 50 ? 'kpi-warn' : 'kpi-bad';
            set('kpi-val-exectime', d.execute_time_pct.toFixed(1) + '%', cls);
        } else {
            set('kpi-val-exectime', '—');
        }

        // Coverage
        if (d.cycle != null && d.coverage_pct != null) {
            set('kpi-val-coverage', `C${d.cycle} · ${d.coverage_pct.toFixed(0)}%`, 'kpi-good');
        } else if (d.total_runs_today > 0) {
            set('kpi-val-coverage', `${d.total_runs_today} runs`, '');
        } else {
            set('kpi-val-coverage', 'Idle');
        }
    },

    _scheduleKpiRefresh() {
        if (this._kpiThrottleTimer) return;
        this._kpiThrottleTimer = setTimeout(() => {
            this._kpiThrottleTimer = null;
            if (this.activitySelectedGroupId) {
                this._fetchKpi(this.activitySelectedGroupId);
            }
        }, 5000);
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
        const monitorSec = document.getElementById('wf-section-monitor');

        if (builderSec) builderSec.style.display = 'none';
        if (activitySec) activitySec.style.display = 'none';
        if (groupSec) groupSec.style.display = 'none';
        if (monitorSec) monitorSec.style.display = 'none';

        // Stop monitor timer if leaving
        if (tab !== 'monitor') this._stopMonitorTimer();

        if (tab === 'builder') {
            if (builderSec) builderSec.style.display = 'block';
        } else if (tab === 'activity') {
            if (activitySec) { activitySec.style.display = 'flex'; activitySec.style.flexDirection = 'column'; }
            this.loadGroupsData();
            this._startLiveStatusPolling();
        } else if (tab === 'group') {
            if (groupSec) groupSec.style.display = 'block';
            this.loadGroupsData();
        } else if (tab === 'monitor') {
            if (monitorSec) { monitorSec.style.display = 'flex'; monitorSec.style.flexDirection = 'column'; }
            this._initMonitorTab();
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
        const quePane = document.getElementById('acv-rtab-queue');
        const stsPane = document.getElementById('acv-rtab-status');

        const btnLog = document.getElementById('acv-rtab-btn-log');
        const btnCfg = document.getElementById('acv-rtab-btn-config');
        const btnQue = document.getElementById('acv-rtab-btn-queue');
        const btnSts = document.getElementById('acv-rtab-btn-status');

        if (logPane) logPane.style.display = (tab === 'log') ? '' : 'none';
        if (cfgPane) cfgPane.style.display = (tab === 'config') ? '' : 'none';
        if (quePane) quePane.style.display = (tab === 'queue') ? '' : 'none';
        if (stsPane) stsPane.style.display = (tab === 'status') ? '' : 'none';

        if (btnLog) btnLog.classList.toggle('active', tab === 'log');
        if (btnCfg) btnCfg.classList.toggle('active', tab === 'config');
        if (btnQue) btnQue.classList.toggle('active', tab === 'queue');
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

        // Fetch KPI for selected group
        this._fetchKpi(this.activitySelectedGroupId);
    },

    // ── Unified Config Handling (v2 Schema) ──

    getActivityConfig(groupId) {
        if (!groupId) return [];
        // Extract basic enabled flag state for dynamic list render from v2 schema
        const conf = this._groupConfigs[groupId] || { activities: {} };

        // 1. Map all system activities based on config
        const mapped = this._systemActivities.map(sys => {
            const actConf = conf.activities[sys.id] || {};
            return {
                id: sys.id,
                name: sys.name,
                description: sys.description,
                enabled: !!actConf.enabled,
                type: sys.type || 'standard',
                sub_events: sys.sub_events || []
            };
        });

        // 2. Sort explicitly based on stored activity_order array, if present
        if (conf.activity_order && Array.isArray(conf.activity_order) && conf.activity_order.length > 0) {
            mapped.sort((a, b) => {
                const idxA = conf.activity_order.indexOf(a.id);
                const idxB = conf.activity_order.indexOf(b.id);

                // If both are found in the saved order, sort mathematically
                if (idxA !== -1 && idxB !== -1) return idxA - idxB;

                // If an item is missing from the saved order, push it to the bottom
                if (idxA !== -1 && idxB === -1) return -1;
                if (idxA === -1 && idxB !== -1) return 1;

                return 0; // Both missing, maintain original system order
            });
        }

        return mapped;
    },

    saveActivityConfig(groupId) {
        if (!groupId) return;
        const items = document.querySelectorAll('#wf-act-dynamic-list .wf-act-group-cb');

        // Update local memory cache first
        if (!this._groupConfigs[groupId]) this._groupConfigs[groupId] = { version: 2, activities: {}, misc: { cooldown_min: 30, limit_min: 45 }, activity_order: [] };

        // Ensure activity_order array exists
        if (!this._groupConfigs[groupId].activity_order) this._groupConfigs[groupId].activity_order = [];

        // Clear order array to overwrite with fresh DOM order
        this._groupConfigs[groupId].activity_order = [];

        items.forEach(cb => {
            const id = cb.dataset.id;
            if (!this._groupConfigs[groupId].activities[id]) {
                this._groupConfigs[groupId].activities[id] = { enabled: false, config: {}, cooldown_enabled: false, cooldown_minutes: 60 };
            }
            this._groupConfigs[groupId].activities[id].enabled = cb.checked;

            // Push exact DOM order sequence into customized array
            this._groupConfigs[groupId].activity_order.push(id);
        });

        // Save to backend (async, non-blocking)
        this._saveConfigToBackend(groupId);
    },

    getMiscConfig(groupId) {
        const defaultMisc = { cooldown_min: 30, limit_min: 45, swap_wait_threshold_min: 5, choose_start_account: false, skip_cooldown: false, continue_on_error: false };
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
        const swapWaitEl = document.getElementById('misc-swap-wait-threshold');
        const chooseStartEl = document.getElementById('misc-choose-start-account');
        const skipCdEl = document.getElementById('misc-skip-cooldown');
        const continueOnErrEl = document.getElementById('misc-continue-on-error');

        if (!this._groupConfigs[groupId]) this._groupConfigs[groupId] = { version: 2, activities: {}, misc: {} };

        this._groupConfigs[groupId].misc = {
            cooldown_min: cdEl ? parseInt(cdEl.value) || 0 : 30,
            limit_min: limitEl ? parseInt(limitEl.value) || 0 : 45,
            swap_wait_threshold_min: swapWaitEl ? parseInt(swapWaitEl.value) || 0 : 5,
            choose_start_account: chooseStartEl ? chooseStartEl.checked : false,
            skip_cooldown: skipCdEl ? skipCdEl.checked : false,
            continue_on_error: continueOnErrEl ? continueOnErrEl.checked : false
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

        const actNode = this._groupConfigs[groupId].activities[activityId];
        actNode.last_run = new Date().toISOString();

        const todayStr = new Date().toLocaleDateString();
        if (actNode.runs_today_date !== todayStr) {
            actNode.runs_today_date = todayStr;
            actNode.runs_today = 1;
        } else {
            actNode.runs_today = (actNode.runs_today || 0) + 1;
        }

        this._saveConfigToBackend(groupId); // Save immediately
    },
    _getRunsToday(activityId, groupId) {
        const conf = this._groupConfigs[groupId];
        if (conf && conf.activities && conf.activities[activityId]) {
            const actNode = conf.activities[activityId];
            // Backward/forward compatibility: trust the metric directly
            // Backend now computes this exclusively based on server-time YYYY-MM-DD
            if (actNode.runs_today !== undefined) {
                return actNode.runs_today || 0;
            }
            const todayStr = new Date().toLocaleDateString();
            if (actNode.runs_today_date === todayStr) {
                return actNode.runs_today || 0;
            }
        }
        return 0;
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
        // Switch to Queue tab to show sequential execution immediately
        this.switchRightTab('queue');
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
            // Backend now tracks last_run per account, so we don't set it globally here
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
            // Sync immediately after stop request so UI doesn't require page/tab switching.
            await this._refreshSelectedGroupStatus();
        } else {
            console.error("Failed to stop bot", result.error);
        }
    },

    // Render the account queue sent by WS `bot_queue_update`
    renderAccountQueue(queueData) {
        let container = document.getElementById('wf-account-queue-container');
        if (!container) return;

        if (!queueData.is_running && !queueData.stop_requested) {
            container.innerHTML = `
                <div class="acv-queue-header" style="font-weight:700; color:var(--foreground); margin-bottom:8px;">Sequential Execution Queue</div>
                <div style="font-size:12px; color:var(--muted-foreground);">Bot Stopped</div>
            `;
            return;
        }

        const accounts = Array.isArray(queueData.accounts) ? queueData.accounts : [];
        const total = accounts.length;
        const runningCount = accounts.filter(a => a.status === 'running').length;
        const doneCount = accounts.filter(a => a.status === 'done').length;
        const errorCount = accounts.filter(a => a.status === 'error').length;
        const pendingCount = accounts.filter(a => !a.status || a.status === 'pending').length;
        const currentIdx = Number.parseInt(queueData.current_idx, 10);
        const currentAcc = Number.isInteger(currentIdx) && currentIdx >= 0 ? accounts[currentIdx] : null;
        const progressPct = total > 0 ? Math.round((doneCount / total) * 100) : 0;
        const stateLabel = queueData.stop_requested ? 'Stopping' : 'Running';
        const stateColor = queueData.stop_requested ? '#ef4444' : '#16a34a';

        let html = `
        <div style="display:flex; flex-direction:column; gap:10px;">
            <div class="acv-queue-header" style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0;">
                <div style="display:flex; flex-direction:column; gap:2px;">
                    <div style="font-weight:700; color:var(--foreground);">Sequential Execution Queue</div>
                    <div style="font-size:12px; color:var(--muted-foreground);">Cycle ${queueData.cycle || 1} - ${total} account(s)</div>
                </div>
                <div style="display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:999px; background:rgba(0,0,0,.04); border:1px solid var(--border); font-size:12px; font-weight:700; color:${stateColor};">
                    <span style="width:8px; height:8px; border-radius:999px; background:${stateColor}; display:inline-block;"></span>
                    ${stateLabel}
                </div>
            </div>

            <div style="display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:8px;">
                <div style="border:1px solid var(--border); border-radius:10px; padding:8px; background:var(--card);">
                    <div style="font-size:11px; color:var(--muted-foreground);">Pending</div>
                    <div style="font-size:16px; font-weight:700; color:var(--foreground);">${pendingCount}</div>
                </div>
                <div style="border:1px solid var(--border); border-radius:10px; padding:8px; background:var(--card);">
                    <div style="font-size:11px; color:var(--muted-foreground);">Running</div>
                    <div style="font-size:16px; font-weight:700; color:#2563eb;">${runningCount}</div>
                </div>
                <div style="border:1px solid var(--border); border-radius:10px; padding:8px; background:var(--card);">
                    <div style="font-size:11px; color:var(--muted-foreground);">Done</div>
                    <div style="font-size:16px; font-weight:700; color:#16a34a;">${doneCount}</div>
                </div>
                <div style="border:1px solid var(--border); border-radius:10px; padding:8px; background:var(--card);">
                    <div style="font-size:11px; color:var(--muted-foreground);">Error</div>
                    <div style="font-size:16px; font-weight:700; color:#dc2626;">${errorCount}</div>
                </div>
            </div>

            <div style="border:1px solid var(--border); border-radius:10px; padding:8px; background:var(--card);">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
                    <span style="font-size:12px; color:var(--muted-foreground);">Queue Progress</span>
                    <span style="font-size:12px; font-weight:700; color:var(--foreground);">${progressPct}%</span>
                </div>
                <div style="height:8px; border-radius:999px; background:var(--muted); overflow:hidden;">
                    <div style="height:100%; width:${progressPct}%; background:linear-gradient(90deg,#16a34a,#22c55e);"></div>
                </div>
            </div>

            <div style="border:1px solid var(--border); border-radius:10px; padding:10px; background:var(--card);">
                <div style="font-size:11px; color:var(--muted-foreground); margin-bottom:4px;">Current Account</div>
                <div style="font-size:13px; font-weight:700; color:var(--foreground);">
                    ${currentAcc ? `${currentAcc.lord_name || 'Unknown'} (Emu ${currentAcc.emu_index ?? '--'})` : 'Waiting for next account...'}
                </div>
            </div>

            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-size:11px; color:var(--muted-foreground);">
                <span><b style="color:var(--foreground);">Legend:</b></span>
                <span>Pending = waiting in queue</span>
                <span>Running = processing now</span>
                <span>Done = finished successfully</span>
                <span>Error = failed this cycle</span>
            </div>

            <div class="acv-queue-list">`;

        accounts.forEach((acc, i) => {
            const isCurrent = currentIdx === i;
            let statusIcon = '...';
            let statusClass = 'pending';
            if (acc.status === 'running') { statusIcon = 'RUN'; statusClass = 'running'; }
            if (acc.status === 'done') { statusIcon = 'OK'; statusClass = 'done'; }
            if (acc.status === 'error') { statusIcon = 'ERR'; statusClass = 'error'; }

            html += `
                <div class="acv-queue-item ${isCurrent ? 'active' : ''} status-${statusClass}">
                    <span class="acv-q-icon" style="font-size:10px; font-weight:700; min-width:36px; text-align:center; border-radius:6px; padding:2px 6px; background:var(--muted);">${statusIcon}</span>
                    <span class="acv-q-name">${acc.lord_name} (Emu ${acc.emu_index})</span>
                </div>
            `;
        });

        html += `</div></div>`;
        container.innerHTML = html;

        // BUG 2 FIX: Update individual activity statuses
        this._updateActivityStatuses(queueData);
    },

    _latestActivityStatuses: null,

    _updateActivityStatuses(queueData) {
        if (!queueData) return;

        // BUG 1 FIX: Server now sends per-activity breakdown in activity_statuses
        const statuses = queueData.activity_statuses || {};
        this._latestActivityStatuses = statuses;

        // NEW: Live Metrics Sync (Last Run, Runs Today)
        if (queueData.activity_metrics) {
            const gid = queueData.group_id;
            if (this._groupConfigs[gid] && this._groupConfigs[gid].activities) {
                Object.keys(queueData.activity_metrics).forEach(actId => {
                    const metrics = queueData.activity_metrics[actId];
                    if (this._groupConfigs[gid].activities[actId]) {
                        this._groupConfigs[gid].activities[actId].last_run = metrics.last_run;
                        this._groupConfigs[gid].activities[actId].runs_today = metrics.runs_today;
                    }
                });
            }

            // If the user's focus corresponds to an updated activity, refresh the panel metrics
            if (this._currentConfigActivityId && queueData.activity_metrics[this._currentConfigActivityId]) {
                const liveLastRun = document.getElementById('acv-cfg-last-run');
                const liveRunsToday = document.getElementById('acv-cfg-runs-today');
                const liveStatusBadge = document.getElementById('acv-cooldown-status-badge');

                if (liveLastRun || liveRunsToday) {
                    const metrics = queueData.activity_metrics[this._currentConfigActivityId];
                    if (liveLastRun) {
                        liveLastRun.textContent = metrics.last_run ? new Date(metrics.last_run).toLocaleString() : 'Never';
                    }
                    if (liveRunsToday) {
                        liveRunsToday.textContent = metrics.runs_today || 0;
                    }
                    if (liveStatusBadge) {
                        const cooldownStatus = this._isOnCooldown(this._currentConfigActivityId, gid)
                            ? `<span style="color:var(--amber-500)">⏳ ${this._formatCooldownRemaining(this._currentConfigActivityId, gid)}</span>`
                            : (metrics.last_run ? '<span style="color:var(--emerald-500)">✓ Ready</span>' : '');
                        liveStatusBadge.innerHTML = cooldownStatus;
                    }
                }
            }
        }

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

    async _refreshSelectedGroupStatus() {
        if (!this.activitySelectedGroupId) return;

        try {
            if (!this.di) await this._initDI();
            const res = await this.di.botRepo.getStatus(this.activitySelectedGroupId);
            if (!res.ok || !res.data) {
                this.isRunning = false;
                this._updateGroupStatusBadge(this.activitySelectedGroupId, {
                    is_running: false,
                    all_on_cooldown: false,
                });
                this._updateActivityStatuses({
                    is_running: false,
                    stop_requested: false,
                    activity_statuses: {},
                    current_activity: null,
                });
                this.renderAccountQueue({
                    is_running: false,
                    stop_requested: false,
                });
                return;
            }

            this.isRunning = !!res.data.is_running;
            this._updateGroupStatusBadge(this.activitySelectedGroupId, {
                is_running: !!res.data.is_running,
                all_on_cooldown: !!(res.data.is_running && res.data.accounts && res.data.accounts.every(a => a.status === 'pending')),
            });
            this._updateActivityStatuses(res.data);
            this.renderAccountQueue(res.data);
        } catch (e) {
            console.warn('Failed to poll selected group status:', e);
        }
    },

    _startLiveStatusPolling() {
        if (this._statusPollInterval) return;

        const tick = async () => {
            if (this._isStatusPollInFlight) return;
            this._isStatusPollInFlight = true;
            try {
                await this._pollGroupStatuses();
                await this._refreshSelectedGroupStatus();
            } finally {
                this._isStatusPollInFlight = false;
            }
        };

        tick();
        this._statusPollInterval = setInterval(tick, 3000);
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

            // Event-type activity: distinct visual treatment
            if (item.type === 'event') {
                const subCount = this._getEnabledSubEventCount(item.id, groupId);
                const totalSub = item.sub_events.length;
                return `
                <div class="acv-activity-row event-type ${item.enabled ? 'enabled' : ''}" id="acv-row-${item.id}" data-id="${item.id}"
                    draggable="true" 
                    ondragstart="WF3.onDragStart(event)" 
                    ondragover="WF3.onDragOver(event)" 
                    ondrop="WF3.onDrop(event)" 
                    ondragend="WF3.onDragEnd(event)">
                    
                    <div class="acv-drag-handle" title="Drag to reorder">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="8" y1="6" x2="21" y2="6"></line>
                            <line x1="8" y1="12" x2="21" y2="12"></line>
                            <line x1="8" y1="18" x2="21" y2="18"></line>
                            <line x1="3" y1="6" x2="3.01" y2="6"></line>
                            <line x1="3" y1="12" x2="3.01" y2="12"></line>
                            <line x1="3" y1="18" x2="3.01" y2="18"></line>
                        </svg>
                    </div>

                    <label class="acv-check-label" style="cursor:pointer;" onclick="event.stopPropagation()">
                        <input type="checkbox" class="wf-act-group-cb" data-name="${item.name.replace(/'/g, "\\'")}" data-id="${item.id}" data-idx="${idx}" ${item.enabled ? 'checked' : ''}
                            onchange="WF3.saveActivityConfig(${groupId}); this.closest('.acv-activity-row').classList.toggle('enabled', this.checked)">
                        <span class="acv-check-box"></span>
                    </label>

                    <div class="acv-event-icon">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                            <line x1="16" y1="2" x2="16" y2="6"></line>
                            <line x1="8" y1="2" x2="8" y2="6"></line>
                            <line x1="3" y1="10" x2="21" y2="10"></line>
                            <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"></path>
                        </svg>
                    </div>

                    <div class="acv-activity-info" style="flex:1; cursor:pointer; padding:2px 0;" onclick="WF3.showEventPopup('${item.id}', ${groupId})">
                        <span class="acv-activity-name">${item.name}</span>
                        <span class="acv-event-badge">${subCount}/${totalSub}</span>
                    </div>
                    <span class="acv-activity-status status-${statusVal}" id="acv-status-${item.id}" data-status="${statusVal}">${statusText}</span>
                    <button class="acv-cfg-btn acv-event-open-btn" title="Manage Sub-events" onclick="WF3.showEventPopup('${item.id}', ${groupId})" style="opacity:1;">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
                    </button>
                </div>
                `;
            }

            return `
            <div class="acv-activity-row ${item.enabled ? 'enabled' : ''}" id="acv-row-${item.id}" data-id="${item.id}"
                draggable="true" 
                ondragstart="WF3.onDragStart(event)" 
                ondragover="WF3.onDragOver(event)" 
                ondrop="WF3.onDrop(event)" 
                ondragend="WF3.onDragEnd(event)">
                
                <div class="acv-drag-handle" title="Drag to reorder">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="8" y1="6" x2="21" y2="6"></line>
                        <line x1="8" y1="12" x2="21" y2="12"></line>
                        <line x1="8" y1="18" x2="21" y2="18"></line>
                        <line x1="3" y1="6" x2="3.01" y2="6"></line>
                        <line x1="3" y1="12" x2="3.01" y2="12"></line>
                        <line x1="3" y1="18" x2="3.01" y2="18"></line>
                    </svg>
                </div>

                <label class="acv-check-label" style="cursor:pointer;" onclick="event.stopPropagation()">
                    <input type="checkbox" class="wf-act-group-cb" data-name="${item.name.replace(/'/g, "\\'")}" data-id="${item.id}" data-idx="${idx}" ${item.enabled ? 'checked' : ''}
                        onchange="WF3.saveActivityConfig(${groupId}); this.closest('.acv-activity-row').classList.toggle('enabled', this.checked)">
                    <span class="acv-check-box"></span>
                </label>
                <div class="acv-activity-info" style="flex:1; cursor:pointer; padding:2px 0;" onclick="WF3.selectActivity('${item.id}', ${groupId}, this)">
                    <span class="acv-activity-name">${item.name}</span>
                </div>
                <span class="acv-activity-status status-${statusVal}" id="acv-status-${item.id}" data-status="${statusVal}">${statusText}</span>
                <button class="acv-cfg-btn" title="Configure" onclick="WF3.showActivityConfig('${item.id}', ${groupId})">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 0-14.14 0M3.51 9a10 10 0 0 0 0 6M20.49 9a10 10 0 0 0 0 6M4.93 19.07a10 10 0 0 0 14.14 0"/></svg>
                </button>
            </div>
            `;
        }).join('');
    },

    // ── Drag & Drop Handlers ──
    onDragStart(e) {
        // e.target is the .acv-activity-row
        if (!e.target.classList.contains('acv-activity-row')) return;

        e.dataTransfer.effectAllowed = 'move';
        // Store the ID of the activity being dragged
        const activityId = e.target.getAttribute('data-id');
        e.dataTransfer.setData('text/plain', activityId);

        // Add a class for visual styling
        setTimeout(() => e.target.classList.add('dragging'), 0);
    },

    onDragOver(e) {
        e.preventDefault(); // Necessary to allow dropping
        e.dataTransfer.dropEffect = 'move';

        const container = document.getElementById('wf-act-dynamic-list');
        const draggingRow = container.querySelector('.dragging');
        if (!draggingRow) return;

        // Find the row we are currently hovering over
        const targetRow = e.target.closest('.acv-activity-row');
        if (!targetRow || targetRow === draggingRow) {
            // Remove drop indicators if not hovering over a valid row
            container.querySelectorAll('.acv-activity-row').forEach(r => r.style.borderTop = '');
            container.querySelectorAll('.acv-activity-row').forEach(r => r.style.borderBottom = '');
            return;
        }

        // Determine if we should drop above or below the target row
        const box = targetRow.getBoundingClientRect();
        const offset = e.clientY - box.top;
        const insertAfter = offset > box.height / 2;

        // Clear previous indicators
        container.querySelectorAll('.acv-activity-row').forEach(r => {
            r.style.borderTop = '';
            r.style.borderBottom = '';
        });

        // Add visual drop indicator
        if (insertAfter) {
            targetRow.style.borderBottom = '2px solid var(--primary)';
        } else {
            targetRow.style.borderTop = '2px solid var(--primary)';
        }
    },

    onDragLeave(e) {
        const targetRow = e.target.closest('.acv-activity-row');
        if (targetRow) {
            targetRow.style.borderTop = '';
            targetRow.style.borderBottom = '';
        }
    },

    onDrop(e) {
        e.preventDefault();
        const draggedActivityId = e.dataTransfer.getData('text/plain');
        if (!draggedActivityId) return;

        const container = document.getElementById('wf-act-dynamic-list');
        const draggedRow = document.getElementById(`acv-row-${draggedActivityId}`);
        const targetRow = e.target.closest('.acv-activity-row');

        if (!draggedRow || !targetRow || draggedRow === targetRow) return;

        // Clear visual drop indicators
        container.querySelectorAll('.acv-activity-row').forEach(r => {
            r.style.borderTop = '';
            r.style.borderBottom = '';
        });

        // Determine if we should drop above or below
        const box = targetRow.getBoundingClientRect();
        const offset = e.clientY - box.top;
        if (offset > box.height / 2) {
            // Insert after target row
            targetRow.after(draggedRow);
        } else {
            // Insert before target row
            targetRow.before(draggedRow);
        }
    },

    onDragEnd(e) {
        const container = document.getElementById('wf-act-dynamic-list');

        // Clean up classes and styles
        container.querySelectorAll('.acv-activity-row').forEach(r => {
            r.classList.remove('dragging');
            r.style.borderTop = '';
            r.style.borderBottom = '';
            r.style.opacity = '1';
        });

        // Save the new order automatically by extracting the active group ID
        // Because "renderActivitiesForGroup" executes under the context of selectGroup
        if (this.activitySelectedGroupId) {
            this.saveActivityConfig(this.activitySelectedGroupId);
        }
    },
    // ───────────────────────────

    renderMiscForGroup(groupId) {
        const container = document.getElementById('wf-act-dynamic-misc-list');
        if (!container) return;

        if (!groupId) {
            container.innerHTML = '<div class="acv-empty-hint">Select a group to configure its Misc settings.</div>';
            return;
        }

        const misc = this.getMiscConfig(groupId);

        container.innerHTML = `
                <div class="acv-misc-item" style="border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 8px;">
                <div style="font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; font-size: 12px;">
                    <span>⏳</span> Account Cooldown
                </div>
                <div style="font-size: 11px; color: var(--muted-foreground); margin-bottom: 6px; line-height: 1.3;">
                    Wait before re-running an account that recently finished.
                </div>
                <div style="font-size: 12px;">
                    <input type="number" class="acv-input-num" id="misc-cooldown-min" value="${misc.cooldown_min}" onchange="WF3.saveMiscConfig(${groupId})" style="width: 60px;"> minute(s)
                </div>
            </div>
            
            <div class="acv-misc-item" style="border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 8px;">
                <div style="font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; font-size: 12px;">
                    <span>⏱</span> Time Limit
                </div>
                <div style="font-size: 11px; color: var(--muted-foreground); margin-bottom: 6px; line-height: 1.3;">
                    Force swap to next account after this much time total.
                </div>
                <div style="font-size: 12px;">
                    <input type="number" class="acv-input-num" id="misc-limit-min" value="${misc.limit_min}" onchange="WF3.saveMiscConfig(${groupId})" style="width: 60px;"> minute(s)
                </div>
            </div>
            
            <div class="acv-misc-item" style="border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 8px;">
                <div style="font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; font-size: 12px;">
                    <span>🔄</span> Smart Wait Threshold
                </div>
                <div style="font-size: 11px; color: var(--muted-foreground); margin-bottom: 6px; line-height: 1.3;">
                    Wait instead of swapping if cooldown ends within this window. Set to 0 to disable.
                </div>
                <div style="font-size: 12px;">
                    <input type="number" class="acv-input-num" id="misc-swap-wait-threshold" value="${misc.swap_wait_threshold_min || 0}" min="0" onchange="WF3.saveMiscConfig(${groupId})" style="width: 60px;"> minute(s)
                </div>
            </div>
            
            <div class="acv-misc-item" style="border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 8px;">
                <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer;">
                    <input type="checkbox" id="misc-choose-start-account" onchange="WF3.saveMiscConfig(${groupId})" ${misc.choose_start_account ? 'checked' : ''} style="margin-top: 2px;">
                    <div>
                        <div style="font-weight: 600; margin-bottom: 2px; display: flex; align-items: center; gap: 6px; font-size: 12px;">
                            <span>🎯</span> Choose Account to Run First
                        </div>
                        <div style="font-size: 11px; color: var(--muted-foreground); line-height: 1.3;">
                            Prompt to select which account should be executed first.
                        </div>
                    </div>
                </label>
            </div>
            
            <div class="acv-misc-item" style="border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 8px;">
                <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer;">
                    <input type="checkbox" id="misc-skip-cooldown" onchange="WF3.saveMiscConfig(${groupId})" ${misc.skip_cooldown ? 'checked' : ''} style="margin-top: 2px;">
                    <div>
                        <div style="font-weight: 600; margin-bottom: 2px; display: flex; align-items: center; gap: 6px; font-size: 12px; color: #fb923c;">
                            <span>⚡</span> Skip Cooldown (Force Run)
                        </div>
                        <div style="font-size: 11px; color: var(--muted-foreground); line-height: 1.3;">
                            Ignore all cooldowns. Bot will re-run everything immediately.
                        </div>
                    </div>
                </label>
            </div>
            
            <div class="acv-misc-item">
                <label style="display: flex; align-items: flex-start; gap: 8px; cursor: pointer;">
                    <input type="checkbox" id="misc-continue-on-error" onchange="WF3.saveMiscConfig(${groupId})" ${misc.continue_on_error ? 'checked' : ''} style="margin-top: 2px;">
                    <div>
                        <div style="font-weight: 600; margin-bottom: 2px; display: flex; align-items: center; gap: 6px; font-size: 12px; color: #ef4444;">
                            <span>🛡️</span> Continue on Error
                        </div>
                        <div style="font-size: 11px; color: var(--muted-foreground); line-height: 1.3;">
                            Log error but continue next activities instead of swapping immediately.
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
        this._currentConfigActivityId = activityId;

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
    <div class="acv-cfg-field" >
        <label class="acv-check-label" style="gap:10px;">
            <input type="checkbox" data-cfgkey="${d.key}" ${val ? 'checked' : ''} onchange="WF3.savePerActivityConfig('${activityId}',${groupId})">
                <span class="acv-check-box"></span>
                <span>${d.label}</span>
        </label>
                </div> `;
            }
            if (d.type === 'select') {
                const opts = d.options.map(o => `<option value = "${o}" ${val === o ? 'selected' : ''}> ${o}</option> `).join('');
                return `
    <div class="acv-cfg-field" >
                    <label class="acv-cfg-label">${d.label}</label>
                    <select class="acv-cfg-select" data-cfgkey="${d.key}" onchange="WF3.savePerActivityConfig('${activityId}',${groupId})">${opts}</select>
                </div> `;
            }
            return `
    <div class="acv-cfg-field" >
                <label class="acv-cfg-label">${d.label}</label>
                <input type="number" class="acv-cfg-input" data-cfgkey="${d.key}" value="${val}" ${d.min !== undefined ? 'min="' + d.min + '"' : ''} ${d.max !== undefined ? 'max="' + d.max + '"' : ''} onchange="WF3.savePerActivityConfig('${activityId}',${groupId})">
            </div>`;
        }).join('');

        // Cooldown section (always shown)
        const cdEnabled = saved.cooldown_enabled || false;
        const cdMinutes = saved.cooldown_minutes !== undefined ? saved.cooldown_minutes : 60;
        const lastRun = this._getLastRun(activityId, groupId);
        const lastRunStr = lastRun ? new Date(lastRun).toLocaleString() : 'Never';
        const runsToday = this._getRunsToday(activityId, groupId);
        const cooldownStatus = this._isOnCooldown(activityId, groupId)
            ? `<span style = "color:var(--amber-500)" >⏳ ${this._formatCooldownRemaining(activityId, groupId)}</span> `
            : (lastRun ? '<span style="color:var(--emerald-500)">✓ Ready</span>' : '');

        const cooldownHtml = `
    <div class="acv-cfg-divider" ></div>
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
                <span>Last run: <span id="acv-cfg-last-run">${lastRunStr}</span></span>
                <span id="acv-cooldown-status-badge">${cooldownStatus}</span>
            </div>
            <div class="acv-cfg-field" style="flex-direction:row; align-items:center; gap:8px; font-size:11px; color:var(--muted-foreground); margin-top:-5px;">
                <span>Runs today: <strong id="acv-cfg-runs-today" style="color:var(--foreground);">${runsToday}</strong></span>
            </div>
`;

        panel.innerHTML = `
    <div class="acv-cfg-header" >
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

    // ── Event Activity — Sub-events Helpers ──

    _getEnabledSubEventCount(activityId, groupId) {
        const conf = this._groupConfigs[groupId];
        if (!conf || !conf.activities || !conf.activities[activityId]) return 0;
        const subCfg = conf.activities[activityId].sub_events_config || {};
        return Object.values(subCfg).filter(s => s.enabled).length;
    },

    showEventPopup(activityId, groupId) {
        const sys = this._systemActivities.find(a => a.id === activityId);
        if (!sys || sys.type !== 'event') return;

        const subEvents = sys.sub_events || [];
        const conf = this._groupConfigs[groupId] || { activities: {} };
        const actConf = conf.activities[activityId] || {};
        const subCfg = actConf.sub_events_config || {};

        // Build sub-events list HTML
        const subEventsHtml = subEvents.map(sub => {
            const subConf = subCfg[sub.id] || {};
            const isEnabled = !!subConf.enabled;
            const configFields = sub.config_fields || [];
            const savedSubConf = subConf.config || {};
            const cdEnabled = subConf.cooldown_enabled ?? (sub.defaults && sub.defaults.cooldown_enabled) ?? false;
            const cdMinutes = subConf.cooldown_minutes ?? (sub.defaults && sub.defaults.cooldown_minutes) ?? 60;

            // Build config fields for this sub-event
            const fieldsHtml = configFields.map(d => {
                const val = savedSubConf[d.key] !== undefined ? savedSubConf[d.key] : d.default;
                if (d.type === 'select') {
                    const opts = d.options.map(o => `<option value="${o}" ${val === o ? 'selected' : ''}>${o}</option>`).join('');
                    return `
                    <div class="acv-cfg-field">
                        <label class="acv-cfg-label">${d.label}</label>
                        <select class="acv-cfg-select" data-subcfgkey="${d.key}" data-subid="${sub.id}" onchange="WF3._saveSubEventConfig('${activityId}', ${groupId})">${opts}</select>
                    </div>`;
                }
                if (d.type === 'checkbox') {
                    return `
                    <div class="acv-cfg-field">
                        <label class="acv-check-label" style="gap:10px;">
                            <input type="checkbox" data-subcfgkey="${d.key}" data-subid="${sub.id}" ${val ? 'checked' : ''} onchange="WF3._saveSubEventConfig('${activityId}', ${groupId})">
                            <span class="acv-check-box"></span>
                            <span>${d.label}</span>
                        </label>
                    </div>`;
                }
                return `
                <div class="acv-cfg-field">
                    <label class="acv-cfg-label">${d.label}</label>
                    <input type="number" class="acv-cfg-input" data-subcfgkey="${d.key}" data-subid="${sub.id}" value="${val}" ${d.min !== undefined ? 'min="'+d.min+'"' : ''} ${d.max !== undefined ? 'max="'+d.max+'"' : ''} onchange="WF3._saveSubEventConfig('${activityId}', ${groupId})">
                </div>`;
            }).join('');

            const hasConfig = configFields.length > 0;

            return `
            <div class="acv-sub-event-row ${isEnabled ? 'enabled' : ''}" data-subid="${sub.id}">
                <div class="acv-sub-event-header">
                    <label class="acv-check-label" style="cursor:pointer;" onclick="event.stopPropagation()">
                        <input type="checkbox" class="acv-sub-event-cb" data-subid="${sub.id}" ${isEnabled ? 'checked' : ''}
                            onchange="WF3._saveSubEventConfig('${activityId}', ${groupId}); this.closest('.acv-sub-event-row').classList.toggle('enabled', this.checked)">
                        <span class="acv-check-box"></span>
                    </label>
                    <div class="acv-sub-event-info" style="flex:1;">
                        <div class="acv-sub-event-name">${sub.name}</div>
                        <div class="acv-sub-event-desc">${sub.description || ''}</div>
                    </div>
                    ${hasConfig ? `<button class="acv-cfg-btn" style="opacity:1;" title="Configure" onclick="WF3._toggleSubEventConfig('${sub.id}')">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 0-14.14 0M3.51 9a10 10 0 0 0 0 6M20.49 9a10 10 0 0 0 0 6M4.93 19.07a10 10 0 0 0 14.14 0"/></svg>
                    </button>` : ''}
                </div>
                <div class="acv-sub-event-config" id="acv-sub-cfg-${sub.id}" style="display:none;">
                    ${fieldsHtml}
                    <div class="acv-cfg-divider"></div>
                    <div class="acv-cfg-section-title">Cooldown</div>
                    <div class="acv-cfg-field">
                        <label class="acv-check-label" style="gap:10px;">
                            <input type="checkbox" data-subcfgkey="cooldown_enabled" data-subid="${sub.id}" ${cdEnabled ? 'checked' : ''} onchange="WF3._saveSubEventConfig('${activityId}', ${groupId})">
                            <span class="acv-check-box"></span>
                            <span>Enable cooldown</span>
                        </label>
                    </div>
                    <div class="acv-cfg-field" style="flex-direction:row; align-items:center; gap:10px;">
                        <label class="acv-cfg-label" style="margin:0; white-space:nowrap;">Cooldown</label>
                        <input type="number" class="acv-cfg-input" data-subcfgkey="cooldown_minutes" data-subid="${sub.id}" value="${cdMinutes}" min="1" max="9999" style="width:80px;" onchange="WF3._saveSubEventConfig('${activityId}', ${groupId})">
                        <span style="font-size:12px; color:var(--muted-foreground);">Minutes</span>
                    </div>
                </div>
            </div>`;
        }).join('');

        // Create or reuse modal
        let modal = document.getElementById('wf-event-popup-overlay');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'wf-event-popup-overlay';
            modal.className = 'wf-fn-overlay';
            document.body.appendChild(modal);
        }

        modal.innerHTML = `
            <div class="acv-event-popup" onclick="event.stopPropagation()">
                <div class="acv-event-popup-header">
                    <div>
                        <div class="acv-event-popup-title">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                            ${sys.name}
                        </div>
                        <div class="acv-event-popup-sub">Manage sub-events that rotate during execution</div>
                    </div>
                    <button class="acv-event-popup-close" onclick="document.getElementById('wf-event-popup-overlay').classList.remove('visible')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>
                <div class="acv-event-popup-body">
                    ${subEventsHtml || '<div class="acv-empty-hint">No sub-events configured.</div>'}
                </div>
            </div>
        `;

        modal.onclick = (e) => {
            if (e.target === modal) modal.classList.remove('visible');
        };
        modal.classList.add('visible');
    },

    _toggleSubEventConfig(subId) {
        const el = document.getElementById(`acv-sub-cfg-${subId}`);
        if (!el) return;
        const isOpen = el.style.display !== 'none';
        el.style.display = isOpen ? 'none' : 'block';
    },

    _saveSubEventConfig(activityId, groupId) {
        if (!this._groupConfigs[groupId]) {
            this._groupConfigs[groupId] = { version: 2, activities: {}, misc: {} };
        }
        if (!this._groupConfigs[groupId].activities[activityId]) {
            this._groupConfigs[groupId].activities[activityId] = { enabled: false, config: {}, cooldown_enabled: false, cooldown_minutes: 60 };
        }

        const actConf = this._groupConfigs[groupId].activities[activityId];
        if (!actConf.sub_events_config) actConf.sub_events_config = {};

        // Read all sub-event checkboxes for enable state
        const popup = document.getElementById('wf-event-popup-overlay');
        if (!popup) return;

        popup.querySelectorAll('.acv-sub-event-cb').forEach(cb => {
            const subId = cb.dataset.subid;
            if (!actConf.sub_events_config[subId]) {
                actConf.sub_events_config[subId] = { enabled: false, config: {}, cooldown_enabled: false, cooldown_minutes: 60 };
            }
            actConf.sub_events_config[subId].enabled = cb.checked;
        });

        // Read all config fields
        popup.querySelectorAll('[data-subcfgkey]').forEach(el => {
            const subId = el.dataset.subid;
            const key = el.dataset.subcfgkey;
            if (!subId || !key) return;

            if (!actConf.sub_events_config[subId]) {
                actConf.sub_events_config[subId] = { enabled: false, config: {}, cooldown_enabled: false, cooldown_minutes: 60 };
            }

            const val = el.type === 'checkbox' ? el.checked : (el.type === 'number' ? +el.value : el.value);

            if (key === 'cooldown_enabled' || key === 'cooldown_minutes') {
                actConf.sub_events_config[subId][key] = val;
            } else {
                if (!actConf.sub_events_config[subId].config) actConf.sub_events_config[subId].config = {};
                actConf.sub_events_config[subId].config[key] = val;
            }
        });

        this._saveConfigToBackend(groupId);

        // Update the badge count in the activity list row
        const sys = this._systemActivities.find(a => a.id === activityId);
        if (sys) {
            const badge = document.querySelector(`#acv-row-${activityId} .acv-event-badge`);
            if (badge) {
                const count = this._getEnabledSubEventCount(activityId, groupId);
                badge.textContent = `${count}/${sys.sub_events.length}`;
            }
        }

        WfToast.show('s', 'Saved', 'Sub-event configuration saved.');
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
    <div class="grp-list-item ${isActive ? 'active' : ''}" onclick = "WF3.editGroup(${g.id})" >
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
        if (countEl) countEl.textContent = `${members.length} account${members.length !== 1 ? 's' : ''} `;

        container.innerHTML = members.map(acc => `
    <div class="grp-member-item" >
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
    <tr style = "border-bottom: 1px solid var(--border);" >
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
    <div class="wf-recipe-card wf-tpl-card" onclick = "WF3.openTemplateInEditor('${t.id}')" >
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
    <div class="wf-list-empty" >
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
                            <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
                        </svg>
                        <p>No saved recipes yet.<br>Click <strong>Create New</strong> or use a template to get started.</p>
                    </div> `;
            } else {
                recGrid.innerHTML = this.recipes.map(r => `
    <div class="wf-recipe-card" onclick = "WF3.openRecipeInEditor('${r.id}')" >
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
            await fetch(`/ api / workflow / recipes / ${id} `, { method: 'DELETE' });
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
    <div class="wf-sidebar-cat" > ${cat}</div>
        ${fns.map(fn => `
                <div class="wf-sidebar-fn" onclick="WF3.addStepFromSidebar('${fn.id}')">
                    <span class="wf-sidebar-fn-icon" style="color:${fn.color}">${fn.icon}</span>
                    <div>
                        <div class="wf-sidebar-fn-name">${fn.label}</div>
                        <div class="wf-sidebar-fn-desc">${fn.description}</div>
                    </div>
                </div>
            `).join('')
            }
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
                WfToast.show('s', 'Saved', `"${name}" ${data.action} `);
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
    <div class="wf-fn-category" > ${cat}</div>
        ${fns.map(fn => `
                <div class="wf-fn-item" onclick="WF3.addStepFromPicker('${fn.id}')">
                    <div class="wf-fn-icon" style="color:${fn.color}">${fn.icon}</div>
                    <div>
                        <div class="wf-fn-label">${fn.label}</div>
                        <div class="wf-fn-desc">${fn.description}</div>
                    </div>
                </div>
            `).join('')
            }
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
    <div class="wf-empty-hint" >
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
                        <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
                    </svg>
                    <h3>No steps yet</h3>
                    <p>Pick a function from the left panel,<br>or click <strong>Add Step</strong> below.</p>
                </div> `;
            return;
        }

        let html = '';
        this.steps.forEach((step, index) => {
            const fn = this.getFnDef(step.function_id);
            const configHtml = this.renderConfigFields(step, fn, index);

            html += `
    <div class="wf-step-card" id = "wf-step-${index}" >
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
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
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
                    `<option value = "${o}" ${val === o ? 'selected' : ''}> ${o}</option> `
                ).join('');
                return `<div class="wf-cf-field" >
                    <span class="wf-cf-label">${p.label}</span>
                    <select class="wf-cf-select" onchange="WF3.updateStepConfig(${index},'${p.key}',this.value)">${opts}</select>
                </div> `;
            }

            if (p.type === 'number') {
                return `<div class="wf-cf-field" >
                    <span class="wf-cf-label">${p.label}</span>
                    <input class="wf-cf-input" type="number" value="${val}" ${p.min !== undefined ? `min="${p.min}"` : ''} ${p.max !== undefined ? `max="${p.max}"` : ''} onchange="WF3.updateStepConfig(${index},'${p.key}',+this.value)" style="width:80px;" />
                </div> `;
            }

            return `<div class="wf-cf-field" >
                <span class="wf-cf-label">${p.label}</span>
                <input class="wf-cf-input" type="text" value="${val}" onchange="WF3.updateStepConfig(${index},'${p.key}',this.value)" />
            </div> `;
        }).join('');

        return `<div class="wf-step-configs" > ${fields}</div> `;
    },

    // ── WebSocket Log & Progress Receivers ──
    setupWebSocket() {
        if (!window.wsClient) return;

        wsClient.on('workflow_log', (data) => {
            const logEl = document.getElementById('wf-exec-log');
            if (!logEl) return;
            const ts = new Date().toLocaleTimeString('en-GB', { hour12: false });
            const line = document.createElement('div');
            line.className = `wf - log - line log - ${data.log_type} `;
            line.innerHTML = `<span class="log-time" > ${ts}</span> <span>${data.message}</span>`;
            logEl.appendChild(line);
            logEl.scrollTop = logEl.scrollHeight;

            if (data.log_type === 'run') {
                document.querySelectorAll('.wf-step-card').forEach(el => el.classList.remove('running'));
                // Extract step idx from "[<n>/<total>]" strings
                const match = data.message.match(/\[(\d+)\//);
                if (match) {
                    const idx = parseInt(match[1]) - 1;
                    const card = document.getElementById(`wf - step - ${idx} `);
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
            WF3.isRunning = !!data.is_running;

            // Use loose equality to handle int/string mismatch
            // eslint-disable-next-line eqeqeq

            // ── MONITOR TAB: must update BEFORE the activity-group gate ──
            if (WF3.activeMainTab === 'monitor' && WF3._monitorGroupId == groupId) {
                WF3._monitorLastData = data;
                WF3._renderMonitorQueue(data);
                WF3._updateMonitorStatusBadge(data);
                WF3._scheduleKpiRefresh();
                // Ensure countdown timer is always running
                WF3._startMonitorTimer();
                // Instant live update: patch activity tags/status from WS data
                WF3._liveUpdateActivityDetail(data);
                // Slow full refresh for duration/runs data (10s throttle)
                if (WF3._monitorSelectedAccountId && !WF3._monDetailRefreshPending) {
                    WF3._monDetailRefreshPending = true;
                    setTimeout(() => {
                        WF3._monDetailRefreshPending = false;
                        if (WF3._monitorSelectedAccountId) {
                            WF3._onMonitorAccountClick(WF3._monitorSelectedAccountId);
                        }
                    }, 10000);
                }
            }

            // Gate: Activity tab updates only for the selected activity group
            if (groupId != WF3.activitySelectedGroupId) return;

            // Update activity badges DIRECTLY (works even if queue panel isn't visible)
            WF3._updateActivityStatuses(data);

            // Also render the account queue UI if the log panel exists
            if (typeof WF3.renderAccountQueue === 'function') {
                WF3.renderAccountQueue(data);
            }

            // Refresh KPI bar (throttled to avoid spam)
            WF3._scheduleKpiRefresh();
        });

        // ── Monitor Timeline events (always buffer, regardless of active tab) ──
        wsClient.on('timeline_event', (data) => {
            if (!WF3) return;
            if (WF3._monitorGroupId && data.group_id != WF3._monitorGroupId) return;
            WF3._pushTimelineEvent(data);
        });

        wsClient.on('workflow_log', (data) => {
            if (!WF3) return;
            WF3._pushTimelineEvent({
                ts: Date.now() / 1000,
                icon: data.log_type === 'ok' ? '\u2705' : data.log_type === 'err' ? '\u274c' : '\u2139\ufe0f',
                message: `Emu ${data.emulator_index}: ${data.message}`,
                emu_index: data.emulator_index,
            });
        });

        wsClient.on('activity_started', (data) => {
            if (!WF3) return;
            if (WF3._monitorGroupId && data.group_id != WF3._monitorGroupId) return;
            WF3._pushTimelineEvent({
                ts: Date.now() / 1000,
                icon: '\u25b6\ufe0f',
                message: `${data.account_id || ''}: Started ${data.activity_name || data.activity_id || ''}`,
                emu_index: data.emu_index,
            });
        });

        wsClient.on('activity_completed', (data) => {
            if (!WF3) return;
            if (WF3._monitorGroupId && data.group_id != WF3._monitorGroupId) return;
            WF3._pushTimelineEvent({
                ts: Date.now() / 1000,
                icon: '\u2705',
                message: `${data.account_id || ''}: ${data.activity_name || data.activity_id || ''} completed`,
                emu_index: data.emu_index,
            });
        });

        wsClient.on('activity_failed', (data) => {
            if (!WF3) return;
            if (WF3._monitorGroupId && data.group_id != WF3._monitorGroupId) return;
            WF3._pushTimelineEvent({
                ts: Date.now() / 1000,
                icon: '\u274c',
                message: `${data.account_id || ''}: ${data.activity_name || data.activity_id || ''} failed`,
                emu_index: data.emu_index,
            });
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
    <div class="wf-log-line log-info" >
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

    // ═══════════════════════════════════════════════
    // MONITOR TAB — Standalone Real-time Overview
    // ═══════════════════════════════════════════════
    _monitorGroupId: null,
    _monitorLastData: null,
    _monitorSelectedAccountId: null,
    _monitorTimerInterval: null,
    _monitorKpiThrottle: null,
    _monTimelineEvents: [],

    async _initMonitorTab() {
        // Populate group dropdown using loadGroupsData
        try {
            if (!this.di) await this._initDI();
            const res = await this.di.groupRepo.getAll();
            const sel = document.getElementById('mon-group-filter');
            if (sel && res.ok) {
                const current = sel.value;
                sel.innerHTML = '<option value="">Select Group...</option>' +
                    (res.data || []).map(g => `<option value="${g.id}">${g.name} (${JSON.parse(g.account_ids || '[]').length})</option>`).join('');
                // Restore selection
                if (current) sel.value = current;
                else if (this._monitorGroupId) sel.value = this._monitorGroupId;
            }
        } catch (e) {
            console.warn('[Monitor] Failed to load groups:', e);
        }

        // If we already have a group selected, refresh
        if (this._monitorGroupId) {
            this._refreshMonitor();
        }

        // Restore timeline open state from localStorage
        try {
            if (localStorage.getItem('mon_timeline_open') === '1') {
                const panel = document.getElementById('mon-timeline');
                const text = document.getElementById('mon-tl-toggle-text');
                if (panel) { panel.style.display = ''; this._renderTimeline(); }
                if (text) text.textContent = 'Hide Timeline \u25b2';
            }
        } catch (e) {}
    },

    async _onMonitorGroupChange(groupId) {
        this._monitorGroupId = groupId ? parseInt(groupId) : null;
        this._monitorSelectedAccountId = null;
        this._monitorLastData = null;

        // Reset detail panel
        const detail = document.getElementById('mon-detail-content');
        if (detail) detail.innerHTML = '<div class="mon-empty">Click an account to view activities</div>';

        if (!groupId) {
            document.getElementById('mon-kpi-bar').style.display = 'none';
            document.getElementById('mon-queue-list').innerHTML = '<div class="mon-empty">Select a group to view accounts</div>';
            document.getElementById('mon-status-badge').className = 'mon-badge mon-badge-idle';
            document.getElementById('mon-status-badge').textContent = 'IDLE';
            this._stopMonitorTimer();
            return;
        }

        await this._refreshMonitor();
    },

    async _refreshMonitor() {
        if (!this._monitorGroupId) return;

        try {
            // Fetch bot status for this group
            const res = await fetch(`/api/bot/status?group_id=${this._monitorGroupId}`);
            const json = await res.json();

            if (json.status === 'ok' && json.data) {
                this._monitorLastData = json.data;
                this._renderMonitorQueue(json.data);
                this._updateMonitorStatusBadge(json.data);
                this._startMonitorTimer();
            } else {
                // Bot not running — show accounts from group data
                this._monitorLastData = null;
                this._renderMonitorQueueFromGroup();
                this._updateMonitorStatusBadge(null);
                // Keep timer alive — cooldowns persist even when bot is idle
                this._startMonitorTimer();
            }

            // Fetch KPI
            this._renderMonitorKpi(this._monitorGroupId);
        } catch (e) {
            console.warn('[Monitor] Refresh failed:', e);
        }
    },

    _updateMonitorStatusBadge(data) {
        const badge = document.getElementById('mon-status-badge');
        const progress = document.getElementById('mon-progress');
        const smartWait = document.getElementById('mon-smart-wait');
        if (!badge) return;

        if (!data) {
            badge.className = 'mon-badge mon-badge-idle';
            badge.textContent = 'IDLE';
            if (progress) progress.style.display = 'none';
            if (smartWait) smartWait.style.display = 'none';
        } else if (data.stop_requested) {
            badge.className = 'mon-badge mon-badge-stopping';
            badge.textContent = 'STOPPING';
            if (progress) progress.style.display = 'none';
            if (smartWait) smartWait.style.display = 'none';
        } else if (data.is_running) {
            badge.className = 'mon-badge mon-badge-running';
            badge.textContent = `RUNNING · Cycle ${data.cycle || 1}`;

            // Account progress
            if (progress) {
                progress.style.display = '';
                progress.textContent = `Account: ${(data.current_idx || 0) + 1}/${data.total_accounts || 0}`;
            }

            // Smart Wait indicator
            const sw = data.smart_wait_active;
            if (smartWait && sw && sw.account_id && sw.remaining_sec > 0) {
                smartWait.style.display = '';
                smartWait.textContent = '';
                const clockSvg = document.createElement('span');
                clockSvg.innerHTML = this._monIcon('clock');
                clockSvg.style.marginRight = '4px';
                smartWait.appendChild(clockSvg);
                smartWait.appendChild(document.createTextNode(`Smart Wait: ${this._formatCD(sw.remaining_sec)}`));
            } else if (smartWait) {
                smartWait.style.display = 'none';
            }
        } else {
            badge.className = 'mon-badge mon-badge-idle';
            badge.textContent = 'STOPPED';
            if (progress) progress.style.display = 'none';
            if (smartWait) smartWait.style.display = 'none';
        }
    },

    async _renderMonitorKpi(groupId) {
        if (!groupId) return;
        // Throttle to avoid spam
        if (this._monitorKpiThrottle) return;
        this._monitorKpiThrottle = setTimeout(() => { this._monitorKpiThrottle = null; }, 5000);

        try {
            const res = await fetch(`/api/monitor/kpi-summary?group_id=${groupId}`);
            if (!res.ok) return;
            const json = await res.json();
            if (json.status !== 'ok' || !json.data) return;

            const bar = document.getElementById('mon-kpi-bar');
            if (bar) bar.style.display = '';

            const d = json.data;
            const set = (id, val, cls) => {
                const el = document.getElementById(id);
                if (!el) return;
                el.textContent = val;
                el.className = 'kpi-value' + (cls ? ' ' + cls : '');
            };

            if (d.fairness_index != null) {
                const cls = d.fairness_index >= 0.85 ? 'kpi-good' : d.fairness_index >= 0.7 ? 'kpi-warn' : 'kpi-bad';
                set('mon-kpi-fairness', d.fairness_index.toFixed(2), cls);
            } else set('mon-kpi-fairness', '—');

            if (d.success_rate != null) {
                const cls = d.success_rate >= 95 ? 'kpi-good' : d.success_rate >= 85 ? 'kpi-warn' : 'kpi-bad';
                set('mon-kpi-success', d.success_rate.toFixed(1) + '%', cls);
            } else set('mon-kpi-success', '—');

            const ppCls = (d.ping_pong_count || 0) === 0 ? 'kpi-good' : 'kpi-bad';
            set('mon-kpi-pingpong', String(d.ping_pong_count || 0), ppCls);

            if (d.execute_time_pct != null) {
                const cls = d.execute_time_pct >= 65 ? 'kpi-good' : d.execute_time_pct >= 50 ? 'kpi-warn' : 'kpi-bad';
                set('mon-kpi-exectime', d.execute_time_pct.toFixed(1) + '%', cls);
            } else set('mon-kpi-exectime', '—');

            if (d.cycle != null && d.coverage_pct != null) {
                set('mon-kpi-coverage', `C${d.cycle} · ${d.coverage_pct.toFixed(0)}%`, 'kpi-good');
            } else if (d.total_runs_today > 0) {
                set('mon-kpi-coverage', `${d.total_runs_today} runs`, '');
            } else set('mon-kpi-coverage', 'Idle');
        } catch (e) {
            console.warn('[Monitor] KPI fetch failed:', e);
        }
    },
    // ── SVG Icon Helper (Lucide set, 14x14) ──
    _monIcon(name, cls = '') {
        const s = 14;
        const a = `width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`;
        const icons = {
            monitor:      `<svg ${a} class="${cls}"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`,
            'play-circle':`<svg ${a} class="${cls}"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>`,
            'check-circle':`<svg ${a} class="${cls}"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
            'x-circle':   `<svg ${a} class="${cls}"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
            clock:        `<svg ${a} class="${cls}"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
            circle:       `<svg ${a} class="${cls}"><circle cx="12" cy="12" r="10"/></svg>`,
            'skip-forward':`<svg ${a} class="${cls}"><polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19"/></svg>`,
            'refresh-cw': `<svg ${a} class="${cls}"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`,
            repeat:       `<svg ${a} class="${cls}"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>`,
            moon:         `<svg ${a} class="${cls}"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`,
            'arrow-right':`<svg ${a} class="${cls}"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
            user:         `<svg ${a} class="${cls}"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
        };
        return icons[name] || '';
    },

    _renderMonitorQueue(data) {
        const list = document.getElementById('mon-queue-list');
        if (!list) return;

        const accounts = data.accounts || [];
        if (!accounts.length) {
            list.innerHTML = '<div class="mon-empty">No accounts in queue</div>';
            return;
        }

        const nextIdx = data.is_running ? (data.current_idx + 1) % accounts.length : -1;

        // Group by emu_index
        const byEmu = {};
        accounts.forEach((acc, idx) => {
            const key = acc.emu_index ?? 'unassigned';
            if (!byEmu[key]) byEmu[key] = [];
            byEmu[key].push({ ...acc, _queueIdx: idx });
        });

        let html = '';
        for (const [emuIdx, accs] of Object.entries(byEmu)) {
            const emuLabel = emuIdx === 'unassigned' ? 'Unassigned' : `Emulator ${emuIdx}`;
            html += `<div class="mon-emu-group">
                <div class="mon-emu-header">${this._monIcon('monitor', 'mon-emu-svg')} ${emuLabel} <span class="mon-emu-count">${accs.length}</span></div>`;

            for (const acc of accs) {
                const isCurrent = acc._queueIdx === data.current_idx && data.is_running;
                const isNext = acc._queueIdx === nextIdx && data.is_running && !isCurrent;
                const statusCls = acc.status === 'running' ? 'mon-st-running'
                    : acc.status === 'done' || acc.status === 'completed' || acc.status === 'success' ? 'mon-st-done'
                    : acc.status === 'error' ? 'mon-st-error'
                    : acc.status === 'skipped' ? 'mon-st-skipped'
                    : 'mon-st-pending';

                const cdSec = acc.cooldown_remaining_sec || 0;
                const selected = this._monitorSelectedAccountId == acc.id ? ' mon-acc-selected' : '';
                const nextCls = isNext ? ' mon-acc-next' : '';

                // Status tag with SVG icon
                let statusHtml = '';
                if (isCurrent) {
                    const actName = data.current_activity?.name || 'Activity';
                    statusHtml = `<span class="mon-status-tag tag-running">${this._monIcon('play-circle')} ${actName}</span>`;
                } else if (acc.status === 'done' || acc.status === 'completed' || acc.status === 'success') {
                    statusHtml = `<span class="mon-status-tag tag-done">${this._monIcon('check-circle')} Done</span>`;
                } else if (acc.status === 'error') {
                    statusHtml = `<span class="mon-status-tag tag-error">${this._monIcon('x-circle')} Error</span>`;
                } else if (acc.status === 'skipped') {
                    statusHtml = `<span class="mon-status-tag tag-skipped">${this._monIcon('skip-forward')} Skipped</span>`;
                } else if (cdSec > 0) {
                    statusHtml = `<span class="mon-status-tag tag-cooldown">${this._monIcon('clock')} <span class="mon-cd" data-cd="${cdSec}">${this._formatCD(cdSec)}</span></span>`;
                } else if (isNext) {
                    statusHtml = `<span class="mon-status-tag tag-next">${this._monIcon('arrow-right')} Next</span>`;
                } else {
                    statusHtml = `<span class="mon-status-tag tag-pending">${this._monIcon('circle')} Pending</span>`;
                }

                // Sub-info line
                const subParts = [
                    acc.emu_index != null ? `Emu ${acc.emu_index}` : '',
                    acc.game_id || '',
                    acc.last_run_time ? this._timeAgo(acc.last_run_time) : 'Never',
                ].filter(Boolean).join(' · ');

                html += `<div class="mon-account-row ${statusCls}${isCurrent ? ' mon-acc-current' : ''}${nextCls}${selected}" 
                    data-acc-id="${acc.id}" onclick="WF3._onMonitorAccountClick(${acc.id})">
                    <span class="mon-acc-order">${acc._queueIdx + 1}</span>
                    <div class="mon-acc-info">
                        <span class="mon-acc-name">${acc.lord_name || acc.game_id || 'Unknown'}</span>
                        <span class="mon-acc-sub">${subParts}</span>
                    </div>
                    ${statusHtml}
                </div>`;
            }
            html += '</div>';
        }

        list.innerHTML = html;

        // Auto-scroll to running account
        const running = list.querySelector('.mon-acc-current');
        if (running) running.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    },

    async _renderMonitorQueueFromGroup() {
        // When bot is not running, show accounts from group config
        const list = document.getElementById('mon-queue-list');
        if (!list) return;

        try {
            if (!this.di) await this._initDI();
            const res = await this.di.groupRepo.getAll();
            if (!res.ok) return;
            const group = (res.data || []).find(g => g.id == this._monitorGroupId);
            if (!group) {
                list.innerHTML = '<div class="mon-empty">Group not found</div>';
                return;
            }

            const accIds = JSON.parse(group.account_ids || '[]');
            if (!accIds.length) {
                list.innerHTML = '<div class="mon-empty">No accounts in this group</div>';
                return;
            }

            // Fetch real account data for names
            let accMap = {};
            try {
                const accRes = await fetch('/api/accounts');
                const accJson = await accRes.json();
                const accList = accJson.status === 'ok' ? (accJson.data || []) : (Array.isArray(accJson) ? accJson : []);
                for (const a of accList) {
                    accMap[a.id || a.game_id] = a;
                }
            } catch (_) { /* fallback to ID */ }

            list.innerHTML = accIds.map((id, i) => {
                const acc = accMap[id] || {};
                const name = acc.lord_name || acc.game_id || `Account #${id}`;
                return `<div class="mon-account-row mon-st-pending" data-acc-id="${id}" onclick="WF3._onMonitorAccountClick(${id})">
                    <span class="mon-acc-order">${i + 1}</span>
                    <div class="mon-acc-info">
                        <span class="mon-acc-name">${name}</span>
                        <span class="mon-acc-sub">Idle</span>
                    </div>
                    <span class="mon-status-tag tag-pending">${this._monIcon('circle')} Idle</span>
                </div>`;
            }).join('');
        } catch (e) {
            list.innerHTML = '<div class="mon-empty">Failed to load accounts</div>';
        }
    },

    async _onMonitorAccountClick(accountId) {
        this._monitorSelectedAccountId = accountId;

        // Highlight selected row
        document.querySelectorAll('.mon-account-row').forEach(el => {
            el.classList.toggle('mon-acc-selected', el.dataset.accId == accountId);
        });

        const actPane = document.getElementById('mon-detail-activities');
        const logPane = document.getElementById('mon-detail-logs');
        // Show skeleton in whichever tab is active
        const skel = '<div class="mon-skeleton"><div class="mon-skel-bar skel-w80"></div><div class="mon-skel-bar skel-w60"></div><div class="mon-skel-bar skel-w90"></div><div class="mon-skel-bar skel-w50"></div></div>';
        if (actPane) actPane.innerHTML = skel;
        if (logPane) logPane.innerHTML = skel;

        try {
            const res = await fetch(`/api/monitor/account-activities?account_id=${accountId}&group_id=${this._monitorGroupId || ''}`);
            const json = await res.json();
            if (json.status === 'ok' && json.data) {
                this._renderMonitorDetail(json.data, accountId);
            } else {
                if (actPane) actPane.innerHTML = '<div class="mon-empty">No activity data for today</div>';
                if (logPane) logPane.innerHTML = '<div class="mon-empty">No logs available</div>';
            }
        } catch (e) {
            if (actPane) actPane.innerHTML = '<div class="mon-empty">Failed to fetch activity data</div>';
            if (logPane) logPane.innerHTML = '<div class="mon-empty">Failed to fetch logs</div>';
        }
    },

    /**
     * Instantly patch activity row DOM elements from WebSocket data.
     * Updates tags (Running/Next/Done/Error) and row highlight classes
     * without re-fetching from the API.
     */
    _liveUpdateActivityDetail(wsData) {
        if (!this._monitorSelectedAccountId) return;

        const actStatuses = wsData.activity_statuses || {};
        const currentActivity = wsData.current_activity || '';
        const currentAccId = String((wsData.accounts || [])[wsData.current_idx]?.id || '');
        const selectedAccId = String(this._monitorSelectedAccountId);
        const isSelectedRunning = (currentAccId === selectedAccId);

        const rows = document.querySelectorAll('#mon-detail-activities .mon-activity-row');
        if (!rows.length) return;

        // Build ordered list of activity names from DOM
        const actNames = [];
        rows.forEach(r => {
            const nameEl = r.querySelector('.mon-act-name');
            if (nameEl) actNames.push(nameEl.textContent.trim());
        });

        // Determine running and next indices for selected account
        let runningIdx = -1;
        let nextIdx = -1;
        if (isSelectedRunning) {
            runningIdx = actNames.indexOf(currentActivity);
            if (runningIdx >= 0) {
                // Next = first pending after running
                for (let i = runningIdx + 1; i < actNames.length; i++) {
                    const st = actStatuses[actNames[i]];
                    if (!st || st === 'pending') { nextIdx = i; break; }
                }
            }
        }

        rows.forEach((row, i) => {
            const name = actNames[i];
            const status = actStatuses[name] || '';
            const tagContainer = row.querySelector('.mon-act-w-tag');

            // Update row class
            row.classList.remove('mon-act-current', 'mon-act-next');
            if (i === runningIdx) {
                row.classList.add('mon-act-current');
            } else if (i === nextIdx) {
                row.classList.add('mon-act-next');
            }

            // Update tag
            if (tagContainer) {
                let tagHtml = '';
                if (i === runningIdx) {
                    tagHtml = `<span class="mon-act-tag mon-tag-running">${this._monIcon('play-circle')} Running</span>`;
                } else if (i === nextIdx) {
                    tagHtml = `<span class="mon-act-tag mon-tag-next">${this._monIcon('arrow-right')} Next</span>`;
                } else if (status === 'done') {
                    tagHtml = `<span class="mon-act-tag mon-tag-done">${this._monIcon('check-circle')} Done</span>`;
                } else if (status === 'error') {
                    tagHtml = `<span class="mon-act-tag mon-tag-error">${this._monIcon('x-circle')} Error</span>`;
                }
                tagContainer.innerHTML = tagHtml;
            }
        });
    },

    _renderMonitorDetail(data, accountId) {
        const actPane = document.getElementById('mon-detail-activities');
        const logPane = document.getElementById('mon-detail-logs');
        if (!actPane) return;

        // Find full account info from last data or DOM
        let accName = `Account #${accountId}`;
        let accInfo = null;
        if (this._monitorLastData) {
            accInfo = (this._monitorLastData.accounts || []).find(a => a.id == accountId);
            if (accInfo) accName = accInfo.lord_name || accInfo.game_id || accName;
        }
        // Fallback: read name from the account queue card
        if (accName.startsWith('Account #')) {
            const accCard = document.querySelector(`.mon-account-row[data-acc-id="${accountId}"] .mon-acc-name`);
            if (accCard && accCard.textContent) accName = accCard.textContent.trim();
        }

        // Build enriched header sub-line
        let headerSub = '';
        if (accInfo) {
            const parts = [];
            if (accInfo.emu_index != null) parts.push(`Emu ${accInfo.emu_index}`);
            if (accInfo.game_id) parts.push(`ID ${accInfo.game_id}`);
            const cdSec = accInfo.cooldown_remaining_sec || 0;
            if (cdSec > 0) {
                parts.push(`CD ${this._formatCD(cdSec)}`);
            } else if (accInfo.status) {
                const stLabel = accInfo.status.charAt(0).toUpperCase() + accInfo.status.slice(1);
                parts.push(`Status: ${stLabel}`);
            }
            headerSub = parts.join(' · ');
        }

        const headerHtml = `<div class="mon-detail-header">
            <div><div class="mon-detail-name">${this._monIcon('user')} ${accName}</div>${headerSub ? `<div class="mon-acc-sub">${headerSub}</div>` : ''}</div>
            <span class="mon-detail-date">${data.date}</span>
        </div>`;

        // ── Activities Tab ──
        const activities = data.activities || [];
        if (!activities.length) {
            actPane.innerHTML = headerHtml + '<div class="mon-empty">No activities recorded today</div>';
        } else {
            // Determine running and next activity indices
            let runningIdx = -1;
            let nextIdx = -1;
            for (let i = 0; i < activities.length; i++) {
                if (activities[i].last_status === 'RUNNING') { runningIdx = i; break; }
            }
            if (runningIdx >= 0) {
                for (let i = runningIdx + 1; i < activities.length; i++) {
                    const st = activities[i].last_status;
                    if (!st || st === 'PENDING') { nextIdx = i; break; }
                }
            }

            // Column header
            let actHtml = headerHtml + `<div class="mon-act-header">
                <span class="mon-act-h-name">Activity</span>
                <span class="mon-act-h-col mon-act-w-tag"></span>
                <span class="mon-act-h-col mon-act-w-status">Status</span>
                <span class="mon-act-h-col mon-act-w-dur">Time</span>
                <span class="mon-act-h-col mon-act-w-runs">Runs</span>
            </div>`;

            actHtml += '<div class="mon-activity-list">';
            for (let i = 0; i < activities.length; i++) {
                const act = activities[i];
                const isCurrent = (i === runningIdx);
                const isNext = (i === nextIdx);

                // Row highlight class
                const rowCls = isCurrent ? 'mon-act-current' : isNext ? 'mon-act-next' : '';

                // Left-side tag (clear visual labels)
                let tagHtml = '';
                if (isCurrent) {
                    tagHtml = `<span class="mon-act-tag mon-tag-running">${this._monIcon('play-circle')} Running</span>`;
                } else if (isNext) {
                    tagHtml = `<span class="mon-act-tag mon-tag-next">${this._monIcon('arrow-right')} Next</span>`;
                } else if (act.last_status === 'SUCCESS') {
                    tagHtml = `<span class="mon-act-tag mon-tag-done">${this._monIcon('check-circle')} Done</span>`;
                } else if (act.last_status === 'FAILED') {
                    tagHtml = `<span class="mon-act-tag mon-tag-error">${this._monIcon('x-circle')} Error</span>`;
                }

                // Error icon (inline tooltip)
                const errIcon = act.last_error
                    ? `<span class="mon-act-err-icon" title="${act.last_error.replace(/"/g, '&quot;')}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></span>`
                    : '';

                // Status column: Ready or Cooldown MM:SS
                let statusHtml = '';
                const cdSec = act.cooldown_remaining_sec || 0;
                if (cdSec > 0) {
                    const mm = String(Math.floor(cdSec / 60)).padStart(2, '0');
                    const ss = String(cdSec % 60).padStart(2, '0');
                    statusHtml = `<span class="mon-act-cd mon-act-w-status" data-cd="${cdSec}">${mm}:${ss}</span>`;
                } else {
                    statusHtml = '<span class="mon-act-status-ready mon-act-w-status">Ready</span>';
                }

                // Last exec time
                const durHtml = act.total_duration_ms > 0
                    ? `<span class="mon-act-dur mon-act-w-dur">${(act.total_duration_ms / 1000).toFixed(0)}s</span>`
                    : '<span class="mon-act-dur mon-act-w-dur">—</span>';

                // Runs count
                const runsHtml = `<span class="mon-act-runs mon-act-w-runs">${act.successes || 0}/${act.runs || 0}</span>`;

                actHtml += `<div class="mon-activity-row ${rowCls}">
                    <div class="mon-act-left">
                        <span class="mon-act-name">${act.activity_name}</span>
                        ${errIcon}
                    </div>
                    <div class="mon-act-right">
                        <span class="mon-act-w-tag">${tagHtml}</span>
                        ${statusHtml}
                        ${durHtml}
                        ${runsHtml}
                    </div>
                </div>`;
            }
            actHtml += '</div>';
            actPane.innerHTML = actHtml;
        }

        // ── Logs Tab ──
        const logs = data.raw_logs || [];
        if (!logPane) return;
        if (!logs.length) {
            logPane.innerHTML = headerHtml + '<div class="mon-empty">No logs recorded today</div>';
            return;
        }
        let logHtml = headerHtml;
        for (const log of logs.slice(0, 50)) {
            const time = log.started_at ? log.started_at.split('T')[1]?.substring(0, 8) || '' : '';
            const stCls = log.status === 'SUCCESS' ? 'mon-log-ok' : log.status === 'FAILED' ? 'mon-log-err' : '';
            logHtml += `<div class="mon-log-row ${stCls}">
                <span class="mon-log-time">${time}</span>
                <span class="mon-log-name">${log.activity_name}</span>
                <span class="mon-log-st">${log.status}</span>
            </div>`;
        }
        logPane.innerHTML = logHtml;
    },

    _switchDetailTab(tab) {
        const actPane = document.getElementById('mon-detail-activities');
        const logPane = document.getElementById('mon-detail-logs');
        document.querySelectorAll('.mon-dtab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        if (actPane) actPane.style.display = tab === 'activities' ? '' : 'none';
        if (logPane) logPane.style.display = tab === 'logs' ? '' : 'none';
    },

    // ── Cooldown Timer ──
    _startMonitorTimer() {
        if (this._monitorTimerInterval) return;
        this._monitorTimerInterval = setInterval(() => {
            document.querySelectorAll('.mon-cd').forEach(el => {
                let cd = parseFloat(el.dataset.cd) - 1;
                if (cd <= 0) {
                    el.remove();
                } else {
                    el.dataset.cd = cd;
                    el.textContent = this._formatCD(cd);
                }
            });
            // Tick activity detail cooldown countdowns
            document.querySelectorAll('.mon-act-cd').forEach(el => {
                let cd = parseInt(el.dataset.cd, 10) - 1;
                if (cd <= 0) {
                    el.textContent = '00:00';
                    el.dataset.cd = '0';
                } else {
                    el.dataset.cd = cd;
                    const mm = String(Math.floor(cd / 60)).padStart(2, '0');
                    const ss = String(cd % 60).padStart(2, '0');
                    el.textContent = `${mm}:${ss}`;
                }
            });
        }, 1000);
    },

    _stopMonitorTimer() {
        if (this._monitorTimerInterval) {
            clearInterval(this._monitorTimerInterval);
            this._monitorTimerInterval = null;
        }
    },

    _formatCD(sec) {
        sec = Math.max(0, Math.floor(sec));
        if (sec >= 3600) {
            const h = Math.floor(sec / 3600);
            const m = Math.floor((sec % 3600) / 60);
            return m > 0 ? `${h}h ${m}m` : `${h}h`;
        }
        if (sec >= 60) {
            const m = Math.floor(sec / 60);
            const s = sec % 60;
            return s > 0 ? `${m}m ${s}s` : `${m}m`;
        }
        return `${sec}s`;
    },

    _timeAgo(epochSec) {
        const diff = Math.floor(Date.now() / 1000 - epochSec);
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    },

    // ── Timeline Panel ──
    _toggleTimeline() {
        const panel = document.getElementById('mon-timeline');
        const text = document.getElementById('mon-tl-toggle-text');
        if (!panel) return;
        const isOpen = panel.style.display !== 'none';
        panel.style.display = isOpen ? 'none' : '';
        if (text) text.textContent = isOpen ? 'Show Timeline \u25bc' : 'Hide Timeline \u25b2';
        try { localStorage.setItem('mon_timeline_open', isOpen ? '0' : '1'); } catch (e) {}
        if (!isOpen) this._renderTimeline();
    },

    _pushTimelineEvent(evt) {
        this._monTimelineEvents.push(evt);
        if (this._monTimelineEvents.length > 200) {
            this._monTimelineEvents = this._monTimelineEvents.slice(-200);
        }
        // Only render if panel is visible
        const panel = document.getElementById('mon-timeline');
        if (panel && panel.style.display !== 'none') {
            this._renderTimeline();
        }
    },

    _renderTimeline() {
        const list = document.getElementById('mon-timeline-list');
        if (!list) return;
        if (!this._monTimelineEvents.length) {
            list.innerHTML = '<div class="mon-empty">No events yet</div>';
            return;
        }
        // Map backend emoji icons → SVG icon names
        const iconMap = {
            '\u{1F504}': 'refresh-cw',  // 🔄
            '\u2705': 'check-circle',    // ✅
            '\u274C': 'x-circle',        // ❌
            '\u25B6\uFE0F': 'play-circle', // ▶️
            '\u23F3': 'clock',           // ⏳
            '\u{1F501}': 'repeat',       // 🔁
            '\u{1F4A4}': 'moon',         // 💤
            '\u2139\uFE0F': 'circle',    // ℹ️
        };
        // Render newest first
        let html = '';
        for (let i = this._monTimelineEvents.length - 1; i >= 0; i--) {
            const e = this._monTimelineEvents[i];
            const t = e.ts ? new Date(e.ts * 1000).toLocaleTimeString('en-GB', {hour12: false}) : '';
            const svgName = iconMap[e.icon] || 'circle';
            const svgHtml = this._monIcon(svgName, 'mon-tl-svg');
            html += `<div class="mon-tl-row">
                <span class="mon-tl-time">${t}</span>
                <span class="mon-tl-icon">${svgHtml}</span>
                <span class="mon-tl-msg">${e.message || ''}</span>
            </div>`;
        }
        list.innerHTML = html;
        list.scrollTop = 0;
    },

    _clearTimeline() {
        this._monTimelineEvents = [];
        const list = document.getElementById('mon-timeline-list');
        if (list) list.innerHTML = '<div class="mon-empty">No events yet</div>';
    },
};


