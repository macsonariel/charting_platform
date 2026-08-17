/**
 * Drawing Manager - Centralized control for all chart overlays
 * 
 * Solves common issues:
 * - Drawings disappearing on chart updates
 * - Drawings not following pan/zoom
 * - Code duplication across drawing types
 * 
 * Usage:
 *   DrawingManager.init(chartG, clipPathId);
 *   DrawingManager.register('sr-zones', { ... });
 *   DrawingManager.refresh();  // On symbol/timeframe change
 *   DrawingManager.updateScales(xScale, yScale);  // On pan/zoom
 */

const DrawingManager = (function () {

    // Private state
    let _chartG = null;           // Main chart <g> element
    let _drawingLayer = null;     // Persistent drawing layer
    let _clipPathId = null;       // Clip path ID for chart bounds
    let _xScale = null;           // Current x scale
    let _yScale = null;           // Current y scale
    let _symbol = null;           // Current symbol
    let _timeframe = null;        // Current timeframe
    let _initialized = false;

    // Performance optimization: debounce and RAF
    let _updateDebounceTimer = null;
    let _pendingScaleUpdate = null;
    const UPDATE_DEBOUNCE_MS = 16; // ~60fps

    // Registered drawing types
    const _drawings = new Map();

    // Cached data per drawing type
    const _dataCache = new Map();

    /**
     * Drawing configuration interface:
     * {
     *   enabled: boolean,
     *   fetchData: async (symbol, timeframe) => data,
     *   render: (g, data, xScale, yScale) => void,
     *   update: (g, data, xScale, yScale) => void,  // Optional: for scale updates
     *   clear: (g) => void  // Optional: custom clear logic
     * }
     */

    return {
        /**
         * Initialize the drawing manager
         * @param {d3.Selection} chartG - The main chart group element
         * @param {string} clipPathId - The clip path ID for chart bounds
         */
        init(chartG, clipPathId = 'chart-clip') {
            if (!chartG) {
                console.error('❌ DrawingManager: chartG is required');
                return false;
            }

            _chartG = chartG;
            _clipPathId = clipPathId;

            // Create persistent drawing layer (inserted before candlesticks so drawings are behind)
            _drawingLayer = _chartG.select('.drawing-manager-layer');
            if (_drawingLayer.empty()) {
                _drawingLayer = _chartG.insert('g', ':first-child')
                    .attr('class', 'drawing-manager-layer')
                    .attr('clip-path', `url(#${clipPathId})`);
            }

            _initialized = true;
            console.log('✅ DrawingManager initialized');
            return true;
        },

        /**
         * Register a new drawing type
         * @param {string} name - Unique name for this drawing type
         * @param {Object} config - Drawing configuration
         */
        register(name, config) {
            if (!name || !config) {
                console.error('❌ DrawingManager: name and config required');
                return;
            }

            // Ensure required functions exist
            if (typeof config.fetchData !== 'function') {
                console.error(`❌ DrawingManager: fetchData function required for '${name}'`);
                return;
            }
            if (typeof config.render !== 'function') {
                console.error(`❌ DrawingManager: render function required for '${name}'`);
                return;
            }

            // Create a group for this drawing type
            let drawingG = null;
            if (_drawingLayer) {
                drawingG = _drawingLayer.select(`.drawing-${name}`);
                if (drawingG.empty()) {
                    drawingG = _drawingLayer.append('g')
                        .attr('class', `drawing-${name}`);
                }
            }

            _drawings.set(name, {
                ...config,
                enabled: config.enabled !== false,  // Default to enabled
                group: drawingG
            });

            console.log(`📐 DrawingManager: registered '${name}'`);
        },

        /**
         * Set current symbol and timeframe
         */
        setContext(symbol, timeframe) {
            const changed = symbol !== _symbol || timeframe !== _timeframe;
            _symbol = symbol;
            _timeframe = timeframe;
            return changed;
        },

        /**
         * Update scale references (call on every pan/zoom)
         */
        setScales(xScale, yScale) {
            _xScale = xScale;
            _yScale = yScale;
        },

        /**
         * Full refresh - fetch data and redraw all enabled drawings
         * Call when symbol/timeframe changes or on initial load
         */
        async refresh() {
            if (!_initialized) {
                console.warn('⚠️ DrawingManager not initialized');
                return;
            }

            console.log('🔄 DrawingManager: refreshing all drawings...');

            const promises = [];

            for (const [name, drawing] of _drawings) {
                if (!drawing.enabled) continue;

                promises.push(this._refreshDrawing(name, drawing));
            }

            await Promise.all(promises);
            console.log('✅ DrawingManager: refresh complete');
        },

        /**
         * Refresh a single drawing type
         */
        async _refreshDrawing(name, drawing) {
            try {
                // Fetch fresh data
                const data = await drawing.fetchData(_symbol, _timeframe);

                // Cache the data
                _dataCache.set(name, data);

                // Clear existing elements
                if (drawing.group) {
                    drawing.group.selectAll('*').remove();
                }

                // Render with fresh data
                if (drawing.group && _xScale && _yScale) {
                    drawing.render(drawing.group, data, _xScale, _yScale);
                }

            } catch (error) {
                console.error(`❌ DrawingManager: error refreshing '${name}'`, error);
            }
        },

        /**
         * Update drawing positions based on current scales
         * Call on pan/zoom - uses cached data, no API fetch
         * Debounced to prevent thrashing during rapid pan/zoom
         */
        updateScales(xScale, yScale) {
            if (!_initialized) return;

            _xScale = xScale;
            _yScale = yScale;

            // Cancel any pending update
            if (_updateDebounceTimer) {
                clearTimeout(_updateDebounceTimer);
            }
            if (_pendingScaleUpdate) {
                cancelAnimationFrame(_pendingScaleUpdate);
            }

            // Debounce the actual update
            _updateDebounceTimer = setTimeout(() => {
                _pendingScaleUpdate = requestAnimationFrame(() => {
                    this._performScaleUpdate();
                    _pendingScaleUpdate = null;
                });
                _updateDebounceTimer = null;
            }, UPDATE_DEBOUNCE_MS);
        },

        /**
         * Internal: Actually perform the scale update (called after debounce)
         */
        _performScaleUpdate() {
            for (const [name, drawing] of _drawings) {
                if (!drawing.enabled || !drawing.group) continue;

                const data = _dataCache.get(name);
                if (!data) continue;

                // Clear and re-render with new scales
                // (Using cached data - no API call)
                drawing.group.selectAll('*').remove();

                if (typeof drawing.update === 'function') {
                    // Use custom update if provided
                    drawing.update(drawing.group, data, _xScale, _yScale);
                } else {
                    // Fall back to full render
                    drawing.render(drawing.group, data, _xScale, _yScale);
                }
            }
        },

        /**
         * Toggle a drawing type on/off
         */
        toggle(name) {
            const drawing = _drawings.get(name);
            if (!drawing) {
                console.warn(`⚠️ DrawingManager: unknown drawing '${name}'`);
                return false;
            }

            drawing.enabled = !drawing.enabled;

            if (drawing.enabled) {
                // Re-render if we have cached data
                const data = _dataCache.get(name);
                if (data && drawing.group && _xScale && _yScale) {
                    drawing.render(drawing.group, data, _xScale, _yScale);
                }
            } else {
                // Clear the drawing
                if (drawing.group) {
                    drawing.group.selectAll('*').remove();
                }
            }

            console.log(`📐 DrawingManager: '${name}' ${drawing.enabled ? 'enabled' : 'disabled'}`);
            return drawing.enabled;
        },

        /**
         * Check if a drawing type is enabled
         */
        isEnabled(name) {
            const drawing = _drawings.get(name);
            return drawing ? drawing.enabled : false;
        },

        /**
         * Clear all drawings
         */
        clearAll() {
            for (const [name, drawing] of _drawings) {
                if (drawing.group) {
                    drawing.group.selectAll('*').remove();
                }
            }
            _dataCache.clear();
        },

        /**
         * Clear a specific drawing type
         */
        clear(name) {
            const drawing = _drawings.get(name);
            if (drawing && drawing.group) {
                drawing.group.selectAll('*').remove();
                _dataCache.delete(name);
            }
        },

        /**
         * Get list of registered drawing types
         */
        getRegisteredDrawings() {
            return Array.from(_drawings.keys());
        },

        /**
         * Check if initialized
         */
        get isInitialized() {
            return _initialized;
        }
    };
})();

// Make globally available
if (typeof window !== 'undefined') {
    window.DrawingManager = DrawingManager;
}
