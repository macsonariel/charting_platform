/**
 * Indicator Calculators
 * Pure calculation functions for technical indicators
 */

const IndicatorCalculators = (function () {

    /**
     * Calculate Simple Moving Average (SMA)
     * @param {Array<number>} data - Array of prices (typically close prices)
     * @param {number} period - Number of periods for the average
     * @returns {Array<number|null>} - Array of SMA values (null for insufficient data)
     */
    function calculateSMA(data, period) {
        if (!data || data.length === 0 || period <= 0) {
            return [];
        }

        const result = [];
        let sum = 0;

        for (let i = 0; i < data.length; i++) {
            sum += data[i];

            if (i < period - 1) {
                // Not enough data points yet
                result.push(null);
            } else {
                if (i >= period) {
                    // Remove the oldest value from sum
                    sum -= data[i - period];
                }
                result.push(sum / period);
            }
        }

        return result;
    }

    /**
     * Calculate Exponential Moving Average (EMA)
     * @param {Array<number>} data - Array of prices
     * @param {number} period - Number of periods
     * @returns {Array<number|null>} - Array of EMA values
     */
    function calculateEMA(data, period) {
        if (!data || data.length === 0 || period <= 0) {
            return [];
        }

        const result = [];
        const multiplier = 2 / (period + 1);
        let ema = null;

        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                // Not enough data, calculate running sum for initial SMA
                result.push(null);
            } else if (i === period - 1) {
                // First EMA is the SMA of first 'period' values
                let sum = 0;
                for (let j = 0; j <= i; j++) {
                    sum += data[j];
                }
                ema = sum / period;
                result.push(ema);
            } else {
                // EMA = (Close - Previous EMA) * multiplier + Previous EMA
                ema = (data[i] - ema) * multiplier + ema;
                result.push(ema);
            }
        }

        return result;
    }

    /**
     * Calculate Weighted Moving Average (WMA)
     * @param {Array<number>} data - Array of prices
     * @param {number} period - Number of periods
     * @returns {Array<number|null>} - Array of WMA values
     */
    function calculateWMA(data, period) {
        if (!data || data.length === 0 || period <= 0) {
            return [];
        }

        const result = [];
        const weightSum = (period * (period + 1)) / 2;

        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                result.push(null);
            } else {
                let weightedSum = 0;
                for (let j = 0; j < period; j++) {
                    weightedSum += data[i - period + 1 + j] * (j + 1);
                }
                result.push(weightedSum / weightSum);
            }
        }

        return result;
    }

    /**
     * Calculate Volume Weighted Moving Average (VWMA)
     * @param {Array<number>} closeData - Array of close prices
     * @param {Array<number>} volumeData - Array of volumes
     * @param {number} period - Number of periods
     * @returns {Array<number|null>} - Array of VWMA values
     */
    function calculateVWMA(closeData, volumeData, period) {
        if (!closeData || !volumeData || closeData.length === 0 || period <= 0) {
            return [];
        }

        const result = [];

        for (let i = 0; i < closeData.length; i++) {
            if (i < period - 1) {
                result.push(null);
            } else {
                let sumPriceVolume = 0;
                let sumVolume = 0;

                for (let j = i - period + 1; j <= i; j++) {
                    sumPriceVolume += closeData[j] * volumeData[j];
                    sumVolume += volumeData[j];
                }

                result.push(sumVolume > 0 ? sumPriceVolume / sumVolume : null);
            }
        }

        return result;
    }

    /**
     * Calculate Bollinger Bands
     * @param {Array<number>} data - Array of prices
     * @param {number} period - SMA period (typically 20)
     * @param {number} stdDev - Standard deviation multiplier (typically 2)
     * @returns {Object} - { upper: [], middle: [], lower: [] }
     */
    function calculateBollingerBands(data, period = 20, stdDev = 2) {
        const sma = calculateSMA(data, period);
        const upper = [];
        const lower = [];

        for (let i = 0; i < data.length; i++) {
            if (i < period - 1 || sma[i] === null) {
                upper.push(null);
                lower.push(null);
            } else {
                // Calculate standard deviation
                let sumSquaredDiff = 0;
                for (let j = i - period + 1; j <= i; j++) {
                    sumSquaredDiff += Math.pow(data[j] - sma[i], 2);
                }
                const std = Math.sqrt(sumSquaredDiff / period);

                upper.push(sma[i] + stdDev * std);
                lower.push(sma[i] - stdDev * std);
            }
        }

        return { upper, middle: sma, lower };
    }

    /**
     * Get calculator function for an indicator type
     * @param {string} indicatorId - Indicator ID (e.g., 'sma', 'ema')
     * @returns {Function|null} - Calculator function or null if not found
     */
    function getCalculator(indicatorId) {
        const calculators = {
            'sma': calculateSMA,
            'ema': calculateEMA,
            'wma': calculateWMA,
            'vwma': calculateVWMA,
            'bb': calculateBollingerBands
        };

        return calculators[indicatorId] || null;
    }

    // Public API
    return {
        calculateSMA,
        calculateEMA,
        calculateWMA,
        calculateVWMA,
        calculateBollingerBands,
        getCalculator
    };
})();

// Expose globally
if (typeof window !== 'undefined') {
    window.IndicatorCalculators = IndicatorCalculators;
}
