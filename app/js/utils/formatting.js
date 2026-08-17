/**
 * Formatting Utilities
 * 
 * Shared formatting functions for the analysis panel and other components.
 */

/**
 * Format price for display with locale-aware formatting.
 * @param {number} price - The price value to format
 * @returns {string} Formatted price string or '--' if invalid
 */
export function formatPrice(price) {
    if (typeof price !== 'number' || isNaN(price)) return '--';
    return price.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * Get CSS class for direction badge styling.
 * @param {string} direction - 'bullish', 'bearish', or 'neutral'
 * @returns {string} CSS class name
 */
export function getDirectionClass(direction) {
    switch (direction?.toLowerCase()) {
        case 'bullish': return 'bullish';
        case 'bearish': return 'bearish';
        default: return 'neutral';
    }
}

/**
 * Format pip distance for display.
 * @param {number} distance - Distance in pips
 * @returns {string} Formatted distance string
 */
export function formatPips(distance) {
    if (distance >= 1000) {
        return (distance / 1000).toFixed(1) + 'K pips away';
    } else if (distance >= 1) {
        return Math.round(distance) + ' pips away';
    } else {
        return '<1 pip away';
    }
}

/**
 * Format volume for display (K, M, B suffixes).
 * @param {number} volume - Volume value
 * @returns {string} Formatted volume string
 */
export function formatVolume(volume) {
    if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)}B`;
    if (volume >= 1e6) return `${(volume / 1e6).toFixed(2)}M`;
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)}K`;
    return volume.toFixed(0);
}

// Legacy global exports for non-module scripts
if (typeof window !== 'undefined') {
    window.FormatUtils = {
        formatPrice,
        getDirectionClass,
        formatPips,
        formatVolume
    };
}
