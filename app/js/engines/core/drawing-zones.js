/**
 * Drawing Zones Renderer
 * Displays rectangles for zones between external swing points
 * 
 * - Green rectangles: Bullish zones (Low → High)
 * - Red rectangles: Bearish zones (High → Low)
 */

const DrawingZones = (function() {
    'use strict';

    // State
    let initialized = false;
    let layerGroup = null;
    let xScale = null;
    let yScale = null;
    let cachedZones = null;
    let visible = true;

    // Colors
    const COLORS = {
        bullish: {
            fill: 'rgba(34, 197, 94, 0.15)',      // Green fill
            stroke: 'rgba(34, 197, 94, 0.6)',      // Green stroke
            text: '#22c55e'
        },
        bearish: {
            fill: 'rgba(239, 68, 68, 0.15)',      // Red fill
            stroke: 'rgba(239, 68, 68, 0.6)',      // Red stroke
            text: '#ef4444'
        }
    };

    /**
     * Initialize the drawing zones renderer
     * @param {Object} config - Configuration with chartGroup, xScale, yScale
     */
    function init(config) {
        if (config.chartGroup) {
            // Use the provided group directly (already created by CoreEngine)
            layerGroup = config.chartGroup;
        }
        
        xScale = config.xScale;
        yScale = config.yScale;
        initialized = true;
        
        console.log('[DrawingZones] Initialized');
    }

    /**
     * Update scales (on zoom/pan)
     */
    function updateScales(x, y) {
        xScale = x;
        yScale = y;
        if (cachedZones && visible) {
            render(cachedZones);
        }
    }

    /**
     * Render zones from data
     * @param {Array} zones - Array of zone objects from API
     */
    function render(zones) {
        if (!initialized || !layerGroup) {
            console.warn('[DrawingZones] Not initialized');
            return;
        }

        cachedZones = zones;

        // Clear existing
        layerGroup.selectAll('*').remove();

        if (!visible || !zones || zones.length === 0) {
            return;
        }

        // When showing filtered data, we typically get only the active zone
        const isFiltered = zones.length === 1;
        console.log(`[DrawingZones] Rendering ${zones.length} zone(s)${isFiltered ? ' (filtered)' : ''}`);

        zones.forEach((zone, index) => {
            renderZone(zone, index, isFiltered);
        });
    }

    /**
     * Render a single zone
     * @param {Object} zone - Zone data
     * @param {number} index - Zone index in the array
     * @param {boolean} isFiltered - Whether this is the only (active) zone
     */
    function renderZone(zone, index, isFiltered = false) {
        const colors = zone.direction === 'bullish' ? COLORS.bullish : COLORS.bearish;

        // Calculate rectangle bounds using zone_high and zone_low
        const x1 = xScale(zone.start_timestamp);
        const x2 = xScale(zone.end_timestamp);
        const yTop = yScale(zone.zone_high);
        const yBottom = yScale(zone.zone_low);

        if (isNaN(x1) || isNaN(x2) || isNaN(yTop) || isNaN(yBottom)) {
            return;
        }

        const width = Math.abs(x2 - x1);
        const height = Math.abs(yBottom - yTop);
        const xMin = Math.min(x1, x2);
        const yMin = Math.min(yTop, yBottom);

        // Adjust opacity for active zone vs others
        const fillOpacity = isFiltered ? 1 : 0.7;

        // Draw rectangle
        const rect = layerGroup.append('rect')
            .attr('class', `drawing-zone zone-${zone.direction}${isFiltered ? ' active' : ''}`)
            .attr('x', xMin)
            .attr('y', yMin)
            .attr('width', width)
            .attr('height', height)
            .attr('fill', colors.fill)
            .attr('stroke', colors.stroke)
            .attr('stroke-width', isFiltered ? 2 : 1)
            .attr('stroke-dasharray', isFiltered ? 'none' : '4,2')
            .attr('rx', 2)
            .attr('ry', 2)
            .attr('opacity', fillOpacity);

        // Add zone label
        const dirLabel = zone.direction === 'bullish' ? '▲ BULL' : '▼ BEAR';
        const label = isFiltered ? `${dirLabel} ZONE (Active)` : dirLabel;
        const labelY = yMin + 15;

        layerGroup.append('text')
            .attr('class', 'zone-label')
            .attr('x', xMin + 5)
            .attr('y', labelY)
            .attr('fill', colors.text)
            .attr('font-size', isFiltered ? '11px' : '10px')
            .attr('font-weight', '600')
            .attr('opacity', 0.9)
            .text(label);

        // Add zone info (candle count, internal swings)
        if (isFiltered) {
            layerGroup.append('text')
                .attr('class', 'zone-info')
                .attr('x', xMin + 5)
                .attr('y', labelY + 13)
                .attr('fill', colors.text)
                .attr('font-size', '9px')
                .attr('opacity', 0.7)
                .text(`${zone.candle_count} candles | ${zone.swing_count} internal swings`);
        } else {
            // Add zone index for non-active zones
            layerGroup.append('text')
                .attr('class', 'zone-index')
                .attr('x', xMin + 5)
                .attr('y', labelY + 12)
                .attr('fill', colors.text)
                .attr('font-size', '8px')
                .attr('opacity', 0.6)
                .text(`#${index}`);
        }

        // Draw start/end markers
        drawSwingMarker(zone.start_timestamp, zone.start_price, zone.start_kind, colors);
        drawSwingMarker(zone.end_timestamp, zone.end_price, zone.end_kind, colors);
    }

    /**
     * Draw a small marker at swing point
     */
    function drawSwingMarker(timestamp, price, kind, colors) {
        const x = xScale(timestamp);
        const y = yScale(price);

        if (isNaN(x) || isNaN(y)) return;

        layerGroup.append('circle')
            .attr('class', 'zone-swing-marker')
            .attr('cx', x)
            .attr('cy', y)
            .attr('r', 4)
            .attr('fill', colors.stroke)
            .attr('stroke', '#fff')
            .attr('stroke-width', 1);
    }

    /**
     * Toggle visibility
     */
    function toggle(show) {
        visible = show !== undefined ? show : !visible;
        if (layerGroup) {
            layerGroup.style('display', visible ? null : 'none');
        }
        if (visible && cachedZones) {
            render(cachedZones);
        }
        return visible;
    }

    /**
     * Clear all zones
     */
    function clear() {
        if (layerGroup) {
            layerGroup.selectAll('*').remove();
        }
        cachedZones = null;
    }

    /**
     * Get current visibility state
     */
    function isVisible() {
        return visible;
    }

    /**
     * Debug: Log zone details to console
     */
    function debugZones() {
        if (!cachedZones) {
            console.log('[DrawingZones] No zones cached');
            return;
        }

        console.log('='.repeat(60));
        console.log('[DrawingZones] ZONES DEBUG');
        console.log('='.repeat(60));
        console.log(`Total zones: ${cachedZones.length}`);

        cachedZones.forEach((zone, i) => {
            const dir = zone.direction === 'bullish' ? '🟢' : '🔴';
            console.log(`\n${dir} Zone #${i}: ${zone.direction.toUpperCase()}`);
            console.log(`   Start: ${zone.start_kind} @ ${zone.start_price.toFixed(2)} (idx: ${zone.start_index})`);
            console.log(`   End:   ${zone.end_kind} @ ${zone.end_price.toFixed(2)} (idx: ${zone.end_index})`);
            console.log(`   Range: ${zone.zone_low.toFixed(2)} - ${zone.zone_high.toFixed(2)}`);
            console.log(`   Candles: ${zone.candle_count}, Internal swings: ${zone.swing_count}`);
        });

        return cachedZones;
    }

    // Public API
    return {
        init,
        updateScales,
        render,
        toggle,
        clear,
        isVisible,
        debugZones,
        getZones: () => cachedZones
    };
})();

// Export for global access
if (typeof window !== 'undefined') {
    window.DrawingZones = DrawingZones;
}

