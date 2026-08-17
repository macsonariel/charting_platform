/**
 * Core Engine - Main Integration Module
 * Renders Core engine analysis (swings, structure, levels, moves) on the D3 chart
 * 
 * This uses the Core engine's data directly, showing the "raw" analysis
 * before any engine-specific (PA, SMC, ICT) interpretation.
 */

const CoreEngine = (function () {
    'use strict';

    // State
    let initialized = false;
    let currentSymbol = null;
    let currentTimeframe = null;
    let candleCount = 400;

    // Chart references
    let chartGroup = null;
    let xScale = null;
    let yScale = null;
    let layerGroup = null;

    // Cached data
    let cachedData = null;
    let fullData = null;  // Unfiltered data for reference

    // Zone navigation state
    let currentZoneIndex = 0;
    let totalZones = 0;
    let useZoneFiltering = true;  // Filter drawings to active zone only

    // Visibility states
    const visibility = {
        swings: false,      // Core swings (off by default)
        structure: false,   // Core BOS/CHoCH (off by default)
        levels: false,      // Protected levels (off by default)
        moves: false,       // Move backgrounds (off by default)
        zones: true,        // Drawing zones (on by default for testing)
        sr_zones: false,    // S/R zones (off by default)
        fvgs: false,        // Fair Value Gaps (off by default)
        liquidity: false    // Liquidity pools (off by default)
    };

    // Colors
    const COLORS = {
        swing_high: '#22c55e',      // Green
        swing_low: '#ef4444',       // Red
        swing_protected: '#8b5cf6', // Purple for protected
        swing_line: '#6b7280',      // Gray for zig-zag line
        bos_bullish: '#22c55e',
        bos_bearish: '#ef4444',
        choch_bullish: '#3b82f6',   // Blue
        choch_bearish: '#8b5cf6',   // Purple
        protected_high: '#22c55e33',
        protected_low: '#ef444433',
        move_bullish: 'rgba(34, 197, 94, 0.05)',
        move_bearish: 'rgba(239, 68, 68, 0.05)'
    };

    /**
     * Initialize the Core engine
     * @param {Object} config - Configuration
     */
    function init(config) {
        chartGroup = config.chartGroup;
        xScale = config.xScale;
        yScale = config.yScale;
        currentSymbol = config.symbol || 'BTCUSDT';
        currentTimeframe = config.timeframe || '1h';
        candleCount = config.candleCount || 400;

        // Create dedicated layer group for Core engine
        if (chartGroup) {
            layerGroup = chartGroup.append('g')
                .attr('class', 'core-engine-layer');

            // Create sub-groups for each layer type (order = z-index, first = back)
            layerGroup.append('g').attr('class', 'core-layer-zones');      // Drawing zones (behind everything)
            layerGroup.append('g').attr('class', 'core-layer-moves');      // Move backgrounds
            layerGroup.append('g').attr('class', 'core-layer-sr-zones');   // S/R zones
            layerGroup.append('g').attr('class', 'core-layer-fvgs');       // Fair Value Gaps
            layerGroup.append('g').attr('class', 'core-layer-liquidity');  // Liquidity pools
            layerGroup.append('g').attr('class', 'core-layer-levels');     // Protected levels
            layerGroup.append('g').attr('class', 'core-layer-structure');  // BOS/CHoCH
            layerGroup.append('g').attr('class', 'core-layer-swings');     // Swing points (on top)

            // Initialize DrawingZones renderer
            if (typeof DrawingZones !== 'undefined') {
                DrawingZones.init({
                    chartGroup: layerGroup.select('.core-layer-zones'),
                    xScale: xScale,
                    yScale: yScale
                });
            }

            console.log(`[CoreEngine] Layer groups created:`, layerGroup.node());
        } else {
            console.warn('[CoreEngine] No chartGroup provided!');
        }

        initialized = true;
        console.log(`✅ CoreEngine initialized for ${currentSymbol} ${currentTimeframe}`);

        if (Object.values(visibility).some(Boolean)) {
            setTimeout(() => loadAnalysis(), 0);
        }
    }

    /**
     * Load and render analysis
     * @param {boolean} forceRefresh - Force reload even if data is cached
     */
    async function loadAnalysis(forceRefresh = false) {
        if (!initialized) {
            console.warn('CoreEngine not initialized');
            return;
        }

        try {
            console.log(`🔧 Loading Core analysis for ${currentSymbol} ${currentTimeframe} (zone ${currentZoneIndex})...`);

            let data;

            if (useZoneFiltering) {
                // Use zone-filtered render endpoint
                data = await CoreEngineAPI.getRender(
                    currentSymbol,
                    currentTimeframe,
                    candleCount,
                    currentZoneIndex,
                    false  // showAllZones
                );

                // Update zone navigation state
                if (data.zone_nav) {
                    totalZones = data.zone_nav.total_zones;
                }
            } else {
                // Use unfiltered analysis endpoint
                data = await CoreEngineAPI.getAnalysis(
                    currentSymbol,
                    currentTimeframe,
                    candleCount
                );
            }

            cachedData = data;

            // Render each layer based on visibility
            renderAll();

            const counts = {
                swings: data.swings?.length || 0,
                structure_breaks: data.structure_breaks?.length || 0,
                character_changes: data.character_changes?.length || 0,
                protected_levels: data.protected_levels?.length || 0,
                zones: data.zones?.length || data.drawing_zones?.length || 0,
                active_zone: data.active_zone ? 'Zone ' + currentZoneIndex : 'All'
            };

            console.log(`✅ Core analysis loaded:`, counts);

            // Dispatch event
            window.dispatchEvent(new CustomEvent('coreEngineLoaded', {
                detail: {
                    symbol: currentSymbol,
                    timeframe: currentTimeframe,
                    data,
                    counts,
                    zoneIndex: currentZoneIndex,
                    totalZones: totalZones
                }
            }));

        } catch (error) {
            console.error('Failed to load Core analysis:', error);
            cachedData = null;
            renderAll();
            window.dispatchEvent(new CustomEvent('coreEngineError', {
                detail: { symbol: currentSymbol, timeframe: currentTimeframe }
            }));
        }
    }

    /**
     * Get zone name from index
     * @param {number} index - Zone index
     * @returns {string} Zone name (live, prev, zone_a, zone_b, etc.)
     */
    function getZoneName(index) {
        if (index === -1) return 'live';
        if (index === 0) return 'prev';
        const letter = String.fromCharCode('a'.charCodeAt(0) + index - 1);
        return `zone_${letter}`;
    }

    /**
     * Get zone index from name
     * @param {string} name - Zone name
     * @returns {number} Zone index
     */
    function getZoneIndex(name) {
        name = name.toLowerCase().trim();
        if (name === 'live') return -1;
        if (name === 'prev') return 0;
        if (name.startsWith('zone_')) {
            const letter = name.replace('zone_', '');
            if (letter.length === 1) {
                return letter.charCodeAt(0) - 'a'.charCodeAt(0) + 1;
            }
        }
        return 0;
    }

    /**
     * Navigate to an older zone (further back in time)
     * From live → prev → zone_a → zone_b...
     */
    async function olderZone() {
        if (currentZoneIndex === -1) {
            // Move from live to prev
            currentZoneIndex = 0;
            console.log(`[CoreEngine] ← Moving from live to prev zone`);
            await loadAnalysis();
            return { index: 0, name: 'prev' };
        }

        if (currentZoneIndex < totalZones - 1) {
            currentZoneIndex++;
            const name = getZoneName(currentZoneIndex);
            console.log(`[CoreEngine] ← Moving to older zone: ${name} (index ${currentZoneIndex})`);
            await loadAnalysis();
            return { index: currentZoneIndex, name };
        }
        console.log(`[CoreEngine] Already at oldest zone: ${getZoneName(currentZoneIndex)}`);
        return { index: currentZoneIndex, name: getZoneName(currentZoneIndex) };
    }

    /**
     * Navigate to a newer zone (closer to current)
     * From zone_a → prev → live
     */
    async function newerZone() {
        if (currentZoneIndex > 0) {
            // Move from zone_a/b/c towards prev
            currentZoneIndex--;
            const name = getZoneName(currentZoneIndex);
            console.log(`[CoreEngine] → Moving to newer zone: ${name} (index ${currentZoneIndex})`);
            await loadAnalysis();
            return { index: currentZoneIndex, name };
        } else if (currentZoneIndex === 0) {
            // Move from prev to live
            return await goToZone('live');
        }
        console.log(`[CoreEngine] Already at live zone`);
        return { index: -1, name: 'live' };
    }

    /**
     * Jump to a specific zone by name or index
     * @param {string|number} target - Zone name ("live", "prev", "zone_a") or index (-1 for live)
     */
    async function goToZone(target) {
        let index;
        if (typeof target === 'string') {
            index = getZoneIndex(target);
        } else {
            index = target;
        }

        // Handle live zone (index -1) - from end of prev_zone to current candle
        if (index === -1) {
            currentZoneIndex = -1;
            console.log(`[CoreEngine] Jumping to LIVE zone (current trading area)`);

            // Call render endpoint with zone_index=-1 to get live zone
            try {
                const data = await CoreEngineAPI.getRender(
                    currentSymbol,
                    currentTimeframe,
                    candleCount,
                    -1,    // zone_index = -1 for live zone
                    false  // show_all_zones = false (we want filtered to live zone)
                );

                if (data.zone_nav) {
                    totalZones = data.zone_nav.total_zones;
                }

                cachedData = data;
                renderAll();

                console.log(`✅ LIVE zone loaded: ${data.swings?.length || 0} swings, ${data.structure_breaks?.length || 0} BOS`);
            } catch (error) {
                console.error('Failed to load LIVE zone:', error);
            }

            return { index: -1, name: 'live' };
        }

        if (index >= 0 && index < totalZones) {
            currentZoneIndex = index;
            const name = getZoneName(index);
            console.log(`[CoreEngine] Jumping to zone: ${name} (index ${index})`);
            await loadAnalysis();
            return { index, name };
        }
        console.warn(`[CoreEngine] Invalid zone: ${target} (valid: -1 to ${totalZones - 1})`);
        return { index: currentZoneIndex, name: getZoneName(currentZoneIndex) };
    }

    /**
     * Toggle zone filtering on/off
     * @param {boolean} enabled - Whether to enable zone filtering
     */
    async function setZoneFiltering(enabled) {
        useZoneFiltering = enabled;
        console.log(`[CoreEngine] Zone filtering: ${enabled ? 'ON' : 'OFF'}`);
        await loadAnalysis();
    }

    /**
     * Get comprehensive zone information
     * @returns {Object} Zone info with naming
     */
    function zoneInfo() {
        const sep = '─'.repeat(50);
        console.log('\n' + sep);
        console.log('📍 ZONE INFORMATION');
        console.log(sep);

        if (!cachedData) {
            console.log('⚠️  No data loaded. Call CoreEngine.loadAnalysis() first.');
            return null;
        }

        // Current displayed zone
        const currentName = getZoneName(currentZoneIndex);
        console.log(`\n🎯 Currently Displaying: ${currentName.toUpperCase()}`);
        console.log(`   Index: ${currentZoneIndex} of ${totalZones - 1}`);

        // Zone info from API
        const zoneInfoData = cachedData.zone_info || {};
        const displayedZone = zoneInfoData.displayed_zone;

        if (displayedZone) {
            console.log(`   Direction: ${displayedZone.direction}`);
            console.log(`   Candles: ${displayedZone.start_index} → ${displayedZone.end_index} (${displayedZone.candle_count} candles)`);
        }

        // Live zone info
        const liveZone = zoneInfoData.live_zone;
        if (liveZone) {
            console.log(`\n🔴 LIVE Zone (current trading):`);
            console.log(`   Candles: ${liveZone.start_index} → ${liveZone.end_index} (${liveZone.candle_count} candles)`);
        }

        // All zones summary
        console.log(`\n📋 All Completed Zones (${totalZones} total):`);
        const allZones = zoneInfoData.all_zones || [];
        allZones.forEach(z => {
            const marker = z.is_displayed ? '→ ' : '  ';
            const dir = z.direction === 'bullish' ? '🟢' : '🔴';
            console.log(`${marker}${z.name.padEnd(8)} ${dir} ${z.direction.padEnd(8)} | ${z.candle_count} candles, ${z.swing_count} swings`);
        });

        // Navigation hints
        console.log(`\n🎮 Navigation:`);
        console.log(`   CoreEngine.newerZone()  → Move to more recent zone`);
        console.log(`   CoreEngine.olderZone()  → Move to older zone`);
        console.log(`   CoreEngine.goToZone('prev')  → Jump to prev_zone`);
        console.log(`   CoreEngine.goToZone('zone_a')  → Jump to zone_a`);
        console.log(sep + '\n');

        return {
            currentZone: currentName,
            currentIndex: currentZoneIndex,
            totalZones: totalZones,
            displayedZone: displayedZone,
            liveZone: liveZone,
            allZones: allZones,
            canGoNewer: currentZoneIndex > 0,
            canGoOlder: currentZoneIndex < totalZones - 1,
        };
    }

    /**
     * Render all visible layers
     */
    function renderAll() {
        if (!cachedData || !layerGroup) {
            console.warn('[CoreEngine] renderAll: no data or layer group');
            return;
        }

        console.log('[CoreEngine] renderAll - visibility:', visibility);
        console.log('[CoreEngine] renderAll - data keys:', Object.keys(cachedData));
        console.log('[CoreEngine] renderAll - swings:', cachedData.swings?.length, 'structure_breaks:', cachedData.structure_breaks?.length);

        // Clear existing
        layerGroup.selectAll('.core-layer-zones > *').remove();
        layerGroup.selectAll('.core-layer-moves > *').remove();
        layerGroup.selectAll('.core-layer-sr-zones > *').remove();
        layerGroup.selectAll('.core-layer-fvgs > *').remove();
        layerGroup.selectAll('.core-layer-liquidity > *').remove();
        layerGroup.selectAll('.core-layer-levels > *').remove();
        layerGroup.selectAll('.core-layer-structure > *').remove();
        layerGroup.selectAll('.core-layer-swings > *').remove();

        // Render each layer
        if (visibility.zones) {
            console.log('[CoreEngine] Rendering zones layer...');
            renderZones();
        }
        if (visibility.moves) renderMoves();
        if (visibility.sr_zones) {
            console.log('[CoreEngine] Rendering S/R zones layer...');
            renderSRZones();
        }
        if (visibility.fvgs) {
            console.log('[CoreEngine] Rendering FVGs layer...');
            renderFVGs();
        }
        if (visibility.liquidity) {
            console.log('[CoreEngine] Rendering liquidity layer...');
            renderLiquidity();
        }
        if (visibility.levels) renderLevels();
        if (visibility.structure) {
            console.log('[CoreEngine] Rendering structure layer...');
            renderStructure();
        }
        if (visibility.swings) {
            console.log('[CoreEngine] Rendering swings layer...');
            renderSwings();
        }
    }

    /**
     * Render drawing zones between external swings
     */
    function renderZones() {
        // Use 'zones' from filtered data or 'drawing_zones' from full data
        const zones = cachedData.zones || cachedData.drawing_zones || [];

        if (typeof DrawingZones !== 'undefined') {
            DrawingZones.render(zones);

            // Log zone info
            const activeZone = cachedData.active_zone;
            if (activeZone) {
                console.log(`[CoreEngine] Showing zone ${currentZoneIndex}: ${activeZone.direction} (${activeZone.candle_count} candles)`);
            } else {
                console.log(`[CoreEngine] Rendered ${zones.length} drawing zones`);
            }
        } else {
            console.warn('[CoreEngine] DrawingZones module not loaded');
        }
    }

    /**
     * Render swing points with zig-zag line
     */
    function renderSwings() {
        if (!cachedData?.swings || !layerGroup) {
            console.warn('[CoreEngine] renderSwings: no swings data');
            return;
        }

        const swingsLayer = layerGroup.select('.core-layer-swings');
        const swings = cachedData.swings;

        console.log(`[CoreEngine] renderSwings: ${swings.length} swings to render`);
        if (swings.length > 0) {
            console.log('[CoreEngine] First swing:', swings[0]);
        }

        // Sort swings by timestamp for zig-zag line
        const sortedSwings = [...swings].sort((a, b) => a.timestamp - b.timestamp);

        // Build zig-zag path connecting all swings
        const zigzagPoints = [];
        sortedSwings.forEach(swing => {
            const x = xScale(swing.timestamp);
            const y = yScale(swing.price);
            if (!isNaN(x) && !isNaN(y)) {
                zigzagPoints.push({ x, y, swing });
            }
        });

        // Draw zig-zag line if we have at least 2 points
        if (zigzagPoints.length >= 2) {
            const lineGenerator = d3.line()
                .x(d => d.x)
                .y(d => d.y);

            swingsLayer.append('path')
                .attr('class', 'core-zigzag-line')
                .attr('d', lineGenerator(zigzagPoints))
                .attr('fill', 'none')
                .attr('stroke', COLORS.swing_line || '#888')
                .attr('stroke-width', 1.5)
                .attr('stroke-dasharray', '4,2')
                .attr('opacity', 0.7);
        }

        let rendered = 0;
        swings.forEach(swing => {
            // Use timestamp for x-position (chart xScale expects timestamp, not bar index)
            const x = xScale(swing.timestamp);
            const y = yScale(swing.price);
            if (isNaN(x) || isNaN(y)) {
                return;
            }

            const isHigh = swing.kind === 'high';
            const isExternal = swing.degree === 'external';
            const color = isHigh ? COLORS.swing_high : COLORS.swing_low;
            const radius = isExternal ? 6 : 4;  // Larger for external
            const yOffset = isHigh ? -12 : 12;

            // Draw circle
            swingsLayer.append('circle')
                .attr('class', `core-swing core-swing-${swing.kind}${isExternal ? ' external' : ''}`)
                .attr('cx', x)
                .attr('cy', y)
                .attr('r', radius)
                .attr('fill', color)
                .attr('stroke', isExternal ? '#fff' : 'none')
                .attr('stroke-width', isExternal ? 1.5 : 0)
                .attr('opacity', swing.broken ? 0.5 : 1);

            // Draw label - prefix with EXT for external swings (HTF-aligned)
            const baseLabel = swing.label || (isHigh ? 'H' : 'L');
            const label = isExternal ? 'EXT ' + baseLabel : baseLabel;

            swingsLayer.append('text')
                .attr('class', 'core-swing-label')
                .attr('x', x)
                .attr('y', y + yOffset)
                .attr('text-anchor', 'middle')
                .attr('fill', color)
                .attr('font-size', isExternal ? '11px' : '9px')
                .attr('font-weight', isExternal ? '700' : '500')
                .text(label);

            rendered++;
        });
        console.log(`[CoreEngine] renderSwings: rendered ${rendered} swings`);
    }

    /**
     * Render structure breaks (BOS) and character changes (CHoCH)
     */
    function renderStructure() {
        if (!layerGroup) return;

        const structureLayer = layerGroup.select('.core-layer-structure');

        // Render BOS events
        const breaks = cachedData?.structure_breaks || [];
        console.log(`[CoreEngine] renderStructure: ${breaks.length} BOS events`);
        if (breaks.length > 0) {
            console.log('[CoreEngine] First BOS:', breaks[0]);
        }
        breaks.forEach(bos => {
            renderStructureEvent(structureLayer, bos, 'BOS');
        });

        // Render CHoCH events
        const chochs = cachedData?.character_changes || [];
        console.log(`[CoreEngine] renderStructure: ${chochs.length} CHoCH events`);
        if (chochs.length > 0) {
            console.log('[CoreEngine] First CHoCH:', chochs[0]);
        }
        chochs.forEach(choch => {
            renderStructureEvent(structureLayer, choch, 'CHoCH');
        });
    }

    /**
     * Render a single structure event (BOS or CHoCH)
     */
    function renderStructureEvent(layer, event, type) {
        // Line starts at the broken swing (protected swing that was broken)
        const brokenTimestamp = event.broken_swing_timestamp || event.breaking_swing_timestamp || event.break_timestamp;
        // Line ends at the breaking swing (candle that triggered the break)
        const breakingTimestamp = event.breaking_swing_timestamp || event.break_timestamp;

        const x1 = xScale(brokenTimestamp);  // Start: broken swing point
        const x2 = xScale(breakingTimestamp); // End: breaking candle

        // Use level (the broken swing's price) for vertical positioning
        const y = yScale(event.level || event.break_price || event.breaking_swing_price);

        if (isNaN(x1) || isNaN(x2) || isNaN(y)) {
            console.warn(`[CoreEngine] Skipping ${type}: x1=${x1}, x2=${x2}, y=${y}`);
            return;
        }

        const isBullish = event.direction === 'up';
        const isChoch = type === 'CHoCH';

        const color = isChoch
            ? (isBullish ? COLORS.choch_bullish : COLORS.choch_bearish)
            : (isBullish ? COLORS.bos_bullish : COLORS.bos_bearish);

        // Draw horizontal dashed line from broken swing to breaking candle
        layer.append('line')
            .attr('class', `core-structure core-${type.toLowerCase()}`)
            .attr('x1', x1)
            .attr('y1', y)
            .attr('x2', x2)
            .attr('y2', y)
            .attr('stroke', color)
            .attr('stroke-width', isChoch ? 2 : 1.5)
            .attr('stroke-dasharray', '4,2');

        // Calculate center of the line for label positioning
        const centerX = (x1 + x2) / 2;

        // Draw label - check for dual event and severity count
        let label = type;
        if (isChoch) {
            // Add severity count if more than 1 swing was broken
            const severity = event.severity || 1;
            if (event.also_bos === true) {
                label = severity > 1 ? `CHoCH/BOS (${severity})` : 'CHoCH/BOS';
            } else {
                label = severity > 1 ? `CHoCH (${severity})` : 'CHoCH';
            }
        }
        const labelY = isBullish ? y - 8 : y + 15;
        layer.append('text')
            .attr('class', `core-structure-label`)
            .attr('x', centerX)
            .attr('y', labelY)
            .attr('text-anchor', 'middle')
            .attr('fill', color)
            .attr('font-size', event.also_bos ? '9px' : '10px')
            .attr('font-weight', '600')
            .text(label);
    }

    /**
     * Render protected levels
     */
    function renderLevels() {
        if (!cachedData?.protected_levels || !layerGroup) return;

        const levelsLayer = layerGroup.select('.core-layer-levels');
        const levels = cachedData.protected_levels;

        levels.forEach(level => {
            if (level.broken) return; // Don't render broken levels

            const y = yScale(level.price);
            if (isNaN(y)) return;

            const isHigh = level.kind === 'high';
            const color = isHigh ? COLORS.protected_high : COLORS.protected_low;
            const strokeColor = isHigh ? COLORS.swing_high : COLORS.swing_low;

            // Get x range for the line (use timestamp for start)
            const x1 = xScale(level.start_timestamp || level.timestamp || 0);
            const x2 = xScale.range()[1]; // Extend to right edge

            // Draw horizontal zone
            levelsLayer.append('line')
                .attr('class', `core-level core-level-${level.kind}`)
                .attr('x1', Math.max(0, x1))
                .attr('y1', y)
                .attr('x2', x2)
                .attr('y2', y)
                .attr('stroke', strokeColor)
                .attr('stroke-width', 1)
                .attr('stroke-dasharray', '6,3')
                .attr('opacity', 0.7);

            // Draw label on right side
            levelsLayer.append('text')
                .attr('class', 'core-level-label')
                .attr('x', x2 - 5)
                .attr('y', y - 4)
                .attr('text-anchor', 'end')
                .attr('fill', strokeColor)
                .attr('font-size', '9px')
                .attr('opacity', 0.8)
                .text(`${isHigh ? 'PDH' : 'PDL'} ${level.price.toFixed(0)}`);
        });
    }

    /**
     * Render move backgrounds
     */
    function renderMoves() {
        if (!layerGroup || !cachedData?.moves?.length) return;

        const movesLayer = layerGroup.select('.core-layer-moves');
        const yRange = yScale.range();
        const top = Math.min(...yRange);
        const height = Math.abs(yRange[1] - yRange[0]);

        cachedData.moves.forEach(move => {
            if (!move.start_timestamp) return;
            const moveX = xScale(new Date(move.start_timestamp));
            const moveEndX = move.end_timestamp
                ? xScale(new Date(move.end_timestamp))
                : xScale.range()[1];
            if (!Number.isFinite(moveX) || !Number.isFinite(moveEndX)) return;

            movesLayer.append('rect')
                .attr('class', `core-move core-move-${move.direction}`)
                .attr('x', moveX)
                .attr('y', top)
                .attr('width', Math.max(1, moveEndX - moveX))
                .attr('height', height)
                .attr('fill', move.direction === 'bullish' ? COLORS.move_bullish : COLORS.move_bearish)
                .attr('pointer-events', 'none');
        });
    }

    /**
     * Render S/R Zones
     */
    function renderSRZones() {
        if (!layerGroup) return;

        const srLayer = layerGroup.select('.core-layer-sr-zones');

        // Get S/R zones from sr_zones (API returns support and resistance arrays)
        const srData = cachedData?.sr_zones;

        // Combine support and resistance zones into one array with zone_type marker
        const zones = [];
        if (srData?.support) {
            srData.support.forEach(z => zones.push({ ...z, zone_type: 'support' }));
        }
        if (srData?.resistance) {
            srData.resistance.forEach(z => zones.push({ ...z, zone_type: 'resistance' }));
        }

        if (zones.length === 0) {
            console.log('[CoreEngine] No S/R zones to render');
            return;
        }

        console.log(`[CoreEngine] Rendering ${zones.length} S/R zones`);

        zones.forEach((zone, i) => {
            const y1 = yScale(zone.high || zone.price);
            const y2 = yScale(zone.low || zone.price);

            if (isNaN(y1) || isNaN(y2)) return;

            // Determine zone color based on type or direction
            const isResistance = zone.zone_type === 'resistance' || zone.kind === 'high';
            const color = isResistance ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)';
            const strokeColor = isResistance ? '#ef4444' : '#22c55e';

            // Get x range
            const x1 = xScale(zone.timestamp || zone.start_timestamp || xScale.domain()[0]);
            const x2 = xScale.range()[1]; // Extend to right edge

            const height = Math.abs(y2 - y1) || 10; // Minimum height
            const yMin = Math.min(y1, y2);

            // Draw zone rectangle
            srLayer.append('rect')
                .attr('class', `core-sr-zone ${isResistance ? 'resistance' : 'support'}`)
                .attr('x', Math.max(0, x1))
                .attr('y', yMin)
                .attr('width', x2 - Math.max(0, x1))
                .attr('height', height)
                .attr('fill', color)
                .attr('stroke', strokeColor)
                .attr('stroke-width', 1)
                .attr('stroke-dasharray', '4,2')
                .attr('opacity', zone.strength || 0.6);

            // Add label
            const labelText = zone.label || (isResistance ? 'R' : 'S');
            srLayer.append('text')
                .attr('class', 'core-sr-zone-label')
                .attr('x', x2 - 5)
                .attr('y', yMin + 12)
                .attr('text-anchor', 'end')
                .attr('fill', strokeColor)
                .attr('font-size', '9px')
                .attr('font-weight', '600')
                .text(`${labelText} ${(zone.price || zone.high)?.toFixed(0)}`);
        });
    }

    /**
     * Render Fair Value Gaps
     */
    function renderFVGs() {
        if (!layerGroup) return;

        const fvgLayer = layerGroup.select('.core-layer-fvgs');
        const fvgs = cachedData?.fair_value_gaps || [];

        if (fvgs.length === 0) {
            console.log('[CoreEngine] No FVGs to render');
            return;
        }

        console.log(`[CoreEngine] Rendering ${fvgs.length} FVGs`);

        fvgs.forEach((fvg, i) => {
            if (fvg.filled) return; // Skip filled gaps

            const y1 = yScale(fvg.high);
            const y2 = yScale(fvg.low);
            const x1 = xScale(fvg.timestamp);
            const x2 = xScale.range()[1]; // Extend to right edge

            if (isNaN(y1) || isNaN(y2) || isNaN(x1)) return;

            const isBullish = fvg.direction === 'bullish';
            const color = isBullish ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)';
            const strokeColor = isBullish ? '#22c55e' : '#ef4444';

            const height = Math.abs(y2 - y1);
            const yMin = Math.min(y1, y2);

            // Draw FVG rectangle
            fvgLayer.append('rect')
                .attr('class', `core-fvg ${fvg.direction}`)
                .attr('x', x1)
                .attr('y', yMin)
                .attr('width', x2 - x1)
                .attr('height', height)
                .attr('fill', color)
                .attr('stroke', strokeColor)
                .attr('stroke-width', 0.5)
                .attr('opacity', 0.8);

            // Add FVG label at the start
            fvgLayer.append('text')
                .attr('class', 'core-fvg-label')
                .attr('x', x1 + 3)
                .attr('y', yMin + height / 2 + 3)
                .attr('fill', strokeColor)
                .attr('font-size', '8px')
                .attr('font-weight', '500')
                .text('FVG');
        });
    }

    /**
     * Render Liquidity Pools
     */
    function renderLiquidity() {
        if (!layerGroup) return;

        const liqLayer = layerGroup.select('.core-layer-liquidity');
        const pools = cachedData?.liquidity_pools || [];

        if (pools.length === 0) {
            console.log('[CoreEngine] No liquidity pools to render');
            return;
        }

        console.log(`[CoreEngine] Rendering ${pools.length} liquidity pools`);

        pools.forEach((pool, i) => {
            if (pool.swept) return; // Skip swept pools

            const y = yScale(pool.price);
            const x1 = xScale(pool.timestamp || xScale.domain()[0]);
            const x2 = xScale.range()[1];

            if (isNaN(y) || isNaN(x1)) return;

            const isBuySide = pool.side === 'buy_side';
            const color = isBuySide ? '#f59e0b' : '#8b5cf6'; // Orange for buy-side, purple for sell-side

            // Draw liquidity line
            liqLayer.append('line')
                .attr('class', `core-liquidity ${pool.side}`)
                .attr('x1', Math.max(0, x1))
                .attr('y1', y)
                .attr('x2', x2)
                .attr('y2', y)
                .attr('stroke', color)
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '8,4')
                .attr('opacity', pool.strength || 0.7);

            // Add $ markers for liquidity
            liqLayer.append('text')
                .attr('class', 'core-liquidity-label')
                .attr('x', x2 - 5)
                .attr('y', y - 3)
                .attr('text-anchor', 'end')
                .attr('fill', color)
                .attr('font-size', '10px')
                .attr('font-weight', '700')
                .text(isBuySide ? '$$$↑' : '$$$↓');
        });
    }

    /**
     * Toggle layer visibility
     * @param {string} layer - Layer name (swings, structure, levels, moves, zones, sr_zones, fvgs, liquidity)
     * @param {boolean} visible - Whether to show
     */
    async function toggleLayer(layer, visible) {
        console.log(`[CoreEngine] toggleLayer('${layer}', ${visible})`);

        if (visibility.hasOwnProperty(layer)) {
            visibility[layer] = visible;
            console.log(`[CoreEngine] visibility updated:`, visibility);

            // Map layer name to CSS class (handle underscores for hyphenated class names)
            const layerClass = layer.replace('_', '-');

            // Toggle the layer group display
            if (layerGroup) {
                const layerEl = layerGroup.select(`.core-layer-${layerClass}`);
                console.log(`[CoreEngine] Layer element (.core-layer-${layerClass}):`, layerEl.node());
                layerEl.style('display', visible ? null : 'none');
            }

            // Auto-load data if not cached and layer is being enabled
            if (visible && !cachedData) {
                console.log(`[CoreEngine] Layer visible but no data cached, loading now...`);
                await loadAnalysis();
            } else if (visible && cachedData) {
                console.log(`[CoreEngine] Re-rendering because layer ${layer} is now visible`);
                renderAll();
            }
        } else {
            console.warn(`[CoreEngine] Unknown layer: ${layer}. Available layers: ${Object.keys(visibility).join(', ')}`);
        }
    }

    /**
     * Update scales (on zoom/pan)
     */
    function updateScales(x, y) {
        xScale = x;
        yScale = y;

        // Update DrawingZones scales
        if (typeof DrawingZones !== 'undefined') {
            DrawingZones.updateScales(x, y);
        }

        if (cachedData) {
            renderAll();
        }
    }

    /**
     * Set symbol
     */
    function setSymbol(symbol) {
        if (currentSymbol === symbol) return;
        currentSymbol = symbol;
        loadAnalysis();
    }

    /**
     * Set timeframe
     */
    function setTimeframe(timeframe) {
        if (currentTimeframe === timeframe) return;
        currentTimeframe = timeframe;
        loadAnalysis();
    }

    function setCandleCount(count) {
        const nextCount = Number.parseInt(count, 10);
        if (Number.isFinite(nextCount) && nextCount > 0) {
            candleCount = nextCount;
        }
    }

    /**
     * Get current state
     */
    function getState() {
        return {
            initialized,
            symbol: currentSymbol,
            timeframe: currentTimeframe,
            visibility: { ...visibility },
            dataCached: !!cachedData
        };
    }

    /**
     * Clear all rendered elements
     */
    function clear() {
        if (layerGroup) {
            layerGroup.selectAll('*').remove();
        }
        cachedData = null;
    }

    /**
     * Debug: Print all move data to console
     */
    function debugMoves() {
        if (!cachedData) {
            console.log('[CoreEngine Debug] No data loaded');
            return;
        }

        console.log('='.repeat(60));
        console.log('[CoreEngine Debug] MOVES DATA');
        console.log('='.repeat(60));

        const moves = cachedData.moves || [];
        console.log(`Total moves: ${moves.length}`);
        moves.forEach((move, i) => {
            console.log(`\nMove ${i + 1}: ${move.direction} (${move.state})`);
            console.log(`  Protected High: ${move.protected_high_price} (ID: ${move.protected_high_id})`);
            console.log(`  Protected Low: ${move.protected_low_price} (ID: ${move.protected_low_id})`);
            console.log(`  Primary CHoCH: ${move.primary_choch_id}`);
        });

        return moves;
    }

    /**
     * Debug: Print all swing data to console
     */
    function debugSwings() {
        if (!cachedData) {
            console.log('[CoreEngine Debug] No data loaded');
            return;
        }

        console.log('='.repeat(60));
        console.log('[CoreEngine Debug] SWINGS DATA');
        console.log('='.repeat(60));

        const swings = cachedData.swings || [];
        console.log(`Total swings: ${swings.length}`);

        // Filter for interesting swings
        const brokenSwings = swings.filter(s => s.broken);

        console.log(`\nBroken swings: ${brokenSwings.length}`);
        brokenSwings.forEach(s => {
            console.log(`  ❌ ${s.label || s.kind} @ ${s.price} (broken by: ${s.broken_by_id})`);
        });

        console.log('\n--- All swings in order ---');
        swings.forEach(s => {
            const flags = [];
            if (s.broken) flags.push('❌BROKEN');
            const date = new Date(s.timestamp).toLocaleDateString();
            console.log(`  ${date} | ${s.label || s.kind.toUpperCase()} @ ${s.price.toFixed(2)} ${flags.length ? '[' + flags.join(' ') + ']' : ''}`);
        });

        // Show HL/LH analysis for debugging protected logic
        console.log('\n--- HL/LH Analysis (for protected logic) ---');
        const lows = swings.filter(s => s.kind === 'low');
        lows.forEach((low, i) => {
            const date = new Date(low.timestamp).toLocaleDateString();
            const nextSwing = swings.find(s => s.index > low.index && s.kind === 'high');
            const nextLabel = nextSwing ? nextSwing.label : 'none';
            console.log(`  ${date} | ${low.label || 'LOW'} @ ${low.price.toFixed(2)} → next high: ${nextLabel}`);
        });

        return swings;
    }

    /**
     * Debug: Print structure breaks and CHoCH
     */
    function debugStructure() {
        if (!cachedData) {
            console.log('[CoreEngine Debug] No data loaded');
            return;
        }

        console.log('='.repeat(60));
        console.log('[CoreEngine Debug] STRUCTURE EVENTS');
        console.log('='.repeat(60));

        const bos = cachedData.structure_breaks || [];
        const choch = cachedData.character_changes || [];

        console.log(`\nBOS events: ${bos.length}`);
        bos.forEach(b => {
            console.log(`  BOS ${b.direction} @ ${b.break_price} (broke: ${b.broken_swing_ids?.join(', ')})`);
        });

        console.log(`\nCHoCH events: ${choch.length}`);
        choch.forEach(c => {
            const status = c.confirmed ? '✅CONFIRMED' : (c.invalidated ? '❌INVALIDATED' : '⏳PENDING');
            console.log(`  CHoCH ${c.direction} @ ${c.break_price} [${status}]`);
        });

        return { bos, choch };
    }

    /**
     * Debug: Print drawing zones info
     */
    function debugZones() {
        if (!cachedData) {
            console.log('[CoreEngine Debug] No data loaded');
            return;
        }

        // Use DrawingZones debug if available
        if (typeof DrawingZones !== 'undefined') {
            return DrawingZones.debugZones();
        }

        // Fallback: print zones from cached data
        const zones = cachedData.drawing_zones || [];
        console.log('='.repeat(60));
        console.log('[CoreEngine Debug] DRAWING ZONES');
        console.log('='.repeat(60));
        console.log(`Total zones: ${zones.length}`);

        zones.forEach((zone, i) => {
            const dir = zone.direction === 'bullish' ? '🟢' : '🔴';
            console.log(`\n${dir} Zone #${i}: ${zone.direction.toUpperCase()}`);
            console.log(`   Start: ${zone.start_kind} @ ${zone.start_price?.toFixed(2)} (idx: ${zone.start_index})`);
            console.log(`   End:   ${zone.end_kind} @ ${zone.end_price?.toFixed(2)} (idx: ${zone.end_index})`);
            console.log(`   Range: ${zone.zone_low?.toFixed(2)} - ${zone.zone_high?.toFixed(2)}`);
        });

        return zones;
    }

    /**
     * Debug: Print ALL Core engine data in a comprehensive format
     */
    function debugAll() {
        if (!cachedData) {
            console.log('[CoreEngine] No data loaded. Call CoreEngine.loadAnalysis() first.');
            return null;
        }

        const data = cachedData;
        const sep = '='.repeat(70);
        const subsep = '-'.repeat(50);

        console.log('\n' + sep);
        console.log('📊 CORE ENGINE - COMPLETE MARKET ANALYSIS');
        console.log(`   Symbol: ${currentSymbol} | Timeframe: ${currentTimeframe}`);
        console.log(`   Timestamp: ${new Date().toISOString()}`);
        console.log(sep);

        // 1. SUMMARY COUNTS
        console.log('\n📈 DATA SUMMARY');
        console.log(subsep);
        console.table({
            'Swings (total)': data.swings?.length || 0,
            'Swings (external)': data.swings?.filter(s => s.degree === 'external').length || 0,
            'Swings (internal)': data.swings?.filter(s => s.degree === 'internal').length || 0,
            'Structure Breaks (BOS)': data.structure_breaks?.length || 0,
            'Character Changes (CHoCH)': data.character_changes?.length || 0,
            'Protected Levels': data.protected_levels?.length || 0,
            'Fair Value Gaps': data.fair_value_gaps?.length || 0,
            'Liquidity Pools': data.liquidity_pools?.length || 0,
            'Liquidity Sweeps': data.recent_sweeps?.length || 0,
            'Drawing Zones': data.drawing_zones?.length || 0,
            'S/R Zones': data.sr_analysis?.all_zones?.length || 0,
            'Legs': data.legs?.length || 0,
            'Ranges': data.ranges?.length || 0,
        });

        // 2. CURRENT STATE
        console.log('\n🎯 CURRENT STATE');
        console.log(subsep);
        console.log(`   Bias: ${data.bias || 'neutral'}`);
        console.log(`   Current Price: ${data.current_price || 'N/A'}`);

        if (data.direction_analysis) {
            const dir = data.direction_analysis;
            console.log(`   Direction: ${dir.direction} (${dir.direction_detail})`);
            console.log(`   Trending: ${dir.is_trending}, Ranging: ${dir.is_ranging}`);
            console.log(`   Pattern: HH=${dir.has_higher_high}, HL=${dir.has_higher_low}, LH=${dir.has_lower_high}, LL=${dir.has_lower_low}`);
        }

        if (data.range_position) {
            const rp = data.range_position;
            console.log(`   Range Position: ${rp.zone} (${(rp.position_ratio * 100).toFixed(1)}%)`);
            console.log(`   External Range: ${rp.external_low?.toFixed(2)} - ${rp.external_high?.toFixed(2)}`);
        }

        // 3. EXTERNAL SWINGS
        if (data.external_high || data.external_low) {
            console.log('\n🔺🔻 EXTERNAL SWINGS (Range Boundaries)');
            console.log(subsep);
            if (data.external_high) {
                console.log(`   External High: ${data.external_high.price?.toFixed(2)} @ idx ${data.external_high.index}`);
            }
            if (data.external_low) {
                console.log(`   External Low:  ${data.external_low.price?.toFixed(2)} @ idx ${data.external_low.index}`);
            }
        }

        // 4. SWINGS
        if (data.swings?.length > 0) {
            console.log('\n📍 SWINGS (last 20)');
            console.log(subsep);
            const recentSwings = data.swings.slice(-20);
            console.table(recentSwings.map(s => ({
                Kind: s.kind,
                Label: s.label || '-',
                Degree: s.degree,
                Price: s.price?.toFixed(2),
                Index: s.index,
                Protected: s.is_protected ? '✓' : '',
                Broken: s.broken ? '✓' : '',
                CHoCH: s.is_choch ? '✓' : '',
                BOS: s.is_bos ? '✓' : ''
            })));
        }

        // 5. STRUCTURE EVENTS
        if (data.structure_breaks?.length > 0 || data.character_changes?.length > 0) {
            console.log('\n⚡ STRUCTURE EVENTS');
            console.log(subsep);

            if (data.structure_breaks?.length > 0) {
                console.log('   BOS Events:');
                data.structure_breaks.forEach(b => {
                    const dir = b.direction === 'up' ? '↑' : '↓';
                    console.log(`      ${dir} BOS @ ${b.level?.toFixed(2)} (severity: ${b.severity})`);
                });
            }

            if (data.character_changes?.length > 0) {
                console.log('   CHoCH Events:');
                data.character_changes.forEach(c => {
                    const dir = c.direction === 'up' ? '↑' : '↓';
                    const status = c.confirmed ? '✅' : c.invalidated ? '❌' : '⏳';
                    console.log(`      ${dir} CHoCH @ ${c.level?.toFixed(2)} ${status} (severity: ${c.severity})`);
                });
            }
        }

        // 6. PROTECTED LEVELS
        if (data.protected_levels?.length > 0) {
            console.log('\n🛡️ PROTECTED LEVELS');
            console.log(subsep);
            console.table(data.protected_levels.filter(l => !l.broken).map(l => ({
                Kind: l.kind,
                Price: l.price?.toFixed(2),
                Degree: l.swing_degree,
                Touches: l.touch_count,
                Strength: l.strength?.toFixed(2)
            })));
        }

        // 7. LIQUIDITY
        if (data.liquidity_pools?.length > 0) {
            console.log('\n💰 LIQUIDITY POOLS');
            console.log(subsep);
            console.table(data.liquidity_pools.filter(p => !p.swept).map(p => ({
                Side: p.side,
                Price: p.price?.toFixed(2),
                Type: p.pool_type,
                Strength: p.strength?.toFixed(2),
                Swept: p.swept ? '✓' : ''
            })));
        }

        // 8. FVGs
        if (data.fair_value_gaps?.length > 0) {
            console.log('\n📐 FAIR VALUE GAPS');
            console.log(subsep);
            console.table(data.fair_value_gaps.filter(f => !f.filled).map(f => ({
                Direction: f.direction,
                High: f.high?.toFixed(2),
                Low: f.low?.toFixed(2),
                Size: f.size?.toFixed(2),
                Filled: f.fill_percentage ? `${(f.fill_percentage * 100).toFixed(0)}%` : '0%'
            })));
        }

        // 9. S/R ZONES
        if (data.sr_analysis?.all_zones?.length > 0) {
            console.log('\n🧱 S/R ZONES');
            console.log(subsep);
            console.table(data.sr_analysis.all_zones.map(z => ({
                Type: z.zone_type || z.kind,
                Price: z.price?.toFixed(2),
                High: z.high?.toFixed(2),
                Low: z.low?.toFixed(2),
                Strength: z.strength?.toFixed(2),
                Touches: z.touch_count
            })));
        }

        // 10. RECENT EVENTS
        if (data.recent_events?.length > 0) {
            console.log('\n🔔 RECENT EVENTS');
            console.log(subsep);
            data.recent_events.slice(0, 5).forEach(e => {
                console.log(`   ${e.event_type} ${e.direction} @ ${e.price?.toFixed(2)} - ${e.description}`);
            });
        }

        // 11. ACTIONABLE CONTEXT
        if (data.actionable) {
            console.log('\n🎯 ACTIONABLE CONTEXT');
            console.log(subsep);
            console.log(`   Thesis: ${data.actionable.current_thesis}`);
            console.log(`   Confidence: ${(data.actionable.confidence * 100).toFixed(0)}%`);
            if (data.actionable.primary_level) {
                const pl = data.actionable.primary_level;
                console.log(`   Primary Level: ${pl.level_type} @ ${pl.price?.toFixed(2)} (${pl.direction})`);
            }
        }

        // 12. MARKET ANALYSIS (8 Sections)
        if (data.analysis) {
            console.log('\n📋 MARKET ANALYSIS (8-Section Q&A)');
            console.log(subsep);
            console.log(`   Summary: ${data.analysis.summary}`);
            console.log(`   Market State: ${data.analysis.market_state}`);
            console.log(`   Clarity Score: ${data.analysis.clarity_score}/100`);
        }

        console.log('\n' + sep);
        console.log('💡 TIP: Access raw data with CoreEngine.getData()');
        console.log('💡 TIP: Toggle layers with CoreEngine.toggleLayer("sr_zones", true)');
        console.log(sep + '\n');

        return data;
    }

    // Public API
    return {
        init,
        loadAnalysis,
        toggleLayer,
        updateScales,
        setSymbol,
        setTimeframe,
        setCandleCount,
        getState,
        clear,
        // Zone navigation (new naming)
        olderZone,      // Navigate to older zone (← in time)
        newerZone,      // Navigate to newer zone (→ in time)
        goToZone,       // Jump to specific zone by name or index
        setZoneFiltering,
        zoneInfo,       // Comprehensive zone info with console output
        // Legacy aliases
        nextZone: olderZone,   // Alias for backwards compatibility
        prevZone: newerZone,   // Alias for backwards compatibility
        getZoneInfo: zoneInfo, // Alias for backwards compatibility
        // Debug commands
        debugMoves,
        debugSwings,
        debugStructure,
        debugZones,
        debugAll,          // Comprehensive debug dump
        // Expose visibility for external sync
        getVisibility: () => ({ ...visibility }),
        // Expose raw data for debugging
        getData: () => cachedData,
        // Get current symbol/timeframe
        getSymbol: () => currentSymbol,
        getTimeframe: () => currentTimeframe
    };
})();

// Export for global access
if (typeof window !== 'undefined') {
    window.CoreEngine = CoreEngine;
}
