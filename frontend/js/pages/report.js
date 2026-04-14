const ReportPage = {
    _accounts: [],
    _groups: [],
    _chartData: { metric: 'power', bucket: 'hour', range: null, series: [] },
    _selectedGameIds: [],
    _selectedGroupId: '',
    _selectedMetric: 'power',
    _selectedRangePreset: '7d',
    _selectedBucket: 'hour',
    _customFrom: '',
    _customTo: '',
    _accountSearch: '',
    _runtimeFilter: 'all',
    _providerFilter: 'all',
    _legendHidden: {},
    _accountsExpanded: false,
    _loadingAccounts: false,
    _loadingChart: false,
    _error: '',
    _lastLoadedAt: '',
    _chartCache: null,
    _boundDocClick: null,
    _boundResize: null,
    _metricOptions: [
        ['power', 'Power'],
        ['gold', 'Gold'],
        ['wood', 'Wood'],
        ['ore', 'Ore'],
        ['mana', 'Mana'],
        ['pet_token', 'Pet Token'],
        ['hall_level', 'Hall Level'],
        ['market_level', 'Market Level'],
    ],
    _rangeOptions: [['24h', '24H'], ['7d', '7D'], ['30d', '30D'], ['custom', 'Custom']],
    _bucketOptions: [['raw', 'Raw'], ['hour', 'Hour'], ['day', 'Day']],
    _palette: ['#73BF69', '#5794F2', '#FF9830', '#F2495C', '#B877D9', '#56D2B8', '#FADE2A', '#8AB8FF'],

    _esc(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    _dt(value) {
        if (!value) return '--';
        const dt = new Date(value);
        return Number.isNaN(dt.getTime()) ? value : dt.toLocaleString();
    },

    _formatInput(value) {
        if (!value) return '';
        const dt = new Date(value);
        if (Number.isNaN(dt.getTime())) return '';
        const offset = dt.getTimezoneOffset() * 60000;
        return new Date(dt.getTime() - offset).toISOString().slice(0, 16);
    },

    _metricLabel(metric = this._selectedMetric) {
        return this._metricOptions.find(([value]) => value === metric)?.[1] || metric;
    },

    _num(value, metric = this._selectedMetric) {
        const num = Number(value || 0);
        if (!Number.isFinite(num)) return '--';
        if (['hall_level', 'market_level'].includes(metric)) return `${Math.round(num)}`;
        const abs = Math.abs(num);
        if (abs >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
        if (abs >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
        if (abs >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
        return Math.round(num).toLocaleString();
    },

    _delta(value, metric = this._selectedMetric) {
        if (value == null || !Number.isFinite(Number(value))) return '--';
        const num = Number(value);
        if (num === 0) return '0';
        return `${num > 0 ? '+' : ''}${this._num(num, metric)}`;
    },

    _normalizeProvider(value) {
        const provider = String(value || '').toLowerCase();
        if (provider === 'funtap') return 'funtap';
        return 'global';
    },

    _runtimeKey(account) {
        const emuStatus = String(account?.emu_status || '').toLowerCase();
        const hasLink = !!account?.emulator_db_id || account?.emu_index != null || !!account?.emu_name;
        if (account?.is_active === 1 && emuStatus === 'online') return 'running';
        if (account?.is_active === 1) return 'ready';
        if (hasLink) return 'linked';
        return 'unlinked';
    },

    _parseGroupAccountIds(group) {
        const raw = group?.account_ids;
        if (Array.isArray(raw)) return raw.map(Number).filter(Boolean);
        if (typeof raw === 'string' && raw.trim()) {
            try {
                const parsed = JSON.parse(raw);
                return Array.isArray(parsed) ? parsed.map(Number).filter(Boolean) : [];
            } catch {
                return [];
            }
        }
        return [];
    },

    _filteredAccounts() {
        const search = this._accountSearch.trim().toLowerCase();
        const group = (this._groups || []).find((item) => String(item.id) === String(this._selectedGroupId || ''));
        const groupAccountIds = new Set(this._parseGroupAccountIds(group));
        return (this._accounts || []).filter((account) => {
            if (this._selectedGroupId && !groupAccountIds.has(Number(account.account_id || 0))) return false;
            if (this._runtimeFilter !== 'all' && this._runtimeKey(account) !== this._runtimeFilter) return false;
            if (this._providerFilter !== 'all' && this._normalizeProvider(account.provider) !== this._providerFilter) return false;
            if (!search) return true;
            const haystack = [
                account.lord_name || '',
                account.game_id || '',
                account.emu_name || '',
                account.alliance || '',
                account.provider || '',
            ].join(' ').toLowerCase();
            return haystack.includes(search);
        });
    },

    _selectedLabel() {
        if (!this._selectedGameIds.length) return 'Choose accounts';
        if (this._selectedGameIds.length === 1) {
            const account = this._accounts.find((item) => item.game_id === this._selectedGameIds[0]);
            return account ? `${account.lord_name || 'Unknown'} (${account.game_id})` : this._selectedGameIds[0];
        }
        return `${this._selectedGameIds.length} accounts selected`;
    },

    _rangeBounds() {
        const now = new Date();
        let from = new Date(now.getTime() - 7 * 86400000);
        let to = new Date(now);
        if (this._selectedRangePreset === '24h') from = new Date(now.getTime() - 86400000);
        if (this._selectedRangePreset === '30d') from = new Date(now.getTime() - 30 * 86400000);
        if (this._selectedRangePreset === 'custom') {
            from = this._customFrom ? new Date(this._customFrom) : from;
            to = this._customTo ? new Date(this._customTo) : to;
        }
        return { from, to };
    },

    _visibleSeries() {
        return (this._chartData.series || []).filter((series) => !this._legendHidden[series.game_id]);
    },

    _tableRows() {
        const rows = [];
        (this._chartData.series || []).forEach((series) => {
            (series.points || []).forEach((point, index, source) => {
                rows.push({
                    game_id: series.game_id,
                    lord_name: series.lord_name || series.game_id,
                    emulator_name: series.emulator_name || '--',
                    timestamp: point.timestamp,
                    value: Number(point.value || 0),
                    delta: index > 0 ? Number(point.value || 0) - Number(source[index - 1].value || 0) : null,
                });
            });
        });
        return rows.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    },

    _summaryCards() {
        const visible = this._visibleSeries();
        const withLatest = visible.filter((item) => item.summary?.latest != null);
        const latestAverage = withLatest.length
            ? withLatest.reduce((sum, item) => sum + Number(item.summary.latest || 0), 0) / withLatest.length
            : null;
        const topGainer = visible
            .filter((item) => item.summary?.delta_in_range != null)
            .sort((a, b) => Number(b.summary.delta_in_range || 0) - Number(a.summary.delta_in_range || 0))[0];
        const newestSync = visible
            .map((item) => item.summary?.last_sync_at)
            .filter(Boolean)
            .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];

        return [
            ['Selected Accounts', `${this._selectedGameIds.length}`, `${visible.length} visible series`],
            [`Latest Avg ${this._metricLabel()}`, latestAverage != null ? this._num(latestAverage) : '--', withLatest.length ? `Across ${withLatest.length} accounts` : 'No datapoints'],
            ['Top Gainer', topGainer ? this._num(topGainer.summary.delta_in_range || 0) : '--', topGainer ? `${topGainer.lord_name || topGainer.game_id}` : 'No delta'],
            ['Newest Sync', newestSync ? this._dt(newestSync) : '--', this._lastLoadedAt ? `Loaded ${this._dt(this._lastLoadedAt)}` : 'Waiting for load'],
        ];
    },

    _tick(ts) {
        const dt = new Date(ts);
        return this._selectedBucket === 'day'
            ? dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
            : dt.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    },

    _buildChartCache() {
        const geom = { width: 1200, height: 360, left: 72, right: 24, top: 20, bottom: 40 };
        const innerWidth = geom.width - geom.left - geom.right;
        const innerHeight = geom.height - geom.top - geom.bottom;
        const visible = this._visibleSeries().map((series, index) => ({
            ...series,
            color: this._palette[index % this._palette.length],
        }));
        const allPoints = visible.flatMap((series) => series.points || []);
        if (!allPoints.length) {
            return { geom, series: [], xTicks: [], yTicks: [], hoverPoints: [] };
        }

        const timestamps = allPoints.map((point) => new Date(point.timestamp).getTime()).filter(Number.isFinite);
        const values = allPoints.map((point) => Number(point.value || 0));
        let minTs = Math.min(...timestamps);
        let maxTs = Math.max(...timestamps);
        let minVal = Math.min(...values);
        let maxVal = Math.max(...values);

        if (minTs === maxTs) maxTs = minTs + 1;
        if (minVal === maxVal) {
            const bump = minVal === 0 ? 1 : Math.max(1, Math.abs(minVal) * 0.1);
            minVal -= bump;
            maxVal += bump;
        }

        const sx = (timestamp) => geom.left + ((timestamp - minTs) / (maxTs - minTs)) * innerWidth;
        const sy = (value) => geom.top + ((maxVal - value) / (maxVal - minVal)) * innerHeight;

        const series = visible.map((item) => {
            const points = (item.points || []).map((point, index, source) => {
                const timestamp = new Date(point.timestamp).getTime();
                if (!Number.isFinite(timestamp)) return null;
                const value = Number(point.value || 0);
                return {
                    x: sx(timestamp),
                    y: sy(value),
                    timestamp,
                    timestampLabel: point.timestamp,
                    value,
                    color: item.color,
                    game_id: item.game_id,
                    lord_name: item.lord_name || item.game_id,
                    delta: index > 0 ? value - Number(source[index - 1].value || 0) : null,
                };
            }).filter(Boolean);

            return {
                ...item,
                pointsChart: points,
                path: points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' '),
            };
        });

        const xTicks = Array.from({ length: 5 }, (_, index) => {
            const ratio = index / 4;
            const ts = minTs + (maxTs - minTs) * ratio;
            return {
                x: geom.left + innerWidth * ratio,
                label: this._tick(ts),
            };
        });

        const yTicks = Array.from({ length: 5 }, (_, index) => {
            const ratio = index / 4;
            return {
                y: geom.top + innerHeight * ratio,
                value: maxVal - (maxVal - minVal) * ratio,
            };
        });

        return {
            geom,
            series,
            xTicks,
            yTicks,
            hoverPoints: series.flatMap((item) => item.pointsChart || []),
        };
    },

    render() {
        return `
            <style>
                .report-shell { display:flex; flex-direction:column; gap:16px; color:#dce3ec; }
                .report-shell .panel { background:#11161f; border:1px solid #202938; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,.18); }
                .report-shell .panel-header { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:14px 16px; border-bottom:1px solid #202938; }
                .report-shell .panel-title { font-size:13px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; color:#9aa7b7; }
                .report-shell .hero { background:linear-gradient(180deg, #10161f 0%, #0b1118 100%); border:1px solid #1f2a3a; border-radius:14px; }
                .report-shell .hero-head { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding:16px 18px 12px; }
                .report-shell .hero-title { font-size:24px; font-weight:800; color:#f5f7fa; margin:0 0 6px; letter-spacing:-.02em; }
                .report-shell .hero-subtitle { font-size:13px; color:#9aa7b7; margin:0; }
                .report-shell .toolbar-grid { display:grid; grid-template-columns:repeat(6, minmax(0, 1fr)); gap:12px; padding:0 18px 18px; }
                .report-shell .toolbar-grid .field:first-child { grid-column:span 2; }
                .report-shell .field { display:flex; flex-direction:column; gap:6px; min-width:0; position:relative; }
                .report-shell .field-label { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#7f8a99; }
                .report-shell .input,
                .report-shell .select,
                .report-shell .btn,
                .report-shell .chip { border:1px solid #2d3748; background:#0b1118; color:#edf2f7; border-radius:8px; min-height:38px; font:inherit; }
                .report-shell .input,
                .report-shell .select { width:100%; padding:0 12px; }
                .report-shell .btn { padding:0 14px; cursor:pointer; transition:border-color .16s ease, background .16s ease, color .16s ease; }
                .report-shell .btn:hover,
                .report-shell .chip:hover { border-color:#5794f2; background:#111b28; }
                .report-shell .btn.active,
                .report-shell .chip.active { border-color:#5794f2; background:rgba(87,148,242,.16); color:#b7d4ff; }
                .report-shell .btn.refresh { background:#1f2a3a; border-color:#30425f; font-weight:700; }
                .report-shell .btn-row { display:flex; gap:8px; flex-wrap:wrap; }
                .report-shell .account-trigger { display:flex; align-items:center; justify-content:space-between; gap:8px; padding:0 12px; cursor:pointer; }
                .report-shell .account-menu { position:absolute; inset:auto 0 auto 0; top:100%; margin-top:6px; z-index:30; background:#0f151d; border:1px solid #263242; border-radius:10px; box-shadow:0 18px 34px rgba(0,0,0,.28); padding:10px; display:flex; flex-direction:column; gap:10px; max-height:300px; overflow:auto; }
                .report-shell .account-quick { display:flex; gap:8px; flex-wrap:wrap; }
                .report-shell .chip { padding:0 12px; cursor:pointer; min-height:32px; font-size:12px; }
                .report-shell .account-option { display:flex; align-items:center; gap:10px; padding:8px 10px; border-radius:8px; cursor:pointer; }
                .report-shell .account-option:hover { background:#141d28; }
                .report-shell .account-meta { display:flex; flex-direction:column; min-width:0; }
                .report-shell .account-meta strong { font-size:13px; color:#f8fafc; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
                .report-shell .account-meta span { font-size:11px; color:#8c98a8; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
                .report-shell .custom-range { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
                .report-shell .summary-grid { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:12px; }
                .report-shell .summary-card { padding:16px; }
                .report-shell .summary-label { font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:#7f8a99; margin-bottom:10px; }
                .report-shell .summary-value { font-size:26px; font-weight:800; color:#f8fafc; letter-spacing:-.03em; }
                .report-shell .summary-note { margin-top:6px; font-size:12px; color:#8c98a8; }
                .report-shell .chart-wrap { position:relative; background:linear-gradient(180deg, rgba(18,23,32,.98) 0%, rgba(10,14,20,.98) 100%); }
                .report-shell .chart-toolbar { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:14px 16px 10px; }
                .report-shell .chart-meta h3 { margin:0; font-size:16px; color:#f8fafc; }
                .report-shell .chart-meta p { margin:4px 0 0; color:#8c98a8; font-size:12px; }
                .report-shell .legend { display:flex; gap:8px; flex-wrap:wrap; }
                .report-shell .legend-btn { display:inline-flex; align-items:center; gap:8px; min-height:32px; padding:0 10px; border-radius:999px; border:1px solid #2d3748; background:#0b1118; color:#dce3ec; cursor:pointer; font-size:12px; font-weight:600; }
                .report-shell .legend-btn.is-hidden { opacity:.45; }
                .report-shell .legend-dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
                .report-shell .chart-stage { position:relative; padding:0 10px 12px; }
                .report-shell .chart-svg { width:100%; height:auto; display:block; border:1px solid #1d2735; border-radius:10px; background:linear-gradient(180deg, rgba(87,148,242,.06), transparent 30%), linear-gradient(0deg, rgba(255,255,255,.01), rgba(255,255,255,.01)); }
                .report-shell .chart-empty { min-height:360px; display:flex; align-items:center; justify-content:center; color:#8c98a8; font-weight:600; text-align:center; padding:32px; border:1px dashed #2d3748; border-radius:10px; }
                .report-shell .tooltip { position:absolute; min-width:220px; max-width:280px; pointer-events:none; background:#0b1118; border:1px solid #2d3748; border-radius:10px; padding:12px 14px; box-shadow:0 18px 36px rgba(0,0,0,.32); color:#f8fafc; display:none; }
                .report-shell .tooltip-title { font-size:12px; color:#8c98a8; margin-bottom:4px; }
                .report-shell .tooltip-main { font-size:14px; font-weight:700; margin-bottom:6px; }
                .report-shell .tooltip-row { display:flex; align-items:center; justify-content:space-between; gap:12px; font-size:12px; margin-top:4px; }
                .report-shell .tooltip-key { color:#8c98a8; }
                .report-shell .delta-up { color:#73BF69; font-weight:700; }
                .report-shell .delta-down { color:#F2495C; font-weight:700; }
                .report-shell .delta-flat { color:#C7D0D9; font-weight:700; }
                .report-shell .table-meta { font-size:12px; color:#8c98a8; }
                .report-shell .table-wrap { overflow:auto; }
                .report-shell table { width:100%; border-collapse:collapse; }
                .report-shell th { text-align:left; padding:12px 14px; font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:#7f8a99; border-bottom:1px solid #202938; background:#0e141d; }
                .report-shell td { padding:12px 14px; border-bottom:1px solid #1a2431; font-size:13px; color:#dce3ec; }
                .report-shell tbody tr:hover td { background:#101822; }
                .report-shell .mono { font-family:var(--font-mono, Consolas, monospace); }
                .report-shell .empty-row { text-align:center; color:#8c98a8; padding:26px; }
                .report-shell .spinner { display:inline-block; width:16px; height:16px; border-radius:50%; border:2px solid rgba(87,148,242,.18); border-top-color:#5794f2; animation:report-spin .8s linear infinite; }
                .report-shell .error-banner { padding:0 18px 18px; color:#ffb4b4; font-size:13px; font-weight:600; }
                @keyframes report-spin { to { transform:rotate(360deg); } }
                @media (max-width: 1100px) {
                    .report-shell .toolbar-grid { grid-template-columns:1fr 1fr 1fr; }
                    .report-shell .toolbar-grid .field:first-child { grid-column:span 3; }
                    .report-shell .summary-grid { grid-template-columns:1fr 1fr; }
                }
                @media (max-width: 720px) {
                    .report-shell .toolbar-grid,
                    .report-shell .summary-grid,
                    .report-shell .custom-range { grid-template-columns:1fr; }
                    .report-shell .toolbar-grid .field:first-child { grid-column:span 1; }
                    .report-shell .hero-head,
                    .report-shell .chart-toolbar,
                    .report-shell .panel-header { flex-direction:column; align-items:flex-start; }
                }
                @media (prefers-reduced-motion: reduce) {
                    .report-shell .btn,
                    .report-shell .chip { transition:none; }
                    .report-shell .spinner { animation:none; }
                }
            </style>
            <div class="report-shell">
                <section class="hero">
                    <div class="hero-head">
                        <div>
                            <h1 class="hero-title">Report</h1>
                            <p class="hero-subtitle">Grafana-style observability for account growth, resources, and scan history trends.</p>
                        </div>
                        <button class="btn refresh" type="button" onclick="ReportPage.reloadChart()">Refresh Data</button>
                    </div>
                    <div class="toolbar-grid">
                        <div class="field">
                            <div class="field-label">Accounts</div>
                            <button class="account-trigger input" type="button" onclick="ReportPage.toggleAccountsExpanded()">
                                <span>${this._esc(this._selectedLabel())}</span>
                                <span>${this._accountsExpanded ? '&#9650;' : '&#9660;'}</span>
                            </button>
                            <div id="report-account-menu-anchor"></div>
                        </div>
                        <div class="field">
                            <div class="field-label">Target Group</div>
                            <select id="report-group-select" class="select"></select>
                        </div>
                        <div class="field">
                            <div class="field-label">Metric</div>
                            <select id="report-metric-select" class="select">
                                ${this._metricOptions.map(([value, label]) => `<option value="${value}" ${value === this._selectedMetric ? 'selected' : ''}>${label}</option>`).join('')}
                            </select>
                        </div>
                        <div class="field">
                            <div class="field-label">Runtime</div>
                            <select id="report-runtime-select" class="select"></select>
                        </div>
                        <div class="field">
                            <div class="field-label">Provider</div>
                            <select id="report-provider-select" class="select"></select>
                        </div>
                        <div class="field">
                            <div class="field-label">Range</div>
                            <div id="report-range-buttons" class="btn-row"></div>
                            <div id="report-custom-range-anchor"></div>
                        </div>
                        <div class="field">
                            <div class="field-label">Resolution</div>
                            <div id="report-bucket-buttons" class="btn-row"></div>
                        </div>
                    </div>
                    <div id="report-error-banner"></div>
                </section>
                <section id="report-summary-grid" class="summary-grid"></section>
                <section class="panel chart-wrap">
                    <div class="chart-toolbar">
                        <div class="chart-meta">
                            <h3>${this._esc(this._metricLabel())} Time Series</h3>
                            <p id="report-chart-subtitle">Bucket: ${this._esc(this._selectedBucket)} · Range: ${this._esc(this._selectedRangePreset.toUpperCase())}</p>
                        </div>
                        <div id="report-legend" class="legend"></div>
                    </div>
                    <div class="chart-stage">
                        <div id="report-chart-host"></div>
                        <div id="report-tooltip" class="tooltip"></div>
                    </div>
                </section>
                <section class="panel">
                    <div class="panel-header">
                        <div class="panel-title">Query Result Table</div>
                        <div id="report-table-meta" class="table-meta">0 row(s)</div>
                    </div>
                    <div class="table-wrap" id="report-table-host"></div>
                </section>
            </div>
        `;
    },

    _bindPersistentEvents() {
        const metricSelect = document.getElementById('report-metric-select');
        const groupSelect = document.getElementById('report-group-select');
        const runtimeSelect = document.getElementById('report-runtime-select');
        const providerSelect = document.getElementById('report-provider-select');
        if (metricSelect) {
            metricSelect.onchange = (event) => this.changeMetric(event.target.value);
        }
        if (groupSelect) {
            groupSelect.onchange = (event) => this.changeTargetGroup(event.target.value);
        }
        if (runtimeSelect) {
            runtimeSelect.onchange = (event) => this.changeRuntimeFilter(event.target.value);
        }
        if (providerSelect) {
            providerSelect.onchange = (event) => this.changeProviderFilter(event.target.value);
        }

        if (!this._boundDocClick) {
            this._boundDocClick = (event) => {
                if (!this._accountsExpanded) return;
                if (!event.target.closest('.field')) {
                    this._accountsExpanded = false;
                    this._renderControls();
                }
            };
            document.addEventListener('click', this._boundDocClick);
        }

        if (!this._boundResize) {
            this._boundResize = () => {
                this._hideTooltip();
                this._renderChartSection();
            };
            window.addEventListener('resize', this._boundResize);
        }
    },

    _renderControls() {
        const rangeButtons = document.getElementById('report-range-buttons');
        const bucketButtons = document.getElementById('report-bucket-buttons');
        const customRangeAnchor = document.getElementById('report-custom-range-anchor');
        const accountMenuAnchor = document.getElementById('report-account-menu-anchor');
        const errorBanner = document.getElementById('report-error-banner');
        const groupSelect = document.getElementById('report-group-select');
        const runtimeSelect = document.getElementById('report-runtime-select');
        const providerSelect = document.getElementById('report-provider-select');

        if (groupSelect) {
            groupSelect.innerHTML = `
                <option value="">All Groups</option>
                ${(this._groups || []).map((group) => `<option value="${group.id}" ${String(group.id) === String(this._selectedGroupId || '') ? 'selected' : ''}>${this._esc(group.name || `Group ${group.id}`)}</option>`).join('')}
            `;
        }

        if (runtimeSelect) {
            runtimeSelect.innerHTML = `
                <option value="all" ${this._runtimeFilter === 'all' ? 'selected' : ''}>All Runtime</option>
                <option value="running" ${this._runtimeFilter === 'running' ? 'selected' : ''}>Running</option>
                <option value="ready" ${this._runtimeFilter === 'ready' ? 'selected' : ''}>Ready</option>
                <option value="linked" ${this._runtimeFilter === 'linked' ? 'selected' : ''}>Linked</option>
                <option value="unlinked" ${this._runtimeFilter === 'unlinked' ? 'selected' : ''}>Unlinked</option>
            `;
        }

        if (providerSelect) {
            providerSelect.innerHTML = `
                <option value="all" ${this._providerFilter === 'all' ? 'selected' : ''}>All Provider</option>
                <option value="global" ${this._providerFilter === 'global' ? 'selected' : ''}>Global</option>
                <option value="funtap" ${this._providerFilter === 'funtap' ? 'selected' : ''}>Funtap</option>
            `;
        }

        if (rangeButtons) {
            rangeButtons.innerHTML = this._rangeOptions.map(([value, label]) => `
                <button type="button" class="btn ${value === this._selectedRangePreset ? 'active' : ''}" onclick="ReportPage.changeRangePreset('${value}')">${label}</button>
            `).join('');
        }

        if (bucketButtons) {
            bucketButtons.innerHTML = this._bucketOptions.map(([value, label]) => `
                <button type="button" class="btn ${value === this._selectedBucket ? 'active' : ''}" onclick="ReportPage.changeBucket('${value}')">${label}</button>
            `).join('');
        }

        if (customRangeAnchor) {
            if (this._selectedRangePreset === 'custom') {
                customRangeAnchor.innerHTML = `
                    <div class="custom-range">
                        <input class="input" type="datetime-local" value="${this._formatInput(this._customFrom)}" onchange="ReportPage.changeCustomRange('from', this.value)">
                        <input class="input" type="datetime-local" value="${this._formatInput(this._customTo)}" onchange="ReportPage.changeCustomRange('to', this.value)">
                    </div>
                `;
            } else {
                const { from, to } = this._rangeBounds();
                customRangeAnchor.innerHTML = `<div style="font-size:12px;color:#8c98a8;">${this._dt(from.toISOString())} -> ${this._dt(to.toISOString())}</div>`;
            }
        }

        if (accountMenuAnchor) {
            if (!this._accountsExpanded) {
                accountMenuAnchor.innerHTML = '';
            } else {
                const filteredAccounts = this._filteredAccounts();
                accountMenuAnchor.innerHTML = `
                    <div class="account-menu">
                        <input class="input" type="text" placeholder="Search account, game id, emulator, alliance..." value="${this._esc(this._accountSearch)}" oninput="ReportPage.changeAccountSearch(this.value)">
                        <div class="account-quick">
                            <button class="chip" type="button" onclick="ReportPage.selectVisibleAccounts()">Select visible</button>
                            <button class="chip" type="button" onclick="ReportPage.selectFirstAccounts(3)">Top 3</button>
                            <button class="chip" type="button" onclick="ReportPage.selectFirstAccounts(5)">Top 5</button>
                            <button class="chip" type="button" onclick="ReportPage.selectAllAccounts()">Select all</button>
                            <button class="chip" type="button" onclick="ReportPage.clearSelectedAccounts()">Clear</button>
                        </div>
                        <div style="font-size:11px;color:#8c98a8;">${filteredAccounts.length} account(s) match current filters</div>
                        ${filteredAccounts.map((account) => `
                            <label class="account-option">
                                <input type="checkbox" ${this._selectedGameIds.includes(account.game_id) ? 'checked' : ''} onchange="ReportPage.toggleAccount('${this._esc(account.game_id)}', this.checked)">
                                <div class="account-meta">
                                    <strong>${this._esc(account.lord_name || 'Unknown')}</strong>
                                    <span>${this._esc(account.game_id)} · ${this._esc(account.emu_name || 'Unlinked')} · ${this._esc(account.provider || 'Global')}</span>
                                </div>
                            </label>
                        `).join('') || '<div class="empty-row">No accounts match current filters.</div>'}
                    </div>
                `;
            }
        }

        if (errorBanner) {
            errorBanner.innerHTML = this._error ? `<div class="error-banner">${this._esc(this._error)}</div>` : '';
        }
    },

    _renderSummarySection() {
        const host = document.getElementById('report-summary-grid');
        if (!host) return;
        host.innerHTML = this._summaryCards().map(([label, value, note]) => `
            <div class="panel summary-card">
                <div class="summary-label">${this._esc(label)}</div>
                <div class="summary-value">${this._esc(value)}</div>
                <div class="summary-note">${this._esc(note)}</div>
            </div>
        `).join('');
    },

    _renderLegend() {
        const host = document.getElementById('report-legend');
        if (!host) return;
        const series = this._chartCache?.series || [];
        host.innerHTML = series.map((item) => `
            <button type="button" class="legend-btn ${this._legendHidden[item.game_id] ? 'is-hidden' : ''}" onclick="ReportPage.toggleLegend('${this._esc(item.game_id)}')">
                <span class="legend-dot" style="background:${item.color};"></span>
                <span>${this._esc(item.lord_name || item.game_id)}</span>
            </button>
        `).join('');
    },

    _renderChartSection() {
        const host = document.getElementById('report-chart-host');
        const subtitle = document.getElementById('report-chart-subtitle');
        if (subtitle) subtitle.textContent = `Bucket: ${this._selectedBucket} · Range: ${this._selectedRangePreset.toUpperCase()}`;
        if (!host) return;

        this._chartCache = this._buildChartCache();
        this._renderLegend();

        if (this._loadingChart) {
            host.innerHTML = `<div class="chart-empty"><div><span class="spinner"></span><div style="margin-top:10px;">Loading chart data...</div></div></div>`;
            this._hideTooltip();
            return;
        }

        if (!this._selectedGameIds.length) {
            host.innerHTML = `<div class="chart-empty">Choose one or more accounts to build the report.</div>`;
            this._hideTooltip();
            return;
        }

        if (!(this._chartCache.series || []).some((series) => (series.pointsChart || []).length)) {
            host.innerHTML = `<div class="chart-empty">No data points found for the current filter.</div>`;
            this._hideTooltip();
            return;
        }

        host.innerHTML = `
            <svg id="report-chart-svg" class="chart-svg" viewBox="0 0 ${this._chartCache.geom.width} ${this._chartCache.geom.height}" preserveAspectRatio="none">
                <rect x="0" y="0" width="${this._chartCache.geom.width}" height="${this._chartCache.geom.height}" fill="transparent"></rect>
                ${this._chartCache.yTicks.map((tick) => `
                    <g>
                        <line x1="${this._chartCache.geom.left}" y1="${tick.y}" x2="${this._chartCache.geom.width - this._chartCache.geom.right}" y2="${tick.y}" stroke="rgba(148,163,184,.18)" stroke-dasharray="4 6"></line>
                        <text x="${this._chartCache.geom.left - 12}" y="${tick.y + 4}" text-anchor="end" fill="#8c98a8" font-size="11">${this._esc(this._num(tick.value))}</text>
                    </g>
                `).join('')}
                ${this._chartCache.xTicks.map((tick) => `
                    <g>
                        <line x1="${tick.x}" y1="${this._chartCache.geom.top}" x2="${tick.x}" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="rgba(148,163,184,.08)"></line>
                        <text x="${tick.x}" y="${this._chartCache.geom.height - 14}" text-anchor="middle" fill="#8c98a8" font-size="11">${this._esc(tick.label)}</text>
                    </g>
                `).join('')}
                <line x1="${this._chartCache.geom.left}" y1="${this._chartCache.geom.height - this._chartCache.geom.bottom}" x2="${this._chartCache.geom.width - this._chartCache.geom.right}" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="rgba(148,163,184,.18)"></line>
                <line x1="${this._chartCache.geom.left}" y1="${this._chartCache.geom.top}" x2="${this._chartCache.geom.left}" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="rgba(148,163,184,.18)"></line>
                ${this._chartCache.series.map((series) => `
                    <g>
                        <path d="${series.path}" fill="none" stroke="${series.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>
                        ${series.pointsChart.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="3.5" fill="${point.color}" stroke="#0b1118" stroke-width="2"></circle>`).join('')}
                    </g>
                `).join('')}
                <line id="report-hover-line" x1="0" y1="${this._chartCache.geom.top}" x2="0" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="#5794f2" stroke-width="1.5" stroke-dasharray="5 5" opacity="0"></line>
                <circle id="report-hover-dot" cx="0" cy="0" r="6.5" fill="#5794f2" stroke="#f8fafc" stroke-width="3" opacity="0"></circle>
            </svg>
        `;

        const svg = document.getElementById('report-chart-svg');
        if (svg) {
            svg.onmousemove = (event) => this._handleChartHover(event);
            svg.onmouseleave = () => this._hideTooltip();
        }
    },

    _handleChartHover(event) {
        if (!this._chartCache?.hoverPoints?.length) return;
        const svg = event.currentTarget;
        const rect = svg.getBoundingClientRect();
        const scaleX = rect.width / this._chartCache.geom.width;
        const scaleY = rect.height / this._chartCache.geom.height;
        const x = (event.clientX - rect.left) / scaleX;
        const y = (event.clientY - rect.top) / scaleY;

        let nearest = null;
        let score = Number.POSITIVE_INFINITY;
        this._chartCache.hoverPoints.forEach((point) => {
            const nextScore = Math.abs(point.x - x) * 2 + Math.abs(point.y - y);
            if (nextScore < score) {
                score = nextScore;
                nearest = point;
            }
        });
        if (!nearest) return;

        const hoverLine = document.getElementById('report-hover-line');
        const hoverDot = document.getElementById('report-hover-dot');
        if (hoverLine) {
            hoverLine.setAttribute('x1', `${nearest.x}`);
            hoverLine.setAttribute('x2', `${nearest.x}`);
            hoverLine.setAttribute('stroke', nearest.color);
            hoverLine.setAttribute('opacity', '1');
        }
        if (hoverDot) {
            hoverDot.setAttribute('cx', `${nearest.x}`);
            hoverDot.setAttribute('cy', `${nearest.y}`);
            hoverDot.setAttribute('fill', nearest.color);
            hoverDot.setAttribute('opacity', '1');
        }

        const tooltip = document.getElementById('report-tooltip');
        if (!tooltip) return;
        const left = Math.min(Math.max((nearest.x * scaleX) + 24, 12), rect.width - 250);
        const top = Math.max((nearest.y * scaleY) - 110, 12);
        const deltaClass = nearest.delta > 0 ? 'delta-up' : nearest.delta < 0 ? 'delta-down' : 'delta-flat';
        tooltip.innerHTML = `
            <div class="tooltip-title">${this._esc(this._dt(nearest.timestampLabel))}</div>
            <div class="tooltip-main"><span class="legend-dot" style="background:${nearest.color};width:8px;height:8px;margin-right:6px;"></span>${this._esc(nearest.lord_name || nearest.game_id)}</div>
            <div class="tooltip-row"><span class="tooltip-key">${this._esc(this._metricLabel())}</span><strong>${this._esc(this._num(nearest.value))}</strong></div>
            <div class="tooltip-row"><span class="tooltip-key">Delta</span><strong class="${deltaClass}">${this._esc(this._delta(nearest.delta))}</strong></div>
            <div class="tooltip-row"><span class="tooltip-key">Game ID</span><strong>${this._esc(nearest.game_id)}</strong></div>
        `;
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
        tooltip.style.display = 'block';
    },

    _hideTooltip() {
        const tooltip = document.getElementById('report-tooltip');
        const hoverLine = document.getElementById('report-hover-line');
        const hoverDot = document.getElementById('report-hover-dot');
        if (tooltip) tooltip.style.display = 'none';
        if (hoverLine) hoverLine.setAttribute('opacity', '0');
        if (hoverDot) hoverDot.setAttribute('opacity', '0');
    },

    _renderTableSection() {
        const host = document.getElementById('report-table-host');
        const meta = document.getElementById('report-table-meta');
        if (!host || !meta) return;
        const rows = this._tableRows();
        meta.textContent = `${rows.length} row(s)`;
        host.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Account</th>
                        <th>Game ID</th>
                        <th>Emulator</th>
                        <th>${this._esc(this._metricLabel())}</th>
                        <th>Delta</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.length ? rows.map((row) => `
                        <tr>
                            <td>${this._esc(this._dt(row.timestamp))}</td>
                            <td>${this._esc(row.lord_name)}</td>
                            <td class="mono">${this._esc(row.game_id)}</td>
                            <td>${this._esc(row.emulator_name)}</td>
                            <td><strong>${this._esc(this._num(row.value))}</strong></td>
                            <td class="${row.delta > 0 ? 'delta-up' : row.delta < 0 ? 'delta-down' : 'delta-flat'}">${this._esc(this._delta(row.delta))}</td>
                        </tr>
                    `).join('') : `<tr><td class="empty-row" colspan="6">No table rows for the current filter.</td></tr>`}
                </tbody>
            </table>
        `;
    },

    _refreshUI() {
        this._renderControls();
        this._renderSummarySection();
        this._renderChartSection();
        this._renderTableSection();
    },

    async loadAccounts() {
        this._loadingAccounts = true;
        this._error = '';
        this._renderControls();
        try {
            const data = await API.getAccounts();
            this._accounts = Array.isArray(data) ? data : [];
        } catch (error) {
            this._accounts = [];
            this._error = error.message || 'Failed to load accounts';
        } finally {
            this._loadingAccounts = false;
            this._renderControls();
        }
    },

    async loadGroups() {
        try {
            const groups = await API.getGroups();
            this._groups = Array.isArray(groups) ? groups : [];
        } catch {
            this._groups = [];
        } finally {
            this._renderControls();
        }
    },

    async loadChartData() {
        if (!this._selectedGameIds.length) {
            this._chartData = { metric: this._selectedMetric, bucket: this._selectedBucket, range: null, series: [] };
            this._refreshUI();
            return;
        }

        const { from, to } = this._rangeBounds();
        if (!Number.isFinite(from.getTime()) || !Number.isFinite(to.getTime()) || from >= to) {
            this._error = 'Invalid date range';
            this._chartData = { metric: this._selectedMetric, bucket: this._selectedBucket, range: null, series: [] };
            this._refreshUI();
            return;
        }

        this._loadingChart = true;
        this._error = '';
        this._renderControls();
        this._renderChartSection();
        try {
            this._chartData = await API.getAccountTimeseries({
                gameIds: this._selectedGameIds,
                metric: this._selectedMetric,
                from: from.toISOString(),
                to: to.toISOString(),
                bucket: this._selectedBucket,
            });
            this._lastLoadedAt = new Date().toISOString();
        } catch (error) {
            this._chartData = { metric: this._selectedMetric, bucket: this._selectedBucket, range: null, series: [] };
            this._error = error.message || 'Failed to load chart data';
        } finally {
            this._loadingChart = false;
            this._refreshUI();
        }
    },

    async reloadChart() { await this.loadChartData(); },
    toggleAccountsExpanded() { this._accountsExpanded = !this._accountsExpanded; this._renderControls(); },
    changeAccountSearch(value) { this._accountSearch = value || ''; this._renderControls(); },
    changeTargetGroup(groupId) { this._selectedGroupId = groupId || ''; this._accountSearch = ''; this._renderControls(); },
    changeRuntimeFilter(value) { this._runtimeFilter = value || 'all'; this._renderControls(); },
    changeProviderFilter(value) { this._providerFilter = value || 'all'; this._renderControls(); },
    toggleAccount(gameId, checked) {
        if (checked) {
            if (!this._selectedGameIds.includes(gameId)) this._selectedGameIds.push(gameId);
        } else {
            this._selectedGameIds = this._selectedGameIds.filter((value) => value !== gameId);
            delete this._legendHidden[gameId];
        }
        this._renderControls();
        this.loadChartData();
    },
    selectFirstAccounts(count) {
        this._selectedGameIds = this._accounts.slice(0, count).map((item) => item.game_id);
        this._legendHidden = {};
        this._renderControls();
        this.loadChartData();
    },
    selectVisibleAccounts() {
        this._selectedGameIds = this._filteredAccounts().map((item) => item.game_id);
        this._legendHidden = {};
        this._renderControls();
        this.loadChartData();
    },
    selectAllAccounts() {
        this._selectedGameIds = this._accounts.map((item) => item.game_id);
        this._legendHidden = {};
        this._renderControls();
        this.loadChartData();
    },
    clearSelectedAccounts() {
        this._selectedGameIds = [];
        this._legendHidden = {};
        this._refreshUI();
    },
    changeMetric(metric) { this._selectedMetric = metric; this.loadChartData(); },
    changeRangePreset(preset) {
        this._selectedRangePreset = preset;
        if (preset === 'custom' && !this._customFrom && !this._customTo) {
            const now = new Date();
            this._customTo = now.toISOString();
            this._customFrom = new Date(now.getTime() - 7 * 86400000).toISOString();
        }
        this._renderControls();
        if (preset !== 'custom') this.loadChartData();
    },
    changeCustomRange(side, value) {
        if (!value) return;
        const iso = new Date(value).toISOString();
        if (side === 'from') this._customFrom = iso;
        if (side === 'to') this._customTo = iso;
        this.loadChartData();
    },
    changeBucket(bucket) { this._selectedBucket = bucket; this.loadChartData(); },
    toggleLegend(gameId) {
        this._legendHidden[gameId] = !this._legendHidden[gameId];
        this._hideTooltip();
        this._refreshUI();
    },

    async init() {
        this._bindPersistentEvents();
        this._refreshUI();
        await this.loadAccounts();
        await this.loadGroups();
    },

    destroy() {
        this._hideTooltip();
        if (this._boundDocClick) document.removeEventListener('click', this._boundDocClick);
        if (this._boundResize) window.removeEventListener('resize', this._boundResize);
        this._boundDocClick = null;
        this._boundResize = null;
        this._accountsExpanded = false;
    },
};
