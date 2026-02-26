/**
 * Toast Notification Component
 */
const Toast = {
    _container: null,

    getContainer() {
        if (!this._container) {
            this._container = document.getElementById('toast-container');
        }
        return this._container;
    },

    show(type, title, message, duration = 4000) {
        const container = this.getContainer();
        if (!container) return;

        const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
        const colors = {
            success: 'var(--emerald-600)',
            error: 'var(--red-500)',
            info: 'var(--blue-500)',
            warning: 'var(--yellow-500)',
        };

        const toast = document.createElement('div');
        toast.className = 'toast toast-enter';
        toast.innerHTML = `
            <span class="toast-icon" style="color:${colors[type] || colors.info}">${icons[type] || icons.info}</span>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                ${message ? `<div class="toast-message">${message}</div>` : ''}
            </div>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.remove('toast-enter');
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 200);
        }, duration);
    },

    success(title, msg) { this.show('success', title, msg); },
    error(title, msg) { this.show('error', title, msg, 6000); },
    info(title, msg) { this.show('info', title, msg); },
    warning(title, msg) { this.show('warning', title, msg); },
};
