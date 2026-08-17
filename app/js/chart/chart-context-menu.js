/**
 * Chart Context Menu
 * 
 * Right-click context menu for chart interactions including:
 * - Setting alerts at clicked price
 * - Changing candle appearance/colors
 * - Switching timeframes
 * - Toggling indicator visibility
 * - View controls (reset zoom, screenshot)
 */

const ChartContextMenu = {
    // State
    _menu: null,
    _clickPosition: { x: 0, y: 0 },
    _clickPrice: null,
    _isVisible: false,
    _chartSvg: null,
    _yScale: null,

    // Candle color schemes
    _colorSchemes: {
        classic: { bullish: '#22c55e', bearish: '#ef4444', name: 'Classic' },
        teal: { bullish: '#14b8a6', bearish: '#a855f7', name: 'Teal/Purple' },
        blue: { bullish: '#3b82f6', bearish: '#f97316', name: 'Blue/Orange' },
        mono: { bullish: '#e2e8f0', bearish: '#475569', name: 'Monochrome' }
    },
    _currentScheme: 'classic',

    /**
     * Initialize the context menu
     * @param {SVGElement} chartSvg - The chart SVG element
     * @param {Function} yScale - D3 y-scale function for price conversion
     */
    init(chartSvg, yScale) {
        this._chartSvg = chartSvg;
        this._yScale = yScale;

        // Load saved color scheme
        const saved = localStorage.getItem('chartColorScheme');
        if (saved && this._colorSchemes[saved]) {
            this._currentScheme = saved;
        }

        // Create menu DOM
        this._createMenu();

        // Bind events
        this._bindEvents();

        console.log('📋 ChartContextMenu initialized');
    },

    /**
     * Update the y-scale reference (call when scale changes)
     */
    updateScale(yScale) {
        this._yScale = yScale;
    },

    /**
     * Create the context menu DOM structure
     */
    _createMenu() {
        // Remove existing if any
        const existing = document.getElementById('chartContextMenu');
        if (existing) existing.remove();

        const menu = document.createElement('div');
        menu.id = 'chartContextMenu';
        menu.className = 'chart-context-menu';
        menu.innerHTML = this._getMenuHTML();

        document.body.appendChild(menu);
        this._menu = menu;

        // Bind menu item clicks
        this._bindMenuActions();
    },

    /**
     * Generate the menu HTML
     */
    _getMenuHTML() {
        const indicators = this._getIndicatorStates();
        const currentTf = window.currentTimeframe || '1h';

        return `
            <!-- Alert Section -->
            <div class="ccm-section">
                <div class="ccm-item" data-action="set-alert">
                    <span class="ccm-icon">🔔</span>
                    <span class="ccm-label">Set Alert at</span>
                    <span class="ccm-alert-price" id="ccmAlertPrice">--</span>
                </div>
            </div>

            <!-- Appearance Section -->
            <div class="ccm-section">
                <div class="ccm-section-header">Appearance</div>
                <div class="ccm-color-options">
                    <div class="ccm-color-swatch classic ${this._currentScheme === 'classic' ? 'active' : ''}" 
                         data-action="set-color" data-scheme="classic" title="Classic (Green/Red)"></div>
                    <div class="ccm-color-swatch teal-purple ${this._currentScheme === 'teal' ? 'active' : ''}" 
                         data-action="set-color" data-scheme="teal" title="Teal/Purple"></div>
                    <div class="ccm-color-swatch blue-orange ${this._currentScheme === 'blue' ? 'active' : ''}" 
                         data-action="set-color" data-scheme="blue" title="Blue/Orange"></div>
                    <div class="ccm-color-swatch mono ${this._currentScheme === 'mono' ? 'active' : ''}" 
                         data-action="set-color" data-scheme="mono" title="Monochrome"></div>
                </div>
            </div>

            <!-- Timeframe Section -->
            <div class="ccm-section">
                <div class="ccm-section-header">Timeframe</div>
                <div class="ccm-timeframe-grid">
                    <div class="ccm-tf-btn ${currentTf === '1m' ? 'active' : ''}" data-action="set-tf" data-tf="1m">1m</div>
                    <div class="ccm-tf-btn ${currentTf === '5m' ? 'active' : ''}" data-action="set-tf" data-tf="5m">5m</div>
                    <div class="ccm-tf-btn ${currentTf === '15m' ? 'active' : ''}" data-action="set-tf" data-tf="15m">15m</div>
                    <div class="ccm-tf-btn ${currentTf === '1h' ? 'active' : ''}" data-action="set-tf" data-tf="1h">1H</div>
                    <div class="ccm-tf-btn ${currentTf === '4h' ? 'active' : ''}" data-action="set-tf" data-tf="4h">4H</div>
                    <div class="ccm-tf-btn ${currentTf === '1d' ? 'active' : ''}" data-action="set-tf" data-tf="1d">1D</div>
                </div>
            </div>

            <!-- Indicators Section -->
            <div class="ccm-section">
                <div class="ccm-section-header">Indicators</div>
                ${indicators.map(ind => `
                    <div class="ccm-item toggle ${ind.active ? 'active' : ''}" data-action="toggle-indicator" data-indicator="${ind.key}">
                        <span class="ccm-toggle-indicator">✓</span>
                        <span class="ccm-label">${ind.name}</span>
                    </div>
                `).join('')}
            </div>

            <!-- View Section -->
            <div class="ccm-section">
                <div class="ccm-item" data-action="reset-zoom">
                    <span class="ccm-icon">🔍</span>
                    <span class="ccm-label">Reset Zoom</span>
                </div>
                <div class="ccm-item" data-action="screenshot">
                    <span class="ccm-icon">📷</span>
                    <span class="ccm-label">Screenshot Chart</span>
                </div>
            </div>
        `;
    },

    /**
     * Get indicator states from global renderStates
     */
    _getIndicatorStates() {
        const states = window.renderStates || {};
        return [
            { key: 'emas', name: 'EMAs', active: states.emas !== false },
            { key: 'volume', name: 'Volume', active: states.volume !== false }
        ];
    },

    /**
     * Bind event listeners
     */
    _bindEvents() {
        // Right-click on chart
        if (this._chartSvg) {
            this._chartSvg.addEventListener('contextmenu', (e) => this._onContextMenu(e));
        }

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (this._isVisible && !this._menu.contains(e.target)) {
                this.hide();
            }
        });

        // ESC to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this._isVisible) {
                this.hide();
            }
        });

        // Scroll to close
        document.addEventListener('scroll', () => {
            if (this._isVisible) this.hide();
        }, true);
    },

    /**
     * Bind click handlers for menu items
     */
    _bindMenuActions() {
        this._menu.querySelectorAll('[data-action]').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this._handleAction(item.dataset.action, item.dataset);
            });
        });
    },

    /**
     * Handle context menu event
     */
    _onContextMenu(e) {
        e.preventDefault();

        this._clickPosition = { x: e.clientX, y: e.clientY };

        // Calculate price at click position if we have yScale
        if (this._yScale) {
            try {
                const chartRect = this._chartSvg.getBoundingClientRect();
                const relativeY = e.clientY - chartRect.top;
                this._clickPrice = this._yScale.invert(relativeY);
            } catch (err) {
                this._clickPrice = null;
            }
        }

        this.show(e.clientX, e.clientY);
    },

    /**
     * Show the context menu at position
     */
    show(x, y) {
        // Update menu content
        this._menu.innerHTML = this._getMenuHTML();
        this._bindMenuActions();

        // Update price display
        const priceEl = this._menu.querySelector('#ccmAlertPrice');
        if (priceEl && this._clickPrice !== null) {
            priceEl.textContent = '$' + this._clickPrice.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }

        // Position menu
        const menuRect = this._menu.getBoundingClientRect();
        const padding = 8;

        // Adjust if near viewport edges
        let finalX = x;
        let finalY = y;
        let flipX = false;
        let flipY = false;

        if (x + menuRect.width + padding > window.innerWidth) {
            finalX = x - menuRect.width;
            flipX = true;
        }

        if (y + menuRect.height + padding > window.innerHeight) {
            finalY = y - menuRect.height;
            flipY = true;
        }

        this._menu.style.left = `${Math.max(padding, finalX)}px`;
        this._menu.style.top = `${Math.max(padding, finalY)}px`;
        this._menu.classList.toggle('flip-x', flipX);
        this._menu.classList.toggle('flip-y', flipY);

        // Show with animation
        requestAnimationFrame(() => {
            this._menu.classList.add('visible');
        });

        this._isVisible = true;
    },

    /**
     * Hide the context menu
     */
    hide() {
        this._menu.classList.remove('visible');
        this._isVisible = false;
    },

    /**
     * Handle menu actions
     */
    _handleAction(action, data) {
        switch (action) {
            case 'set-alert':
                this._setAlert();
                break;

            case 'set-color':
                this._setColorScheme(data.scheme);
                break;

            case 'set-tf':
                this._setTimeframe(data.tf);
                break;

            case 'toggle-indicator':
                this._toggleIndicator(data.indicator);
                break;

            case 'reset-zoom':
                this._resetZoom();
                break;

            case 'screenshot':
                this._takeScreenshot();
                break;

            default:
                console.warn('Unknown action:', action);
        }

        // Keep menu open for toggles, close for other actions
        if (action !== 'toggle-indicator' && action !== 'set-color') {
            this.hide();
        }
    },

    /**
     * Set alert at clicked price
     */
    _setAlert() {
        if (this._clickPrice === null) {
            console.warn('No price available for alert');
            return;
        }

        const priceStr = this._clickPrice.toFixed(2);

        // Check if AlertSystem exists
        if (typeof AlertSystem !== 'undefined' && AlertSystem.openNewAlertModal) {
            AlertSystem.openNewAlertModal({
                price: this._clickPrice,
                symbol: window.currentSymbol || 'BTCUSDT'
            });
        } else {
            // Fallback: show toast notification
            if (typeof showToast === 'function') {
                showToast(`Alert set at $${priceStr}`, 'success');
            } else {
                alert(`Alert would be set at $${priceStr}\n(Alert system not available)`);
            }
        }

        console.log(`🔔 Alert requested at price: ${priceStr}`);
    },

    /**
     * Set candle color scheme
     */
    _setColorScheme(scheme) {
        if (!this._colorSchemes[scheme]) return;

        this._currentScheme = scheme;
        localStorage.setItem('chartColorScheme', scheme);

        const colors = this._colorSchemes[scheme];

        // Update CSS custom properties
        document.documentElement.style.setProperty('--candle-bullish', colors.bullish);
        document.documentElement.style.setProperty('--candle-bearish', colors.bearish);

        // Dispatch event for chart to update
        window.dispatchEvent(new CustomEvent('chart-color-change', {
            detail: colors
        }));

        // Update active state in menu
        this._menu.querySelectorAll('.ccm-color-swatch').forEach(swatch => {
            swatch.classList.toggle('active', swatch.dataset.scheme === scheme);
        });

        console.log(`🎨 Color scheme changed to: ${colors.name}`);
    },

    /**
     * Set timeframe
     */
    _setTimeframe(tf) {
        // Use global timeframe selector if available
        const tfSelect = document.getElementById('timeframeSelect');
        if (tfSelect) {
            tfSelect.value = tf;
            tfSelect.dispatchEvent(new Event('change'));
        } else if (typeof switchTimeframe === 'function') {
            switchTimeframe(tf);
        } else {
            console.warn('Cannot change timeframe - no handler found');
        }

        console.log(`⏱️ Timeframe changed to: ${tf}`);
    },

    /**
     * Toggle indicator visibility
     */
    _toggleIndicator(indicator) {
        // Toggle in global renderStates
        if (window.renderStates) {
            window.renderStates[indicator] = !window.renderStates[indicator];
        }

        // Dispatch event for chart to update
        window.dispatchEvent(new CustomEvent('indicator-toggle', {
            detail: {
                indicator,
                visible: window.renderStates?.[indicator] ?? true
            }
        }));

        // Update toggle state in menu
        const item = this._menu.querySelector(`[data-indicator="${indicator}"]`);
        if (item) {
            item.classList.toggle('active');
        }

        // Trigger chart redraw
        if (typeof updateChart === 'function') {
            updateChart();
        }

        console.log(`📊 Toggled indicator: ${indicator}`);
    },

    /**
     * Reset chart zoom to default
     */
    _resetZoom() {
        if (typeof resetChartToDefault === 'function') {
            resetChartToDefault();
        } else {
            console.warn('resetChartToDefault function not available');
        }
        console.log('🔍 Chart zoom reset');
    },

    /**
     * Take screenshot of chart
     */
    _takeScreenshot() {
        if (!this._chartSvg) {
            console.warn('No chart SVG available');
            return;
        }

        try {
            // Get the SVG as string
            const svgElement = this._chartSvg.closest('svg') || this._chartSvg;
            const serializer = new XMLSerializer();
            const svgString = serializer.serializeToString(svgElement);

            // Create canvas
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
            const url = URL.createObjectURL(svgBlob);

            const img = new Image();
            img.onload = () => {
                canvas.width = svgElement.clientWidth || 1920;
                canvas.height = svgElement.clientHeight || 1080;

                // Fill background
                ctx.fillStyle = document.body.getAttribute('data-theme') === 'dark'
                    ? '#18181b' : '#ffffff';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.drawImage(img, 0, 0);
                URL.revokeObjectURL(url);

                // Download
                const link = document.createElement('a');
                const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
                link.download = `chart_${window.currentSymbol || 'BTC'}_${window.currentTimeframe || '1h'}_${timestamp}.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();

                console.log('📷 Screenshot saved');
            };

            img.onerror = () => {
                console.error('Failed to load SVG for screenshot');
                URL.revokeObjectURL(url);
            };

            img.src = url;
        } catch (error) {
            console.error('Screenshot failed:', error);
        }
    }
};

// Export for global access
if (typeof window !== 'undefined') {
    window.ChartContextMenu = ChartContextMenu;
}
