/**
 * Alert System
 * 
 * Main alert manager that monitors price against key levels
 * and triggers toast notifications when thresholds are crossed.
 */

const AlertSystem = {
    // Alerted level IDs to prevent duplicates
    _alertedLevels: new Set(),

    // Cached levels from analysis
    _levels: {
        sr_zones: [],
        fvgs: [],
        protected_levels: [],
        liquidity_pools: []
    },

    // Last known price
    _lastPrice: 0,

    // Alert type metadata
    ALERT_TYPES: {
        sr_resistance: { icon: '🔴', title: 'Resistance Alert', type: 'resistance' },
        sr_support: { icon: '🟢', title: 'Support Alert', type: 'support' },
        fvg: { icon: '📦', title: 'FVG Alert', type: 'fvg' },
        protected_high: { icon: '⚠️', title: 'Protected High', type: 'protected' },
        protected_low: { icon: '⚠️', title: 'Protected Low', type: 'protected' },
        liquidity: { icon: '💧', title: 'Liquidity Alert', type: 'liquidity' },
        setup: { icon: '🎯', title: 'Setup Alert', type: 'setup' }
    },

    /**
     * Initialize the alert system
     */
    init() {
        // Ensure dependencies are loaded
        if (typeof Toast === 'undefined') {
            console.warn('AlertSystem: Toast not loaded');
            return this;
        }
        if (typeof AlertConfig === 'undefined') {
            console.warn('AlertSystem: AlertConfig not loaded');
            return this;
        }

        Toast.init();
        AlertConfig.init();

        console.log('AlertSystem initialized with threshold:', AlertConfig.getThreshold() + '%');
        return this;
    },

    /**
     * Update cached levels from analysis data
     */
    updateLevels(data) {
        if (!data) return;

        // S/R Zones
        if (data.sr_zones) {
            this._levels.sr_zones = data.sr_zones.map(z => ({
                id: z.id || `sr_${z.price_low}_${z.price_high}`,
                type: z.zone_type, // 'resistance' or 'support'
                price: (z.price_low + z.price_high) / 2,
                priceHigh: z.price_high,
                priceLow: z.price_low
            }));
        }

        // FVGs
        if (data.fvgs || data.fair_value_gaps) {
            const fvgs = data.fvgs || data.fair_value_gaps || [];
            this._levels.fvgs = fvgs
                .filter(f => !f.filled)
                .map(f => ({
                    id: f.id || `fvg_${f.low}_${f.high}`,
                    price: (f.low + f.high) / 2,
                    priceHigh: f.high,
                    priceLow: f.low,
                    direction: f.direction
                }));
        }

        // Protected Levels
        if (data.protected_levels) {
            this._levels.protected_levels = data.protected_levels
                .filter(l => !l.broken)
                .map(l => ({
                    id: l.id || `pl_${l.kind}_${l.price}`,
                    type: l.kind, // 'high' or 'low'
                    price: l.price
                }));
        }

        // Liquidity Pools
        if (data.liquidity_pools) {
            this._levels.liquidity_pools = data.liquidity_pools
                .filter(l => !l.swept)
                .map(l => ({
                    id: l.id || `liq_${l.price}`,
                    price: l.price,
                    type: l.type
                }));
        }
    },

    /**
     * Check price against all levels and trigger alerts
     * @param {number} price - Current price
     */
    checkPrice(price) {
        if (!price || !AlertConfig.isEnabled()) return;

        const threshold = AlertConfig.getThreshold();
        this._lastPrice = price;

        // Check S/R zones
        this._checkSRZones(price, threshold);

        // Check FVGs
        this._checkFVGs(price, threshold);

        // Check Protected Levels
        this._checkProtectedLevels(price, threshold);

        // Check Liquidity
        this._checkLiquidity(price, threshold);

        // Clean up alerted levels that are no longer in range
        this._cleanupAlertedLevels(price, threshold);
    },

    /**
     * Check S/R zones
     */
    _checkSRZones(price, threshold) {
        for (const zone of this._levels.sr_zones) {
            const alertType = zone.type === 'resistance' ? 'sr_resistance' : 'sr_support';

            if (!AlertConfig.isTypeEnabled(alertType)) continue;
            if (this._alertedLevels.has(zone.id)) continue;

            // Check proximity to zone
            const distance = this._getDistanceToZone(price, zone.priceLow, zone.priceHigh);

            if (distance <= threshold) {
                this._triggerAlert(alertType, zone.id, zone.price, distance);
            }
        }
    },

    /**
     * Check FVGs
     */
    _checkFVGs(price, threshold) {
        if (!AlertConfig.isTypeEnabled('fvg')) return;

        for (const fvg of this._levels.fvgs) {
            if (this._alertedLevels.has(fvg.id)) continue;

            const distance = this._getDistanceToZone(price, fvg.priceLow, fvg.priceHigh);

            if (distance <= threshold) {
                this._triggerAlert('fvg', fvg.id, fvg.price, distance, fvg.direction);
            }
        }
    },

    /**
     * Check Protected Levels
     */
    _checkProtectedLevels(price, threshold) {
        for (const level of this._levels.protected_levels) {
            const alertType = level.type === 'high' ? 'protected_high' : 'protected_low';

            if (!AlertConfig.isTypeEnabled(alertType)) continue;
            if (this._alertedLevels.has(level.id)) continue;

            const distance = Math.abs(price - level.price) / price * 100;

            if (distance <= threshold) {
                this._triggerAlert(alertType, level.id, level.price, distance);
            }
        }
    },

    /**
     * Check Liquidity pools
     */
    _checkLiquidity(price, threshold) {
        if (!AlertConfig.isTypeEnabled('liquidity')) return;

        for (const pool of this._levels.liquidity_pools) {
            if (this._alertedLevels.has(pool.id)) continue;

            const distance = Math.abs(price - pool.price) / price * 100;

            if (distance <= threshold) {
                this._triggerAlert('liquidity', pool.id, pool.price, distance);
            }
        }
    },

    /**
     * Calculate distance to a zone
     */
    _getDistanceToZone(price, zoneLow, zoneHigh) {
        if (price >= zoneLow && price <= zoneHigh) {
            return 0; // Inside zone
        } else if (price < zoneLow) {
            return (zoneLow - price) / price * 100;
        } else {
            return (price - zoneHigh) / price * 100;
        }
    },

    /**
     * Trigger an alert
     */
    _triggerAlert(alertType, levelId, levelPrice, distance, extra = null) {
        // Mark as alerted
        this._alertedLevels.add(levelId);

        // Get alert metadata
        const meta = this.ALERT_TYPES[alertType] || { icon: '📢', title: 'Alert', type: 'info' };

        // Format message
        let message = `Price approaching ${this._formatPrice(levelPrice)}`;
        if (distance > 0) {
            message += ` (${distance.toFixed(2)}% away)`;
        } else {
            message = `Price is at ${this._formatPrice(levelPrice)}`;
        }

        if (alertType === 'fvg' && extra) {
            message = `Approaching ${extra} FVG at ${this._formatPrice(levelPrice)}`;
        }

        // Show toast
        Toast.show({
            type: meta.type,
            icon: meta.icon,
            title: meta.title,
            message: message,
            duration: 5000
        });

        console.log(`Alert: ${meta.title} - ${message}`);
    },

    /**
     * Clean up alerted levels that are no longer in proximity
     * (Allow re-alerting if price moves away and comes back)
     */
    _cleanupAlertedLevels(price, threshold) {
        const resetThreshold = threshold * 3; // Reset when 3x beyond threshold

        const toRemove = [];

        for (const levelId of this._alertedLevels) {
            let levelPrice = null;

            // Find the level
            for (const zone of this._levels.sr_zones) {
                if (zone.id === levelId) {
                    levelPrice = zone.price;
                    break;
                }
            }
            if (!levelPrice) {
                for (const fvg of this._levels.fvgs) {
                    if (fvg.id === levelId) {
                        levelPrice = fvg.price;
                        break;
                    }
                }
            }
            if (!levelPrice) {
                for (const pl of this._levels.protected_levels) {
                    if (pl.id === levelId) {
                        levelPrice = pl.price;
                        break;
                    }
                }
            }

            if (levelPrice) {
                const distance = Math.abs(price - levelPrice) / price * 100;
                if (distance > resetThreshold) {
                    toRemove.push(levelId);
                }
            }
        }

        for (const id of toRemove) {
            this._alertedLevels.delete(id);
        }
    },

    /**
     * Format price for display
     */
    _formatPrice(price) {
        if (!price) return '--';
        return price.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    },

    /**
     * Manually trigger a setup alert
     */
    triggerSetupAlert(setupType, message) {
        if (!AlertConfig.isTypeEnabled('setup')) return;

        Toast.show({
            type: 'setup',
            icon: '🎯',
            title: `Setup: ${setupType}`,
            message: message,
            duration: 6000
        });
    },

    /**
     * Get alert statistics
     */
    getStats() {
        return {
            alertedCount: this._alertedLevels.size,
            levelsTracked: {
                sr: this._levels.sr_zones.length,
                fvg: this._levels.fvgs.length,
                protected: this._levels.protected_levels.length,
                liquidity: this._levels.liquidity_pools.length
            },
            lastPrice: this._lastPrice
        };
    },

    /**
     * Reset all alerted levels
     */
    reset() {
        this._alertedLevels.clear();
    }
};

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AlertSystem;
}
