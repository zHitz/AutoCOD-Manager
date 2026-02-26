/**
 * Notification Bell Component
 * Manages notification dropdown and WS-driven notifications.
 */
const NotificationManager = {
    _notifications: [],
    _maxItems: 20,

    add(type, title, desc) {
        const icons = {
            success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--emerald-500)"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
            info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--blue-500)"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
            warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--yellow-500)"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
            error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--red-500)"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
        };

        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        this._notifications.unshift({
            type, title, desc, time: timeStr,
            icon: icons[type] || icons.info,
        });

        if (this._notifications.length > this._maxItems) {
            this._notifications.pop();
        }

        this.render();
        // Show dot
        const dot = document.getElementById('notif-dot');
        if (dot) dot.style.display = 'block';
    },

    render() {
        const list = document.getElementById('notif-list');
        if (!list) return;

        if (this._notifications.length === 0) {
            list.innerHTML = `<div style="padding:32px;text-align:center;color:var(--muted-foreground);font-size:13px">No notifications</div>`;
            return;
        }

        list.innerHTML = this._notifications.map(n => `
            <div class="notif-item">
                <div class="notif-item-icon">${n.icon}</div>
                <div>
                    <div class="notif-item-title">${n.title}</div>
                    <div class="notif-item-desc">${n.desc}</div>
                    <span class="notif-item-time">${n.time}</span>
                </div>
            </div>
        `).join('');
    },

    clear() {
        this._notifications = [];
        this.render();
        const dot = document.getElementById('notif-dot');
        if (dot) dot.style.display = 'none';
    },
};

// Global toggle functions
function toggleNotifications() {
    const dd = document.getElementById('notif-dropdown');
    const btn = document.getElementById('notif-btn');
    if (!dd) return;
    const open = dd.style.display !== 'none';
    dd.style.display = open ? 'none' : 'block';
    if (btn) btn.classList.toggle('open', !open);

    // Close user popup if open
    const popup = document.getElementById('user-popup');
    if (popup) popup.style.display = 'none';
}

function clearNotifications() {
    NotificationManager.clear();
}

function toggleUserMenu() {
    const popup = document.getElementById('user-popup');
    const btn = document.getElementById('user-profile-btn');
    if (!popup) return;
    const open = popup.style.display !== 'none';
    popup.style.display = open ? 'none' : 'block';
    if (btn) btn.classList.toggle('open', !open);

    // Close notif dropdown if open
    const dd = document.getElementById('notif-dropdown');
    if (dd) dd.style.display = 'none';
}

// Close dropdowns when clicking outside
document.addEventListener('mousedown', (e) => {
    const notifWrapper = document.getElementById('notif-wrapper');
    const userSection = document.getElementById('user-section');
    const dd = document.getElementById('notif-dropdown');
    const popup = document.getElementById('user-popup');

    if (notifWrapper && !notifWrapper.contains(e.target) && dd) {
        dd.style.display = 'none';
        const btn = document.getElementById('notif-btn');
        if (btn) btn.classList.remove('open');
    }

    if (userSection && !userSection.contains(e.target) && popup) {
        popup.style.display = 'none';
        const btn = document.getElementById('user-profile-btn');
        if (btn) btn.classList.remove('open');
    }
});
