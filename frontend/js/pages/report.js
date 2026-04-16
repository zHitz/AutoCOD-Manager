const ReportPage = {
    _storageKey: 'cod_report_preferences_v2',
    _accounts: [],
    _groups: [],
    _chartData: { metric: 'power', bucket: 'hour', aggregation: 'last', range: null, series: [], meta: {} },
    _eventsData: { items: [] },
    _farmingData: [],
    _activeTab: 'growth',
    _selectedGameIds: [],
    _selectedGroupId: '',
    _selectedMetric: 'power',
    _selectedRangePreset: '7d',
    _selectedBucket: 'hour',
    _selectedAggregation: 'last',
    _customFrom: '',
    _customTo: '',
    _accountSearch: '',
    _runtimeFilter: 'all',
    _providerFilter: 'all',
    _timezoneMode: 'local',
    _targetGrowthPct: '',
    _targetDueAt: '',
    _legendHidden: {},
    _accountsExpanded: false,
    _loadingAccounts: false,
    _loadingChart: false,
    _savingTarget: false,
    _error: '',
    _lastLoadedAt: '',
    _chartCache: null,
    _sortField: 'risk_level',
    _sortDirection: 'desc',
    _boundDocClick: null,
    _boundResize: null,
    _loadRequestId: 0,
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
    _aggregationOptions: [['last', 'Last'], ['avg', 'Avg'], ['min', 'Min'], ['max', 'Max'], ['sum', 'Sum'], ['delta', 'Delta']],
    _palette: ['#2f855a', '#3182ce', '#dd6b20', '#d53f8c', '#805ad5', '#0f766e', '#b7791f', '#4a5568'],

    _esc(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    _loadPreferences() {
        try {
            const raw = localStorage.getItem(this._storageKey);
            if (!raw) return;
            const saved = JSON.parse(raw);
            if (!saved || typeof saved !== 'object') return;
            this._selectedGameIds = Array.isArray(saved.selectedGameIds) ? saved.selectedGameIds.map(String) : [];
            this._selectedGroupId = String(saved.selectedGroupId || '');
            this._selectedMetric = String(saved.selectedMetric || this._selectedMetric);
            this._selectedRangePreset = String(saved.selectedRangePreset || this._selectedRangePreset);
            this._selectedBucket = String(saved.selectedBucket || this._selectedBucket);
            this._selectedAggregation = String(saved.selectedAggregation || this._selectedAggregation);
            this._customFrom = String(saved.customFrom || '');
            this._customTo = String(saved.customTo || '');
            this._runtimeFilter = String(saved.runtimeFilter || this._runtimeFilter);
            this._providerFilter = String(saved.providerFilter || this._providerFilter);
            this._timezoneMode = String(saved.timezoneMode || this._timezoneMode);
            this._targetGrowthPct = saved.targetGrowthPct != null ? String(saved.targetGrowthPct) : '';
            this._targetDueAt = String(saved.targetDueAt || '');
        } catch (_) { }
    },

    _persistPreferences() {
        try {
            localStorage.setItem(this._storageKey, JSON.stringify({
                selectedGameIds: this._selectedGameIds,
                selectedGroupId: this._selectedGroupId,
                selectedMetric: this._selectedMetric,
                selectedRangePreset: this._selectedRangePreset,
                selectedBucket: this._selectedBucket,
                selectedAggregation: this._selectedAggregation,
                customFrom: this._customFrom,
                customTo: this._customTo,
                runtimeFilter: this._runtimeFilter,
                providerFilter: this._providerFilter,
                timezoneMode: this._timezoneMode,
                targetGrowthPct: this._targetGrowthPct,
                targetDueAt: this._targetDueAt,
            }));
        } catch (_) { }
    },

    _dt(value, { mode = this._timezoneMode } = {}) {
        if (!value) return '--';
        const dt = new Date(value);
        if (Number.isNaN(dt.getTime())) return value;
        const opts = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        if (mode === 'utc') opts.timeZone = 'UTC';
        const rendered = dt.toLocaleString(undefined, opts);
        return mode === 'utc' ? `${rendered} UTC` : rendered;
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
        const num = Number(value);
        if (!Number.isFinite(num)) return '--';
        if (this._selectedAggregation === 'delta' || ['hall_level', 'market_level'].includes(metric)) return `${Math.round(num).toLocaleString()}`;
        const abs = Math.abs(num);
        if (abs >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
        if (abs >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
        if (abs >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
        return Math.round(num).toLocaleString();
    },

    _pct(value) {
        const num = Number(value);
        if (!Number.isFinite(num)) return '--';
        return `${num >= 0 ? '+' : ''}${num.toFixed(1)}%`;
    },

    _delta(value, metric = this._selectedMetric) {
        const num = Number(value);
        if (!Number.isFinite(num)) return '--';
        return `${num >= 0 ? '+' : ''}${this._num(num, metric)}`;
    },

    _hours(value) {
        const num = Number(value);
        if (!Number.isFinite(num)) return '--';
        if (num < 3600) return `${Math.round(num / 60)}m`;
        if (num < 86400) return `${(num / 3600).toFixed(1)}h`;
        return `${(num / 86400).toFixed(1)}d`;
    },

    _normalizeProvider(value) {
        return String(value || '').toLowerCase() === 'funtap' ? 'funtap' : 'global';
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
            } catch (_) {
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
            if (this._selectedGroupId && !groupAccountIds.has(Number(account.account_id || 0)) && !groupAccountIds.has(String(account.account_id || ''))) return false;
            if (this._runtimeFilter !== 'all' && this._runtimeKey(account) !== this._runtimeFilter) return false;
            if (this._providerFilter !== 'all' && this._normalizeProvider(account.provider) !== this._providerFilter) return false;
            if (!search) return true;
            const haystack = [account.lord_name || '', account.game_id || '', account.emu_name || '', account.alliance || '', account.provider || ''].join(' ').toLowerCase();
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

    _currentTargetMeta() {
        return this._chartData?.meta?.target || {};
    },

    _normalizeScopeId(value) {
        const num = Number(value);
        return Number.isInteger(num) && num > 0 ? num : null;
    },

    _effectiveScope() {
        if (this._selectedGameIds.length === 1) {
            const account = this._accounts.find((item) => item.game_id === this._selectedGameIds[0]);
            const accountId = this._normalizeScopeId(account?.account_id);
            if (accountId) return { scopeType: 'account', scopeId: accountId };
        }
        const groupId = this._normalizeScopeId(this._selectedGroupId);
        if (groupId) return { scopeType: 'group', scopeId: groupId };
        return { scopeType: '', scopeId: '' };
    },

    _scopeLabel() {
        const scope = this._effectiveScope();
        if (scope.scopeType === 'account') {
            const account = this._accounts.find((item) => item.game_id === this._selectedGameIds[0]);
            return account ? `${account.lord_name || 'Unknown'} (${account.game_id})` : 'Selected account';
        }
        if (scope.scopeType === 'group') {
            const group = (this._groups || []).find((item) => String(item.id) === String(scope.scopeId));
            return group ? `Group: ${group.name}` : `Group ${scope.scopeId}`;
        }
        return 'Temporary target';
    },

    _normalizeLegendState() {
        const validIds = new Set((this._chartData.series || []).map((item) => item.game_id));
        Object.keys(this._legendHidden).forEach((gameId) => {
            if (!validIds.has(gameId)) delete this._legendHidden[gameId];
        });
        if (this._selectedGameIds.length === 1) delete this._legendHidden[this._selectedGameIds[0]];
        const visibleCount = (this._chartData.series || []).filter((item) => !this._legendHidden[item.game_id]).length;
        if ((this._chartData.series || []).length && visibleCount === 0) this._legendHidden = {};
    },

    _summaryRows() {
        return (this._chartData.series || []).map((series) => {
            const derived = series.derived_summary || {};
            return {
                game_id: series.game_id,
                lord_name: series.lord_name || series.game_id,
                latest: Number(series.summary?.latest),
                growth_pct_in_range: Number(derived.growth_pct_in_range),
                growth_rate_per_day: Number(derived.growth_rate_per_day),
                data_freshness_seconds: Number(derived.data_freshness_seconds),
                data_completeness_ratio: Number(derived.data_completeness_ratio),
                risk_level: String(derived.risk_level || 'healthy'),
                quality_flags: Array.isArray(series.quality_flags) ? series.quality_flags : [],
                target_gap_pct: Number(derived.gap_to_target_pct),
                eta_to_target: Number(derived.eta_to_target),
            };
        });
    },

    _sortValue(row, field) {
        if (field === 'risk_level') return ({ high: 3, medium: 2, healthy: 1 })[row.risk_level] || 0;
        if (field === 'quality_flags') return (row.quality_flags || []).length;
        return row[field];
    },

    _sortedSummaryRows() {
        const rows = this._summaryRows();
        const dir = this._sortDirection === 'desc' ? -1 : 1;
        return rows.sort((a, b) => {
            const av = this._sortValue(a, this._sortField);
            const bv = this._sortValue(b, this._sortField);
            if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
            return String(av || '').localeCompare(String(bv || '')) * dir;
        });
    },

    _sortIndicator(field) {
        if (this._sortField !== field) return '<span style="opacity:.35; margin-left:6px;">↕</span>';
        return this._sortDirection === 'asc' ? '<span style="margin-left:6px;">↑</span>' : '<span style="margin-left:6px;">↓</span>';
    },

    _summaryCards() {
        const visible = this._visibleSeries();
        const derived = visible.map((item) => item.derived_summary || {});
        const growthValues = derived.map((item) => Number(item.growth_pct_in_range)).filter(Number.isFinite).sort((a, b) => a - b);
        const medianGrowth = growthValues.length ? growthValues[Math.floor(growthValues.length / 2)] : null;
        const topGainer = visible.slice().sort((a, b) => Number(b.derived_summary?.growth_pct_in_range || -Infinity) - Number(a.derived_summary?.growth_pct_in_range || -Infinity))[0];
        const atRiskCount = visible.filter((item) => ['high', 'medium'].includes(item.derived_summary?.risk_level)).length;
        const targetRows = visible.filter((item) => item.derived_summary?.target_progress_pct != null);
        const avgTargetProgress = targetRows.length ? targetRows.reduce((sum, item) => sum + Number(item.derived_summary?.target_progress_pct || 0), 0) / targetRows.length : null;
        const freshRows = visible.filter((item) => Number(item.derived_summary?.data_freshness_seconds || Infinity) <= 24 * 3600);
        return [
            ['Median Growth %', medianGrowth != null ? this._pct(medianGrowth) : '--', growthValues.length ? `${growthValues.length} account(s)` : 'No datapoints'],
            ['Top Gainer', topGainer ? this._pct(topGainer.derived_summary?.growth_pct_in_range) : '--', topGainer ? `${topGainer.lord_name || topGainer.game_id}` : 'No signal'],
            ['At Risk Accounts', `${atRiskCount}`, visible.length ? `${Math.round((atRiskCount / visible.length) * 100)}% of visible series` : 'No visible series'],
            ['Target Progress', avgTargetProgress != null ? `${Math.round(avgTargetProgress)}%` : '--', targetRows.length ? `${targetRows.length} targeted series` : 'No target active'],
            ['Freshness Health', visible.length ? `${freshRows.length}/${visible.length}` : '--', this._lastLoadedAt ? `Loaded ${this._dt(this._lastLoadedAt)}` : 'Waiting for load'],
        ];
    },

    _riskBadge(level) {
        const map = {
            critical: '<span class="risk-badge risk-high">Critical</span>',
            high: '<span class="risk-badge risk-high">High</span>',
            medium: '<span class="risk-badge risk-medium">Medium</span>',
            healthy: '<span class="risk-badge risk-healthy">Healthy</span>',
        };
        return map[level] || map.healthy;
    },

    _qualityBadge(flag) {
        const labels = { stale_data: 'Stale', data_gap: 'Gap', low_coverage: 'Low Cov', outlier_jump: 'Outlier', missing_scan_coverage: 'Missing Scans', stale_or_inactive_collection: 'Stale Collection', operational_issue: 'Ops Issue', possible_outlier: 'Possible Outlier' };
        return `<span class="quality-pill">${this._esc(labels[flag] || flag)}</span>`;
    },

    _buildChartCache() {
        const geom = { width: 1200, height: 360, left: 72, right: 24, top: 32, bottom: 40 };
        const innerWidth = geom.width - geom.left - geom.right;
        const innerHeight = geom.height - geom.top - geom.bottom;
        const visible = this._visibleSeries().map((series, index) => ({ ...series, color: this._palette[index % this._palette.length] }));
        const allPoints = visible.flatMap((series) => series.points || []);
        if (!allPoints.length) return { geom, series: [], xTicks: [], yTicks: [], hoverPoints: [], eventMarkers: [] };

        const timestamps = allPoints.map((point) => new Date(point.timestamp).getTime()).filter(Number.isFinite);
        const values = allPoints.map((point) => Number(point.value || 0)).filter(Number.isFinite);
        let minTs = Math.min(...timestamps);
        let maxTs = Math.max(...timestamps);
        let minVal = Math.min(...values);
        let maxVal = Math.max(...values);
        if (minTs === maxTs) maxTs = minTs + 1;
        if (minVal === maxVal) {
            const bump = Math.max(1, Math.abs(minVal) * 0.1, Math.abs(maxVal) * 0.1);
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
            return { x: geom.left + innerWidth * ratio, label: this._dt(minTs + (maxTs - minTs) * ratio, { mode: this._timezoneMode }) };
        });
        const yTicks = Array.from({ length: 5 }, (_, index) => {
            const ratio = index / 4;
            return { y: geom.top + innerHeight * ratio, value: maxVal - (maxVal - minVal) * ratio };
        });

        const eventMarkers = [];
        (this._eventsData.items || []).forEach((item) => {
            if (!series.find((entry) => entry.game_id === item.game_id)) return;
            (item.events || []).slice(-20).forEach((event) => {
                const timestamp = new Date(event.timestamp).getTime();
                if (!Number.isFinite(timestamp)) return;
                eventMarkers.push({
                    x: sx(timestamp),
                    color: event.status === 'FAILED' ? '#e53e3e' : '#2f855a',
                });
            });
        });
        return { geom, series, xTicks, yTicks, eventMarkers, hoverPoints: series.flatMap((item) => item.pointsChart || []) };
    },

    render() {
        return `
            <style>
                /* FORCE FIX FOR CACHING: Selects in hero must be light background for native options */
                .report-shell .hero .select {
                    border: 1px solid hsl(214, 32%, 91%) !important;
                    background: white !important;
                    color: #1e293b !important;
                    border-radius: 8px !important;
                }
                .report-shell .hero .select option {
                    color: #1e293b !important;
                    background: white !important;
                }
                .report-shell .hero .account-menu, .report-shell .hero .account-menu * {
                    color: var(--foreground) !important;
                }
                .report-shell .hero .account-menu .input {
                    background: white !important;
                    color: #1e293b !important;
                    border: 1px solid var(--input) !important;
                }
            </style>
            <div class="report-shell">
                <section class="panel hero">
                    <div class="hero-head">
                        <div><h1 class="hero-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>Growth Command Center</h1><p class="hero-subtitle">Track growth velocity, target progress, data quality, and operational signals for every account from one screen.</p></div>
                        <div class="button-row">
                            <button class="btn" type="button" onclick="ReportPage.reloadChart()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>Refresh</button>
                            <button class="btn" type="button" onclick="ReportPage.exportCsv()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>Export CSV</button>
                            <button class="btn" type="button" onclick="ReportPage.saveTarget()" ${this._savingTarget ? 'disabled' : ''}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>${this._savingTarget ? 'Saving...' : 'Save Target'}</button>
                            <button class="btn" type="button" onclick="ReportPage.clearSavedTarget()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>Clear Target</button>
                        </div>
                    </div>
                    <div class="toolbar-grid">
                        <div class="field span-4"><div class="field-label">Accounts</div><button class="account-trigger input" type="button" onclick="ReportPage.toggleAccountsExpanded()"><span>${this._esc(this._selectedLabel())}</span><span>${this._accountsExpanded ? '&#9650;' : '&#9660;'}</span></button><div id="report-account-menu-anchor"></div></div>
                        <div class="field span-2"><div class="field-label">Target Group</div><select id="report-group-select" class="select" style="background: white; color: #1e293b;"></select></div>
                        <div class="field span-2"><div class="field-label">Metric</div><select id="report-metric-select" class="select" style="background: white; color: #1e293b;">${this._metricOptions.map(([value, label]) => `<option value="${value}" ${value === this._selectedMetric ? 'selected' : ''}>${label}</option>`).join('')}</select></div>
                        <div class="field span-2"><div class="field-label">Runtime</div><select id="report-runtime-select" class="select" style="background: white; color: #1e293b;"></select></div>
                        <div class="field span-2"><div class="field-label">Provider</div><select id="report-provider-select" class="select" style="background: white; color: #1e293b;"></select></div>
                        <div class="field span-3"><div class="field-label">Range</div><div id="report-range-buttons" class="button-row"></div><div id="report-custom-range-anchor"></div></div>
                        <div class="field span-2"><div class="field-label">Bucket</div><div id="report-bucket-buttons" class="button-row"></div></div>
                        <div class="field span-3"><div class="field-label">Aggregation</div><div id="report-aggregation-buttons" class="button-row"></div></div>
                        <div class="field span-2"><div class="field-label">Timezone</div><div id="report-timezone-buttons" class="button-row"></div></div>
                        <div class="field span-2"><div class="field-label">Target Growth %</div><input id="report-target-growth" class="input" type="number" placeholder="e.g. 18" value="${this._esc(this._targetGrowthPct)}"></div>
                        <div class="field span-2"><div class="field-label">Target Due Date</div><input id="report-target-due" class="input" type="datetime-local" value="${this._formatInput(this._targetDueAt)}"></div>
                        <div class="field span-3"><div class="field-label">Target Context</div><div id="report-target-context" class="status-pill">Loading...</div></div>
                    </div>
                    <div id="report-error-banner"></div>
                </section>
                
                <div class="report-tabs">
                    <button class="tab-btn active" id="tab-btn-growth" onclick="ReportPage.switchTab('growth')">Growth Analytics</button>
                    <button class="tab-btn" id="tab-btn-farming" onclick="ReportPage.switchTab('farming')">Farming Efficiency</button>
                </div>

                <div id="tab-growth">
                    <section id="report-summary-grid" class="summary-grid"></section>
                    <section class="panel"><div class="panel-header"><div class="panel-heading"><div id="report-chart-title" class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>${this._esc(this._metricLabel())} Time Series</div><div id="report-chart-subtitle" class="panel-subtitle"></div></div><div id="report-legend" class="legend"></div></div><div class="chart-stage"><div id="report-chart-host"></div><div id="report-tooltip" class="tooltip"></div></div></section>
                    <section class="insight-grid">
                        <section class="panel"><div class="panel-header"><div class="panel-heading"><div class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>At Risk Feed</div><div class="panel-subtitle">Rule-based explanations from growth, coverage, freshness, and recent execution history.</div></div></div><div id="report-risk-feed" class="risk-feed"></div></section>
                        <section class="panel"><div class="panel-header"><div class="panel-heading"><div class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>Account Drilldown</div><div class="panel-subtitle">Single-account detail for target tracking and explainability.</div></div></div><div id="report-drilldown-host"></div></section>
                    </section>
                    <section class="panel"><div class="panel-header"><div class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>Analyst Table</div><div id="report-table-meta" style="font-size:12px;color:var(--muted-foreground);">0 row(s)</div></div><div class="table-wrap" id="report-table-host"></div></section>
                </div>
                
                <div id="tab-farming" style="display: none;">
                    <section id="farming-summary-grid" class="summary-grid"></section>
                    <section class="insight-grid" style="grid-template-columns: 1fr 1fr;">
                        <section class="panel"><div class="panel-header"><div class="panel-heading"><div class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>Top Farmers</div><div class="panel-subtitle">Accounts with the highest gathering frequency.</div></div></div><div id="farming-leaderboard"></div></section>
                        <section class="panel"><div class="panel-header"><div class="panel-heading"><div class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>Lazy Accounts</div><div class="panel-subtitle">Accounts with zero or old gathering activity.</div></div></div><div id="farming-lazy-board"></div></section>
                    </section>
                    <section class="panel"><div class="panel-header"><div class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>Farming Breakdown</div><div id="farming-table-meta" style="font-size:12px;color:var(--muted-foreground);">0 row(s)</div></div><div class="table-wrap" id="farming-table-host"></div></section>
                </div>
            </div>
        `;
    },

    _bindPersistentEvents() {
        const metricSelect = document.getElementById('report-metric-select');
        const groupSelect = document.getElementById('report-group-select');
        const runtimeSelect = document.getElementById('report-runtime-select');
        const providerSelect = document.getElementById('report-provider-select');
        const targetGrowth = document.getElementById('report-target-growth');
        const targetDue = document.getElementById('report-target-due');
        if (metricSelect) metricSelect.onchange = (event) => this.changeMetric(event.target.value);
        if (groupSelect) groupSelect.onchange = (event) => this.changeTargetGroup(event.target.value);
        if (runtimeSelect) runtimeSelect.onchange = (event) => this.changeRuntimeFilter(event.target.value);
        if (providerSelect) providerSelect.onchange = (event) => this.changeProviderFilter(event.target.value);
        if (targetGrowth) targetGrowth.onchange = (event) => this.changeTargetGrowth(event.target.value);
        if (targetDue) targetDue.onchange = (event) => this.changeTargetDue(event.target.value);

        if (!this._boundDocClick) {
            this._boundDocClick = (event) => {
                if (!this._accountsExpanded) return;
                if (event.target.closest('.account-trigger') || event.target.closest('.account-menu')) return;
                this._accountsExpanded = false;
                this._renderControls();
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
        const aggregationButtons = document.getElementById('report-aggregation-buttons');
        const timezoneButtons = document.getElementById('report-timezone-buttons');
        const customRangeAnchor = document.getElementById('report-custom-range-anchor');
        const accountMenuAnchor = document.getElementById('report-account-menu-anchor');
        const errorBanner = document.getElementById('report-error-banner');
        const groupSelect = document.getElementById('report-group-select');
        const runtimeSelect = document.getElementById('report-runtime-select');
        const providerSelect = document.getElementById('report-provider-select');
        const targetContext = document.getElementById('report-target-context');
        const targetMeta = this._currentTargetMeta();

        if (groupSelect) groupSelect.innerHTML = `<option value="">All Groups</option>${(this._groups || []).map((group) => `<option value="${group.id}" ${String(group.id) === String(this._selectedGroupId || '') ? 'selected' : ''}>${this._esc(group.name || `Group ${group.id}`)}</option>`).join('')}`;
        if (runtimeSelect) runtimeSelect.innerHTML = `<option value="all" ${this._runtimeFilter === 'all' ? 'selected' : ''}>All Runtime</option><option value="running" ${this._runtimeFilter === 'running' ? 'selected' : ''}>Running</option><option value="ready" ${this._runtimeFilter === 'ready' ? 'selected' : ''}>Ready</option><option value="linked" ${this._runtimeFilter === 'linked' ? 'selected' : ''}>Linked</option><option value="unlinked" ${this._runtimeFilter === 'unlinked' ? 'selected' : ''}>Unlinked</option>`;
        if (providerSelect) providerSelect.innerHTML = `<option value="all" ${this._providerFilter === 'all' ? 'selected' : ''}>All Provider</option><option value="global" ${this._providerFilter === 'global' ? 'selected' : ''}>Global</option><option value="funtap" ${this._providerFilter === 'funtap' ? 'selected' : ''}>Funtap</option>`;
        if (rangeButtons) rangeButtons.innerHTML = this._rangeOptions.map(([value, label]) => `<button type="button" class="btn ${value === this._selectedRangePreset ? 'active' : ''}" onclick="ReportPage.changeRangePreset('${value}')">${label}</button>`).join('');
        if (bucketButtons) bucketButtons.innerHTML = this._bucketOptions.map(([value, label]) => `<button type="button" class="btn ${value === this._selectedBucket ? 'active' : ''}" onclick="ReportPage.changeBucket('${value}')">${label}</button>`).join('');
        if (aggregationButtons) aggregationButtons.innerHTML = this._aggregationOptions.map(([value, label]) => `<button type="button" class="btn ${value === this._selectedAggregation ? 'active' : ''}" onclick="ReportPage.changeAggregation('${value}')">${label}</button>`).join('');
        if (timezoneButtons) timezoneButtons.innerHTML = ['local', 'utc'].map((value) => `<button type="button" class="btn ${value === this._timezoneMode ? 'active' : ''}" onclick="ReportPage.changeTimezoneMode('${value}')">${value.toUpperCase()}</button>`).join('');
        if (targetContext) {
            const sourceLabel = targetMeta.source === 'persisted' ? 'Saved target' : (targetMeta.source === 'temporary' ? 'Temporary target' : 'No saved target');
            targetContext.textContent = `${this._scopeLabel()} · ${sourceLabel}`;
        }
        if (customRangeAnchor) {
            if (this._selectedRangePreset === 'custom') customRangeAnchor.innerHTML = `<div class="button-row" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;"><input class="input" type="datetime-local" value="${this._formatInput(this._customFrom)}" onchange="ReportPage.changeCustomRange('from', this.value)"><input class="input" type="datetime-local" value="${this._formatInput(this._customTo)}" onchange="ReportPage.changeCustomRange('to', this.value)"></div>`;
            else {
                const { from, to } = this._rangeBounds();
                customRangeAnchor.innerHTML = `<div style="font-size:12px;color:var(--muted-foreground);">${this._dt(from)} → ${this._dt(to)}</div>`;
            }
        }
        this._renderAccountMenu(accountMenuAnchor);
        if (errorBanner) errorBanner.innerHTML = this._error ? `<div class="error-banner">${this._esc(this._error)}</div>` : '';
    },

    _renderAccountMenu(anchor = document.getElementById('report-account-menu-anchor')) {
        if (!anchor) return;
        if (!this._accountsExpanded) {
            anchor.innerHTML = '';
            return;
        }
        const filteredAccounts = this._filteredAccounts();
        anchor.innerHTML = `<div class="account-menu" onmousedown="event.stopPropagation()" onclick="event.stopPropagation()"><input id="report-account-search-input" class="input" type="text" placeholder="Search account, game id, emulator, alliance..." value="${this._esc(this._accountSearch)}" oninput="ReportPage.changeAccountSearch(this.value)" onclick="event.stopPropagation()"><div class="button-row"><button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.selectVisibleAccounts()">Select visible</button><button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.selectFirstAccounts(3)">Top 3</button><button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.selectFirstAccounts(5)">Top 5</button><button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.selectAllAccounts()">Select all</button><button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.clearSelectedAccounts()">Clear</button></div><div style="font-size:11px;color:var(--muted-foreground);">${filteredAccounts.length} account(s) match current filters</div>${filteredAccounts.map((account) => `<label class="account-option" onclick="event.stopPropagation()"><input type="checkbox" ${this._selectedGameIds.includes(account.game_id) ? 'checked' : ''} onchange="ReportPage.toggleAccount('${this._esc(account.game_id)}', this.checked)"><div><div>${this._esc(account.lord_name || 'Unknown')}</div><div style="font-size:11px;color:var(--muted-foreground);">${this._esc(account.game_id)} · ${this._esc(account.emu_name || 'Unlinked')} · ${this._esc(account.provider || 'Global')}</div></div></label>`).join('') || '<div class="empty-row">No accounts match current filters.</div>'}</div>`;
    },

    _restoreAccountSearchFocus() {
        if (!this._accountsExpanded) return;
        const active = document.activeElement;
        if (active && active.id === 'report-account-search-input') return;
        window.requestAnimationFrame(() => {
            const input = document.getElementById('report-account-search-input');
            if (!input) return;
            const length = input.value.length;
            input.focus();
            try { input.setSelectionRange(length, length); } catch (_) { }
        });
    },

    _renderSummarySection() {
        const host = document.getElementById('report-summary-grid');
        if (!host) return;
        const loadingClass = this._loadingChart ? ' is-loading' : '';
        const icons = [
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>',
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
        ];
        host.innerHTML = this._summaryCards().map(([label, value, note], index) => `<div class="panel summary-card${loadingClass}">${icons[index] || ''}<div class="summary-label">${this._esc(label)}</div><div class="summary-value">${this._esc(value)}</div><div class="summary-note">${this._esc(note)}</div></div>`).join('');
    },

    _renderLegend() {
        const host = document.getElementById('report-legend');
        if (!host) return;
        const series = this._chartCache?.series || [];
        host.innerHTML = series.map((item) => {
            const hiddenClass = this._legendHidden[item.game_id] ? ' legend-hidden' : '';
            return `<button type="button" class="btn legend-btn${hiddenClass}" onclick="ReportPage.toggleLegend('${this._esc(item.game_id)}')"><span class="legend-dot" style="background:${item.color};"></span><div><div>${this._esc(item.lord_name || item.game_id)}</div><div class="legend-meta">${this._riskBadge(item.derived_summary?.risk_level || 'healthy')}${(item.quality_flags || []).map((flag) => this._qualityBadge(flag)).join('')}</div></div></button>`;
        }).join('');
    },

    _renderChartSection() {
        const host = document.getElementById('report-chart-host');
        const subtitle = document.getElementById('report-chart-subtitle');
        const title = document.getElementById('report-chart-title');
        if (title) title.textContent = `${this._metricLabel()} Time Series`;
        if (subtitle) subtitle.textContent = `Bucket ${this._selectedBucket.toUpperCase()} · Aggregation ${this._selectedAggregation.toUpperCase()} · Range ${this._selectedRangePreset.toUpperCase()} · Timezone ${this._timezoneMode.toUpperCase()}`;
        if (!host) return;
        this._chartCache = this._buildChartCache();
        this._renderLegend();
        if (this._loadingChart) {
            host.innerHTML = `<div class="chart-empty"><div><span class="spinner"></span><div style="margin-top:10px;">Loading growth data…</div></div></div>`;
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
        host.innerHTML = `<svg id="report-chart-svg" class="chart-svg" viewBox="0 0 ${this._chartCache.geom.width} ${this._chartCache.geom.height}" preserveAspectRatio="xMidYMid meet"><rect x="0" y="0" width="${this._chartCache.geom.width}" height="${this._chartCache.geom.height}" fill="transparent"></rect>${this._chartCache.yTicks.map((tick) => `<g><line x1="${this._chartCache.geom.left}" y1="${tick.y}" x2="${this._chartCache.geom.width - this._chartCache.geom.right}" y2="${tick.y}" stroke="rgba(148,163,184,.18)" stroke-dasharray="4 6"></line><text x="${this._chartCache.geom.left - 12}" y="${tick.y + 4}" text-anchor="end" fill="hsl(215, 16%, 47%)" font-size="11">${this._esc(this._num(tick.value))}</text></g>`).join('')}${this._chartCache.xTicks.map((tick) => `<g><line x1="${tick.x}" y1="${this._chartCache.geom.top}" x2="${tick.x}" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="rgba(148,163,184,.08)"></line><text x="${tick.x}" y="${this._chartCache.geom.height - 14}" text-anchor="middle" fill="hsl(215, 16%, 47%)" font-size="11">${this._esc(tick.label)}</text></g>`).join('')}<line x1="${this._chartCache.geom.left}" y1="${this._chartCache.geom.height - this._chartCache.geom.bottom}" x2="${this._chartCache.geom.width - this._chartCache.geom.right}" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="rgba(148,163,184,.18)"></line><line x1="${this._chartCache.geom.left}" y1="${this._chartCache.geom.top}" x2="${this._chartCache.geom.left}" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="rgba(148,163,184,.18)"></line>${this._chartCache.series.map((series) => `<g><path d="${series.path}" fill="none" stroke="${series.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>${series.pointsChart.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="3.5" fill="${point.color}" stroke="white" stroke-width="2"></circle>`).join('')}</g>`).join('')}${this._chartCache.eventMarkers.map((marker) => `<g><line x1="${marker.x}" y1="${this._chartCache.geom.top}" x2="${marker.x}" y2="${this._chartCache.geom.top + 18}" stroke="${marker.color}" stroke-width="1.5" opacity=".9"></line><circle cx="${marker.x}" cy="${this._chartCache.geom.top + 20}" r="4" fill="${marker.color}"></circle></g>`).join('')}<line id="report-hover-line" x1="0" y1="${this._chartCache.geom.top}" x2="0" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="hsl(222, 47%, 11%)" stroke-width="1.5" stroke-dasharray="5 5" opacity="0"></line><circle id="report-hover-dot" cx="0" cy="0" r="6.5" fill="hsl(222, 47%, 11%)" stroke="white" stroke-width="3" opacity="0"></circle></svg>`;
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
        if (hoverLine) { hoverLine.setAttribute('x1', `${nearest.x}`); hoverLine.setAttribute('x2', `${nearest.x}`); hoverLine.setAttribute('stroke', nearest.color); hoverLine.setAttribute('opacity', '1'); }
        if (hoverDot) { hoverDot.setAttribute('cx', `${nearest.x}`); hoverDot.setAttribute('cy', `${nearest.y}`); hoverDot.setAttribute('fill', nearest.color); hoverDot.setAttribute('opacity', '1'); }
        const series = (this._chartData.series || []).find((item) => item.game_id === nearest.game_id) || {};
        const tooltip = document.getElementById('report-tooltip');
        if (!tooltip) return;
        tooltip.innerHTML = `<div class="tooltip-title">${this._esc(this._dt(nearest.timestampLabel))}</div><div class="tooltip-main">${this._esc(nearest.lord_name || nearest.game_id)}</div><div class="tooltip-row"><span>${this._esc(this._metricLabel())}</span><strong>${this._esc(this._num(nearest.value))}</strong></div><div class="tooltip-row"><span>Delta</span><strong class="${nearest.delta > 0 ? 'delta-up' : nearest.delta < 0 ? 'delta-down' : 'delta-flat'}">${this._esc(this._delta(nearest.delta))}</strong></div><div class="tooltip-row"><span>Growth %</span><strong>${this._esc(this._pct(series.derived_summary?.growth_pct_in_range))}</strong></div>`;
        const stageRect = svg.closest('.chart-stage')?.getBoundingClientRect() || rect;
        const offsetLeft = rect.left - stageRect.left;
        const offsetTop = rect.top - stageRect.top;
        tooltip.style.left = `${Math.min(Math.max(offsetLeft + (nearest.x * scaleX) + 20, 12), stageRect.width - 260)}px`;
        tooltip.style.top = `${Math.max(offsetTop + (nearest.y * scaleY) - 120, 12)}px`;
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

    _renderRiskFeed() {
        const host = document.getElementById('report-risk-feed');
        if (!host) return;
        if (!this._selectedGameIds.length) {
            host.innerHTML = '<div class="empty-row" style="grid-column:1/-1;">Pick one or more accounts to see risk signals.</div>';
            return;
        }
        const items = this._chartData?.meta?.risk_feed || [];
        host.innerHTML = items.length ? items.map((item) => `<div class="risk-card"><div style="display:flex;align-items:center;justify-content:space-between;gap:8px;"><strong>${this._esc(item.lord_name || item.game_id)}</strong>${this._riskBadge(item.risk_level || 'medium')}</div><div style="font-size:12px;color:var(--muted-foreground);">${this._esc(item.game_id)}</div><div class="legend-meta">${(item.reasons || []).map((reason) => this._qualityBadge(reason)).join('')}</div><div style="font-size:12px;color:var(--muted-foreground);">Target gap: ${item.target_gap_pct == null ? '--' : this._pct(item.target_gap_pct)}</div><div style="font-size:12px;color:var(--foreground);">${this._esc(item.recommended_action || 'Monitor closely.')}</div></div>`).join('') : '<div class="empty-row" style="grid-column:1/-1;">No at-risk accounts for the current view.</div>';
    },

    _renderTableSection() {
        const host = document.getElementById('report-table-host');
        const meta = document.getElementById('report-table-meta');
        if (!host || !meta) return;
        const rows = this._sortedSummaryRows();
        meta.textContent = `${rows.length} row(s)`;
        host.innerHTML = `<table><thead><tr><th onclick="ReportPage.sortBy('lord_name')">Account ${this._sortIndicator('lord_name')}</th><th onclick="ReportPage.sortBy('game_id')">Game ID ${this._sortIndicator('game_id')}</th><th onclick="ReportPage.sortBy('latest')">${this._esc(this._metricLabel())} ${this._sortIndicator('latest')}</th><th onclick="ReportPage.sortBy('growth_pct_in_range')">Growth % ${this._sortIndicator('growth_pct_in_range')}</th><th onclick="ReportPage.sortBy('growth_rate_per_day')">Velocity/Day ${this._sortIndicator('growth_rate_per_day')}</th><th onclick="ReportPage.sortBy('data_freshness_seconds')">Freshness ${this._sortIndicator('data_freshness_seconds')}</th><th onclick="ReportPage.sortBy('data_completeness_ratio')">Coverage ${this._sortIndicator('data_completeness_ratio')}</th><th onclick="ReportPage.sortBy('risk_level')">Risk ${this._sortIndicator('risk_level')}</th><th onclick="ReportPage.sortBy('target_gap_pct')">Target Gap % ${this._sortIndicator('target_gap_pct')}</th><th onclick="ReportPage.sortBy('eta_to_target')">ETA ${this._sortIndicator('eta_to_target')}</th><th onclick="ReportPage.sortBy('quality_flags')">Quality ${this._sortIndicator('quality_flags')}</th></tr></thead><tbody>${rows.length ? rows.map((row) => `<tr><td>${this._esc(row.lord_name)}</td><td>${this._esc(row.game_id)}</td><td><strong>${this._esc(this._num(row.latest))}</strong></td><td class="${row.growth_pct_in_range > 0 ? 'delta-up' : row.growth_pct_in_range < 0 ? 'delta-down' : 'delta-flat'}">${this._esc(this._pct(row.growth_pct_in_range))}</td><td class="${row.growth_rate_per_day > 0 ? 'delta-up' : row.growth_rate_per_day < 0 ? 'delta-down' : 'delta-flat'}">${this._esc(this._delta(row.growth_rate_per_day))}</td><td>${this._esc(this._hours(row.data_freshness_seconds))}</td><td>${Number.isFinite(row.data_completeness_ratio) ? `${Math.round(row.data_completeness_ratio * 100)}%` : '--'}</td><td>${this._riskBadge(row.risk_level)}</td><td>${this._esc(this._pct(row.target_gap_pct))}</td><td>${Number.isFinite(row.eta_to_target) ? this._esc(this._hours(row.eta_to_target)) : '--'}</td><td>${(row.quality_flags || []).map((flag) => this._qualityBadge(flag)).join('') || '<span style="color:var(--muted-foreground);">--</span>'}</td></tr>`).join('') : '<tr><td class="empty-row" colspan="11">No analyst rows for the current filter.</td></tr>'}</tbody></table>`;
    },

    _renderDrilldown() {
        const host = document.getElementById('report-drilldown-host');
        if (!host) return;
        if (this._selectedGameIds.length !== 1) {
            host.innerHTML = '<div class="empty-row">Select exactly one account to unlock the drilldown view.</div>';
            return;
        }
        const gameId = this._selectedGameIds[0];
        const series = (this._chartData.series || []).find((item) => item.game_id === gameId);
        if (!series) {
            host.innerHTML = '<div class="empty-row">No data loaded for the selected account.</div>';
            return;
        }
        const derived = series.derived_summary || {};
        const eventBlock = (this._eventsData.items || []).find((item) => item.game_id === gameId);
        host.innerHTML = `<div class="drilldown"><div><div class="drill-grid"><div class="drill-tile"><div class="summary-label">Latest ${this._esc(this._metricLabel())}</div><div class="drill-value">${this._esc(this._num(series.summary?.latest))}</div></div><div class="drill-tile"><div class="summary-label">Growth %</div><div class="drill-value">${this._esc(this._pct(derived.growth_pct_in_range))}</div></div><div class="drill-tile"><div class="summary-label">Velocity / Day</div><div class="drill-value">${this._esc(this._delta(derived.growth_rate_per_day))}</div></div><div class="drill-tile"><div class="summary-label">Coverage</div><div class="drill-value">${derived.data_completeness_ratio == null ? '--' : `${Math.round(derived.data_completeness_ratio * 100)}%`}</div></div><div class="drill-tile"><div class="summary-label">Freshness</div><div class="drill-value">${this._esc(this._hours(derived.data_freshness_seconds))}</div></div><div class="drill-tile"><div class="summary-label">Forecast ETA</div><div class="drill-value">${Number.isFinite(derived.eta_to_target) ? this._esc(this._hours(derived.eta_to_target)) : '--'}</div></div></div><div class="drill-tile" style="margin-top:12px;"><div class="summary-label">Reason Tags</div><div class="legend-meta" style="margin-top:8px;">${this._riskBadge(derived.risk_level || 'healthy')}${(series.quality_flags || []).map((flag) => this._qualityBadge(flag)).join('')}${(derived.root_cause_hints || []).map((hint) => this._qualityBadge(hint)).join('')}<span class="status-pill">${this._esc((derived.target_status || 'insufficient_data').replace(/_/g, ' '))}</span><span class="status-pill">${this._esc((derived.forecast_confidence || 'low').toUpperCase())} confidence</span></div><div style="margin-top:12px;color:var(--muted-foreground);font-size:12px;">Last sync ${this._esc(this._dt(series.summary?.last_sync_at))} · Last activity ${this._esc(this._dt(derived.last_activity_at))}</div></div></div><div class="drill-tile"><div class="summary-label">Activity Timeline</div><div class="timeline">${(eventBlock?.events || []).slice().reverse().slice(0, 12).map((event) => `<div class="timeline-item"><div><div>${this._esc(event.label || 'Activity')}</div><div style="font-size:11px;color:var(--muted-foreground);">${this._esc(event.status || '--')}</div></div><div style="text-align:right;"><div style="font-size:12px;">${this._esc(this._dt(event.timestamp))}</div><div style="font-size:11px;color:${event.status === 'FAILED' ? 'var(--red-600)' : 'var(--emerald-600)'};">${this._esc(event.error_message || '')}</div></div></div>`).join('') || '<div class="empty-row">No activity events in the selected range.</div>'}</div></div></div>`;
    },

    _refreshUI() {
        this._persistPreferences();
        this._renderControls();
        this._renderSummarySection();
        this._renderChartSection();
        this._renderRiskFeed();
        this._renderTableSection();
        this._renderDrilldown();
    },

    async loadAccounts() {
        this._loadingAccounts = true;
        this._error = '';
        this._renderControls();
        try {
            const data = await API.getAccounts();
            this._accounts = Array.isArray(data) ? data : [];
            const validIds = new Set(this._accounts.map((item) => item.game_id));
            this._selectedGameIds = this._selectedGameIds.filter((gameId) => validIds.has(gameId));
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
            if (this._selectedGroupId) {
                const selectedGroupId = this._normalizeScopeId(this._selectedGroupId);
                const hasGroup = selectedGroupId && this._groups.some((item) => this._normalizeScopeId(item?.id) === selectedGroupId);
                if (!hasGroup) this._selectedGroupId = '';
            }
        } catch (_) {
            this._groups = [];
            this._selectedGroupId = '';
        } finally {
            this._renderControls();
        }
    },

    async loadChartData() {
        if (!this._selectedGameIds.length) {
            this._chartData = { metric: this._selectedMetric, bucket: this._selectedBucket, aggregation: this._selectedAggregation, range: null, series: [], meta: {} };
            this._eventsData = { items: [] };
            this._legendHidden = {};
            this._refreshUI();
            return;
        }
        const { from, to } = this._rangeBounds();
        if (!Number.isFinite(from.getTime()) || !Number.isFinite(to.getTime()) || from >= to) {
            this._error = 'Invalid date range';
            this._chartData = { metric: this._selectedMetric, bucket: this._selectedBucket, aggregation: this._selectedAggregation, range: null, series: [], meta: {} };
            this._eventsData = { items: [] };
            this._refreshUI();
            return;
        }
        this._loadingChart = true;
        this._error = '';
        const requestId = ++this._loadRequestId;
        this._refreshUI();
        const scope = this._effectiveScope();
        try {
            const chartData = await API.getAccountTimeseries({
                gameIds: this._selectedGameIds,
                metric: this._selectedMetric,
                from: from.toISOString(),
                to: to.toISOString(),
                bucket: this._selectedBucket,
                aggregation: this._selectedAggregation,
                scopeType: scope.scopeType,
                scopeId: scope.scopeId,
                targetGrowthPct: this._targetGrowthPct !== '' ? this._targetGrowthPct : null,
                targetDueAt: this._targetDueAt || null,
            });
            if (requestId !== this._loadRequestId) return;
            this._chartData = chartData;
            this._eventsData = await API.getReportAccountEvents({ gameIds: this._selectedGameIds, from: from.toISOString(), to: to.toISOString() });
            if (requestId !== this._loadRequestId) return;
            const targetMeta = this._currentTargetMeta();
            if (targetMeta.source === 'persisted') {
                this._targetGrowthPct = targetMeta.target_growth_pct != null ? String(targetMeta.target_growth_pct) : this._targetGrowthPct;
                this._targetDueAt = targetMeta.due_at || this._targetDueAt;
            }
            this._normalizeLegendState();
            this._lastLoadedAt = new Date().toISOString();
        } catch (error) {
            if (requestId !== this._loadRequestId) return;
            this._chartData = { metric: this._selectedMetric, bucket: this._selectedBucket, aggregation: this._selectedAggregation, range: null, series: [], meta: {} };
            this._eventsData = { items: [] };
            this._error = error.message || 'Failed to load chart data';
        } finally {
            if (requestId === this._loadRequestId) {
                this._loadingChart = false;
                this._refreshUI();
            }
        }
    },

    async reloadChart() { await this.loadChartData(); },
    
    switchTab(tabId) {
        if (this._activeTab === tabId) return;
        this._activeTab = tabId;
        
        // Update DOM visibility
        document.getElementById('tab-btn-growth')?.classList.toggle('active', tabId === 'growth');
        document.getElementById('tab-btn-farming')?.classList.toggle('active', tabId === 'farming');
        
        const tabGrowth = document.getElementById('tab-growth');
        const tabFarming = document.getElementById('tab-farming');
        
        if (tabGrowth) tabGrowth.style.display = tabId === 'growth' ? 'block' : 'none';
        if (tabFarming) tabFarming.style.display = tabId === 'farming' ? 'block' : 'none';
        
        // Load data if needed
        if (tabId === 'farming') {
            this.loadFarmingData();
        } else {
            this._refreshUI(); 
            this._renderChartSection(); // chart requires strict visibility redraw
        }
    },
    
    async loadFarmingData() {
        if (!this._selectedGameIds.length) {
            this._farmingData = [];
            this._error = '';
            this._renderFarmingSection();
            return;
        }
        
        // Deduce days_back from range preset
        let daysBack = 7;
        if (this._selectedRangePreset === '24h') daysBack = 1;
        else if (this._selectedRangePreset === '30d') daysBack = 30;
        else if (this._selectedRangePreset === 'custom') {
            try {
                const ms = new Date(this._customTo).getTime() - new Date(this._customFrom).getTime();
                daysBack = Math.max(1, Math.round(ms / 86400000));
            } catch (_) {}
        }
        
        const params = new URLSearchParams({
            game_ids: this._selectedGameIds.join(','),
            days_back: String(daysBack),
        });

        const host = document.getElementById('farming-summary-grid');
        if (host) host.classList.add('is-loading');

        try {
            this._farmingData = await API.get(`/api/reports/accounts/farming?${params.toString()}`);
            this._error = '';
        } catch (error) {
            this._farmingData = [];
            this._error = error.message || 'Failed to load farming data';
        } finally {
            if (host) host.classList.remove('is-loading');
            this._renderFarmingSection();
            this._refreshUI();
        }
    },
    
    _renderFarmingSection() {
        if (this._activeTab !== 'farming') return;
        
        // 1. KPI Cards
        const kpiHost = document.getElementById('farming-summary-grid');
        if (kpiHost) {
            const totalGathers = this._farmingData.reduce((acc, row) => acc + (row.total_gathers || 0), 0);
            const totalCenter = this._farmingData.reduce((acc, row) => acc + (row.center_gathers || 0), 0);
            
            let gold = 0, wood = 0, ore = 0;
            this._farmingData.forEach(row => {
                const dist = row.rss_distribution || {};
                gold += dist.gold || 0;
                wood += dist.wood || 0;
                ore += dist.ore || 0;
            });
            const topRss = [{l:'Gold', v:gold}, {l:'Wood', v:wood}, {l:'Ore', v:ore}].sort((a,b) => b.v - a.v)[0];
            
            const totalDurMs = this._farmingData.reduce((acc, row) => acc + (row.total_duration_ms || 0), 0);
            const avgDurHours = totalGathers ? (totalDurMs / totalGathers / 3600000).toFixed(1) : 0;

            const cards = [
                ['Total Gathering Missions', this._num(totalGathers), `${this._num(totalCenter)} from RSS Center`],
                ['Farming Activity', this._farmingData.filter(d => d.total_gathers > 0).length, `Active farming accounts`],
                ['Most Mined Resource', totalGathers ? topRss.l : '--', totalGathers ? `${this._num(topRss.v)} missions` : 'Insufficient data'],
                ['Avg Mission Duration', totalGathers ? `${avgDurHours}h` : '--', 'Time per gathering task']
            ];
            
            const icons = [
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>',
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
            ];
            
            kpiHost.innerHTML = cards.map(([label, value, note], index) => `<div class="panel summary-card">${icons[index] || ''}<div class="summary-label">${this._esc(label)}</div><div class="summary-value" style="color:var(--primary);">${this._esc(value)}</div><div class="summary-note">${this._esc(note)}</div></div>`).join('');
        }

        // 2. Leaderboard
        const leaderHost = document.getElementById('farming-leaderboard');
        if (leaderHost) {
            const sorted = [...this._farmingData].filter((row) => Number(row.total_gathers || 0) > 0).sort((a,b) => b.total_gathers - a.total_gathers).slice(0, 10);
            leaderHost.innerHTML = sorted.length ? `<div style="display:flex;flex-direction:column;gap:12px;padding:16px;">
                ${sorted.map((r, i) => {
                    const acc = this._accounts.find(a => a.game_id === r.game_id) || {};
                    const barWidth = sorted[0].total_gathers ? (r.total_gathers / sorted[0].total_gathers * 100) : 0;
                    return `<div style="display:flex;align-items:center;gap:12px;">
                        <div style="width:24px;height:24px;background:var(--secondary);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:var(--muted-foreground);">${i+1}</div>
                        <div style="flex:1;">
                            <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:13px;">
                                <span><strong>${this._esc(acc.lord_name || r.game_id)}</strong></span>
                                <span style="font-family:monospace;color:var(--primary);">${this._num(r.total_gathers)}</span>
                            </div>
                            <div style="height:6px;background:var(--secondary);border-radius:3px;overflow:hidden;">
                                <div style="height:100%;width:${barWidth}%;background:var(--primary);border-radius:3px;"></div>
                            </div>
                        </div>
                    </div>`;
                }).join('')}
            </div>` : '<div class="chart-empty">No farming data in this period.</div>';
        }

        // 3. Lazy Board
        const lazyHost = document.getElementById('farming-lazy-board');
        if (lazyHost) {
            const now = Date.now();
            // accounts with 0 gathers or last gather > 48h ago
            const lazy = this._farmingData.filter(r => {
                if (r.total_gathers === 0) return true;
                if (!r.last_gathered_at) return true;
                return (now - new Date(r.last_gathered_at).getTime()) > 48 * 3600000;
            }).sort((a,b) => (a.total_gathers - b.total_gathers) || ((new Date(a.last_gathered_at||0).getTime()) - (new Date(b.last_gathered_at||0).getTime())));
            
            lazyHost.innerHTML = lazy.length ? `<div style="display:flex;flex-direction:column;gap:12px;padding:16px;">
                ${lazy.slice(0, 10).map((r) => {
                    const acc = this._accounts.find(a => a.game_id === r.game_id) || {};
                    let lazyMsg = "No recent activity";
                    if (r.last_gathered_at) {
                        const ms = now - new Date(r.last_gathered_at).getTime();
                        lazyMsg = `Idle for ${this._hours(ms / 1000)}`;
                    }
                    return `<div style="display:flex;justify-content:space-between;align-items:center;background:hsl(222, 18%, 10%);padding:12px;border-radius:6px;border:1px solid hsl(222, 18%, 18%);color:hsl(210, 40%, 96%);">
                        <div>
                            <div style="font-size:13px;font-weight:600;color:hsl(210, 40%, 96%);">${this._esc(acc.lord_name || r.game_id)}</div>
                            <div style="font-size:11px;color:hsl(32, 95%, 67%);margin-top:2px;">${this._esc(lazyMsg)}</div>
                        </div>
                        ${this._riskBadge('critical')}
                    </div>`;
                }).join('')}
            </div>` : '<div class="chart-empty">All accounts are actively farming!</div>';
        }

        // 4. Breakdown Table
        const tableHost = document.getElementById('farming-table-host');
        const countMeta = document.getElementById('farming-table-meta');
        if (tableHost) {
            if (countMeta) countMeta.innerText = `${this._farmingData.length} row(s)`;
            
            let sorted = [...this._farmingData].sort((a, b) => b.total_gathers - a.total_gathers);
            
            const html = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Account Name</th>
                            <th>Game ID</th>
                            <th>Total Gathers</th>
                            <th>RSS Center</th>
                            <th>World Gathers</th>
                            <th>Success Rate</th>
                            <th>Avg Duration</th>
                            <th>Last Active</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${sorted.length ? sorted.map(row => {
                            const acc = this._accounts.find(a => a.game_id === row.game_id) || {};
                            const successRate = Number(row.success_rate || 0);
                            const srClass = successRate >= 90 ? 'color:var(--emerald);' : (successRate < 50 && row.total_gathers ? 'color:var(--red);' : '');
                            const avgDur = row.total_gathers ? (row.total_duration_ms / row.total_gathers / 1000) : 0;
                            return `<tr>
                                <td><strong>${this._esc(acc.lord_name || '--')}</strong></td>
                                <td style="font-family:monospace;color:var(--muted-foreground);">${this._esc(row.game_id)}</td>
                                <td style="font-weight:bold;">${this._num(row.total_gathers)}</td>
                                <td>${this._num(row.center_gathers)}</td>
                                <td>${this._num(row.world_gathers)}</td>
                                <td style="${srClass}">${successRate.toFixed(1)}%</td>
                                <td style="color:var(--muted-foreground);">${this._hours(avgDur)}</td>
                                <td>${this._dt(row.last_gathered_at)}</td>
                            </tr>`;
                        }).join('') : '<tr><td colspan="8" class="empty-row">No farming activity in the selected period.</td></tr>'}
                    </tbody>
                </table>
            `;
            tableHost.innerHTML = html;
        }
    },

    toggleAccountsExpanded() { this._accountsExpanded = !this._accountsExpanded; this._renderControls(); },
    changeAccountSearch(value) { this._accountSearch = value || ''; this._renderAccountMenu(); this._restoreAccountSearchFocus(); },
    changeTargetGroup(groupId) { this._selectedGroupId = this._normalizeScopeId(groupId) || ''; this._accountSearch = ''; this._refreshUI(); this.loadChartData(); },
    changeRuntimeFilter(value) { this._runtimeFilter = value || 'all'; this._refreshUI(); },
    changeProviderFilter(value) { this._providerFilter = value || 'all'; this._refreshUI(); },
    changeTimezoneMode(value) { this._timezoneMode = value || 'local'; this._refreshUI(); },
    changeTargetGrowth(value) { this._targetGrowthPct = value === '' ? '' : String(value); this._persistPreferences(); },
    changeTargetDue(value) { this._targetDueAt = value ? new Date(value).toISOString() : ''; this._persistPreferences(); },
    sortBy(field) { if (this._sortField === field) this._sortDirection = this._sortDirection === 'asc' ? 'desc' : 'asc'; else { this._sortField = field; this._sortDirection = 'desc'; } this._renderTableSection(); },
    toggleAccount(gameId, checked) { if (checked) { if (!this._selectedGameIds.includes(gameId)) this._selectedGameIds.push(gameId); } else { this._selectedGameIds = this._selectedGameIds.filter((value) => value !== gameId); delete this._legendHidden[gameId]; } this._refreshUI(); this._restoreAccountSearchFocus(); this.loadChartData(); },
    selectFirstAccounts(count) { this._selectedGameIds = this._filteredAccounts().slice(0, count).map((item) => item.game_id); this._legendHidden = {}; this._refreshUI(); this._restoreAccountSearchFocus(); this.loadChartData(); },
    selectVisibleAccounts() { this._selectedGameIds = this._filteredAccounts().map((item) => item.game_id); this._legendHidden = {}; this._refreshUI(); this._restoreAccountSearchFocus(); this.loadChartData(); },
    selectAllAccounts() { this._selectedGameIds = this._accounts.map((item) => item.game_id); this._legendHidden = {}; this._refreshUI(); this._restoreAccountSearchFocus(); this.loadChartData(); },
    clearSelectedAccounts() { this._selectedGameIds = []; this._legendHidden = {}; this._chartData = { metric: this._selectedMetric, bucket: this._selectedBucket, aggregation: this._selectedAggregation, range: null, series: [], meta: {} }; this._eventsData = { items: [] }; this._refreshUI(); this._restoreAccountSearchFocus(); },
    changeMetric(metric) { this._selectedMetric = metric; this.loadChartData(); },
    changeRangePreset(preset) { this._selectedRangePreset = preset; if (preset === 'custom' && !this._customFrom && !this._customTo) { const now = new Date(); this._customTo = now.toISOString(); this._customFrom = new Date(now.getTime() - 7 * 86400000).toISOString(); } this._refreshUI(); this.loadChartData(); },
    changeCustomRange(side, value) { if (!value) return; const iso = new Date(value).toISOString(); if (side === 'from') this._customFrom = iso; if (side === 'to') this._customTo = iso; this._refreshUI(); this.loadChartData(); },
    changeBucket(bucket) { this._selectedBucket = bucket; this.loadChartData(); },
    changeAggregation(aggregation) { this._selectedAggregation = aggregation; this.loadChartData(); },
    toggleLegend(gameId) { this._legendHidden[gameId] = !this._legendHidden[gameId]; this._hideTooltip(); this._refreshUI(); },

    async saveTarget() {
        const scope = this._effectiveScope();
        const targetGrowthPct = Number(this._targetGrowthPct);
        if (!scope.scopeType || !scope.scopeId) { this._error = 'Select exactly one account or a group before saving a target.'; this._renderControls(); return; }
        if (!Number.isFinite(targetGrowthPct)) { this._error = 'Target Growth % is required.'; this._renderControls(); return; }
        if (!this._targetDueAt) { this._error = 'Target Due Date is required.'; this._renderControls(); return; }
        this._savingTarget = true;
        this._error = '';
        this._renderControls();
        try {
            await API.upsertReportTarget({ scope_type: scope.scopeType, scope_id: Number(scope.scopeId), metric: this._selectedMetric, target_growth_pct: targetGrowthPct, due_at: this._targetDueAt });
            await this.loadChartData();
        } catch (error) {
            this._error = error.message || 'Failed to save target';
            this._renderControls();
        } finally {
            this._savingTarget = false;
            this._renderControls();
        }
    },

    async clearSavedTarget() {
        const targetMeta = this._currentTargetMeta();
        if (!targetMeta || !targetMeta.id) {
            this._targetGrowthPct = '';
            this._targetDueAt = '';
            this._persistPreferences();
            this._renderControls();
            return;
        }
        try {
            await API.deleteReportTarget(targetMeta.id);
            this._targetGrowthPct = '';
            this._targetDueAt = '';
            await this.loadChartData();
        } catch (error) {
            this._error = error.message || 'Failed to delete target';
            this._renderControls();
        }
    },

    exportCsv() {
        const rows = this._sortedSummaryRows();
        const sanitize = (value) => String(value ?? '').replace(/,/g, '').replace(/"/g, '""');
        const csv = [['Account', 'Game ID', 'Metric', 'Growth %', 'Velocity/Day', 'Freshness', 'Coverage', 'Risk', 'Target Gap %', 'ETA', 'Flags'].join(',')].concat(rows.map((row) => [row.lord_name, row.game_id, this._num(row.latest), this._pct(row.growth_pct_in_range), this._delta(row.growth_rate_per_day), this._hours(row.data_freshness_seconds), row.data_completeness_ratio == null ? '--' : `${Math.round(row.data_completeness_ratio * 100)}%`, row.risk_level, this._pct(row.target_gap_pct), Number.isFinite(row.eta_to_target) ? this._hours(row.eta_to_target) : '--', (row.quality_flags || []).join('|')].map((value) => `"${sanitize(value)}"`).join(','))).join('n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `report-${this._selectedMetric}-${Date.now()}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    },

    async init() {
        this._loadPreferences();
        this._bindPersistentEvents();
        this._refreshUI();
        await this.loadAccounts();
        await this.loadGroups();
        if (this._selectedGameIds.length) await this.loadChartData();
    },

    destroy() {
        this._hideTooltip();
        this._loadRequestId++;
        if (this._boundDocClick) document.removeEventListener('click', this._boundDocClick);
        if (this._boundResize) window.removeEventListener('resize', this._boundResize);
        this._boundDocClick = null;
        this._boundResize = null;
        this._accountsExpanded = false;
        this._chartCache = null;
        this._loadingChart = false;
    },
};
