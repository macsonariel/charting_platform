/**
 * Core Engine API - Fetch data from Core engine endpoints
 */
const CoreEngineAPI = (function () {
    'use strict';

    const API_BASE = '/api/core';

    /**
     * Get raw analysis data (swings, breaks, levels, etc.)
     * @param {string} symbol - Trading symbol (e.g., 'BTCUSDT')
     * @param {string} timeframe - Chart timeframe (e.g., '1h')
     * @param {number} periods - Number of candles
     * @returns {Promise<Object>} - Raw analysis data
     */
    async function getAnalysis(symbol, timeframe, periods = 300) {
        const url = `${API_BASE}/analyze?symbol=${symbol}&timeframe=${timeframe}&periods=${periods}`;

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Core API error: ${response.status}`);
            }
            const result = await response.json();
            return result.data || result;
        } catch (error) {
            console.error('Core API fetch error:', error);
            throw error;
        }
    }

    /**
     * Get summary data for panels
     * @param {string} symbol - Trading symbol
     * @param {string} timeframe - Chart timeframe
     * @param {number} periods - Number of candles
     * @returns {Promise<Object>} - Summary data
     */
    async function getSummary(symbol, timeframe, periods = 300) {
        const url = `${API_BASE}/summary?symbol=${symbol}&timeframe=${timeframe}&periods=${periods}`;

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Core API error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Core API summary error:', error);
            throw error;
        }
    }

    /**
     * Get zone-filtered render data
     * @param {string} symbol - Trading symbol
     * @param {string} timeframe - Chart timeframe
     * @param {number} periods - Number of candles
     * @param {number} zoneIndex - Zone index to display (0 = most recent)
     * @param {boolean} showAllZones - Show all zones without filtering
     * @returns {Promise<Object>} - Filtered render data
     */
    async function getRender(symbol, timeframe, periods = 300, zoneIndex = 0, showAllZones = false) {
        const url = `${API_BASE}/render?symbol=${symbol}&timeframe=${timeframe}&periods=${periods}&zone_index=${zoneIndex}&show_all_zones=${showAllZones}`;

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Core API error: ${response.status}`);
            }
            const result = await response.json();
            return result.data || result;
        } catch (error) {
            console.error('Core API render error:', error);
            throw error;
        }
    }

    // Public API
    return {
        getAnalysis,
        getSummary,
        getRender
    };
})();

// Export for global access
if (typeof window !== 'undefined') {
    window.CoreEngineAPI = CoreEngineAPI;
}
