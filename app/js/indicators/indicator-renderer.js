/**
 * Indicator Renderer
 * D3.js rendering logic for drawing indicators on the chart
 */

const IndicatorRenderer = (function () {

    // Store rendered indicator elements
    const renderedIndicators = new Map();

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

    // Track color assignments
    let colorIndex = 0;
    const colorAssignments = new Map();

    /**
     * Get a color for an indicator (consistent across renders)
     * @param {string} instanceId - Unique instance ID
     * @returns {string} - Color hex code
     */
    function getIndicatorColor(instanceId) {
        if (!colorAssignments.has(instanceId)) {
            colorAssignments.set(instanceId, DEFAULT_COLORS[colorIndex % DEFAULT_COLORS.length]);
            colorIndex++;
        }
        return colorAssignments.get(instanceId);
    }

    /**
     * Draw a line indicator (SMA, EMA, etc.)
     * @param {Object} config - Configuration object
     * @param {string} config.instanceId - Unique instance ID
     * @param {string} config.name - Display name (e.g., "SMA(20)")
     * @param {Array<Date>} config.timestamps - X-axis values (timestamps)
     * @param {Array<number|null>} config.values - Y-axis values (indicator values)
     * @param {d3.scale} config.xScale - D3 x-axis scale
     * @param {d3.scale} config.yScale - D3 y-axis scale
     * @param {d3.selection} config.container - D3 selection for the chart group
     * @param {string} [config.color] - Optional line color
     * @param {number} [config.strokeWidth] - Optional stroke width
     */
    function drawLine(config) {
        const {
            instanceId,
            name,
            timestamps,
            values,
            xScale,
            yScale,
            container,
            color = getIndicatorColor(instanceId),
            strokeWidth = 1.5
        } = config;

        if (!container || !xScale || !yScale || !timestamps || !values) {
            console.warn('IndicatorRenderer.drawLine: Missing required parameters');
            return;
        }

        // Remove existing indicator if present
        removeLine(instanceId, container);

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

        if (dataPoints.length === 0) {
            console.warn(`IndicatorRenderer.drawLine: No valid data points for ${name}`);
            return;
        }

        // Create indicator group
        const indicatorGroup = container.append('g')
            .attr('class', `indicator-line indicator-${instanceId}`)
            .attr('clip-path', 'url(#chart-clip)')
            .style('cursor', 'pointer');

        // Create line generator
        const lineGenerator = d3.line()
            .x(d => xScale(d.timestamp))
            .y(d => yScale(d.value))
            .curve(d3.curveMonotoneX); // Smooth curve

        // Draw invisible wider line for easier mouse interaction
        indicatorGroup.append('path')
            .datum(dataPoints)
            .attr('class', 'indicator-path-hitbox')
            .attr('d', lineGenerator)
            .attr('fill', 'none')
            .attr('stroke', 'transparent')
            .attr('stroke-width', 12)
            .style('cursor', 'pointer');

        // Draw the visible line
        const visiblePath = indicatorGroup.append('path')
            .datum(dataPoints)
            .attr('class', 'indicator-path')
            .attr('d', lineGenerator)
            .attr('fill', 'none')
            .attr('stroke', color)
            .attr('stroke-width', strokeWidth)
            .attr('stroke-opacity', 0.85)
            .attr('stroke-linecap', 'round')
            .attr('stroke-linejoin', 'round');

        // Add hover effects
        indicatorGroup.on('mouseenter', function () {
            d3.select(this).select('.indicator-path')
                .attr('stroke-width', strokeWidth + 1)
                .attr('stroke-opacity', 1);
        }).on('mouseleave', function () {
            d3.select(this).select('.indicator-path')
                .attr('stroke-width', strokeWidth)
                .attr('stroke-opacity', 0.85);
        });

        // Add right-click context menu
        indicatorGroup.on('contextmenu', function (event) {
            event.preventDefault();
            event.stopPropagation();
            showIndicatorContextMenu(event, instanceId, name);
        });

        // Add label at the end of the line
        const lastPoint = dataPoints[dataPoints.length - 1];
        if (lastPoint) {
            indicatorGroup.append('text')
                .attr('class', 'indicator-label')
                .attr('x', xScale(lastPoint.timestamp) + 5)
                .attr('y', yScale(lastPoint.value))
                .attr('fill', color)
                .attr('font-size', '10px')
                .attr('font-weight', '500')
                .attr('dominant-baseline', 'middle')
                .text(name);
        }

        // Store reference
        renderedIndicators.set(instanceId, {
            group: indicatorGroup,
            config: config
        });

        console.log(`📈 Rendered ${name} with ${dataPoints.length} points`);
    }

    /**
     * Show context menu for indicator right-click
     */
    function showIndicatorContextMenu(event, instanceId, name) {
        // Remove any existing context menu
        d3.select('.indicator-context-menu').remove();

        const menu = d3.select('body').append('div')
            .attr('class', 'indicator-context-menu')
            .style('position', 'fixed')
            .style('left', `${event.clientX}px`)
            .style('top', `${event.clientY}px`)
            .style('background', 'var(--bg-secondary)')
            .style('border', '1px solid var(--border-color)')
            .style('border-radius', '8px')
            .style('box-shadow', '0 4px 16px rgba(0,0,0,0.2)')
            .style('padding', '4px')
            .style('z-index', '10000')
            .style('min-width', '150px');

        // Settings option
        menu.append('div')
            .attr('class', 'context-menu-item')
            .style('padding', '8px 12px')
            .style('cursor', 'pointer')
            .style('border-radius', '4px')
            .style('font-size', '13px')
            .style('color', 'var(--text-primary)')
            .style('display', 'flex')
            .style('align-items', 'center')
            .style('gap', '8px')
            .html(`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg> Settings...`)
            .on('mouseenter', function () { d3.select(this).style('background', 'var(--bg-hover)'); })
            .on('mouseleave', function () { d3.select(this).style('background', 'transparent'); })
            .on('click', function () {
                menu.remove();
                if (window.IndicatorSettings?.openSettings) {
                    window.IndicatorSettings.openSettings(instanceId);
                }
            });

        // Remove option
        menu.append('div')
            .attr('class', 'context-menu-item')
            .style('padding', '8px 12px')
            .style('cursor', 'pointer')
            .style('border-radius', '4px')
            .style('font-size', '13px')
            .style('color', 'var(--candle-down)')
            .style('display', 'flex')
            .style('align-items', 'center')
            .style('gap', '8px')
            .html(`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg> Remove ${name}`)
            .on('mouseenter', function () { d3.select(this).style('background', 'rgba(242,54,69,0.1)'); })
            .on('mouseleave', function () { d3.select(this).style('background', 'transparent'); })
            .on('click', function () {
                menu.remove();
                if (window.IndicatorManager?.removeIndicator) {
                    window.IndicatorManager.removeIndicator(instanceId);
                }
            });

        // Click anywhere else to close
        d3.select('body').on('click.contextmenu', function () {
            menu.remove();
            d3.select('body').on('click.contextmenu', null);
        });
    }

    /**
     * Draw Bollinger Bands (3 lines: upper, middle, lower + fill)
     * @param {Object} config - Configuration object
     */
    function drawBollingerBands(config) {
        const {
            instanceId,
            name,
            timestamps,
            upper,
            middle,
            lower,
            xScale,
            yScale,
            container,
            color = '#2962ff',
            strokeWidth = 1
        } = config;

        if (!container || !xScale || !yScale) {
            console.warn('IndicatorRenderer.drawBollingerBands: Missing required parameters');
            return;
        }

        // Remove existing
        removeLine(instanceId, container);

        // Create data points
        const dataPoints = [];
        for (let i = 0; i < timestamps.length; i++) {
            if (upper[i] !== null && middle[i] !== null && lower[i] !== null) {
                dataPoints.push({
                    timestamp: timestamps[i],
                    upper: upper[i],
                    middle: middle[i],
                    lower: lower[i]
                });
            }
        }

        if (dataPoints.length === 0) return;

        // Create indicator group
        const indicatorGroup = container.append('g')
            .attr('class', `indicator-bb indicator-${instanceId}`)
            .attr('clip-path', 'url(#chart-clip)');

        // Create area fill between upper and lower
        const areaGenerator = d3.area()
            .x(d => xScale(d.timestamp))
            .y0(d => yScale(d.lower))
            .y1(d => yScale(d.upper))
            .curve(d3.curveMonotoneX);

        indicatorGroup.append('path')
            .datum(dataPoints)
            .attr('class', 'bb-fill')
            .attr('d', areaGenerator)
            .attr('fill', color)
            .attr('fill-opacity', 0.1);

        // Draw upper line
        const lineGenerator = d3.line()
            .x(d => xScale(d.timestamp))
            .curve(d3.curveMonotoneX);

        indicatorGroup.append('path')
            .datum(dataPoints)
            .attr('class', 'bb-upper')
            .attr('d', lineGenerator.y(d => yScale(d.upper)))
            .attr('fill', 'none')
            .attr('stroke', color)
            .attr('stroke-width', strokeWidth)
            .attr('stroke-opacity', 0.6)
            .attr('stroke-dasharray', '4,2');

        // Draw middle line
        indicatorGroup.append('path')
            .datum(dataPoints)
            .attr('class', 'bb-middle')
            .attr('d', lineGenerator.y(d => yScale(d.middle)))
            .attr('fill', 'none')
            .attr('stroke', color)
            .attr('stroke-width', strokeWidth)
            .attr('stroke-opacity', 0.85);

        // Draw lower line
        indicatorGroup.append('path')
            .datum(dataPoints)
            .attr('class', 'bb-lower')
            .attr('d', lineGenerator.y(d => yScale(d.lower)))
            .attr('fill', 'none')
            .attr('stroke', color)
            .attr('stroke-width', strokeWidth)
            .attr('stroke-opacity', 0.6)
            .attr('stroke-dasharray', '4,2');

        // Store reference
        renderedIndicators.set(instanceId, {
            group: indicatorGroup,
            config: config
        });

        console.log(`📊 Rendered ${name} Bollinger Bands`);
    }

    /**
     * Remove an indicator line from the chart
     * @param {string} instanceId - Instance ID to remove
     * @param {d3.selection} [container] - Optional container (for fallback)
     */
    function removeLine(instanceId, container) {
        const existing = renderedIndicators.get(instanceId);
        if (existing && existing.group) {
            existing.group.remove();
            renderedIndicators.delete(instanceId);
            console.log(`🗑️ Removed indicator ${instanceId}`);
        } else if (container) {
            // Fallback: try to find by class
            container.selectAll(`.indicator-${instanceId}`).remove();
        }
    }

    /**
     * Update all rendered indicators with new scales
     * Call this on zoom/pan
     * @param {d3.scale} xScale - Updated x-axis scale
     * @param {d3.scale} yScale - Updated y-axis scale
     */
    function updateScales(xScale, yScale) {
        renderedIndicators.forEach((indicator, instanceId) => {
            const config = indicator.config;

            // Re-draw with new scales
            if (config.upper && config.middle && config.lower) {
                // Bollinger Bands
                drawBollingerBands({
                    ...config,
                    xScale,
                    yScale
                });
            } else {
                // Line indicator
                drawLine({
                    ...config,
                    xScale,
                    yScale
                });
            }
        });
    }

    /**
     * Clear all rendered indicators
     */
    function clearAll() {
        renderedIndicators.forEach((indicator, instanceId) => {
            if (indicator.group) {
                indicator.group.remove();
            }
        });
        renderedIndicators.clear();
        console.log('🧹 Cleared all indicators');
    }

    /**
     * Get list of currently rendered indicator IDs
     * @returns {Array<string>} - Array of instance IDs
     */
    function getRenderedIndicators() {
        return Array.from(renderedIndicators.keys());
    }

    // Public API
    return {
        drawLine,
        drawBollingerBands,
        removeLine,
        updateScales,
        clearAll,
        getRenderedIndicators,
        getIndicatorColor
    };
})();

// Expose globally
if (typeof window !== 'undefined') {
    window.IndicatorRenderer = IndicatorRenderer;
}
