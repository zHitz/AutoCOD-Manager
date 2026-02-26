/**
 * History Page — Clean table layout.
 */
const HistoryPage = {
    render() {
        return `
            <div class="page-enter">
                <div class="page-header">
                    <div class="page-header-info">
                        <h2>History & Logs</h2>
                        <p>View past task execution results and scan data.</p>
                    </div>
                    <div class="page-actions">
                        <button class="btn btn-outline btn-sm" onclick="HistoryPage.load()">
                            <svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Refresh
                        </button>
                    </div>
                </div>

                <div class="card" style="overflow:hidden">
                    <div style="overflow-x:auto">
                        <table class="history-table" id="history-table">
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>Device</th>
                                    <th>Task</th>
                                    <th>Status</th>
                                    <th>Duration</th>
                                    <th>Reliable</th>
                                    <th>Details</th>
                                </tr>
                            </thead>
                            <tbody id="history-body">
                                <tr>
                                    <td colspan="7" style="text-align:center;padding:48px;color:var(--muted-foreground)">
                                        <div class="spinner" style="margin:0 auto 8px"></div>
                                        Loading history...
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    },

    async init() { await this.load(); },
    destroy() { },

    async load() {
        try {
            const history = await API.getHistory(100);
            this.renderTable(history);
        } catch (e) {
            Toast.error('Error', 'Failed to load history');
        }
    },

    renderTable(items) {
        const tbody = document.getElementById('history-body');
        if (!tbody) return;

        if (!items || items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;padding:48px;color:var(--muted-foreground)">
                        <div class="empty-state-icon" style="margin:0 auto 16px;width:48px;height:48px">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:24px;height:24px"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                        </div>
                        <div class="font-medium">No task history yet</div>
                        <div class="text-sm" style="margin-top:4px">Run some scans to see results here.</div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = items.map(item => {
            const time = item.started_at
                ? new Date(item.started_at).toLocaleString()
                : (item.created_at || '--');
            const statusClass = item.status === 'SUCCESS' ? 'badge-success'
                : item.status === 'FAILED' ? 'badge-destructive'
                    : 'badge-secondary';
            const reliable = item.is_reliable
                ? '<span class="reliable">✓ Yes</span>'
                : '<span class="unreliable">⚠ No</span>';
            const duration = item.duration_ms
                ? `${(item.duration_ms / 1000).toFixed(1)}s`
                : '--';
            const details = item.data
                ? this.formatDetails(item.task_type, item.data)
                : (item.error || '--');

            return `
                <tr>
                    <td class="text-sm text-mono">${time}</td>
                    <td class="text-mono">${item.serial}</td>
                    <td><span class="badge badge-outline" style="text-transform:capitalize">${item.task_type}</span></td>
                    <td><span class="badge ${statusClass}">${item.status}</span></td>
                    <td class="text-mono">${duration}</td>
                    <td>${reliable}</td>
                    <td class="text-sm">${details}</td>
                </tr>
            `;
        }).join('');
    },

    formatDetails(type, data) {
        if (!data) return '--';
        try {
            if (type === 'profile') return `${data.name || '?'} | Power: ${DeviceCard.formatNum(data.power)}`;
            if (type === 'resources') {
                const g = data.gold?.total || 0;
                return `Gold: ${DeviceCard.formatNum(g)}`;
            }
            if (type === 'hall' || type === 'building') return `Level: ${data.level || '?'}`;
            if (type === 'pet') return `Token: ${data.token || '?'}`;
            return JSON.stringify(data).substring(0, 50);
        } catch (e) { return '--'; }
    },
};
