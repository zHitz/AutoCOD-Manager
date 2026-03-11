/**
 * Accounts Data Page
 * Shows a detailed table of Game Accounts with an off-canvas Slide Profile View.
 */
const AccountsPage = {
    _accountsData: [],
    _pendingAccounts: [],
    _selectedAccountId: null,
    _activeDetailTab: 'overview',
    _viewMode: 'table',
    _pageState: 'loading',  // 'loading' | 'ready' | 'error' | 'empty'
    _errorMessage: '',
    _actionLoading: {},     // { [actionKey]: true }
    _comparisonCache: {},
    _sortField: null,
    _sortDirection: 'asc',

    formatDateTime(value) {
        if (!value) return 'Never';
        const dt = new Date(value);
        if (Number.isNaN(dt.getTime())) return 'Never';
        return dt.toLocaleString();
    },

    _normalizeLoginMethod(method) {
        const m = (method || '').toLowerCase();
        if (m === 'google') return 'Google';
        if (m === 'facebook') return 'Facebook';
        if (m === 'email') return 'Email';
        return 'Email';
    },

    _normalizeProvider(provider) {
        const p = (provider || '').toLowerCase();
        if (p === 'funtap') return 'Funtap';
        return 'Global';
    },

    _getRuntimeStatus(row) {
        const emuStatus = (row.emu_status || '').toLowerCase();
        const hasEmulatorLink = !!row.emulator_db_id || row.emu_index != null || !!row.emu_name;
        if (row.is_active === 1 && emuStatus === 'online') {
            return { label: '🟢 Running', style: 'background:rgba(16,185,129,0.1);color:var(--emerald-500);border:1px solid rgba(16,185,129,0.25);border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;', title: 'Active and online now' };
        }
        if (row.is_active === 1) {
            return { label: '🟡 Ready', style: 'background:rgba(234,179,8,0.1);color:var(--yellow-500);border:1px solid rgba(234,179,8,0.25);border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;', title: 'Enabled but emulator is offline' };
        }
        if (hasEmulatorLink) {
            return { label: '⚪ Linked', style: 'background:var(--muted);color:var(--muted-foreground);border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;border:1px solid var(--border);', title: 'Linked to emulator, not active' };
        }
        return { label: '🔴 Unlinked', style: 'background:rgba(239,68,68,0.1);color:var(--red-500);border:1px solid rgba(239,68,68,0.25);border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;', title: 'No emulator linked' };
    },

    formatResource(valAbs) {
        if (!valAbs || isNaN(valAbs)) return '0M';
        if (valAbs >= 1000000000) return (valAbs / 1000000000).toFixed(1) + 'B';
        if (valAbs >= 1000000) return (valAbs / 1000000).toFixed(1) + 'M';
        if (valAbs >= 1000) return (valAbs / 1000).toFixed(1) + 'K';
        return valAbs.toString();
    },

    formatPower(valAbs) {
        if (!valAbs || isNaN(valAbs)) return '0M';
        if (valAbs >= 1000000000) return (valAbs / 1000000000).toFixed(1) + 'B';
        if (valAbs >= 1000000) return (valAbs / 1000000).toFixed(1) + 'M';
        return valAbs.toLocaleString();
    },



    _sortValue(row, field) {
        const text = (v) => (v == null ? '' : String(v)).toLowerCase();
        switch (field) {
            case 'account_id': return Number(row.account_id || 0);
            case 'emulator': return text(row.emu_name || (row.emu_index != null ? `ldp-${row.emu_index}` : ''));
            case 'name': return text(row.lord_name || '');
            case 'game_id': return text(row.game_id || '');
            case 'power': return Number(row.power || 0);
            case 'runtime': {
                const rank = { '🟢 Running': 4, '🟡 Ready': 3, '⚪ Linked': 2, '🔴 Unlinked': 1 };
                return rank[this._getRuntimeStatus(row).label] || 0;
            }
            case 'provider': return text(this._normalizeProvider(row.provider));
            case 'gold': return Number(row.gold || 0);
            case 'wood': return Number(row.wood || 0);
            case 'ore': return Number(row.ore || 0);
            case 'pet_token': return Number(row.pet_token || 0);
            case 'mana': return Number(row.mana || 0);
            default: return Number(row.account_id || 0);
        }
    },

    _sortedAccounts() {
        if (!this._sortField) return [...this._accountsData];
        const dir = this._sortDirection === 'desc' ? -1 : 1;
        return [...this._accountsData].sort((a, b) => {
            const av = this._sortValue(a, this._sortField);
            const bv = this._sortValue(b, this._sortField);
            if (av === bv) return Number(a.account_id || 0) - Number(b.account_id || 0);
            if (typeof av === 'string' || typeof bv === 'string') return String(av).localeCompare(String(bv)) * dir;
            return (av > bv ? 1 : -1) * dir;
        });
    },

    sortBy(field) {
        if (this._sortField === field) {
            this._sortDirection = this._sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this._sortField = field;
            this._sortDirection = 'asc';
        }

        if (typeof router !== 'undefined' && router._currentPage === 'accounts') {
            const root = document.getElementById('page-root');
            if (root) root.innerHTML = this.render();
        }
    },

    _sortIndicator(field) {
        if (this._sortField !== field) return '<span style="opacity:.35; margin-left:6px;">↕</span>';
        return this._sortDirection === 'asc'
            ? '<span style="margin-left:6px;color:var(--primary);">↑</span>'
            : '<span style="margin-left:6px;color:var(--primary);">↓</span>';
    },

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
                .resource-cell { display: inline-flex; align-items: center; justify-content: flex-end; gap: 6px; min-width: 78px; }
                .resource-delta { width: 10px; display: inline-block; text-align: center; font-size: 10px; line-height: 1; font-family: sans-serif; }
                .resource-delta.up { color: var(--emerald-500); }
                .resource-delta.down { color: var(--red-500); }
                .resource-delta.neutral, .resource-delta.empty { color: var(--muted-foreground); }

                /* Status dots */
                .status-dot-on  { width: 7px; height: 7px; border-radius: 50%; background: var(--emerald-500); box-shadow: 0 0 5px var(--emerald-500); display: inline-block; flex-shrink: 0; }
                .status-dot-off { width: 7px; height: 7px; border-radius: 50%; background: var(--border); display: inline-block; flex-shrink: 0; }

                /* Skeleton loading animation */
                @keyframes pulse-bg {
                    0%, 100% { opacity: 1; }
                    50% { opacity: .5; }
                }
                .skel-box { background: var(--muted); border-radius: 4px; animation: pulse-bg 1.5s ease-in-out infinite; }
                .skel-text { height: 16px; margin: 4px 0; }
                .skel-badge { width: 50px; height: 18px; border-radius: 12px; }
                .skel-avatar { width: 32px; height: 32px; border-radius: 6px; }

                /* Table header group row */
                .th-group { background: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: 0.6px; text-transform: uppercase; color: var(--muted-foreground); padding: 8px 16px; border-bottom: 1px solid var(--border); text-align: center; }
                .th-col { padding: 10px 14px; font-weight: 600; font-size: 12px; color: var(--muted-foreground); background: var(--card); border-bottom: 2px solid var(--border); white-space: nowrap; }
                .th-col.accent { color: var(--primary); }
                .th-sortable { cursor: pointer; user-select: none; }
                .th-sortable:hover { background: var(--accent); }

                /* ── GRID / CARD LIST ── */
                .account-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; align-items: start; }

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
                    overflow-y: auto; overflow-x: hidden;
                }
                .slide-panel.active { transform: translateX(0); }

                /* Safe Delete Modal */
                #custom-delete-modal { display: none; position: fixed; inset: 0; z-index: 2000; align-items: center; justify-content: center; }
                #custom-delete-modal.active { display: flex; }
                .modal-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(2px); animation: fadeIn 0.2s ease; }
                .modal-content { position: relative; background: var(--card); width: 440px; max-width: 90vw; border-radius: 12px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); padding: 24px; animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1); border: 1px solid var(--border); }
                .modal-icon { width: 48px; height: 48px; border-radius: 50%; background: rgba(var(--red-500-rgb, 239,68,68),0.1); color: var(--red-500); display: flex; align-items: center; justify-content: center; margin-bottom: 16px; }
                .modal-title { font-size: 18px; font-weight: 800; color: var(--foreground); margin: 0 0 8px; }

                /* ── Form Modal Styles (Add/Edit) ── */
                .form-section { margin-bottom: 28px; }
                .section-label {
                    font-size: 10px; font-weight: 700; letter-spacing: 0.12em;
                    color: var(--primary); text-transform: uppercase;
                    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
                }
                .section-label::after {
                    content: ''; flex: 1; height: 1px;
                    background: linear-gradient(90deg, rgba(var(--primary-rgb, 99, 102, 241), 0.25), transparent);
                }
                .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
                .form-grid.full { grid-template-columns: 1fr; }
                .field { display: flex; flex-direction: column; gap: 7px; }
                .field label {
                    font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
                    color: var(--muted-foreground); text-transform: uppercase;
                    display: flex; align-items: center; gap: 5px;
                }
                .field .required {
                    display: inline-block; width: 5px; height: 5px; border-radius: 50%;
                    background: var(--primary); margin-bottom: 1px;
                }
                .field input, .field select, .field textarea {
                    background: var(--muted); border: 1px solid var(--border);
                    border-radius: 10px; padding: 11px 14px;
                    font-family: inherit; font-size: 13px; font-weight: 400;
                    color: var(--foreground);
                    transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
                    outline: none; appearance: none; -webkit-appearance: none; width: 100%;
                }
                .field input::placeholder, .field textarea::placeholder { color: var(--muted-foreground); opacity: 0.6; }
                .field input:focus, .field select:focus, .field textarea:focus {
                    border-color: rgba(var(--primary-rgb, 99, 102, 241), 0.5);
                    box-shadow: 0 0 0 3px rgba(var(--primary-rgb, 99, 102, 241), 0.1);
                    background: var(--card);
                }
                .field select {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='none' stroke='%2364748b' stroke-width='2' viewBox='0 0 24 24'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
                    background-repeat: no-repeat; background-position: right 14px center;
                    padding-right: 36px; cursor: pointer;
                }
                .field select option { background: var(--card); color: var(--foreground); }
                .field textarea { resize: vertical; min-height: 90px; line-height: 1.6; }
                .field .hint { font-size: 11px; color: var(--muted-foreground); margin-top: -2px; }
                .modal-footer {
                    display: flex; align-items: center; justify-content: flex-end; gap: 10px;
                    padding: 18px 28px 24px; border-top: 1px solid var(--border); margin-top: 10px;
                }
                @media (max-width: 560px) { .form-grid { grid-template-columns: 1fr; } }

                .modal-desc { font-size: 14px; color: var(--muted-foreground); margin: 0 0 20px; line-height: 1.5; }
                .modal-target { padding: 12px; background: var(--muted); border-radius: 6px; border: 1px solid var(--border); margin-bottom: 20px; }
                .modal-target-label { font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--muted-foreground); letter-spacing: 0.5px; margin-bottom: 4px; }
                .modal-target-value { font-size: 14px; font-weight: 600; color: var(--foreground); }
                @keyframes slideUp { from { opacity: 0; transform: translateY(20px) scale(0.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
                @keyframes fadeDown { from { opacity: 0; transform: translateY(-12px); } to { opacity: 1; transform: translateY(0); } }

                /* Panel wrapper */
                .panel-content-wrap { padding: 32px 24px 80px; }

                /* ── Header ── */
                .panel-header {
                    display: flex; align-items: center; justify-content: space-between;
                    padding: 20px 28px; background: var(--card); border: 1px solid var(--border);
                    border-radius: 16px; margin-bottom: 20px; animation: fadeDown 0.4s ease both;
                }
                .header-left { display: flex; align-items: center; gap: 18px; }
                .panel-avatar {
                    width: 56px; height: 56px; border-radius: 14px;
                    background: linear-gradient(135deg, var(--primary), var(--indigo-500, #6366f1));
                    color: #fff; display: flex; align-items: center; justify-content: center;
                    font-size: 26px; font-weight: 700; flex-shrink: 0;
                    box-shadow: 0 0 24px rgba(var(--primary-rgb, 99, 102, 241), 0.35);
                }
                .title-block h2 { font-size: 22px; font-weight: 700; letter-spacing: 0.03em; color: var(--foreground); margin: 0; }
                .title-block .meta { display: flex; align-items: center; gap: 12px; font-size: 12px; color: var(--muted-foreground); margin-top: 4px; }
                .meta span { display: flex; align-items: center; gap: 4px; }
                
                .header-actions { display: flex; gap: 10px; }
                .btn-ghost { background: var(--muted); color: var(--muted-foreground); border: 1px solid var(--border); }
                .btn-ghost:hover { color: var(--foreground); border-color: rgba(255,255,255,0.12); }
                .overflow-menu.active { display: block !important; }

                /* ── Stat Cards ── */
                .stats-row {
                    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
                    margin-bottom: 20px; animation: fadeDown 0.4s 0.1s ease both;
                }
                .stat-card {
                    background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
                    position: relative; overflow: hidden; transition: border-color 0.2s, transform 0.2s;
                }
                .stat-card:hover { border-color: rgba(var(--primary-rgb, 99,102,241), 0.25); transform: translateY(-2px); }
                .stat-card::before {
                    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
                    background: linear-gradient(90deg, transparent, var(--primary), transparent);
                    opacity: 0; transition: opacity 0.3s;
                }
                .stat-card:hover::before { opacity: 1; }
                .stat-label { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; color: var(--muted-foreground); text-transform: uppercase; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
                .stat-value { font-size: 32px; font-weight: 700; color: var(--foreground); line-height: 1; }
                .stat-value.accent { color: var(--primary); }
                .stat-sub { font-size: 11px; color: var(--muted-foreground); margin-top: 8px; display: flex; align-items: center; gap: 6px; }
                
                .progress-bar { width: 100%; height: 4px; background: var(--muted); border-radius: 4px; margin-top: 10px; overflow: hidden; }
                @keyframes growBar { from { width: 0 !important; } }
                .progress-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, var(--primary), var(--yellow-400)); transition: width 0.45s ease; transform-origin: left; }
                .sync-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--emerald-500); animation: pulse 2s infinite; display: inline-block; }
                .stat-value-sync { display: flex; flex-direction: column; gap: 2px; line-height: 1.05; }
                .stat-value-sync .sync-date-line { font-size: 29px; font-weight: 700; letter-spacing: -0.01em; }
                .stat-value-sync .sync-time-line { font-size: 23px; font-weight: 600; color: var(--foreground); opacity: 0.95; }
                @keyframes pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.5); } 50% { box-shadow: 0 0 0 6px rgba(16,185,129,0); } }

                /* ── Tabs ── */
                .panel-tabs {
                    display: flex; gap: 4px; border-bottom: 1px solid var(--border);
                    margin-bottom: 20px; animation: fadeDown 0.4s 0.15s ease both;
                }
                .panel-tab {
                    padding: 10px 20px; font-size: 13px; font-weight: 600; color: var(--muted-foreground); cursor: pointer;
                    border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.2s; user-select: none;
                }
                .panel-tab:hover:not(.active) { color: var(--foreground); }
                .panel-tab.active { color: var(--primary); border-bottom-color: var(--primary); }

                /* ── Info Sections ── */
                .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; animation: fadeDown 0.4s 0.2s ease both; }
                .info-card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 24px; }
                .section-title { font-size: 10px; font-weight: 700; letter-spacing: 0.12em; color: var(--primary); text-transform: uppercase; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
                .section-title::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(var(--primary-rgb, 99, 102, 241), 0.3), transparent); }
                
                .info-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border); }
                .info-row:last-child { border-bottom: none; padding-bottom: 0; }
                .info-row:first-of-type { padding-top: 0; }
                .info-key { font-size: 12px; color: var(--muted-foreground); font-weight: 400; }
                .info-val { font-size: 13px; font-weight: 600; color: var(--foreground); display: flex; align-items: center; gap: 6px; }

                .provider-tag { background: rgba(59,130,246,0.1); color: var(--blue-500); border: 1px solid rgba(59,130,246,0.2); padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }
                .alliance-tag { background: rgba(var(--primary-rgb, 99,102,241), 0.12); color: var(--primary); border: 1px solid rgba(var(--primary-rgb, 99,102,241), 0.25); padding: 3px 12px; border-radius: 6px; font-size: 14px; font-weight: 700; letter-spacing: 0.05em; }
                
                .level-meter { display: flex; align-items: center; gap: 10px; }
                .level-num { font-size: 16px; font-weight: 700; color: var(--yellow-500); min-width: 20px; }
                .meter { width: 80px; height: 5px; background: var(--muted); border-radius: 4px; overflow: hidden; }
                .meter-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, var(--yellow-500), #fde047); }
                .level-max { font-size: 11px; color: var(--muted-foreground); }

                .status-dot-on  { width: 6px; height: 6px; border-radius: 50%; background: var(--emerald-500); box-shadow: 0 0 5px var(--emerald-500); display: inline-block; }
                .status-dot-off { width: 6px; height: 6px; border-radius: 50%; background: var(--border); display: inline-block; }

                /* Common badging system */
                .slide-badge { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 20px; display: inline-flex; align-items: center; gap: 5px; letter-spacing: 0.05em; }
                .slide-badge--online  { background: rgba(16,185,129,0.12); color: var(--emerald-500); border: 1px solid rgba(16,185,129,0.25); }
                .slide-badge--offline { background: var(--muted); color: var(--muted-foreground); border: 1px solid var(--border); }
                .slide-badge--matched { background: rgba(59,130,246,0.12); color: var(--blue-500); border: 1px solid rgba(59,130,246,0.25); }
                .slide-badge--unsynced { background: rgba(107,114,128,0.08); color: var(--muted-foreground); border: 1px solid var(--border); }



                /* ── RESOURCES TAB STYLES ── */
                .res-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 16px; }
                .res-card {
                    background: var(--card); border: 1px solid rgba(0,0,0,0.06);
                    border-radius: 12px; padding: 16px; transition: all 0.2s ease;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                }
                .res-card:hover { border-color: var(--border); box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-1px); }
                .res-card.critical { border-color: rgba(239,68,68,0.4); background: rgba(239,68,68,0.06); box-shadow: 0 0 12px rgba(239,68,68,0.08); }
                .res-header { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
                .res-icon { font-size: 14px; }
                .res-label { font-size: 12px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; }
                .res-label.gold { color: var(--yellow-600, #d97706); }
                .res-label.wood { color: var(--orange-700, #c2410c); }
                .res-label.ore  { color: var(--indigo-500, #6366f1); }
                .res-value { font-size: 20px; font-weight: 700; margin-bottom: 12px; color: var(--foreground); font-variant-numeric: tabular-nums; }
                .res-value.critical { color: var(--red-500); }
                .res-bar  { height: 6px; background: var(--muted); border-radius: 99px; overflow: hidden; margin-bottom: 8px; }
                .res-fill { height: 100%; border-radius: 99px; }
                .res-fill.gold    { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
                .res-fill.wood    { background: linear-gradient(90deg, #ea580c, #f97316); }
                .res-fill.ore     { background: linear-gradient(90deg, #6366f1, #818cf8); }
                .res-fill.critical-fill { background: linear-gradient(90deg, #dc2626, #f87171); }
                .res-footer { display: flex; justify-content: space-between; font-size: 11px; }
                .res-cap { color: var(--muted-foreground); }
                .res-cap.warn { color: var(--red-500); font-weight: 600; }
                .delta-up   { color: var(--emerald-500); font-weight: 700; }
                .delta-down { color: var(--red-500); font-weight: 700; }
                .delta-loading { color: var(--muted-foreground); font-size: 11px; opacity: 0.5; }

                .pet-card {
                    background: var(--card);
                    border: 1px solid rgba(0,0,0,0.06); border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                    padding: 16px; display: flex; justify-content: space-between;
                    align-items: center; margin-bottom: 16px;
                }
                .pet-left { display: flex; align-items: center; gap: 14px; }
                .pet-icon { width: 38px; height: 38px; background: var(--muted); border-radius: 8px; display: flex; align-items: center; justify-content: center; }
                .pet-label-txt { font-size: 12px; font-weight: 700; color: var(--muted-foreground); letter-spacing: 0.6px; text-transform: uppercase; margin-bottom: 4px; }
                .pet-value { font-size: 16px; font-weight: 700; color: var(--foreground); line-height: 1; }
                .pet-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
                .pet-badge { background: transparent; border: 1px solid var(--border); color: var(--muted-foreground); padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
                .pet-delta { font-size: 12px; font-weight: 700; }

                .ai-insight {
                    background: transparent; border: 1px solid var(--border);
                    border-radius: 10px; padding: 16px;
                    display: flex; gap: 12px; align-items: flex-start;
                }
                .ai-icon { color: var(--primary); margin-top: 2px; flex-shrink: 0; }
                .ai-title { font-size: 12px; font-weight: 700; color: var(--primary); margin-bottom: 4px; display: flex; align-items: center; gap: 4px; }
                .ai-body  { font-size: 14px; color: var(--foreground); line-height: 1.55; }

                /* ── ACTIVITY LOG TAB STYLES ── */
                .act-section-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted-foreground); margin-bottom: 12px; }
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
                            <p style="margin:0; color: var(--muted-foreground); font-size:13px;">${this._pageState === 'loading' ? 'Loading...' : this._accountsData.length + ' accounts connected'}</p>
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
                        <button class="btn btn-outline btn-sm" style="display:flex;align-items:center;gap:6px; opacity:0.6; cursor:not-allowed;" title="Coming soon">
                            <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Export CSV
                        </button>
                        <button class="btn btn-outline btn-sm" style="display:flex;align-items:center;gap:6px;" id="actions-sync-all-btn" onclick="AccountsPage.fetchData()">
                            <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Sync All
                        </button>
                        <button class="btn btn-primary btn-sm" style="display:flex;align-items:center;gap:6px;" onclick="AccountsPage.openAddForm()">
                            <svg style="width:13px;height:13px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                            Add Account
                        </button>
                    </div>
                </div>

                <!-- Pending Queue Banner -->
                <div id="pending-queue-container">${this._renderPendingBanner()}</div>

                <!-- Main content: table or grid -->
                <div class="${this._viewMode === 'grid' ? '' : 'card'}" style="overflow: auto; flex: 1; ${this._viewMode === 'table' ? 'padding:0;' : ''}">
                    ${this._viewMode === 'table' ? `
                    <table class="accounts-table">
                        <thead style="position: sticky; top: 0; z-index: 10;">
                            <tr>
                                <th class="th-col th-sortable freeze-col-1 stt-col" style="padding-left:14px;z-index:11;" onclick="AccountsPage.sortBy('account_id')"># ${this._sortIndicator('account_id')}</th>
                                <th class="th-col th-sortable freeze-col-2" style="min-width:110px;z-index:11;" onclick="AccountsPage.sortBy('emulator')">Emulator ${this._sortIndicator('emulator')}</th>
                                <th class="th-col th-sortable freeze-col-3" style="min-width:140px;z-index:11;border-right:2px solid var(--border);" onclick="AccountsPage.sortBy('name')">Name ${this._sortIndicator('name')}</th>
                                <th class="th-col th-sortable" style="border-left:1px solid var(--border);font-size:11px;" onclick="AccountsPage.sortBy('game_id')">Game ID ${this._sortIndicator('game_id')}</th>
                                <th class="th-col th-sortable accent" style="text-align:right;" onclick="AccountsPage.sortBy('power')">Power ${this._sortIndicator('power')}</th>
                                <th class="th-col th-sortable" style="text-align:center;" onclick="AccountsPage.sortBy('runtime')">Runtime State ${this._sortIndicator('runtime')}</th>
                                <th class="th-col th-sortable" style="text-align:center;" onclick="AccountsPage.sortBy('provider')">Provider ${this._sortIndicator('provider')}</th>
                                <th class="th-col th-sortable" style="text-align:right;color:var(--yellow-600,#d97706);border-left:1px solid var(--border);" onclick="AccountsPage.sortBy('gold')">Gold ${this._sortIndicator('gold')}</th>
                                <th class="th-col th-sortable" style="text-align:right;color:var(--emerald-600,#059669);" onclick="AccountsPage.sortBy('wood')">Wood ${this._sortIndicator('wood')}</th>
                                <th class="th-col th-sortable" style="text-align:right;color:var(--indigo-500,#6366f1);" onclick="AccountsPage.sortBy('ore')">Ore ${this._sortIndicator('ore')}</th>
                                <th class="th-col th-sortable" style="text-align:right;color:var(--orange-500,#f97316);" onclick="AccountsPage.sortBy('pet_token')">Pet 🐾 ${this._sortIndicator('pet_token')}</th>
                                <th class="th-col th-sortable" style="text-align:right;color:var(--purple-500,#a855f7);" onclick="AccountsPage.sortBy('mana')">Mana ✦ ${this._sortIndicator('mana')}</th>
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
                
                <!-- Safe Delete Modal Container -->
                <div id="delete-modal-container"></div>
            </div>
        `;
    },

    _renderTableBody() {
        if (this._pageState === 'loading') {
            return Array(6).fill(0).map((_, i) => `
                <tr class="account-row" style="animation: pulse-bg 1.5s ease-in-out infinite;">
                    <td class="freeze-col-1 stt-col" style="padding:11px 0 11px 14px;"><div class="skel-box skel-text" style="width:20px;"></div></td>
                    <td class="freeze-col-2" style="padding:11px 14px;"><div class="skel-box skel-text" style="width:70px;"></div></td>
                    <td class="freeze-col-3" style="padding:11px 14px; border-right:2px solid var(--border);"><div class="skel-box skel-text" style="width:100px;"></div></td>
                    <td style="padding:11px 14px; border-left:1px solid var(--border);"><div class="skel-box skel-text" style="width:80px;"></div></td>
                    <td style="padding:11px 14px;"><div class="skel-box skel-text" style="width:60px; margin-left:auto;"></div></td>
                    <td style="padding:11px 14px; text-align:center;"><div class="skel-box skel-badge" style="margin: 0 auto;"></div></td>
                    <td style="padding:11px 14px;"><div class="skel-box skel-text" style="width:50px; margin: 0 auto;"></div></td>
                    <td style="padding:11px 14px; border-left:1px solid var(--border);"><div class="skel-box skel-text" style="width:50px; margin-left:auto;"></div></td>
                    <td style="padding:11px 14px;"><div class="skel-box skel-text" style="width:50px; margin-left:auto;"></div></td>
                    <td style="padding:11px 14px;"><div class="skel-box skel-text" style="width:50px; margin-left:auto;"></div></td>
                    <td style="padding:11px 14px;"><div class="skel-box skel-text" style="width:50px; margin-left:auto;"></div></td>
                    <td style="padding:11px 14px;"><div class="skel-box skel-text" style="width:50px; margin-left:auto;"></div></td>
                    <td style="padding:11px 14px;"></td>
                </tr>
            `).join('');
        }

        if (this._pageState === 'error') {
            return `
            <tr>
                <td colspan="13" style="padding: 30px;">
                    <div style="background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.2); border-radius:8px; padding:20px; text-align:center; color:var(--red-500);">
                        <svg style="width:24px;height:24px;margin:0 auto 10px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                        <h3 style="margin:0 0 6px; font-size:16px;">Could not load accounts</h3>
                        <p style="margin:0 0 16px; font-size:13px; opacity:0.8;">${this._errorMessage}</p>
                        <button class="btn btn-outline" onclick="AccountsPage.fetchData()">Try Again</button>
                    </div>
                </td>
            </tr>`;
        }

        if (this._pageState === 'empty') {
            return `
            <tr>
                <td colspan="13" style="padding: 40px;">
                    <div style="text-align:center; max-width:400px; margin: 0 auto; color:var(--muted-foreground);">
                        <svg style="width:40px;height:40px;margin:0 auto 14px;color:var(--border);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
                        <h3 style="margin:0 0 8px; font-size:18px; color:var(--foreground);">No accounts yet</h3>
                        <p style="margin:0 0 20px; font-size:14px; line-height:1.5;">Add your first game account to start tracking resources, managing status, and syncing data.</p>
                        <button class="btn btn-primary" onclick="AccountsPage.openAddForm()">+ Add Account</button>
                    </div>
                </td>
            </tr>`;
        }

        return this._sortedAccounts().map((row) => {
            const statusStr = (row.emu_status || 'offline').toLowerCase();
            const dotClass = statusStr === 'online' ? 'status-dot-on' : 'status-dot-off';
            const isSelected = this._selectedAccountId === row.account_id;

            // Format metrics
            const powFormatted = AccountsPage.formatPower(row.power);
            const goldFormatted = AccountsPage.formatResource(row.gold);
            const woodFormatted = AccountsPage.formatResource(row.wood);
            const oreFormatted = AccountsPage.formatResource(row.ore);
            const manaFormatted = AccountsPage.formatResource(row.mana);
            const ingameName = row.lord_name || '—';
            const displayEmail = row.email || '—';
            const displayAlliance = row.alliance || '—';
            const gameId = row.game_id || '—';
            const isLegacy = gameId.startsWith('LEGACY-');

            // Delta setup
            const mkInlineDelta = (key) => {
                const cached = this._comparisonCache[gameId];
                if (!cached || !cached.delta || cached.delta[key] == null) return '<span class="resource-delta empty"></span>';
                if (cached.delta[key] === 0) return '<span class="resource-delta neutral" title="No change">•</span>';
                const v = cached.delta[key];
                const isUp = v > 0;
                return `<span class="resource-delta ${isUp ? 'up' : 'down'}" title="${isUp ? '+' : ''}${v.toLocaleString()}">${isUp ? '▲' : '▼'}</span>`;
            };
            const runtimeStatus = this._getRuntimeStatus(row);
            const statusBadge = `<span title="${runtimeStatus.title}" style="${runtimeStatus.style}">${runtimeStatus.label}</span>`;

            return `
            <tr class="account-row${isSelected ? ' selected' : ''}" onclick="AccountsPage.openDetail(${row.account_id})">
                <td class="freeze-col-1 stt-col" style="padding:11px 0 11px 14px;font-size:12px;color:var(--muted-foreground);">${row.account_id}</td>
                <td class="freeze-col-2" style="padding:11px 14px;font-size:13px;">
                    <div style="display:flex;align-items:center;gap:7px;">
                        <span class="${dotClass}" title="${statusStr}"></span>
                        <span style="font-weight:500;">${row.emu_name || (row.emu_index != null ? 'LDP-' + row.emu_index : '—')}</span>
                    </div>
                </td>
                <td class="freeze-col-3" style="padding:11px 14px;font-size:13px;font-weight:700;color:var(--primary);border-right:2px solid var(--border);">${ingameName}</td>
                <td style="padding:11px 14px;font-size:12px;font-family:monospace;color:var(--muted-foreground);border-left:1px solid var(--border);">${isLegacy ? '<span style="color:var(--yellow-500)" title="Legacy account - needs Game ID">⚠️</span>' : gameId}</td>
                <td style="padding:11px 14px;text-align:right;font-family:monospace;font-weight:700;font-size:13px;">${powFormatted}</td>
                <td style="padding:11px 14px;text-align:center;">${statusBadge}</td>
                <td style="padding:11px 14px;text-align:center;font-size:12px;">${this._normalizeProvider(row.provider)}</td>
                <td style="padding:11px 14px;text-align:right;border-left:1px solid var(--border);">
                    <span class="resource-cell"><span class="resource-val" style="color:var(--yellow-600,#d97706);font-size:13px;">${goldFormatted}</span>${mkInlineDelta('gold')}</span>
                </td>
                <td style="padding:11px 14px;text-align:right;">
                    <span class="resource-cell"><span class="resource-val" style="color:var(--emerald-600,#059669);font-size:13px;">${woodFormatted}</span>${mkInlineDelta('wood')}</span>
                </td>
                <td style="padding:11px 14px;text-align:right;">
                    <span class="resource-cell"><span class="resource-val" style="color:var(--indigo-500,#6366f1);font-size:13px;">${oreFormatted}</span>${mkInlineDelta('ore')}</span>
                </td>
                <td style="padding:11px 14px;text-align:right;">
                    <span class="resource-cell"><span class="resource-val" style="color:var(--orange-500,#f97316);font-size:13px;">${(row.pet_token || 0).toLocaleString()}</span>${mkInlineDelta('pet_token')}</span>
                </td>
                <td style="padding:11px 14px;text-align:right;">
                    <span class="resource-cell"><span class="resource-val" style="color:var(--purple-500,#a855f7);font-size:13px;">${manaFormatted}</span>${mkInlineDelta('mana')}</span>
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
        if (this._pageState === 'loading') {
            return Array(4).fill(0).map((_, i) => `
                <div class="account-card" style="animation: pulse-bg 1.5s ease-in-out infinite;">
                    <div class="card-dot" style="background:var(--border)"></div>
                    <div class="account-info">
                        <div class="skel-box skel-text" style="width:120px;height:18px;"></div>
                        <div class="skel-box skel-text" style="width:140px;height:12px;"></div>
                    </div>
                    <div class="account-power" style="margin-left:auto;">
                        <div class="power-label">
                            <div class="skel-box skel-text" style="width:60px;"></div>
                        </div>
                        <div class="power-bar"><div class="skel-box" style="width:100%;height:100%;"></div></div>
                    </div>
                </div>
            `).join('');
        }
        if (this._pageState === 'error') {
            return `<div style="grid-column: 1/-1; text-align:center; padding:40px; color:var(--red-500); background:rgba(239,68,68,0.05); border-radius:8px;">${this._errorMessage}</div>`;
        }
        if (this._pageState === 'empty') {
            return `<div style="grid-column: 1/-1; text-align:center; padding:40px; color:var(--muted-foreground);">No accounts found. Use 'Add Account' to get started.</div>`;
        }
        return this._accountsData.map((row, index) => {
            const statusStr = (row.emu_status || 'offline').toLowerCase();
            const statusClass = statusStr === 'online' ? 'status-online' : statusStr === 'idle' ? 'status-idle' : 'status-offline';
            const powFormatted = AccountsPage.formatPower(row.power);
            const powerPct = Math.min((parseFloat((row.power / 1000000).toFixed(1)) / 30) * 100, 100);
            const ingameName = row.lord_name || '—';
            const displayAlliance = row.alliance || '—';

            return `
            <div class="account-card ${statusClass}" onclick="AccountsPage.openDetail(${row.account_id})" style="animation: fadeIn 0.28s ease ${index * 0.05}s both;">
                <div class="card-dot"></div>
                <div class="account-info">
                    <div class="account-name">
                        ${ingameName}
                        <span class="alliance-badge">${displayAlliance !== '—' ? displayAlliance : '—'}</span>
                    </div>
                    <div class="account-emulator">${row.emu_name || (row.emu_index != null ? 'LDP-' + row.emu_index : 'No Emulator')} · ${row.game_id ? 'ID: ' + row.game_id : 'No ID'}</div>
                </div>
                <div class="account-power">
                    <div class="power-label">
                        <span class="power-value">${powFormatted} power</span>
                        <span class="power-hall">Hall ${row.hall_level || 0}</span>
                    </div>
                    <div class="power-bar"><div class="power-fill" style="width:${powerPct}%"></div></div>
                    <div class="sync-time">Synced: ${this.formatDateTime(row.last_scan_at)}</div>
                </div>
                <div class="card-actions">
                    <button class="card-btn-view" onclick="event.stopPropagation(); AccountsPage.openDetail(${row.account_id})">
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
        const appContainer = document.getElementById('page-root');
        if (appContainer) appContainer.innerHTML = this.render();
    },

    openAddForm() {
        this._selectedAccountId = null; // No selected account means "adding new"
        const panel = document.getElementById('accounts-slide-panel');
        const overlay = document.getElementById('accounts-slide-overlay');
        if (panel && overlay) {
            panel.innerHTML = this._renderAddEditForm('add');
            void panel.offsetWidth;
            panel.classList.add('active');
            overlay.classList.add('active');
        }
    },

    openEditForm(id) {
        this._selectedAccountId = id;
        const panel = document.getElementById('accounts-slide-panel');
        const overlay = document.getElementById('accounts-slide-overlay');
        if (panel && overlay) {
            panel.innerHTML = this._renderAddEditForm('edit');
            void panel.offsetWidth;
            panel.classList.add('active');
            overlay.classList.add('active');
        }
    },

    _renderAddEditForm(mode) {
        let acc = {};
        if (mode === 'edit') {
            acc = this._accountsData.find(a => a.account_id == this._selectedAccountId) || {};
        }

        const title = mode === 'add' ? 'Add New Account' : 'Edit Account';
        const isEdit = mode === 'edit';

        return `
            <div class="panel-content-wrap" style="max-width: 780px; margin: 0 auto; padding: 20px;">
                <!-- Header -->
                <div class="panel-header" style="align-items: center; border-radius: 20px;">
                    <div style="display:flex; align-items:center; gap: 14px;">
                        <div class="modal-icon" style="margin-bottom:0;">
                            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
                              <circle cx="9" cy="7" r="4"/>
                              <line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/>
                            </svg>
                        </div>
                        <div class="title-block">
                            <h2 style="font-family:'Outfit', sans-serif;">${title}</h2>
                            <p style="font-size: 12px; color: var(--muted-foreground); margin-top: 2px;">
                                ${isEdit ? 'Update system records for this instance' : 'Register a new bot account to the system'}
                            </p>
                        </div>
                    </div>
                    <button class="btn btn-ghost" onclick="AccountsPage.closeDetail()" style="padding: 9px; border-radius: 10px;" title="Close">
                        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>

                <!-- Body -->
                <div style="background: var(--card); border: 1px solid var(--border); border-radius: 20px; position:relative; overflow:hidden;">
                    <!-- Top accent line -->
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent 0%, var(--primary) 40%, var(--yellow-500) 60%, transparent 100%);"></div>

                    <form id="accounts-add-edit-form" onsubmit="event.preventDefault(); AccountsPage.saveAccount('${mode}');" style="padding: 28px 30px 0;">
                        <!-- Section: Identity -->
                        <div class="form-section">
                            <div class="section-label">Identity</div>
                            <div class="form-grid">
                                <div class="field">
                                    <label><span class="required"></span> Game ID</label>
                                    <input type="text" id="form-game-id" value="${acc.game_id || ''}" ${isEdit ? 'readonly' : ''} placeholder="e.g. 12345678"/>
                                    <div id="err-game-id" style="font-size:11px; color:var(--red-500); margin-top:4px; display:none;"></div>
                                    <span id="hint-game-id" class="hint">${isEdit ? 'Game ID cannot be changed.' : 'The unique in-game numeric player ID.'}</span>
                                </div>
                                <div class="field">
                                    <label>Emulator Index</label>
                                    <input type="number" id="form-emu-index" value="${acc.emu_index !== undefined && acc.emu_index !== null ? acc.emu_index : ''}" placeholder="Optional"/>
                                </div>
                                <div class="field">
                                    <label>In-game Lord Name</label>
                                    <input type="text" id="form-lord-name" value="${acc.lord_name || ''}" ${isEdit ? 'disabled' : ''} placeholder=""/>
                                </div>
                                <div class="field">
                                    <label>Power (M)</label>
                                    <input type="number" step="0.1" id="form-power" value="${isEdit ? (acc.power ? (acc.power / 1000000).toFixed(1) : '') : ''}" ${isEdit ? 'disabled' : ''} placeholder="e.g. 14.9"/>
                                </div>
                            </div>
                            ${isEdit ? '<p style="font-size:11px;color:var(--muted-foreground); margin-top:6px;">Identity metrics synchronize automatically via Full Scan.</p>' : ''}
                        </div>

                        <!-- Section: Login -->
                        <div class="form-section">
                            <div class="section-label">Login &amp; Access</div>
                            <div class="form-grid">
                                <div class="field">
                                    <label>Login Method</label>
                                    <select id="form-login-method" onchange="AccountsPage._checkEmailRequired()">
                                        <option value="Facebook" ${this._normalizeLoginMethod(acc.login_method) === 'Facebook' ? 'selected' : ''}>🔵 Facebook</option>
                                        <option value="Google" ${this._normalizeLoginMethod(acc.login_method) === 'Google' ? 'selected' : ''}>🟡 Google</option>
                                        <option value="Email" ${this._normalizeLoginMethod(acc.login_method) === 'Email' ? 'selected' : ''}>✉️ Email</option>
                                    </select>
                                    <div id="err-login-method" style="font-size:11px; color:var(--red-500); margin-top:4px; display:none;"></div>
                                </div>
                                <div class="field">
                                    <label>
                                        Login Email 
                                        <span id="email-asterisk" class="required" style="display:${(this._normalizeLoginMethod(acc.login_method) === 'Google' || this._normalizeLoginMethod(acc.login_method) === 'Facebook' || this._normalizeLoginMethod(acc.login_method) === 'Email') ? 'inline-block' : 'none'}; margin-left:4px;"></span>
                                    </label>
                                    <input type="email" id="form-email" value="${acc.email || ''}" placeholder="account@gmail.com"/>
                                    <div id="err-email" style="font-size:11px; color:var(--red-500); margin-top:4px; display:none;"></div>
                                </div>
                                <div class="field">
                                    <label>Provider</label>
                                    <select id="form-provider">
                                        <option value="Global" ${this._normalizeProvider(acc.provider) === 'Global' ? 'selected' : ''}>🌐 Global</option>
                                        <option value="Funtap" ${this._normalizeProvider(acc.provider) === 'Funtap' ? 'selected' : ''}>🎮 Funtap</option>
                                    </select>
                                </div>
                                <div class="field">
                                    <label>Alliance Tag</label>
                                    <input type="text" id="form-alliance" value="${acc.alliance || ''}" placeholder="e.g. [RFFO]"/>
                                </div>
                            </div>
                        </div>

                        <!-- Section: Notes -->
                        <div class="form-section" style="margin-bottom:0;">
                            <div class="section-label">Internal Notes</div>
                            <div class="form-grid full">
                                <div class="field">
                                    <textarea id="form-note" placeholder="Optional notes about this account...">${acc.note || ''}</textarea>
                                </div>
                            </div>
                        </div>

                        <!-- Footer -->
                        <div class="modal-footer">
                            <span id="form-save-feedback" style="font-size:13px; font-weight:600; color:var(--emerald-500); opacity:0; transition:opacity 0.3s; margin-right:auto;">Saved</span>
                            
                            <div id="form-save-spinner" style="display:none; align-items:center; gap:6px; font-size:13px; color:var(--muted-foreground); margin-right:auto;">
                                <span class="status-dot-on" style="background:var(--primary); box-shadow:none; animation: pulse-bg 1s infinite;"></span> Saving...
                            </div>

                            <button type="button" class="btn btn-ghost" id="form-btn-cancel" onclick="AccountsPage.closeDetail()" style="padding: 10px 22px; border-radius: 10px; font-size: 13px; font-weight: 600;">Cancel</button>
                            
                            <button type="submit" class="btn btn-primary" id="form-btn-submit" style="padding: 10px 22px; border-radius: 10px; font-size: 13px; font-weight: 600; border: none; display: flex; align-items: center; gap: 7px; background: var(--primary); color: #fff; box-shadow: 0 4px 16px rgba(var(--primary-rgb, 99, 102, 241), 0.35); transition: all 0.2s;">
                                <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                                    <polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
                                </svg>
                                Save Account
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    },

    _checkEmailRequired() {
        const method = document.getElementById('form-login-method').value;
        const reqSpan = document.getElementById('email-asterisk');
        if (reqSpan) {
            reqSpan.style.display = (method === 'Google' || method === 'Facebook' || method === 'Email') ? 'inline' : 'none';
        }
    },

    async saveAccount(mode) {
        // Reset errors
        ['game-id', 'login-method', 'email'].forEach(k => {
            const errEl = document.getElementById(`err-${k}`);
            if (errEl) errEl.style.display = 'none';
        });

        const gameIdStr = document.getElementById('form-game-id').value.trim();
        const emuIndex = document.getElementById('form-emu-index').value;
        const loginMethod = this._normalizeLoginMethod(document.getElementById('form-login-method').value);
        const email = document.getElementById('form-email').value.trim();
        const provider = this._normalizeProvider(document.getElementById('form-provider').value);
        const alliance = document.getElementById('form-alliance').value.trim();
        const note = document.getElementById('form-note').value;

        let hasError = false;

        // Validations
        if (!gameIdStr) {
            this._showInlineError('game-id', 'Game ID is required');
            hasError = true;
        } else if (!/^\d+$/.test(gameIdStr) && !gameIdStr.startsWith('LEGACY-')) {
            this._showInlineError('game-id', 'Game ID must contain only numbers');
            hasError = true;
        } else if (mode === 'add' && this._accountsData.some(a => a.game_id === gameIdStr)) {
            this._showInlineError('game-id', 'This Game ID already exists in your roster.');
            hasError = true;
        }

        if (loginMethod === 'Google' || loginMethod === 'Facebook') {
            if (!email) {
                this._showInlineError('email', `${loginMethod} login requires an email address.`);
                hasError = true;
            } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
                this._showInlineError('email', 'Invalid email format.');
                hasError = true;
            }
        }

        if (hasError) return;

        // Loading State
        const submitBtn = document.getElementById('form-btn-submit');
        const cancelBtn = document.getElementById('form-btn-cancel');
        const spinner = document.getElementById('form-save-spinner');
        submitBtn.disabled = true;
        cancelBtn.disabled = true;
        spinner.style.display = 'flex';

        let payload = {
            game_id: gameIdStr,
            emu_index: emuIndex || null,
            login_method: loginMethod,
            email: email,
            provider: provider,
            alliance: alliance,
            note: note
        };

        if (mode === 'add') {
            const lordName = document.getElementById('form-lord-name').value;
            const powerM = document.getElementById('form-power').value;
            payload.lord_name = lordName;
            payload.power = powerM ? parseFloat(powerM) * 1000000 : 0;

            try {
                const res = await fetch('/api/accounts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    document.getElementById('form-save-feedback').style.opacity = '1';
                    setTimeout(() => {
                        this.closeDetail();
                        this.fetchData();
                    }, 500);
                } else {
                    if (window.app && app.showUtilsToast) app.showUtilsToast('Add Failed: ' + data.error);
                }
            } catch (err) {
                if (window.app && app.showUtilsToast) app.showUtilsToast('Network error saving account');
            } finally {
                submitBtn.disabled = false; cancelBtn.disabled = false; spinner.style.display = 'none';
            }
        } else if (mode === 'edit') {
            try {
                const res = await fetch(`/api/accounts/${encodeURIComponent(gameIdStr)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) throw new Error(`HTTP Error ${res.status}`);

                const data = await res.json();
                if (data.status === 'ok') {
                    document.getElementById('form-save-feedback').style.opacity = '1';
                    setTimeout(() => {
                        this.fetchData().then(() => {
                            if (this._selectedAccountId) {
                                this.openDetail(this._selectedAccountId);
                            }
                        });
                    }, 500);
                } else {
                    if (window.app && app.showUtilsToast) app.showUtilsToast('Update Failed: ' + data.error);
                }
            } catch (err) {
                if (window.app && app.showUtilsToast) app.showUtilsToast('Network error saving account');
            } finally {
                submitBtn.disabled = false; cancelBtn.disabled = false; spinner.style.display = 'none';
            }
        }
    },

    _showInlineError(id, msg) {
        const el = document.getElementById(`err-${id}`);
        if (el) {
            el.textContent = msg;
            el.style.display = 'block';
        }
        const hintEl = document.getElementById(`hint-${id}`);
        if (hintEl) {
            hintEl.style.display = 'none';
        }
    },

    async deleteAccount(gameId) {
        if (!confirm('Are you sure you want to delete this account? This action cannot be undone.')) return;
        try {
            const res = await fetch(`/api/accounts/${encodeURIComponent(gameId)}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.status === 'deleted') {
                this.closeDetail();
                this.fetchData();
            } else {
                if (window.app && app.showUtilsToast) app.showUtilsToast('Delete Failed: ' + data.error);
            }
        } catch (err) {
            if (window.app && app.showUtilsToast) app.showUtilsToast('Network error deleting account');
        }
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
        const acc = this._accountsData.find(a => a.account_id == this._selectedAccountId);
        if (!acc) return '';

        const ingameName = acc.lord_name || 'No Name';
        const avatarInitial = ingameName.charAt(0).toUpperCase();
        const isOnline = (acc.emu_status || '').toLowerCase() === 'online';
        const statusColor = isOnline ? 'var(--emerald-500)' : 'var(--red-500,#ef4444)';
        const statusLabel = isOnline ? 'Online' : 'Offline';
        const emuDisplay = acc.emu_name || (acc.emu_index != null ? 'LDP-' + acc.emu_index : 'No Emulator');
        const powFormatted = AccountsPage.formatPower(acc.power);
        const accMatching = acc.lord_name ? 'Yes' : 'No';
        const accountsTotal = acc.provider ? 1 : 0;
        const displayAlliance = acc.alliance || 'No alliance';
        const syncDateLine = acc.last_scan_at ? new Date(acc.last_scan_at).toLocaleDateString() : 'Never';
        const syncTimeLine = acc.last_scan_at ? new Date(acc.last_scan_at).toLocaleTimeString() : '—';
        const gameIdDisplay = acc.game_id || 'Unknown';
        const isLegacyId = gameIdDisplay.startsWith('LEGACY-');

        // Status based on is_active
        let activeStatus, activeColor;
        if (acc.is_active === 1 && isOnline) {
            activeStatus = '🟢 Active'; activeColor = 'var(--emerald-500)';
        } else if (acc.is_active === 1) {
            activeStatus = '⚪ Idle'; activeColor = 'var(--yellow-500)';
        } else {
            activeStatus = '🔴 None'; activeColor = 'var(--red-500,#ef4444)';
        }

        return `
            <div class="panel-content-wrap">
                <!-- Panel Header -->
                <div class="panel-header">
                    <div class="header-left">
                        <div class="panel-avatar">
                            ${avatarInitial}
                        </div>
                        <div class="title-block">
                            <h2>${ingameName}</h2>
                            <div class="meta">
                                <span>
                                    <span class="slide-badge slide-badge--${isOnline ? 'online' : 'offline'}">
                                        <span class="${isOnline ? 'status-dot-on' : 'status-dot-off'}"></span>
                                        ${statusLabel}
                                    </span>
                                </span>
                                <span>
                                    ${accMatching === 'Yes'
                ? '<span class="slide-badge slide-badge--matched">✓ Matched</span>'
                : '<span class="slide-badge slide-badge--unsynced">✗ Unsynced</span>'}
                                </span>
                                <span><span style="font-family:monospace;${isLegacyId ? 'color:var(--yellow-500);' : ''}">${isLegacyId ? '⚠️ Legacy' : 'ID: ' + gameIdDisplay}</span></span>
                                <span>${emuDisplay}</span>
                            </div>
                        </div>
                    </div>
                    <div class="header-actions" style="position:relative;">
                        <button class="btn btn-ghost" onclick="AccountsPage.promptDeleteAccount('${acc.game_id}', '${ingameName.replace(/'/g, "\\'")}')" style="padding: 9px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; color: var(--red-500);" title="Delete Account">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                        </button>
                        <button class="btn btn-primary" onclick="AccountsPage.openEditForm('${acc.account_id}')" style="padding: 9px 20px; border-radius: 10px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; display: flex; align-items: center; gap: 6px; background: var(--primary); color: #fff; box-shadow: 0 4px 16px rgba(var(--primary-rgb, 99, 102, 241), 0.3); transition: all 0.2s;">
                            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                            Edit
                        </button>
                        <button class="btn btn-ghost" onclick="AccountsPage.closeDetail()" style="padding: 9px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;" title="Close">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                        </button>
                    </div>
                </div>

                <!-- Stats Row -->
                <div class="stats-row">
                    <div class="stat-card">
                        <div class="stat-label">
                            <svg width="12" height="12" fill="none" stroke="var(--primary)" stroke-width="2.5" viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                            Power
                        </div>
                        <div class="stat-value accent">${powFormatted}</div>
                        <div class="stat-sub">Combat strength index</div>
                    </div>

                    <div class="stat-card">
                        <div class="stat-label">
                            <svg width="12" height="12" fill="none" stroke="var(--yellow-500)" stroke-width="2.5" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
                            Hall Level
                        </div>
                        <div class="stat-value">${acc.hall_level || 0}</div>
                        <div class="progress-bar"><div class="progress-fill" style="width:${Math.round((acc.hall_level || 0) / 25 * 100)}%"></div></div>
                        <div class="stat-sub">${Math.round((acc.hall_level || 0) / 25 * 100)}% to max (25)</div>
                    </div>

                    <div class="stat-card">
                        <div class="stat-label">
                            <span class="sync-dot"></span>
                            Last Sync
                        </div>
                        <div class="stat-value stat-value-sync"><span class="sync-date-line">${syncDateLine}</span><span class="sync-time-line">${syncTimeLine}</span></div>
                        <div class="stat-sub">${activeStatus.substring(2)} · ${emuDisplay}</div>
                    </div>
                </div>

                <!-- Tabs -->
                <div class="panel-tabs">
                    <div class="panel-tab ${this._activeDetailTab === 'overview' ? 'active' : ''}" onclick="AccountsPage.switchTab('overview')">Overview</div>
                    <div class="panel-tab ${this._activeDetailTab === 'resources' ? 'active' : ''}" onclick="AccountsPage.switchTab('resources')">Resources</div>
                    <div class="panel-tab ${this._activeDetailTab === 'activity' ? 'active' : ''}" onclick="AccountsPage.switchTab('activity')">Activity Log</div>
                </div>

                <!-- Tab Content -->
                <div id="panel-tab-content">
                    ${this._renderActiveTab(acc)}
                </div>
            </div>
        `;
    },

    switchTab(tabId) {
        this._activeDetailTab = tabId;
        const acc = this._accountsData.find(a => a.account_id === this._selectedAccountId);
        const container = document.getElementById('panel-tab-content');
        if (container && acc) {
            container.innerHTML = this._renderActiveTab(acc);
            document.querySelectorAll('.panel-tab').forEach(el => {
                el.classList.toggle('active', el.textContent.trim().toLowerCase().startsWith(tabId.toLowerCase().split(' ')[0]));
            });
            // Auto-fetch comparison data for Resources tab
            if (tabId === 'resources' && acc.game_id) {
                this._fetchComparison(acc.game_id);
            }
        }
    },

    async _fetchComparison(gameId) {
        try {
            const res = await fetch(`/api/accounts/${encodeURIComponent(gameId)}/comparison`);
            const data = await res.json();
            if (data && data.delta) {
                this._comparisonCache[gameId] = data;
                this._updateDeltaUI(data.delta, data.previous);
                return data;
            }
        } catch (e) {
            console.warn('[Accounts] Comparison fetch failed:', e);
        }
    },

    _formatDelta(value) {
        if (!value || value === 0) return '';
        const abs = Math.abs(value);
        let formatted;
        if (abs >= 1_000_000_000) formatted = (abs / 1_000_000_000).toFixed(1) + 'B';
        else if (abs >= 1_000_000) formatted = (abs / 1_000_000).toFixed(1) + 'M';
        else if (abs >= 1_000) formatted = (abs / 1_000).toFixed(1) + 'K';
        else formatted = abs.toLocaleString();
        const isUp = value > 0;
        return `<span class="${isUp ? 'delta-up' : 'delta-down'}">${isUp ? '▲' : '▼'} ${isUp ? '+' : '-'}${formatted}</span>`;
    },

    _updateDeltaUI(delta, previous) {
        const prevTime = previous ? new Date(previous.created_at).toLocaleDateString() : '';
        // Update resource deltas
        ['gold', 'wood', 'ore', 'mana'].forEach(key => {
            const el = document.getElementById(`res-delta-${key}`);
            if (el) el.innerHTML = this._formatDelta(delta[key]);
        });
        // Update pet token delta
        const petEl = document.getElementById('res-delta-pet_token');
        if (petEl) petEl.innerHTML = this._formatDelta(delta.pet_token);
        // Update mana delta
        const manaEl = document.getElementById('res-delta-mana');
        if (manaEl) manaEl.innerHTML = this._formatDelta(delta.mana);
        // Update comparison timestamp
        const tsEl = document.getElementById('comparison-timestamp');
        if (tsEl && prevTime) tsEl.textContent = `vs ${prevTime}`;
    },

    _renderActiveTab(acc) {
        const loginMethod = this._normalizeLoginMethod(acc.login_method || 'Email');
        const displayEmail = acc.email || '—';
        const displayAlliance = acc.alliance || '—';
        const hallLvl = acc.hall_level || 0;
        const marketLvl = acc.market_level || 0;
        const accMatching = acc.lord_name ? 'Yes' : 'No';
        const accountsTotal = acc.provider ? 1 : 0;

        /* ───── OVERVIEW ───── */
        if (this._activeDetailTab === 'overview') {
            const loginDotClass = loginMethod === 'Google' ? 'method-dot-google' : loginMethod === 'Facebook' ? 'method-dot-facebook' : 'method-dot-apple';
            const hallPct = Math.round(hallLvl / 25 * 100);
            const mktPct = Math.round(marketLvl / 25 * 100);
            const emuDisplay = acc.emu_name || (acc.emu_index != null ? 'LDP-' + acc.emu_index : 'No Emulator');
            const isOnline = (acc.emu_status || '').toLowerCase() === 'online';

            return `
                <div class="info-grid">
                    <!-- Column 1: Login + Emulator -->
                    <div class="info-card">
                        <div class="section-title">Login &amp; Access</div>
                        <div class="info-row">
                            <span class="info-key">Method</span>
                            <span class="info-val">
                                <span class="${loginDotClass}"></span>
                                ${loginMethod}
                            </span>
                        </div>
                        <div class="info-row">
                            <span class="info-key">Email</span>
                            <span class="info-val" style="font-size:12px; color: var(--muted-foreground)">${displayEmail}</span>
                        </div>

                        <div class="section-title" style="margin-top:24px">Emulator Info</div>
                        <div class="info-row">
                            <span class="info-key">Instance</span>
                            <span class="info-val">
                                ${emuDisplay}
                                <span class="${isOnline ? 'status-dot-on' : 'status-dot-off'}" style="margin-left:2px"></span>
                            </span>
                        </div>
                        <div class="info-row">
                            <span class="info-key">Provider</span>
                            <span class="info-val"><span class="provider-tag">${this._normalizeProvider(acc.provider)}</span></span>
                        </div>
                    </div>

                    <!-- Column 2: Game Status -->
                    <div class="info-card">
                        <div class="section-title">Game Status</div>
                        <div class="info-row">
                            <span class="info-key">Alliance</span>
                            <span class="info-val"><span class="alliance-tag">${displayAlliance}</span></span>
                        </div>
                        <div class="info-row">
                            <span class="info-key">Hall Level</span>
                            <span class="info-val">
                                <div class="level-meter">
                                    <span class="level-num">${hallLvl}</span>
                                    <div class="meter"><div class="meter-fill" style="width:${hallPct}%"></div></div>
                                    <span class="level-max">/ 25</span>
                                </div>
                            </span>
                        </div>
                        <div class="info-row">
                            <span class="info-key">Market Level</span>
                            <span class="info-val">
                                <div class="level-meter">
                                    <span class="level-num">${marketLvl}</span>
                                    <div class="meter"><div class="meter-fill" style="width:${mktPct}%"></div></div>
                                    <span class="level-max">/ 25</span>
                                </div>
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }

        /* ───── RESOURCES ───── */
        if (this._activeDetailTab === 'resources') {
            const goldFormatted = AccountsPage.formatResource(acc.gold || 0);
            const woodFormatted = AccountsPage.formatResource(acc.wood || 0);
            const oreFormatted = AccountsPage.formatResource(acc.ore || 0);
            const manaFormatted = AccountsPage.formatResource(acc.mana || 0);
            const petToken = acc.pet_token || 0;
            // Cap = 3000M (3B) for simplicity; pct based on that
            const goldPct = Math.min(Math.round((acc.gold || 0) / 3000000000 * 100), 100);
            const woodPct = Math.min(Math.round((acc.wood || 0) / 3000000000 * 100), 100);
            const orePct = Math.min(Math.round((acc.ore || 0) / 3000000000 * 100), 100);
            const manaPct = Math.min(Math.round((acc.mana || 0) / 3000000000 * 100), 100);
            const oreIsCritical = orePct < 30;
    
            // Pre-loaded comparison data (if cached)
            const cached = this._comparisonCache[acc.game_id];
            const delta = cached ? cached.delta : null;
            const prevScan = cached ? cached.previous : null;
            const prevTimeLabel = prevScan ? new Date(prevScan.created_at).toLocaleDateString() : '';

            const mkDelta = (key) => {
                if (!delta || !delta[key] || delta[key] === 0) return '<span id="res-delta-' + key + '" class="delta-loading">—</span>';
                const v = delta[key];
                const abs = Math.abs(v);
                let fmt;
                if (abs >= 1e9) fmt = (abs / 1e9).toFixed(1) + 'B';
                else if (abs >= 1e6) fmt = (abs / 1e6).toFixed(1) + 'M';
                else if (abs >= 1e3) fmt = (abs / 1e3).toFixed(1) + 'K';
                else fmt = abs.toLocaleString();
                const up = v > 0;
                return `<span id="res-delta-${key}" class="${up ? 'delta-up' : 'delta-down'}">${up ? '▲' : '▼'} ${up ? '+' : '-'}${fmt}</span>`;
            };

            const timeAgo = acc.last_scan_at ? AccountsPage.formatDateTime(acc.last_scan_at) : 'Never';

            return `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                    <div class="ov-section-title" style="margin:0;">Resource Stockpile</div>
                    <div style="display:flex;align-items:center;gap:12px;">
                        <span id="comparison-timestamp" style="font-size:11px;color:var(--primary);font-weight:600;">${prevTimeLabel ? 'vs ' + prevTimeLabel : ''}</span>
                        <span style="font-size:11px;color:var(--muted-foreground);font-family:monospace;">Last updated: ${timeAgo}</span>
                    </div>
                </div>

                <div class="res-grid">
                    <!-- Gold -->
                    <div class="res-card">
                        <div class="res-header">
                            <span class="res-icon">🪙</span>
                            <span class="res-label gold">Gold</span>
                        </div>
                        <div class="res-value">${goldFormatted}</div>
                        <div class="res-bar"><div class="res-fill gold" style="width:${goldPct}%"></div></div>
                        <div class="res-footer">
                            <span class="res-cap">Cap max</span>
                            ${mkDelta('gold')}
                        </div>
                    </div>

                    <!-- Wood -->
                    <div class="res-card">
                        <div class="res-header">
                            <span class="res-icon">🪵</span>
                            <span class="res-label wood">Wood</span>
                        </div>
                        <div class="res-value">${woodFormatted}</div>
                        <div class="res-bar"><div class="res-fill wood" style="width:${woodPct}%"></div></div>
                        <div class="res-footer">
                            <span class="res-cap">Cap max</span>
                            ${mkDelta('wood')}
                        </div>
                    </div>

                    <!-- Ore -->
                    <div class="res-card ${oreIsCritical ? 'critical' : ''}">
                        <div class="res-header">
                            <svg class="res-icon" style="width:14px;color:${oreIsCritical ? 'var(--red-500)' : 'var(--indigo-400,#818cf8)'}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                            <span class="res-label ore" style="${oreIsCritical ? 'color:var(--red-500);' : ''}">Ore</span>
                            ${oreIsCritical ? '<span style="font-size:9px;font-weight:700;background:var(--red-500);color:#fff;padding:1px 6px;border-radius:4px;margin-left:6px;letter-spacing:0.5px;">CRITICAL</span>' : ''}
                        </div>
                        <div class="res-value ${oreIsCritical ? 'critical' : ''}">${oreFormatted}</div>
                        <div class="res-bar"><div class="res-fill ${oreIsCritical ? 'critical-fill' : 'ore'}" style="width:${orePct}%"></div></div>
                        <div class="res-footer">
                            <span class="res-cap ${oreIsCritical ? 'warn' : ''}">Cap max</span>
                            ${mkDelta('ore')}
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
                            <div class="pet-value">${(acc.pet_token || 0).toLocaleString()}</div>
                        </div>
                    </div>
                    <div class="pet-right">
                        <span class="pet-badge">Special Currency</span>
                        <span id="res-delta-pet_token" class="pet-delta">${delta && delta.pet_token ? (delta.pet_token > 0 ? '<span class="delta-up">▲ +' + delta.pet_token.toLocaleString() + '</span>' : '<span class="delta-down">▼ ' + delta.pet_token.toLocaleString() + '</span>') : '<span class="delta-loading">—</span>'}</span>
                    </div>
                </div>

                <!-- Mana -->
                <div class="pet-card" style="margin-top:16px;">
                    <div class="pet-left">
                        <div class="pet-icon">
                            <svg style="width:20px;color:#a855f7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
                        </div>
                        <div>
                            <div class="pet-label-txt">Mana</div>
                            <div class="pet-value">${manaFormatted}</div>
                        </div>
                    </div>
                    <div class="pet-right">
                        <span class="pet-badge" style="background:rgba(168,85,247,0.1);color:#a855f7;border-color:rgba(168,85,247,0.25);">Magic Resource</span>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div class="res-bar" style="width:100px;height:6px;"><div class="res-fill" style="width:${manaPct}%;background:linear-gradient(90deg,#a855f7,#c084fc);"></div></div>
                            ${mkDelta('mana')}
                        </div>
                    </div>
                </div>

                <!-- AI Insight -->
                <div class="ai-insight">
                    <div class="ai-icon">
                        <svg style="width:18px;height:18px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    </div>
                    <div>
                        <div class="ai-title">
                            ✦ Daily Summary
                        </div>
                        <div class="ai-body">
                            ${delta
                    ? `${delta.power > 0 ? '<strong>Power increased by ' + AccountsPage.formatPower(delta.power) + '</strong>. ' : delta.power < 0 ? '<strong>Power decreased by ' + AccountsPage.formatPower(Math.abs(delta.power)) + '</strong>. ' : ''}
                       ${delta.gold > 0 ? 'Gold ▲' + AccountsPage.formatResource(delta.gold) + '. ' : delta.gold < 0 ? 'Gold ▼' + AccountsPage.formatResource(Math.abs(delta.gold)) + '. ' : ''}
                       ${oreIsCritical ? '<strong>⚠ Ore is critically low (' + orePct + '%)</strong> — prioritize farming.' : 'Resources are stable.'}
                       ${prevTimeLabel ? '<br><span style="font-size:11px;color:var(--muted-foreground);">Compared with scan from ' + prevTimeLabel + '</span>' : ''}`
                    : `${oreIsCritical ? '<strong>Ore is critically low (' + orePct + '%)</strong> — prioritize farming runs.' : 'Resources look healthy.'}
                       <span style="font-size:11px;color:var(--muted-foreground);">Run at least 2 daily scans to enable change tracking.</span>`}
                        </div>
                    </div>
                </div>
            `;
        }

        /* ───── ACTIVITY LOG ───── */
        if (this._activeDetailTab === 'activity') {
            const pVal = acc.note || '';
            const tID = acc.account_id;
            return `
                <!-- Operator Notes -->
                <div style="margin-bottom:28px;">
                    <div class="act-section-title">Operator Notes</div>
                    <textarea class="act-textarea" id="act-note-${tID}" oninput="AccountsPage._handleNoteInput(${tID})">${pVal}</textarea>
                    <div class="act-save-row">
                        <span class="act-save-feedback" id="act-save-fb-${tID}">✓ Saved</span>
                        <button class="act-save-btn" id="act-save-btn-${tID}" onclick="AccountsPage._saveNote(${tID})">Save Note</button>
                    </div>
                </div>

                <!-- Timeline -->
                <div>
                    <div class="act-section-title" style="margin-bottom:16px;">Recent History</div>
                    <div class="timeline">
                        <div style="text-align:center; padding: 20px; font-size:13px; color:var(--muted-foreground); border:1px dashed var(--border); border-radius:6px;">
                            Activity history will appear here after sync operations.
                        </div>
                    </div>
                </div>
            `;
        }
        return '';
    },

    _noteOriginals: {},

    _handleNoteInput(id) {
        const ta = document.getElementById(`act-note-${id}`);
        const btn = document.getElementById(`act-save-btn-${id}`);
        if (!ta || !btn) return;
        if (!(id in this._noteOriginals)) {
            const acc = this._accountsData.find(a => a.account_id === id);
            this._noteOriginals[id] = acc ? (acc.note || '') : '';
        }
        const changed = ta.value !== this._noteOriginals[id];
        btn.classList.toggle('enabled', changed);
    },

    async _saveNote(id) {
        const ta = document.getElementById(`act-note-${id}`);
        const btn = document.getElementById(`act-save-btn-${id}`);
        const fb = document.getElementById(`act-save-fb-${id}`);
        if (!ta || !btn || !fb) return;

        const acc = this._accountsData.find(a => a.account_id === id);
        if (!acc) return;

        btn.classList.remove('enabled');
        fb.textContent = 'Saving...';
        fb.style.color = 'var(--muted-foreground)';
        fb.classList.add('show');

        try {
            const res = await fetch(`/api/accounts/${encodeURIComponent(acc.game_id)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note: ta.value })
            });
            const data = await res.json();

            if (data.status === 'ok') {
                acc.note = ta.value;
                this._noteOriginals[id] = ta.value;
                fb.textContent = 'Saved via API!';
                fb.style.color = 'var(--emerald-500)';
                setTimeout(() => fb.classList.remove('show'), 2200);
            } else {
                throw new Error(data.error || 'Failed to save');
            }
        } catch (e) {
            fb.textContent = e.message;
            fb.style.color = 'var(--red-500)';
            setTimeout(() => fb.classList.remove('show'), 3000);
            btn.classList.add('enabled');
        }
    },

    async fetchData() {
        this._pageState = 'loading';

        if (typeof router !== 'undefined' && router._currentPage === 'accounts') {
            const root = document.getElementById('page-root');
            if (root) root.innerHTML = this.render();
        }

        try {
            const [accRes, pendRes] = await Promise.all([
                fetch('/api/accounts'),
                fetch('/api/pending-accounts'),
            ]);

            if (!accRes.ok) throw new Error(`HTTP Error ${accRes.status}`);

            this._accountsData = await accRes.json();
            const pendData = await pendRes.json();
            this._pendingAccounts = Array.isArray(pendData) ? pendData : [];

            if (this._accountsData.length === 0) {
                this._pageState = 'empty';
            } else {
                this._pageState = 'ready';
                // Preload comparison deltas so table renders immediately
                const jobs = this._accountsData
                    .filter(account => account.game_id && !this._comparisonCache[account.game_id])
                    .map(account => this._fetchComparison(account.game_id));
                if (jobs.length) await Promise.allSettled(jobs);
            }
        } catch (e) {
            console.error('Failed to fetch accounts:', e);
            this._accountsData = [];
            this._pendingAccounts = [];
            this._pageState = 'error';
            this._errorMessage = e.message || 'Connection error';
        } finally {
            if (typeof router !== 'undefined' && router._currentPage === 'accounts') {
                const root = document.getElementById('page-root');
                if (root) root.innerHTML = this.render();
            }
        }
    },

    // ── Pending Queue ──

    _renderPendingBanner() {
        if (!this._pendingAccounts || this._pendingAccounts.length === 0) return '';

        const count = this._pendingAccounts.length;
        const cards = this._pendingAccounts.map(p => {
            const emuName = p.emu_name || (p.emu_index != null ? 'LDP-' + p.emu_index : 'Unknown');
            return `
            <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 18px;display:flex;align-items:center;justify-content:space-between;gap:16px;min-width:340px;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;flex-shrink:0;">?</div>
                    <div>
                        <div style="font-weight:700;font-size:14px;">${p.lord_name || 'Unknown Lord'}</div>
                        <div style="font-size:12px;color:var(--muted-foreground);font-family:monospace;">ID: ${p.game_id} &middot; ${emuName}</div>
                    </div>
                </div>
                <div style="display:flex;gap:6px;flex-shrink:0;">
                    <button class="btn btn-primary btn-sm" style="font-size:12px;padding:5px 14px;" onclick="event.stopPropagation(); AccountsPage.showConfirmForm(${p.id})">
                        ✓ Confirm
                    </button>
                    <button class="btn btn-ghost btn-sm" style="font-size:12px;padding:5px 10px;color:var(--muted-foreground);" onclick="event.stopPropagation(); AccountsPage.dismissPending(${p.id})">
                        ✗
                    </button>
                </div>
            </div>`;
        }).join('');

        return `
        <div style="background:linear-gradient(135deg,rgba(245,158,11,0.08),rgba(217,119,6,0.04));border:1px solid rgba(245,158,11,0.2);border-radius:12px;padding:16px 20px;margin-bottom:16px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <span style="font-size:18px;">📋</span>
                <span style="font-weight:700;font-size:14px;color:var(--foreground);">Pending Accounts</span>
                <span style="background:rgba(245,158,11,0.15);color:#d97706;border:1px solid rgba(245,158,11,0.3);border-radius:20px;padding:1px 10px;font-size:12px;font-weight:700;">${count}</span>
                <span style="font-size:12px;color:var(--muted-foreground);">New accounts discovered via Full Scan — confirm to add to your roster.</span>
            </div>
            <div id="pending-confirm-form-area"></div>
            <div style="display:flex;gap:10px;overflow-x:auto;padding-bottom:4px;">
                ${cards}
            </div>
        </div>`;
    },

    showConfirmForm(pendingId) {
        const p = this._pendingAccounts.find(x => x.id === pendingId);
        if (!p) return;

        const area = document.getElementById('pending-confirm-form-area');
        if (!area) return;

        area.innerHTML = `
        <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px 22px;margin-bottom:14px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
                <div style="width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,var(--primary),var(--indigo-500,#6366f1));color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;">✓</div>
                <div>
                    <div style="font-weight:700;font-size:14px;">Confirm: ${p.lord_name || 'Unknown'}</div>
                    <div style="font-size:12px;color:var(--muted-foreground);font-family:monospace;">Game ID: ${p.game_id}</div>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:14px;">
                <div>
                    <label style="display:block;font-size:11px;font-weight:700;color:var(--muted-foreground);margin-bottom:4px;">Login Method</label>
                    <select id="pq-login-method" style="width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground);font-size:13px;">
                        <option value="">-- Select --</option>
                        <option value="Facebook">Facebook</option>
                        <option value="Google">Google</option>
                        <option value="Email">Email</option>
                    </select>
                </div>
                <div>
                    <label style="display:block;font-size:11px;font-weight:700;color:var(--muted-foreground);margin-bottom:4px;">Login Email</label>
                    <input type="email" id="pq-email" placeholder="email@example.com" style="width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground);font-size:13px;" />
                </div>
                <div>
                    <label style="display:block;font-size:11px;font-weight:700;color:var(--muted-foreground);margin-bottom:4px;">Provider</label>
                    <select id="pq-provider" style="width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground);font-size:13px;">
                        <option value="Global">Global</option>
                        <option value="Funtap">Funtap</option>
                    </select>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">
                <div>
                    <label style="display:block;font-size:11px;font-weight:700;color:var(--muted-foreground);margin-bottom:4px;">Alliance Tag</label>
                    <input type="text" id="pq-alliance" placeholder="e.g. [ABC]" style="width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground);font-size:13px;" />
                </div>
                <div>
                    <label style="display:block;font-size:11px;font-weight:700;color:var(--muted-foreground);margin-bottom:4px;">Notes</label>
                    <input type="text" id="pq-note" placeholder="Optional notes..." style="width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--foreground);font-size:13px;" />
                </div>
            </div>
            <div style="display:flex;justify-content:flex-end;gap:8px;">
                <button class="btn btn-outline btn-sm" onclick="document.getElementById('pending-confirm-form-area').innerHTML=''">Cancel</button>
                <button class="btn btn-primary btn-sm" onclick="AccountsPage.confirmPending(${pendingId})">Create Account</button>
            </div>
        </div>`;
    },

    async confirmPending(pendingId) {
        const loginMethod = this._normalizeLoginMethod(document.getElementById('pq-login-method')?.value || 'Email');
        const email = document.getElementById('pq-email')?.value || '';
        const provider = this._normalizeProvider(document.getElementById('pq-provider')?.value || 'Global');
        const alliance = document.getElementById('pq-alliance')?.value || '';
        const note = document.getElementById('pq-note')?.value || '';

        const btn = event?.currentTarget;
        if (btn) {
            btn.disabled = true;
            const oldTxt = btn.textContent;
            btn.textContent = 'Creating...';
            btn.dataset.oldTxt = oldTxt;
        }

        try {
            const res = await fetch(`/api/pending-accounts/${pendingId}/confirm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ login_method: loginMethod, email, provider, alliance, note }),
            });

            if (!res.ok) throw new Error(`HTTP Error ${res.status}`);

            const data = await res.json();
            if (data.status === 'confirmed') {
                if (window.app && app.showUtilsToast) app.showUtilsToast('Account confirmed! ✓', 'success');
                this.fetchData();
            } else {
                if (window.app && app.showUtilsToast) app.showUtilsToast('Confirm failed: ' + (data.error || 'Unknown'), 'error');
            }
        } catch (e) {
            if (window.app && app.showUtilsToast) app.showUtilsToast('Network error confirming account (' + e.message + ')', 'error');
        } finally {
            if (btn && document.body.contains(btn)) {
                btn.disabled = false;
                btn.textContent = btn.dataset.oldTxt;
            }
        }
    },

    async dismissPending(pendingId) {
        if (!confirm('Dismiss this pending account? It will reappear on next scan.')) return;

        const btn = event?.currentTarget;
        if (btn) btn.disabled = true;

        try {
            const res = await fetch(`/api/pending-accounts/${pendingId}/dismiss`, { method: 'POST' });

            if (!res.ok) throw new Error(`HTTP Error ${res.status}`);

            const data = await res.json();
            if (data.status === 'dismissed') {
                this.fetchData();
            } else {
                if (window.app && app.showUtilsToast) app.showUtilsToast('Dismiss failed: ' + (data.error || 'Unknown'), 'error');
            }
        } catch (e) {
            if (window.app && app.showUtilsToast) app.showUtilsToast('Network error dismissing (' + e.message + ')', 'error');
        } finally {
            if (btn && document.body.contains(btn)) {
                btn.disabled = false;
            }
        }
    },

    init() {
        this._noteOriginals = {};
        this.fetchData();
    },
    destroy() {
        this._selectedAccountId = null;
        this._pendingAccounts = [];
        this._noteOriginals = {};
    }
};
