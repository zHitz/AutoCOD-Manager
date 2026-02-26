/**
 * Accounts Data Page
 * Shows a detailed table of Game Accounts with an off-canvas Slide Profile View.
 */
const AccountsPage = {
    _mockData: [
        {
            id: 1, emuName: 'LDPlayer-01', ingameName: 'DragonSlayer', pow: '12.5',
            loginMethod: 'Google', email: 'dragon@gmail.com', provider: 'Global',
            emulator: '#1', hallLvl: 25, marketLvl: 24, alliance: '[KOR] Warriors',
            accountsTotal: 3, accMatching: 'Yes', note: 'Main account', status: 'online', trendToken: 'up',
            gold: '1.2', wood: '5.5', ore: '2.1', petToken: 450
        },
        {
            id: 2, emuName: 'LDPlayer-02', ingameName: 'FarmBot_01', pow: '2.1',
            loginMethod: 'Facebook', email: 'farm01@yahoo.com', provider: 'Global',
            emulator: '#2', hallLvl: 11, marketLvl: 10, alliance: 'None',
            accountsTotal: 1, accMatching: 'No', note: 'Farm wood fast', status: 'offline', trendToken: 'up',
            gold: '0.1', wood: '12.0', ore: '0.5', petToken: 12
        },
        {
            id: 3, emuName: 'LDPlayer-03', ingameName: 'FarmBot_02', pow: '1.8',
            loginMethod: 'Facebook', email: 'farm02@yahoo.com', provider: 'Global',
            emulator: '#3', hallLvl: 9, marketLvl: 9, alliance: 'None',
            accountsTotal: 1, accMatching: 'No', note: 'Farm ore', status: 'online', trendToken: 'down',
            gold: '0.2', wood: '1.0', ore: '15.5', petToken: 5
        },
        {
            id: 4, emuName: 'LDPlayer-04', ingameName: 'SniperWolf', pow: '8.4',
            loginMethod: 'Apple', email: '-', provider: 'Global',
            emulator: '#4', hallLvl: 22, marketLvl: 20, alliance: '[US] Eagles',
            accountsTotal: 2, accMatching: 'Yes', note: 'Alt attack', status: 'offline', trendToken: 'up',
            gold: '4.5', wood: '2.2', ore: '3.1', petToken: 120
        },
        {
            id: 5, emuName: 'LDPlayer-05', ingameName: 'MinerKing', pow: '3.5',
            loginMethod: 'Google', email: 'miner@gmail.com', provider: 'Asia',
            emulator: '#5', hallLvl: 15, marketLvl: 15, alliance: '[KOR] Warriors',
            accountsTotal: 5, accMatching: 'Yes', note: 'Supply main', status: 'online', trendToken: 'up',
            gold: '25.0', wood: '18.0', ore: '22.0', petToken: 60
        }
    ],

    _selectedAccountId: null,
    _activeDetailTab: 'overview',
    _viewMode: 'table',

    render() {
        return `
            <style>
                /* ── TABLE CORE ── */
                .accounts-table { border-collapse: collapse; width: 100%; }
                .accounts-table th, .accounts-table td { white-space: nowrap; }

                /* Frozen columns */
                .freeze-col-1 { position: sticky; left: 0; z-index: 5; background: var(--card); border-right: 1px solid var(--border); }
                .freeze-col-2 { position: sticky; left: 48px; z-index: 5; background: var(--card); }
                .freeze-col-3 { position: sticky; left: 158px; z-index: 5; background: var(--card); border-right: 2px solid var(--border); }
                .stt-col { width: 48px !important; min-width: 48px; max-width: 48px; }

                /* Row states */
                .account-row { cursor: pointer; transition: background 0.15s; background: var(--card); }
                .account-row:hover { background: var(--accent); }
                .account-row:hover .freeze-col-1,
                .account-row:hover .freeze-col-2,
                .account-row:hover .freeze-col-3 { background: var(--accent); }
                .account-row.selected { background: var(--accent); }
                .account-row.selected .freeze-col-1,
                .account-row.selected .freeze-col-2,
                .account-row.selected .freeze-col-3 { background: var(--accent); }
                /* left accent bar on hover */
                .account-row td:first-child { border-left: 3px solid transparent; transition: border-color 0.15s; }
                .account-row:hover td:first-child { border-left-color: var(--primary); }
                .account-row.selected td:first-child { border-left-color: var(--primary); }

                /* Hover arrow for actions column */
                .hover-actions-arrow {
                    opacity: 0; transition: opacity 0.2s, transform 0.2s;
                    transform: translateX(-4px); display: flex; align-items: center; gap: 4px;
                    color: var(--primary); font-weight: 600; font-size: 13px;
                }
                .account-row:hover .hover-actions-arrow { opacity: 1; transform: translateX(0); }

                /* Badges */
                .badge-status-yes { background: rgba(16,185,129,0.1); color: var(--emerald-500); border: 1px solid rgba(16,185,129,0.25); border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 700; }
                .badge-status-no  { background: rgba(239,68,68,0.1);  color: var(--red-500);     border: 1px solid rgba(239,68,68,0.25);  border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 700; }

                /* Resource values in table */
                .resource-val { font-weight: 600; letter-spacing: 0.3px; font-variant-numeric: tabular-nums; }

                /* Status dots */
                .status-dot-on  { width: 7px; height: 7px; border-radius: 50%; background: var(--emerald-500); box-shadow: 0 0 5px var(--emerald-500); display: inline-block; flex-shrink: 0; }
                .status-dot-off { width: 7px; height: 7px; border-radius: 50%; background: var(--border); display: inline-block; flex-shrink: 0; }

                /* Table header group row */
                .th-group { background: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: 0.6px; text-transform: uppercase; color: var(--muted-foreground); padding: 8px 16px; border-bottom: 1px solid var(--border); text-align: center; }
                .th-col { padding: 10px 14px; font-weight: 600; font-size: 12px; color: var(--muted-foreground); background: var(--card); border-bottom: 2px solid var(--border); white-space: nowrap; }
                .th-col.accent { color: var(--primary); }

                /* ── GRID / CARD LIST ── */
                .account-list { display: flex; flex-direction: column; gap: 8px; }

                .account-card {
                    background: var(--card); border: 1px solid var(--border);
                    border-radius: 10px; padding: 16px 20px;
                    display: flex; align-items: center; gap: 16px;
                    cursor: pointer; transition: all 0.18s ease;
                    position: relative; overflow: hidden;
                }
                .account-card::before {
                    content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
                    border-radius: 3px 0 0 3px;
                }
                .account-card.status-online::before  { background: var(--emerald-500); }
                .account-card.status-offline::before { background: var(--red-500); }
                .account-card.status-idle::before    { background: var(--yellow-500); }
                .account-card:hover { border-color: var(--border); background: var(--accent); transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
                .account-card.status-offline { opacity: 0.75; }
                .account-card.status-offline:hover   { opacity: 1; }

                .card-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 1px; }
                .status-online  .card-dot { background: var(--emerald-500); box-shadow: 0 0 7px var(--emerald-500); }
                .status-offline .card-dot { background: var(--red-500);     box-shadow: 0 0 7px var(--red-500); }
                .status-idle    .card-dot { background: var(--yellow-500);  box-shadow: 0 0 7px var(--yellow-500); }

                .account-info { min-width: 180px; }
                .account-name { font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 7px; margin-bottom: 3px; }
                .alliance-badge { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: var(--muted); color: var(--muted-foreground); letter-spacing: 0.4px; }
                .account-emulator { font-size: 11px; color: var(--muted-foreground); font-family: monospace; }

                .account-power { flex: 1; min-width: 220px; }
                .power-label { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
                .power-value { font-size: 13px; font-weight: 600; color: var(--foreground); }
                .power-hall  { font-size: 11px; color: var(--muted-foreground); font-family: monospace; }
                .power-bar   { height: 4px; background: var(--muted); border-radius: 99px; overflow: hidden; }
                .power-fill  { height: 100%; border-radius: 99px; transition: width 0.8s cubic-bezier(0.4,0,0.2,1); }
                .status-online  .power-fill { background: linear-gradient(90deg, var(--emerald-400, #34d399), var(--emerald-300, #6ee7b7)); }
                .status-offline .power-fill { background: linear-gradient(90deg, var(--red-400, #f87171), var(--red-300, #fca5a5)); }
                .status-idle    .power-fill { background: linear-gradient(90deg, var(--yellow-400, #fbbf24), var(--yellow-300, #fde68a)); }
                .sync-time { font-size: 11px; color: var(--muted-foreground); margin-top: 5px; text-align: right; }

                .card-actions { display: flex; gap: 7px; align-items: center; flex-shrink: 0; }
                .card-btn-view { padding: 7px 14px; font-size: 12px; font-weight: 600; background: var(--accent); color: var(--primary); border: 1px solid var(--border); border-radius: 6px; cursor: pointer; transition: all 0.15s; font-family: inherit; display: flex; align-items: center; gap: 4px; }
                .card-btn-view:hover { background: var(--primary); color: #fff; }
                .card-btn-icon { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: var(--muted); border: 1px solid var(--border); border-radius: 6px; cursor: pointer; color: var(--muted-foreground); transition: all 0.15s; }
                .card-btn-icon:hover { color: var(--foreground); border-color: var(--border); }

                /* ── SLIDE PANEL ── */
                .slide-panel-overlay {
                    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(0,0,0,0.35); z-index: 1000;
                    opacity: 0; pointer-events: none; transition: opacity 0.3s ease;
                    backdrop-filter: blur(2px);
                }
                .slide-panel-overlay.active { opacity: 1; pointer-events: auto; }

                .slide-panel {
                    position: fixed; top: 0; right: 0; width: 960px; max-width: 95vw; height: 100vh;
                    background: var(--card); z-index: 1001;
                    box-shadow: -8px 0 40px rgba(0,0,0,0.12);
                    transform: translateX(100%); transition: transform 0.32s cubic-bezier(0.4,0,0.2,1);
                    display: flex; flex-direction: column;
                }
                .slide-panel.active { transform: translateX(0); }

                /* Panel header */
                .panel-header {
                    padding: 20px 28px; border-bottom: 1px solid var(--border);
                    display: flex; justify-content: space-between; align-items: flex-start;
                    background: var(--card); flex-shrink: 0;
                }
                .panel-body { flex: 1; overflow-y: auto; }

                /* Key stats strip below header */
                .panel-stats-strip {
                    display: flex; gap: 0; border-bottom: 1px solid var(--border);
                    background: var(--muted); flex-shrink: 0;
                }
                .panel-stat-item {
                    flex: 1; padding: 12px 20px; border-right: 1px solid var(--border);
                    display: flex; flex-direction: column; gap: 3px;
                }
                .panel-stat-item:last-child { border-right: none; }
                .panel-stat-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: var(--muted-foreground); }
                .panel-stat-value { font-size: 18px; font-weight: 800; color: var(--foreground); line-height: 1; }
                .panel-stat-sub { font-size: 11px; color: var(--muted-foreground); margin-top: 1px; }

                /* Panel tabs */
                .panel-tabs {
                    display: flex; gap: 0; border-bottom: 1px solid var(--border);
                    background: var(--card); flex-shrink: 0; padding: 0 28px;
                }
                .panel-tab {
                    padding: 13px 0; margin-right: 28px; color: var(--muted-foreground); cursor: pointer;
                    border-bottom: 2px solid transparent; font-weight: 600; font-size: 13px;
                    transition: all 0.18s; margin-bottom: -1px; user-select: none;
                }
                .panel-tab:hover { color: var(--foreground); }
                .panel-tab.active { color: var(--primary); border-bottom-color: var(--primary); }

                /* Tab content wrapper */
                .panel-tab-body { padding: 24px 28px; }

                /* ── OVERVIEW TAB STYLES ── */
                .ov-section-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted-foreground); margin-bottom: 10px; }
                .ov-row {
                    display: flex; justify-content: space-between; align-items: center;
                    padding: 9px 12px; border-radius: 6px; transition: background 0.12s;
                }
                .ov-row:hover { background: var(--muted); }
                .ov-row + .ov-row { border-top: 1px solid var(--border-light, #f0f0f0); }
                .ov-label { color: var(--muted-foreground); font-size: 13px; display: flex; align-items: center; gap: 5px; }
                .ov-value { font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 6px; }
                .ov-value.matched { color: var(--emerald-500); }
                .level-mini-bar { width: 48px; height: 3px; background: var(--muted); border-radius: 99px; overflow: hidden; display: inline-block; }
                .level-mini-fill { height: 100%; background: var(--primary); border-radius: 99px; }
                .info-card { background: var(--muted); border-radius: 8px; padding: 14px 16px; }

                .method-dot-google   { width: 8px; height: 8px; border-radius: 50%; background: #EA4335; display: inline-block; }
                .method-dot-facebook { width: 8px; height: 8px; border-radius: 50%; background: #1877F2; display: inline-block; }
                .method-dot-apple    { width: 8px; height: 8px; border-radius: 50%; background: #555; display: inline-block; }

                .ov-quick-actions { display: flex; gap: 8px; padding: 16px 0 4px; border-top: 1px solid var(--border); margin-top: 4px; }
                .ov-qa-btn { flex: 1; padding: 9px 12px; font-size: 12px; font-weight: 600; background: var(--muted); border: 1px solid var(--border); border-radius: 6px; color: var(--muted-foreground); cursor: pointer; transition: all 0.15s; font-family: inherit; display: flex; align-items: center; justify-content: center; gap: 5px; }
                .ov-qa-btn:hover { background: var(--surface-300, var(--muted)); color: var(--foreground); border-color: var(--border); }

                /* ── RESOURCES TAB STYLES ── */
                .res-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; margin-bottom: 14px; }
                .res-card {
                    background: var(--card); border: 1px solid var(--border);
                    border-radius: 10px; padding: 16px; transition: border-color 0.15s;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
                }
                .res-card:hover { border-color: var(--border); }
                .res-card.critical { border-color: rgba(239,68,68,0.35); background: rgba(239,68,68,0.03); }
                .res-header { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
                .res-icon { font-size: 13px; }
                .res-label { font-size: 10px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; }
                .res-label.gold { color: var(--yellow-600, #d97706); }
                .res-label.wood { color: var(--orange-700, #c2410c); }
                .res-label.ore  { color: var(--indigo-500, #6366f1); }
                .res-value { font-size: 20px; font-weight: 800; margin-bottom: 10px; color: var(--foreground); font-variant-numeric: tabular-nums; }
                .res-value.critical { color: var(--red-500); }
                .res-bar  { height: 4px; background: var(--muted); border-radius: 99px; overflow: hidden; margin-bottom: 8px; }
                .res-fill { height: 100%; border-radius: 99px; }
                .res-fill.gold    { background: var(--yellow-400, #fbbf24); }
                .res-fill.wood    { background: var(--orange-500, #f97316); }
                .res-fill.ore     { background: var(--indigo-400, #818cf8); }
                .res-fill.critical-fill { background: var(--red-400, #f87171); }
                .res-footer { display: flex; justify-content: space-between; font-size: 11px; }
                .res-cap { color: var(--muted-foreground); }
                .res-cap.warn { color: var(--red-500); font-weight: 600; }
                .delta-up   { color: var(--emerald-500); font-weight: 700; }
                .delta-down { color: var(--red-500); font-weight: 700; }

                .pet-card {
                    background: linear-gradient(90deg, #fdf4ff 0%, #faf5ff 100%);
                    border: 1px solid #e9d5ff; border-radius: 10px;
                    padding: 14px 18px; display: flex; justify-content: space-between;
                    align-items: center; margin-bottom: 14px;
                }
                .pet-left { display: flex; align-items: center; gap: 14px; }
                .pet-icon { width: 38px; height: 38px; background: #fff; border-radius: 8px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(168,85,247,0.18); }
                .pet-label-txt { font-size: 10px; font-weight: 700; color: #7c3aed; letter-spacing: 0.6px; text-transform: uppercase; margin-bottom: 3px; }
                .pet-value { font-size: 20px; font-weight: 800; color: var(--foreground); line-height: 1; }
                .pet-right { display: flex; flex-direction: column; align-items: flex-end; gap: 5px; }
                .pet-badge { background: #fff; border: 1px solid #e9d5ff; color: #7c3aed; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
                .pet-delta { font-size: 11px; font-weight: 700; }

                .ai-insight {
                    background: var(--blue-50, #eff6ff); border: 1px solid #bfdbfe;
                    border-radius: 10px; padding: 14px 16px;
                    display: flex; gap: 12px; align-items: flex-start;
                }
                .ai-icon { color: var(--primary); margin-top: 2px; flex-shrink: 0; }
                .ai-title { font-size: 12px; font-weight: 700; color: var(--blue-700, #1d4ed8); margin-bottom: 4px; display: flex; align-items: center; gap: 5px; }
                .ai-body  { font-size: 13px; color: var(--blue-800, #1e3a8a); line-height: 1.55; }

                /* ── ACTIVITY LOG TAB STYLES ── */
                .act-section-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted-foreground); margin-bottom: 10px; }
                .act-textarea {
                    width: 100%; min-height: 80px; padding: 11px 13px;
                    background: var(--card); border: 1px solid var(--border);
                    border-radius: 7px; font-family: inherit; resize: vertical;
                    font-size: 13px; line-height: 1.6; color: var(--foreground);
                    outline: none; transition: border-color 0.18s; box-sizing: border-box;
                }
                .act-textarea:focus { border-color: var(--primary); }
                .act-save-row { display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-top: 10px; }
                .act-save-feedback { font-size: 12px; color: var(--emerald-500); font-weight: 600; opacity: 0; transition: opacity 0.3s; }
                .act-save-feedback.show { opacity: 1; }
                .act-save-btn { padding: 7px 18px; font-size: 13px; font-weight: 600; background: var(--primary); color: #fff; border: none; border-radius: 6px; cursor: pointer; transition: all 0.15s; font-family: inherit; opacity: 0.4; pointer-events: none; }
                .act-save-btn.enabled { opacity: 1; pointer-events: auto; }
                .act-save-btn.enabled:hover { filter: brightness(1.08); }

                .timeline { position: relative; padding-left: 20px; border-left: 1px solid var(--border); display: flex; flex-direction: column; gap: 20px; margin-left: 7px; }
                .tl-item { position: relative; }
                .tl-dot {
                    position: absolute; left: -27px; top: 4px;
                    width: 14px; height: 14px; border-radius: 50%;
                    background: var(--card); border: 2px solid var(--border);
                    box-shadow: 0 0 0 3px var(--card);
                    display: flex; align-items: center; justify-content: center;
                }
                .tl-dot.primary { border-color: var(--primary); background: var(--primary); }
                .tl-dot.success { border-color: var(--emerald-500); background: var(--card); }
                .tl-dot.info    { border-color: var(--yellow-500);  background: var(--card); }
                .tl-dot.primary::after { content: ''; width: 5px; height: 5px; border-radius: 50%; background: #fff; }
                .tl-dot.success::after { content: ''; width: 5px; height: 5px; border-radius: 50%; background: var(--emerald-500); }
                .tl-dot.info::after    { content: ''; width: 5px; height: 5px; border-radius: 50%; background: var(--yellow-500); }
                .tl-time { font-size: 11px; color: var(--muted-foreground); margin-bottom: 3px; font-variant-numeric: tabular-nums; }
                .tl-text { font-size: 13px; color: var(--foreground); }
                .tl-text strong { font-weight: 700; }

                /* pow-badge */
                .pow-badge {
                    background: linear-gradient(135deg, #FFB020 0%, #F56A00 100%);
                    color: #fff; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 14px;
                    display: inline-flex; align-items: center; gap: 6px;
                    box-shadow: 0 4px 12px rgba(245,106,0,0.3);
                }
            </style>

            <div style="position: relative; height: 100%; display: flex; flex-direction: column;">
                <!-- Page Header -->
                <div class="page-header" style="justify-content: space-between; flex-shrink: 0; align-items: flex-start; margin-bottom: 20px;">
                    <div class="page-header-info">
                        <h2 style="margin:0 0 4px;">Game Accounts</h2>
                        <div style="display:flex; align-items:center; gap: 14px; flex-wrap: wrap;">
                            <p style="margin:0; color: var(--muted-foreground); font-size:13px;">${this._mockData.length} accounts connected</p>
                            <!-- View Toggle -->
                            <div style="display:flex; background: var(--card); border-radius: 6px; padding: 2px; border: 1px solid var(--border);">
                                <button class="btn btn-sm" style="padding: 4px 12px; border:none; border-radius: 4px; font-size:12px; display:flex; align-items:center; gap:5px; ${this._viewMode === 'table' ? 'background:var(--primary); color:white; font-weight:600;' : 'background:transparent; color:var(--muted-foreground);'}" onclick="AccountsPage.toggleViewMode('table')">
                                    <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg> List
                                </button>
                                <button class="btn btn-sm" style="padding: 4px 12px; border:none; border-radius: 4px; font-size:12px; display:flex; align-items:center; gap:5px; ${this._viewMode === 'grid' ? 'background:var(--primary); color:white; font-weight:600;' : 'background:transparent; color:var(--muted-foreground);'}" onclick="AccountsPage.toggleViewMode('grid')">
                                    <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg> Grid
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="page-actions" style="display:flex; gap: 8px;">
                        <button class="btn btn-outline btn-sm" style="display:flex;align-items:center;gap:6px;">
                            <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Export CSV
                        </button>
                        <button class="btn btn-outline btn-sm" style="display:flex;align-items:center;gap:6px;">
                            <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Sync All
                        </button>
                        <button class="btn btn-primary btn-sm" style="display:flex;align-items:center;gap:6px;">
                            <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                            Add Account
                        </button>
                    </div>
                </div>

                <!-- Main content: table or grid -->
                <div class="${this._viewMode === 'grid' ? '' : 'card'}" style="overflow: auto; flex: 1; ${this._viewMode === 'table' ? 'padding:0;' : ''}">
                    ${this._viewMode === 'table' ? `
                    <table class="accounts-table">
                        <thead style="position: sticky; top: 0; z-index: 10;">
                            <tr>
                                <th class="th-group freeze-col-1 stt-col" colspan="1" style="background:var(--muted);z-index:11;text-align:left;padding-left:14px;"></th>
                                <th class="th-group freeze-col-2" colspan="1" style="background:var(--muted);z-index:11;"></th>
                                <th class="th-group freeze-col-3" colspan="1" style="background:var(--muted);z-index:11;text-align:left;">Identity</th>
                                <th class="th-group" colspan="5" style="border-left:1px solid var(--border)">Account Details</th>
                                <th class="th-group" colspan="4" style="border-left:1px solid var(--border)">Progress & Social</th>
                                <th class="th-group" colspan="4" style="border-left:1px solid var(--border)">Resources</th>
                                <th class="th-group" colspan="1"></th>
                            </tr>
                            <tr>
                                <th class="th-col freeze-col-1 stt-col" style="padding-left:14px;z-index:11;">#</th>
                                <th class="th-col freeze-col-2" style="min-width:110px;z-index:11;">Emulator</th>
                                <th class="th-col freeze-col-3" style="min-width:140px;z-index:11;border-right:2px solid var(--border);">Name</th>
                                <th class="th-col accent" style="text-align:right;border-left:1px solid var(--border);">Power</th>
                                <th class="th-col">Login</th>
                                <th class="th-col">Email</th>
                                <th class="th-col">Target</th>
                                <th class="th-col" style="text-align:center;">Sync</th>
                                <th class="th-col" style="text-align:right;border-left:1px solid var(--border);">Hall</th>
                                <th class="th-col" style="text-align:right;">Market</th>
                                <th class="th-col">Alliance</th>
                                <th class="th-col" style="text-align:center;">Accs</th>
                                <th class="th-col" style="text-align:right;color:var(--yellow-600,#d97706);border-left:1px solid var(--border);">Gold</th>
                                <th class="th-col" style="text-align:right;color:var(--emerald-600,#059669);">Wood</th>
                                <th class="th-col" style="text-align:right;color:var(--indigo-500,#6366f1);">Ore</th>
                                <th class="th-col" style="text-align:right;color:var(--orange-500,#f97316);">Pet 🐾</th>
                                <th class="th-col" style="width:60px;"></th>
                            </tr>
                        </thead>
                        <tbody id="accounts-table-body">
                            ${this._renderTableBody()}
                        </tbody>
                    </table>
                    ` : `
                    <div class="account-list">
                        ${this._renderGridBody()}
                    </div>
                    `}
                </div>

                <!-- Overlay -->
                <div id="accounts-slide-overlay" class="slide-panel-overlay" onclick="AccountsPage.closeDetail()"></div>
                <!-- Slide Panel -->
                <div id="accounts-slide-panel" class="slide-panel"></div>
            </div>
        `;
    },

    _renderTableBody() {
        return this._mockData.map((row) => {
            const dotClass = row.status === 'online' ? 'status-dot-on' : 'status-dot-off';
            const loginColor = row.loginMethod === 'Google' ? '#EA4335' : row.loginMethod === 'Facebook' ? '#1877F2' : '#555';
            const isSelected = this._selectedAccountId === row.id;
            return `
            <tr class="account-row${isSelected ? ' selected' : ''}" onclick="AccountsPage.openDetail(${row.id})">
                <td class="freeze-col-1 stt-col" style="padding:11px 0 11px 14px;font-size:12px;color:var(--muted-foreground);">${row.id}</td>
                <td class="freeze-col-2" style="padding:11px 14px;font-size:13px;">
                    <div style="display:flex;align-items:center;gap:7px;">
                        <span class="${dotClass}" title="${row.status}"></span>
                        <span style="font-weight:500;">${row.emuName}</span>
                    </div>
                </td>
                <td class="freeze-col-3" style="padding:11px 14px;font-size:13px;font-weight:700;color:var(--primary);border-right:2px solid var(--border);">${row.ingameName}</td>
                <td style="padding:11px 14px;text-align:right;font-family:monospace;font-weight:700;font-size:13px;border-left:1px solid var(--border);">${row.pow}</td>
                <td style="padding:11px 14px;font-size:13px;">
                    <span style="border:1px solid ${loginColor}22;background:${loginColor}10;color:${loginColor};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">${row.loginMethod}</span>
                </td>
                <td style="padding:11px 14px;font-size:12px;color:var(--muted-foreground);max-width:160px;overflow:hidden;text-overflow:ellipsis;">${row.email}</td>
                <td style="padding:11px 14px;font-size:13px;">
                    <span style="background:var(--muted);color:var(--foreground);padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">${row.emulator}</span>
                </td>
                <td style="padding:11px 14px;text-align:center;">
                    ${row.accMatching === 'Yes'
                        ? '<span class="badge-status-yes">✓ Linked</span>'
                        : '<span class="badge-status-no">✗ None</span>'}
                </td>
                <td style="padding:11px 14px;text-align:right;font-weight:700;font-size:13px;border-left:1px solid var(--border);">${row.hallLvl}</td>
                <td style="padding:11px 14px;text-align:right;font-weight:700;font-size:13px;">${row.marketLvl}</td>
                <td style="padding:11px 14px;font-size:12px;color:var(--muted-foreground);">${row.alliance}</td>
                <td style="padding:11px 14px;text-align:center;font-size:13px;">${row.accountsTotal}</td>
                <td style="padding:11px 14px;text-align:right;border-left:1px solid var(--border);">
                    <span class="resource-val" style="color:var(--yellow-600,#d97706);font-size:13px;">${row.gold}M</span>
                    <span style="color:${row.trendToken==='up'?'var(--emerald-500)':'var(--red-500)'};font-size:10px;margin-left:2px;">${row.trendToken==='up'?'↑':'↓'}</span>
                </td>
                <td style="padding:11px 14px;text-align:right;">
                    <span class="resource-val" style="color:var(--emerald-600,#059669);font-size:13px;">${row.wood}M</span>
                    <span style="color:var(--emerald-500);font-size:10px;margin-left:2px;">↑</span>
                </td>
                <td style="padding:11px 14px;text-align:right;">
                    <span class="resource-val" style="color:var(--indigo-500,#6366f1);font-size:13px;">${row.ore}M</span>
                    <span style="color:var(--red-500);font-size:10px;margin-left:2px;">↓</span>
                </td>
                <td style="padding:11px 14px;text-align:right;">
                    <span class="resource-val" style="color:var(--orange-500,#f97316);font-size:13px;">${row.petToken}</span>
                    <span style="color:var(--emerald-500);font-size:10px;margin-left:2px;">↑</span>
                </td>
                <td style="padding:11px 14px;">
                    <div class="hover-actions-arrow">
                        View <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                </td>
            </tr>
            `;
        }).join('');
    },

    _renderGridBody() {
        return this._mockData.map((row, index) => {
            const statusClass = row.status === 'online' ? 'status-online' : row.status === 'idle' ? 'status-idle' : 'status-offline';
            const powerPct = Math.min((parseFloat(row.pow) / 30) * 100, 100);
            return `
            <div class="account-card ${statusClass}" onclick="AccountsPage.openDetail(${row.id})" style="animation: fadeIn 0.28s ease ${index * 0.05}s both;">
                <div class="card-dot"></div>
                <div class="account-info">
                    <div class="account-name">
                        ${row.ingameName}
                        <span class="alliance-badge">${row.alliance !== 'None' ? row.alliance : '—'}</span>
                    </div>
                    <div class="account-emulator">${row.emuName} · ${row.emulator}</div>
                </div>
                <div class="account-power">
                    <div class="power-label">
                        <span class="power-value">${row.pow}M power</span>
                        <span class="power-hall">Hall ${row.hallLvl}</span>
                    </div>
                    <div class="power-bar"><div class="power-fill" style="width:${powerPct}%"></div></div>
                    <div class="sync-time">Synced 2m ago</div>
                </div>
                <div class="card-actions">
                    <button class="card-btn-view" onclick="event.stopPropagation(); AccountsPage.openDetail(${row.id})">
                        View <svg style="width:12px;height:12px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
                    </button>
                    <div class="card-btn-icon" onclick="event.stopPropagation()" title="Sync">
                        <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                    </div>
                </div>
            </div>
            `;
        }).join('');
    },

    toggleViewMode(mode) {
        if (this._viewMode === mode) return;
        this._viewMode = mode;
        const mc = document.querySelector('.main-content');
        if (mc) mc.innerHTML = this.render();
    },

    openDetail(id) {
        this._selectedAccountId = id;
        this._activeDetailTab = 'overview';
        const panel = document.getElementById('accounts-slide-panel');
        const overlay = document.getElementById('accounts-slide-overlay');
        if (panel && overlay) {
            panel.innerHTML = this._renderSlideContent();
            void panel.offsetWidth;
            panel.classList.add('active');
            overlay.classList.add('active');
            // highlight selected row
            document.querySelectorAll('.account-row').forEach(r => r.classList.remove('selected'));
            const row = document.querySelector(`.account-row[onclick*="openDetail(${id})"]`);
            if (row) row.classList.add('selected');
        }
    },

    closeDetail() {
        const panel = document.getElementById('accounts-slide-panel');
        const overlay = document.getElementById('accounts-slide-overlay');
        if (panel && overlay) {
            panel.classList.remove('active');
            overlay.classList.remove('active');
            document.querySelectorAll('.account-row').forEach(r => r.classList.remove('selected'));
            setTimeout(() => {
                panel.innerHTML = '';
                this._selectedAccountId = null;
            }, 320);
        }
    },

    _renderSlideContent() {
        const acc = this._mockData.find(a => a.id === this._selectedAccountId);
        if (!acc) return '';

        const avatarInitial = acc.ingameName.charAt(0).toUpperCase();
        const isOnline = acc.status === 'online';
        const statusColor = isOnline ? 'var(--emerald-500)' : 'var(--red-500,#ef4444)';
        const statusLabel = isOnline ? 'Online' : 'Offline';

        return `
            <!-- Panel Header -->
            <div class="panel-header">
                <div style="display:flex; align-items:center; gap: 14px;">
                    <!-- Close button -->
                    <button onclick="AccountsPage.closeDetail()" style="width:32px;height:32px;border-radius:8px;background:var(--muted);border:1px solid var(--border);cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--muted-foreground);flex-shrink:0;" title="Close">
                        <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                    <!-- Avatar -->
                    <div style="width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,var(--primary),var(--indigo-500,#6366f1));color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;box-shadow:0 4px 12px rgba(59,130,246,0.25);flex-shrink:0;">
                        ${avatarInitial}
                    </div>
                    <div>
                        <div style="display:flex;align-items:center;gap:10px;">
                            <h2 style="margin:0;font-size:20px;font-weight:800;">${acc.ingameName}</h2>
                            <span style="font-size:11px;font-weight:700;background:${isOnline ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'};color:${statusColor};border:1px solid ${isOnline ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)'};padding:2px 8px;border-radius:20px;display:flex;align-items:center;gap:4px;">
                                <span style="width:6px;height:6px;border-radius:50%;background:${statusColor};${isOnline ? 'box-shadow:0 0 5px var(--emerald-500);' : ''}display:inline-block;"></span>
                                ${statusLabel}
                            </span>
                        </div>
                        <div style="font-size:12px;color:var(--muted-foreground);margin-top:3px;display:flex;gap:8px;align-items:center;">
                            <span>${acc.emuName}</span>
                            <span style="color:var(--border);">|</span>
                            <span>Target ${acc.emulator}</span>
                            <span style="color:var(--border);">|</span>
                            <span>Last synced 2m ago</span>
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                    <button class="btn btn-ghost btn-sm" style="color:var(--red-500);">
                        <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                        Delete
                    </button>
                    <button class="btn btn-outline btn-sm">
                        <svg style="width:13px;height:13px;margin-right:4px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        Edit
                    </button>
                    <button class="btn btn-primary btn-sm">
                        <svg style="width:13px;height:13px;margin-right:4px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Force Sync
                    </button>
                </div>
            </div>

            <!-- Key Stats Strip -->
            <div class="panel-stats-strip">
                <div class="panel-stat-item">
                    <span class="panel-stat-label">⚡ Power</span>
                    <span class="panel-stat-value">${acc.pow}M</span>
                    <span class="panel-stat-sub" style="color:var(--primary)">Top metric</span>
                </div>
                <div class="panel-stat-item">
                    <span class="panel-stat-label">🏛 Hall Level</span>
                    <span class="panel-stat-value">${acc.hallLvl}</span>
                    <span class="panel-stat-sub">${Math.round(acc.hallLvl/30*100)}% to max</span>
                </div>
                <div class="panel-stat-item">
                    <span class="panel-stat-label">🏪 Market Level</span>
                    <span class="panel-stat-value">${acc.marketLvl}</span>
                    <span class="panel-stat-sub">${Math.round(acc.marketLvl/30*100)}% to max</span>
                </div>
                <div class="panel-stat-item">
                    <span class="panel-stat-label">🔗 Match Status</span>
                    <span class="panel-stat-value" style="font-size:14px;padding-top:2px;">
                        ${acc.accMatching === 'Yes'
                            ? '<span class="badge-status-yes" style="font-size:13px;padding:4px 10px;">✓ Matched</span>'
                            : '<span class="badge-status-no" style="font-size:13px;padding:4px 10px;">✗ Unsynced</span>'}
                    </span>
                    <span class="panel-stat-sub">${acc.accountsTotal} account(s) linked</span>
                </div>
                <div class="panel-stat-item">
                    <span class="panel-stat-label">🌐 Provider</span>
                    <span class="panel-stat-value" style="font-size:15px;padding-top:4px;">${acc.provider}</span>
                    <span class="panel-stat-sub">${acc.alliance !== 'None' ? acc.alliance : 'No alliance'}</span>
                </div>
            </div>

            <!-- Tabs -->
            <div class="panel-tabs">
                <div class="panel-tab ${this._activeDetailTab === 'overview'  ? 'active' : ''}" onclick="AccountsPage.switchTab('overview')">Overview</div>
                <div class="panel-tab ${this._activeDetailTab === 'resources' ? 'active' : ''}" onclick="AccountsPage.switchTab('resources')">Resources</div>
                <div class="panel-tab ${this._activeDetailTab === 'activity'  ? 'active' : ''}" onclick="AccountsPage.switchTab('activity')">Activity Log</div>
            </div>

            <!-- Tab Content -->
            <div id="panel-tab-content" class="panel-body">
                <div class="panel-tab-body">
                    ${this._renderActiveTab(acc)}
                </div>
            </div>
        `;
    },

    switchTab(tabId) {
        this._activeDetailTab = tabId;
        const acc = this._mockData.find(a => a.id === this._selectedAccountId);
        const container = document.getElementById('panel-tab-content');
        if (container && acc) {
            container.innerHTML = `<div class="panel-tab-body">${this._renderActiveTab(acc)}</div>`;
            document.querySelectorAll('.panel-tab').forEach(el => {
                el.classList.toggle('active', el.textContent.trim().toLowerCase().startsWith(tabId.toLowerCase().split(' ')[0]));
            });
        }
    },

    _renderActiveTab(acc) {
        /* ───── OVERVIEW ───── */
        if (this._activeDetailTab === 'overview') {
            const loginDotClass = acc.loginMethod === 'Google' ? 'method-dot-google' : acc.loginMethod === 'Facebook' ? 'method-dot-facebook' : 'method-dot-apple';
            const hallPct  = Math.round(acc.hallLvl / 30 * 100);
            const mktPct   = Math.round(acc.marketLvl / 30 * 100);
            return `
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px;">
                    <!-- Left -->
                    <div style="display:flex;flex-direction:column;gap:20px;">
                        <div>
                            <div class="ov-section-title">Login & Access</div>
                            <div class="info-card">
                                <div class="ov-row">
                                    <span class="ov-label">Method</span>
                                    <span class="ov-value"><span class="${loginDotClass}"></span> ${acc.loginMethod}</span>
                                </div>
                                <div class="ov-row">
                                    <span class="ov-label">Email</span>
                                    <span class="ov-value" style="font-family:monospace;font-size:12px;font-weight:500;">${acc.email}</span>
                                </div>
                            </div>
                        </div>
                        <div>
                            <div class="ov-section-title">Emulator Info</div>
                            <div class="info-card">
                                <div class="ov-row">
                                    <span class="ov-label">Instance</span>
                                    <span class="ov-value">
                                        LDP-${acc.emulator.replace('#','')}
                                        <span style="width:7px;height:7px;border-radius:50%;background:${acc.status==='online'?'var(--emerald-500)':'var(--border)'};${acc.status==='online'?'box-shadow:0 0 5px var(--emerald-500);':''}display:inline-block;"></span>
                                    </span>
                                </div>
                                <div class="ov-row">
                                    <span class="ov-label">Provider</span>
                                    <span class="ov-value">${acc.provider}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Right -->
                    <div style="display:flex;flex-direction:column;gap:20px;">
                        <div>
                            <div class="ov-section-title">Game Status</div>
                            <div class="info-card">
                                <div class="ov-row">
                                    <span class="ov-label">Alliance</span>
                                    <span class="ov-value">${acc.alliance}</span>
                                </div>
                                <div class="ov-row">
                                    <span class="ov-label">Hall Level</span>
                                    <span class="ov-value">
                                        ${acc.hallLvl}
                                        <span class="level-mini-bar"><span class="level-mini-fill" style="width:${hallPct}%;display:block;height:100%;"></span></span>
                                        <span style="font-size:11px;color:var(--muted-foreground);font-weight:400;">/ 30</span>
                                    </span>
                                </div>
                                <div class="ov-row">
                                    <span class="ov-label">Market Level</span>
                                    <span class="ov-value">
                                        ${acc.marketLvl}
                                        <span class="level-mini-bar"><span class="level-mini-fill" style="width:${mktPct}%;display:block;height:100%;"></span></span>
                                        <span style="font-size:11px;color:var(--muted-foreground);font-weight:400;">/ 30</span>
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div>
                            <div class="ov-section-title">Match</div>
                            <div class="info-card">
                                <div class="ov-row">
                                    <span class="ov-label">
                                        Status
                                        <svg style="width:11px;height:11px;color:var(--muted-foreground)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" title="Whether this account is matched to a player profile"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
                                    </span>
                                    <span class="ov-value ${acc.accMatching==='Yes'?'matched':''}">
                                        ${acc.accMatching==='Yes'
                                            ? '<svg style="width:13px;height:13px;background:var(--emerald-500);color:white;border-radius:3px;padding:1px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg> Matched'
                                            : '<span style="color:var(--red-500);">✗ Unsynced</span>'}
                                    </span>
                                </div>
                                <div class="ov-row">
                                    <span class="ov-label">Total Linked</span>
                                    <span class="ov-value">${acc.accountsTotal} account(s)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="ov-quick-actions">
                    <button class="ov-qa-btn">
                        <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Force Sync
                    </button>
                    <button class="ov-qa-btn">
                        <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        Edit Account
                    </button>
                    <button class="ov-qa-btn">
                        <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                        View Alliance
                    </button>
                </div>
            `;
        }

        /* ───── RESOURCES ───── */
        if (this._activeDetailTab === 'resources') {
            const goldM = parseFloat(acc.gold);
            const woodM = parseFloat(acc.wood);
            const oreM  = parseFloat(acc.ore);
            // Cap = 30M for simplicity; pct based on that
            const goldPct = Math.min(Math.round(goldM / 2.4 * 100), 100); // assume cap 2.4M
            const woodPct = Math.min(Math.round(woodM / 16 * 100), 100);
            const orePct  = Math.min(Math.round(oreM  / 25 * 100), 100);
            const oreIsCritical = orePct < 30;

            return `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                    <div class="ov-section-title" style="margin:0;">Resource Stockpile</div>
                    <span style="font-size:11px;color:var(--muted-foreground);font-family:monospace;">Last updated: 2m ago</span>
                </div>

                <div class="res-grid">
                    <!-- Gold -->
                    <div class="res-card">
                        <div class="res-header">
                            <span class="res-icon">🪙</span>
                            <span class="res-label gold">Gold</span>
                        </div>
                        <div class="res-value">${goldM * 1000 >= 1000 ? goldM.toFixed(1) + 'M' : (goldM * 1000).toLocaleString()}</div>
                        <div class="res-bar"><div class="res-fill gold" style="width:${goldPct}%"></div></div>
                        <div class="res-footer">
                            <span class="res-cap">${goldPct}% cap</span>
                            <span class="delta-up">▲ +12,000</span>
                        </div>
                    </div>

                    <!-- Wood -->
                    <div class="res-card">
                        <div class="res-header">
                            <span class="res-icon">🪵</span>
                            <span class="res-label wood">Wood</span>
                        </div>
                        <div class="res-value">${woodM >= 1 ? woodM.toFixed(1) + 'M' : (woodM * 1000).toLocaleString()}</div>
                        <div class="res-bar"><div class="res-fill wood" style="width:${woodPct}%"></div></div>
                        <div class="res-footer">
                            <span class="res-cap">${woodPct}% cap</span>
                            <span class="delta-up">▲ +8,000</span>
                        </div>
                    </div>

                    <!-- Ore -->
                    <div class="res-card ${oreIsCritical ? 'critical' : ''}">
                        <div class="res-header">
                            <svg class="res-icon" style="width:14px;color:${oreIsCritical?'var(--red-500)':'var(--indigo-400,#818cf8)'}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                            <span class="res-label ore" style="${oreIsCritical?'color:var(--red-500);':''}">Ore${oreIsCritical?' ⚠':''}</span>
                        </div>
                        <div class="res-value ${oreIsCritical ? 'critical' : ''}">${oreM >= 1 ? oreM.toFixed(1) + 'M' : (oreM * 1000).toLocaleString()}</div>
                        <div class="res-bar"><div class="res-fill ${oreIsCritical ? 'critical-fill' : 'ore'}" style="width:${orePct}%"></div></div>
                        <div class="res-footer">
                            <span class="res-cap ${oreIsCritical ? 'warn' : ''}">${orePct}%${oreIsCritical ? ' — Critical' : ' cap'}</span>
                            <span class="delta-down">▼ 3,000</span>
                        </div>
                    </div>
                </div>

                <!-- Pet Tokens -->
                <div class="pet-card">
                    <div class="pet-left">
                        <div class="pet-icon">
                            <svg style="width:20px;color:#a855f7" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polygon points="2 17 12 22 22 17 22 12 12 17 2 12 2 17"/></svg>
                        </div>
                        <div>
                            <div class="pet-label-txt">Pet Tokens</div>
                            <div class="pet-value">${acc.petToken}</div>
                        </div>
                    </div>
                    <div class="pet-right">
                        <span class="pet-badge">Special Currency</span>
                        <span class="pet-delta delta-up">▲ +2 today</span>
                    </div>
                </div>

                <!-- AI Insight -->
                <div class="ai-insight">
                    <div class="ai-icon">
                        <svg style="width:18px;height:18px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    </div>
                    <div>
                        <div class="ai-title">
                            ✦ AI Insight
                        </div>
                        <div class="ai-body">
                            ${oreIsCritical
                                ? `<strong>Ore is critically low (${orePct}%)</strong> and declining — prioritize farming runs before your next Hall upgrade. `
                                : 'Resources look healthy. '}
                            Gold cap will be reached in <strong>~2 days</strong> at current production rates.
                        </div>
                    </div>
                </div>
            `;
        }

        /* ───── ACTIVITY LOG ───── */
        if (this._activeDetailTab === 'activity') {
            return `
                <!-- Operator Notes -->
                <div style="margin-bottom:28px;">
                    <div class="act-section-title">Operator Notes</div>
                    <textarea class="act-textarea" id="act-note-${acc.id}" oninput="AccountsPage._handleNoteInput(${acc.id})">${acc.note}</textarea>
                    <div class="act-save-row">
                        <span class="act-save-feedback" id="act-save-fb-${acc.id}">✓ Saved</span>
                        <button class="act-save-btn" id="act-save-btn-${acc.id}" onclick="AccountsPage._saveNote(${acc.id})">Save Note</button>
                    </div>
                </div>

                <!-- Timeline -->
                <div>
                    <div class="act-section-title" style="margin-bottom:16px;">Recent History</div>
                    <div class="timeline">
                        <div class="tl-item">
                            <div class="tl-dot primary"></div>
                            <div class="tl-time">Today, 10:23 AM</div>
                            <div class="tl-text"><strong>Synced successfully</strong> via LDP-${acc.emulator.replace('#','')}</div>
                        </div>
                        <div class="tl-item">
                            <div class="tl-dot success"></div>
                            <div class="tl-time">Yesterday, 4:00 PM</div>
                            <div class="tl-text">Resources updated: <strong>Gold +12k</strong></div>
                        </div>
                        <div class="tl-item">
                            <div class="tl-dot info"></div>
                            <div class="tl-time">2 days ago</div>
                            <div class="tl-text"><strong>Account matched</strong> to player profile</div>
                        </div>
                        <div class="tl-item">
                            <div class="tl-dot"></div>
                            <div class="tl-time">3 days ago</div>
                            <div class="tl-text">Login method changed to ${acc.loginMethod}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        return '';
    },

    _noteOriginals: {},

    _handleNoteInput(id) {
        const ta  = document.getElementById(`act-note-${id}`);
        const btn = document.getElementById(`act-save-btn-${id}`);
        if (!ta || !btn) return;
        if (!(id in this._noteOriginals)) {
            const acc = this._mockData.find(a => a.id === id);
            this._noteOriginals[id] = acc ? acc.note : '';
        }
        const changed = ta.value !== this._noteOriginals[id];
        btn.classList.toggle('enabled', changed);
    },

    _saveNote(id) {
        const ta  = document.getElementById(`act-note-${id}`);
        const btn = document.getElementById(`act-save-btn-${id}`);
        const fb  = document.getElementById(`act-save-fb-${id}`);
        if (!ta || !btn || !fb) return;
        const acc = this._mockData.find(a => a.id === id);
        if (acc) acc.note = ta.value;
        this._noteOriginals[id] = ta.value;
        btn.classList.remove('enabled');
        fb.classList.add('show');
        setTimeout(() => fb.classList.remove('show'), 2200);
    },

    init() { this._noteOriginals = {}; },
    destroy() {
        this._selectedAccountId = null;
        this._noteOriginals = {};
    }
};
