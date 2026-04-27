const ReportPage = {
    _storageKey: 'cod_report_preferences_v2',
    _accounts: [],
    _groups: [],
    _chartData: { metric: 'power', bucket: 'hour', aggregation: 'last', range: null, series: [], meta: {} },
    _eventsData: { items: [] },
    _farmingData: [],
    _workflowChartData: { metric: 'run_count', bucket: 'hour', aggregation: 'sum', range: null, series: [], meta: {}, activity: null },
    _workflowEventsData: { items: [] },
    _workflowActivities: [],
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
    _workflowLegendHidden: {},
    _accountsExpanded: false,
    _loadingAccounts: false,
    _loadingChart: false,
    _savingTarget: false,
    _editingPoint: null,
    _savingPoint: false,
    _error: '',
    _lastLoadedAt: '',
    _chartCache: null,
    _sortField: 'risk_level',
    _sortDirection: 'desc',
    _boundDocClick: null,
    _boundResize: null,
    _loadRequestId: 0,
    _workflowLoadRequestId: 0,
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
    _workflowMetricOptions: [
        ['run_count', 'Run Count'],
        ['success_rate', 'Success Rate'],
        ['avg_duration_ms', 'Avg Duration'],
        ['total_duration_ms', 'Total Duration'],
        ['success_count', 'Success Count'],
        ['fail_count', 'Fail Count'],
        ['attempts_avg', 'Attempts Avg'],
    ],
    _workflowAggregationOptions: [['sum', 'Sum'], ['avg', 'Avg'], ['min', 'Min'], ['max', 'Max'], ['count', 'Count'], ['last', 'Last']],
    _palette: ['#2f855a', '#3182ce', '#dd6b20', '#d53f8c', '#805ad5', '#0f766e', '#b7791f', '#4a5568'],
    _selectedWorkflowActivityId: '',
    _selectedWorkflowMetric: 'run_count',
    _selectedWorkflowAggregation: 'sum',
    _workflowChartCache: null,
    _workflowSortField: 'run_count',
    _workflowSortDirection: 'desc',

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
            this._selectedWorkflowActivityId = String(saved.selectedWorkflowActivityId || '');
            this._selectedWorkflowMetric = String(saved.selectedWorkflowMetric || this._selectedWorkflowMetric);
            this._selectedWorkflowAggregation = String(saved.selectedWorkflowAggregation || this._selectedWorkflowAggregation);
            this._activeTab = ['growth', 'workflow', 'farming'].includes(saved.activeTab) ? saved.activeTab : this._activeTab;
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
                selectedWorkflowActivityId: this._selectedWorkflowActivityId,
                selectedWorkflowMetric: this._selectedWorkflowMetric,
                selectedWorkflowAggregation: this._selectedWorkflowAggregation,
                activeTab: this._activeTab,
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

    _workflowMetricLabel(metric = this._selectedWorkflowMetric) {
        return this._workflowMetricOptions.find(([value]) => value === metric)?.[1] || metric;
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
        if (num < 60) return `${Math.max(0, Math.round(num))}s`;
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

    _activeSelectedGameIds() {
        const visibleIds = new Set(this._filteredAccounts().map((account) => String(account.game_id || '')));
        return (this._selectedGameIds || []).filter((gameId) => visibleIds.has(String(gameId || '')));
    },

    _selectedLabel() {
        if (!this._selectedGameIds.length) return 'Choose accounts';
        const activeIds = this._activeSelectedGameIds();
        if (activeIds.length !== this._selectedGameIds.length && activeIds.length > 0) {
            return `${activeIds.length}/${this._selectedGameIds.length} accounts active`;
        }
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

    _normalizeWorkflowLegendState() {
        const validIds = new Set((this._workflowChartData.series || []).map((item) => item.game_id));
        Object.keys(this._workflowLegendHidden).forEach((gameId) => {
            if (!validIds.has(gameId)) delete this._workflowLegendHidden[gameId];
        });
        if (this._selectedGameIds.length === 1) delete this._workflowLegendHidden[this._selectedGameIds[0]];
        const visibleCount = (this._workflowChartData.series || []).filter((item) => !this._workflowLegendHidden[item.game_id]).length;
        if ((this._workflowChartData.series || []).length && visibleCount === 0) this._workflowLegendHidden = {};
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
                latest_point: series.summary?.latest_point || null,
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

    _workflowSortIndicator(field) {
        if (this._workflowSortField !== field) return '<span style="opacity:.35; margin-left:6px;">↕</span>';
        return this._workflowSortDirection === 'asc' ? '<span style="margin-left:6px;">↑</span>' : '<span style="margin-left:6px;">↓</span>';
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
                    source_value: Number(point.source_value ?? point.value ?? 0),
                    snapshot_id: point.snapshot_id,
                    source: point.source,
                    metric: point.metric || this._selectedMetric,
                    editable: !!point.editable,
                    aggregation_note: point.aggregation_note || '',
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
                        <div><h1 id="report-hero-title" class="hero-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>Growth Command Center</h1><p id="report-hero-subtitle" class="hero-subtitle">Track growth velocity, target progress, data quality, and operational signals for every account from one screen.</p></div>
                        <div class="button-row">
                            <button id="report-refresh-button" class="btn" type="button" onclick="ReportPage.reloadChart()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>Refresh</button>
                            <button id="report-export-button" class="btn" type="button" onclick="ReportPage.exportCsv()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>Export CSV</button>
                            <button id="report-save-target-button" class="btn" type="button" onclick="ReportPage.saveTarget()" ${this._savingTarget ? 'disabled' : ''}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>${this._savingTarget ? 'Saving...' : 'Save Target'}</button>
                            <button id="report-clear-target-button" class="btn" type="button" onclick="ReportPage.clearSavedTarget()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>Clear Target</button>
                        </div>
                    </div>
                    <div class="toolbar-grid">
                        <div class="field span-4"><div class="field-label">Accounts</div><button class="account-trigger input" type="button" onclick="ReportPage.toggleAccountsExpanded()"><span>${this._esc(this._selectedLabel())}</span><span>${this._accountsExpanded ? '&#9650;' : '&#9660;'}</span></button><div id="report-account-menu-anchor"></div></div>
                        <div class="field span-2"><div id="report-group-label" class="field-label">Target Group</div><select id="report-group-select" class="select" style="background: white; color: #1e293b;"></select></div>
                        <div id="report-metric-field" class="field span-2"><div class="field-label">Metric</div><select id="report-metric-select" class="select" style="background: white; color: #1e293b;">${this._metricOptions.map(([value, label]) => `<option value="${value}" ${value === this._selectedMetric ? 'selected' : ''}>${label}</option>`).join('')}</select></div>
                        <div class="field span-2"><div class="field-label">Runtime</div><select id="report-runtime-select" class="select" style="background: white; color: #1e293b;"></select></div>
                        <div class="field span-2"><div class="field-label">Provider</div><select id="report-provider-select" class="select" style="background: white; color: #1e293b;"></select></div>
                        <div class="field span-3"><div class="field-label">Range</div><div id="report-range-buttons" class="button-row"></div><div id="report-custom-range-anchor"></div></div>
                        <div class="field span-2"><div class="field-label">Bucket</div><div id="report-bucket-buttons" class="button-row"></div></div>
                        <div id="report-aggregation-field" class="field span-3"><div class="field-label">Aggregation</div><div id="report-aggregation-buttons" class="button-row"></div></div>
                        <div class="field span-2"><div class="field-label">Timezone</div><div id="report-timezone-buttons" class="button-row"></div></div>
                        <div id="report-target-growth-field" class="field span-2"><div class="field-label">Target Growth %</div><input id="report-target-growth" class="input" type="number" placeholder="e.g. 18" value="${this._esc(this._targetGrowthPct)}"></div>
                        <div id="report-target-due-field" class="field span-2"><div class="field-label">Target Due Date</div><input id="report-target-due" class="input" type="datetime-local" value="${this._formatInput(this._targetDueAt)}"></div>
                        <div id="report-target-context-field" class="field span-3"><div class="field-label">Target Context</div><div id="report-target-context" class="status-pill">Loading...</div></div>
                    </div>
                    <div id="report-error-banner"></div>
                </section>
                
                <div class="report-tabs">
                    <button class="tab-btn active" id="tab-btn-growth" onclick="ReportPage.switchTab('growth')">Growth Analytics</button>
                    <button class="tab-btn" id="tab-btn-workflow" onclick="ReportPage.switchTab('workflow')">Workflow Analytics</button>
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

                <div id="tab-workflow" style="display: none;">
                    <section class="panel">
                        <div class="panel-header">
                            <div class="panel-heading">
                                <div class="panel-title">Workflow Filters</div>
                                <div class="panel-subtitle">Analyze one workflow activity across selected accounts using the same time window and bucket controls.</div>
                            </div>
                        </div>
                        <div class="toolbar-grid" style="margin-top:0;padding:0 16px 16px;">
                            <div class="field span-4">
                                <div class="field-label">Workflow Activity</div>
                                <select id="report-workflow-activity-select" class="select"></select>
                            </div>
                            <div class="field span-3">
                                <div class="field-label">Workflow Metric</div>
                                <select id="report-workflow-metric-select" class="select">
                                    ${this._workflowMetricOptions.map(([value, label]) => `<option value="${value}" ${value === this._selectedWorkflowMetric ? 'selected' : ''}>${label}</option>`).join('')}
                                </select>
                            </div>
                            <div class="field span-5">
                                <div class="field-label">Workflow Aggregation</div>
                                <div id="report-workflow-aggregation-buttons" class="button-row"></div>
                            </div>
                        </div>
                    </section>
                    <section id="workflow-summary-grid" class="summary-grid"></section>
                    <section class="panel">
                        <div class="panel-header">
                            <div class="panel-heading">
                                <div id="workflow-chart-title" class="panel-title">Workflow Analytics</div>
                                <div id="workflow-chart-subtitle" class="panel-subtitle"></div>
                            </div>
                            <div id="workflow-legend" class="legend"></div>
                        </div>
                        <div class="chart-stage">
                            <div id="workflow-chart-host"></div>
                            <div id="workflow-tooltip" class="tooltip"></div>
                        </div>
                    </section>
                    <section class="insight-grid">
                        <section class="panel">
                            <div class="panel-header"><div class="panel-heading"><div class="panel-title">Workflow Risk Feed</div><div class="panel-subtitle">Accounts that are stale, failing, or under-executed for this workflow.</div></div></div>
                            <div id="workflow-risk-feed" class="risk-feed"></div>
                        </section>
                        <section class="panel">
                            <div class="panel-header"><div class="panel-heading"><div class="panel-title">Workflow Drilldown</div><div class="panel-subtitle">Per-account execution quality, duration, and recent run history.</div></div></div>
                            <div id="workflow-drilldown-host"></div>
                        </section>
                    </section>
                    <section class="panel">
                        <div class="panel-header">
                            <div class="panel-title">Workflow Table</div>
                            <div id="workflow-table-meta" style="font-size:12px;color:var(--muted-foreground);">0 row(s)</div>
                        </div>
                        <div class="table-wrap" id="workflow-table-host"></div>
                    </section>
                </div>
                
                <div id="tab-farming" style="display: none;">
                    <section id="farming-summary-grid" class="summary-grid"></section>
                    <section class="panel">
                        <div class="panel-header">
                            <div class="panel-heading">
                                <div class="panel-title">Gathering Frequency by Day</div>
                                <div id="farming-chart-subtitle" class="panel-subtitle">Daily execution trend across the currently selected accounts.</div>
                            </div>
                        </div>
                        <div class="chart-stage">
                            <div id="farming-chart-host"></div>
                        </div>
                    </section>
                    <section class="insight-grid" style="grid-template-columns: 1fr 1fr;">
                        <section class="panel"><div class="panel-header"><div class="panel-heading"><div class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>Top Farmers</div><div class="panel-subtitle">Accounts with the highest gathering frequency.</div></div></div><div id="farming-leaderboard"></div></section>
                        <section class="panel"><div class="panel-header"><div class="panel-heading"><div class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>Lazy Accounts</div><div class="panel-subtitle">Accounts with zero or old gathering activity.</div></div></div><div id="farming-lazy-board"></div></section>
                    </section>
                    <section class="panel"><div class="panel-header"><div class="panel-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;display:inline;vertical-align:-2px;margin-right:6px;opacity:.5;"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>Farming Breakdown</div><div id="farming-table-meta" style="font-size:12px;color:var(--muted-foreground);">0 row(s)</div></div><div class="table-wrap" id="farming-table-host"></div></section>
                </div>
                <div id="report-edit-modal-host"></div>
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
        const workflowActivitySelect = document.getElementById('report-workflow-activity-select');
        const workflowMetricSelect = document.getElementById('report-workflow-metric-select');
        if (metricSelect) metricSelect.onchange = (event) => this.changeMetric(event.target.value);
        if (groupSelect) groupSelect.onchange = (event) => this.changeTargetGroup(event.target.value);
        if (runtimeSelect) runtimeSelect.onchange = (event) => this.changeRuntimeFilter(event.target.value);
        if (providerSelect) providerSelect.onchange = (event) => this.changeProviderFilter(event.target.value);
        if (targetGrowth) targetGrowth.onchange = (event) => this.changeTargetGrowth(event.target.value);
        if (targetDue) targetDue.onchange = (event) => this.changeTargetDue(event.target.value);
        if (workflowActivitySelect) workflowActivitySelect.onchange = (event) => this.changeWorkflowActivity(event.target.value);
        if (workflowMetricSelect) workflowMetricSelect.onchange = (event) => this.changeWorkflowMetric(event.target.value);

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
                this._hideWorkflowTooltip();
                if (this._activeTab === 'workflow') this._renderWorkflowChartSection();
                else this._renderChartSection();
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
        const workflowActivitySelect = document.getElementById('report-workflow-activity-select');
        const workflowAggregationButtons = document.getElementById('report-workflow-aggregation-buttons');
        const heroTitle = document.getElementById('report-hero-title');
        const heroSubtitle = document.getElementById('report-hero-subtitle');
        const groupLabel = document.getElementById('report-group-label');
        const metricField = document.getElementById('report-metric-field');
        const aggregationField = document.getElementById('report-aggregation-field');
        const targetGrowthField = document.getElementById('report-target-growth-field');
        const targetDueField = document.getElementById('report-target-due-field');
        const targetContextField = document.getElementById('report-target-context-field');
        const saveTargetButton = document.getElementById('report-save-target-button');
        const clearTargetButton = document.getElementById('report-clear-target-button');
        const exportButton = document.getElementById('report-export-button');
        const targetMeta = this._currentTargetMeta();
        const isGrowthTab = this._activeTab === 'growth';
        const isWorkflowTab = this._activeTab === 'workflow';
        const isFarmingTab = this._activeTab === 'farming';

        if (groupSelect) groupSelect.innerHTML = `<option value="">All Groups</option>${(this._groups || []).map((group) => `<option value="${group.id}" ${String(group.id) === String(this._selectedGroupId || '') ? 'selected' : ''}>${this._esc(group.name || `Group ${group.id}`)}</option>`).join('')}`;
        if (runtimeSelect) runtimeSelect.innerHTML = `<option value="all" ${this._runtimeFilter === 'all' ? 'selected' : ''}>All Runtime</option><option value="running" ${this._runtimeFilter === 'running' ? 'selected' : ''}>Running</option><option value="ready" ${this._runtimeFilter === 'ready' ? 'selected' : ''}>Ready</option><option value="linked" ${this._runtimeFilter === 'linked' ? 'selected' : ''}>Linked</option><option value="unlinked" ${this._runtimeFilter === 'unlinked' ? 'selected' : ''}>Unlinked</option>`;
        if (providerSelect) providerSelect.innerHTML = `<option value="all" ${this._providerFilter === 'all' ? 'selected' : ''}>All Provider</option><option value="global" ${this._providerFilter === 'global' ? 'selected' : ''}>Global</option><option value="funtap" ${this._providerFilter === 'funtap' ? 'selected' : ''}>Funtap</option>`;
        if (rangeButtons) rangeButtons.innerHTML = this._rangeOptions.map(([value, label]) => `<button type="button" class="btn ${value === this._selectedRangePreset ? 'active' : ''}" onclick="ReportPage.changeRangePreset('${value}')">${label}</button>`).join('');
        if (bucketButtons) bucketButtons.innerHTML = this._bucketOptions.map(([value, label]) => `<button type="button" class="btn ${value === this._selectedBucket ? 'active' : ''}" onclick="ReportPage.changeBucket('${value}')">${label}</button>`).join('');
        if (aggregationButtons) aggregationButtons.innerHTML = this._aggregationOptions.map(([value, label]) => `<button type="button" class="btn ${value === this._selectedAggregation ? 'active' : ''}" onclick="ReportPage.changeAggregation('${value}')">${label}</button>`).join('');
        if (timezoneButtons) timezoneButtons.innerHTML = ['local', 'utc'].map((value) => `<button type="button" class="btn ${value === this._timezoneMode ? 'active' : ''}" onclick="ReportPage.changeTimezoneMode('${value}')">${value.toUpperCase()}</button>`).join('');
        if (workflowActivitySelect) {
            workflowActivitySelect.innerHTML = (this._workflowActivities || []).length
                ? (this._workflowActivities || []).map((item) => `<option value="${this._esc(item.id)}" ${item.id === this._selectedWorkflowActivityId ? 'selected' : ''}>${this._esc(item.name)}</option>`).join('')
                : '<option value="">No workflow activities</option>';
        }
        if (workflowAggregationButtons) {
            workflowAggregationButtons.innerHTML = this._workflowAggregationOptions.map(([value, label]) => `<button type="button" class="btn ${value === this._selectedWorkflowAggregation ? 'active' : ''}" onclick="ReportPage.changeWorkflowAggregation('${value}')">${label}</button>`).join('');
        }
        if (heroTitle) heroTitle.innerHTML = isWorkflowTab
            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 16l3-3 3 2 5-6"/></svg>Workflow Command Center'
            : isFarmingTab
                ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 21h10"/><path d="M12 21V9"/><path d="M5 9c0-1.7 1.3-3 3-3 1.3 0 2.4.8 2.8 2 .5-1.2 1.7-2 3-2 1.7 0 3 1.3 3 3 0 4-3.4 6.6-5.8 8.4-.6.4-1.5.4-2.1 0C8.4 15.6 5 13 5 9z"/></svg>Farming Efficiency Center'
                : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>Growth Command Center';
        if (heroSubtitle) heroSubtitle.textContent = isWorkflowTab
            ? 'Track workflow throughput, duration, success rate, and execution risk across selected accounts.'
            : isFarmingTab
                ? 'Compare gathering output, idle accounts, and farming efficiency without digging through logs.'
                : 'Track growth velocity, target progress, data quality, and operational signals for every account from one screen.';
        if (groupLabel) groupLabel.textContent = isGrowthTab ? 'Target Group' : 'Group Filter';
        if (metricField) metricField.style.display = isGrowthTab ? '' : 'none';
        if (aggregationField) aggregationField.style.display = isGrowthTab ? '' : 'none';
        if (targetGrowthField) targetGrowthField.style.display = isGrowthTab ? '' : 'none';
        if (targetDueField) targetDueField.style.display = isGrowthTab ? '' : 'none';
        if (targetContextField) targetContextField.style.display = isGrowthTab ? '' : 'none';
        if (saveTargetButton) saveTargetButton.style.display = isGrowthTab ? '' : 'none';
        if (clearTargetButton) clearTargetButton.style.display = isGrowthTab ? '' : 'none';
        if (exportButton) exportButton.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>${isWorkflowTab ? 'Export Workflow CSV' : isFarmingTab ? 'Export Farming CSV' : 'Export CSV'}`;
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
        const activeSelectedCount = this._activeSelectedGameIds().length;
        const accountRows = filteredAccounts.map((account) => `
            <label class="account-option" onclick="event.stopPropagation()">
                <input type="checkbox" ${this._selectedGameIds.includes(account.game_id) ? 'checked' : ''} onchange="ReportPage.toggleAccount('${this._esc(account.game_id)}', this.checked)">
                <div>
                    <div>${this._esc(account.lord_name || 'Unknown')}</div>
                    <div>${this._esc(account.game_id)} - ${this._esc(account.emu_name || 'Unlinked')} - ${this._esc(account.provider || 'Global')}</div>
                </div>
            </label>`).join('');
        anchor.innerHTML = `
            <div class="account-menu" onmousedown="event.stopPropagation()" onclick="event.stopPropagation()">
                <div class="account-menu-sticky">
                    <input id="report-account-search-input" class="input" type="text" placeholder="Search account, game id, emulator, alliance..." value="${this._esc(this._accountSearch)}" oninput="ReportPage.changeAccountSearch(this.value)" onclick="event.stopPropagation()">
                    <div class="button-row account-menu-actions">
                        <button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.selectVisibleAccounts()">Select visible</button>
                        <button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.selectFirstAccounts(3)">Top 3</button>
                        <button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.selectFirstAccounts(5)">Top 5</button>
                        <button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.selectAllAccounts()">All</button>
                        <button class="chip" type="button" onclick="event.stopPropagation(); ReportPage.clearSelectedAccounts()">Clear</button>
                    </div>
                    <div class="account-menu-meta">${filteredAccounts.length} match current filters - ${activeSelectedCount}/${this._selectedGameIds.length} selected active</div>
                </div>
                <div class="account-list">
                    ${accountRows || '<div class="empty-row">No accounts match current filters.</div>'}
                </div>
            </div>`;
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
        const activeGameIds = this._activeSelectedGameIds();
        if (title) title.textContent = `${this._metricLabel()} Time Series`;
        if (subtitle) subtitle.textContent = `Bucket ${this._selectedBucket.toUpperCase()} - Aggregation ${this._selectedAggregation.toUpperCase()} - Range ${this._selectedRangePreset.toUpperCase()} - Timezone ${this._timezoneMode.toUpperCase()} - Click a dot to edit source data`;
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
        if (!activeGameIds.length) {
            host.innerHTML = `<div class="chart-empty">No selected accounts match the current group/runtime/provider filters.</div>`;
            this._hideTooltip();
            return;
        }
        if (!(this._chartCache.series || []).some((series) => (series.pointsChart || []).length)) {
            host.innerHTML = `<div class="chart-empty">No data points found for the current filter.</div>`;
            this._hideTooltip();
            return;
        }
        let pointIndex = 0;
        host.innerHTML = `<svg id="report-chart-svg" class="chart-svg" viewBox="0 0 ${this._chartCache.geom.width} ${this._chartCache.geom.height}" preserveAspectRatio="xMidYMid meet"><rect x="0" y="0" width="${this._chartCache.geom.width}" height="${this._chartCache.geom.height}" fill="transparent"></rect>${this._chartCache.yTicks.map((tick) => `<g><line x1="${this._chartCache.geom.left}" y1="${tick.y}" x2="${this._chartCache.geom.width - this._chartCache.geom.right}" y2="${tick.y}" stroke="rgba(148,163,184,.18)" stroke-dasharray="4 6"></line><text x="${this._chartCache.geom.left - 12}" y="${tick.y + 4}" text-anchor="end" fill="hsl(215, 16%, 47%)" font-size="11">${this._esc(this._num(tick.value))}</text></g>`).join('')}${this._chartCache.xTicks.map((tick) => `<g><line x1="${tick.x}" y1="${this._chartCache.geom.top}" x2="${tick.x}" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="rgba(148,163,184,.08)"></line><text x="${tick.x}" y="${this._chartCache.geom.height - 14}" text-anchor="middle" fill="hsl(215, 16%, 47%)" font-size="11">${this._esc(tick.label)}</text></g>`).join('')}<line x1="${this._chartCache.geom.left}" y1="${this._chartCache.geom.height - this._chartCache.geom.bottom}" x2="${this._chartCache.geom.width - this._chartCache.geom.right}" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="rgba(148,163,184,.18)"></line><line x1="${this._chartCache.geom.left}" y1="${this._chartCache.geom.top}" x2="${this._chartCache.geom.left}" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="rgba(148,163,184,.18)"></line>${this._chartCache.eventMarkers.map((marker) => `<g class="report-event-marker"><line x1="${marker.x}" y1="${this._chartCache.geom.top - 4}" x2="${marker.x}" y2="${this._chartCache.geom.top + 10}" stroke="${marker.color}" stroke-width="2" opacity=".55"></line><path d="M ${marker.x} ${this._chartCache.geom.top - 4} l 8 4 l -8 4 z" fill="${marker.color}" opacity=".65"></path><title>Activity event marker</title></g>`).join('')}${this._chartCache.series.map((series) => `<g><path d="${series.path}" fill="none" stroke="${series.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>${series.pointsChart.map((point) => { const index = pointIndex++; return `<circle class="report-data-hit ${point.editable ? 'is-editable' : ''}" data-point-index="${index}" cx="${point.x}" cy="${point.y}" r="13" fill="transparent" stroke="transparent"></circle><circle class="report-data-point ${point.editable ? 'is-editable' : ''}" data-point-index="${index}" cx="${point.x}" cy="${point.y}" r="4.5" fill="${point.color}" stroke="white" stroke-width="2"><title>${this._esc(point.editable ? 'Click to edit this datapoint' : 'Datapoint is not editable')}</title></circle>`; }).join('')}</g>`).join('')}<line id="report-hover-line" x1="0" y1="${this._chartCache.geom.top}" x2="0" y2="${this._chartCache.geom.height - this._chartCache.geom.bottom}" stroke="hsl(222, 47%, 11%)" stroke-width="1.5" stroke-dasharray="5 5" opacity="0"></line><circle id="report-hover-dot" cx="0" cy="0" r="6.5" fill="hsl(222, 47%, 11%)" stroke="white" stroke-width="3" opacity="0"></circle></svg>`;
        const svg = document.getElementById('report-chart-svg');
        if (svg) {
            svg.onmousemove = (event) => this._handleChartHover(event);
            svg.onmouseleave = () => this._hideTooltip();
            svg.onclick = (event) => this._handleChartClick(event);
            svg.querySelectorAll('.report-data-point,.report-data-hit').forEach((node) => {
                node.addEventListener('click', (event) => {
                    event.stopPropagation();
                    const index = Number(node.getAttribute('data-point-index'));
                    const point = this._chartCache.hoverPoints[index];
                    if (point?.editable) this.openDatapointEditor(point);
                });
            });
        }
    },

    _nearestChartPoint(event) {
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
        return { nearest, svg, rect, scaleX, scaleY, score };
    },

    _handleChartHover(event) {
        const result = this._nearestChartPoint(event);
        if (!result?.nearest) return;
        const { nearest, svg, rect, scaleX, scaleY } = result;
        const hoverLine = document.getElementById('report-hover-line');
        const hoverDot = document.getElementById('report-hover-dot');
        if (hoverLine) { hoverLine.setAttribute('x1', `${nearest.x}`); hoverLine.setAttribute('x2', `${nearest.x}`); hoverLine.setAttribute('stroke', nearest.color); hoverLine.setAttribute('opacity', '1'); }
        if (hoverDot) { hoverDot.setAttribute('cx', `${nearest.x}`); hoverDot.setAttribute('cy', `${nearest.y}`); hoverDot.setAttribute('fill', nearest.color); hoverDot.setAttribute('opacity', '1'); }
        const series = (this._chartData.series || []).find((item) => item.game_id === nearest.game_id) || {};
        const tooltip = document.getElementById('report-tooltip');
        if (!tooltip) return;
        tooltip.innerHTML = `<div class="tooltip-title">${this._esc(this._dt(nearest.timestampLabel))}</div><div class="tooltip-main">${this._esc(nearest.lord_name || nearest.game_id)}</div><div class="tooltip-row"><span>${this._esc(this._metricLabel())}</span><strong>${this._esc(this._num(nearest.value))}</strong></div><div class="tooltip-row"><span>Delta</span><strong class="${nearest.delta > 0 ? 'delta-up' : nearest.delta < 0 ? 'delta-down' : 'delta-flat'}">${this._esc(this._delta(nearest.delta))}</strong></div><div class="tooltip-row"><span>Growth %</span><strong>${this._esc(this._pct(series.derived_summary?.growth_pct_in_range))}</strong></div>${nearest.editable ? '<div class="tooltip-hint">Click node to edit source data</div>' : ''}`;
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

    _pointEditorPayload(point) {
        if (!point?.snapshot_id) return null;
        return {
            snapshot_id: Number(point.snapshot_id),
            game_id: String(point.game_id || ''),
            lord_name: point.lord_name || point.game_id || '',
            metric: point.metric || this._selectedMetric,
            source: point.source || '',
            timestamp: point.timestampLabel || point.timestamp || '',
            value: Number(point.source_value ?? point.value ?? 0),
            chart_value: Number(point.value || 0),
            aggregation_note: point.aggregation_note || '',
        };
    },

    openDatapointEditor(point) {
        const payload = this._pointEditorPayload(point);
        if (!payload) {
            this._error = 'This datapoint is not editable because it has no source snapshot.';
            this._renderControls();
            return;
        }
        this._hideTooltip();
        this._editingPoint = payload;
        this._renderPointEditor();
    },

    openLatestDatapointEditor(gameId) {
        const series = (this._chartData.series || []).find((item) => item.game_id === gameId);
        const latestPoint = series?.summary?.latest_point;
        if (!latestPoint?.snapshot_id) {
            this._error = 'Latest datapoint is not editable for this row.';
            this._renderControls();
            return;
        }
        this.openDatapointEditor({
            ...latestPoint,
            game_id: series.game_id,
            lord_name: series.lord_name || series.game_id,
            timestampLabel: latestPoint.timestamp,
            value: latestPoint.value,
        });
    },

    closeDatapointEditor() {
        if (this._savingPoint) return;
        this._editingPoint = null;
        this._renderPointEditor();
    },

    _renderPointEditor() {
        const host = document.getElementById('report-edit-modal-host');
        if (!host) return;
        const point = this._editingPoint;
        if (!point) {
            host.innerHTML = '';
            return;
        }
        const note = point.aggregation_note
            ? `<div class="edit-modal-warning">${this._esc(point.aggregation_note)}. Editing will update that backing snapshot, then reload the chart.</div>`
            : '<div class="edit-modal-warning">This updates the backing scan row used by the dashboard, then reloads the current view.</div>';
        host.innerHTML = `
            <div class="edit-modal-backdrop" onclick="ReportPage.closeDatapointEditor()">
                <div class="edit-modal" onclick="event.stopPropagation()">
                    <div class="edit-modal-header">
                        <div>
                            <div class="edit-modal-kicker">Edit Source Datapoint</div>
                            <h3>${this._esc(this._metricLabel(point.metric))}</h3>
                        </div>
                        <button class="btn" type="button" onclick="ReportPage.closeDatapointEditor()">Close</button>
                    </div>
                    <div class="edit-modal-body">
                        <div class="edit-meta-grid">
                            <div><span>Account</span><strong>${this._esc(point.lord_name || point.game_id)}</strong></div>
                            <div><span>Game ID</span><strong>${this._esc(point.game_id)}</strong></div>
                            <div><span>Timestamp</span><strong>${this._esc(this._dt(point.timestamp))}</strong></div>
                            <div><span>Snapshot ID</span><strong>#${this._esc(point.snapshot_id)}</strong></div>
                            <div><span>Chart Value</span><strong>${this._esc(this._num(point.chart_value, point.metric))}</strong></div>
                            <div><span>Source Value</span><strong>${this._esc(this._num(point.value, point.metric))}</strong></div>
                        </div>
                        ${note}
                        <label class="field">
                            <span class="field-label">Correct value</span>
                            <input id="report-edit-point-value" class="input" type="number" min="0" step="1" value="${this._esc(point.value)}" onkeydown="if(event.key==='Enter'){event.preventDefault();ReportPage.saveDatapointEdit();}">
                        </label>
                    </div>
                    <div class="edit-modal-footer">
                        <button class="btn" type="button" onclick="ReportPage.closeDatapointEditor()" ${this._savingPoint ? 'disabled' : ''}>Cancel</button>
                        <button class="btn primary" type="button" onclick="ReportPage.saveDatapointEdit()" ${this._savingPoint ? 'disabled' : ''}>${this._savingPoint ? 'Saving...' : 'Save and Reload'}</button>
                    </div>
                </div>
            </div>`;
        window.requestAnimationFrame(() => {
            const input = document.getElementById('report-edit-point-value');
            if (input) {
                input.focus();
                input.select();
            }
        });
    },

    async saveDatapointEdit() {
        if (!this._editingPoint || this._savingPoint) return;
        const input = document.getElementById('report-edit-point-value');
        const value = Number(input?.value);
        if (!Number.isFinite(value) || value < 0) {
            this._error = 'Correct value must be a non-negative number.';
            this._renderControls();
            return;
        }
        this._savingPoint = true;
        this._renderPointEditor();
        try {
            await API.updateReportDatapoint({
                snapshot_id: this._editingPoint.snapshot_id,
                game_id: this._editingPoint.game_id,
                metric: this._editingPoint.metric,
                value,
            });
            this._editingPoint = null;
            this._error = '';
            await this.loadChartData();
        } catch (error) {
            this._error = error.message || 'Failed to update datapoint';
            this._renderControls();
        } finally {
            this._savingPoint = false;
            this._renderPointEditor();
        }
    },

    _renderRiskFeed() {
        const host = document.getElementById('report-risk-feed');
        if (!host) return;
        const activeGameIds = this._activeSelectedGameIds();
        if (!this._selectedGameIds.length) {
            host.innerHTML = '<div class="empty-row" style="grid-column:1/-1;">Pick one or more accounts to see risk signals.</div>';
            return;
        }
        if (!activeGameIds.length) {
            host.innerHTML = '<div class="empty-row" style="grid-column:1/-1;">No selected accounts match the current filters.</div>';
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
        const pointRows = this._datapointRows();
        meta.textContent = `${rows.length} account row(s) - ${pointRows.length} datapoint row(s)`;
        const summaryTable = `<div class="table-section-title">Account Summary</div><table><thead><tr><th onclick="ReportPage.sortBy('lord_name')">Account ${this._sortIndicator('lord_name')}</th><th onclick="ReportPage.sortBy('game_id')">Game ID ${this._sortIndicator('game_id')}</th><th onclick="ReportPage.sortBy('latest')">${this._esc(this._metricLabel())} ${this._sortIndicator('latest')}</th><th onclick="ReportPage.sortBy('growth_pct_in_range')">Growth % ${this._sortIndicator('growth_pct_in_range')}</th><th onclick="ReportPage.sortBy('growth_rate_per_day')">Velocity/Day ${this._sortIndicator('growth_rate_per_day')}</th><th onclick="ReportPage.sortBy('data_freshness_seconds')">Freshness ${this._sortIndicator('data_freshness_seconds')}</th><th onclick="ReportPage.sortBy('data_completeness_ratio')">Coverage ${this._sortIndicator('data_completeness_ratio')}</th><th onclick="ReportPage.sortBy('risk_level')">Risk ${this._sortIndicator('risk_level')}</th><th onclick="ReportPage.sortBy('target_gap_pct')">Target Gap % ${this._sortIndicator('target_gap_pct')}</th><th onclick="ReportPage.sortBy('eta_to_target')">ETA ${this._sortIndicator('eta_to_target')}</th><th onclick="ReportPage.sortBy('quality_flags')">Quality ${this._sortIndicator('quality_flags')}</th><th>Fix Latest</th></tr></thead><tbody>${rows.length ? rows.map((row) => `<tr><td>${this._esc(row.lord_name)}</td><td>${this._esc(row.game_id)}</td><td><strong>${this._esc(this._num(row.latest))}</strong></td><td class="${row.growth_pct_in_range > 0 ? 'delta-up' : row.growth_pct_in_range < 0 ? 'delta-down' : 'delta-flat'}">${this._esc(this._pct(row.growth_pct_in_range))}</td><td class="${row.growth_rate_per_day > 0 ? 'delta-up' : row.growth_rate_per_day < 0 ? 'delta-down' : 'delta-flat'}">${this._esc(this._delta(row.growth_rate_per_day))}</td><td>${this._esc(this._hours(row.data_freshness_seconds))}</td><td>${Number.isFinite(row.data_completeness_ratio) ? `${Math.round(row.data_completeness_ratio * 100)}%` : '--'}</td><td>${this._riskBadge(row.risk_level)}</td><td>${this._esc(this._pct(row.target_gap_pct))}</td><td>${Number.isFinite(row.eta_to_target) ? this._esc(this._hours(row.eta_to_target)) : '--'}</td><td>${(row.quality_flags || []).map((flag) => this._qualityBadge(flag)).join('') || '<span style="color:var(--muted-foreground);">--</span>'}</td><td>${row.latest_point?.editable ? `<button class="mini-action" type="button" onclick="ReportPage.openLatestDatapointEditor(decodeURIComponent('${encodeURIComponent(row.game_id)}'))">Edit</button>` : '<span style="color:var(--muted-foreground);">--</span>'}</td></tr>`).join('') : '<tr><td class="empty-row" colspan="12">No analyst rows for the current filter.</td></tr>'}</tbody></table>`;
        const pointTable = `<div class="table-section-title">Source Datapoints</div><table><thead><tr><th>Time</th><th>Account</th><th>Game ID</th><th>${this._esc(this._metricLabel())}</th><th>Source Value</th><th>Delta</th><th>Snapshot</th><th>Source</th><th>Fix</th></tr></thead><tbody>${pointRows.length ? pointRows.map((row) => `<tr><td>${this._esc(this._dt(row.timestamp))}</td><td>${this._esc(row.lord_name)}</td><td>${this._esc(row.game_id)}</td><td><strong>${this._esc(this._num(row.value, row.metric))}</strong></td><td>${this._esc(this._num(row.source_value, row.metric))}</td><td class="${row.delta > 0 ? 'delta-up' : row.delta < 0 ? 'delta-down' : 'delta-flat'}">${row.delta == null ? '--' : this._esc(this._delta(row.delta, row.metric))}</td><td>${row.snapshot_id ? `#${this._esc(row.snapshot_id)}` : '--'}</td><td>${this._esc(row.aggregation_note ? 'bucket last snapshot' : (row.source || '--'))}</td><td>${row.editable ? `<button class="mini-action" type="button" onclick="ReportPage.openDatapointEditor({snapshot_id:${Number(row.snapshot_id)},game_id:decodeURIComponent('${encodeURIComponent(row.game_id)}'),lord_name:decodeURIComponent('${encodeURIComponent(row.lord_name)}'),metric:'${this._esc(row.metric)}',source:'${this._esc(row.source || '')}',timestampLabel:'${this._esc(row.timestamp)}',timestamp:'${this._esc(row.timestamp)}',value:${Number(row.value) || 0},source_value:${Number(row.source_value) || 0},aggregation_note:decodeURIComponent('${encodeURIComponent(row.aggregation_note || '')}'),editable:true})">Edit</button>` : '<span style="color:var(--muted-foreground);">--</span>'}</td></tr>`).join('') : '<tr><td class="empty-row" colspan="9">No datapoints for the current filter.</td></tr>'}</tbody></table>`;
        host.innerHTML = `${summaryTable}<div class="table-subsection">${pointTable}</div>`;
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

    _visibleWorkflowSeries() {
        return (this._workflowChartData.series || []).filter((series) => !this._workflowLegendHidden[series.game_id]);
    },

    _buildWorkflowChartCache() {
        const geom = { width: 1200, height: 360, left: 72, right: 24, top: 32, bottom: 40 };
        const innerWidth = geom.width - geom.left - geom.right;
        const innerHeight = geom.height - geom.top - geom.bottom;
        const visible = this._visibleWorkflowSeries().map((series, index) => ({ ...series, color: this._palette[index % this._palette.length] }));
        const allPoints = visible.flatMap((series) => series.points || []);
        if (!allPoints.length) return { geom, series: [], xTicks: [], yTicks: [], hoverPoints: [] };
        const timestamps = allPoints.map((point) => new Date(point.timestamp).getTime()).filter(Number.isFinite);
        const values = allPoints.map((point) => Number(point.value || 0)).filter(Number.isFinite);
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
                return { x: sx(timestamp), y: sy(value), timestamp, timestampLabel: point.timestamp, value, color: item.color, game_id: item.game_id, lord_name: item.lord_name || item.game_id, delta: index > 0 ? value - Number(source[index - 1].value || 0) : null };
            }).filter(Boolean);
            return { ...item, pointsChart: points, path: points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' ') };
        });
        const xTicks = Array.from({ length: 5 }, (_, index) => {
            const ratio = index / 4;
            return { x: geom.left + innerWidth * ratio, label: this._dt(minTs + (maxTs - minTs) * ratio, { mode: this._timezoneMode }) };
        });
        const yTicks = Array.from({ length: 5 }, (_, index) => {
            const ratio = index / 4;
            return { y: geom.top + innerHeight * ratio, value: maxVal - (maxVal - minVal) * ratio };
        });
        return { geom, series, xTicks, yTicks, hoverPoints: series.flatMap((item) => item.pointsChart || []) };
    },

    _workflowValueLabel(value) {
        if (this._selectedWorkflowMetric === 'success_rate') return this._pct(value);
        if (this._selectedWorkflowMetric.includes('duration')) return this._hours(Number(value || 0) / 1000);
        if (this._selectedWorkflowMetric === 'attempts_avg') return Number.isFinite(Number(value)) ? Number(value).toFixed(2) : '--';
        return this._num(value);
    },

    _workflowRows() {
        return (this._workflowChartData.series || []).map((series) => {
            const derived = series.derived_summary || {};
            return {
                game_id: series.game_id,
                lord_name: series.lord_name || series.game_id,
                latest: Number(series.summary?.latest),
                run_count: Number(derived.run_count),
                success_rate: Number(derived.success_rate),
                fail_count: Number(derived.fail_count),
                avg_duration_ms: Number(derived.avg_duration_ms),
                total_duration_ms: Number(derived.total_duration_ms),
                attempts_avg: Number(derived.attempts_avg),
                data_freshness_seconds: Number(derived.data_freshness_seconds),
                data_completeness_ratio: Number(derived.data_completeness_ratio),
                risk_level: String(derived.risk_level || 'healthy'),
                quality_flags: Array.isArray(series.quality_flags) ? series.quality_flags : [],
            };
        });
    },

    _sortedWorkflowRows() {
        const rows = this._workflowRows();
        const dir = this._workflowSortDirection === 'desc' ? -1 : 1;
        return rows.sort((a, b) => {
            const av = this._sortValue(a, this._workflowSortField);
            const bv = this._sortValue(b, this._workflowSortField);
            if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
            return String(av || '').localeCompare(String(bv || '')) * dir;
        });
    },

    _datapointRows() {
        return (this._chartData.series || []).flatMap((series) => (series.points || []).map((point, index, source) => {
            const value = Number(point.value || 0);
            const prevValue = index > 0 ? Number(source[index - 1].value || 0) : null;
            return {
                game_id: series.game_id,
                lord_name: series.lord_name || series.game_id,
                timestamp: point.timestamp,
                value,
                source_value: Number(point.source_value ?? point.value ?? 0),
                delta: prevValue == null ? null : value - prevValue,
                snapshot_id: point.snapshot_id,
                source: point.source,
                metric: point.metric || this._selectedMetric,
                editable: !!point.editable,
                aggregation_note: point.aggregation_note || '',
            };
        })).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    },

    _renderWorkflowSummarySection() {
        const host = document.getElementById('workflow-summary-grid');
        if (!host) return;
        const visible = this._visibleWorkflowSeries();
        const runTotal = visible.reduce((sum, item) => sum + Number(item.derived_summary?.run_count || 0), 0);
        const failTotal = visible.reduce((sum, item) => sum + Number(item.derived_summary?.fail_count || 0), 0);
        const avgSuccessRate = visible.length ? visible.reduce((sum, item) => sum + Number(item.derived_summary?.success_rate || 0), 0) / visible.length : null;
        const avgDuration = visible.length ? visible.reduce((sum, item) => sum + Number(item.derived_summary?.avg_duration_ms || 0), 0) / visible.length : null;
        const newestRun = visible.map((item) => item.derived_summary?.last_activity_at).filter(Boolean).sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];
        const cards = [
            ['Runs In Range', this._num(runTotal), `${visible.length} visible account(s)`],
            ['Success Rate', avgSuccessRate != null ? this._pct(avgSuccessRate) : '--', failTotal ? `${failTotal} failed runs` : 'No failures'],
            ['Avg Duration', avgDuration != null ? this._hours(avgDuration / 1000) : '--', this._workflowMetricLabel()],
            ['Latest Workflow Run', newestRun ? this._dt(newestRun) : '--', this._workflowChartData.activity?.name || 'No workflow selected'],
        ];
        host.innerHTML = cards.map(([label, value, note]) => `<div class="panel summary-card"><div class="summary-label">${this._esc(label)}</div><div class="summary-value">${this._esc(value)}</div><div class="summary-note">${this._esc(note)}</div></div>`).join('');
    },

    _renderWorkflowChartSection() {
        const host = document.getElementById('workflow-chart-host');
        const title = document.getElementById('workflow-chart-title');
        const subtitle = document.getElementById('workflow-chart-subtitle');
        const activeGameIds = this._activeSelectedGameIds();
        if (title) title.textContent = `${this._workflowChartData.activity?.name || 'Workflow'} · ${this._workflowMetricLabel()}`;
        if (subtitle) subtitle.textContent = `Bucket ${this._selectedBucket.toUpperCase()} · Aggregation ${this._selectedWorkflowAggregation.toUpperCase()} · Range ${this._selectedRangePreset.toUpperCase()} · Timezone ${this._timezoneMode.toUpperCase()}`;
        if (!host) return;
        this._workflowChartCache = this._buildWorkflowChartCache();
        const legend = document.getElementById('workflow-legend');
        if (legend) legend.innerHTML = (this._workflowChartCache.series || []).map((item) => {
            const hiddenClass = this._workflowLegendHidden[item.game_id] ? ' legend-hidden' : '';
            return `<button type="button" class="btn legend-btn${hiddenClass}" onclick="ReportPage.toggleWorkflowLegend('${this._esc(item.game_id)}')"><span class="legend-dot" style="background:${item.color};"></span><div><div>${this._esc(item.lord_name || item.game_id)}</div><div class="legend-meta">${this._riskBadge(item.derived_summary?.risk_level || 'healthy')}${(item.quality_flags || []).map((flag) => this._qualityBadge(flag)).join('')}</div></div></button>`;
        }).join('');
        if (this._loadingChart && this._activeTab === 'workflow') {
            host.innerHTML = `<div class="chart-empty"><div><span class="spinner"></span><div style="margin-top:10px;">Loading workflow analytics…</div></div></div>`;
            return;
        }
        if (!this._selectedGameIds.length) { host.innerHTML = `<div class="chart-empty">Choose one or more accounts to build workflow analytics.</div>`; return; }
        if (!activeGameIds.length) { host.innerHTML = `<div class="chart-empty">No selected accounts match the current group/runtime/provider filters.</div>`; return; }
        if (!this._selectedWorkflowActivityId) { host.innerHTML = `<div class="chart-empty">Choose a workflow activity first.</div>`; return; }
        if (!(this._workflowChartCache.series || []).some((series) => (series.pointsChart || []).length)) { host.innerHTML = `<div class="chart-empty">No workflow data points found for the current filter.</div>`; return; }
        host.innerHTML = `<svg id="workflow-chart-svg" class="chart-svg" viewBox="0 0 ${this._workflowChartCache.geom.width} ${this._workflowChartCache.geom.height}" preserveAspectRatio="xMidYMid meet"><rect x="0" y="0" width="${this._workflowChartCache.geom.width}" height="${this._workflowChartCache.geom.height}" fill="transparent"></rect>${this._workflowChartCache.yTicks.map((tick) => `<g><line x1="${this._workflowChartCache.geom.left}" y1="${tick.y}" x2="${this._workflowChartCache.geom.width - this._workflowChartCache.geom.right}" y2="${tick.y}" stroke="rgba(148,163,184,.18)" stroke-dasharray="4 6"></line><text x="${this._workflowChartCache.geom.left - 12}" y="${tick.y + 4}" text-anchor="end" fill="#8fa2b8" font-size="11">${this._esc(this._workflowValueLabel(tick.value))}</text></g>`).join('')}${this._workflowChartCache.xTicks.map((tick) => `<g><line x1="${tick.x}" y1="${this._workflowChartCache.geom.top}" x2="${tick.x}" y2="${this._workflowChartCache.geom.height - this._workflowChartCache.geom.bottom}" stroke="rgba(148,163,184,.08)"></line><text x="${tick.x}" y="${this._workflowChartCache.geom.height - 14}" text-anchor="middle" fill="#8fa2b8" font-size="11">${this._esc(tick.label)}</text></g>`).join('')}<line x1="${this._workflowChartCache.geom.left}" y1="${this._workflowChartCache.geom.height - this._workflowChartCache.geom.bottom}" x2="${this._workflowChartCache.geom.width - this._workflowChartCache.geom.right}" y2="${this._workflowChartCache.geom.height - this._workflowChartCache.geom.bottom}" stroke="rgba(148,163,184,.18)"></line><line x1="${this._workflowChartCache.geom.left}" y1="${this._workflowChartCache.geom.top}" x2="${this._workflowChartCache.geom.left}" y2="${this._workflowChartCache.geom.height - this._workflowChartCache.geom.bottom}" stroke="rgba(148,163,184,.18)"></line>${this._workflowChartCache.series.map((series) => `<g><path d="${series.path}" fill="none" stroke="${series.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>${series.pointsChart.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="3.5" fill="${point.color}" stroke="#0b1118" stroke-width="2"></circle>`).join('')}</g>`).join('')}<line id="workflow-hover-line" x1="0" y1="${this._workflowChartCache.geom.top}" x2="0" y2="${this._workflowChartCache.geom.height - this._workflowChartCache.geom.bottom}" stroke="#63b3ed" stroke-width="1.5" stroke-dasharray="5 5" opacity="0"></line><circle id="workflow-hover-dot" cx="0" cy="0" r="6.5" fill="#63b3ed" stroke="#f8fafc" stroke-width="3" opacity="0"></circle></svg>`;
        const svg = document.getElementById('workflow-chart-svg');
        if (svg) { svg.onmousemove = (event) => this._handleWorkflowChartHover(event); svg.onmouseleave = () => this._hideWorkflowTooltip(); }
    },

    _handleWorkflowChartHover(event) {
        if (!this._workflowChartCache?.hoverPoints?.length) return;
        const svg = event.currentTarget;
        const rect = svg.getBoundingClientRect();
        const scaleX = rect.width / this._workflowChartCache.geom.width;
        const scaleY = rect.height / this._workflowChartCache.geom.height;
        const x = (event.clientX - rect.left) / scaleX;
        const y = (event.clientY - rect.top) / scaleY;
        let nearest = null;
        let score = Number.POSITIVE_INFINITY;
        this._workflowChartCache.hoverPoints.forEach((point) => {
            const nextScore = Math.abs(point.x - x) * 2 + Math.abs(point.y - y);
            if (nextScore < score) { score = nextScore; nearest = point; }
        });
        if (!nearest) return;
        const hoverLine = document.getElementById('workflow-hover-line');
        const hoverDot = document.getElementById('workflow-hover-dot');
        if (hoverLine) { hoverLine.setAttribute('x1', `${nearest.x}`); hoverLine.setAttribute('x2', `${nearest.x}`); hoverLine.setAttribute('stroke', nearest.color); hoverLine.setAttribute('opacity', '1'); }
        if (hoverDot) { hoverDot.setAttribute('cx', `${nearest.x}`); hoverDot.setAttribute('cy', `${nearest.y}`); hoverDot.setAttribute('fill', nearest.color); hoverDot.setAttribute('opacity', '1'); }
        const series = (this._workflowChartData.series || []).find((item) => item.game_id === nearest.game_id) || {};
        const tooltip = document.getElementById('workflow-tooltip');
        if (!tooltip) return;
        tooltip.innerHTML = `<div class="tooltip-title">${this._esc(this._dt(nearest.timestampLabel))}</div><div class="tooltip-main">${this._esc(nearest.lord_name || nearest.game_id)}</div><div class="tooltip-row"><span>${this._esc(this._workflowMetricLabel())}</span><strong>${this._esc(this._workflowValueLabel(nearest.value))}</strong></div><div class="tooltip-row"><span>Delta</span><strong class="${nearest.delta > 0 ? 'delta-up' : nearest.delta < 0 ? 'delta-down' : 'delta-flat'}">${this._esc(this._workflowValueLabel(nearest.delta))}</strong></div><div class="tooltip-row"><span>Success Rate</span><strong>${this._esc(this._pct(series.derived_summary?.success_rate))}</strong></div>`;
        const stageRect = svg.closest('.chart-stage')?.getBoundingClientRect() || rect;
        const offsetLeft = rect.left - stageRect.left;
        const offsetTop = rect.top - stageRect.top;
        tooltip.style.left = `${Math.min(Math.max(offsetLeft + (nearest.x * scaleX) + 20, 12), stageRect.width - 260)}px`;
        tooltip.style.top = `${Math.max(offsetTop + (nearest.y * scaleY) - 120, 12)}px`;
        tooltip.style.display = 'block';
    },

    _handleChartClick(event) {
        const result = this._nearestChartPoint(event);
        if (!result?.nearest?.editable) return;
        const hitRadius = 34;
        if (result.score <= hitRadius) this.openDatapointEditor(result.nearest);
    },

    _hideWorkflowTooltip() {
        const tooltip = document.getElementById('workflow-tooltip');
        const hoverLine = document.getElementById('workflow-hover-line');
        const hoverDot = document.getElementById('workflow-hover-dot');
        if (tooltip) tooltip.style.display = 'none';
        if (hoverLine) hoverLine.setAttribute('opacity', '0');
        if (hoverDot) hoverDot.setAttribute('opacity', '0');
    },

    _renderWorkflowRiskFeed() {
        const host = document.getElementById('workflow-risk-feed');
        if (!host) return;
        const activeGameIds = this._activeSelectedGameIds();
        if (!this._selectedGameIds.length) { host.innerHTML = '<div class="empty-row" style="grid-column:1/-1;">Pick one or more accounts to see workflow risk signals.</div>'; return; }
        if (!activeGameIds.length) { host.innerHTML = '<div class="empty-row" style="grid-column:1/-1;">No selected accounts match the current filters.</div>'; return; }
        const items = this._workflowChartData?.meta?.risk_feed || [];
        host.innerHTML = items.length ? items.map((item) => `<div class="risk-card"><div style="display:flex;align-items:center;justify-content:space-between;gap:8px;"><strong>${this._esc(item.lord_name || item.game_id)}</strong>${this._riskBadge(item.risk_level || 'medium')}</div><div style="font-size:12px;color:var(--muted-foreground);">${this._esc(item.game_id)}</div><div class="legend-meta">${(item.reasons || []).map((reason) => this._qualityBadge(reason)).join('')}</div><div style="font-size:12px;color:var(--muted-foreground);">${this._esc(item.recommended_action || '')}</div></div>`).join('') : '<div class="empty-row" style="grid-column:1/-1;">No workflow risk signals for the current view.</div>';
    },

    _renderWorkflowTableSection() {
        const host = document.getElementById('workflow-table-host');
        const meta = document.getElementById('workflow-table-meta');
        if (!host || !meta) return;
        const rows = this._sortedWorkflowRows();
        meta.textContent = `${rows.length} row(s)`;
        host.innerHTML = `<table><thead><tr><th onclick="ReportPage.sortWorkflowBy('lord_name')">Account ${this._workflowSortIndicator('lord_name')}</th><th onclick="ReportPage.sortWorkflowBy('game_id')">Game ID ${this._workflowSortIndicator('game_id')}</th><th onclick="ReportPage.sortWorkflowBy('run_count')">Runs ${this._workflowSortIndicator('run_count')}</th><th onclick="ReportPage.sortWorkflowBy('success_rate')">Success Rate ${this._workflowSortIndicator('success_rate')}</th><th onclick="ReportPage.sortWorkflowBy('avg_duration_ms')">Avg Duration ${this._workflowSortIndicator('avg_duration_ms')}</th><th onclick="ReportPage.sortWorkflowBy('total_duration_ms')">Total Duration ${this._workflowSortIndicator('total_duration_ms')}</th><th onclick="ReportPage.sortWorkflowBy('attempts_avg')">Attempts Avg ${this._workflowSortIndicator('attempts_avg')}</th><th onclick="ReportPage.sortWorkflowBy('data_freshness_seconds')">Freshness ${this._workflowSortIndicator('data_freshness_seconds')}</th><th onclick="ReportPage.sortWorkflowBy('risk_level')">Risk ${this._workflowSortIndicator('risk_level')}</th><th onclick="ReportPage.sortWorkflowBy('quality_flags')">Quality ${this._workflowSortIndicator('quality_flags')}</th></tr></thead><tbody>${rows.length ? rows.map((row) => `<tr><td>${this._esc(row.lord_name)}</td><td>${this._esc(row.game_id)}</td><td><strong>${this._esc(this._num(row.run_count))}</strong></td><td class="${row.success_rate >= 80 ? 'delta-up' : row.success_rate < 50 ? 'delta-down' : 'delta-flat'}">${this._esc(this._pct(row.success_rate))}</td><td>${this._esc(this._hours(row.avg_duration_ms / 1000))}</td><td>${this._esc(this._hours(row.total_duration_ms / 1000))}</td><td>${Number.isFinite(row.attempts_avg) ? row.attempts_avg.toFixed(2) : '--'}</td><td>${this._esc(this._hours(row.data_freshness_seconds))}</td><td>${this._riskBadge(row.risk_level)}</td><td>${(row.quality_flags || []).map((flag) => this._qualityBadge(flag)).join('') || '<span style="color:var(--muted-foreground);">--</span>'}</td></tr>`).join('') : '<tr><td class="empty-row" colspan="10">No workflow rows for the current filter.</td></tr>'}</tbody></table>`;
    },

    _renderWorkflowDrilldown() {
        const host = document.getElementById('workflow-drilldown-host');
        if (!host) return;
        if (this._selectedGameIds.length !== 1) { host.innerHTML = '<div class="empty-row">Select exactly one account to unlock workflow drilldown.</div>'; return; }
        const gameId = this._selectedGameIds[0];
        const series = (this._workflowChartData.series || []).find((item) => item.game_id === gameId);
        if (!series) { host.innerHTML = '<div class="empty-row">No workflow data loaded for the selected account.</div>'; return; }
        const derived = series.derived_summary || {};
        const eventBlock = (this._workflowEventsData.items || []).find((item) => item.game_id === gameId);
        host.innerHTML = `<div class="drilldown"><div><div class="drill-grid"><div class="drill-tile"><div class="summary-label">Run Count</div><div class="drill-value">${this._esc(this._num(derived.run_count))}</div></div><div class="drill-tile"><div class="summary-label">Success Rate</div><div class="drill-value">${this._esc(this._pct(derived.success_rate))}</div></div><div class="drill-tile"><div class="summary-label">Avg Duration</div><div class="drill-value">${this._esc(this._hours(derived.avg_duration_ms / 1000))}</div></div><div class="drill-tile"><div class="summary-label">Total Duration</div><div class="drill-value">${this._esc(this._hours(derived.total_duration_ms / 1000))}</div></div><div class="drill-tile"><div class="summary-label">Fail Count</div><div class="drill-value">${this._esc(this._num(derived.fail_count))}</div></div><div class="drill-tile"><div class="summary-label">Attempts Avg</div><div class="drill-value">${Number.isFinite(derived.attempts_avg) ? derived.attempts_avg.toFixed(2) : '--'}</div></div></div><div class="drill-tile" style="margin-top:12px;"><div class="summary-label">Workflow Status</div><div class="legend-meta" style="margin-top:8px;">${this._riskBadge(derived.risk_level || 'healthy')}${(series.quality_flags || []).map((flag) => this._qualityBadge(flag)).join('')}</div><div style="margin-top:12px;color:var(--muted-foreground);font-size:12px;">Last workflow run ${this._esc(this._dt(derived.last_activity_at))}</div></div></div><div class="drill-tile"><div class="summary-label">Run Timeline</div><div class="timeline">${(eventBlock?.events || []).slice().reverse().slice(0, 12).map((event) => `<div class="timeline-item"><div><div>${this._esc(event.label || 'Workflow')}</div><div style="font-size:11px;color:var(--muted-foreground);">${this._esc(event.status || '--')}</div></div><div style="text-align:right;"><div style="font-size:12px;">${this._esc(this._dt(event.timestamp))}</div><div style="font-size:11px;color:${event.status === 'FAILED' ? 'var(--red-600)' : 'var(--emerald-600)'};">${this._esc(event.error_message || '')}</div></div></div>`).join('') || '<div class="empty-row">No workflow runs in the selected range.</div>'}</div></div></div>`;
    },

    _renderFarmingDailyChart() {
        const host = document.getElementById('farming-chart-host');
        const subtitle = document.getElementById('farming-chart-subtitle');
        if (!host) return;
        const { from, to } = this._rangeBounds();
        const days = [];
        if (Number.isFinite(from.getTime()) && Number.isFinite(to.getTime())) {
            const cursor = new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), from.getUTCDate()));
            const end = new Date(Date.UTC(to.getUTCFullYear(), to.getUTCMonth(), to.getUTCDate()));
            while (cursor <= end) {
                days.push(cursor.toISOString().slice(0, 10));
                cursor.setUTCDate(cursor.getUTCDate() + 1);
            }
        }
        const seriesMap = new Map();
        (this._farmingData || []).forEach((row) => {
            (row.daily_series || []).forEach((item) => {
                const current = seriesMap.get(item.date) || {
                    date: item.date,
                    total_gathers: 0,
                    successful_gathers: 0,
                    failed_gathers: 0,
                    center_gathers: 0,
                    world_gathers: 0,
                };
                current.total_gathers += Number(item.total_gathers || 0);
                current.successful_gathers += Number(item.successful_gathers || 0);
                current.failed_gathers += Number(item.failed_gathers || 0);
                current.center_gathers += Number(item.center_gathers || 0);
                current.world_gathers += Number(item.world_gathers || 0);
                seriesMap.set(item.date, current);
            });
        });
        const dailyRows = (days.length ? days : [...seriesMap.keys()].sort()).map((date) => seriesMap.get(date) || {
            date,
            total_gathers: 0,
            successful_gathers: 0,
            failed_gathers: 0,
            center_gathers: 0,
            world_gathers: 0,
        });
        if (subtitle) subtitle.textContent = dailyRows.length
            ? `${dailyRows.length} day(s) - ${this._activeSelectedGameIds().length} active account(s)`
            : 'Daily execution trend across the currently selected accounts.';
        if (!this._selectedGameIds.length) {
            host.innerHTML = '<div class="chart-empty">Choose one or more accounts to see daily gathering frequency.</div>';
            return;
        }
        if (!this._activeSelectedGameIds().length) {
            host.innerHTML = '<div class="chart-empty">No selected accounts match the current group/runtime/provider filters.</div>';
            return;
        }
        if (!dailyRows.length) {
            host.innerHTML = '<div class="chart-empty">No daily gathering activity in the selected range.</div>';
            return;
        }
        const totalRuns = dailyRows.reduce((sum, item) => sum + Number(item.total_gathers || 0), 0);
        const totalSuccess = dailyRows.reduce((sum, item) => sum + Number(item.successful_gathers || 0), 0);
        const totalCenter = dailyRows.reduce((sum, item) => sum + Number(item.center_gathers || 0), 0);
        const activeDays = dailyRows.filter((item) => Number(item.total_gathers || 0) > 0).length;
        const peakDay = dailyRows.reduce((best, item) => Number(item.total_gathers || 0) > Number(best?.total_gathers || -1) ? item : best, null);
        const successPct = totalRuns ? (totalSuccess / totalRuns) * 100 : 0;
        const centerPct = totalRuns ? (totalCenter / totalRuns) * 100 : 0;
        const width = 1200;
        const height = 350;
        const left = 56;
        const right = 24;
        const top = 28;
        const bottom = 58;
        const innerWidth = width - left - right;
        const innerHeight = height - top - bottom;
        const maxValue = Math.max(...dailyRows.map((item) => Number(item.total_gathers || 0)), 1);
        const barWidth = Math.max(12, Math.min(44, innerWidth / Math.max(dailyRows.length, 1) - 8));
        const step = dailyRows.length > 1 ? innerWidth / dailyRows.length : innerWidth / 2;
        const yTicks = Array.from({ length: 5 }, (_, index) => {
            const ratio = index / 4;
            return { y: top + innerHeight * ratio, value: maxValue - maxValue * ratio };
        });
        const linePoints = dailyRows.map((item, index) => {
            const centerValue = Number(item.center_gathers || 0);
            const x = left + step * index + step / 2;
            const y = top + innerHeight - ((centerValue / maxValue) * innerHeight);
            return { x, y, value: centerValue };
        });
        const linePath = linePoints.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' ');
        host.innerHTML = `
        <div class="farming-daily-kpis">
            <div class="farming-daily-kpi tone-blue">
                <div class="farming-daily-label">Total Runs</div>
                <div class="farming-daily-value">${this._esc(this._num(totalRuns))}</div>
                <div class="farming-daily-note">${activeDays}/${dailyRows.length} active day(s)</div>
            </div>
            <div class="farming-daily-kpi tone-green">
                <div class="farming-daily-label">Success Rate</div>
                <div class="farming-daily-value">${this._esc(this._pct(successPct))}</div>
                <div class="farming-daily-note">${this._esc(this._num(totalSuccess))} successful runs</div>
            </div>
            <div class="farming-daily-kpi tone-amber">
                <div class="farming-daily-label">RSS Center Share</div>
                <div class="farming-daily-value">${this._esc(this._pct(centerPct))}</div>
                <div class="farming-daily-note">${this._esc(this._num(totalCenter))} center missions</div>
            </div>
            <div class="farming-daily-kpi tone-indigo">
                <div class="farming-daily-label">Peak Day</div>
                <div class="farming-daily-value">${this._esc(this._num(peakDay?.total_gathers || 0))}</div>
                <div class="farming-daily-note">${this._esc(peakDay ? this._dt(`${peakDay.date}T00:00:00Z`, { mode: this._timezoneMode }).split(',')[0] : '--')}</div>
            </div>
        </div>
        <div class="farming-daily-legend">
            <span><span class="legend-dot" style="background:rgba(16,185,129,.95);"></span>Successful runs</span>
            <span><span class="legend-dot" style="background:rgba(239,68,68,.95);"></span>Failed runs</span>
            <span><span class="legend-dot" style="background:rgba(245,158,11,.95);"></span>RSS Center trend</span>
        </div>
        <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
            <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"></rect>
            ${yTicks.map((tick) => `<g><line x1="${left}" y1="${tick.y}" x2="${width - right}" y2="${tick.y}" stroke="rgba(148,163,184,.18)" stroke-dasharray="4 6"></line><text x="${left - 10}" y="${tick.y + 4}" text-anchor="end" fill="hsl(215, 16%, 47%)" font-size="11">${this._esc(this._num(tick.value))}</text></g>`).join('')}
            <line x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}" stroke="rgba(148,163,184,.18)"></line>
            <path d="${linePath}" fill="none" stroke="rgba(245,158,11,.9)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>
            ${dailyRows.map((item, index) => {
                const total = Number(item.total_gathers || 0);
                const success = Number(item.successful_gathers || 0);
                const failed = Number(item.failed_gathers || 0);
                const center = Number(item.center_gathers || 0);
                const x = left + step * index + (step - barWidth) / 2;
                const barHeight = (total / maxValue) * innerHeight;
                const y = top + innerHeight - barHeight;
                const successHeight = total > 0 ? (success / total) * barHeight : 0;
                const failedHeight = total > 0 ? (failed / total) * barHeight : 0;
                const successY = top + innerHeight - successHeight;
                const failedY = successY - failedHeight;
                const label = this._dt(`${item.date}T00:00:00Z`, { mode: this._timezoneMode }).split(',')[0];
                const linePoint = linePoints[index];
                return `<g>
                    <title>${this._esc(label)}: ${this._esc(String(total))} total, ${this._esc(String(success))} success, ${this._esc(String(failed))} failed, ${this._esc(String(center))} RSS Center</title>
                    <rect x="${x}" y="${top}" width="${barWidth}" height="${innerHeight}" rx="12" fill="rgba(148,163,184,.06)"></rect>
                    ${successHeight > 0 ? `<rect x="${x}" y="${successY}" width="${barWidth}" height="${successHeight}" rx="10" fill="url(#farmingSuccessGradient)"></rect>` : ''}
                    ${failedHeight > 0 ? `<rect x="${x}" y="${failedY}" width="${barWidth}" height="${failedHeight}" rx="10" fill="rgba(239,68,68,.88)"></rect>` : ''}
                    ${total === 0 ? `<line x1="${x + 4}" y1="${height - bottom - 2}" x2="${x + barWidth - 4}" y2="${height - bottom - 2}" stroke="rgba(148,163,184,.45)" stroke-width="3" stroke-linecap="round"></line>` : ''}
                    <circle cx="${linePoint.x}" cy="${linePoint.y}" r="5" fill="rgba(245,158,11,.98)" stroke="white" stroke-width="2"></circle>
                    <text x="${x + barWidth / 2}" y="${Math.max(y - 10, top + 10)}" text-anchor="middle" fill="${total > 0 ? 'hsl(215, 25%, 35%)' : 'rgba(148,163,184,.7)'}" font-size="11" font-weight="700">${this._esc(String(total))}</text>
                    <text x="${x + barWidth / 2}" y="${height - 20}" text-anchor="middle" fill="hsl(215, 16%, 47%)" font-size="10">${this._esc(label)}</text>
                    ${center > 0 ? `<text x="${linePoint.x}" y="${Math.max(linePoint.y - 10, top + 10)}" text-anchor="middle" fill="rgba(180,83,9,.92)" font-size="10" font-weight="700">${this._esc(String(center))}</text>` : ''}
                </g>`;
            }).join('')}
            <defs>
                <linearGradient id="farmingSuccessGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="rgba(20,184,166,.92)"></stop>
                    <stop offset="100%" stop-color="rgba(134,239,172,.9)"></stop>
                </linearGradient>
            </defs>
        </svg>
        `;
    },

    _applyTabState() {
        document.getElementById('tab-btn-growth')?.classList.toggle('active', this._activeTab === 'growth');
        document.getElementById('tab-btn-workflow')?.classList.toggle('active', this._activeTab === 'workflow');
        document.getElementById('tab-btn-farming')?.classList.toggle('active', this._activeTab === 'farming');
        const tabGrowth = document.getElementById('tab-growth');
        const tabWorkflow = document.getElementById('tab-workflow');
        const tabFarming = document.getElementById('tab-farming');
        if (tabGrowth) tabGrowth.style.display = this._activeTab === 'growth' ? 'block' : 'none';
        if (tabWorkflow) tabWorkflow.style.display = this._activeTab === 'workflow' ? 'block' : 'none';
        if (tabFarming) tabFarming.style.display = this._activeTab === 'farming' ? 'block' : 'none';
    },

    _refreshUI() {
        this._persistPreferences();
        this._applyTabState();
        this._renderControls();
        this._renderSummarySection();
        this._renderChartSection();
        this._renderRiskFeed();
        this._renderTableSection();
        this._renderDrilldown();
        this._renderWorkflowSummarySection();
        this._renderWorkflowChartSection();
        this._renderWorkflowRiskFeed();
        this._renderWorkflowTableSection();
        this._renderWorkflowDrilldown();
        this._renderFarmingDailyChart();
        this._renderPointEditor();
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

    async loadWorkflowActivities() {
        try {
            const response = await API.getWorkflowActivityRegistry();
            const rawActivities = Array.isArray(response)
                ? response
                : Array.isArray(response?.data)
                    ? response.data
                    : response?.data && typeof response.data === 'object'
                        ? Object.values(response.data)
                        : response && typeof response === 'object'
                            ? Object.values(response)
                            : [];
            this._workflowActivities = rawActivities.filter((item) => item?.id && item?.name);
            const hasSelected = this._workflowActivities.some((item) => item.id === this._selectedWorkflowActivityId);
            if (!hasSelected) this._selectedWorkflowActivityId = this._workflowActivities[0]?.id || '';
        } catch (error) {
            this._workflowActivities = [];
            this._selectedWorkflowActivityId = '';
            this._error = error?.message || 'Failed to load workflow activities';
        } finally {
            this._renderControls();
        }
    },

    async loadChartData() {
        const activeGameIds = this._activeSelectedGameIds();
        if (!activeGameIds.length) {
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
                gameIds: activeGameIds,
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
            this._eventsData = await API.getReportAccountEvents({ gameIds: activeGameIds, from: from.toISOString(), to: to.toISOString() });
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

    async loadWorkflowData() {
        const activeGameIds = this._activeSelectedGameIds();
        if (!activeGameIds.length || !this._selectedWorkflowActivityId) {
            this._workflowChartData = {
                metric: this._selectedWorkflowMetric,
                bucket: this._selectedBucket,
                aggregation: this._selectedWorkflowAggregation,
                range: null,
                series: [],
                meta: {},
                activity: null,
            };
            this._workflowEventsData = { items: [] };
            this._workflowLegendHidden = {};
            this._refreshUI();
            return;
        }
        const { from, to } = this._rangeBounds();
        if (!Number.isFinite(from.getTime()) || !Number.isFinite(to.getTime()) || from >= to) {
            this._error = 'Invalid date range';
            this._workflowChartData = {
                metric: this._selectedWorkflowMetric,
                bucket: this._selectedBucket,
                aggregation: this._selectedWorkflowAggregation,
                range: null,
                series: [],
                meta: {},
                activity: null,
            };
            this._workflowEventsData = { items: [] };
            this._refreshUI();
            return;
        }
        this._loadingChart = true;
        this._error = '';
        const requestId = ++this._workflowLoadRequestId;
        this._refreshUI();
        try {
            const chartData = await API.getReportWorkflowTimeseries({
                gameIds: activeGameIds,
                activityId: this._selectedWorkflowActivityId,
                metric: this._selectedWorkflowMetric,
                from: from.toISOString(),
                to: to.toISOString(),
                bucket: this._selectedBucket,
                aggregation: this._selectedWorkflowAggregation,
            });
            if (requestId !== this._workflowLoadRequestId) return;
            this._workflowChartData = chartData || {
                metric: this._selectedWorkflowMetric,
                bucket: this._selectedBucket,
                aggregation: this._selectedWorkflowAggregation,
                range: null,
                series: [],
                meta: {},
                activity: null,
            };
            this._workflowEventsData = await API.getReportAccountEventsFiltered({
                gameIds: activeGameIds,
                from: from.toISOString(),
                to: to.toISOString(),
                activityId: this._selectedWorkflowActivityId,
            });
            if (requestId !== this._workflowLoadRequestId) return;
            this._normalizeWorkflowLegendState();
            this._lastLoadedAt = new Date().toISOString();
        } catch (error) {
            if (requestId !== this._workflowLoadRequestId) return;
            this._workflowChartData = {
                metric: this._selectedWorkflowMetric,
                bucket: this._selectedBucket,
                aggregation: this._selectedWorkflowAggregation,
                range: null,
                series: [],
                meta: {},
                activity: null,
            };
            this._workflowEventsData = { items: [] };
            this._error = error.message || 'Failed to load workflow analytics';
        } finally {
            if (requestId === this._workflowLoadRequestId) {
                this._loadingChart = false;
                this._refreshUI();
            }
        }
    },

    async reloadChart() {
        if (this._activeTab === 'workflow') {
            await this.loadWorkflowData();
            return;
        }
        if (this._activeTab === 'farming') {
            await this.loadFarmingData();
            return;
        }
        await this.loadChartData();
    },

    _reloadActiveTab() {
        if (this._activeTab === 'workflow') return this.loadWorkflowData();
        if (this._activeTab === 'farming') return this.loadFarmingData();
        return this.loadChartData();
    },
    
    switchTab(tabId) {
        if (this._activeTab === tabId) return;
        this._activeTab = tabId;
        this._refreshUI();
        // Load data if needed
        if (tabId === 'farming') {
            this.loadFarmingData();
        } else if (tabId === 'workflow') {
            this.loadWorkflowData();
        } else {
            this.loadChartData();
        }
    },
    
    async loadFarmingData() {
        const activeGameIds = this._activeSelectedGameIds();
        if (!activeGameIds.length) {
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
            game_ids: activeGameIds.join(','),
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
            const uniqueDays = new Set(this._farmingData.flatMap((row) => (row.daily_series || []).map((item) => item.date))).size;
            
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
            const dailyAvg = uniqueDays ? (totalGathers / uniqueDays).toFixed(1) : '0';

            const cards = [
                ['Total Gathering Missions', this._num(totalGathers), `${this._num(totalCenter)} from RSS Center`],
                ['Farming Activity', this._farmingData.filter(d => d.total_gathers > 0).length, `Active farming accounts`],
                ['Most Mined Resource', totalGathers ? topRss.l : '--', totalGathers ? `${this._num(topRss.v)} missions` : 'Insufficient data'],
                ['Avg Frequency / Day', totalGathers ? dailyAvg : '--', uniqueDays ? `${uniqueDays} tracked day(s)` : 'No day buckets'],
                ['Avg Mission Duration', totalGathers ? `${avgDurHours}h` : '--', 'Time per gathering task']
            ];
            
            const icons = [
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>',
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;opacity:.35;position:absolute;top:14px;right:16px;"><path d="M3 3v18h18"/><path d="M7 16l4-4 3 3 5-7"/></svg>',
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
    changeTargetGroup(groupId) { this._selectedGroupId = this._normalizeScopeId(groupId) || ''; this._accountSearch = ''; this._refreshUI(); this._reloadActiveTab(); },
    changeRuntimeFilter(value) { this._runtimeFilter = value || 'all'; this._refreshUI(); this._reloadActiveTab(); },
    changeProviderFilter(value) { this._providerFilter = value || 'all'; this._refreshUI(); this._reloadActiveTab(); },
    changeTimezoneMode(value) { this._timezoneMode = value || 'local'; this._refreshUI(); },
    changeTargetGrowth(value) { this._targetGrowthPct = value === '' ? '' : String(value); this._persistPreferences(); },
    changeTargetDue(value) { this._targetDueAt = value ? new Date(value).toISOString() : ''; this._persistPreferences(); },
    sortBy(field) { if (this._sortField === field) this._sortDirection = this._sortDirection === 'asc' ? 'desc' : 'asc'; else { this._sortField = field; this._sortDirection = 'desc'; } this._renderTableSection(); },
    toggleAccount(gameId, checked) { if (checked) { if (!this._selectedGameIds.includes(gameId)) this._selectedGameIds.push(gameId); } else { this._selectedGameIds = this._selectedGameIds.filter((value) => value !== gameId); delete this._legendHidden[gameId]; delete this._workflowLegendHidden[gameId]; } this._refreshUI(); this._restoreAccountSearchFocus(); this._reloadActiveTab(); },
    selectFirstAccounts(count) { this._selectedGameIds = this._filteredAccounts().slice(0, count).map((item) => item.game_id); this._legendHidden = {}; this._workflowLegendHidden = {}; this._refreshUI(); this._restoreAccountSearchFocus(); this._reloadActiveTab(); },
    selectVisibleAccounts() { this._selectedGameIds = this._filteredAccounts().map((item) => item.game_id); this._legendHidden = {}; this._workflowLegendHidden = {}; this._refreshUI(); this._restoreAccountSearchFocus(); this._reloadActiveTab(); },
    selectAllAccounts() { this._selectedGameIds = this._accounts.map((item) => item.game_id); this._legendHidden = {}; this._workflowLegendHidden = {}; this._refreshUI(); this._restoreAccountSearchFocus(); this._reloadActiveTab(); },
    clearSelectedAccounts() { this._selectedGameIds = []; this._legendHidden = {}; this._workflowLegendHidden = {}; this._chartData = { metric: this._selectedMetric, bucket: this._selectedBucket, aggregation: this._selectedAggregation, range: null, series: [], meta: {} }; this._eventsData = { items: [] }; this._workflowChartData = { metric: this._selectedWorkflowMetric, bucket: this._selectedBucket, aggregation: this._selectedWorkflowAggregation, range: null, series: [], meta: {}, activity: null }; this._workflowEventsData = { items: [] }; this._refreshUI(); this._restoreAccountSearchFocus(); },
    changeMetric(metric) { this._selectedMetric = metric; this.loadChartData(); },
    changeRangePreset(preset) { this._selectedRangePreset = preset; if (preset === 'custom' && !this._customFrom && !this._customTo) { const now = new Date(); this._customTo = now.toISOString(); this._customFrom = new Date(now.getTime() - 7 * 86400000).toISOString(); } this._refreshUI(); this._reloadActiveTab(); },
    changeCustomRange(side, value) { if (!value) return; const iso = new Date(value).toISOString(); if (side === 'from') this._customFrom = iso; if (side === 'to') this._customTo = iso; this._refreshUI(); this._reloadActiveTab(); },
    changeBucket(bucket) { this._selectedBucket = bucket; this._reloadActiveTab(); },
    changeAggregation(aggregation) { this._selectedAggregation = aggregation; this.loadChartData(); },
    toggleLegend(gameId) { this._legendHidden[gameId] = !this._legendHidden[gameId]; this._hideTooltip(); this._refreshUI(); },
    changeWorkflowActivity(value) { this._selectedWorkflowActivityId = value || ''; this._workflowLegendHidden = {}; this._refreshUI(); this.loadWorkflowData(); },
    changeWorkflowMetric(value) { this._selectedWorkflowMetric = value || 'run_count'; this.loadWorkflowData(); },
    changeWorkflowAggregation(value) { this._selectedWorkflowAggregation = value || 'sum'; this.loadWorkflowData(); },
    toggleWorkflowLegend(gameId) { this._workflowLegendHidden[gameId] = !this._workflowLegendHidden[gameId]; this._hideWorkflowTooltip(); this._refreshUI(); },
    sortWorkflowBy(field) { if (this._workflowSortField === field) this._workflowSortDirection = this._workflowSortDirection === 'asc' ? 'desc' : 'asc'; else { this._workflowSortField = field; this._workflowSortDirection = 'desc'; } this._renderWorkflowTableSection(); },

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
        const isWorkflow = this._activeTab === 'workflow';
        const isFarming = this._activeTab === 'farming';
        const rows = isWorkflow
            ? this._sortedWorkflowRows()
            : isFarming
                ? [...this._farmingData].sort((a, b) => Number(b.total_gathers || 0) - Number(a.total_gathers || 0))
                : this._sortedSummaryRows();
        const sanitize = (value) => String(value ?? '').replace(/,/g, '').replace(/"/g, '""');
        const csv = isWorkflow
            ? [['Account', 'Game ID', 'Runs', 'Success Rate', 'Avg Duration', 'Total Duration', 'Attempts Avg', 'Freshness', 'Risk', 'Flags'].join(',')]
                .concat(rows.map((row) => [
                    row.lord_name,
                    row.game_id,
                    this._num(row.run_count),
                    this._pct(row.success_rate),
                    this._hours(row.avg_duration_ms / 1000),
                    this._hours(row.total_duration_ms / 1000),
                    Number.isFinite(row.attempts_avg) ? row.attempts_avg.toFixed(2) : '--',
                    this._hours(row.data_freshness_seconds),
                    row.risk_level,
                    (row.quality_flags || []).join('|'),
                ].map((value) => `"${sanitize(value)}"`).join(','))).join('\n')
            : isFarming
                ? [['Account', 'Game ID', 'Total Gathers', 'RSS Center', 'World Gathers', 'Success Rate', 'Avg Duration', 'Last Active'].join(',')]
                    .concat(rows.map((row) => {
                        const account = this._accounts.find((item) => item.game_id === row.game_id) || {};
                        const avgDurationSeconds = Number(row.total_gathers) ? Number(row.total_duration_ms || 0) / Number(row.total_gathers) / 1000 : 0;
                        return [
                            account.lord_name || row.game_id,
                            row.game_id,
                            this._num(row.total_gathers),
                            this._num(row.center_gathers),
                            this._num(row.world_gathers),
                            `${Number(row.success_rate || 0).toFixed(1)}%`,
                            this._hours(avgDurationSeconds),
                            this._dt(row.last_gathered_at),
                        ].map((value) => `"${sanitize(value)}"`).join(',');
                    })).join('\n')
            : [['Account', 'Game ID', 'Metric', 'Growth %', 'Velocity/Day', 'Freshness', 'Coverage', 'Risk', 'Target Gap %', 'ETA', 'Flags'].join(',')]
                .concat(rows.map((row) => [
                    row.lord_name,
                    row.game_id,
                    this._num(row.latest),
                    this._pct(row.growth_pct_in_range),
                    this._delta(row.growth_rate_per_day),
                    this._hours(row.data_freshness_seconds),
                    row.data_completeness_ratio == null ? '--' : `${Math.round(row.data_completeness_ratio * 100)}%`,
                    row.risk_level,
                    this._pct(row.target_gap_pct),
                    Number.isFinite(row.eta_to_target) ? this._hours(row.eta_to_target) : '--',
                    (row.quality_flags || []).join('|'),
                ].map((value) => `"${sanitize(value)}"`).join(','))).join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = isWorkflow
            ? `workflow-report-${this._selectedWorkflowMetric}-${Date.now()}.csv`
            : isFarming
                ? `farming-report-${Date.now()}.csv`
            : `report-${this._selectedMetric}-${Date.now()}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    },

    async init() {
        this._loadPreferences();
        this._bindPersistentEvents();
        this._refreshUI();
        await this.loadAccounts();
        await this.loadGroups();
        await this.loadWorkflowActivities();
        if (this._selectedGameIds.length) {
            if (this._activeTab === 'workflow') await this.loadWorkflowData();
            else if (this._activeTab === 'farming') await this.loadFarmingData();
            else await this.loadChartData();
        }
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
