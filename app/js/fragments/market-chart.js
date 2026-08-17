/**
 * Real-time Candlestick Dashboard (D3.js Version)
 * Replicates Plotly Dash candlestick functionality using D3.js
 * Based on: https://github.com/ChadThackray/plotly-dash-candlesticks-2022
 * Uses Binance API for real-time data
 */

function createChartNarrator(config = {}, opts = {}) {
    return {
        init: async () => { },
        enable: () => { },
        disable: () => { },
        isEnabled: () => false,
        loadAnalysis: async () => { },
        updateScales: () => { },
    };
}

// Configuration
let currentSymbol = 'BTCUSDT';
let currentTimeframe = localStorage.getItem('selectedTimeframe') || '1h';
let isRunning = false;
let updateInterval = null;
let websocket = null;
let reconnectTimeout = null; // Store reconnect timeout so it can be cleared in stopUpdate()
let lastSuccessfulConnectionTime = null; // Track when connection was established
let lastMessageTime = null; // Track last message received for health monitoring
let healthCheckInterval = null; // Interval for connection health checks
const WS_HEALTH_CHECK_INTERVAL = 15000; // Check health every 15 seconds
const WS_MESSAGE_TIMEOUT = 60000; // Consider dead if no message in 60 seconds

// Keep chart and Core Engine requests on the same candle window.

// Swing sensitivity configuration
// Lower value = more frequent swings, Higher value = less frequent swings
let swingSensitivity = 0.5;

// Chart data
let chartData = {
    x: [], // Timestamps
    open: [],
    high: [],
    low: [],
    close: [],
    volume: []
};

// Lazy loading state - viewport-based candle loading
let isLoadingMoreCandles = false; // Prevent concurrent fetches
let hasMoreHistoricalData = true; // False when we've fetched all available data
let lastLoadedCandleCount = 0; // Track how many candles we've loaded
let initialViewDomain = null; // Store initial view position for reset button
const MIN_CANDLE_WIDTH_PX = 4; // Minimum candle width in pixels
const DEFAULT_CANDLE_WIDTH_PX = 8; // Default candle width
const LAZY_LOAD_THRESHOLD = 20; // Load more when within this many candles of edge
const INITIAL_CANDLE_MULTIPLIER = 2; // Load 2x viewport capacity initially

// Store detected swings
let detectedSwings = [];

// Expose current symbol and timeframe for ConsolePrint and other modules
window.currentSymbol = currentSymbol;
window.currentTimeframe = currentTimeframe;


// Algorithm render toggles - track which renders are enabled
const renderStates = {
    narrator: true,   // Narrator toggle - ENABLED
    swings: true,     // ENABLED
    volatility: true,   // ENABLED
    momentum: true,     // ENABLED
    volume: true,       // ENABLED
    emas: true,         // ENABLED
    consolidation: true  // ENABLED
};

// Binance API configuration
const BINANCE_API_BASE = 'https://api.binance.com/api/v3';
const BINANCE_WS_BASE = 'wss://stream.binance.com:9443/ws';

// Backend API base (use window override if set). Default to uvicorn dev server.
const BACKEND_API_BASE = (typeof window !== 'undefined' && window.BACKEND_API_BASE) ? window.BACKEND_API_BASE : 'http://127.0.0.1:8000';

// Timeframe mapping to Binance intervals
const timeframeMap = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '1h': '1h',
    '4h': '4h',
    '1d': '1d',
    '1w': '1w',
    '1M': '1M'
};

// D3 chart state. These references are shared by render and interaction paths.
const margin = { top: 20, right: 100, bottom: 60, left: 20 };
let width = 0;
let height = 0;
let chartWidth = 0;
let chartHeight = 0;
let svg = null;
let g = null;
let baseXScale = null;
let baseYScale = null;
let xScale = null;
let yScale = null;
let xAxis = null;
let yAxis = null;
let currentZoomTransform = null;
let currentPriceLine = null;
let chartInitialized = false;
let chartNarrator = null;

function updateYAxisFromVisibleCandles(data) {
    if (!baseYScale || !baseXScale || !data || data.length === 0) return;

    // Get the visible time range from the current x-axis domain
    const visibleTimeRange = baseXScale.domain();

    // Filter data to only include candles within the visible x-axis range
    const visibleData = data.filter(d =>
        d.timestamp >= visibleTimeRange[0] && d.timestamp <= visibleTimeRange[1]
    );

    if (visibleData.length === 0) {
        // Fallback to all data if no visible candles
        const minPrice = d3.min(data, d => d.low);
        const maxPrice = d3.max(data, d => d.high);
        const priceRange = maxPrice - minPrice;
        const domainRange = priceRange / 0.9;
        const priceCenter = (maxPrice + minPrice) / 2;
        const domainMin = priceCenter - domainRange / 2;
        const domainMax = priceCenter + domainRange / 2;
        baseYScale.domain([
            Math.max(0, domainMin),
            domainMax
        ]);
    } else {
        // Calculate min/max price from only visible candles
        const minPrice = d3.min(visibleData, d => d.low);
        const maxPrice = d3.max(visibleData, d => d.high);
        const priceRange = maxPrice - minPrice;

        // Calculate domain so visible price data occupies 90% of chart height
        const domainRange = priceRange / 0.9;

        // Center the price data in the domain, leaving 5% space at top and bottom
        const priceCenter = (maxPrice + minPrice) / 2;
        const domainMin = priceCenter - domainRange / 2;
        const domainMax = priceCenter + domainRange / 2;

        baseYScale.domain([
            Math.max(0, domainMin), // Don't go below 0 for price
            domainMax
        ]);
    }

    // Update yScale reference
    yScale = baseYScale;
}

function setDefaultChartView(data) {
    // Ensure scales have ranges set before setting domains
    if (!baseXScale.range() || baseXScale.range().length === 0) {
        baseXScale.range([0, chartWidth]);
    }
    if (!baseYScale.range() || baseYScale.range().length === 0) {
        baseYScale.range([chartHeight, 0]);
    }

    // For x-axis: zoom in 3x and leave 10% space on the right
    const fullTimeExtent = d3.extent(data, d => d.timestamp);
    const fullTimeRange = fullTimeExtent[1].getTime() - fullTimeExtent[0].getTime();

    // Zoom in 3x (show 1/3 = 33.33% of full range)
    const zoomedTimeRange = fullTimeRange / 3;

    // Position so last candle has 10% space on the right
    const rightEdge = fullTimeExtent[1].getTime(); // Last candle time
    const adjustedRightEdge = rightEdge + (zoomedTimeRange * 0.1);
    const adjustedLeftEdge = adjustedRightEdge - (zoomedTimeRange * 1.1);

    baseXScale.domain([
        new Date(adjustedLeftEdge),
        new Date(adjustedRightEdge)
    ]);

    // For y-axis: zoom to show price data of VISIBLE candles using 90% of available chart height
    updateYAxisFromVisibleCandles(data);

    // Update scales
    xScale = baseXScale;
    yScale = baseYScale;
}

// Performance optimization: cache and throttling
let renderAnimationFrame = null;
let updateThrottleTimer = null;
let candlestickContainer = null; // Cache container reference
let yAxisZoomArea = null; // Cache y-axis zoom area reference
let yAxisZoomBehavior = null; // Cache y-axis zoom behavior
let xAxisZoomArea = null; // Cache x-axis zoom area reference
let xAxisZoomBehavior = null; // Cache x-axis zoom behavior

// Store drag start position for y-axis zoom
let yAxisDragStartY = null;
let yAxisDragStartDomain = null;

// Store drag start position for x-axis zoom
let xAxisDragStartX = null;
let xAxisDragStartDomain = null;

// Store drag start position for chart panel drag
let chartDragStartX = null;
let chartDragStartY = null;
let chartDragStartXDomain = null;
let chartDragStartYDomain = null;

// Zoom limits (based on full data range, independent of main chart zoom)
let yAxisMinRange = null; // Will be set based on full data range
let yAxisMaxRange = null; // Will be set based on full data range
let xAxisMinRange = null; // Will be set based on full data range (in milliseconds)
let xAxisMaxRange = null; // Will be set based on full data range (in milliseconds)
let fullDataPriceRange = null; // Store full price range for limit calculations
let fullDataTimeRange = null; // Store full time range for limit calculations

// DOM Elements
const symbolSelect = document.getElementById('symbolSelect');
const timeframeSelect = document.getElementById('timeframeSelect');
const currentPriceEl = document.getElementById('currentPrice');
const priceChangeEl = document.getElementById('priceChange');
const volumeEl = document.getElementById('volume');
const statusEl = document.getElementById('status');
const themeToggleBtn = document.getElementById('themeToggle');
const fpsCounterEl = document.getElementById('fpsCounter');

// Public timeframe switch used by the interval bar. The select's own change
// handler publishes chartContextChanged, which refreshes both Core panels.
window.switchTimeframe = (timeframe) => {
    if (!timeframeSelect || !Object.hasOwn(timeframeMap, timeframe)) return false;
    if (timeframeSelect.value === timeframe) return true;
    timeframeSelect.value = timeframe;
    timeframeSelect.dispatchEvent(new Event('change'));
    return true;
};

// ------------------------------------------------------------
// FRAME TIMING / FPS COUNTER (matches display refresh rate)
// ------------------------------------------------------------
let lastFrameTime = null;
let smoothedFps = null;
let lastFpsDisplayTime = 0;

function recordFrameForFps() {
    if (!fpsCounterEl || typeof performance === 'undefined') return;

    const now = performance.now();

    if (lastFrameTime != null) {
        const delta = now - lastFrameTime;
        if (delta > 0) {
            const instantFps = 1000 / delta;
            // Exponential moving average to smooth jitter
            smoothedFps = smoothedFps == null
                ? instantFps
                : smoothedFps * 0.9 + instantFps * 0.1;

            // Only update DOM a few times per second
            if (now - lastFpsDisplayTime > 250) {
                fpsCounterEl.textContent = String(Math.round(smoothedFps));
                lastFpsDisplayTime = now;
            }
        }
    }

    lastFrameTime = now;
}

// ------------------------------------------------------------
// THEME TOGGLING (LIGHT / DARK)
// ------------------------------------------------------------
function applyTheme(theme) {
    const root = document.body; // enhanced-chart.css uses [data-theme="dark"]
    if (!root) return;

    if (theme === 'dark') {
        root.setAttribute('data-theme', 'dark');
    } else {
        root.setAttribute('data-theme', 'light'); // FIXED: Set to 'light' instead of removing
        theme = 'light';
    }

    // Optionally persist in localStorage so reload keeps choice
    try {
        window.localStorage.setItem('chartTheme', theme);
    } catch (_) {
        // Ignore storage errors
    }
}

function initThemeFromStorage() {
    let stored = null;
    try {
        stored = window.localStorage.getItem('chartTheme');
    } catch (_) {
        stored = null;
    }
    const prefersDark = window.matchMedia &&
        window.matchMedia('(prefers-color-scheme: dark)').matches;

    const initialTheme = stored || (prefersDark ? 'dark' : 'light');
    applyTheme(initialTheme);
}

function toggleTheme() {
    const root = document.body;
    if (!root) return;
    const isDark = root.getAttribute('data-theme') === 'dark';
    applyTheme(isDark ? 'light' : 'dark');
}

// Loading overlay helpers (visual only)
function showLoadingOverlay() {
    const loading = document.getElementById('loadingOverlay');
    if (loading) {
        loading.classList.remove('hidden');
    }
}

function hideLoadingOverlay() {
    const loading = document.getElementById('loadingOverlay');
    if (loading) {
        loading.classList.add('hidden');
    }
}

// Bento cards and narrator panel loading state helpers
function showPanelsLoading() {
    // Add loading class to all bento cards
    document.querySelectorAll('.bento-card').forEach(card => {
        card.classList.add('loading');
    });
    // Add loading class to narrator panel
    const narratorPanel = document.getElementById('narratorPanel');
    if (narratorPanel) {
        narratorPanel.classList.add('loading');
    }
}

function hidePanelsLoading() {
    // Remove loading class from all bento cards
    document.querySelectorAll('.bento-card').forEach(card => {
        card.classList.remove('loading');
    });
    // Remove loading class from narrator panel
    const narratorPanel = document.getElementById('narratorPanel');
    if (narratorPanel) {
        narratorPanel.classList.remove('loading');
    }
}

// Direction swings container reference
let directionSwingsContainer = null;

/**
 * Draw direction swings on chart - the 4 external swings used for HTF direction
 * @param {boolean} clear - If true, only clear existing markers
 * @param {object|null} viewModel - The Core summary published by PanelController
 */
async function drawDirectionSwings(clear = false, viewModel = null) {
    // Ensure we have the chart group
    if (!g || !baseXScale || !baseYScale || !chartData) {
        console.warn('drawDirectionSwings: Chart not ready');
        return;
    }

    // Create or get container
    if (!directionSwingsContainer) {
        directionSwingsContainer = g.append('g')
            .attr('class', 'direction-swings-container')
            .attr('clip-path', 'url(#chart-clip)');
    }

    // Clear existing markers
    directionSwingsContainer.selectAll('*').remove();

    if (clear) return;

    try {
        // PanelController owns the request and publishes the shared view model.
        const data = viewModel || window.latestCoreViewModel;

        if (!data?.success || !data.direction_swings) {
            return;
        }

        const dirSwings = data.direction_swings;
        console.log(`📍 Drawing ${dirSwings.swings.length} direction swings (${dirSwings.source || 'unknown source'})`);

        // Draw each swing
        dirSwings.swings.forEach((swing, i) => {
            // Match by timestamp - convert swing timestamp to Date
            const swingTime = new Date(swing.timestamp);

            // Find the closest candle by timestamp
            let candleIndex = -1;
            for (let j = 0; j < chartData.x.length; j++) {
                const candleTime = chartData.x[j];
                // Allow 1 minute tolerance for matching
                if (Math.abs(candleTime.getTime() - swingTime.getTime()) < 60000) {
                    candleIndex = j;
                    break;
                }
            }

            if (candleIndex === -1) {
                console.warn(`Swing timestamp ${swing.timestamp} not found in chart data`);
                return;
            }

            const candleTime = chartData.x[candleIndex];
            const x = baseXScale(candleTime);
            const y = baseYScale(swing.price);

            // Choose colors based on label
            let color, bgColor;
            if (swing.label === 'HH' || swing.label === 'HL') {
                color = '#22c55e'; // Green for bullish structure
                bgColor = 'rgba(34, 197, 94, 0.8)';
            } else if (swing.label === 'LH' || swing.label === 'LL') {
                color = '#ef4444'; // Red for bearish structure
                bgColor = 'rgba(239, 68, 68, 0.8)';
            } else {
                color = '#60a5fa'; // Blue for first H/L
                bgColor = 'rgba(96, 165, 250, 0.8)';
            }

            // Offset label above/below the price
            const yOffset = swing.kind === 'high' ? -20 : 20;

            // Draw marker circle
            directionSwingsContainer.append('circle')
                .attr('cx', x)
                .attr('cy', y)
                .attr('r', 5)
                .attr('fill', color)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1.5)
                .style('pointer-events', 'none');

            // Draw label background
            const labelWidth = swing.label.length > 1 ? 28 : 18;
            directionSwingsContainer.append('rect')
                .attr('x', x - labelWidth / 2)
                .attr('y', y + yOffset - 8)
                .attr('width', labelWidth)
                .attr('height', 16)
                .attr('rx', 3)
                .attr('fill', bgColor)
                .style('pointer-events', 'none');

            // Draw label text
            directionSwingsContainer.append('text')
                .attr('x', x)
                .attr('y', y + yOffset)
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'middle')
                .attr('fill', '#fff')
                .attr('font-size', '10px')
                .attr('font-weight', 'bold')
                .attr('font-family', 'monospace')
                .style('pointer-events', 'none')
                .text(swing.label);

            // Draw price tag
            const priceText = swing.price.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
            const priceYOffset = swing.kind === 'high' ? -38 : 38;

            directionSwingsContainer.append('text')
                .attr('x', x)
                .attr('y', y + priceYOffset)
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'middle')
                .attr('fill', color)
                .attr('font-size', '9px')
                .attr('font-family', 'monospace')
                .style('pointer-events', 'none')
                .text(priceText);
        });

        console.log('✅ Direction swings drawn');
    } catch (error) {
        console.error('❌ Error drawing direction swings:', error);
    }
}

// Expose to window for testing
window.drawDirectionSwings = drawDirectionSwings;
window.addEventListener('coreSnapshotUpdated', event => {
    if (event.detail?.symbol !== currentSymbol || event.detail?.timeframe !== currentTimeframe) return;
    drawDirectionSwings(false, event.detail);
});

// Initialize chart when script is loaded, but ensure D3 is available first.
let marketChartInitAttempts = 0;

async function initMarketChart() {
    try {
        // Set initial theme before drawing
        initThemeFromStorage();

        await initializeChart();
        setupEventListeners();

        // Note: MarketNarrator is initialized from dashboard level, not here
        // The chart fragment just updates the narrator when data changes

        // Initialize Core Engine for raw structure visualization
        try {
            if (typeof CoreEngine !== 'undefined' && g && baseXScale && baseYScale) {
                CoreEngine.init({
                    chartGroup: g,
                    xScale: baseXScale,
                    yScale: baseYScale,
                    symbol: currentSymbol,
                    timeframe: currentTimeframe,
                    candleCount: chartData.x.length || 400
                });
                console.log(`✅ CoreEngine initialized with ${chartData.x.length} candles`);
            }
        } catch (e) {
            console.warn('CoreEngine initialization failed:', e);
        }

    } catch (error) {
        console.error('Failed to initialize market chart:', error);
        // Ensure loading overlay is not left hanging
        try {
            hideLoadingOverlay();
        } catch (_) {
            // ignore
        }

        // Show error message to user
        const loading = document.getElementById('loadingOverlay');
        if (loading) {
            loading.innerHTML = `
                <div class="error-message">
                    <p style="color: #ef4444; font-weight: bold;">Failed to load chart</p>
                    <p style="color: #666;">${error.message || 'Unknown error'}</p>
                    <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Retry</button>
                </div>
            `;
            loading.classList.remove('hidden');
        }
    }
}

(function scheduleMarketChartInit() {
    // Wait for D3 to be available before initializing
    if (typeof d3 === 'undefined') {
        if (marketChartInitAttempts < 50) { // up to ~5s with 100ms interval
            marketChartInitAttempts += 1;
            console.log(`Waiting for D3.js... attempt ${marketChartInitAttempts}/50`);
            setTimeout(scheduleMarketChartInit, 100);
        } else {
            console.error('D3 not available after multiple attempts. Chart initialization aborted.');
            console.error('Make sure D3.js CDN is accessible: https://d3js.org/d3.v7.min.js');
            try {
                hideLoadingOverlay();
                const loading = document.getElementById('loadingOverlay');
                if (loading) {
                    loading.innerHTML = `
                        <div class="error-message">
                            <p style="color: #ef4444; font-weight: bold;">D3.js library failed to load</p>
                            <p style="color: #666;">Cannot initialize chart without D3.js</p>
                            <p style="color: #666; font-size: 12px;">Check your internet connection or console for details</p>
                            <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Retry</button>
                        </div>
                    `;
                    loading.classList.remove('hidden');
                }
            } catch (_) {
                // ignore
            }
        }
        return;
    }

    // D3 is ready, initialize chart
    console.log('D3.js loaded successfully, initializing market chart...');
    initMarketChart();
})();

/**
 * Update chart dimensions when container size changes (e.g., DevTools open/close)
 * Updates SVG, zoom-panel-area, clip-path, and scales to match new container size
 */
function updateChartDimensions() {
    const container = d3.select('#candlestickChart').node();
    if (!container) return false;

    const parentContainer = container.parentElement;
    if (!parentContainer) return false;

    const newWidth = parentContainer.clientWidth;
    const newHeight = parentContainer.clientHeight;

    // Skip if dimensions haven't changed or are invalid
    if (!newWidth || !newHeight || newWidth === 0 || newHeight === 0) return false;
    if (newWidth === width && newHeight === height) return false;

    console.log(`📐 Updating chart dimensions: ${width}x${height} → ${newWidth}x${newHeight}`);

    // Update global dimensions
    width = newWidth;
    height = newHeight;
    chartWidth = width - margin.left - margin.right;
    chartHeight = height - margin.top - margin.bottom;

    // Update SVG size
    svg.attr('width', width).attr('height', height);

    // Update clip path
    svg.select('#chart-clip rect')
        .attr('width', chartWidth)
        .attr('height', chartHeight);

    // Update zoom-panel-area
    svg.select('.zoom-panel-area')
        .attr('width', chartWidth)
        .attr('height', chartHeight + 60);

    // Update y-axis zoom area position and size
    svg.select('.y-axis-zoom-area')
        .attr('x', chartWidth + margin.left)
        .attr('y', margin.top)
        .attr('height', chartHeight);

    // Update x-axis zoom area position and size
    svg.select('.x-axis-zoom-area')
        .attr('x', margin.left)
        .attr('y', chartHeight + margin.top - 10)
        .attr('width', chartWidth);

    // Update scales ranges (preserve domains for current view)
    if (baseXScale) baseXScale.range([0, chartWidth]);
    if (baseYScale) baseYScale.range([chartHeight, 0]);
    if (xScale) xScale.range([0, chartWidth]);
    if (yScale) yScale.range([chartHeight, 0]);

    // Update axis positions
    if (xAxis) xAxis.attr('transform', `translate(0,${chartHeight})`);
    if (yAxis) yAxis.attr('transform', `translate(${chartWidth + 8},0)`);

    return true;
}

/**
 * Initialize D3.js chart
 */
async function initializeChart() {
    console.log('Starting chart initialization...');

    // Initialize zoom transform now that D3 is available
    if (currentZoomTransform === null && typeof d3 !== 'undefined') {
        currentZoomTransform = d3.zoomIdentity;
    }

    // Get container dimensions
    const container = d3.select('#candlestickChart').node();
    if (!container) {
        throw new Error('Chart container #candlestickChart not found');
    }
    console.log('Chart container found:', container);

    const parentContainer = container.parentElement;
    if (!parentContainer) {
        throw new Error('Chart parent container not found');
    }
    console.log('Parent container found:', parentContainer);

    width = parentContainer.clientWidth;
    height = parentContainer.clientHeight;

    console.log(`Container dimensions: ${width}x${height}`);

    if (!width || !height || width === 0 || height === 0) {
        throw new Error(`Invalid container dimensions: ${width}x${height}. Container may not be visible or properly sized.`);
    }

    chartWidth = width - margin.left - margin.right;
    chartHeight = height - margin.top - margin.bottom;

    console.log(`Chart dimensions: ${chartWidth}x${chartHeight}`);

    // Create SVG with crisp rendering
    svg = d3.select('#candlestickChart')
        .attr('width', width)
        .attr('height', height)
        .style('shape-rendering', 'geometricPrecision') // Smooth rendering for candlesticks
        .style('text-rendering', 'optimizeLegibility') // Better text rendering
        .style('image-rendering', '-webkit-optimize-contrast') // Better image rendering
        .style('image-rendering', 'crisp-edges'); // Crisp edges for images

    // Create main group
    g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create base scales (these never change - used for zoom rescaling)
    baseXScale = d3.scaleTime()
        .range([0, chartWidth]);

    baseYScale = d3.scaleLinear()
        .range([chartHeight, 0]);

    // Create working scales (these are the transformed versions)
    xScale = baseXScale.copy();
    yScale = baseYScale.copy();

    // Create clipping path to prevent overflow into axes (only once)
    // Remove existing defs if any
    svg.select('defs').remove();
    const defs = svg.append('defs');
    const clipPath = defs.append('clipPath')
        .attr('id', 'chart-clip');
    clipPath.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', chartWidth)
        .attr('height', chartHeight);

    // Create axes
    xAxis = g.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0,${chartHeight})`);

    // Position y-axis on the right side
    yAxis = g.append('g')
        .attr('class', 'y-axis')
        .attr('transform', `translate(${chartWidth + 8},0)`);

    // Create zoom panel area (chart + x-axis labels) with mouse wheel zoom and drag
    // Zoom from right edge (most recent time) to left
    const zoomPanelArea = svg.append('rect')
        .attr('class', 'zoom-panel-area')
        .attr('x', margin.left)
        .attr('y', margin.top)
        .attr('width', chartWidth)
        .attr('height', chartHeight + 60) // Include x-axis label area
        .attr('fill', 'transparent')
        .style('pointer-events', 'all') // Enable interactions
        .style('cursor', 'crosshair') // Show crosshair cursor
        .on('mousedown', function (event) {
            // Store initial state when drag starts
            // Get mouse position relative to the SVG
            const svgRect = svg.node().getBoundingClientRect();
            chartDragStartX = event.clientX - svgRect.left - margin.left;
            chartDragStartY = event.clientY - svgRect.top - margin.top;
            chartDragStartXDomain = baseXScale.domain().slice(); // Copy array
            chartDragStartYDomain = baseYScale.domain().slice(); // Copy array
            zoomPanelArea.style('cursor', 'crosshair'); // Maintain crosshair while dragging
        })
        .on('mousemove', function (event) {
            // Get mouse position relative to the SVG
            const svgRect = svg.node().getBoundingClientRect();
            const currentX = event.clientX - svgRect.left - margin.left;
            const currentY = event.clientY - svgRect.top - margin.top;

            // Update crosshair position (always, even during panning)
            if (currentX >= 0 && currentX <= chartWidth && currentY >= 0 && currentY <= chartHeight) {
                // Update vertical line (follows mouse X) with half-pixel alignment for crisp rendering
                crosshairVertical
                    .attr('x1', Math.round(currentX) + 0.5) // Half-pixel alignment for crisp 1px line
                    .attr('x2', Math.round(currentX) + 0.5) // Half-pixel alignment for crisp 1px line
                    .attr('y1', 0)
                    .attr('y2', chartHeight)
                    .style('display', 'block');

                // Update horizontal line (follows mouse Y) with half-pixel alignment for crisp rendering
                crosshairHorizontal
                    .attr('x1', 0)
                    .attr('x2', chartWidth)
                    .attr('y1', Math.round(currentY) + 0.5) // Half-pixel alignment for crisp 1px line
                    .attr('y2', Math.round(currentY) + 0.5) // Half-pixel alignment for crisp 1px line
                    .style('display', 'block');

                // Update price label (Y-axis) - positioned to align with Y-axis tick labels
                if (window._crosshairPriceLabel && baseYScale) {
                    const price = baseYScale.invert(currentY);
                    const priceText = price >= 1000 ? price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                        : price >= 1 ? price.toFixed(4)
                            : price.toFixed(6);

                    const priceLabel = window._crosshairPriceLabel;
                    const labelText = priceLabel.select('text');
                    const labelBg = priceLabel.select('rect');

                    labelText.text(priceText);

                    // Get text dimensions for background
                    const textNode = labelText.node();
                    const textBBox = textNode ? textNode.getBBox() : { width: 70, height: 14 };
                    const padding = 3;

                    // Position label on Y-axis (right side, aligned with axis ticks at chartWidth + 8)
                    const labelX = margin.left + chartWidth + 12;
                    const labelY = margin.top + currentY;

                    labelBg
                        .attr('x', labelX - padding)
                        .attr('y', labelY - textBBox.height / 2 - padding)
                        .attr('width', textBBox.width + padding * 2)
                        .attr('height', textBBox.height + padding * 2);

                    labelText
                        .attr('x', labelX)
                        .attr('y', labelY);

                    priceLabel.style('display', 'block');
                }

                // Update time label (X-axis) - positioned to align with X-axis tick labels
                if (window._crosshairTimeLabel && baseXScale) {
                    const time = baseXScale.invert(currentX);
                    const timeText = d3.timeFormat('%b %d, %H:%M')(time);

                    const timeLabel = window._crosshairTimeLabel;
                    const labelText = timeLabel.select('text');
                    const labelBg = timeLabel.select('rect');

                    labelText.text(timeText);

                    // Get text dimensions for background
                    const textNode = labelText.node();
                    const textBBox = textNode ? textNode.getBBox() : { width: 90, height: 14 };
                    const padding = 3;

                    // Position label on X-axis (bottom, at chartHeight + bottom margin area)
                    const labelX = margin.left + currentX;
                    const labelY = margin.top + chartHeight + 15;

                    labelBg
                        .attr('x', labelX - textBBox.width / 2 - padding)
                        .attr('y', labelY - textBBox.height / 2 - padding)
                        .attr('width', textBBox.width + padding * 2)
                        .attr('height', textBBox.height + padding * 2);

                    labelText
                        .attr('x', labelX)
                        .attr('y', labelY);


                    timeLabel.style('display', 'block');
                }
            } else {
                // Hide if outside chart bounds
                crosshairVertical.style('display', 'none');
                crosshairHorizontal.style('display', 'none');
                if (window._crosshairPriceLabel) window._crosshairPriceLabel.style('display', 'none');
                if (window._crosshairTimeLabel) window._crosshairTimeLabel.style('display', 'none');
            }

            // Handle panning if mouse button is pressed
            if (event.buttons === 1 && chartDragStartX !== null && chartDragStartY !== null &&
                chartDragStartXDomain && chartDragStartYDomain) {
                // Prevent default to avoid text selection
                event.preventDefault();

                // Calculate drag distances in chart coordinates
                const deltaX = currentX - chartDragStartX;
                const deltaY = currentY - chartDragStartY;

                // === HORIZONTAL PANNING (X-axis) ===
                // Convert pixel movement to time movement
                // Maintain the same time range (zoom level) - only pan, don't zoom
                const startXRange = chartDragStartXDomain[1].getTime() - chartDragStartXDomain[0].getTime();
                const pixelsPerTime = chartWidth / startXRange;
                const timeDelta = -deltaX / pixelsPerTime; // Negative because drag right should move left in time

                // Calculate new domain - maintain the same range (zoom level)
                const newStartTime = chartDragStartXDomain[0].getTime() + timeDelta;
                const newEndTime = chartDragStartXDomain[1].getTime() + timeDelta;

                // Get full data range to prevent panning beyond data bounds
                let finalStartTime = newStartTime;
                let finalEndTime = newEndTime;

                if (chartData && chartData.x && chartData.x.length > 0) {
                    const fullDataStart = chartData.x[0].getTime();
                    const fullDataEnd = chartData.x[chartData.x.length - 1].getTime();

                    // Only clamp if the entire visible range is outside the data bounds
                    // Allow partial overlap for flexible panning
                    if (finalEndTime < fullDataStart) {
                        // Entire view is before data start - clamp to start
                        finalStartTime = fullDataStart;
                        finalEndTime = fullDataStart + startXRange;
                    } else if (finalStartTime > fullDataEnd) {
                        // Entire view is after data end - clamp to end
                        finalEndTime = fullDataEnd;
                        finalStartTime = fullDataEnd - startXRange;
                    }
                    // Otherwise allow partial overlap - user can pan to see edges
                }

                // === VERTICAL PANNING (Y-axis) ===
                // Convert pixel movement to price movement
                // Maintain the same price range (zoom level) - only pan, don't zoom
                const startYRange = chartDragStartYDomain[1] - chartDragStartYDomain[0];
                const pixelsPerPrice = chartHeight / startYRange;
                const priceDelta = deltaY / pixelsPerPrice; // Positive deltaY (drag down) should move price view up (show lower prices)

                // Calculate new domain - maintain the same range (zoom level)
                // Drag down = move view up = show lower prices = increase min and max by same amount
                // Drag up = move view down = show higher prices = decrease min and max by same amount
                const newMinPrice = chartDragStartYDomain[0] + priceDelta;
                const newMaxPrice = chartDragStartYDomain[1] + priceDelta;

                // Allow panning beyond data bounds for flexibility (no clamping)
                // Users can pan to see extended price ranges
                let finalMinPrice = newMinPrice;
                let finalMaxPrice = newMaxPrice;

                // Update domains if ranges are maintained (same zoom levels)
                // Check ranges separately so one axis can pan even if the other hits a boundary
                let xUpdated = false;
                let yUpdated = false;

                const newXRange = finalEndTime - finalStartTime;
                const newYRange = finalMaxPrice - finalMinPrice;

                // Update X-axis if range is maintained
                if (Math.abs(newXRange - startXRange) < 1 && finalStartTime < finalEndTime) {
                    baseXScale.domain([new Date(finalStartTime), new Date(finalEndTime)]);
                    xScale = baseXScale;
                    xUpdated = true;
                }

                // Update Y-axis if range is maintained (allow any price range, no clamping)
                if (Math.abs(newYRange - startYRange) < 0.01 && finalMinPrice < finalMaxPrice) {
                    baseYScale.domain([finalMinPrice, finalMaxPrice]);
                    yScale = baseYScale;
                    yUpdated = true;
                }

                // Don't auto-update Y-axis during horizontal pan/zoom - keep current y-axis domain
                // This prevents candlesticks from shifting when zooming horizontally
                // Y-axis should only change when user explicitly zooms vertically or resets chart

                // Update chart if either axis changed
                if (xUpdated || yUpdated) {
                    // Cancel any ongoing structure animations before updating
                    if (typeof window.cancelStructureAnimations === 'function') {
                        window.cancelStructureAnimations();
                    }

                    // Update chart
                    if (renderAnimationFrame) {
                        cancelAnimationFrame(renderAnimationFrame);
                    }
                    renderAnimationFrame = requestAnimationFrame(() => {
                        updateAxesAndGrid();
                        updateCandlesticks();
                        if (updateThrottleTimer) {
                            clearTimeout(updateThrottleTimer);
                            updateThrottleTimer = null;
                        }
                        updateChartDisplayImmediate();
                        recordFrameForFps();

                        // Update narrator scales after pan
                        if (chartNarrator && xUpdated) {
                            chartNarrator.updateScales(xScale, yScale);
                        }

                        // Update Core Engine annotations after pan
                        if (typeof CoreEngine !== 'undefined' && CoreEngine.updateScales) {
                            CoreEngine.updateScales(xScale, yScale);
                        }
                        // Update Indicators after pan
                        if (typeof IndicatorEngine !== 'undefined' && IndicatorEngine.refresh) {
                            IndicatorEngine.refresh();
                        }
                    });
                }
            }
            // Crosshair is updated at the beginning of this handler, so it moves with the chart during panning
        })
        .on('mouseup', function (event) {
            // Reset drag state
            chartDragStartX = null;
            chartDragStartY = null;
            chartDragStartXDomain = null;
            chartDragStartYDomain = null;
            zoomPanelArea.style('cursor', 'grab'); // Reset cursor
        })
        .on('mouseleave', function (event) {
            // Reset drag state if mouse leaves area
            chartDragStartX = null;
            chartDragStartY = null;
            chartDragStartXDomain = null;
            chartDragStartYDomain = null;
            zoomPanelArea.style('cursor', 'grab'); // Reset cursor
        })
        .on('wheel', function (event) {
            // Prevent default scrolling
            event.preventDefault();
            event.stopPropagation();

            // Calculate zoom factor from wheel delta
            const deltaY = event.deltaY;
            const baseZoomSpeed = 0.05; // Base sensitivity
            let zoomFactor = 1;

            if (deltaY > 0) {
                // Wheel down = zoom in (smaller time range) - INVERTED
                zoomFactor = 1 - baseZoomSpeed;
            } else if (deltaY < 0) {
                // Wheel up = zoom out (larger time range) - INVERTED
                zoomFactor = 1 + baseZoomSpeed;
            } else {
                return; // No change
            }

            // Apply zoom to x-domain - always zoom from the right edge (most recent time)
            const baseXDomain = baseXScale.domain();
            const xDomainRange = baseXDomain[1].getTime() - baseXDomain[0].getTime();
            // Keep the right edge (end time) fixed, adjust only the left edge
            const rightEdge = baseXDomain[1].getTime(); // Most recent time - keep this fixed
            let newXDomainRange = xDomainRange / zoomFactor;

            // Apply zoom limits
            if (xAxisMinRange !== null && newXDomainRange < xAxisMinRange) {
                newXDomainRange = xAxisMinRange;
            }
            if (xAxisMaxRange !== null && newXDomainRange > xAxisMaxRange) {
                newXDomainRange = xAxisMaxRange;
            }

            const newXDomain = [
                new Date(rightEdge - newXDomainRange), // Adjust left edge
                new Date(rightEdge) // Keep right edge fixed
            ];

            if (newXDomainRange > 0 && newXDomain[0].getTime() < newXDomain[1].getTime()) {
                baseXScale.domain(newXDomain);

                // Update scales
                xScale = baseXScale;

                // Don't update Y-axis during horizontal zoom - keep current y-axis domain

                // Cancel any ongoing structure animations before updating
                if (typeof window.cancelStructureAnimations === 'function') {
                    window.cancelStructureAnimations();
                }

                // Update chart
                if (renderAnimationFrame) {
                    cancelAnimationFrame(renderAnimationFrame);
                }
                renderAnimationFrame = requestAnimationFrame(() => {
                    updateAxesAndGrid();
                    updateCandlesticks();
                    if (updateThrottleTimer) {
                        clearTimeout(updateThrottleTimer);
                        updateThrottleTimer = null;
                    }
                    updateChartDisplayImmediate();
                    recordFrameForFps();

                    // Update narrator scales after zoom
                    if (chartNarrator) {
                        chartNarrator.updateScales(xScale, yScale);
                    }

                    // Update Core Engine annotations after zoom
                    if (typeof CoreEngine !== 'undefined' && CoreEngine.updateScales) {
                        CoreEngine.updateScales(xScale, yScale);
                    }
                    // Update Indicators after zoom
                    if (typeof IndicatorEngine !== 'undefined' && IndicatorEngine.refresh) {
                        IndicatorEngine.refresh();
                    }
                });
            }
        });

    // Create separate zoom behavior for y-axis (vertical zoom only)
    yAxisZoomBehavior = d3.zoom()
        .scaleExtent([0.5, 20])
        .filter((event) => {
            // Allow all mouse and touch events on y-axis
            return event.type === 'wheel' || event.type === 'mousedown' || event.type === 'mousemove' || event.type === 'mouseup' || event.type.startsWith('touch');
        })
        .on('zoom', handleYAxisZoom);

    // Apply zoom to y-axis area (right side of chart) - only the y-axis label area
    yAxisZoomArea = svg.append('rect')
        .attr('class', 'y-axis-zoom-area')
        .attr('x', chartWidth + margin.left)
        .attr('y', margin.top)
        .attr('width', 80)
        .attr('height', chartHeight)
        .attr('fill', 'transparent')
        .attr('cursor', 'ns-resize')
        .style('pointer-events', 'all')
        .on('wheel', function (event) {
            // Prevent default behavior and handle wheel zoom
            event.preventDefault();
            event.stopPropagation();

            // Calculate vertical position in y-axis label area (0 = bottom, 1 = top)
            const rect = this.getBoundingClientRect();
            const mouseY = event.clientY - rect.top;
            const positionFromBottom = 1 - (mouseY / rect.height); // 0 at top, 1 at bottom

            // Calculate sensitivity multiplier based on vertical position
            // At bottom (positionFromBottom = 1): multiplier = 1.0 (100% sensitivity)
            // At top (positionFromBottom = 0): multiplier = 0.35 (35% sensitivity)
            const sensitivityMultiplier = 0.35 + (positionFromBottom * 0.65);

            // Calculate zoom factor from wheel delta
            const deltaY = event.deltaY;
            const baseZoomSpeed = 0.05; // Base sensitivity
            const zoomSpeed = baseZoomSpeed * sensitivityMultiplier;
            let zoomFactor = 1;

            if (deltaY > 0) {
                // Scroll down = zoom in (smaller range) - INVERTED
                zoomFactor = 1 - zoomSpeed;
            } else if (deltaY < 0) {
                // Scroll up = zoom out (larger range) - INVERTED
                zoomFactor = 1 + zoomSpeed;
            } else {
                return; // No change
            }

            // Apply zoom to y-domain - always zoom from vertical center
            const baseYDomain = baseYScale.domain();
            const yDomainRange = baseYDomain[1] - baseYDomain[0];
            // Always use the center of the current price domain as zoom center
            const priceCenterY = (baseYDomain[0] + baseYDomain[1]) / 2;
            let newYDomainRange = yDomainRange / zoomFactor;

            // Apply zoom limits
            if (yAxisMinRange !== null && newYDomainRange < yAxisMinRange) {
                newYDomainRange = yAxisMinRange;
            }
            if (yAxisMaxRange !== null && newYDomainRange > yAxisMaxRange) {
                newYDomainRange = yAxisMaxRange;
            }

            const newYDomain = [
                priceCenterY - newYDomainRange / 2,
                priceCenterY + newYDomainRange / 2
            ];

            if (newYDomainRange > 0 && newYDomain[0] < newYDomain[1]) {
                baseYScale.domain(newYDomain);

                // Update working scale (no transform needed - we use baseYScale directly)
                yScale = baseYScale;

                // Update chart
                if (renderAnimationFrame) {
                    cancelAnimationFrame(renderAnimationFrame);
                }
                renderAnimationFrame = requestAnimationFrame(() => {
                    updateAxesAndGrid();
                    updateCandlesticks();
                    if (updateThrottleTimer) {
                        clearTimeout(updateThrottleTimer);
                        updateThrottleTimer = null;
                    }
                    updateChartDisplayImmediate();
                    recordFrameForFps();
                });
            }
        })
        .call(yAxisZoomBehavior);

    // Create separate zoom behavior for x-axis (horizontal zoom only)
    xAxisZoomBehavior = d3.zoom()
        .scaleExtent([0.5, 20])
        .filter((event) => {
            // Allow all mouse and touch events on x-axis
            return event.type === 'wheel' || event.type === 'mousedown' || event.type === 'mousemove' || event.type === 'mouseup' || event.type.startsWith('touch');
        })
        .on('zoom', handleXAxisZoom);

    // Apply zoom to x-axis area (bottom of chart) - only the x-axis label area
    xAxisZoomArea = svg.append('rect')
        .attr('class', 'x-axis-zoom-area')
        .attr('x', margin.left)
        .attr('y', chartHeight + margin.top - 10) // Move up 10px so it's fully visible
        .attr('width', chartWidth)
        .attr('height', 40) // Reduced height
        .attr('fill', 'transparent')
        .attr('cursor', 'ew-resize')
        .style('pointer-events', 'all')
        .on('wheel', function (event) {
            // Prevent default behavior and handle wheel zoom
            event.preventDefault();
            event.stopPropagation();

            // Calculate zoom factor from wheel delta (same as zoom-panel-area)
            const deltaY = event.deltaY;
            const baseZoomSpeed = 0.05; // Base sensitivity
            let zoomFactor = 1;

            if (deltaY > 0) {
                // Wheel down = zoom in (smaller time range) - INVERTED
                zoomFactor = 1 - baseZoomSpeed;
            } else if (deltaY < 0) {
                // Wheel up = zoom out (larger time range) - INVERTED
                zoomFactor = 1 + baseZoomSpeed;
            } else {
                return; // No change
            }

            // Apply zoom to x-domain - always zoom from the right edge (most recent time)
            const baseXDomain = baseXScale.domain();
            const xDomainRange = baseXDomain[1].getTime() - baseXDomain[0].getTime();
            // Keep the right edge (end time) fixed, adjust only the left edge
            const rightEdge = baseXDomain[1].getTime(); // Most recent time - keep this fixed
            let newXDomainRange = xDomainRange / zoomFactor;

            // Apply zoom limits
            if (xAxisMinRange !== null && newXDomainRange < xAxisMinRange) {
                newXDomainRange = xAxisMinRange;
            }
            if (xAxisMaxRange !== null && newXDomainRange > xAxisMaxRange) {
                newXDomainRange = xAxisMaxRange;
            }

            const newXDomain = [
                new Date(rightEdge - newXDomainRange), // Adjust left edge
                new Date(rightEdge) // Keep right edge fixed
            ];

            if (newXDomainRange > 0 && newXDomain[0].getTime() < newXDomain[1].getTime()) {
                baseXScale.domain(newXDomain);

                // Update scales
                xScale = baseXScale;

                // Don't update Y-axis during horizontal zoom - keep current y-axis domain

                // Cancel any ongoing structure animations before updating
                if (typeof window.cancelStructureAnimations === 'function') {
                    window.cancelStructureAnimations();
                }

                // Update chart
                if (renderAnimationFrame) {
                    cancelAnimationFrame(renderAnimationFrame);
                }
                renderAnimationFrame = requestAnimationFrame(() => {
                    updateAxesAndGrid();
                    updateCandlesticks();
                    if (updateThrottleTimer) {
                        clearTimeout(updateThrottleTimer);
                        updateThrottleTimer = null;
                    }
                    updateChartDisplayImmediate();
                    recordFrameForFps();

                    // Update narrator scales after zoom
                    if (chartNarrator) {
                        chartNarrator.updateScales(xScale, yScale);
                    }
                });
            }
        })
        .call(xAxisZoomBehavior);

    // Create chart title as overlay on top-left of zoom-panel-area with glass effect background
    const titleMargin = { top: 15, left: 15 }; // Margin from top and left edges
    const titlePadding = { top: 6, right: 12, bottom: 6, left: 12 }; // Padding around text

    // Create drop shadow filter for the title (reuse existing defs)
    const existingDefs = svg.select('defs');
    const filter = existingDefs.append('filter')
        .attr('id', 'chart-title-shadow')
        .attr('x', '-50%')
        .attr('y', '-50%')
        .attr('width', '200%')
        .attr('height', '200%');

    filter.append('feGaussianBlur')
        .attr('in', 'SourceAlpha')
        .attr('stdDeviation', 3)
        .attr('result', 'blur');

    filter.append('feOffset')
        .attr('in', 'blur')
        .attr('dx', 0)
        .attr('dy', 3)
        .attr('result', 'offsetBlur');

    const feComponentTransfer = filter.append('feComponentTransfer')
        .attr('in', 'offsetBlur');

    feComponentTransfer.append('feFuncA')
        .attr('type', 'linear')
        .attr('slope', 0.6); // Increased shadow opacity

    filter.append('feMerge')
        .append('feMergeNode')
        .attr('in', 'ComponentTransfer');

    filter.append('feMerge')
        .append('feMergeNode')
        .attr('in', 'SourceGraphic');

    // Create a group for the title (background + text)
    const chartTitleGroup = svg.append('g')
        .attr('class', 'chart-title-group')
        .attr('transform', `translate(${titleMargin.left},${titleMargin.top})`)
        .style('pointer-events', 'none'); // Don't interfere with zoom/pan interactions

    // Create glass effect background rectangle
    const titleText = `${currentSymbol} - ${currentTimeframe}`;
    const titleTextNode = svg.append('text')
        .attr('class', 'chart-title-temp')
        .attr('x', 0)
        .attr('y', 0)
        .style('font-size', '14px')
        .style('font-weight', '600')
        .style('visibility', 'hidden')
        .text(titleText);

    const textBBox = titleTextNode.node().getBBox();
    titleTextNode.remove();

    // Calculate background dimensions
    const bgWidth = textBBox.width + titlePadding.left + titlePadding.right;
    const bgHeight = textBBox.height + titlePadding.top + titlePadding.bottom;

    // Glass effect background with shadow applied to border
    chartTitleGroup.append('rect')
        .attr('class', 'chart-title-bg')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', bgWidth)
        .attr('height', bgHeight)
        .attr('rx', 8) // Rounded corners
        .attr('ry', 8)
        .style('fill', 'rgba(255, 255, 255, 0.85)') // Semi-transparent white
        .style('backdrop-filter', 'blur(10px)') // Glass blur effect
        .style('-webkit-backdrop-filter', 'blur(10px)') // Safari support
        .style('stroke', 'rgba(0, 0, 0, 0.1)') // Subtle border
        .style('stroke-width', '1px')
        .style('filter', 'url(#chart-title-shadow)'); // Drop shadow applied to border

    // Title text - center vertically within the background
    const chartTitle = chartTitleGroup.append('text')
        .attr('class', 'chart-title')
        .attr('x', titlePadding.left)
        .attr('y', bgHeight / 2) // Center vertically in the background
        .attr('text-anchor', 'start')
        .attr('dominant-baseline', 'middle') // Center text vertically
        .style('font-size', '14px')
        .style('font-weight', '600')
        .style('fill', '#1a1a1a')
        .text(titleText);

    // Update title when symbol/timeframe changes
    const updateTitle = () => {
        const newText = `${currentSymbol} - ${currentTimeframe}`;
        chartTitleGroup.select('.chart-title').text(newText);

        // Update background size to match new text
        const tempText = svg.append('text')
            .attr('class', 'chart-title-temp')
            .attr('x', 0)
            .attr('y', 0)
            .style('font-size', '14px')
            .style('font-weight', '600')
            .style('visibility', 'hidden')
            .text(newText);

        const newBBox = tempText.node().getBBox();
        tempText.remove();

        const newBgWidth = newBBox.width + titlePadding.left + titlePadding.right;
        const newBgHeight = newBBox.height + titlePadding.top + titlePadding.bottom;

        chartTitleGroup.select('.chart-title-bg')
            .attr('width', newBgWidth)
            .attr('height', newBgHeight);

        // Update text position to stay centered
        chartTitleGroup.select('.chart-title')
            .attr('y', newBgHeight / 2);
    };

    // Store update function for later use
    window.updateChartTitle = updateTitle;

    // Create candlestick container (only once, reused for performance)
    candlestickContainer = g.append('g')
        .attr('class', 'candlestick-container')
        .attr('clip-path', 'url(#chart-clip)');

    // Create crosshair container for cursor tracking
    const crosshairContainer = g.append('g')
        .attr('class', 'crosshair-container')
        .attr('clip-path', 'url(#chart-clip)')
        .style('pointer-events', 'none'); // Don't interfere with interactions

    // Create crosshair lines (initially hidden)
    const crosshairVertical = crosshairContainer.append('line')
        .attr('class', 'crosshair-vertical')
        .style('stroke', 'rgba(0, 0, 0, 0.17)') // 17% opacity
        .style('stroke-width', '1px')
        .style('stroke-dasharray', '4,4') // Dotted line
        .style('shape-rendering', 'crispEdges') // Crisp lines
        .style('display', 'none');

    const crosshairHorizontal = crosshairContainer.append('line')
        .attr('class', 'crosshair-horizontal')
        .style('stroke', 'rgba(0, 0, 0, 0.17)') // 17% opacity
        .style('stroke-width', '1px')
        .style('stroke-dasharray', '4,4') // Dotted line
        .style('shape-rendering', 'crispEdges') // Crisp lines
        .style('display', 'none');

    // Create crosshair price label (Y-axis) - positioned on right side
    const crosshairPriceLabel = svg.append('g')
        .attr('class', 'crosshair-price-label')
        .style('display', 'none')
        .style('pointer-events', 'none');

    crosshairPriceLabel.append('rect')
        .attr('class', 'crosshair-label-bg')
        .attr('fill', '#1a1a2e')
        .attr('rx', 3)
        .attr('ry', 3);

    crosshairPriceLabel.append('text')
        .attr('class', 'crosshair-label-text')
        .attr('fill', '#e0e0e0')
        .attr('font-size', '11px')
        .attr('font-family', 'monospace')
        .attr('text-anchor', 'start')
        .attr('dominant-baseline', 'middle');

    // Create crosshair time label (X-axis) - positioned at bottom
    const crosshairTimeLabel = svg.append('g')
        .attr('class', 'crosshair-time-label')
        .style('display', 'none')
        .style('pointer-events', 'none');

    crosshairTimeLabel.append('rect')
        .attr('class', 'crosshair-label-bg')
        .attr('fill', '#1a1a2e')
        .attr('rx', 3)
        .attr('ry', 3);

    crosshairTimeLabel.append('text')
        .attr('class', 'crosshair-label-text')
        .attr('fill', '#e0e0e0')
        .attr('font-size', '11px')
        .attr('font-family', 'monospace')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle');

    // Store label references globally for mousemove handler
    window._crosshairPriceLabel = crosshairPriceLabel;
    window._crosshairTimeLabel = crosshairTimeLabel;

    // Crosshair is handled within the main mousemove handler (see zoomPanelArea.on('mousemove'))

    // Create current price line container
    const currentPriceLineContainer = g.append('g')
        .attr('class', 'current-price-line-container')
        .attr('clip-path', 'url(#chart-clip)')
        .style('pointer-events', 'none'); // Don't interfere with interactions

    // Create current price line (initially hidden) - now uses candle colors
    currentPriceLine = currentPriceLineContainer.append('line')
        .attr('class', 'current-price-line')
        .style('stroke', 'var(--candle-up, #089981)') // Default to bullish green
        .style('stroke-width', '1px')
        .style('stroke-dasharray', '4,4') // Dashed line
        .style('shape-rendering', 'crispEdges') // Crisp lines
        .style('display', 'none');

    // Create current price badge container (positioned on Y-axis)
    const currentPriceBadgeContainer = svg.append('g')
        .attr('class', 'current-price-badge-container')
        .style('pointer-events', 'none')
        .style('display', 'none');

    // Badge background (pill shape)
    currentPriceBadgeContainer.append('rect')
        .attr('class', 'current-price-badge-bg')
        .attr('height', 22)
        .attr('rx', 3)
        .attr('ry', 3);

    // Arrow pointer
    currentPriceBadgeContainer.append('path')
        .attr('class', 'current-price-badge-arrow');

    // Badge text
    currentPriceBadgeContainer.append('text')
        .attr('class', 'current-price-badge-text')
        .attr('dominant-baseline', 'middle')
        .attr('text-anchor', 'start')
        .style('fill', '#ffffff')
        .style('font-size', '11px')
        .style('font-weight', '600')
        .style('font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif');

    // Store reference for updates
    window._currentPriceBadge = currentPriceBadgeContainer;

    // Create grid lines (will be updated in renderChart)
    // Grid lines are created dynamically in renderChart() to match current scale domains

    // Initialize narrator system for visual analysis
    try {
        console.log('🎬 Initializing narrator system...');
        const chartConfig = {
            svg: svg.node(),
            g: g.node(),
            xScale,
            yScale,
            chartData
        };
        console.log('📋 Chart config:', chartConfig);
        chartNarrator = createChartNarrator(chartConfig, {
            showToggleButton: false,  // We use our own button in the toolbar
            initiallyVisible: false,
            apiBaseUrl: 'http://localhost:8000'
        });
        console.log('🔧 chartNarrator created:', chartNarrator);

        // Initialize narrator with D3 elements
        await chartNarrator.init(g, xScale, yScale, chartData);
        console.log('✅ Chart narrator initialized and ready');
    } catch (error) {
        console.error('❌ Failed to initialize narrator:', error);
        console.error('Error stack:', error.stack);
    }

    // Load initial data
    await loadHistoricalData();

    // Automatically start real-time updates after chart is initialized
    await startUpdate();
}

// ============================================================================
// VIEWPORT-BASED CANDLE LOADING
// ============================================================================

/**
 * Get how many candles can fit in the current viewport.
 * Based on current chart width and candle rendering width
 */
function getViewportCandleCapacity() {
    const viewportWidth = chartWidth || 800; // Fallback if not initialized
    const candleWidth = DEFAULT_CANDLE_WIDTH_PX; // ~8px per candle at default zoom
    return Math.ceil(viewportWidth / candleWidth) + LAZY_LOAD_THRESHOLD;
}
// Expose for other modules (e.g., ConsolePrint analysis)
window.getViewportCandleCapacity = getViewportCandleCapacity;

/**
 * Get initial load count based on viewport capacity
 */
function getInitialLoadCount() {
    const capacity = getViewportCandleCapacity();
    return Math.max(200, capacity * INITIAL_CANDLE_MULTIPLIER); // At least 200, or 2x viewport
}

/**
 * Check if we need to load more historical candles
 * Called when panning left or zooming out
 */
function checkNeedMoreCandles() {
    if (isLoadingMoreCandles || !hasMoreHistoricalData || !xScale) return false;

    const visibleDomain = xScale.domain();
    if (!visibleDomain || !chartData.x || chartData.x.length === 0) return false;

    const oldestVisibleTime = visibleDomain[0];
    const oldestLoadedTime = chartData.x[0];

    // Calculate how many candles are buffered on the left
    const bufferCandlesLeft = chartData.x.findIndex(t => t >= oldestVisibleTime);

    // Need more if we're within threshold of the oldest loaded data
    return bufferCandlesLeft >= 0 && bufferCandlesLeft < LAZY_LOAD_THRESHOLD;
}

/**
 * Update chart-overlay engines with newly available historical candles.
 * Panel analysis intentionally uses a stable Core lookback and is not tied to
 * how far the user has zoomed or panned the chart.
 * Called when more historical candles are loaded via pan/zoom
 */
function updateEnginesWithCandleCount(newCandleCount) {
    console.log(`🔄 Updating engines with ${newCandleCount} candles...`);

    try {
        // Update CoreEngine
        if (typeof CoreEngine !== 'undefined' && CoreEngine.setCandleCount) {
            CoreEngine.setCandleCount(newCandleCount);
            CoreEngine.loadAnalysis(true);
            console.log(`✅ CoreEngine updated with ${newCandleCount} candles`);
        }
    } catch (e) {
        console.warn('Failed to update CoreEngine:', e);
    }
}

/**
 * Load more historical candles (for lazy loading)
 * Fetches older candles and prepends to existing data
 */
async function loadMoreHistoricalCandles() {
    if (isLoadingMoreCandles || !hasMoreHistoricalData) return;

    isLoadingMoreCandles = true;
    console.log('📥 Loading more historical candles...');

    try {
        const interval = timeframeMap[currentTimeframe] || '1h';
        const oldestTimestamp = chartData.x[0];
        const loadCount = getViewportCandleCapacity();

        // Fetch candles BEFORE the oldest one we have
        const moreCandles = await fetchHistoricalData(
            currentSymbol,
            interval,
            loadCount,
            null, // startTime
            oldestTimestamp // endTime - fetch before this
        );

        if (!moreCandles || moreCandles.length === 0) {
            hasMoreHistoricalData = false;
            console.log('📭 No more historical data available');
            return;
        }

        // Filter out any duplicates (candles we already have)
        const existingTimestamps = new Set(chartData.x.map(t => t.getTime()));
        const newCandles = moreCandles.filter(c => !existingTimestamps.has(c.timestamp.getTime()));

        if (newCandles.length === 0) {
            hasMoreHistoricalData = false;
            console.log('📭 No new candles (all duplicates)');
            return;
        }

        console.log(`📥 Prepending ${newCandles.length} new candles`);

        // PRESERVE current visible range before updating data
        const currentVisibleDomain = xScale ? xScale.domain().map(d => d.getTime ? d.getTime() : d) : null;

        // Prepend new candles to existing data
        chartData.x.unshift(...newCandles.map(c => c.timestamp));
        chartData.open.unshift(...newCandles.map(c => c.open));
        chartData.high.unshift(...newCandles.map(c => c.high));
        chartData.low.unshift(...newCandles.map(c => c.low));
        chartData.close.unshift(...newCandles.map(c => c.close));
        chartData.volume.unshift(...newCandles.map(c => c.volume));

        lastLoadedCandleCount = chartData.x.length;

        // Update baseXScale domain to include ALL data (new + old)
        if (baseXScale && chartData.x.length > 0) {
            baseXScale.domain([chartData.x[0], chartData.x[chartData.x.length - 1]]);
        }

        // RESTORE the visible range - keep showing same candles as before
        if (currentVisibleDomain && xScale) {
            xScale.domain([new Date(currentVisibleDomain[0]), new Date(currentVisibleDomain[1])]);
        }

        // Re-render with new data (but same visible position)
        renderChart();

        // Update engines with new candle count and reload analysis
        updateEnginesWithCandleCount(chartData.x.length);

        console.log(`📊 Total candles now: ${chartData.x.length}`);

    } catch (error) {
        console.error('Error loading more candles:', error);
    } finally {
        isLoadingMoreCandles = false;
    }
}

/**
 * Load historical data and render chart
 */
async function loadHistoricalData() {
    // Show visual loading overlay while historical data is fetched
    showLoadingOverlay();

    // Add safety timeout - if loading takes more than 30 seconds, show error
    const timeoutId = setTimeout(() => {
        hideLoadingOverlay();
        const loading = document.getElementById('loadingOverlay');
        if (loading) {
            loading.innerHTML = `
                <div class="error-message">
                    <p style="color: #ef4444; font-weight: bold;">Chart loading timeout</p>
                    <p style="color: #666;">Unable to fetch market data. Please check your connection.</p>
                    <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Retry</button>
                </div>
            `;
            loading.classList.remove('hidden');
        }
    }, 30000);

    try {
        const interval = timeframeMap[currentTimeframe] || '1h';

        // Reset lazy loading state for new data load
        hasMoreHistoricalData = true;
        isLoadingMoreCandles = false;

        // Use viewport-based initial load (2x viewport capacity)
        const initialLoadCount = getInitialLoadCount();
        console.log(`Fetching ${initialLoadCount} candles for ${currentSymbol} (${interval}) [viewport-based]`);
        const candles = await fetchHistoricalData(currentSymbol, interval, initialLoadCount);

        clearTimeout(timeoutId); // Clear timeout on success

        if (!candles || candles.length === 0) {
            throw new Error('No candle data received from API');
        }

        console.log(`Received ${candles.length} candles`);

        // Convert to chart data format
        chartData = {
            x: candles.map(c => c.timestamp),
            open: candles.map(c => c.open),
            high: candles.map(c => c.high),
            low: candles.map(c => c.low),
            close: candles.map(c => c.close),
            volume: candles.map(c => c.volume)
        };

        // Calculate and store full data ranges for zoom limits (independent of main chart zoom)
        if (chartData.x.length > 0 && chartData.high.length > 0 && chartData.low.length > 0) {
            const minPrice = Math.min(...chartData.low);
            const maxPrice = Math.max(...chartData.high);
            fullDataPriceRange = maxPrice - minPrice;

            const firstTime = chartData.x[0].getTime();
            const lastTime = chartData.x[chartData.x.length - 1].getTime();
            fullDataTimeRange = lastTime - firstTime;

            // Set zoom limits using same rules for both axes: 0.1% min, 3x max
            yAxisMinRange = fullDataPriceRange * 0.001; // 0.1% of full price range
            yAxisMaxRange = fullDataPriceRange * 3; // 3x full price range

            xAxisMinRange = fullDataTimeRange * 0.001; // 0.1% of full time range
            xAxisMaxRange = fullDataTimeRange * 3; // 3x full time range
        }

        // Update price display
        if (chartData.close.length > 0) {
            const lastPrice = chartData.close[chartData.close.length - 1];
            if (currentPriceEl) {
                currentPriceEl.textContent = `$${lastPrice.toFixed(2)}`;
            }

            if (chartData.close.length > 1) {
                const prevPrice = chartData.close[chartData.close.length - 2];
                const change = ((lastPrice - prevPrice) / prevPrice) * 100;
                if (priceChangeEl) {
                    priceChangeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
                    priceChangeEl.className = change >= 0 ? 'change positive' : 'change negative';
                }
            }

            const lastVolume = chartData.volume[chartData.volume.length - 1];
            if (volumeEl) {
                volumeEl.textContent = lastVolume.toFixed(2);
            }

            // Update current price line
            updateCurrentPriceLine();
        }

        // Reset initialization flag before rendering to ensure default view is applied
        chartInitialized = false;

        // Render chart (will apply default view on first render)
        renderChart();

        // Hide loading overlay as soon as chart is rendered
        hideLoadingOverlay();

        // Expose chart references for indicator engine and other modules
        window.chartData = chartData;
        window.chartGroup = g;
        window.baseXScale = baseXScale;
        window.baseYScale = baseYScale;
        window.xScale = xScale;
        window.yScale = yScale;

        // Expose chart control functions for interval bar and other modules
        window.updateCandlesticks = updateCandlesticks;
        window.updateAxesAndGrid = updateAxesAndGrid;
        window.updateYAxisFromVisibleCandles = updateYAxisFromVisibleCandles;
        window.updateChartDisplayImmediate = updateChartDisplayImmediate;
        window.resetChartToDefault = resetChartToDefault;

        // Initialize/update chart context menu with current yScale
        if (typeof ChartContextMenu !== 'undefined') {
            const chartSvg = document.getElementById('candlestickChart');
            if (chartSvg && !ChartContextMenu._menu) {
                ChartContextMenu.init(chartSvg, baseYScale);
                console.log('📋 ChartContextMenu initialized after chart render');
            } else if (ChartContextMenu._menu) {
                ChartContextMenu.updateScale(baseYScale);
            }
        }

        // Draw algorithm renders if enabled
        await updateChartDisplay();

        // Draw direction swings (4 external swings for HTF direction)
        try {
            await drawDirectionSwings();
        } catch (e) {
            console.warn('drawDirectionSwings failed:', e);
        }

        // Update narrator's references to latest chart data and scales
        if (chartNarrator) {
            chartNarrator.chartData = chartData;
            chartNarrator.xScale = xScale;
            chartNarrator.yScale = yScale;
            console.log('📊 Updated narrator chartData reference');
        }

        // Count visible candles and log on reload
        try {
            const domain = xScale && xScale.domain ? xScale.domain() : null;
            if (domain && domain.length === 2) {
                const [visibleStart, visibleEnd] = domain;
                const xData = chartData.x || [];
                const startTs = visibleStart.getTime ? visibleStart.getTime() : visibleStart;
                const endTs = visibleEnd.getTime ? visibleEnd.getTime() : visibleEnd;
                let visibleCount = 0;
                for (let i = 0; i < xData.length; i++) {
                    const t = xData[i] && xData[i].getTime ? xData[i].getTime() : xData[i];
                    if (t >= startTs && t <= endTs) visibleCount++;
                }
                console.log(`📈 Visible candles on reload: ${visibleCount}`);
            } else {
                console.log('📈 Visible candles on reload: domain unavailable');
            }
        } catch (e) {
            console.warn('Could not compute visible candle count:', e);
        }
        // Load narrator analysis only if enabled
        if (chartNarrator && renderStates.narrator) {
            try {
                await chartNarrator.loadAnalysis(currentSymbol, currentTimeframe, { swingOnly: true });
                console.log('✅ Narrator analysis loaded');
            } catch (error) {
                console.error('❌ Failed to load narrator analysis:', error);
            }
        }

        // Load zone visibility data for dynamic drawing filtering
        if (typeof window.ZoneVisibilityController !== 'undefined') {
            try {
                const zoneResponse = await fetch(`/api/core/zone-visibility?symbol=${currentSymbol}&timeframe=${currentTimeframe}&periods=${chartData.x.length}`);
                const zoneData = await zoneResponse.json();
                if (zoneData.success) {
                    // Cache zone data for use in renderChart
                    window.cachedZoneData = {
                        zones: zoneData.visibility.zones || [],
                        currentPrice: zoneData.current_price,
                        totalZones: zoneData.visibility.total_zones,
                    };
                    console.log(`✅ Zone visibility loaded: ${zoneData.visibility.visible_zones} visible zones`);
                }
            } catch (error) {
                console.error('❌ Failed to load zone visibility:', error);
            }
        }

        clearTimeout(timeoutId); // Clear timeout on success
        console.log('Chart loaded successfully');
    } catch (error) {
        clearTimeout(timeoutId); // Clear timeout on error
        console.error('Error loading historical data:', error);

        // Show error in overlay
        const loading = document.getElementById('loadingOverlay');
        if (loading) {
            loading.innerHTML = `
                <div class="error-message">
                    <p style="color: #ef4444; font-weight: bold;">Failed to load chart data</p>
                    <p style="color: #666;">${error.message || 'Network error - check console for details'}</p>
                    <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Retry</button>
                </div>
            `;
            loading.classList.remove('hidden');
        }
    } finally {
        // Loading overlay is now hidden immediately after chart render
        // (moved earlier to show chart as soon as it's ready)
    }
}

/**
 * Render candlestick chart using D3.js
 */
function renderChart() {
    if (!chartData.x || chartData.x.length === 0) return;

    // Prepare data
    const data = chartData.x.map((timestamp, i) => ({
        timestamp,
        open: chartData.open[i],
        high: chartData.high[i],
        low: chartData.low[i],
        close: chartData.close[i],
        volume: chartData.volume[i]
    }));

    // Zoom limits are calculated once in loadHistoricalData() based on full data range
    // They remain constant and independent of main chart zoom or current view

    // Only update base scales domains on initial load
    // This preserves the user's current pan/zoom position when toggling renders
    if (!chartInitialized) {
        // Ensure scales are initialized and have ranges before setting default view
        if (baseXScale && baseYScale) {
            // Ensure ranges are set (they should be set in initializeChart, but double-check)
            if (!baseXScale.range() || baseXScale.range().length === 0) {
                baseXScale.range([0, chartWidth]);
            }
            if (!baseYScale.range() || baseYScale.range().length === 0) {
                baseYScale.range([chartHeight, 0]);
            }
            // Set default view (3x zoom, 10% right margin, 5% top/bottom padding)
            setDefaultChartView(data);
            chartInitialized = true;
        } else {
            // If scales don't exist yet, set them up with default view
            console.warn('Scales not initialized, setting up default view');
            baseXScale = d3.scaleTime().range([0, chartWidth]);
            baseYScale = d3.scaleLinear().range([chartHeight, 0]);
            setDefaultChartView(data);
            chartInitialized = true;
        }
    }

    // Use base scales directly (no zoom transform applied)
    xScale = baseXScale;
    yScale = baseYScale;

    // Initialize DrawingManager if not already done
    if (typeof DrawingManager !== 'undefined' && !DrawingManager.isInitialized) {
        if (g) {
            DrawingManager.init(g, 'chart-clip');
            // S/R zones drawing disabled - using core structure drawings instead
            // if (typeof SRZonesDrawing !== 'undefined') {
            //     SRZonesDrawing.register();
            // }
            DrawingManager.setScales(xScale, yScale);
        }
    }

    // Update DrawingManager context and refresh if symbol/timeframe changed
    if (typeof DrawingManager !== 'undefined' && DrawingManager.isInitialized) {
        const contextChanged = DrawingManager.setContext(currentSymbol, currentTimeframe);
        DrawingManager.setScales(xScale, yScale);
        if (contextChanged) {
            DrawingManager.refresh();  // Full refresh on context change
        }
    }

    // Update axes and grid (separate function for performance)
    updateAxesAndGrid();

    // Update candlesticks (separate function for performance)
    updateCandlesticks();

    // Update zone visibility controller with current price
    // This dynamically shows/hides drawings based on price position relative to zones
    if (typeof window.ZoneVisibilityController !== 'undefined' && chartData.close && chartData.close.length > 0) {
        const currentPrice = chartData.close[chartData.close.length - 1];

        // If we have cached zone data, update visibility
        if (window.cachedZoneData && window.cachedZoneData.zones) {
            window.ZoneVisibilityController.init(window.cachedZoneData.zones, currentPrice);
        } else {
            // Just update with current price (will recalculate when zones are loaded)
            window.ZoneVisibilityController.update(currentPrice);
        }
    }
}

/**
 * Reset chart to default state (reset pan/zoom to initial view)
 * Shows the most recent candles with 10% space on the right
 */
function resetChartToDefault() {
    if (!chartData || !chartData.x || chartData.x.length === 0) return;

    // Prepare data
    const data = chartData.x.map((timestamp, i) => ({
        timestamp,
        open: chartData.open[i],
        high: chartData.high[i],
        low: chartData.low[i],
        close: chartData.close[i],
        volume: chartData.volume[i]
    }));

    // Calculate view to show most recent candles (like initial load)
    // Use viewport capacity to determine how many candles to show
    const viewportCapacity = getViewportCandleCapacity();
    const candlesToShow = Math.min(viewportCapacity, chartData.x.length);

    // Get the most recent candles (end of the array)
    const lastCandle = chartData.x[chartData.x.length - 1];
    const firstVisibleCandle = chartData.x[Math.max(0, chartData.x.length - candlesToShow)];

    // Calculate time range for visible candles
    const visibleTimeRange = lastCandle.getTime() - firstVisibleCandle.getTime();

    // Position so last candle has 10% space on the right
    const rightEdge = lastCandle.getTime();
    const adjustedRightEdge = rightEdge + (visibleTimeRange * 0.1);
    const adjustedLeftEdge = rightEdge - (visibleTimeRange * 0.9);

    // Update xScale to show the reset view (but keep baseXScale covering all data)
    xScale.domain([
        new Date(adjustedLeftEdge),
        new Date(adjustedRightEdge)
    ]);

    // Update y-axis to show only visible candles (90% of chart height)
    updateYAxisFromVisibleCandles(data);

    // Update scales
    yScale = baseYScale;

    // Update chart
    if (renderAnimationFrame) {
        cancelAnimationFrame(renderAnimationFrame);
    }
    renderAnimationFrame = requestAnimationFrame(() => {
        updateAxesAndGrid();
        updateCandlesticks();
        if (updateThrottleTimer) {
            clearTimeout(updateThrottleTimer);
            updateThrottleTimer = null;
        }
        updateChartDisplayImmediate();
        recordFrameForFps();
    });
}

/**
 * Update axes and grid (optimized, called separately)
 */
function updateAxesAndGrid() {
    if (!xScale || !yScale) return;

    // Update axes with crisp rendering
    xAxis.call(d3.axisBottom(xScale)
        .tickFormat('') // Remove x-axis labels
        .tickSize(0)) // Remove tick marks
        .style('shape-rendering', 'crispEdges'); // Crisp axis lines

    yAxis.call(d3.axisRight(yScale)
        .tickFormat(d => `$${d.toFixed(2)}`))
        .style('shape-rendering', 'crispEdges'); // Crisp axis lines

    // Grid lines - black with 5% opacity, 1px width
    // Vertical grid lines (from x-axis ticks) - doubled count for reasonable density
    const defaultXTicks = xScale.ticks();
    const xTickCount = defaultXTicks.length * 2; // Double (reduced from 4x for performance)
    const xTicks = xScale.ticks(xTickCount);
    const gridX = g.selectAll('.grid-x')
        .data(xTicks, d => d.getTime ? d.getTime() : d);

    gridX.enter()
        .append('line')
        .attr('class', 'grid grid-x')
        .merge(gridX)
        .attr('x1', d => Math.round(xScale(d)) + 0.5) // Half-pixel alignment for crisp 1px lines
        .attr('x2', d => Math.round(xScale(d)) + 0.5) // Half-pixel alignment for crisp 1px lines
        .attr('y1', 0)
        .attr('y2', chartHeight)
        .style('stroke', 'rgba(0, 0, 0, 0)') // Disabled - set to 0 opacity
        .style('stroke-width', '1px')
        .style('shape-rendering', 'crispEdges') // Crisp grid lines
        .style('pointer-events', 'none');

    gridX.exit().remove();

    // Add labels on each vertical grid line (only show if there's enough space)
    const gridXLabels = g.selectAll('.grid-x-label')
        .data(xTicks, d => d.getTime ? d.getTime() : d);

    // Calculate minimum spacing needed between labels (approximate text width + padding)
    const minLabelSpacing = 50; // pixels
    const labelData = [];
    let lastLabelX = -Infinity;

    // Filter labels to prevent overlap
    xTicks.forEach(tick => {
        const x = xScale(tick);
        if (x - lastLabelX >= minLabelSpacing) {
            labelData.push(tick);
            lastLabelX = x;
        }
    });

    const filteredLabels = g.selectAll('.grid-x-label')
        .data(labelData, d => d.getTime ? d.getTime() : d);

    filteredLabels.enter()
        .append('text')
        .attr('class', 'grid-x-label')
        .merge(filteredLabels)
        .attr('x', d => xScale(d))
        .attr('y', chartHeight + 8) // Position below the chart with better spacing
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'hanging')
        .style('font-size', '11px')
        .style('font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif')
        .style('fill', 'var(--text-secondary, #787b86)') // Theme-aware color
        .style('pointer-events', 'none')
        .text(d => {
            // Check if time is 00:00 (midnight)
            const hours = d.getHours();
            const minutes = d.getMinutes();

            if (hours === 0 && minutes === 0) {
                // Show day number and day of week for midnight
                const dayOfMonth = d.getDate();
                const dayOfWeek = d3.timeFormat('%a')(d); // Mon, Tue, Wed, etc.
                return `${dayOfMonth} ${dayOfWeek}`;
            } else {
                // Show time for other hours
                return d3.timeFormat('%H:%M')(d);
            }
        });

    filteredLabels.exit().remove();

    // Horizontal grid lines (from y-axis ticks) - use default count for performance
    const defaultYTicks = yScale.ticks();
    const yTickCount = defaultYTicks.length; // Use default count (reduced from 2x for performance)
    const yTicks = yScale.ticks(yTickCount);
    const gridY = g.selectAll('.grid-y')
        .data(yTicks, d => d);

    gridY.enter()
        .append('line')
        .attr('class', 'grid grid-y')
        .merge(gridY)
        .attr('x1', 0)
        .attr('x2', chartWidth)
        .attr('y1', d => Math.round(yScale(d)) + 0.5) // Half-pixel alignment for crisp 1px lines
        .attr('y2', d => Math.round(yScale(d)) + 0.5) // Half-pixel alignment for crisp 1px lines
        .style('stroke', 'rgba(0, 0, 0, 0)') // Disabled - set to 0 opacity
        .style('stroke-width', '1px')
        .style('shape-rendering', 'crispEdges') // Crisp grid lines
        .style('pointer-events', 'none');

    gridY.exit().remove();

    // Update current price line
    updateCurrentPriceLine();

    // Check if we need to load more historical candles (debounced lazy loading)
    // This triggers on any pan/zoom interaction
    if (checkNeedMoreCandles()) {
        loadMoreHistoricalCandles();
    }
}

/**
 * Update the current price line position
 */
function updateCurrentPriceLine() {
    if (!currentPriceLine || !yScale || !chartData.close || chartData.close.length === 0) return;

    const currentPrice = chartData.close[chartData.close.length - 1];
    const yPosition = yScale(currentPrice);

    // Determine if bullish or bearish (compare to previous close or open)
    const lastOpen = chartData.open ? chartData.open[chartData.open.length - 1] : currentPrice;
    const isBullish = currentPrice >= lastOpen;
    const priceColor = isBullish ? 'var(--candle-up, #089981)' : 'var(--candle-down, #f23645)';

    // Update line position with half-pixel alignment for crisp rendering
    currentPriceLine
        .attr('x1', 0)
        .attr('x2', chartWidth)
        .attr('y1', Math.round(yPosition) + 0.5) // Half-pixel alignment
        .attr('y2', Math.round(yPosition) + 0.5) // Half-pixel alignment
        .style('stroke', priceColor)
        .style('display', 'block');

    // Update current price badge on Y-axis
    if (window._currentPriceBadge) {
        const badge = window._currentPriceBadge;
        const priceText = currentPrice >= 1000
            ? `$${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : currentPrice >= 1
                ? `$${currentPrice.toFixed(4)}`
                : `$${currentPrice.toFixed(6)}`;

        // Get the text element and update it
        const textEl = badge.select('.current-price-badge-text');
        textEl.text(priceText);

        // Calculate badge dimensions
        const textNode = textEl.node();
        const textBBox = textNode ? textNode.getBBox() : { width: 70, height: 14 };
        const padding = 6;
        const badgeWidth = textBBox.width + padding * 2;
        const badgeHeight = 22;

        // Position badge on Y-axis (right side of chart)
        const badgeX = margin.left + chartWidth + 12;
        const badgeY = margin.top + yPosition - badgeHeight / 2;

        // Update background
        badge.select('.current-price-badge-bg')
            .attr('x', badgeX)
            .attr('y', badgeY)
            .attr('width', badgeWidth)
            .style('fill', isBullish ? '#089981' : '#f23645');

        // Update arrow (pointing left into the chart)
        badge.select('.current-price-badge-arrow')
            .attr('d', `M${badgeX} ${margin.top + yPosition} L${badgeX - 6} ${margin.top + yPosition - 5} L${badgeX - 6} ${margin.top + yPosition + 5} Z`)
            .style('fill', isBullish ? '#089981' : '#f23645');

        // Update text position
        textEl
            .attr('x', badgeX + padding)
            .attr('y', margin.top + yPosition);

        // Show badge
        badge.style('display', 'block');
    }
}

/**
 * Update candlesticks (optimized, uses data join pattern)
 */
function updateCandlesticks() {
    if (!chartData.x || chartData.x.length === 0 || !candlestickContainer) return;

    // Get visible time range from scale
    const visibleDomain = xScale.domain();
    const visibleStart = visibleDomain[0].getTime();
    const visibleEnd = visibleDomain[1].getTime();

    // Add buffer (10% on each side) for smooth scrolling
    const buffer = (visibleEnd - visibleStart) * 0.1;
    const cullStart = visibleStart - buffer;
    const cullEnd = visibleEnd + buffer;

    // Prepare only visible data (viewport culling for performance)
    const data = [];
    for (let i = 0; i < chartData.x.length; i++) {
        const ts = chartData.x[i].getTime();
        if (ts >= cullStart && ts <= cullEnd) {
            data.push({
                timestamp: chartData.x[i],
                open: chartData.open[i],
                high: chartData.high[i],
                low: chartData.low[i],
                close: chartData.close[i],
                volume: chartData.volume[i]
            });
        }
    }

    // Efficient data join: only update what changed
    const candlesticks = candlestickContainer.selectAll('.candlestick')
        .data(data, d => d.timestamp.getTime()); // Use timestamp as key for efficient updates

    // Remove old candlesticks
    candlesticks.exit().remove();

    // Enter: create new candlesticks
    const candlesticksEnter = candlesticks.enter()
        .append('g')
        .attr('class', 'candlestick')
        .style('cursor', 'pointer');

    // Draw wicks for new candlesticks
    candlesticksEnter.append('line')
        .attr('class', 'wick wick-top');

    candlesticksEnter.append('line')
        .attr('class', 'wick wick-bottom');

    candlesticksEnter.append('rect')
        .attr('class', 'body');

    // Merge enter and update selections
    const candlesticksMerged = candlesticksEnter.merge(candlesticks);

    // Calculate body width (cached calculation)
    let bodyWidth;
    if (data.length > 1) {
        const sampleSize = Math.min(10, Math.floor(data.length / 2));
        let totalSpacing = 0;
        let spacingCount = 0;

        for (let i = 0; i < sampleSize && i < data.length - 1; i++) {
            const x1 = xScale(data[i].timestamp);
            const x2 = xScale(data[i + 1].timestamp);
            totalSpacing += Math.abs(x2 - x1);
            spacingCount++;
        }

        const avgSpacing = spacingCount > 0 ? totalSpacing / spacingCount : chartWidth / data.length;
        // No zoom scale applied (zoom removed)
        const widthPercentage = 0.6;
        bodyWidth = Math.max(1, Math.min(50, avgSpacing * widthPercentage));
    } else {
        // No zoom scale applied (zoom removed)
        bodyWidth = Math.max(2, Math.min(50, (chartWidth / Math.max(data.length, 10)) * 0.6));
    }

    // Update all candlesticks (position and appearance) with pixel-perfect alignment
    // Add 0.5px spacing between candles by offsetting each candle based on its index
    candlesticksMerged
        .attr('transform', d => {
            const x = xScale(d.timestamp);
            // Add 0.25px spacing on each side (0.5px total between candles)
            const spacingOffset = (d.index || 0) * 0.5;
            return `translate(${x + spacingOffset},0)`;
        });

    // Update wicks - centered at x=0 to align with body center
    // Use exact yScale values without rounding to prevent cumulative shifting
    candlesticksMerged.select('.wick-top')
        .attr('x1', 0)
        .attr('x2', 0)
        .attr('y1', d => yScale(Math.max(d.open, d.close))) // Exact value, no rounding
        .attr('y2', d => yScale(d.high)) // Exact value, no rounding
        .attr('stroke', d => d.close >= d.open ? '#10b981' : '#ef4444')
        .attr('stroke-width', 1)
        .style('shape-rendering', 'crispEdges'); // Crisp wick lines

    candlesticksMerged.select('.wick-bottom')
        .attr('x1', 0)
        .attr('x2', 0)
        .attr('y1', d => yScale(Math.min(d.open, d.close))) // Exact value, no rounding
        .attr('y2', d => yScale(d.low)) // Exact value, no rounding
        .attr('stroke', d => d.close >= d.open ? '#10b981' : '#ef4444')
        .attr('stroke-width', 1)
        .style('shape-rendering', 'crispEdges'); // Crisp wick lines

    // Update bodies - centered at x=0 to align with wick center
    // Use exact yScale values without rounding to prevent cumulative shifting
    candlesticksMerged.select('.body')
        .attr('x', -bodyWidth / 2) // Center at x=0 (exact calculation, perfect centering with wick)
        .attr('y', d => yScale(Math.max(d.open, d.close))) // Exact value, no rounding
        .attr('width', bodyWidth) // Use exact width (no rounding) to maintain perfect centering
        .attr('height', d => Math.max(1, Math.abs(yScale(d.close) - yScale(d.open)))) // Exact value, min 1px
        .attr('fill', d => d.close >= d.open ? '#10b981' : '#ef4444')
        .attr('stroke', d => d.close >= d.open ? '#10b981' : '#ef4444') // Border same color as body
        .attr('stroke-width', 1)
        .style('shape-rendering', 'crispEdges'); // Crisp edges for sharp rectangles
}

/**
 * Handle zoom event (throttled for performance)
 */
// Main chart zoom handler removed - zoom functionality disabled for main chart panel

/**
 * Handle y-axis zoom event (vertical zoom only)
 * Scroll down / drag down = zoom out (larger price range)
 * Scroll up / drag up = zoom in (smaller price range)
 */
function handleYAxisZoom(event) {
    // For drag events, handle zoom based on vertical movement
    if (event.sourceEvent && event.sourceEvent.type === 'mousedown') {
        // Store initial state when drag starts
        yAxisDragStartY = event.sourceEvent.clientY;
        yAxisDragStartDomain = baseYScale.domain().slice(); // Copy array
        return;
    }

    if (event.sourceEvent && event.sourceEvent.type === 'mousemove' && event.sourceEvent.buttons === 1 && yAxisDragStartY !== null) {
        // Calculate vertical drag distance
        const currentY = event.sourceEvent.clientY;
        const deltaY = currentY - yAxisDragStartY;

        // Calculate vertical position in y-axis label area (0 = bottom, 1 = top)
        // Get the y-axis zoom area element
        const yAxisRect = yAxisZoomArea.node().getBoundingClientRect();
        const currentYRelative = currentY - yAxisRect.top;
        const positionFromBottom = 1 - (currentYRelative / yAxisRect.height); // 0 at top, 1 at bottom

        // Calculate sensitivity multiplier based on vertical position
        // At bottom (positionFromBottom = 1): multiplier = 1.0 (100% sensitivity)
        // At top (positionFromBottom = 0): multiplier = 0.35 (35% sensitivity)
        const sensitivityMultiplier = 0.35 + (positionFromBottom * 0.65);

        // Drag down (positive deltaY) = zoom in (decrease range) - INVERTED
        // Drag up (negative deltaY) = zoom out (increase range) - INVERTED
        const baseDragSensitivity = 0.001; // Base sensitivity
        const dragSensitivity = baseDragSensitivity * sensitivityMultiplier;

        if (yAxisDragStartDomain) {
            const startRange = yAxisDragStartDomain[1] - yAxisDragStartDomain[0];
            // Always use the center of the initial price domain as zoom center
            const priceCenterY = (yAxisDragStartDomain[0] + yAxisDragStartDomain[1]) / 2;

            // Calculate zoom factor from drag distance
            // Positive deltaY (drag down) decreases range (zoom in) - INVERTED
            // Negative deltaY (drag up) increases range (zoom out) - INVERTED
            const zoomFactor = 1 - (deltaY * dragSensitivity);

            let newYDomainRange = startRange / zoomFactor;

            // Apply zoom limits
            if (yAxisMinRange !== null && newYDomainRange < yAxisMinRange) {
                newYDomainRange = yAxisMinRange;
            }
            if (yAxisMaxRange !== null && newYDomainRange > yAxisMaxRange) {
                newYDomainRange = yAxisMaxRange;
            }

            // Always zoom from the vertical center of the price range
            const newYDomain = [
                priceCenterY - newYDomainRange / 2,
                priceCenterY + newYDomainRange / 2
            ];

            // Clamp domain to prevent invalid ranges
            if (newYDomainRange > 0 && newYDomain[0] < newYDomain[1]) {
                baseYScale.domain(newYDomain);

                // Update working scale (no transform needed - we use baseYScale directly)
                yScale = baseYScale;

                // Update chart
                if (renderAnimationFrame) {
                    cancelAnimationFrame(renderAnimationFrame);
                }
                renderAnimationFrame = requestAnimationFrame(() => {
                    updateAxesAndGrid();
                    updateCandlesticks();
                    if (updateThrottleTimer) {
                        clearTimeout(updateThrottleTimer);
                        updateThrottleTimer = null;
                    }
                    updateChartDisplayImmediate();
                    recordFrameForFps();
                });
            }
        }
        return;
    }

    if (event.sourceEvent && event.sourceEvent.type === 'mouseup') {
        // Reset drag state
        yAxisDragStartY = null;
        yAxisDragStartDomain = null;
        return;
    }
}

function handleXAxisZoom(event) {
    // For drag events, handle zoom based on horizontal movement
    if (event.sourceEvent && event.sourceEvent.type === 'mousedown') {
        // Store initial state when drag starts
        xAxisDragStartX = event.sourceEvent.clientX;
        xAxisDragStartDomain = baseXScale.domain().slice(); // Copy array
        return;
    }

    if (event.sourceEvent && event.sourceEvent.type === 'mousemove' && event.sourceEvent.buttons === 1 && xAxisDragStartX !== null) {
        // Calculate horizontal drag distance
        const currentX = event.sourceEvent.clientX;
        const deltaX = currentX - xAxisDragStartX;

        // Calculate horizontal position in x-axis label area (0 = left, 1 = right)
        // Get the x-axis zoom area element
        const xAxisRect = xAxisZoomArea.node().getBoundingClientRect();
        const currentXRelative = currentX - xAxisRect.left;
        const positionFromLeft = currentXRelative / xAxisRect.width; // 0 at left, 1 at right

        // Calculate sensitivity multiplier based on horizontal position
        // At center (positionFromLeft = 0.5): multiplier = 1.0 (100% sensitivity)
        // At edges (positionFromLeft = 0 or 1): multiplier = 0.35 (35% sensitivity)
        const distanceFromCenter = Math.abs(positionFromLeft - 0.5) * 2; // 0 at center, 1 at edges
        const sensitivityMultiplier = 0.35 + ((1 - distanceFromCenter) * 0.65);

        // Drag right (positive deltaX) = zoom in (decrease range) - INVERTED
        // Drag left (negative deltaX) = zoom out (increase range) - INVERTED
        const baseDragSensitivity = 0.001; // Base sensitivity
        const dragSensitivity = baseDragSensitivity * sensitivityMultiplier;

        if (xAxisDragStartDomain) {
            const startRange = xAxisDragStartDomain[1] - xAxisDragStartDomain[0];
            // Always use the center of the initial time domain as zoom center
            const timeCenterX = (xAxisDragStartDomain[0] + xAxisDragStartDomain[1]) / 2;

            // Calculate zoom factor from drag distance
            // Positive deltaX (drag right) decreases range (zoom in) - INVERTED
            // Negative deltaX (drag left) increases range (zoom out) - INVERTED
            const zoomFactor = 1 - (deltaX * dragSensitivity);

            let newXDomainRange = startRange / zoomFactor;

            // Apply zoom limits
            if (xAxisMinRange !== null && newXDomainRange < xAxisMinRange) {
                newXDomainRange = xAxisMinRange;
            }
            if (xAxisMaxRange !== null && newXDomainRange > xAxisMaxRange) {
                newXDomainRange = xAxisMaxRange;
            }

            // Always zoom from the horizontal center of the time range
            const newXDomain = [
                timeCenterX - newXDomainRange / 2,
                timeCenterX + newXDomainRange / 2
            ];

            // Clamp domain to prevent invalid ranges
            if (newXDomainRange > 0 && newXDomain[0] < newXDomain[1]) {
                baseXScale.domain(newXDomain);

                // Update working scale (no transform needed - we use baseXScale directly)
                xScale = baseXScale;

                // Update chart
                if (renderAnimationFrame) {
                    cancelAnimationFrame(renderAnimationFrame);
                }
                renderAnimationFrame = requestAnimationFrame(() => {
                    updateAxesAndGrid();
                    updateCandlesticks();
                    if (updateThrottleTimer) {
                        clearTimeout(updateThrottleTimer);
                        updateThrottleTimer = null;
                    }
                    updateChartDisplayImmediate();
                    recordFrameForFps();

                    // Check if we need to load more historical candles (lazy loading)
                    if (checkNeedMoreCandles()) {
                        loadMoreHistoricalCandles();
                    }
                });
            }
        }
        return;
    }

    if (event.sourceEvent && event.sourceEvent.type === 'mouseup') {
        // Reset drag state
        xAxisDragStartX = null;
        xAxisDragStartDomain = null;
        return;
    }
}

// X-axis zoom functionality removed - now handled by main chart zoom with x-axis zoom logic

// Main chart zoom functions removed - zoom functionality disabled for main chart panel

async function updateChartDisplayImmediate() {
    if (!chartData || chartData.x.length === 0) return;

    g.selectAll('.algorithm-overlay').remove();
    g.selectAll('.key-level-line').remove();
    g.selectAll('.key-level-label').remove();
    g.selectAll('.key-level-label-bg').remove();
    g.selectAll('.key-level-type').remove();
    g.selectAll('.key-level-type-bg').remove();

    const overlay = g.append('g')
        .attr('class', 'algorithm-overlay')
        .attr('clip-path', 'url(#chart-clip)');

    const promises = [];
    if (renderStates.swings) promises.push(detectAndDrawSwings(overlay));
    if (renderStates.volatility) promises.push(detectAndDrawVolatility(overlay));
    if (renderStates.momentum) promises.push(detectAndDrawMomentum(overlay));
    if (renderStates.volume) promises.push(detectAndDrawVolume(overlay));
    if (renderStates.emas) promises.push(detectAndDrawEMAs(overlay));
    if (renderStates.consolidation) promises.push(detectAndDrawConsolidation(overlay));
    await Promise.all(promises);

    if (typeof DrawingManager !== 'undefined' && DrawingManager.isInitialized) {
        DrawingManager.updateScales(xScale, yScale);
    }

    if (typeof MarketNarrator !== 'undefined' && MarketNarrator.update) {
        MarketNarrator.update(currentSymbol, currentTimeframe, chartData, window.latestCoreViewModel || null);
    }
}

async function updateChartDisplay() {
    if (!chartData || chartData.x.length === 0) return;

    // Throttle updates to prevent excessive rendering
    if (updateThrottleTimer) {
        clearTimeout(updateThrottleTimer);
    }

    updateThrottleTimer = setTimeout(async () => {
        await updateChartDisplayImmediate();
    }, 50); // 50ms throttle
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    console.log('🔧 setupEventListeners called');

    // Get fresh references to DOM elements (in case they weren't available at module load time)
    const symbolSelectEl = document.getElementById('symbolSelect');
    const timeframeSelectEl = document.getElementById('timeframeSelect');

    console.log('🔧 symbolSelectEl:', symbolSelectEl);
    console.log('🔧 timeframeSelectEl:', timeframeSelectEl);

    if (!symbolSelectEl || !timeframeSelectEl) {
        console.error('❌ Could not find symbolSelect or timeframeSelect elements');
        return;
    }

    console.log('✅ Setting up event listeners for selects');

    symbolSelectEl.addEventListener('change', async (e) => {
        console.log('📊 Symbol changed to:', e.target.value);
        const wasRunning = isRunning;
        if (wasRunning) stopUpdate();
        currentSymbol = e.target.value;
        window.currentSymbol = currentSymbol; // Update for ConsolePrint
        window.dispatchEvent(new CustomEvent('chartContextChanged', {
            detail: { symbol: currentSymbol, timeframe: currentTimeframe }
        }));

        // Show loading state on bento cards and narrator panel
        showPanelsLoading();

        // Clear pipeline cache to ensure fresh data for new symbol
        if (window.pipelineCache) {
            window.pipelineCache.clear();
            console.log('🗑️ Cleared pipeline cache for symbol change');
        }

        // Clear stored analysis data
        window.deepPhaseAnalysisData = null;
        window.lastMarketAnalysisData = null;
        window.lastMarketNarrative = null;
        window.lastMarketWarnings = null;

        if (window.updateChartTitle) window.updateChartTitle();
        try {
            await resetChart();
            if (wasRunning) await startUpdate();

            // Update Core Engine with new symbol
            if (typeof CoreEngine !== 'undefined' && CoreEngine.setSymbol) {
                CoreEngine.setSymbol(currentSymbol);
            }
        } finally {
            // Hide loading state after data is loaded
            hidePanelsLoading();
        }
    });

    // Debounce timeframe changes
    let timeframeSwitchTimeout = null;
    timeframeSelectEl.addEventListener('change', async (e) => {
        console.log('⏱️ Timeframe change event fired:', e.target.value);

        // Clear any pending timeframe switch
        if (timeframeSwitchTimeout) {
            clearTimeout(timeframeSwitchTimeout);
        }

        const wasRunning = isRunning;
        if (wasRunning) stopUpdate();
        currentTimeframe = e.target.value;
        window.currentTimeframe = currentTimeframe; // Update for ConsolePrint
        window.dispatchEvent(new CustomEvent('chartContextChanged', {
            detail: { symbol: currentSymbol, timeframe: currentTimeframe }
        }));

        // Save selected timeframe to localStorage
        localStorage.setItem('selectedTimeframe', currentTimeframe);

        // Show loading state on bento cards and narrator panel
        showPanelsLoading();

        // Clear pipeline cache to ensure fresh data for new timeframe
        if (window.pipelineCache) {
            window.pipelineCache.clear();
            console.log('🗑️ Cleared pipeline cache for timeframe change');
        }

        // Clear stored analysis data
        window.deepPhaseAnalysisData = null;
        window.lastMarketAnalysisData = null;
        window.lastMarketNarrative = null;
        window.lastMarketWarnings = null;

        if (window.updateChartTitle) window.updateChartTitle();

        // Reset chart with new timeframe data
        console.log(`⏱️ Switching timeframe to ${currentTimeframe}...`);
        timeframeSwitchTimeout = setTimeout(async () => {
            try {
                await resetChart();
                if (wasRunning) await startUpdate();

                // Update Core Engine with new timeframe
                if (typeof CoreEngine !== 'undefined' && CoreEngine.setTimeframe) {
                    CoreEngine.setTimeframe(currentTimeframe);
                }
            } finally {
                // Hide loading state after data is loaded
                hidePanelsLoading();
            }
        }, 100);
    });

    // Reset chart button
    const resetChartBtn = document.getElementById('resetChartBtn');
    if (resetChartBtn) {
        resetChartBtn.addEventListener('click', resetChartToDefault);
    }

    // Theme toggle
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }

    // Initialize chart context menu (right-click)
    if (typeof ChartContextMenu !== 'undefined') {
        const chartSvg = document.getElementById('candlestickChart');
        if (chartSvg) {
            ChartContextMenu.init(chartSvg, baseYScale);
            console.log('📋 ChartContextMenu initialized');
        }
    }

    // Start/Stop, Reset, and Zoom buttons removed from UI
    // Zoom still works via mouse wheel/gestures

    // ========================================
    // FAVORITE TIMEFRAMES FUNCTIONALITY
    // ========================================
    initializeFavoriteTimeframes();
}

/**
 * Initialize favorite timeframes functionality
 * - Loads favorites from localStorage
 * - Renders favorite chips
 * - Sets up custom dropdown with inline star buttons
 */
function initializeFavoriteTimeframes() {
    const STORAGE_KEY = 'favoriteTimeframes';
    const favoritesContainer = document.getElementById('favoriteTimeframes');
    const favoritesDivider = document.getElementById('favoritesDivider');
    const timeframeSelectEl = document.getElementById('timeframeSelect');

    // Custom dropdown elements
    const dropdownWrapper = document.getElementById('timeframeDropdownWrapper');
    const dropdownTrigger = document.getElementById('timeframeDropdownTrigger');
    const dropdownMenu = document.getElementById('timeframeDropdownMenu');
    const timeframeCurrent = document.getElementById('timeframeCurrent');

    if (!favoritesContainer || !timeframeSelectEl) {
        console.warn('⚠️ Favorite timeframes elements not found');
        return;
    }

    // Load favorites from localStorage
    function loadFavorites() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            console.warn('Failed to load favorite timeframes:', e);
            return [];
        }
    }

    // Save favorites to localStorage
    function saveFavorites(favorites) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
        } catch (e) {
            console.warn('Failed to save favorite timeframes:', e);
        }
    }

    // Get display name for timeframe
    function getTimeframeDisplay(tf) {
        const displays = {
            '1m': '1m', '5m': '5m', '15m': '15m',
            '1h': '1H', '4h': '4H', '1d': '1D',
            '1w': '1W', '1M': '1M'
        };
        return displays[tf] || tf.toUpperCase();
    }

    // Toggle dropdown open/close
    function toggleDropdown(forceClose = false) {
        if (!dropdownMenu || !dropdownTrigger) return;

        if (forceClose || dropdownMenu.classList.contains('show')) {
            dropdownMenu.classList.remove('show');
            dropdownTrigger.classList.remove('open');
        } else {
            dropdownMenu.classList.add('show');
            dropdownTrigger.classList.add('open');
            updateDropdownStars();
            updateDropdownActiveItem();
        }
    }

    // Update star buttons in dropdown to reflect favorites
    function updateDropdownStars() {
        if (!dropdownMenu) return;
        const favorites = loadFavorites();
        const starBtns = dropdownMenu.querySelectorAll('.tf-star-btn');

        starBtns.forEach(btn => {
            const tf = btn.dataset.tf;
            if (favorites.includes(tf)) {
                btn.classList.add('is-favorite');
            } else {
                btn.classList.remove('is-favorite');
            }
        });
    }

    // Update active item in dropdown
    function updateDropdownActiveItem() {
        if (!dropdownMenu) return;
        const currentValue = timeframeSelectEl.value;
        const items = dropdownMenu.querySelectorAll('.timeframe-dropdown-item');

        items.forEach(item => {
            if (item.dataset.value === currentValue) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    // Update dropdown trigger display
    function updateDropdownTrigger() {
        if (!timeframeCurrent) return;
        timeframeCurrent.textContent = getTimeframeDisplay(timeframeSelectEl.value);
    }

    // Render favorite chips
    function renderFavorites() {
        const favorites = loadFavorites();
        favoritesContainer.innerHTML = '';

        favorites.forEach(tf => {
            const chip = document.createElement('div');
            chip.className = 'tf-chip';
            if (tf === currentTimeframe) {
                chip.classList.add('active');
            }
            chip.dataset.timeframe = tf;

            const label = document.createElement('span');
            label.className = 'chip-label';
            label.textContent = getTimeframeDisplay(tf);

            const removeBtn = document.createElement('span');
            removeBtn.className = 'chip-remove';
            removeBtn.textContent = '×';
            removeBtn.title = 'Remove from favorites';

            chip.appendChild(label);
            chip.appendChild(removeBtn);

            // Click on chip to switch timeframe
            chip.addEventListener('click', (e) => {
                if (e.target.classList.contains('chip-remove')) return;
                timeframeSelectEl.value = tf;
                timeframeSelectEl.dispatchEvent(new Event('change'));
                updateDropdownTrigger();
            });

            // Click on remove button to unfavorite
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                removeFavorite(tf);
            });

            favoritesContainer.appendChild(chip);
        });

        // Show/hide divider based on favorites count
        if (favoritesDivider) {
            if (favorites.length > 0) {
                favoritesDivider.style.display = '';
            } else {
                favoritesDivider.style.display = 'none';
            }
        }

        // Update dropdown stars
        updateDropdownStars();
    }

    // Add timeframe to favorites
    function addFavorite(tf) {
        const favorites = loadFavorites();
        if (!favorites.includes(tf)) {
            favorites.push(tf);
            saveFavorites(favorites);
            renderFavorites();
            console.log(`⭐ Added ${tf} to favorites`);
        }
    }

    // Remove timeframe from favorites
    function removeFavorite(tf) {
        let favorites = loadFavorites();
        favorites = favorites.filter(f => f !== tf);
        saveFavorites(favorites);
        renderFavorites();
        console.log(`⭐ Removed ${tf} from favorites`);
    }

    // Toggle favorite for a specific timeframe
    function toggleFavorite(tf, starBtn) {
        const favorites = loadFavorites();

        // Add animation to star button
        if (starBtn) {
            starBtn.classList.add('animating');
            setTimeout(() => starBtn.classList.remove('animating'), 300);
        }

        if (favorites.includes(tf)) {
            removeFavorite(tf);
        } else {
            addFavorite(tf);
        }
    }

    // Update active chip when timeframe changes
    function updateActiveChip() {
        const chips = favoritesContainer.querySelectorAll('.tf-chip');
        chips.forEach(chip => {
            if (chip.dataset.timeframe === currentTimeframe) {
                chip.classList.add('active');
            } else {
                chip.classList.remove('active');
            }
        });
        updateDropdownTrigger();
        updateDropdownActiveItem();
    }

    // Setup dropdown trigger clicks - both main button and arrow button toggle dropdown
    const dropdownArrowBtn = document.getElementById('timeframeMenuToggle');

    if (dropdownTrigger) {
        dropdownTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown();
        });
    }

    if (dropdownArrowBtn) {
        dropdownArrowBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown();
        });
    }

    // Setup dropdown item clicks
    if (dropdownMenu) {
        const items = dropdownMenu.querySelectorAll('.timeframe-dropdown-item');
        items.forEach(item => {
            // Click on item (but not star) to select timeframe
            item.addEventListener('click', (e) => {
                // Ignore clicks on the star button
                if (e.target.closest('.tf-star-btn')) {
                    console.log('Click on star button - ignoring for selection');
                    return;
                }

                const value = item.dataset.value;
                console.log(`📅 Timeframe dropdown item clicked: ${value}`);

                timeframeSelectEl.value = value;
                timeframeSelectEl.dispatchEvent(new Event('change'));
                updateDropdownTrigger();

                // Force close dropdown with slight delay to ensure UI updates
                requestAnimationFrame(() => {
                    toggleDropdown(true);
                    console.log('Dropdown closed');
                });
            });
        });

        // Setup star button clicks
        const starBtns = dropdownMenu.querySelectorAll('.tf-star-btn');
        starBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const tf = btn.dataset.tf;
                toggleFavorite(tf, btn);
            });
        });
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (dropdownWrapper && !dropdownWrapper.contains(e.target)) {
            toggleDropdown(true);
        }
    });

    // Close dropdown on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            toggleDropdown(true);
        }
    });

    // Listen for timeframe changes to update UI
    timeframeSelectEl.addEventListener('change', () => {
        setTimeout(updateActiveChip, 50); // Small delay to ensure currentTimeframe is updated
    });

    // Initial render
    renderFavorites();
    updateDropdownTrigger();
    console.log('✅ Favorite timeframes initialized with custom dropdown');
}

/**
 * Listen for narrator events to highlight swings
 */
window.addEventListener('narrator-highlight-swings', (event) => {
    const { indices, timestamps } = event.detail;
    // Highlight regular swings only
    const gSelection = g.select ? g : d3.select(g);
    if (typeof window.highlightSwingPoints === 'function') {
        window.highlightSwingPoints(indices, timestamps || [], gSelection, xScale, yScale, chartData, detectedSwings);
    }
});

window.addEventListener('narrator-clear-highlights', () => {
    console.log('🧹 Clearing narrator swing highlights');
    const gSelection = g.select ? g : d3.select(g);
    if (typeof window.clearNarratorHighlights === 'function') {
        window.clearNarratorHighlights(gSelection);
    }
});

/**
 * Fetch historical candlestick data from Binance or Backend (for forex)
 * @param {string} symbol - Trading pair symbol
 * @param {string} interval - Candle interval (1m, 5m, 1h, etc)
 * @param {number} limit - Max candles to fetch (default 5000)
 * @param {Date} startTime - Optional: fetch candles AFTER this time
 * @param {Date} endTime - Optional: fetch candles BEFORE this time (for lazy loading)
 */
async function fetchHistoricalData(symbol, interval, limit = 5000, startTime = null, endTime = null) {
    // Forex pairs that need to go through backend API (Massive.com/Polygon.io)
    const FOREX_PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD'];
    const isForex = FOREX_PAIRS.includes(symbol.toUpperCase());

    if (isForex) {
        // Fetch from backend API for forex pairs
        return await fetchFromBackendAPI(symbol, interval, limit);
    }

    // Fetch from Binance for crypto pairs
    try {
        const startTimeMs = startTime ? startTime.getTime() : null;
        const endTimeMs = endTime ? endTime.getTime() : null;

        let url = `${BINANCE_API_BASE}/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`;
        if (startTimeMs) {
            url += `&startTime=${startTimeMs}`;
        }
        if (endTimeMs) {
            url += `&endTime=${endTimeMs - 1}`; // -1 to exclude the endTime candle (avoid duplicates)
        }

        console.log(`Fetching from: ${url}`);

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
        }

        const data = await response.json();

        if (!Array.isArray(data) || data.length === 0) {
            throw new Error(`No data returned from Binance API for ${symbol}`);
        }

        let candles = data.map(kline => ({
            timestamp: new Date(kline[0]),
            open: parseFloat(kline[1]),
            high: parseFloat(kline[2]),
            low: parseFloat(kline[3]),
            close: parseFloat(kline[4]),
            volume: parseFloat(kline[5])
        }));

        return candles;
    } catch (error) {
        console.error('Error fetching historical data:', error);
        throw error;
    }
}

/**
 * Fetch data from backend API (for forex pairs via Massive.com/Polygon.io)
 */
async function fetchFromBackendAPI(symbol, interval, limit) {
    try {
        const url = `${BACKEND_API_BASE}/api/chart-data?symbol=${symbol}&timeframe=${interval}&periods=${limit}`;
        console.log(`Fetching forex from backend: ${url}`);

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
        }

        const result = await response.json();

        if (!result.data || result.data.length === 0) {
            throw new Error(`No data returned from backend API for ${symbol}`);
        }

        // Convert backend format to chart format
        let candles = result.data.map(item => ({
            timestamp: new Date(item.time * 1000), // Backend returns Unix timestamp
            open: parseFloat(item.open),
            high: parseFloat(item.high),
            low: parseFloat(item.low),
            close: parseFloat(item.close),
            volume: parseFloat(item.volume || 0)
        }));

        console.log(`✅ Fetched ${candles.length} forex candles for ${symbol}`);
        return candles;
    } catch (error) {
        console.error('Error fetching from backend API:', error);
        throw error;
    }
}

/**
 * Initialize WebSocket connection for real-time updates
 * Features:
 * - Robust reconnection that handles Binance 24-hour timeout (code 1000)
 * - Health monitoring to detect zombie connections
 * - Automatic gap-filling to fetch missed candles after reconnection
 */
function initializeWebSocket() {
    // Clean up existing connection
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
        healthCheckInterval = null;
    }
    if (websocket) {
        websocket.onclose = null;
        websocket.close();
        websocket = null;
    }

    const symbol = currentSymbol.toLowerCase();
    const interval = timeframeMap[currentTimeframe] || '1h';
    const stream = `${symbol}@kline_${interval}`;
    const wsUrl = `${BINANCE_WS_BASE}/${stream}`;

    console.log(`Connecting to Binance WebSocket: ${wsUrl}`);

    // Clear any existing reconnect timeout
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }

    let reconnectAttempts = 0;
    const maxRapidReconnectAttempts = 5; // Limit for rapid reconnects (within 30s)
    const reconnectDelay = 3000;

    /**
     * Start health monitoring to detect zombie connections
     */
    const startHealthCheck = () => {
        if (healthCheckInterval) {
            clearInterval(healthCheckInterval);
        }
        healthCheckInterval = setInterval(() => {
            if (lastMessageTime && Date.now() - lastMessageTime > WS_MESSAGE_TIMEOUT) {
                console.warn('⚠️ WebSocket appears dead - no messages in 60s. Reconnecting...');
                if (websocket) {
                    websocket.close();
                }
            }
        }, WS_HEALTH_CHECK_INTERVAL);
    };

    /**
     * Fetch candles that may have been missed during disconnection
     */
    const fetchMissedCandles = async () => {
        if (chartData.x.length === 0) return;

        const lastCandleTime = chartData.x[chartData.x.length - 1].getTime();
        const now = Date.now();
        const timeSinceLast = now - lastCandleTime;

        // Get timeframe interval in milliseconds
        const tfIntervals = {
            '1m': 60000, '5m': 300000, '15m': 900000, '1h': 3600000,
            '4h': 14400000, '1d': 86400000, '1w': 604800000, '1M': 2592000000
        };
        const intervalMs = tfIntervals[currentTimeframe] || 3600000;

        // Only fetch if we might have missed candles (gap > 1.5x interval)
        if (timeSinceLast > intervalMs * 1.5) {
            console.log(`📊 Detected potential gap of ${Math.round(timeSinceLast / intervalMs)} candles, fetching missed data...`);

            try {
                const binanceInterval = timeframeMap[currentTimeframe] || '1h';
                const candlesToFetch = Math.min(100, Math.ceil(timeSinceLast / intervalMs) + 5);

                const response = await fetch(
                    `${BINANCE_API_BASE}/klines?symbol=${currentSymbol}&interval=${binanceInterval}&limit=${candlesToFetch}`
                );
                const data = await response.json();

                if (data && data.length > 0) {
                    let addedCount = 0;
                    for (const kline of data) {
                        const candleTime = new Date(kline[0]);
                        // Only add if this candle is newer than our last one
                        if (candleTime.getTime() > lastCandleTime) {
                            const existingIndex = chartData.x.findIndex(t => t.getTime() === candleTime.getTime());
                            if (existingIndex < 0) {
                                // Insert in chronological order
                                chartData.x.push(candleTime);
                                chartData.open.push(parseFloat(kline[1]));
                                chartData.high.push(parseFloat(kline[2]));
                                chartData.low.push(parseFloat(kline[3]));
                                chartData.close.push(parseFloat(kline[4]));
                                chartData.volume.push(parseFloat(kline[5]));
                                addedCount++;
                            }
                        }
                    }
                    if (addedCount > 0) {
                        console.log(`✅ Fetched ${addedCount} missed candles`);
                        // Re-render chart with new data
                        renderChart();
                    }
                }
            } catch (error) {
                console.error('Failed to fetch missed candles:', error);
            }
        }
    };

    const connect = () => {
        try {
            websocket = new WebSocket(wsUrl);

            websocket.onopen = async () => {
                console.log('✅ WebSocket connected to Binance');
                lastSuccessfulConnectionTime = Date.now();
                lastMessageTime = Date.now();
                reconnectAttempts = 0;

                if (statusEl) {
                    statusEl.textContent = 'Connected';
                    statusEl.className = 'status running';
                }

                if (reconnectTimeout) {
                    clearTimeout(reconnectTimeout);
                    reconnectTimeout = null;
                }

                // Start health monitoring
                startHealthCheck();

                // Fetch any missed candles (for reconnection scenarios)
                await fetchMissedCandles();
            };

            websocket.onmessage = async (event) => {
                lastMessageTime = Date.now(); // Update for health monitoring

                try {
                    const data = JSON.parse(event.data);

                    if (data.k) {
                        const kline = data.k;
                        const candle = {
                            timestamp: new Date(kline.t),
                            open: parseFloat(kline.o),
                            high: parseFloat(kline.h),
                            low: parseFloat(kline.l),
                            close: parseFloat(kline.c),
                            volume: parseFloat(kline.v)
                        };

                        if (kline.x) {
                            // Candle is closed - add or update it
                            await addCandleToChart(candle);
                        } else {
                            // Candle is still open - update current candle or add new one if timestamp changed
                            await updateCurrentCandle(candle);
                        }
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            websocket.onclose = (event) => {
                console.log(`WebSocket disconnected (code: ${event.code}, reason: ${event.reason || 'none'})`);

                // Clean up health monitoring
                if (healthCheckInterval) {
                    clearInterval(healthCheckInterval);
                    healthCheckInterval = null;
                }

                if (isRunning) {
                    // Determine if this is a rapid reconnect (within 30s of last success)
                    const timeSinceSuccess = lastSuccessfulConnectionTime
                        ? Date.now() - lastSuccessfulConnectionTime
                        : Infinity;
                    const isRapidReconnect = timeSinceSuccess < 30000;

                    // For rapid reconnects, apply limit to prevent infinite loops
                    // For normal disconnects (like 24-hour timeout), always reconnect
                    const shouldReconnect = !isRapidReconnect || reconnectAttempts < maxRapidReconnectAttempts;

                    if (shouldReconnect) {
                        reconnectAttempts++;
                        // Exponential backoff with cap
                        const delay = Math.min(reconnectDelay * Math.pow(1.5, reconnectAttempts - 1), 30000);

                        if (statusEl) {
                            statusEl.textContent = `Reconnecting in ${Math.round(delay / 1000)}s...`;
                            statusEl.className = 'status stopped';
                        }

                        console.log(`🔄 Scheduling reconnect in ${Math.round(delay / 1000)}s (attempt ${reconnectAttempts})`);

                        reconnectTimeout = setTimeout(() => {
                            if (isRunning) {
                                connect();
                            }
                        }, delay);
                    } else {
                        console.error('❌ Max rapid reconnection attempts reached. Please refresh the page.');
                        if (statusEl) {
                            statusEl.textContent = 'Connection Lost';
                            statusEl.className = 'status stopped';
                        }
                    }
                }
            };
        } catch (error) {
            console.error('Error creating WebSocket:', error);
        }
    };

    connect();
}

/**
 * Add new candle to chart
 */
async function addCandleToChart(candle) {
    // Check if candle already exists (by timestamp)
    const existingIndex = chartData.x.findIndex(t => t.getTime() === candle.timestamp.getTime());

    if (existingIndex >= 0) {
        // Update existing candle
        chartData.open[existingIndex] = candle.open;
        chartData.high[existingIndex] = candle.high;
        chartData.low[existingIndex] = candle.low;
        chartData.close[existingIndex] = candle.close;
        chartData.volume[existingIndex] = candle.volume;
    } else {
        // Add new candle
        chartData.x.push(candle.timestamp);
        chartData.open.push(candle.open);
        chartData.high.push(candle.high);
        chartData.low.push(candle.low);
        chartData.close.push(candle.close);
        chartData.volume.push(candle.volume);
    }

    // Update price display
    const lastPrice = chartData.close[chartData.close.length - 1];
    if (currentPriceEl) {
        currentPriceEl.textContent = `$${lastPrice.toFixed(2)}`;
    }

    // Check price alerts
    if (typeof AlertSystem !== 'undefined' && AlertSystem.checkPrice) {
        AlertSystem.checkPrice(lastPrice);
    }

    if (chartData.close.length > 1) {
        const prevPrice = chartData.close[chartData.close.length - 2];
        const change = ((lastPrice - prevPrice) / prevPrice) * 100;
        if (priceChangeEl) {
            priceChangeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
            priceChangeEl.className = change >= 0 ? 'change positive' : 'change negative';
        }
    }

    const lastVolume = chartData.volume[chartData.volume.length - 1];
    if (volumeEl) {
        volumeEl.textContent = lastVolume.toFixed(2);
    }

    // Reset initialization flag when changing symbol/timeframe so chart reinitializes
    chartInitialized = false;

    // Re-render chart
    renderChart();
    await updateChartDisplay();
}

/**
 * Update current (open) candle (optimized - only updates last candle)
 * Also handles transition to new candle when timeframe changes
 */
async function updateCurrentCandle(candle) {
    const lastIndex = chartData.x.length - 1;

    if (lastIndex < 0) {
        // No candles yet, add this one
        chartData.x.push(candle.timestamp);
        chartData.open.push(candle.open);
        chartData.high.push(candle.high);
        chartData.low.push(candle.low);
        chartData.close.push(candle.close);
        chartData.volume.push(candle.volume);

        // Full render for first candle
        renderChart();
        await updateChartDisplay();
        return;
    }

    const lastTimestamp = chartData.x[lastIndex];
    const candleTime = candle.timestamp.getTime();
    const lastTime = lastTimestamp.getTime();

    // Check if this is a new candle (timestamp is different/newer)
    if (candleTime > lastTime) {
        // New candle has started - add it
        chartData.x.push(candle.timestamp);
        chartData.open.push(candle.open);
        chartData.high.push(candle.high);
        chartData.low.push(candle.low);
        chartData.close.push(candle.close);
        chartData.volume.push(candle.volume);

        // Update price display
        if (currentPriceEl) {
            const lastPrice = chartData.close[chartData.close.length - 1];
            currentPriceEl.textContent = `$${lastPrice.toFixed(2)}`;
        }

        // Update current price line
        updateCurrentPriceLine();

        // Re-render chart to show new candle
        renderChart();
        await updateChartDisplay();
        return;
    }

    // Check if this is the current candle (same timestamp)
    if (candleTime === lastTime) {
        // Update existing candle data
        chartData.high[lastIndex] = Math.max(chartData.high[lastIndex], candle.high);
        chartData.low[lastIndex] = Math.min(chartData.low[lastIndex], candle.low);
        chartData.close[lastIndex] = candle.close;
        chartData.volume[lastIndex] = candle.volume;

        // Update price display
        if (currentPriceEl) {
            const lastPrice = chartData.close[lastIndex];
            currentPriceEl.textContent = `$${lastPrice.toFixed(2)}`;
        }

        // Update current price line
        updateCurrentPriceLine();

        // Ensure we're using the current scales (they should be set in renderChart)
        // Use baseXScale and baseYScale directly since we're not using zoom transforms
        if (!baseXScale || !baseYScale) {
            console.warn('Scales not initialized, skipping candlestick update');
            return;
        }

        // Update only the last candlestick (much faster than full render)
        if (candlestickContainer) {
            // Find the candlestick by timestamp match, not by index
            const targetTimestamp = chartData.x[lastIndex].getTime();
            const lastCandle = candlestickContainer.selectAll('.candlestick')
                .filter(function (d) {
                    return d && d.timestamp && d.timestamp.getTime() === targetTimestamp;
                });

            if (!lastCandle.empty()) {
                const d = {
                    timestamp: chartData.x[lastIndex],
                    open: chartData.open[lastIndex],
                    high: chartData.high[lastIndex],
                    low: chartData.low[lastIndex],
                    close: chartData.close[lastIndex]
                };

                // Use baseXScale and baseYScale directly (they are the current working scales)
                const xPos = baseXScale(d.timestamp);
                const openY = baseYScale(d.open);
                const closeY = baseYScale(d.close);
                const highY = baseYScale(d.high);
                const lowY = baseYScale(d.low);

                lastCandle.attr('transform', `translate(${xPos},0)`);
                lastCandle.select('.wick-top')
                    .attr('y1', baseYScale(Math.max(d.open, d.close)))
                    .attr('y2', highY);
                lastCandle.select('.wick-bottom')
                    .attr('y1', baseYScale(Math.min(d.open, d.close)))
                    .attr('y2', lowY);
                lastCandle.select('.body')
                    .attr('y', baseYScale(Math.max(d.open, d.close)))
                    .attr('height', Math.abs(closeY - openY) || 1)
                    .attr('fill', d.close >= d.open ? '#10b981' : '#ef4444')
                    .attr('stroke', d.close >= d.open ? '#10b981' : '#ef4444');
            } else {
                // Candlestick not found in DOM (may be virtualized or not yet rendered)
                // Silently trigger a re-render on next frame
                if (!window._chartRenderPending) {
                    window._chartRenderPending = true;
                    requestAnimationFrame(() => {
                        window._chartRenderPending = false;
                        renderChart();
                    });
                }
            }
        }

        // Update y-scale if price moved outside current domain
        const currentYDomain = baseYScale.domain();
        if (candle.high > currentYDomain[1] || candle.low < currentYDomain[0]) {
            const data = chartData.x.map((timestamp, i) => ({
                timestamp,
                low: chartData.low[i],
                high: chartData.high[i]
            }));
            const minPrice = d3.min(data, d => d.low);
            const maxPrice = d3.max(data, d => d.high);
            const priceRange = maxPrice - minPrice;
            const padding = priceRange * 0.02;

            baseYScale.domain([
                Math.max(0, minPrice - padding),
                maxPrice + padding
            ]);

            // Update working scales
            xScale = baseXScale;
            yScale = baseYScale;

            // Update axes and grid
            updateAxesAndGrid();

            // Re-render the last candlestick with new scale
            if (candlestickContainer) {
                // Find the candlestick by timestamp match, not by index
                const targetTimestamp = chartData.x[lastIndex].getTime();
                const lastCandle = candlestickContainer.selectAll('.candlestick')
                    .filter(function (d) {
                        return d && d.timestamp && d.timestamp.getTime() === targetTimestamp;
                    });

                if (!lastCandle.empty()) {
                    const d = {
                        timestamp: chartData.x[lastIndex],
                        open: chartData.open[lastIndex],
                        high: chartData.high[lastIndex],
                        low: chartData.low[lastIndex],
                        close: chartData.close[lastIndex]
                    };

                    const xPos = baseXScale(d.timestamp);
                    const openY = baseYScale(d.open);
                    const closeY = baseYScale(d.close);
                    const highY = baseYScale(d.high);
                    const lowY = baseYScale(d.low);

                    lastCandle.attr('transform', `translate(${xPos},0)`);
                    lastCandle.select('.wick-top')
                        .attr('y1', baseYScale(Math.max(d.open, d.close)))
                        .attr('y2', highY);
                    lastCandle.select('.wick-bottom')
                        .attr('y1', baseYScale(Math.min(d.open, d.close)))
                        .attr('y2', lowY);
                    lastCandle.select('.body')
                        .attr('y', baseYScale(Math.max(d.open, d.close)))
                        .attr('height', Math.abs(closeY - openY) || 1)
                        .attr('fill', d.close >= d.open ? '#10b981' : '#ef4444')
                        .attr('stroke', d.close >= d.open ? '#10b981' : '#ef4444');
                }
            }
        }
    }
    // If timestamp is older, ignore it (shouldn't happen in normal operation)
}

/**
 * Toggle update (start/stop)
 */
async function toggleUpdate() {
    if (isRunning) {
        stopUpdate();
    } else {
        await startUpdate();
    }
}

/**
 * Start real-time updates
 */
async function startUpdate() {
    if (isRunning) return;

    isRunning = true;
    if (statusEl) {
        if (statusEl) {
            statusEl.textContent = 'Starting...';
            statusEl.className = 'status running';
        }
    }

    initializeWebSocket();
}

/**
 * Stop real-time updates
 */
function stopUpdate() {
    if (!isRunning) return;

    isRunning = false;
    if (statusEl) {
        statusEl.textContent = 'Stopped';
        statusEl.className = 'status stopped';
    }

    // Clear any pending reconnection attempts
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }

    // Clear health check interval
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
        healthCheckInterval = null;
    }

    if (websocket) {
        // Remove all event handlers to prevent errors during close
        websocket.onopen = null;
        websocket.onmessage = null;
        websocket.onerror = null;
        websocket.onclose = null;

        // Only close if WebSocket is in a state that can be closed
        // 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED
        if (websocket.readyState === WebSocket.CONNECTING || websocket.readyState === WebSocket.OPEN) {
            try {
                websocket.close();
            } catch (error) {
                // Ignore errors when closing (connection might already be closed)
                console.log('WebSocket close error (ignored):', error);
            }
        }

        websocket = null;
    }

    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
}

/**
 * Reset chart
 */
async function resetChart() {
    stopUpdate();
    chartData = {
        x: [],
        open: [],
        high: [],
        low: [],
        close: [],
        volume: []
    };
    detectedSwings = [];

    // Main chart zoom reset removed - zoom functionality disabled

    await loadHistoricalData();
}

// Placeholder functions for algorithm detection (to be implemented)
async function detectAndDrawSwings(overlay) {
    // Handle macro swings using universal structure swing scanner
    // Macro swings use swing points from the next higher timeframe
    if (renderStates.macroSwings) {
        if (typeof detectSwingStructure !== 'function') {
            console.error('Universal swing detection API not loaded.');
        } else {
            try {
                // Get the higher timeframe for macro swings
                const macroTimeframe = getMacroSwingTimeframe(currentTimeframe);

                if (!macroTimeframe) {
                    console.warn(`No higher timeframe available for macro swings on ${currentTimeframe}`);
                    return;
                }

                // Fetch data for the higher timeframe
                const macroInterval = timeframeMap[macroTimeframe] || macroTimeframe;
                const higherTFCandles = await fetchHistoricalData(currentSymbol, macroInterval, 5000);

                if (!higherTFCandles || higherTFCandles.length === 0) {
                    console.warn(`No data available for higher timeframe ${macroTimeframe}`);
                    return;
                }

                // Convert to chart data format
                const macroChartData = {
                    x: higherTFCandles.map(c => c.timestamp),
                    open: higherTFCandles.map(c => c.open),
                    high: higherTFCandles.map(c => c.high),
                    low: higherTFCandles.map(c => c.low),
                    close: higherTFCandles.map(c => c.close),
                    volume: higherTFCandles.map(c => c.volume)
                };

                // Detect macro swings using universal structure on higher timeframe data
                const macroSwings = await detectSwingStructure(
                    macroChartData,
                    macroTimeframe,
                    false, // Not a higher TF from the macro TF's perspective
                    swingSensitivity
                );

                // Render macro swings using standard swing renderer if available
                if (macroSwings.length > 0) {
                    if (typeof renderSwingsD3 === 'function') {
                        renderSwingsD3(macroSwings, overlay, xScale, yScale, {
                            showLabels: true,
                            showBOS: true,
                            showCHOCH: true,
                            showLines: true,
                            chartData: chartData
                        });
                    }
                }
            } catch (error) {
                console.error('Error in macro swing detection:', error);
            }
        }
    }

    // Micro swing detection removed (no longer used)

    // Handle regular swings using original scanner
    if (renderStates.swings) {
        if (typeof detectSwingStructure !== 'function' && typeof evaluateSwingsWithQuality !== 'function') {
            //console.error('Swing detection API not loaded.');
            return;
        }

        const isHigherTF = currentTimeframe === '4h' || currentTimeframe === '1d';

        try {
            if (typeof evaluateSwingsWithQuality === 'function') {
                detectedSwings = await evaluateSwingsWithQuality(
                    chartData,
                    currentTimeframe,
                    isHigherTF,
                    swingSensitivity
                );
            } else {
                detectedSwings = await detectSwingStructure(
                    chartData,
                    currentTimeframe,
                    isHigherTF,
                    swingSensitivity
                );
            }
        } catch (error) {
            //console.error('Error in swing detection:', error);
            return;
        }

        if (detectedSwings.length === 0) return;

        // Log external/internal classification
        const external = detectedSwings.filter(s => s.swing_class === 'external');
        const internal = detectedSwings.filter(s => s.swing_class === 'internal');
        const externalHighs = external.filter(s => s.type === 'high').length;
        const externalLows = external.filter(s => s.type === 'low').length;
        const internalHighs = internal.filter(s => s.type === 'high').length;
        const internalLows = internal.filter(s => s.type === 'low').length;
        //console.log(`📊 Regular swings detected: ${detectedSwings.length} total`);
        //console.log(`   🔵 External: ${externalHighs} highs, ${externalLows} lows`);
        //console.log(`   🟢 Internal: ${internalHighs} highs, ${internalLows} lows`);

        if (typeof renderSwingsD3 === 'function') {
            renderSwingsD3(detectedSwings, overlay, xScale, yScale, {
                showLabels: true,
                showBOS: true,
                showCHOCH: true,
                showLines: true,
                showQualityScores: true,
                chartData: chartData
            });
        }
    }
}

/**
 * Detect and draw volatility indicators
 * LEGACY: calculateVolatility API was removed - this is now a no-op stub
 */
async function detectAndDrawVolatility(overlay) {
    // Legacy volatility API was removed - no-op
    return;
}

/**
 * Detect and draw momentum indicators
 * LEGACY: calculateMomentum API was removed - this is now a no-op stub
 */
async function detectAndDrawMomentum(overlay) {
    // Legacy momentum API was removed - no-op
    return;
}

async function detectAndDrawVolume(overlay) {
    if (!renderStates.volume) return;

    if (!chartData || chartData.close.length < 2 || !chartData.volume) return;

    try {
        // Render volume bars for all candles (similar to Pine Script volume indicator)
        // Pass null for volumeData to indicate we want all candles rendered
        if (typeof renderVolumeD3 === 'function') {
            renderVolumeD3(null, chartData, overlay, xScale, yScale, {
                showLabels: false // No labels by default, just bars
            });
        }
    } catch (error) {
        console.error('Error in volume rendering:', error);
    }
}

/**
 * Detect and draw EMA indicators
 * LEGACY: calculateEMA API was removed - this is now a no-op stub
 */
async function detectAndDrawEMAs(overlay) {
    // Legacy EMA API was removed - no-op
    return;
}

/**
 * Detect and draw consolidation zones
 * LEGACY: calculateConsolidationZones API was removed - this is now a no-op stub
 */
async function detectAndDrawConsolidation(overlay) {
    // Legacy consolidation zones API was removed - no-op
    return;
}

// Initialize chart controls when DOM is ready.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Set timeframeSelect to saved value
        if (timeframeSelect) {
            timeframeSelect.value = currentTimeframe;
        }
        window.ProfileMenu?.init();
        initializeLayersToggle();
    });
} else {
    // DOM already loaded
    // Set timeframeSelect to saved value
    if (timeframeSelect) {
        timeframeSelect.value = currentTimeframe;
    }
    window.ProfileMenu?.init();
    initializeLayersToggle();
}

// Handle window resize events
let resizeTimeout;
window.addEventListener('resize', () => {
    // Debounce resize events to avoid excessive re-renders
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        if (chartData && chartData.x && chartData.x.length > 0) {
            // Update dimensions first, then re-render if dimensions changed
            if (updateChartDimensions()) {
                console.log('📐 Window resized, re-rendering chart...');
                renderChart();
            }
        }
    }, 150); // Wait 150ms after resize stops
});

/**
 * Initialize drawing layers toggle menu
 */
function initializeLayersToggle() {
    const toggleBtn = document.getElementById('layersToggle');
    const menu = document.getElementById('layersMenu');

    if (!toggleBtn || !menu) return;

    // Toggle menu on button click
    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        menu.classList.toggle('show');

        // Close other dropdowns
        document.querySelectorAll('.dropdown-menu.show').forEach(m => {
            if (m !== menu) m.classList.remove('show');
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!menu.contains(e.target) && !toggleBtn.contains(e.target)) {
            menu.classList.remove('show');
        }
    });

    // Core Engine layers
    const coreLayers = [
        'core-swings',      // Swing points with zig-zag
        'core-structure',   // BOS/CHoCH events
        'core-levels',      // Protected levels
        'core-moves',       // Directional move backgrounds
        'core-zones',       // Drawing zones
        'core-sr_zones',    // S/R zones
        'core-fvgs',        // Fair Value Gaps
        'core-liquidity'    // Liquidity pools
    ];

    // Core Layer toggle handlers
    coreLayers.forEach(layer => {
        const checkbox = document.getElementById(`layer-${layer}`);
        if (checkbox) {
            checkbox.addEventListener('change', async () => {
                const layerName = layer.replace('core-', '');
                await toggleCoreLayer(layerName, checkbox.checked);
                console.log(`🔧 Core ${layerName} layer ${checkbox.checked ? 'shown' : 'hidden'}`);
            });
        }
    });

    // Show All button - shows all layers
    const showAllBtn = document.getElementById('layersShowAll');
    if (showAllBtn) {
        showAllBtn.addEventListener('click', async () => {
            // Show Core layers
            for (const layer of coreLayers) {
                const checkbox = document.getElementById(`layer-${layer}`);
                if (checkbox) {
                    checkbox.checked = true;
                    const layerName = layer.replace('core-', '');
                    await toggleCoreLayer(layerName, true);
                }
            }
            console.log('📐 All layers shown');
        });
    }

    // Hide All button - hides all layers
    const hideAllBtn = document.getElementById('layersHideAll');
    if (hideAllBtn) {
        hideAllBtn.addEventListener('click', async () => {
            // Hide Core layers
            for (const layer of coreLayers) {
                const checkbox = document.getElementById(`layer-${layer}`);
                if (checkbox) {
                    checkbox.checked = false;
                    const layerName = layer.replace('core-', '');
                    await toggleCoreLayer(layerName, false);
                }
            }
            console.log('📐 All layers hidden');
        });
    }

    // Sync initial checkbox states with CoreEngine visibility defaults
    if (typeof CoreEngine !== 'undefined' && CoreEngine.getVisibility) {
        const visibility = CoreEngine.getVisibility();
        coreLayers.forEach(layer => {
            const layerName = layer.replace('core-', '');
            const checkbox = document.getElementById(`layer-${layer}`);
            if (checkbox && visibility.hasOwnProperty(layerName)) {
                checkbox.checked = visibility[layerName];
            }
        });
    }

    console.log('✅ Layers toggle initialized');
}

/**
 * Toggle visibility of Core engine layers
 * Uses CoreEngine to toggle and render layers
 */
async function toggleCoreLayer(layerName, visible) {
    // Use CoreEngine if available (it handles data loading automatically now)
    if (typeof CoreEngine !== 'undefined' && CoreEngine.toggleLayer) {
        await CoreEngine.toggleLayer(layerName, visible);
    }

    // Map layer name to CSS class (handle underscores for hyphenated class names)
    const layerClass = layerName.replace('_', '-');
    const selector = `.core-layer-${layerClass}`;

    // Also toggle by selector for fallback
    const layers = document.querySelectorAll(selector);
    layers.forEach(layer => {
        layer.style.display = visible ? '' : 'none';
    });

    // Also check for D3 groups in the main chart
    if (typeof d3 !== 'undefined' && typeof g !== 'undefined') {
        const gSelection = g.select ? g : d3.select(g);
        gSelection.selectAll(selector).style('display', visible ? null : 'none');
    }
}

// Expose toggleCoreLayer globally
if (typeof window !== 'undefined') {
    window.toggleCoreLayer = toggleCoreLayer;
}
