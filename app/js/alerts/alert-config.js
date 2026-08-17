/**
 * Alert Configuration
 * 
 * Manages user preferences for price alerts.
 * Persists settings to localStorage.
 */

const AlertConfig = {
    // Storage key
    STORAGE_KEY: 'tradingbuddy_alert_config',

    // Default configuration
    defaults: {
        enabled: true,
        threshold: 0.25,  // Percentage
        types: {
            sr_resistance: true,
            sr_support: true,
            fvg: true,
            protected_high: true,
            protected_low: true,
            liquidity: false,  // Off by default
            setup: true,
        }
    },

    // Current config
    _config: null,

    /**
     * Initialize and load config
     */
    init() {
        this._load();
        return this;
    },

    /**
     * Load config from localStorage
     */
    _load() {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                this._config = { ...this.defaults, ...JSON.parse(stored) };
                // Merge types to handle new alert types
                this._config.types = { ...this.defaults.types, ...this._config.types };
            } else {
                this._config = { ...this.defaults };
            }
        } catch (e) {
            console.warn('Failed to load alert config:', e);
            this._config = { ...this.defaults };
        }
    },

    /**
     * Save config to localStorage
     */
    _save() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this._config));
        } catch (e) {
            console.warn('Failed to save alert config:', e);
        }
    },

    /**
     * Check if alerts are globally enabled
     */
    isEnabled() {
        return this._config?.enabled ?? true;
    },

    /**
     * Enable or disable all alerts
     */
    setEnabled(enabled) {
        if (!this._config) this.init();
        this._config.enabled = enabled;
        this._save();
    },

    /**
     * Check if a specific alert type is enabled
     */
    isTypeEnabled(type) {
        if (!this._config) this.init();
        return this._config.enabled && (this._config.types[type] ?? false);
    },

    /**
     * Enable or disable a specific alert type
     */
    setTypeEnabled(type, enabled) {
        if (!this._config) this.init();
        this._config.types[type] = enabled;
        this._save();
    },

    /**
     * Get the proximity threshold
     */
    getThreshold() {
        return this._config?.threshold ?? 0.25;
    },

    /**
     * Set the proximity threshold
     */
    setThreshold(threshold) {
        if (!this._config) this.init();
        this._config.threshold = Math.max(0.1, Math.min(5, threshold));
        this._save();
    },

    /**
     * Get all type settings
     */
    getTypes() {
        if (!this._config) this.init();
        return { ...this._config.types };
    },

    /**
     * Get full config
     */
    getConfig() {
        if (!this._config) this.init();
        return { ...this._config };
    },

    /**
     * Reset to defaults
     */
    reset() {
        this._config = { ...this.defaults };
        this._save();
    }
};

// Auto-initialize
AlertConfig.init();

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AlertConfig;
}
