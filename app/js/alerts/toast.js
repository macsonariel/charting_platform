/**
 * Toast Notification Component
 * 
 * Creates and manages toast popup notifications for price alerts.
 */

const Toast = {
    // Container for all toasts
    container: null,

    // Toast queue
    toasts: [],

    /**
     * Initialize the toast container
     */
    init() {
        if (this.container) return;

        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);

        // Inject styles
        this._injectStyles();
    },

    /**
     * Show a toast notification
     * @param {Object} options - Toast options
     * @param {string} options.type - Alert type (resistance, support, fvg, etc.)
     * @param {string} options.icon - Emoji icon
     * @param {string} options.title - Toast title
     * @param {string} options.message - Toast message
     * @param {number} options.duration - Auto-dismiss time in ms (default: 5000)
     */
    show({ type = 'info', icon = '📢', title = 'Alert', message = '', duration = 5000 }) {
        this.init();

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" aria-label="Close">×</button>
        `;

        // Close button handler
        toast.querySelector('.toast-close').addEventListener('click', () => {
            this.dismiss(toast);
        });

        // Add to container (at top)
        this.container.insertBefore(toast, this.container.firstChild);
        this.toasts.push(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.add('toast-visible');
        });

        // Auto dismiss
        if (duration > 0) {
            setTimeout(() => {
                this.dismiss(toast);
            }, duration);
        }

        return toast;
    },

    /**
     * Dismiss a toast
     */
    dismiss(toast) {
        if (!toast || !toast.parentNode) return;

        toast.classList.remove('toast-visible');
        toast.classList.add('toast-hiding');

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            this.toasts = this.toasts.filter(t => t !== toast);
        }, 300);
    },

    /**
     * Dismiss all toasts
     */
    dismissAll() {
        [...this.toasts].forEach(toast => this.dismiss(toast));
    },

    /**
     * Inject toast styles
     */
    _injectStyles() {
        if (document.getElementById('toast-styles')) return;

        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            .toast-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
                pointer-events: none;
            }
            
            .toast {
                display: flex;
                align-items: flex-start;
                gap: 12px;
                min-width: 300px;
                max-width: 400px;
                padding: 14px 16px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                border-left: 4px solid #64748b;
                pointer-events: auto;
                opacity: 0;
                transform: translateX(100%);
                transition: all 0.3s ease;
            }
            
            .toast-visible {
                opacity: 1;
                transform: translateX(0);
            }
            
            .toast-hiding {
                opacity: 0;
                transform: translateX(100%);
            }
            
            .toast-icon {
                font-size: 20px;
                flex-shrink: 0;
            }
            
            .toast-content {
                flex: 1;
                min-width: 0;
            }
            
            .toast-title {
                font-weight: 600;
                font-size: 13px;
                color: #1e293b;
                margin-bottom: 2px;
            }
            
            .toast-message {
                font-size: 12px;
                color: #64748b;
                line-height: 1.4;
            }
            
            .toast-close {
                background: none;
                border: none;
                font-size: 18px;
                color: #94a3b8;
                cursor: pointer;
                padding: 0;
                line-height: 1;
                flex-shrink: 0;
            }
            
            .toast-close:hover {
                color: #64748b;
            }
            
            /* Alert type colors */
            .toast-resistance {
                border-left-color: #ef4444;
            }
            
            .toast-support {
                border-left-color: #22c55e;
            }
            
            .toast-fvg {
                border-left-color: #3b82f6;
            }
            
            .toast-protected {
                border-left-color: #f59e0b;
            }
            
            .toast-liquidity {
                border-left-color: #06b6d4;
            }
            
            .toast-setup {
                border-left-color: #8b5cf6;
            }
            
            /* Dark theme */
            [data-theme="dark"] .toast {
                background: #1e293b;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            }
            
            [data-theme="dark"] .toast-title {
                color: #f1f5f9;
            }
            
            [data-theme="dark"] .toast-message {
                color: #94a3b8;
            }
            
            [data-theme="dark"] .toast-close {
                color: #64748b;
            }
            
            [data-theme="dark"] .toast-close:hover {
                color: #94a3b8;
            }
        `;
        document.head.appendChild(style);
    }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Toast;
}
