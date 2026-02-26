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
    _viewMode: 'table', // 'table' or 'grid'

    render() {
        return `
            <style>
                .accounts-table th, .accounts-table td {
                    white-space: nowrap;
                }
                .freeze-col-1 { position: sticky; left: 0; z-index: 5; background: var(--surface-100); border-right: 1px solid var(--border); }
                .freeze-col-2 { position: sticky; left: 56px; z-index: 5; background: var(--surface-100); border-right: 1px solid var(--border); }
                .freeze-col-3 { position: sticky; left: 166px; z-index: 5; background: var(--surface-100); border-right: 1px solid var(--border); }
                
                .stt-col { width: 56px !important; min-width: 56px; max-width: 56px; }
                
                .account-row { cursor: pointer; transition: background 0.15s, box-shadow 0.15s; background: var(--surface-100); }
                .account-row:hover { background: var(--surface-50); box-shadow: inset 2px 0 0 var(--primary); }
                .account-row:hover .freeze-col-1, .account-row:hover .freeze-col-2, .account-row:hover .freeze-col-3 { background: var(--surface-50); }
                
                .hover-actions-arrow { 
                    opacity: 0; transition: opacity 0.2s, transform 0.2s; 
                    transform: translateX(-4px); display: flex; align-items: center; gap: 4px; 
                    color: var(--primary); font-weight: 600; font-size: 13px; 
                }
                .account-row:hover .hover-actions-arrow { opacity: 1; transform: translateX(0); }
                
                .badge-status-yes { background: rgba(16, 185, 129, 0.1); color: var(--emerald-500); border: 1px solid rgba(16, 185, 129, 0.2); }
                .badge-status-no { background: rgba(239, 68, 68, 0.1); color: var(--red-500); border: 1px solid rgba(239, 68, 68, 0.2); }
                
                .resource-val { font-weight: 600; letter-spacing: 0.3px; }
                .status-dot-on { width: 8px; height: 8px; border-radius: 50%; background: var(--emerald-500); box-shadow: 0 0 4px var(--emerald-500); }
                .status-dot-off { width: 8px; height: 8px; border-radius: 50%; background: var(--border-strong, #999); }
                
                /* Slide Panel Styles */
                .slide-panel-overlay {
                    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(0,0,0,0.4); z-index: 1000;
                    opacity: 0; pointer-events: none; transition: opacity 0.3s ease;
                }
                .slide-panel-overlay.active { opacity: 1; pointer-events: auto; }
                
                .slide-panel {
                    position: fixed; top: 0; right: 0; width: 640px; max-width: 100vw; height: 100vh;
                    background: var(--surface-100, #ffffff); z-index: 1001;
                    box-shadow: -4px 0 32px rgba(0,0,0,0.15);
                    transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    display: flex; flex-direction: column;
                }
                .slide-panel.active { transform: translateX(0); }
                
                .panel-header {
                    padding: 24px 32px; border-bottom: 1px solid var(--border);
                    display: flex; justify-content: space-between; align-items: flex-start;
                    background: var(--surface-100); position: sticky; top: 0; z-index: 10;
                }
                .panel-body { flex: 1; overflow-y: auto; padding: 32px; }
                
                /* Detail Tabs */
                .panel-tabs {
                    display: flex; gap: 32px; border-bottom: 1px solid var(--border); margin-bottom: 24px;
                }
                .panel-tab {
                    padding: 0 0 12px 0; color: var(--text-muted); cursor: pointer;
                    border-bottom: 2px solid transparent; font-weight: 600; font-size: 14px; transition: all 0.2s;
                    margin-bottom: -1px;
                }
                .panel-tab:hover { color: var(--text); }
                .panel-tab.active { color: var(--primary); border-bottom-color: var(--primary); }
                
                /* Detail Component Styles */
                .pow-badge {
                    background: linear-gradient(135deg, #FFB020 0%, #F56A00 100%);
                    color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.2);
                    padding: 4px 12px; border-radius: 20px; font-weight: 700;
                    display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(245,106,0,0.3);
                }
                
                .stat-card-high { background: var(--surface-100); border: 1px solid var(--primary-light, rgba(59,130,246,0.2)); border-left: 4px solid var(--primary); box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
                .stat-card-med { background: var(--surface-100); border: 1px solid var(--border); box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
            </style>
            
            <div style="position: relative; height: 100%; display: flex; flex-direction: column;">
                <div class="page-header" style="justify-content: space-between; flex-shrink: 0; align-items: flex-start; margin-bottom: 24px;">
                    <div class="page-header-info">
                        <h2>Game Accounts</h2>
                        <div style="display:flex; align-items:center; gap: 16px; margin-top: 4px;">
                            <p style="margin:0;">Detailed view of all game accounts, resources, and statuses across your emulators.</p>
                            
                            <!-- View Toggle Switch -->
                            <div style="display:flex; background: var(--surface-100); border-radius: 6px; padding: 3px; border: 1px solid var(--border); box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
                                <button class="btn btn-sm" style="padding: 4px 14px; border:none; ${this._viewMode === 'table' ? 'background:var(--primary); color:white; font-weight:600; box-shadow:0 2px 4px rgba(0,0,0,0.1);' : 'background:transparent; color:var(--text-muted);'}" onclick="AccountsPage.toggleViewMode('table')">
                                    <svg style="width:14px;height:14px;margin-right:6px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg> List
                                </button>
                                <button class="btn btn-sm" style="padding: 4px 14px; border:none; ${this._viewMode === 'grid' ? 'background:var(--primary); color:white; font-weight:600; box-shadow:0 2px 4px rgba(0,0,0,0.1);' : 'background:transparent; color:var(--text-muted);'}" onclick="AccountsPage.toggleViewMode('grid')">
                                    <svg style="width:14px;height:14px;margin-right:6px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg> Grid
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="page-actions" style="display:flex; gap: 8px;">
                        <button class="btn btn-outline btn-sm">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Export CSV
                        </button>
                        <button class="btn btn-primary btn-sm">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                            Add Account
                        </button>
                    </div>
                </div>

                <div class="${this._viewMode === 'grid' ? '' : 'card'}" style="padding: ${this._viewMode === 'grid' ? '0' : '0'}; overflow: auto; flex: 1;">
                    ${this._viewMode === 'table' ? `
                        <thead style="position: sticky; top: 0; z-index: 10; background: var(--surface-100);">
                            <!-- Group Header Row -->
                            <tr style="background: var(--surface-200);">
                                <th colspan="3" style="padding: 12px 16px 14px; font-weight: 700; font-size: 12px; color: var(--text); border-right: 1px solid var(--border); border-bottom: 2px solid var(--border-strong, #ddd); text-align: center; z-index: 11; background: var(--surface-200);" class="freeze-col-1">Identity & Core</th>
                                <th colspan="5" style="padding: 12px 16px 14px; font-weight: 700; font-size: 12px; color: var(--text); border-right: 1px solid var(--border); border-bottom: 2px solid var(--border-strong, #ddd); text-align: center;">Account Details</th>
                                <th colspan="4" style="padding: 12px 16px 14px; font-weight: 700; font-size: 12px; color: var(--text); border-right: 1px solid var(--border); border-bottom: 2px solid var(--border-strong, #ddd); text-align: center;">Progress & Social</th>
                                <th colspan="4" style="padding: 12px 16px 14px; font-weight: 700; font-size: 12px; color: var(--text); border-right: 1px solid var(--border); border-bottom: 2px solid var(--border-strong, #ddd); text-align: center;">Resources</th>
                                <th colspan="1" style="padding: 12px 16px 14px; font-weight: 700; font-size: 12px; color: var(--text); border-bottom: 2px solid var(--border-strong, #ddd); text-align: center;">Actions</th>
                            </tr>
                            <!-- Column Header Row -->
                            <tr>
                                <th class="freeze-col-1 stt-col" style="padding: 12px 0 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); z-index: 11; background: var(--surface-100);">STT</th>
                                <th class="freeze-col-2" style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); min-width: 110px; z-index: 11; background: var(--surface-100);">Emu Name</th>
                                <th class="freeze-col-3" style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); min-width: 140px; z-index: 11; background: var(--surface-100);">In-game Name</th>
                                
                                <th style="padding: 12px 16px; font-weight: 700; font-size: 13px; color: var(--primary); text-align: right;">POW (M)</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Login</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Email</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Target</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: center;" title="Match sync status">Sync</th>
                                
                                <th style="padding: 12px 16px; font-weight: 700; font-size: 13px; color: var(--text); text-align: right;">Hall</th>
                                <th style="padding: 12px 16px; font-weight: 700; font-size: 13px; color: var(--text); text-align: right;">Market</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Alliance</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: center;">Accs</th>
                                
                                <th style="padding: 12px 16px; font-weight: 700; font-size: 13px; color: var(--yellow-600); text-align: right;">Gold</th>
                                <th style="padding: 12px 16px; font-weight: 700; font-size: 13px; color: var(--emerald-600); text-align: right;">Wood</th>
                                <th style="padding: 12px 16px; font-weight: 700; font-size: 13px; color: var(--indigo-600); text-align: right;">Ore</th>
                                <th style="padding: 12px 16px; font-weight: 700; font-size: 13px; color: var(--orange-600); text-align: right;">Pet</th>
                                
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: right;"></th>
                            </tr>
                        </thead>
                        <tbody id="accounts-table-body">
                            ${this._renderTableBody()}
                        </tbody>
                    </table>
                    ` : `
                    <style>
                        .account-list { display: flex; flex-direction: column; gap: 10px; padding-right: 8px; }
                        
                        .account-card {
                            background: var(--surface-100); border: 1px solid var(--border);
                            border-radius: 12px; padding: 18px 22px;
                            display: flex; align-items: center; gap: 18px;
                            cursor: pointer; transition: all 0.2s ease;
                            position: relative; overflow: hidden;
                        }
                        .account-card::before {
                            content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
                            border-radius: 3px 0 0 3px; transition: opacity 0.2s;
                        }
                        
                        /* Status Colors matching index.css + prototype */
                        .account-card.status-online::before { background: var(--emerald-500); }
                        .account-card.status-offline::before { background: var(--red-500); }
                        .account-card.status-idle::before { background: var(--yellow-500); }
                        
                        .account-card:hover {
                            border-color: var(--primary-light, #bbc);
                            background: var(--surface-50);
                            transform: translateY(-1px);
                            box-shadow: 0 4px 24px rgba(0,0,0,0.08); /* Lighter shadow for card view */
                        }
                        .account-card.status-offline { opacity: 0.75; }
                        .account-card.status-offline:hover { opacity: 1; }
                        
                        .card-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
                        .status-online .card-dot { background: var(--emerald-500); box-shadow: 0 0 8px var(--emerald-500); }
                        .status-offline .card-dot { background: var(--red-500); box-shadow: 0 0 8px var(--red-500); }
                        .status-idle .card-dot { background: var(--yellow-500); box-shadow: 0 0 8px var(--yellow-500); }
                        
                        .account-info { min-width: 170px; display: flex; flex-direction: column; justify-content: center; }
                        .account-name { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
                        .alliance-badge {
                            font-size: 10px; font-weight: 600; padding: 2px 7px;
                            border-radius: 4px; background: var(--surface-200); color: var(--text-muted);
                            font-family: inherit; letter-spacing: 0.5px;
                        }
                        .account-emulator { font-size: 12px; color: var(--text-muted); font-family: monospace; }
                        
                        .account-power { flex: 1; min-width: 250px; }
                        .power-label { display: flex; justify-content: space-between; align-items: center; margin-bottom: 7px; }
                        .power-value { font-size: 13px; font-weight: 600; color: var(--text); }
                        .power-hall { font-size: 12px; color: var(--text-muted); font-family: monospace; }
                        .power-bar { height: 5px; background: var(--surface-200); border-radius: 99px; overflow: hidden; }
                        .power-fill { height: 100%; border-radius: 99px; transition: width 0.8s cubic-bezier(0.4,0,0.2,1); }
                        
                        .status-online .power-fill { background: linear-gradient(90deg, #22d47b, #4fffb0); } /* prototype green gradient */
                        .status-offline .power-fill { background: linear-gradient(90deg, #ff5c5c, #ff8888); } /* prototype red gradient */
                        .status-idle .power-fill { background: linear-gradient(90deg, #f5b731, #ffd97a); } /* prototype yellow gradient */
                        
                        .sync-time { font-size: 11px; color: var(--text-muted); margin-top: 6px; text-align: right; }
                        .card-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
                    </style>
                    <div class="account-list">
                        ${this._renderGridBody()}
                    </div>
                    `}
                </div>

                <!-- Slide Panel Overlay -->
                <div id="accounts-slide-overlay" class="slide-panel-overlay" onclick="AccountsPage.closeDetail()"></div>
                
                <!-- Slide Panel Main Container -->
                <div id="accounts-slide-panel" class="slide-panel">
                    <!-- Dynamic details appended here -->
                </div>
            </div>
        `;
    },

    _renderTableBody() {
        return this._mockData.map((row) => {
            const rowBg = 'inherit';
            const statusIndicatorClass = row.status === 'online' ? 'status-dot-on' : 'status-dot-off';
            return `
            <tr class="account-row" onclick="AccountsPage.openDetail(${row.id})" style="border-bottom: 1px solid var(--border);">
                <!-- Frozen columns -->
                <td class="freeze-col-1 stt-col" style="padding: 12px 0 12px 16px; font-size: 13px; border-bottom: 1px solid var(--border);">${row.id}</td>
                <td class="freeze-col-2" style="padding: 12px 16px; font-size: 13px; font-weight: 500; border-bottom: 1px solid var(--border);">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <span class="${statusIndicatorClass}" title="Status: ${row.status}"></span>
                        ${row.emuName}
                    </div>
                </td>
                <td class="freeze-col-3" style="padding: 12px 16px; font-size: 13px; font-weight: 600; color: var(--primary); border-bottom: 1px solid var(--border);">${row.ingameName}</td>
                
                <!-- Account Details -->
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace; font-weight: bold; border-bottom: 1px solid var(--border);">${row.pow}</td>
                <td style="padding: 12px 16px; font-size: 13px; border-bottom: 1px solid var(--border);">
                    <span class="badge badge-outline" style="border-radius:4px; border-color: ${row.loginMethod === 'Google' ? '#EA4335' : row.loginMethod === 'Facebook' ? '#1877F2' : 'var(--border)'}">${row.loginMethod}</span>
                </td>
                <td style="padding: 12px 16px; font-size: 13px; color: var(--text-muted); border-bottom: 1px solid var(--border);">${row.email}</td>
                <td style="padding: 12px 16px; font-size: 13px; border-bottom: 1px solid var(--border);">
                     <span class="badge" style="background:var(--surface-200); color:var(--text);">${row.emulator}</span>
                </td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: center; border-bottom: 1px solid var(--border);" title="${row.accMatching === 'Yes' ? 'Matching Linked' : 'Not Synced'}">
                    ${row.accMatching === 'Yes'
                    ? '<span class="badge badge-status-yes" style="padding:2px 6px">✓ Linked</span>'
                    : '<span class="badge badge-status-no" style="padding:2px 6px">✗ Unsynced</span>'}
                </td>
                
                <!-- Progress -->
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-weight: 700; border-bottom: 1px solid var(--border);">${row.hallLvl}</td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-weight: 700; border-bottom: 1px solid var(--border);">${row.marketLvl}</td>
                <td style="padding: 12px 16px; font-size: 13px; border-bottom: 1px solid var(--border);">${row.alliance}</td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: center; border-bottom: 1px solid var(--border);">${row.accountsTotal}</td>
                
                <!-- Resources -->
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace; border-bottom: 1px solid var(--border);">
                    <div class="resource-val" style="color: var(--yellow-500);">${row.gold}M <span style="color:var(--emerald-500); font-size:10px">${row.trendToken === 'up' ? '↑' : '↓'}</span></div>
                </td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace; border-bottom: 1px solid var(--border);">
                    <div class="resource-val" style="color: var(--emerald-500);">${row.wood}M <span style="color:var(--emerald-500); font-size:10px">↑</span></div>
                </td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace; border-bottom: 1px solid var(--border);">
                    <div class="resource-val" style="color: var(--indigo-500);">${row.ore}M <span style="color:var(--red-500); font-size:10px">↓</span></div>
                </td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace; border-bottom: 1px solid var(--border);">
                    <div class="resource-val" style="color: var(--orange-500);">${row.petToken} <span style="color:var(--emerald-500); font-size:10px">↑</span></div>
                </td>
                
                <!-- Actions -->
                <td style="padding: 12px 16px; border-bottom: 1px solid var(--border);">
                    <div class="hover-actions-arrow" style="justify-content: flex-end;">
                        View <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                </td>
            </tr>
            `;
        }).join('');
    },

    _renderGridBody() {
        return this._mockData.map((row, index) => {
            const statusClass = row.status === 'online' ? 'status-online' : 'status-offline';
            // fake power calc for visual width mapping 10M to 100%
            const powerPct = Math.min((parseFloat(row.pow) / 30) * 100, 100);

            return `
            <div class="account-card ${statusClass}" onclick="AccountsPage.openDetail(${row.id})" style="animation: fadeIn 0.3s ease ${index * 0.05}s both;">
                <div class="card-dot"></div>
                
                <div class="account-info">
                    <div class="account-name">
                        ${row.ingameName}
                        <span class="alliance-badge">${row.alliance}</span>
                    </div>
                    <div class="account-emulator">${row.emuName} <span style="color:var(--border-strong, #ccc)">|</span> ${row.emulator}</div>
                </div>
                
                <div class="account-power">
                    <div class="power-label">
                        <span class="power-value">${row.pow}M power</span>
                        <span class="power-hall">Hall ${row.hallLvl}</span>
                    </div>
                    <div class="power-bar">
                        <div class="power-fill" style="width: ${powerPct}%;"></div>
                    </div>
                    <div class="sync-time">Last synced 2m ago</div>
                </div>
                
                <div class="card-actions">
                    <button class="btn btn-outline" style="padding: 8px 16px; font-size: 12px; font-weight: 600;" onclick="event.stopPropagation(); AccountsPage.openDetail(${row.id})">
                        View <svg style="width:14px;height:14px;margin-left:4px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </button>
                    <button class="btn btn-outline" style="width: 34px; height: 34px; padding: 0; display: flex; align-items: center; justify-content: center; background: var(--surface-100);" onclick="event.stopPropagation()" title="Quick Sync">
                         <svg style="width:14px;height:14px; color: var(--text-muted);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                    </button>
                </div>
            </div>
            `;
        }).join('');
    },

    toggleViewMode(mode) {
        if (this._viewMode === mode) return;
        this._viewMode = mode;
        const mainContainer = document.querySelector('.main-content');
        if (mainContainer) {
            mainContainer.innerHTML = this.render();
            // Re-bind any specific listeners if needed (not strictly required here since we use inline onclicks)
        }
    },

    openDetail(id) {
        this._selectedAccountId = id;
        this._activeDetailTab = 'overview';
        const panel = document.getElementById('accounts-slide-panel');
        const overlay = document.getElementById('accounts-slide-overlay');

        if (panel && overlay) {
            panel.innerHTML = this._renderSlideContent();
            void panel.offsetWidth; // Force reflow
            panel.classList.add('active');
            overlay.classList.add('active');
        }
    },

    closeDetail() {
        const panel = document.getElementById('accounts-slide-panel');
        const overlay = document.getElementById('accounts-slide-overlay');
        if (panel && overlay) {
            panel.classList.remove('active');
            overlay.classList.remove('active');
            setTimeout(() => {
                panel.innerHTML = '';
                this._selectedAccountId = null;
            }, 300);
        }
    },

    _renderSlideContent() {
        const acc = this._mockData.find(a => a.id === this._selectedAccountId);
        if (!acc) return '';

        const avatarInitial = acc.ingameName.charAt(0).toUpperCase();

        return `
            <!-- Sticky Header -->
            <div class="panel-header">
                <div style="display:flex; align-items: center; gap: 16px;">
                    <div style="width: 56px; height: 56px; border-radius: 50%; background: linear-gradient(135deg, var(--primary), var(--indigo-500)); color: white; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);">
                        ${avatarInitial}
                    </div>
                    <div>
                        <h2 style="margin: 0; font-size: 22px;">${acc.ingameName}</h2>
                        <div style="font-size: 13px; color: var(--text-muted); font-weight: 500; margin-top: 4px; display: flex; gap: 8px; align-items: center;">
                            <span>${acc.emuName}</span>
                            <span style="color: var(--border-strong, #ccc);">|</span>
                            <span>Target: ${acc.emulator}</span>
                        </div>
                    </div>
                </div>
                <div class="page-actions" style="display:flex; flex-direction: column; align-items: flex-end; gap: 8px;">
                    <div style="display:flex; gap: 8px;">
                        <button class="btn btn-ghost btn-sm" style="color: var(--red-500)">Delete</button>
                        <button class="btn btn-outline btn-sm">Edit</button>
                        <button class="btn btn-primary btn-sm">Force Sync</button>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); font-weight: 500;">Last synced 2m ago</div>
                </div>
            </div>

            <!-- Scrollable Body -->
            <div class="panel-body">
                <!-- Highlighted Stats -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
                    <div class="pow-badge">
                        <svg style="width:16px;height:16px" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                        Power: ${acc.pow} M
                    </div>
                </div>

                <!-- Hierarchical Stat Cards Grid -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px;">
                    <!-- High Priority -->
                    <div class="card stat-card-high" style="padding: 24px 20px; border-radius: 12px;">
                        <div class="text-muted" style="text-transform: uppercase; font-weight: 700; font-size: 11px; letter-spacing: 0.8px; color: var(--primary);">Main Hall Level</div>
                        <div style="font-size: 36px; font-weight: 800; margin-top: 8px; line-height: 1;">${acc.hallLvl}</div>
                    </div>
                    
                    <div class="card stat-card-med" style="padding: 24px 20px; border-radius: 12px; display: flex; flex-direction: column; justify-content: center;">
                        <div class="text-muted" style="text-transform: uppercase; font-weight: 700; font-size: 11px; letter-spacing: 0.8px; margin-bottom: 12px;">Match Status</div>
                        ${acc.accMatching === 'Yes'
                ? '<span class="badge badge-status-yes" style="font-size:14px; padding:6px 12px; align-self: flex-start; border-radius: 6px;">✓ Validated & Linked</span>'
                : '<span class="badge badge-status-no" style="font-size:14px; padding:6px 12px; align-self: flex-start; border-radius: 6px;">✗ Unsynced</span>'}
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px;">
                    <!-- Medium Priority -->
                    <div class="card stat-card-med" style="padding: 20px; border-radius: 12px;">
                        <div class="text-muted" style="text-transform: uppercase; font-weight: 700; font-size: 11px; letter-spacing: 0.8px;">Market Level</div>
                        <div style="font-size: 28px; font-weight: 700; margin-top: 6px;">${acc.marketLvl}</div>
                    </div>
                    <div class="card stat-card-med" style="padding: 20px; border-radius: 12px;">
                        <div class="text-muted" style="text-transform: uppercase; font-weight: 700; font-size: 11px; letter-spacing: 0.8px;">Total Accounts</div>
                        <div style="font-size: 28px; font-weight: 700; margin-top: 6px;">${acc.accountsTotal}</div>
                    </div>
                </div>

                <!-- Section Tabs Navigation -->
                <div class="panel-tabs">
                    <div class="panel-tab ${this._activeDetailTab === 'overview' ? 'active' : ''}" onclick="AccountsPage.switchTab('overview')">Overview</div>
                    <div class="panel-tab ${this._activeDetailTab === 'resources' ? 'active' : ''}" onclick="AccountsPage.switchTab('resources')">Resources</div>
                    <div class="panel-tab ${this._activeDetailTab === 'activity' ? 'active' : ''}" onclick="AccountsPage.switchTab('activity')">Activity Log</div>
                </div>
                
                <!-- Dynamic Content Area -->
                <div id="panel-tab-content">
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
            container.innerHTML = this._renderActiveTab(acc);

            document.querySelectorAll('.panel-tab').forEach(el => {
                el.classList.remove('active');
                if (el.textContent.toLowerCase() === tabId) el.classList.add('active');
            });
        }
    },

    _renderActiveTab(acc) {
        if (this._activeDetailTab === 'overview') {
            return `
                <div style="margin-bottom: 24px;">
                    <h3 style="font-size: 13px; font-weight: 700; color: var(--text); letter-spacing: 0.5px; margin-bottom: 16px; text-transform: uppercase;">Account Overview</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px;">
                        
                        <!-- Left Column -->
                        <div style="display: flex; flex-direction: column; gap: 24px;">
                            <div>
                                <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 12px; text-transform: uppercase;">Login & Access</div>
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-light, #f0f0f0);">
                                    <span style="color: var(--text-muted); font-size: 13px;">Method</span>
                                    <span style="font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                                        ${acc.loginMethod} 
                                        <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--primary);"></span>
                                    </span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-light, #f0f0f0);">
                                    <span style="color: var(--text-muted); font-size: 13px;">Email</span>
                                    <span style="font-weight: 600; font-size: 13px;">${acc.email}</span>
                                </div>
                            </div>
                            
                            <div>
                                <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 12px; text-transform: uppercase;">Emulator Info</div>
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-light, #f0f0f0);">
                                    <span style="color: var(--text-muted); font-size: 13px;">Instance</span>
                                    <span style="font-weight: 600; font-size: 13px;">LDP-${acc.emulator.replace('#', '')}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-light, #f0f0f0);">
                                    <span style="color: var(--text-muted); font-size: 13px;">Provider</span>
                                    <span style="font-weight: 600; font-size: 13px;">${acc.provider}</span>
                                </div>
                            </div>
                        </div>

                        <!-- Right Column -->
                        <div style="display: flex; flex-direction: column; gap: 24px;">
                            <div>
                                <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 12px; text-transform: uppercase;">Game Status</div>
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-light, #f0f0f0);">
                                    <span style="color: var(--text-muted); font-size: 13px;">Alliance</span>
                                    <span style="font-weight: 600; font-size: 13px;">${acc.alliance}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-light, #f0f0f0);">
                                    <span style="color: var(--text-muted); font-size: 13px;">Hall Level</span>
                                    <span style="font-weight: 600; font-size: 13px;">${acc.hallLvl}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-light, #f0f0f0);">
                                    <span style="color: var(--text-muted); font-size: 13px;">Market Level</span>
                                    <span style="font-weight: 600; font-size: 13px;">${acc.marketLvl}</span>
                                </div>
                            </div>
                            
                            <div>
                                <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 12px; text-transform: uppercase;">Match</div>
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-light, #f0f0f0);">
                                    <span style="color: var(--text-muted); font-size: 13px; display: flex; align-items:center; gap: 4px;">Status <svg style="width:12px;color:var(--text-muted)" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg></span>
                                    <span style="color: var(--emerald-500); font-weight: 600; font-size: 13px; display: flex; align-items:center; gap: 4px;">
                                        <div style="background:var(--emerald-500); color:white; border-radius:4px; padding: 2px;"><svg style="width:10px;height:10px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg></div>
                                        Matched
                                    </span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-light, #f0f0f0);">
                                    <span style="color: var(--text-muted); font-size: 13px;">Total Linked</span>
                                    <span style="font-weight: 600; font-size: 13px;">${acc.accountsTotal} account(s)</span>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            `;
        }
        if (this._activeDetailTab === 'resources') {
            return `
                <div style="margin-bottom: 16px;">
                    <h3 style="font-size: 13px; font-weight: 700; color: var(--text); letter-spacing: 0.5px; margin: 0 0 16px 0; text-transform: uppercase;">Resource Stockpile</h3>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                    <!-- Gold -->
                    <div style="padding: 16px; border-radius: 8px; background: var(--surface-100); border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.02)">
                        <div style="display:flex; align-items:center; gap: 6px; font-size: 11px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.5px; margin-bottom: 8px;">
                           <div style="width:12px; height:12px; border-radius:50%; background:var(--yellow-400);"></div> GOLD
                        </div>
                        <div style="font-size: 20px; font-weight: 800; margin-bottom: 12px; color: var(--text);">${parseFloat(acc.gold) * 1000},000</div>
                        <div style="height: 4px; background: var(--surface-200); border-radius: 2px; margin-bottom: 8px; overflow: hidden;">
                            <div style="height: 100%; width: 50%; background: var(--yellow-500); border-radius: 2px;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 11px;">
                            <span style="color: var(--text-muted);">50% cap</span>
                            <span style="color: var(--emerald-500); font-weight: 600;">▲ +12,000</span>
                        </div>
                    </div>
                    
                    <!-- Wood -->
                    <div style="padding: 16px; border-radius: 8px; background: var(--surface-100); border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.02)">
                        <div style="display:flex; align-items:center; gap: 6px; font-size: 11px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.5px; margin-bottom: 8px;">
                           <div style="width:10px; height:12px; background:var(--orange-800); border-radius: 2px;"></div> WOOD
                        </div>
                        <div style="font-size: 20px; font-weight: 800; margin-bottom: 12px; color: var(--text);">${parseFloat(acc.wood) * 1000},000</div>
                        <div style="height: 4px; background: var(--surface-200); border-radius: 2px; margin-bottom: 8px; overflow: hidden;">
                            <div style="height: 100%; width: 75%; background: var(--border-strong, #ccc); border-radius: 2px;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 11px;">
                            <span style="color: var(--text-muted);">75% cap</span>
                            <span style="color: var(--emerald-500); font-weight: 600;">▲ +8,000</span>
                        </div>
                    </div>
                    
                    <!-- Ore -->
                    <div style="padding: 16px; border-radius: 8px; background: var(--surface-100); border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.02)">
                        <div style="display:flex; align-items:center; gap: 6px; font-size: 11px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.5px; margin-bottom: 8px;">
                           <svg style="width:12px; color: var(--indigo-400)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg> ORE
                        </div>
                        <div style="font-size: 20px; font-weight: 800; margin-bottom: 12px; color: var(--text);">${parseFloat(acc.ore) * 1000},000</div>
                        <div style="height: 4px; background: var(--surface-200); border-radius: 2px; margin-bottom: 8px; overflow: hidden;">
                            <div style="height: 100%; width: 24%; background: var(--border-strong, #ccc); border-radius: 2px;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 11px;">
                            <span style="color: var(--text-muted);">24% cap</span>
                            <span style="color: var(--red-500); font-weight: 600;">▼ 3,000</span>
                        </div>
                    </div>
                </div>

                <!-- Pet Tokens Full Width -->
                <div style="padding: 16px 20px; border-radius: 8px; background: linear-gradient(90deg, #FDF4FF 0%, #FAF5FF 100%); border: 1px solid #F3E8FF; display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div style="display:flex; align-items:center; gap: 16px;">
                        <div style="width: 40px; height: 40px; background: white; border-radius: 8px; display:flex; align-items:center; justify-content:center; box-shadow: 0 2px 8px rgba(168, 85, 247, 0.15);">
                            <svg style="width:20px; color:var(--purple-500, #A855F7)" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polygon points="2 17 12 22 22 17 22 12 12 17 2 12 2 17"/></svg>
                        </div>
                        <div>
                            <div style="font-size: 11px; font-weight: 700; color: var(--purple-600, #9333EA); letter-spacing: 0.5px; margin-bottom: 4px;">PET TOKENS</div>
                            <div style="font-size: 20px; font-weight: 800; color: var(--text); line-height: 1;">${acc.petToken}</div>
                        </div>
                    </div>
                    <div style="background: white; border: 1px solid #E9D5FF; color: var(--purple-600, #9333EA); padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600;">Special Currency</div>
                </div>

                <!-- AI Insight -->
                <div style="padding: 16px; border-radius: 8px; background: var(--blue-50, #EFF6FF); border: 1px solid #BFDBFE; display: flex; gap: 12px;">
                    <div style="color: var(--blue-600, #2563EB); margin-top: 2px;">
                        <svg style="width:18px;height:18px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    </div>
                    <div>
                        <div style="font-size: 13px; font-weight: 700; color: var(--blue-700, #1D4ED8); margin-bottom: 4px;">AI Insight</div>
                        <div style="font-size: 13px; color: var(--blue-800, #1E3A8A); line-height: 1.5;">
                            Ore is critically low (24%). Consider prioritizing farming runs before your next Hall upgrade. Gold cap will be reached in ~2 days at current production rates.
                        </div>
                    </div>
                </div>
            `;
        }
        if (this._activeDetailTab === 'activity') {
            return `
                <div style="margin-bottom: 24px;">
                    <h3 style="font-size: 13px; font-weight: 700; color: var(--text); letter-spacing: 0.5px; margin-bottom: 16px; text-transform: uppercase;">Activity Log</h3>
                    
                    <div style="margin-bottom: 32px;">
                        <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Operator Notes</div>
                        <textarea class="form-control" style="width: 100%; min-height: 100px; padding: 12px; border-radius: 6px; background: var(--surface-100); border: 1px solid var(--border); font-family: inherit; resize: vertical; margin-bottom: 12px; font-size: 13px; line-height: 1.5;">${acc.note}</textarea>
                        <div style="display:flex; justify-content: flex-end;">
                            <button class="btn btn-primary btn-sm" style="padding: 6px 16px;">Save Note</button>
                        </div>
                    </div>

                    <div>
                        <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.5px;">Recent History</div>
                        <div style="padding-left: 8px; border-left: 1px solid var(--border); display: flex; flex-direction: column; gap: 20px; position: relative; margin-left: 6px;">
                            
                            <div style="position: relative; padding-left: 16px;">
                                <div style="position: absolute; left: -12.5px; top: 4px; width: 8px; height: 8px; background: var(--primary); border-radius: 50%; box-shadow: 0 0 0 4px var(--surface-100);"></div>
                                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 2px;">Today, 10:23 AM</div>
                                <div style="font-size: 13px; color: var(--text);">Synced successfully via LDP-${acc.emulator.replace('#', '')}</div>
                            </div>
                            
                            <div style="position: relative; padding-left: 16px;">
                                <div style="position: absolute; left: -11.5px; top: 4px; width: 6px; height: 6px; background: var(--border-strong, #ccc); border-radius: 50%; box-shadow: 0 0 0 4px var(--surface-100);"></div>
                                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 2px;">Yesterday, 4:00 PM</div>
                                <div style="font-size: 13px; color: var(--text);">Resources updated: Gold +12k</div>
                            </div>
                            
                            <div style="position: relative; padding-left: 16px;">
                                <div style="position: absolute; left: -11.5px; top: 4px; width: 6px; height: 6px; background: var(--border-strong, #ccc); border-radius: 50%; box-shadow: 0 0 0 4px var(--surface-100);"></div>
                                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 2px;">2 days ago</div>
                                <div style="font-size: 13px; font-weight: 600; color: var(--text);">Account matched to profile</div>
                            </div>

                        </div>
                    </div>
                </div>
            `;
        }
        return '';
    },

    init() { },
    destroy() {
        this._selectedAccountId = null;
    }
};
