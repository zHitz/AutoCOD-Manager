/**
 * API Client + WebSocket Handler
 * Centralized communication layer for backend.
 */
const API = {
    BASE: '',

    async get(path) {
        const res = await fetch(`${this.BASE}${path}`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || err.detail || `HTTP Error ${res.status}: ${res.statusText}`);
        }
        return res.json();
    },

    async post(path, body = {}) {
        const res = await fetch(`${this.BASE}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || err.detail || `HTTP Error ${res.status}: ${res.statusText}`);
        }
        return res.json();
    },

    // ── Device endpoints ──
    getDevices() { return this.get('/api/devices'); },
    refreshDevices() { return this.post('/api/devices/refresh'); },
    getHealth() { return this.get('/api/devices/health'); },

    // ── Task endpoints ──
    runTask(serial, taskType) {
        return this.post(`/api/tasks/run?serial=${serial}&task_type=${taskType}`);
    },
    runAllTasks(taskType, indices) {
        let url = `/api/tasks/run-all?task_type=${taskType}`;
        if (indices && indices.length) url += `&indices=${indices.join(',')}`;
        return this.post(url);
    },
    getQueue() { return this.get('/api/tasks/queue'); },
    getHistory(limit) { return this.get(`/api/tasks/history?limit=${limit || 50}`); },

    // ── Reports ──
    getReports(limit, serial) {
        let url = `/api/reports/history?limit=${limit || 50}`;
        if (serial) url += `&serial=${serial}`;
        return this.get(url);
    },
    getLatestReport(serial) { return this.get(`/api/reports/latest/${serial}`); },

    // ── Config ──
    getConfig() { return this.get('/api/config'); },
    getOcrKeys() { return this.get('/api/config/ocr-keys'); },
    saveOcrKeys(keys) { return this.post('/api/config/ocr-keys', { keys }); },

    // ── LDPlayer Emulators ──
    getAllEmulators() { return this.get('/api/emulators/all'); },
    launchEmulator(index) { return this.post(`/api/emulators/launch?index=${index}`); },
    quitEmulator(index) { return this.post(`/api/emulators/quit?index=${index}`); },

    // ── Macros ──
    getMacros() { return this.get('/api/macros/list'); },
    getMacroInfo(index, filename) {
        return this.get(`/api/macros/info?index=${index}&filename=${encodeURIComponent(filename)}`);
    },
    runMacro(index, filename) {
        return this.post(`/api/macros/run?index=${index}&filename=${encodeURIComponent(filename)}`);
    },

    // ── Schedules ──
    getSchedules() { return this.get('/api/schedules'); },
    createSchedule(data) { return this.post('/api/schedules', data); },
    getSchedule(id) { return this.get(`/api/schedules/${id}`); },
    updateSchedule(id, data) {
        return fetch(`/api/schedules/${id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }).then(r => r.json());
    },
    deleteSchedule(id) {
        return fetch(`/api/schedules/${id}`, { method: 'DELETE' }).then(r => r.json());
    },
    executeSchedule(id) { return this.post(`/api/schedules/${id}/execute`); },

    // ── APK Management ──
    getApks() { return this.get('/api/apks'); },
    downloadApk(appId) { return this.post(`/api/apks/${appId}/download`); },
    installApk(appId, serial) { return this.post(`/api/apks/${appId}/install?serial=${serial}`); },
    installApkAll(appId, indices) { return this.post(`/api/apks/${appId}/install-all`, { indices }); },
};


/**
 * WebSocket Manager — auto-reconnecting WS client.
 */
class WSClient {
    constructor() {
        this.ws = null;
        this.listeners = {};
        this.reconnectDelay = 2000;
        this._reconnectTimer = null;
    }

    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws`;

        try {
            this.ws = new WebSocket(url);
        } catch (e) {
            this._scheduleReconnect();
            return;
        }

        this.ws.onopen = () => {
            this._updateStatus(true);
            // Start ping interval
            this._pingInterval = setInterval(() => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send('ping');
                }
            }, 15000);
        };

        this.ws.onclose = () => {
            this._updateStatus(false);
            clearInterval(this._pingInterval);
            this._scheduleReconnect();
        };

        this.ws.onerror = () => {
            this._updateStatus(false);
        };

        this.ws.onmessage = (evt) => {
            try {
                const msg = JSON.parse(evt.data);
                if (msg.event && this.listeners[msg.event]) {
                    this.listeners[msg.event].forEach(fn => fn(msg.data));
                }
                // Also fire wildcard listeners
                if (this.listeners['*']) {
                    this.listeners['*'].forEach(fn => fn(msg.event, msg.data));
                }
            } catch (e) {
                // Ignore malformed messages
            }
        };
    }

    on(event, callback) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(callback);
    }

    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(fn => fn !== callback);
        }
    }

    _scheduleReconnect() {
        if (this._reconnectTimer) return;
        this._reconnectTimer = setTimeout(() => {
            this._reconnectTimer = null;
            this.connect();
        }, this.reconnectDelay);
    }

    _updateStatus(online) {
        const el = document.getElementById('ws-status');
        if (el) {
            const dot = el.querySelector('.status-dot');
            const text = el.querySelector('span:last-child');
            if (dot) {
                dot.className = `status-dot ${online ? 'online' : 'offline'}`;
            }
            if (text) {
                text.textContent = online ? 'Connected' : 'Disconnected';
            }
        }
    }
}

// Global instances
const wsClient = new WSClient();
