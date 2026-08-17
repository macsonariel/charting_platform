/**
 * Chart Interval Bar
 * Provides zoom range selector (1D, 5D, 1M, etc.) and timezone selector
 */

const ChartIntervalBar = (function () {
    'use strict';

    // Interval configurations: { label, days, timeframe, candlesNeeded }
    // candlesNeeded = approximate number of candles to fit in viewport
    const INTERVALS = {
        '1D': { days: 1, timeframe: '1m', label: '1D', candlesPerDay: 1440 },      // 1 day = 1440 1-min candles
        '5D': { days: 5, timeframe: '5m', label: '5D', candlesPerDay: 288 },        // 5 days = 1440 5-min candles
        '1M': { days: 30, timeframe: '30m', label: '1M', candlesPerDay: 48 },       // 30 days = 1440 30-min candles
        '3M': { days: 90, timeframe: '1h', label: '3M', candlesPerDay: 24 },        // 90 days = 2160 1-hour candles
        '6M': { days: 180, timeframe: '4h', label: '6M', candlesPerDay: 6 },        // 180 days = 1080 4-hour candles
        'YTD': { days: 'ytd', timeframe: '1d', label: 'YTD', candlesPerDay: 1 },    // YTD = ~365 daily candles
        '1Y': { days: 365, timeframe: '1d', label: '1Y', candlesPerDay: 1 },        // 1 year = 365 daily candles
        '5Y': { days: 1825, timeframe: '1w', label: '5Y', candlesPerDay: 0.143 },   // 5 years = ~260 weekly candles
        'All': { days: 'all', timeframe: '1w', label: 'All', candlesPerDay: 0.143 }
    };

    // Common timezones with UTC offset
    const TIMEZONES = [
        { value: 'UTC', label: '(UTC+0) UTC', offset: 0 },
        { value: 'Europe/London', label: '(UTC+0) London', offset: 0 },
        { value: 'Europe/Paris', label: '(UTC+1) Paris', offset: 1 },
        { value: 'Europe/Berlin', label: '(UTC+1) Berlin', offset: 1 },
        { value: 'Africa/Johannesburg', label: '(UTC+2) Johannesburg', offset: 2 },
        { value: 'Europe/Moscow', label: '(UTC+3) Moscow', offset: 3 },
        { value: 'Asia/Dubai', label: '(UTC+4) Dubai', offset: 4 },
        { value: 'Asia/Karachi', label: '(UTC+5) Karachi', offset: 5 },
        { value: 'Asia/Kolkata', label: '(UTC+5:30) Mumbai', offset: 5.5 },
        { value: 'Asia/Bangkok', label: '(UTC+7) Bangkok', offset: 7 },
        { value: 'Asia/Hong_Kong', label: '(UTC+8) Hong Kong', offset: 8 },
        { value: 'Asia/Singapore', label: '(UTC+8) Singapore', offset: 8 },
        { value: 'Asia/Tokyo', label: '(UTC+9) Tokyo', offset: 9 },
        { value: 'Australia/Sydney', label: '(UTC+10) Sydney', offset: 10 },
        { value: 'Pacific/Auckland', label: '(UTC+12) Auckland', offset: 12 },
        { value: 'Pacific/Honolulu', label: '(UTC-10) Honolulu', offset: -10 },
        { value: 'America/Anchorage', label: '(UTC-9) Anchorage', offset: -9 },
        { value: 'America/Los_Angeles', label: '(UTC-8) Los Angeles', offset: -8 },
        { value: 'America/Denver', label: '(UTC-7) Denver', offset: -7 },
        { value: 'America/Chicago', label: '(UTC-6) Chicago', offset: -6 },
        { value: 'America/New_York', label: '(UTC-5) New York', offset: -5 },
        { value: 'America/Sao_Paulo', label: '(UTC-3) São Paulo', offset: -3 }
    ];

    let _bar = null;
    let _currentInterval = '1M';
    let _currentTimezone = 'UTC';
    let _timeUpdateInterval = null;

    /**
     * Initialize the interval bar
     */
    function init() {
        // Find existing bar in HTML (may be in a dynamically loaded fragment)
        _bar = document.querySelector('.chart-interval-bar');

        if (!_bar) {
            console.warn('⚠️ ChartIntervalBar: .chart-interval-bar not found, will retry...');
            // Retry after a delay since fragments load asynchronously
            setTimeout(init, 1000);
            return;
        }

        // Update timezone dropdown options with UTC format
        _updateTimezoneOptions();

        // Load and apply saved preferences
        _loadPreferences();
        _applyPreferences();

        // Attach event listeners
        _attachEventListeners();

        // Start time update
        _startTimeUpdate();

        // Listen for interval change events from other sources
        document.addEventListener('intervalChanged', _handleExternalIntervalChange);

        console.log('📊 ChartIntervalBar initialized');
    }

    /**
     * Ensure bar is initialized before use
     */
    function _ensureBarReady() {
        if (!_bar) {
            _bar = document.querySelector('.chart-interval-bar');
        }
        return !!_bar;
    }

    /**
     * Update timezone dropdown with UTC offset format
     */
    function _updateTimezoneOptions() {
        const select = _bar.querySelector('#timezoneSelect');
        if (!select) return;

        // Sort by offset, then by name
        const sortedTimezones = [...TIMEZONES].sort((a, b) => {
            if (a.offset !== b.offset) return a.offset - b.offset;
            return a.label.localeCompare(b.label);
        });

        select.innerHTML = sortedTimezones.map(tz =>
            `<option value="${tz.value}">${tz.label}</option>`
        ).join('');
    }

    /**
     * Apply saved preferences to the UI
     */
    function _applyPreferences() {
        // Apply active interval
        const intervalBtns = _bar.querySelectorAll('.interval-btn');
        intervalBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.interval === _currentInterval) {
                btn.classList.add('active');
            }
        });

        // Apply timezone
        const timezoneSelect = _bar.querySelector('#timezoneSelect');
        if (timezoneSelect) {
            timezoneSelect.value = _currentTimezone;
        }
    }

    /**
     * Attach event listeners
     */
    function _attachEventListeners() {
        // Interval buttons
        const intervalBtns = _bar.querySelectorAll('.interval-btn');
        intervalBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const interval = e.target.dataset.interval;
                _selectInterval(interval);
            });
        });

        // Timezone select
        const timezoneSelect = _bar.querySelector('#timezoneSelect');
        if (timezoneSelect) {
            timezoneSelect.addEventListener('change', (e) => {
                _changeTimezone(e.target.value);
            });
        }
    }

    /**
     * Select an interval and zoom chart to show that time range
     */
    function _selectInterval(interval) {
        if (!INTERVALS[interval]) return;

        // Ensure bar is ready
        if (!_ensureBarReady()) {
            console.warn('ChartIntervalBar: bar not ready for interval selection');
            return;
        }

        // Update active button
        const intervalBtns = _bar.querySelectorAll('.interval-btn');
        intervalBtns.forEach(btn => btn.classList.remove('active'));
        const activeBtn = _bar.querySelector(`[data-interval="${interval}"]`);
        if (activeBtn) activeBtn.classList.add('active');

        _currentInterval = interval;
        _savePreferences();

        const config = INTERVALS[interval];

        // Calculate the time range to display
        const now = new Date();
        let startDate, endDate = new Date(now.getTime() + 3600000); // Add 1 hour buffer on right

        if (config.days === 'ytd') {
            startDate = new Date(now.getFullYear(), 0, 1);
        } else if (config.days === 'all') {
            startDate = new Date(2015, 0, 1); // Far back date
        } else {
            startDate = new Date(now.getTime() - (config.days * 24 * 60 * 60 * 1000));
        }

        // First, switch to the appropriate timeframe if available
        if (typeof window.switchTimeframe === 'function') {
            // This will trigger data fetch and chart re-render
            window.switchTimeframe(config.timeframe);

            // After timeframe switch, zoom to the correct range
            // Use a short delay to allow the chart to update
            setTimeout(() => {
                _zoomChartToRange(startDate, endDate, config.days);
            }, 500);
        } else {
            // Can't switch timeframe, just zoom the existing chart
            _zoomChartToRange(startDate, endDate, config.days);
        }

        // Log for debugging
        console.log(`📊 Interval changed to ${interval}: ${config.days} days @ ${config.timeframe}`);

        // Show toast notification
        if (typeof window.showToast === 'function') {
            window.showToast(`Chart: ${config.label} (${config.timeframe} candles)`, 'info');
        }
    }

    /**
     * Zoom chart to show the specified time range
     */
    function _zoomChartToRange(startDate, endDate, days) {
        // Access chart scales and data
        const baseXScale = window.baseXScale;
        const xScale = window.xScale;
        const chartData = window.chartData;

        if (!baseXScale || !xScale || !chartData || !chartData.x || chartData.x.length === 0) {
            console.warn('Chart scales or data not available for zoom');
            return;
        }

        // Get the data time range
        const dataStartTime = chartData.x[0].getTime();
        const dataEndTime = chartData.x[chartData.x.length - 1].getTime();

        // Clamp the requested range to available data
        let clampedStart = Math.max(startDate.getTime(), dataStartTime);
        let clampedEnd = Math.min(endDate.getTime(), dataEndTime);

        // If the range is inverted or too small, show the most recent data that fits
        if (clampedStart >= clampedEnd) {
            // Show as much data as we have, or the requested range from the end
            const requestedRange = endDate.getTime() - startDate.getTime();
            const availableRange = dataEndTime - dataStartTime;
            const rangeToShow = Math.min(requestedRange, availableRange);

            clampedEnd = dataEndTime + (rangeToShow * 0.1); // Add 10% right buffer
            clampedStart = dataEndTime - (rangeToShow * 0.9);
        } else {
            // Add 10% buffer on the right
            const range = clampedEnd - clampedStart;
            clampedEnd += range * 0.1;
        }

        // Update xScale domain (this controls what's visible)
        xScale.domain([
            new Date(clampedStart),
            new Date(clampedEnd)
        ]);

        // Also update baseXScale if we're using it directly
        if (baseXScale !== xScale) {
            baseXScale.domain([
                new Date(clampedStart),
                new Date(clampedEnd)
            ]);
        }

        // Trigger chart redraw
        if (typeof window.updateYAxisFromVisibleCandles === 'function') {
            const data = chartData.x.map((timestamp, i) => ({
                timestamp,
                open: chartData.open[i],
                high: chartData.high[i],
                low: chartData.low[i],
                close: chartData.close[i],
                volume: chartData.volume[i]
            }));
            window.updateYAxisFromVisibleCandles(data);
        }

        // Trigger the chart update functions
        if (typeof window.updateAxesAndGrid === 'function') {
            window.updateAxesAndGrid();
        }
        if (typeof window.updateCandlesticks === 'function') {
            window.updateCandlesticks();
        }
        if (typeof window.updateChartDisplayImmediate === 'function') {
            window.updateChartDisplayImmediate();
        }

        console.log(`📊 Zoomed chart to show ${days} days (${new Date(clampedStart).toLocaleDateString()} - ${new Date(clampedEnd).toLocaleDateString()})`);
    }

    /**
     * Handle interval change from external source
     */
    function _handleExternalIntervalChange(e) {
        // Just update button state, don't trigger zoom again
        if (e.detail && e.detail.interval) {
            const intervalBtns = _bar.querySelectorAll('.interval-btn');
            intervalBtns.forEach(btn => {
                btn.classList.remove('active');
                if (btn.dataset.interval === e.detail.interval) {
                    btn.classList.add('active');
                }
            });
        }
    }

    /**
     * Change timezone
     */
    function _changeTimezone(timezone) {
        _currentTimezone = timezone;
        _savePreferences();

        // Update time display immediately
        _updateTimeDisplay();

        // Dispatch event for chart x-axis labels
        const event = new CustomEvent('timezoneChanged', {
            detail: { timezone }
        });
        document.dispatchEvent(event);

        console.log(`🕐 Timezone changed to ${timezone}`);

        if (typeof window.showToast === 'function') {
            const tz = TIMEZONES.find(t => t.value === timezone);
            window.showToast(`Timezone: ${tz ? tz.label : timezone}`, 'info');
        }
    }

    /**
     * Start time update interval
     */
    function _startTimeUpdate() {
        _updateTimeDisplay();
        _timeUpdateInterval = setInterval(_updateTimeDisplay, 1000);
    }

    /**
     * Update the current time display
     */
    function _updateTimeDisplay() {
        const timeDisplay = document.getElementById('currentTimeDisplay');
        if (!timeDisplay) return;

        try {
            const now = new Date();
            const options = {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false,
                timeZone: _currentTimezone
            };
            timeDisplay.textContent = now.toLocaleTimeString('en-US', options);
        } catch (e) {
            timeDisplay.textContent = '--:--';
        }
    }

    /**
     * Save preferences to localStorage
     */
    function _savePreferences() {
        try {
            localStorage.setItem('chartIntervalBar', JSON.stringify({
                interval: _currentInterval,
                timezone: _currentTimezone
            }));
        } catch (e) {
            console.warn('Could not save interval bar preferences');
        }
    }

    /**
     * Load preferences from localStorage
     */
    function _loadPreferences() {
        try {
            const saved = localStorage.getItem('chartIntervalBar');
            if (saved) {
                const prefs = JSON.parse(saved);
                _currentInterval = prefs.interval || '1M';
                _currentTimezone = prefs.timezone || 'UTC';
            }
        } catch (e) {
            console.warn('Could not load interval bar preferences');
        }
    }

    /**
     * Get current interval
     */
    function getCurrentInterval() {
        return _currentInterval;
    }

    /**
     * Get current timezone
     */
    function getCurrentTimezone() {
        return _currentTimezone;
    }

    /**
     * Set interval programmatically
     */
    function setInterval(interval) {
        if (INTERVALS[interval]) {
            _selectInterval(interval);
        }
    }

    /**
     * Set timezone programmatically
     */
    function setTimezone(timezone) {
        const select = document.getElementById('timezoneSelect');
        if (select) {
            select.value = timezone;
            _changeTimezone(timezone);
        }
    }

    /**
     * Destroy the interval bar
     */
    function destroy() {
        if (_timeUpdateInterval) {
            clearInterval(_timeUpdateInterval);
        }
        document.removeEventListener('intervalChanged', _handleExternalIntervalChange);
    }

    // Public API
    return {
        init,
        destroy,
        getCurrentInterval,
        getCurrentTimezone,
        setInterval,
        setTimezone
    };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Delay to ensure chart is loaded first
    setTimeout(() => {
        ChartIntervalBar.init();
    }, 800);
});

// Also expose globally
window.ChartIntervalBar = ChartIntervalBar;
