/**
 * S/R Zones Drawing Module
 * 
 * Draws Support and Resistance zones on the chart as shaded rectangles.
 * Uses DrawingManager for lifecycle management.
 */

const SRZonesDrawing = {

    /**
     * Register with DrawingManager
     */
    register() {
        if (typeof DrawingManager === 'undefined') {
            console.error('❌ SRZonesDrawing: DrawingManager not found');
            return;
        }

        DrawingManager.register('sr-zones', {
            enabled: true,
            fetchData: this.fetchData.bind(this),
            render: this.render.bind(this),
            update: this.render.bind(this)  // Same as render (just redraws)
        });

        console.log('📊 SRZonesDrawing registered');
    },

    /**
     * Fetch S/R zone data from API
     */
    async fetchData(symbol, timeframe) {
        const url = `/api/core/summary?symbol=${symbol}&timeframe=${timeframe}&periods=300`;

        try {
            const response = await fetch(url);
            if (!response.ok) {
                console.warn('  ⚠️ SRZones: API returned', response.status);
                return null;
            }

            const data = await response.json();
            return data.sr_zones || null;

        } catch (error) {
            console.error('  ❌ SRZones: fetch error', error);
            return null;
        }
    },

    /**
     * Render S/R zones
     * @param {d3.Selection} g - SVG group element
     * @param {Object} data - S/R zone data
     * @param {d3.Scale} xScale - X axis scale
     * @param {d3.Scale} yScale - Y axis scale
     */
    render(g, data, xScale, yScale) {
        if (!g || !data) return;

        // Get chart dimensions
        const xRange = xScale.range();
        const xStart = Math.min(xRange[0], xRange[1]);
        const xEnd = Math.max(xRange[0], xRange[1]);

        // Render resistance zones
        if (data.resistance && data.resistance.length > 0) {
            data.resistance.forEach((zone, i) => {
                this._renderZone(g, zone, i, 'resistance', xStart, xEnd, yScale);
            });
        }

        // Render support zones
        if (data.support && data.support.length > 0) {
            data.support.forEach((zone, i) => {
                this._renderZone(g, zone, i, 'support', xStart, xEnd, yScale);
            });
        }
    },

    /**
     * Render a single zone
     */
    _renderZone(g, zone, index, type, xStart, xEnd, yScale) {
        const isResistance = type === 'resistance';
        const color = isResistance ? '#ef4444' : '#22c55e';
        const label = isResistance ? `R${index + 1}` : `S${index + 1}`;

        const yTop = yScale(zone.high);
        const yBottom = yScale(zone.low);
        const height = Math.abs(yBottom - yTop);
        const opacity = Math.max(0.15, Math.min(0.4, zone.strength * 0.5));

        // Draw zone rectangle
        g.append('rect')
            .attr('class', `sr-zone sr-zone-${type}`)
            .attr('x', xStart)
            .attr('y', Math.min(yTop, yBottom))
            .attr('width', xEnd - xStart)
            .attr('height', height)
            .attr('fill', color)
            .attr('fill-opacity', opacity)
            .attr('stroke', color)
            .attr('stroke-width', 1)
            .attr('stroke-opacity', 0.5)
            .style('pointer-events', 'none');

        // Add label (only first 3 zones)
        if (index < 3) {
            const priceText = zone.midpoint.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });

            g.append('text')
                .attr('class', `sr-zone-label sr-zone-label-${type}`)
                .attr('x', xStart + 10)
                .attr('y', (yTop + yBottom) / 2 + 4)
                .attr('fill', color)
                .attr('font-size', '10px')
                .attr('font-weight', 'bold')
                .attr('font-family', 'monospace')
                .style('pointer-events', 'none')
                .text(`${label}: ${priceText}`);
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.SRZonesDrawing = SRZonesDrawing;
}
