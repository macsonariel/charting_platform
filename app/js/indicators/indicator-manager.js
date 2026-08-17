/**
 * Indicator Manager
 * Manages indicator catalog, favorites, and active state
 */

const IndicatorManager = (function () {
    // Indicator catalog with categories
    const INDICATOR_CATALOG = {
        trend: {
            name: 'Trend',
            icon: '📈',
            indicators: [
                {
                    id: 'sma',
                    name: 'SMA',
                    fullName: 'Simple Moving Average',
                    description: 'Average price over a specified period',
                    params: { period: 20 },
                    paramLabels: { period: 'Period' }
                },
                {
                    id: 'ema',
                    name: 'EMA',
                    fullName: 'Exponential Moving Average',
                    description: 'Weighted average giving more importance to recent prices',
                    params: { period: 20 },
                    paramLabels: { period: 'Period' }
                },
                {
                    id: 'wma',
                    name: 'WMA',
                    fullName: 'Weighted Moving Average',
                    description: 'Linearly weighted moving average',
                    params: { period: 20 },
                    paramLabels: { period: 'Period' }
                },
                {
                    id: 'vwma',
                    name: 'VWMA',
                    fullName: 'Volume Weighted Moving Average',
                    description: 'Moving average weighted by volume',
                    params: { period: 20 },
                    paramLabels: { period: 'Period' }
                },
                {
                    id: 'ichimoku',
                    name: 'Ichimoku Cloud',
                    fullName: 'Ichimoku Kinko Hyo',
                    description: 'Comprehensive trend indicator showing support, resistance, and momentum',
                    params: { tenkan: 9, kijun: 26, senkou: 52 },
                    paramLabels: { tenkan: 'Tenkan', kijun: 'Kijun', senkou: 'Senkou' }
                },
                {
                    id: 'adx',
                    name: 'ADX',
                    fullName: 'Average Directional Index',
                    description: 'Measures trend strength regardless of direction',
                    params: { period: 14 },
                    paramLabels: { period: 'Period' }
                }
            ]
        },
        volume: {
            name: 'Volume',
            icon: '📊',
            indicators: [
                {
                    id: 'volume',
                    name: 'Volume',
                    fullName: 'Volume Bars',
                    description: 'Standard volume histogram',
                    params: {},
                    paramLabels: {}
                },
                {
                    id: 'obv',
                    name: 'OBV',
                    fullName: 'On-Balance Volume',
                    description: 'Cumulative volume flow indicator',
                    params: {},
                    paramLabels: {}
                },
                {
                    id: 'vwap',
                    name: 'VWAP',
                    fullName: 'Volume Weighted Average Price',
                    description: 'Average price weighted by volume, resets daily',
                    params: {},
                    paramLabels: {}
                },
                {
                    id: 'volume_profile',
                    name: 'Volume Profile',
                    fullName: 'Volume Profile',
                    description: 'Shows volume distribution at price levels',
                    params: { rows: 24 },
                    paramLabels: { rows: 'Rows' }
                },
                {
                    id: 'mfi',
                    name: 'MFI',
                    fullName: 'Money Flow Index',
                    description: 'Volume-weighted RSI showing buying/selling pressure',
                    params: { period: 14 },
                    paramLabels: { period: 'Period' }
                }
            ]
        },
        momentum: {
            name: 'Momentum',
            icon: '⚡',
            indicators: [
                {
                    id: 'rsi',
                    name: 'RSI',
                    fullName: 'Relative Strength Index',
                    description: 'Momentum oscillator measuring speed of price changes',
                    params: { period: 14, overbought: 70, oversold: 30 },
                    paramLabels: { period: 'Period', overbought: 'OB', oversold: 'OS' }
                },
                {
                    id: 'macd',
                    name: 'MACD',
                    fullName: 'Moving Average Convergence Divergence',
                    description: 'Trend-following momentum indicator',
                    params: { fast: 12, slow: 26, signal: 9 },
                    paramLabels: { fast: 'Fast', slow: 'Slow', signal: 'Signal' }
                },
                {
                    id: 'stochastic',
                    name: 'Stochastic',
                    fullName: 'Stochastic Oscillator',
                    description: 'Compares closing price to price range over time',
                    params: { kPeriod: 14, dPeriod: 3, smooth: 3 },
                    paramLabels: { kPeriod: '%K', dPeriod: '%D', smooth: 'Smooth' }
                },
                {
                    id: 'cci',
                    name: 'CCI',
                    fullName: 'Commodity Channel Index',
                    description: 'Measures deviation from statistical mean',
                    params: { period: 20 },
                    paramLabels: { period: 'Period' }
                },
                {
                    id: 'roc',
                    name: 'ROC',
                    fullName: 'Rate of Change',
                    description: 'Percentage change between current and past price',
                    params: { period: 12 },
                    paramLabels: { period: 'Period' }
                },
                {
                    id: 'momentum',
                    name: 'Momentum',
                    fullName: 'Momentum Indicator',
                    description: 'Difference between current and past price',
                    params: { period: 10 },
                    paramLabels: { period: 'Period' }
                }
            ]
        },
        volatility: {
            name: 'Volatility',
            icon: '📉',
            indicators: [
                {
                    id: 'bollinger',
                    name: 'Bollinger Bands',
                    fullName: 'Bollinger Bands',
                    description: 'Volatility bands placed above and below a moving average',
                    params: { period: 20, stdDev: 2 },
                    paramLabels: { period: 'Period', stdDev: 'StdDev' }
                },
                {
                    id: 'atr',
                    name: 'ATR',
                    fullName: 'Average True Range',
                    description: 'Measures market volatility',
                    params: { period: 14 },
                    paramLabels: { period: 'Period' }
                },
                {
                    id: 'keltner',
                    name: 'Keltner Channel',
                    fullName: 'Keltner Channel',
                    description: 'Volatility-based envelope indicator',
                    params: { period: 20, multiplier: 2 },
                    paramLabels: { period: 'Period', multiplier: 'Mult' }
                },
                {
                    id: 'donchian',
                    name: 'Donchian Channel',
                    fullName: 'Donchian Channel',
                    description: 'Shows highest high and lowest low over period',
                    params: { period: 20 },
                    paramLabels: { period: 'Period' }
                }
            ]
        },
        oscillators: {
            name: 'Oscillators',
            icon: '📐',
            indicators: [
                {
                    id: 'williams_r',
                    name: 'Williams %R',
                    fullName: 'Williams Percent Range',
                    description: 'Momentum indicator similar to Stochastic',
                    params: { period: 14 },
                    paramLabels: { period: 'Period' }
                },
                {
                    id: 'ao',
                    name: 'AO',
                    fullName: 'Awesome Oscillator',
                    description: 'Shows market momentum using moving averages',
                    params: { fast: 5, slow: 34 },
                    paramLabels: { fast: 'Fast', slow: 'Slow' }
                },
                {
                    id: 'trix',
                    name: 'TRIX',
                    fullName: 'Triple Exponential Average',
                    description: 'Triple-smoothed EMA rate of change',
                    params: { period: 18 },
                    paramLabels: { period: 'Period' }
                },
                {
                    id: 'ultimate',
                    name: 'Ultimate Oscillator',
                    fullName: 'Ultimate Oscillator',
                    description: 'Multi-timeframe momentum oscillator',
                    params: { short: 7, medium: 14, long: 28 },
                    paramLabels: { short: 'Short', medium: 'Med', long: 'Long' }
                }
            ]
        },
        smc: {
            name: 'SMC/ICT',
            icon: '💰',
            indicators: [
                {
                    id: 'order_blocks',
                    name: 'Order Blocks',
                    fullName: 'Order Blocks',
                    description: 'Institutional supply and demand zones',
                    params: { lookback: 20 },
                    paramLabels: { lookback: 'Lookback' }
                },
                {
                    id: 'fvg',
                    name: 'FVG',
                    fullName: 'Fair Value Gaps',
                    description: 'Imbalance zones likely to be filled',
                    params: { minSize: 0.1 },
                    paramLabels: { minSize: 'Min %' }
                },
                {
                    id: 'liquidity_pools',
                    name: 'Liquidity Pools',
                    fullName: 'Liquidity Pools',
                    description: 'Areas of stop-loss clusters',
                    params: { sensitivity: 3 },
                    paramLabels: { sensitivity: 'Sens' }
                },
                {
                    id: 'breaker_blocks',
                    name: 'Breaker Blocks',
                    fullName: 'Breaker Blocks',
                    description: 'Failed order blocks that become support/resistance',
                    params: {},
                    paramLabels: {}
                },
                {
                    id: 'killzones',
                    name: 'Killzones',
                    fullName: 'ICT Killzones',
                    description: 'High-probability trading sessions',
                    params: {},
                    paramLabels: {}
                }
            ]
        }
    };

    // State
    let favorites = [];
    let activeIndicators = [];
    let listeners = [];

    // Load from localStorage
    function loadState() {
        try {
            const savedFavorites = localStorage.getItem('indicator_favorites');
            const savedActive = localStorage.getItem('indicator_active');

            if (savedFavorites) {
                favorites = JSON.parse(savedFavorites);
            }
            if (savedActive) {
                activeIndicators = JSON.parse(savedActive);
            }
        } catch (e) {
            console.warn('Failed to load indicator state:', e);
        }
    }

    // Save to localStorage
    function saveState() {
        try {
            localStorage.setItem('indicator_favorites', JSON.stringify(favorites));
            localStorage.setItem('indicator_active', JSON.stringify(activeIndicators));
        } catch (e) {
            console.warn('Failed to save indicator state:', e);
        }
    }

    // Notify listeners of state changes
    function notifyListeners(event, data) {
        listeners.forEach(listener => {
            try {
                listener(event, data);
            } catch (e) {
                console.error('Indicator listener error:', e);
            }
        });
    }

    // Get indicator by ID
    function getIndicatorById(id) {
        for (const category of Object.values(INDICATOR_CATALOG)) {
            const indicator = category.indicators.find(ind => ind.id === id);
            if (indicator) {
                return { ...indicator, category: category.name };
            }
        }
        return null;
    }

    // Get all indicators flat
    function getAllIndicators() {
        const all = [];
        for (const [catId, category] of Object.entries(INDICATOR_CATALOG)) {
            for (const indicator of category.indicators) {
                all.push({
                    ...indicator,
                    categoryId: catId,
                    categoryName: category.name,
                    categoryIcon: category.icon
                });
            }
        }
        return all;
    }

    // Initialize
    loadState();

    return {
        // Get catalog
        getCatalog() {
            return INDICATOR_CATALOG;
        },

        // Get all indicators
        getAllIndicators,

        // Get indicator by ID
        getIndicatorById,

        // Get indicators by category
        getIndicatorsByCategory(categoryId) {
            const category = INDICATOR_CATALOG[categoryId];
            if (!category) return [];
            return category.indicators.map(ind => ({
                ...ind,
                categoryId,
                categoryName: category.name,
                categoryIcon: category.icon
            }));
        },

        // Search indicators
        searchIndicators(query) {
            const lowerQuery = query.toLowerCase();
            return getAllIndicators().filter(ind =>
                ind.name.toLowerCase().includes(lowerQuery) ||
                ind.fullName.toLowerCase().includes(lowerQuery) ||
                ind.description.toLowerCase().includes(lowerQuery)
            );
        },

        // Favorites management
        getFavorites() {
            return favorites.map(fav => ({
                ...getIndicatorById(fav.id),
                params: fav.params,
                isActive: activeIndicators.some(a => a.id === fav.id)
            })).filter(f => f.id); // Filter out any null results
        },

        isFavorite(indicatorId) {
            return favorites.some(f => f.id === indicatorId);
        },

        addFavorite(indicatorId, params = null) {
            if (this.isFavorite(indicatorId)) return false;

            const indicator = getIndicatorById(indicatorId);
            if (!indicator) return false;

            favorites.push({
                id: indicatorId,
                params: params || { ...indicator.params }
            });
            saveState();
            notifyListeners('favorite_added', { id: indicatorId });
            return true;
        },

        removeFavorite(indicatorId) {
            const index = favorites.findIndex(f => f.id === indicatorId);
            if (index === -1) return false;

            favorites.splice(index, 1);
            saveState();
            notifyListeners('favorite_removed', { id: indicatorId });
            return true;
        },

        toggleFavorite(indicatorId) {
            if (this.isFavorite(indicatorId)) {
                return this.removeFavorite(indicatorId);
            } else {
                return this.addFavorite(indicatorId);
            }
        },

        // Active indicators management
        getActiveIndicators() {
            return activeIndicators.map(active => ({
                ...getIndicatorById(active.id),
                params: active.params,
                instanceId: active.instanceId
            })).filter(a => a.id);
        },

        isActive(indicatorId) {
            return activeIndicators.some(a => a.id === indicatorId);
        },

        addIndicator(indicatorId, params = null) {
            const indicator = getIndicatorById(indicatorId);
            if (!indicator) return null;

            const instanceId = `${indicatorId}_${Date.now()}`;
            const instance = {
                id: indicatorId,
                instanceId,
                params: params || { ...indicator.params }
            };

            activeIndicators.push(instance);
            saveState();
            notifyListeners('indicator_added', instance);
            return instanceId;
        },

        removeIndicator(instanceId) {
            const index = activeIndicators.findIndex(a => a.instanceId === instanceId);
            if (index === -1) {
                // Try by indicator ID (remove first match)
                const idIndex = activeIndicators.findIndex(a => a.id === instanceId);
                if (idIndex === -1) return false;
                const removed = activeIndicators.splice(idIndex, 1)[0];
                saveState();
                notifyListeners('indicator_removed', removed);
                return true;
            }

            const removed = activeIndicators.splice(index, 1)[0];
            saveState();
            notifyListeners('indicator_removed', removed);
            return true;
        },

        toggleIndicator(indicatorId, params = null) {
            if (this.isActive(indicatorId)) {
                return this.removeIndicator(indicatorId);
            } else {
                return this.addIndicator(indicatorId, params);
            }
        },

        updateIndicatorParams(instanceId, params) {
            const indicator = activeIndicators.find(a => a.instanceId === instanceId);
            if (!indicator) return false;

            indicator.params = { ...indicator.params, ...params };
            saveState();
            notifyListeners('indicator_updated', indicator);
            return true;
        },

        // Event listeners
        addListener(callback) {
            listeners.push(callback);
            return () => {
                const index = listeners.indexOf(callback);
                if (index > -1) listeners.splice(index, 1);
            };
        },

        // Reset state
        reset() {
            favorites = [];
            activeIndicators = [];
            saveState();
            notifyListeners('reset', {});
        }
    };
})();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = IndicatorManager;
}
