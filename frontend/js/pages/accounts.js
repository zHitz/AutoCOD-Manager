/**
 * Accounts Data Page
 * Shows a detailed table of Game Accounts.
 */
const AccountsPage = {
    _mockData: [
        {
            id: 1, emuName: 'LDPlayer-01', ingameName: 'DragonSlayer', pow: '12.5',
            loginMethod: 'Google', email: 'dragon@gmail.com', provider: 'Global',
            emulator: '#1', hallLvl: 25, marketLvl: 24, alliance: '[KOR] Warriors',
            accountsTotal: 3, accMatching: 'Yes', note: 'Main account',
            gold: '1.2', wood: '5.5', ore: '2.1', petToken: 450
        },
        {
            id: 2, emuName: 'LDPlayer-02', ingameName: 'FarmBot_01', pow: '2.1',
            loginMethod: 'Facebook', email: 'farm01@yahoo.com', provider: 'Global',
            emulator: '#2', hallLvl: 11, marketLvl: 10, alliance: 'None',
            accountsTotal: 1, accMatching: 'No', note: 'Farm wood fast',
            gold: '0.1', wood: '12.0', ore: '0.5', petToken: 12
        },
        {
            id: 3, emuName: 'LDPlayer-03', ingameName: 'FarmBot_02', pow: '1.8',
            loginMethod: 'Facebook', email: 'farm02@yahoo.com', provider: 'Global',
            emulator: '#3', hallLvl: 9, marketLvl: 9, alliance: 'None',
            accountsTotal: 1, accMatching: 'No', note: 'Farm ore',
            gold: '0.2', wood: '1.0', ore: '15.5', petToken: 5
        },
        {
            id: 4, emuName: 'LDPlayer-04', ingameName: 'SniperWolf', pow: '8.4',
            loginMethod: 'Apple', email: '-', provider: 'Global',
            emulator: '#4', hallLvl: 22, marketLvl: 20, alliance: '[US] Eagles',
            accountsTotal: 2, accMatching: 'Yes', note: 'Alt attack',
            gold: '4.5', wood: '2.2', ore: '3.1', petToken: 120
        },
        {
            id: 5, emuName: 'LDPlayer-05', ingameName: 'MinerKing', pow: '3.5',
            loginMethod: 'Google', email: 'miner@gmail.com', provider: 'Asia',
            emulator: '#5', hallLvl: 15, marketLvl: 15, alliance: '[KOR] Warriors',
            accountsTotal: 5, accMatching: 'Yes', note: 'Supply main',
            gold: '25.0', wood: '18.0', ore: '22.0', petToken: 60
        }
    ],

    render() {
        return `
            <div class="page-enter">
                <div class="page-header" style="justify-content: space-between;">
                    <div class="page-header-info">
                        <h2>Game Accounts</h2>
                        <p>Detailed view of all game accounts, resources, and statuses across your emulators.</p>
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

                <div class="card" style="padding: 0; overflow-x: auto;">
                    <table class="grid-table" style="width: 100%; min-width: 1600px; border-collapse: collapse; text-align: left;">
                        <thead style="background: var(--surface-100); border-bottom: 1px solid var(--border);">
                            <tr>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); width: 60px;">STT</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Emu Name</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">In-game Name</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: right;">POW (M)</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Login Method</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Email</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Provider</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Target</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: right;">Hall Lvl</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: right;">Market Lvl</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Alliance</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: center;">Accounts Num</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: center;">Match</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: right; color: var(--yellow-500);">Gold (M)</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: right; color: var(--emerald-500);">Wood (M)</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: right; color: var(--indigo-500);">Ore (M)</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted); text-align: right; color: var(--orange-500);">Pet C.</th>
                                <th style="padding: 12px 16px; font-weight: 600; font-size: 13px; color: var(--text-muted);">Note</th>
                            </tr>
                        </thead>
                        <tbody id="accounts-table-body">
                            ${this._renderTableBody()}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    },

    _renderTableBody() {
        return this._mockData.map((row, index) => `
            <tr style="border-bottom: 1px solid var(--border); transition: background 0.2s;" onmouseover="this.style.background='var(--surface-50)'" onmouseout="this.style.background='transparent'">
                <td style="padding: 12px 16px; font-size: 13px;">${row.id}</td>
                <td style="padding: 12px 16px; font-size: 13px; font-weight: 500;">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <div style="width:6px;height:6px;border-radius:50%;background:var(--emerald-500)"></div>
                        ${row.emuName}
                    </div>
                </td>
                <td style="padding: 12px 16px; font-size: 13px; font-weight: 600; color: var(--primary);">${row.ingameName}</td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace;">${row.pow}</td>
                <td style="padding: 12px 16px; font-size: 13px;">
                    <span class="badge badge-outline" style="border-radius:4px; border-color: ${row.loginMethod === 'Google' ? '#EA4335' : row.loginMethod === 'Facebook' ? '#1877F2' : '#333'}">${row.loginMethod}</span>
                </td>
                <td style="padding: 12px 16px; font-size: 13px; color: var(--text-muted);">${row.email}</td>
                <td style="padding: 12px 16px; font-size: 13px;">${row.provider}</td>
                <td style="padding: 12px 16px; font-size: 13px;">
                     <span class="badge" style="background:var(--surface-200); color:var(--text);">${row.emulator}</span>
                </td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-weight: 600;">${row.hallLvl}</td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-weight: 600;">${row.marketLvl}</td>
                <td style="padding: 12px 16px; font-size: 13px;">${row.alliance}</td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: center;">${row.accountsTotal}</td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: center;">
                    ${row.accMatching === 'Yes' ? '<span style="color:var(--emerald-500)">✓</span>' : '<span style="color:var(--red-500)">✗</span>'}
                </td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace; font-weight: 600; color: var(--yellow-500);">${row.gold}</td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace; font-weight: 600; color: var(--emerald-500);">${row.wood}</td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace; font-weight: 600; color: var(--indigo-500);">${row.ore}</td>
                <td style="padding: 12px 16px; font-size: 13px; text-align: right; font-family: monospace; font-weight: 600; color: var(--orange-500);">${row.petToken}</td>
                <td style="padding: 12px 16px; font-size: 12px; color: var(--text-muted); max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${row.note}">${row.note}</td>
            </tr>
        `).join('');
    },

    init() { },
    destroy() { }
};
