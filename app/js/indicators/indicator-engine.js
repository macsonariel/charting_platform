/**
 * Indicator Engine
 * Orchestrates indicator calculation and rendering on the chart
 * Integrates with DrawingManager for proper pan/zoom support
 */

const IndicatorEngine = (function () {

    let isInitialized = false;
    let chartGroup = null;
    let xScale = null;
    let yScale = null;

    // Track active indicator renders
    const activeRenders = new Map();

    // Store calculated indicator data for re-rendering on zoom/pan
    const indicatorDataCache = new Map();

    /**
     * Initialize the indicator engine
     * Should be called after chart is ready
     */
    function init() {
        if (isInitialized) return;

        // Wait for chart and DrawingManager to be ready
        const checkDependencies = () => {
            const dmReady = typeof DrawingManager !== 'undefined' && DrawingManager.isInitialized;
            const chartReady = window.chartGroup && window.baseXScale && window.baseYScale;

            if (dmReady && chartReady) {
                chartGroup = window.chartGroup;
                xScale = window.baseXScale;
                yScale = window.baseYScale;

                // Register indicators as a drawing type with DrawingManager
                registerWithDrawingManager();

                // Listen for indicator change events
                document.addEventListener('indicatorChange', handleIndicatorChange);

                isInitialized = true;
                console.log('✅ IndicatorEngine initialized with DrawingManager integration');

                // Render any already-active indicators
                renderActiveIndicators();
            } else {
                // Retry after a short delay
                setTimeout(checkDependencies, 500);
            }
        };

        checkDependencies();
    }

    /**
     * Register indicators as a drawing type with DrawingManager
     */
    function registerWithDrawingManager() {
        DrawingManager.register('indicators', {
            enabled: true,

            // fetchData returns the cached indicator data
            fetchData: async (symbol, timeframe) => {
                // Return cached data - actual calculation happens on indicator toggle
                return {
                    indicators: Array.from(indicatorDataCache.entries())
                };
            },

            // render draws all active indicators
            render: (g, data, xScale, yScale) => {
                if (!data || !data.indicators) return;

                // Clear existing indicator elements in this group
                g.selectAll('.indicator-line').remove();

                const chartData = window.chartData;
                if (!chartData || !chartData.x) return;

                // Render each cached indicator
                data.indicators.forEach(([instanceId, indicatorData]) => {
                    renderIndicatorLine(g, instanceId, indicatorData, chartData.x, xScale, yScale);
                });
            },

            // update is called on pan/zoom with cached data
            update: (g, data, xScale, yScale) => {
                if (!data || !data.indicators) return;

                // Clear and re-render with new scales
                g.selectAll('.indicator-line').remove();

                const chartData = window.chartData;
                if (!chartData || !chartData.x) return;

                data.indicators.forEach(([instanceId, indicatorData]) => {
                    renderIndicatorLine(g, instanceId, indicatorData, chartData.x, xScale, yScale);
                });
            }
        });

        console.log('📐 IndicatorEngine registered with DrawingManager');
    }

    /**
     * Render a single indicator line
     */
    function renderIndicatorLine(g, instanceId, indicatorData, timestamps, xScale, yScale) {
        const { name, values, color } = indicatorData;

        // Create data points array (filter out null values)
        const dataPoints = [];
        for (let i = 0; i < timestamps.length; i++) {
            if (values[i] !== null && !isNaN(values[i])) {
                dataPoints.push({
                    timestamp: timestamps[i],
                    value: values[i]
                });
            }
        }

        if (dataPoints.length === 0) return;

        // Create line generator
        const lineGenerator = d3.line()
            .x(d => xScale(d.timestamp))
            .y(d => yScale(d.value))
            .curve(d3.curveMonotoneX);

        // Draw the line
        g.append('path')
            .datum(dataPoints)
            .attr('class', `indicator-line indicator-${instanceId}`)
            .attr('d', lineGenerator)
            .attr('fill', 'none')
            .attr('stroke', color)
            .attr('stroke-width', 1.5)
            .attr('stroke-opacity', 0.85)
            .attr('stroke-linecap', 'round')
            .attr('stroke-linejoin', 'round');

        // Add label at the end of the line
        const lastPoint = dataPoints[dataPoints.length - 1];
        if (lastPoint) {
            g.append('text')
                .attr('class', `indicator-line indicator-label-${instanceId}`)
                .attr('x', xScale(lastPoint.timestamp) + 5)
                .attr('y', yScale(lastPoint.value))
                .attr('fill', color)
                .attr('font-size', '10px')
                .attr('font-weight', '500')
                .attr('dominant-baseline', 'middle')
                .text(name);
        }
    }

    /**
     * Handle indicator change events from IndicatorManager
     * @param {CustomEvent} event - Event with detail { event, data }
     */
    function handleIndicatorChange(event) {
        const { event: eventType, data } = event.detail;

        console.log(`🔧 IndicatorEngine received: ${eventType}`, data);

        switch (eventType) {
            case 'indicator_added':
                calculateAndCacheIndicator(data.id, data.params);
                break;
            case 'indicator_removed':
                removeIndicator(data.instanceId || data.id);
                break;
            case 'indicator_updated':
                removeIndicator(data.instanceId || data.id);
                calculateAndCacheIndicator(data.id, data.params);
                break;
            case 'favorite_added':
            case 'favorite_removed':
                // Favorites don't affect rendering
                break;
            default:
                console.log(`Unknown indicator event: ${eventType}`);
        }
    }

    /**
     * Render all currently active indicators
     */
    function renderActiveIndicators() {
        if (typeof IndicatorManager === 'undefined') {
            console.warn('IndicatorManager not available');
            return;
        }

        const activeIndicators = IndicatorManager.getActiveIndicators();

        activeIndicators.forEach(indicator => {
            calculateAndCacheIndicator(indicator.id, indicator.params, indicator.instanceId);
        });
    }

    // Default colors for indicators
    const DEFAULT_COLORS = [
        '#2962ff', // Blue
        '#ff6d00', // Orange
        '#00c853', // Green
        '#aa00ff', // Purple
        '#ff1744', // Red
        '#00bfa5', // Teal
        '#ffc400', // Amber
        '#d500f9', // Pink
    ];
    let colorIndex = 0;
    const colorAssignments = new Map();

    function getIndicatorColor(instanceId) {
        if (!colorAssignments.has(instanceId)) {
            colorAssignments.set(instanceId, DEFAULT_COLORS[colorIndex % DEFAULT_COLORS.length]);
            colorIndex++;
        }
        return colorAssignments.get(instanceId);
    }

    /**
     * Calculate indicator values and cache them for rendering
     * @param {string} indicatorId - Indicator type ID (e.g., 'sma')
     * @param {Object} params - Indicator parameters
     * @param {string} [instanceId] - Optional specific instance ID
     */
    function calculateAndCacheIndicator(indicatorId, params = {}, instanceId = null) {
        if (!isInitialized) {
            console.warn('IndicatorEngine not ready, cannot calculate');
            return;
        }

        // Get chart data
        const chartData = window.chartData;
        if (!chartData || !chartData.x || !chartData.close) {
            console.warn('No chart data available for indicator calculation');
            return;
        }

        // Generate instance ID if not provided
        const instId = instanceId || `${indicatorId}_${Date.now()}`;
        const color = getIndicatorColor(instId);

        let values = [];
        let name = '';

        // Calculate based on indicator type
        switch (indicatorId) {
            case 'sma':
                const smaPeriod = params.period || 20;
                values = IndicatorCalculators.calculateSMA(chartData.close, smaPeriod);
                name = `SMA(${smaPeriod})`;
                break;
            case 'ema':
                const emaPeriod = params.period || 20;
                values = IndicatorCalculators.calculateEMA(chartData.close, emaPeriod);
                name = `EMA(${emaPeriod})`;
                break;
            case 'wma':
                const wmaPeriod = params.period || 20;
                values = IndicatorCalculators.calculateWMA(chartData.close, wmaPeriod);
                name = `WMA(${wmaPeriod})`;
                break;
            case 'vwma':
                const vwmaPeriod = params.period || 20;
                values = IndicatorCalculators.calculateVWMA(chartData.close, chartData.volume, vwmaPeriod);
                name = `VWMA(${vwmaPeriod})`;
                break;
            default:
                console.warn(`Unknown indicator type: ${indicatorId}`);
                return;
        }

        // Cache the calculated data
        indicatorDataCache.set(instId, {
            type: indicatorId,
            name,
            values,
            color,
            params
        });

        activeRenders.set(instId, { type: indicatorId, params });

        console.log(`📊 Cached ${name} with ${values.filter(v => v !== null).length} values`);

        // Trigger DrawingManager refresh to render
        triggerRender();
    }

    /**
     * Remove an indicator from cache and chart
     * @param {string} instanceId - Instance ID to remove
     */
    function removeIndicator(instanceId) {
        indicatorDataCache.delete(instanceId);
        activeRenders.delete(instanceId);
        colorAssignments.delete(instanceId);

        console.log(`🗑️ Removed indicator ${instanceId}`);

        // Trigger DrawingManager refresh
        triggerRender();
    }

    /**
     * Trigger a re-render of all indicators
     * Directly renders to the DrawingManager's indicators group
     */
    function triggerRender() {
        if (typeof DrawingManager === 'undefined' || !DrawingManager.isInitialized) {
            return;
        }

        // Get the drawing group from DrawingManager
        const drawingLayer = document.querySelector('.drawing-manager-layer .drawing-indicators');
        if (!drawingLayer) return;

        const g = d3.select(drawingLayer);

        // Clear and re-render all indicators
        g.selectAll('.indicator-line').remove();

        const chartData = window.chartData;
        const currentXScale = window.baseXScale;
        const currentYScale = window.baseYScale;

        if (!chartData || !chartData.x || !currentXScale || !currentYScale) return;

        indicatorDataCache.forEach((indicatorData, instanceId) => {
            renderIndicatorLine(g, instanceId, indicatorData, chartData.x, currentXScale, currentYScale);
        });
    }

    /**
     * Refresh all indicators (e.g., after new candles loaded)
     */
    function refresh() {
        if (!isInitialized) return;

        // Recalculate all active indicators with fresh chart data
        activeRenders.forEach((renderInfo, instanceId) => {
            indicatorDataCache.delete(instanceId);
            calculateAndCacheIndicator(renderInfo.type, renderInfo.params, instanceId);
        });
    }

    /**
     * Clear all rendered indicators
     */
    function clearAll() {
        indicatorDataCache.clear();
        activeRenders.clear();
        colorAssignments.clear();
        colorIndex = 0;

        triggerRender();
    }

    // Public API
    return {
        init,
        calculateAndCacheIndicator,
        removeIndicator,
        refresh,
        clearAll,
        renderActiveIndicators
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Delay to ensure chart and DrawingManager are initialized first
        setTimeout(() => IndicatorEngine.init(), 1500);
    });
} else {
    setTimeout(() => IndicatorEngine.init(), 1500);
}

// Expose globally
if (typeof window !== 'undefined') {
    window.IndicatorEngine = IndicatorEngine;
}
