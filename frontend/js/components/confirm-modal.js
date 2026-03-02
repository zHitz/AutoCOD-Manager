/**
 * ConfirmModal — Premium confirmation dialog matching the design system.
 * Replaces native confirm() with a beautiful, animated modal.
 *
 * Usage:
 *   const ok = await ConfirmModal.show({
 *       title: 'Restart Server',
 *       message: 'The backend will restart. This page will reload automatically.',
 *       icon: 'restart',        // 'restart' | 'shutdown' | 'warning' | 'danger' | 'info'
 *       confirmText: 'Restart',
 *       cancelText: 'Cancel',
 *       variant: 'default',     // 'default' | 'danger'
 *   });
 *   if (ok) { ... }
 */
const ConfirmModal = {
    _resolve: null,

    show({ title, message, icon = 'info', confirmText = 'Confirm', cancelText = 'Cancel', variant = 'default' } = {}) {
        return new Promise((resolve) => {
            this._resolve = resolve;
            this._render({ title, message, icon, confirmText, cancelText, variant });
        });
    },

    _getIcon(type) {
        const icons = {
            restart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="23 4 23 10 17 10" />
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
            </svg>`,
            shutdown: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                <line x1="12" y1="2" x2="12" y2="12" />
            </svg>`,
            warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>`,
            danger: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
            </svg>`,
            info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>`,
        };
        return icons[type] || icons.info;
    },

    _render({ title, message, icon, confirmText, cancelText, variant }) {
        // Remove any existing modal
        this._remove();

        const iconColorClass = (variant === 'danger') ? 'confirm-modal-icon--danger' : 'confirm-modal-icon--default';
        const btnClass = (variant === 'danger') ? 'btn btn-destructive btn-md' : 'btn btn-default btn-md';

        const overlay = document.createElement('div');
        overlay.className = 'confirm-modal-overlay';
        overlay.id = 'confirm-modal-overlay';
        overlay.innerHTML = `
            <div class="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="confirm-modal-title">
                <div class="confirm-modal-icon ${iconColorClass}">
                    ${this._getIcon(icon)}
                </div>
                <h3 class="confirm-modal-title" id="confirm-modal-title">${title}</h3>
                <p class="confirm-modal-message">${message}</p>
                <div class="confirm-modal-actions">
                    <button class="btn btn-outline btn-md" id="confirm-modal-cancel">${cancelText}</button>
                    <button class="${btnClass}" id="confirm-modal-confirm">${confirmText}</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Events
        document.getElementById('confirm-modal-confirm').addEventListener('click', () => this._close(true));
        document.getElementById('confirm-modal-cancel').addEventListener('click', () => this._close(false));
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) this._close(false);
        });

        // Keyboard
        const keyHandler = (e) => {
            if (e.key === 'Escape') this._close(false);
            if (e.key === 'Enter') this._close(true);
        };
        document.addEventListener('keydown', keyHandler);
        overlay._keyHandler = keyHandler;

        // Focus confirm button
        requestAnimationFrame(() => {
            document.getElementById('confirm-modal-confirm')?.focus();
        });
    },

    _close(result) {
        const overlay = document.getElementById('confirm-modal-overlay');
        if (!overlay) return;

        // Remove keyboard listener
        if (overlay._keyHandler) {
            document.removeEventListener('keydown', overlay._keyHandler);
        }

        // Animate out
        const modal = overlay.querySelector('.confirm-modal');
        overlay.style.animation = 'confirmOverlayOut 0.15s ease forwards';
        if (modal) modal.style.animation = 'confirmModalOut 0.15s ease forwards';

        setTimeout(() => {
            this._remove();
            if (this._resolve) {
                this._resolve(result);
                this._resolve = null;
            }
        }, 150);
    },

    _remove() {
        const existing = document.getElementById('confirm-modal-overlay');
        if (existing) existing.remove();
    },
};
