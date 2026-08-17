/**
 * Analysis Panel V2 Controller
 * 
 * Handles tab switching, data binding, and UI updates for the new panel design.
 * Uses ap-* element IDs to avoid conflicts with legacy code.
 */

const AnalysisPanelV2 = {
    // State
    _currentTab: 'context',
    _lastData: null,

    /**
     * Initialize the panel
     */
    init() {
        this._bindTabEvents();
        this.setLoading();
        console.log('📊 AnalysisPanelV2 initialized');
    },

    /**
     * Bind tab click events
     */
    _bindTabEvents() {
        const tabNav = document.querySelector('.ap-tab-nav');
        if (!tabNav) return;

        tabNav.addEventListener('click', (e) => {
            const tabBtn = e.target.closest('.ap-tab-btn');
            if (!tabBtn) return;

            const tabName = tabBtn.dataset.tab;
            this.switchTab(tabName);
        });
    },

    /**
     * Switch to a tab
     */
    switchTab(tabName) {
        this._currentTab = tabName;

        // Update button states
        document.querySelectorAll('.ap-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update pane visibility
        document.querySelectorAll('.ap-tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.dataset.pane === tabName);
        });
    },

    /**
     * Update panel with new data
     */
    update(data) {
        if (
            !data ||
            data.schema_version !== '1.0' ||
            data.engine !== 'core' ||
            data.source !== 'market_snapshot' ||
            data.status !== 'ready'
        ) {
            this.setError('Core response is unavailable or incompatible.');
            return;
        }
        this._lastData = data;

        const updated = this._formatTimeAgo(data.generated_at);
        this._setDataStatus('ready', `Updated ${updated || 'now'} · ${data.symbol} ${data.timeframe}`);

        this._updateGauge(data);
        this._updateThesis(data);
        this._updateEvents(data);
        this._updateContext(data);
        this._updateLevels(data);
        this._updateSignals(data);
        this._updateFooter(data);
        this._updateQuickStrip(data);

        console.log('📊 AnalysisPanelV2 updated');
    },

    setLoading(message = 'Loading Core analysis…') {
        this._lastData = null;
        this._setDataStatus('loading', message);
        this._clearMarketData('Loading…');
    },

    setError(message = 'Core analysis is unavailable.') {
        this._lastData = null;
        this._setDataStatus('error', message);
        this._clearMarketData('Unavailable');
    },

    _setDataStatus(state, message) {
        const status = document.getElementById('apDataStatus');
        if (!status) return;
        status.className = `ap-data-status ${state}`;
        status.textContent = message;
    },

    _clearMarketData(label) {
        const textValues = {
            apBiasValue: '—',
            apBiasLabel: label,
            apThesisText: label,
            apDirection: '—',
            apState: '—',
            apZone: '—',
            apMtfPercent: '—',
            apProtectedHigh: '—',
            apProtectedLow: '—',
            apLiqAbove: '—',
            apLiqBelow: '—',
            apInvPrice: '—',
            apBias: '—',
            apBiasReason: '—',
            apBullScenario: '—',
            apBearScenario: '—',
            apCurrentPrice: '—',
            apFooterInv: '—',
            qsBiasBadge: label.toUpperCase(),
            qsState: '—',
            qsZoneLabel: '—',
            qsProtectedHigh: '—',
            qsProtectedLow: '—',
            qsLiqAbove: '—',
            qsLiqBelow: '—',
            qsInvalidation: '—',
            qsCurrentPrice: '—',
        };

        Object.entries(textValues).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });

        const needle = document.getElementById('apNeedleGroup');
        if (needle) needle.style.transform = 'rotate(0deg)';
        const rangeIndicator = document.getElementById('apRangeIndicator');
        if (rangeIndicator) rangeIndicator.style.left = '50%';

        ['apDirection', 'apZone', 'apBias'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.className = 'ap-badge neutral';
        });
        const gaugeValue = document.getElementById('apBiasValue');
        const gaugeLabel = document.getElementById('apBiasLabel');
        if (gaugeValue) gaugeValue.className = 'ap-bias-value neutral';
        if (gaugeLabel) gaugeLabel.className = 'ap-bias-label neutral';
        const quickBias = document.getElementById('qsBiasBadge');
        const quickState = document.getElementById('qsState');
        if (quickBias) quickBias.className = 'qs-badge neutral';
        if (quickState) quickState.className = 'qs-state neutral';

        document.querySelectorAll('.ap-mtf-dot').forEach(dot => {
            dot.className = 'ap-mtf-dot unknown';
        });

        const events = document.getElementById('apEvents');
        if (events) {
            events.innerHTML = `<span class="ap-events-label">Recent:</span><span class="ap-event-chip neutral">${label}</span>`;
        }
        ['apFVGs', 'apSupportZones', 'apResistanceZones'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.innerHTML = `<span class="ap-muted">${label}</span>`;
        });

        this._setTickerAlerts([{ id: `status-${label}`, type: 'info', icon: '◈', text: label }]);
    },

    /**
     * Update the Quick Strip (bottom horizontal bar)
     */
    _updateQuickStrip(data) {
        const overview = data.quick_overview || {};
        // === Bias Badge ===
        const biasBadge = document.getElementById('qsBiasBadge');
        if (biasBadge) {
            const dir = overview.bias || 'neutral';
            const arrow = dir === 'bullish' ? '↑' : dir === 'bearish' ? '↓' : '→';
            biasBadge.className = `qs-badge ${dir}`;
            biasBadge.textContent = `${dir.toUpperCase()} ${arrow}`;
        }

        // === Structure State ===
        const stateEl = document.getElementById('qsState');
        if (stateEl) {
            const state = overview.state || 'neutral';
            stateEl.className = `qs-state ${state}`;
            stateEl.textContent = state.charAt(0).toUpperCase() + state.slice(1);
        }

        // === Price Zone ===
        const zoneLabel = document.getElementById('qsZoneLabel');
        if (zoneLabel && overview.zone) {
            const zone = overview.zone;
            zoneLabel.textContent = zone.charAt(0).toUpperCase() + zone.slice(1);
            // Add color class based on zone
            zoneLabel.className = 'qs-value';
            if (zone === 'premium') zoneLabel.classList.add('bearish');
            else if (zone === 'discount') zoneLabel.classList.add('bullish');
        } else if (zoneLabel) {
            zoneLabel.textContent = '—';
            zoneLabel.className = 'qs-value';
        }

        // === Protected Levels ===
        const protectedHigh = document.getElementById('qsProtectedHigh');
        const protectedLow = document.getElementById('qsProtectedLow');
        if (protectedHigh && overview.protected_high != null) {
            protectedHigh.textContent = this._formatPrice(overview.protected_high);
        } else if (protectedHigh) {
            protectedHigh.textContent = '--';
        }
        if (protectedLow && overview.protected_low != null) {
            protectedLow.textContent = this._formatPrice(overview.protected_low);
        } else if (protectedLow) {
            protectedLow.textContent = '--';
        }

        // === Liquidity Targets ===
        const liqAbove = document.getElementById('qsLiqAbove');
        const liqBelow = document.getElementById('qsLiqBelow');
        if (liqAbove && overview.liquidity_above != null) {
            liqAbove.textContent = this._formatPrice(overview.liquidity_above);
        } else if (liqAbove) {
            liqAbove.textContent = '--';
        }
        if (liqBelow && overview.liquidity_below != null) {
            liqBelow.textContent = this._formatPrice(overview.liquidity_below);
        } else if (liqBelow) {
            liqBelow.textContent = '--';
        }

        // === Invalidation Level ===
        const invalidation = document.getElementById('qsInvalidation');
        if (invalidation && overview.invalidation != null) {
            invalidation.textContent = this._formatPrice(overview.invalidation);
        } else if (invalidation) {
            invalidation.textContent = '--';
        }

        // === Alert Ticker ===
        this._updateAlertTicker(data);

        // === Current Price ===
        const priceEl = document.getElementById('qsCurrentPrice');
        if (priceEl && overview.current_price != null) {
            priceEl.textContent = this._formatPrice(overview.current_price);
        } else if (priceEl) {
            priceEl.textContent = '--';
        }
    },

    /**
     * Update alert ticker with scrolling alerts from /api/insights
     */
    _updateAlertTicker(data) {
        if (!this._tickerInitialized) {
            this._initTicker();
        }

        const alerts = (data.recent_events || []).slice(0, 6).map(event => ({
            id: event.source_id || `${event.event_type}-${event.timestamp}`,
            type: event.direction || 'info',
            icon: event.event_type === 'CHoCH' ? '⚡' : event.event_type === 'SWEEP' ? '◇' : '◈',
            text: event.description || event.event_type || 'Market structure update',
        }));

        if (alerts.length === 0) {
            alerts.push({
                id: 'monitoring',
                type: 'info',
                icon: '◈',
                text: data.thesis || 'No recent structural events',
            });
        }
        this._setTickerAlerts(alerts);
    },

    /**
     * Initialize the JS-based ticker system
     */
    _initTicker() {
        const track = document.getElementById('qsAlertTrack');
        const ticker = document.getElementById('qsAlertTicker');

        // If DOM elements not ready, retry on next frame
        if (!track || !ticker) {
            requestAnimationFrame(() => this._initTicker());
            return;
        }

        // Now we can mark as initialized
        this._tickerInitialized = true;
        this._tickerAlerts = [];
        this._tickerElements = [];
        this._tickerSpeed = 0.3; // pixels per frame (slower, smoother)
        this._tickerGap = 40; // gap between items
        this._tickerPaused = false;
        this._lastAlertIds = new Set();

        // Remove CSS animation - we'll handle it with JS
        track.style.animation = 'none';
        track.style.transform = 'none';
        track.style.display = 'flex';
        track.style.alignItems = 'center';
        track.style.gap = `${this._tickerGap}px`;

        // Pause on hover
        ticker.addEventListener('mouseenter', () => this._tickerPaused = true);
        ticker.addEventListener('mouseleave', () => this._tickerPaused = false);

        // The ticker is fed from the same Core snapshot as both panels.
        this._animateTicker();

        console.log('📢 Alert ticker initialized');
    },

    _setTickerAlerts(alerts) {
        const track = document.getElementById('qsAlertTrack');
        if (!track || !this._tickerInitialized) return;

        track.replaceChildren();
        this._tickerAlerts = [];
        this._tickerElements = [];
        this._tickerPosition = 0;
        alerts.forEach(alert => this._addTickerAlert(alert));
    },

    /**
     * Add a single alert to the ticker
     */
    _addTickerAlert(alert) {
        const track = document.getElementById('qsAlertTrack');
        if (!track) return;

        // Check if already exists
        if (this._tickerAlerts.some(a => a.id === alert.id)) return;

        // Add to our tracking array
        this._tickerAlerts.push(alert);

        // Create DOM element
        const el = document.createElement('div');
        el.className = `qs-alert-item ${alert.type}`;
        el.dataset.alertId = alert.id;
        el.innerHTML = `
            <span class="qs-alert-icon">${alert.icon}</span>
            <span class="qs-alert-text">${alert.text}</span>
        `;

        // Add to track
        track.appendChild(el);
        this._tickerElements.push(el);
    },

    /**
     * Animate the ticker using JS (recycle elements)
     */
    _animateTicker() {
        const track = document.getElementById('qsAlertTrack');
        const ticker = document.getElementById('qsAlertTicker');

        if (!track || !ticker) return;

        // Initialize position tracking
        this._tickerPosition = 0;

        const animate = () => {
            if (!this._tickerPaused && this._tickerElements.length > 0) {
                // Update position
                this._tickerPosition -= this._tickerSpeed;

                // Get first element to check for recycling
                const firstEl = this._tickerElements[0];
                if (firstEl) {
                    const firstWidth = firstEl.offsetWidth + this._tickerGap;

                    // When first element is fully off-screen, recycle it
                    if (Math.abs(this._tickerPosition) >= firstWidth) {
                        // Move element to end of DOM
                        track.appendChild(firstEl);
                        // Update our array order
                        this._tickerElements.push(this._tickerElements.shift());
                        // Adjust position to maintain seamless scroll
                        this._tickerPosition += firstWidth;
                    }
                }

                // Apply transform
                track.style.transform = `translateX(${this._tickerPosition}px)`;
            }

            requestAnimationFrame(animate);
        };

        requestAnimationFrame(animate);
    },

    /**
     * Update speedometer gauge and bias display
     * 
     * Needle rotation: -90° = 100% bearish, 0° = neutral, +90° = 100% bullish
     * So the full range is 180 degrees across the semicircle
     */
    _updateGauge(data) {
        const direction = data.structure?.bias || data.structure?.direction || 'neutral';
        const confidence = Math.max(0, Math.min(100, Number(data.confidence?.score) || 0));

        // Calculate needle angle
        // -90° = 100% bearish (left side)
        // 0° = neutral (center/up)
        // +90° = 100% bullish (right side)
        let needleAngle = 0;

        if (direction === 'bearish') {
            // Map confidence 50-100 to angle -45 to -90 (more bearish = more left)
            needleAngle = -((confidence / 100) * 90);
        } else if (direction === 'bullish') {
            // Map confidence 50-100 to angle +45 to +90 (more bullish = more right)
            needleAngle = (confidence / 100) * 90;
        } else {
            // Neutral - point straight up
            needleAngle = 0;
        }

        // Update needle rotation
        const needleGroup = document.getElementById('apNeedleGroup');
        if (needleGroup) {
            needleGroup.style.transform = `rotate(${needleAngle}deg)`;
        }

        // Update bias display
        const biasValue = document.getElementById('apBiasValue');
        const biasLabel = document.getElementById('apBiasLabel');

        if (biasValue) {
            biasValue.textContent = `${Math.round(confidence)}%`;
            biasValue.className = `ap-bias-value ${direction}`;
        }

        if (biasLabel) {
            const labelText = direction === 'bullish' ? 'Bullish' :
                direction === 'bearish' ? 'Bearish' : 'Neutral';
            biasLabel.textContent = labelText;
            biasLabel.className = `ap-bias-label ${direction}`;
        }
    },

    /**
     * Update thesis box
     */
    _updateThesis(data) {
        const thesisText = document.getElementById('apThesisText');
        if (!thesisText) return;
        thesisText.textContent = data.thesis || 'No clear structural thesis is available.';
    },

    /**
     * Update recent events strip
     */
    _updateEvents(data) {
        const eventsContainer = document.getElementById('apEvents');
        if (!eventsContainer) return;

        const events = data.recent_events || [];
        const label = '<span class="ap-events-label">Recent:</span>';

        if (events.length === 0) {
            eventsContainer.innerHTML = label + '<span class="ap-event-chip neutral">No events</span>';
            return;
        }

        const chips = events.slice(0, 3).map(event => {
            const dir = event.direction || 'neutral';
            const arrow = dir === 'bullish' ? '↑' : dir === 'bearish' ? '↓' : '';
            const time = this._formatTimeAgo(event.timestamp);
            return `<span class="ap-event-chip ${dir}">${event.event_type || event.type} ${arrow} <span class="ap-event-time">${time}</span></span>`;
        }).join('');

        eventsContainer.innerHTML = label + chips;
    },

    /**
     * Update Context tab
     */
    _updateContext(data) {
        // Direction badge
        const directionBadge = document.getElementById('apDirection');
        if (directionBadge) {
            const dir = data.structure?.direction || 'neutral';
            directionBadge.className = `ap-badge ${dir}`;
            directionBadge.textContent = dir.toUpperCase();
            const source = (data.structure?.direction_source || 'unavailable').replaceAll('_', ' ');
            const sourceTimeframe = data.structure?.source_timeframe || data.timeframe || '';
            directionBadge.title = `Derived from ${source} (${sourceTimeframe})`;
        }

        // State
        const stateEl = document.getElementById('apState');
        if (stateEl) stateEl.textContent = data.structure?.state || '--';

        // Range position
        const zoneEl = document.getElementById('apZone');
        const indicator = document.getElementById('apRangeIndicator');
        if (data.range_position) {
            // Use ?? instead of || to handle 0 as a valid value
            const pct = data.range_position.percentage ?? 50;
            if (zoneEl) {
                const zone = data.range_position.zone || 'equilibrium';
                zoneEl.textContent = zone.charAt(0).toUpperCase() + zone.slice(1);
                zoneEl.className = `ap-badge ${zone === 'discount' ? 'bullish' : zone === 'premium' ? 'bearish' : 'neutral'}`;
            }
            // pct=0 means at low (left), pct=100 means at high (right)
            if (indicator) indicator.style.left = `${pct}%`;
        } else {
            if (zoneEl) {
                zoneEl.textContent = '—';
                zoneEl.className = 'ap-badge neutral';
            }
            if (indicator) indicator.style.left = '50%';
        }

        // MTF dots are generated from the authoritative response so the active
        // chart timeframe is represented even when it is not in the defaults.
        const mtfDots = document.getElementById('apMtfDots');
        if (data.mtf?.timeframes) {
            mtfDots?.replaceChildren();
            Object.entries(data.mtf.timeframes).forEach(([tf, info]) => {
                if (!mtfDots) return;
                const dot = document.createElement('div');
                dot.className = `ap-mtf-dot ${info.direction || 'neutral'}`;
                dot.dataset.tf = tf;
                dot.title = info.direction === 'error'
                    ? `${tf.toUpperCase()}: unavailable`
                    : `${tf.toUpperCase()}: ${info.direction || 'unknown'} · ${info.state || 'unknown'}`;

                const indicator = document.createElement('span');
                indicator.className = 'ap-mtf-indicator';
                const label = document.createElement('span');
                label.className = 'ap-mtf-label';
                label.textContent = tf.toUpperCase();
                dot.append(indicator, label);
                mtfDots.appendChild(dot);
            });
        }

        const mtfPercent = document.getElementById('apMtfPercent');
        if (mtfPercent) {
            mtfPercent.textContent = data.mtf?.total_analyzed > 0
                ? `${data.mtf.aligned_count}/${data.mtf.total_analyzed}`
                : '—';
        }
    },

    /**
     * Update Levels tab
     */
    _updateLevels(data) {
        // Protected levels
        const highEl = document.getElementById('apProtectedHigh');
        const lowEl = document.getElementById('apProtectedLow');

        if (highEl) highEl.textContent = data.levels?.high != null ? this._formatPrice(data.levels.high) : '—';
        if (lowEl) lowEl.textContent = data.levels?.low != null ? this._formatPrice(data.levels.low) : '—';

        // Liquidity
        const liqAbove = document.getElementById('apLiqAbove');
        const liqBelow = document.getElementById('apLiqBelow');

        if (liqAbove && data.liquidity?.above) {
            liqAbove.textContent = data.liquidity.above.slice(0, 2).map(p => this._formatPrice(p)).join(' • ') || 'None';
        }
        if (liqBelow && data.liquidity?.below) {
            liqBelow.textContent = data.liquidity.below.slice(0, 2).map(p => this._formatPrice(p)).join(' • ') || 'None';
        }

        // Invalidation
        const invPrice = document.getElementById('apInvPrice');
        if (invPrice) invPrice.textContent = data.invalidation?.price != null
            ? this._formatPrice(data.invalidation.price)
            : '—';

        // Fair Value Gaps - Compact chip layout
        const fvgsEl = document.getElementById('apFVGs');
        if (fvgsEl && data.fvgs) {
            if (data.fvgs.length > 0) {
                fvgsEl.innerHTML = `
                    <div class="ap-chips">
                        ${data.fvgs.slice(0, 5).map(fvg => {
                    const dir = fvg.direction || 'neutral';
                    const arrow = dir === 'bullish' ? '↑' : dir === 'bearish' ? '↓' : '';
                    const mid = (fvg.high + fvg.low) / 2;
                    return `<span class="ap-chip ${dir}" title="${this._formatPrice(fvg.low)} - ${this._formatPrice(fvg.high)}">${arrow} ${this._formatPrice(mid)}</span>`;
                }).join('')}
                    </div>
                `;
            } else {
                fvgsEl.innerHTML = '<span class="ap-muted">None</span>';
            }
        }

        // Support & Resistance - Combined compact layout
        const supportEl = document.getElementById('apSupportZones');
        const resistanceEl = document.getElementById('apResistanceZones');

        if (supportEl && data.sr_zones?.support) {
            if (data.sr_zones.support.length > 0) {
                supportEl.innerHTML = `
                    <div class="ap-chips">
                        ${data.sr_zones.support.slice(0, 3).map(zone => {
                    const mid = (zone.high + zone.low) / 2;
                    const touches = zone.touches || 0;
                    return `<span class="ap-chip bullish" title="${touches} touches">${this._formatPrice(mid)}</span>`;
                }).join('')}
                    </div>
                `;
            } else {
                supportEl.innerHTML = '<span class="ap-muted">None</span>';
            }
        }

        if (resistanceEl && data.sr_zones?.resistance) {
            if (data.sr_zones.resistance.length > 0) {
                resistanceEl.innerHTML = `
                    <div class="ap-chips">
                        ${data.sr_zones.resistance.slice(0, 3).map(zone => {
                    const mid = (zone.high + zone.low) / 2;
                    const touches = zone.touches || 0;
                    return `<span class="ap-chip bearish" title="${touches} touches">${this._formatPrice(mid)}</span>`;
                }).join('')}
                    </div>
                `;
            } else {
                resistanceEl.innerHTML = '<span class="ap-muted">None</span>';
            }
        }
    },

    /**
     * Update Signals tab
     */
    _updateSignals(data) {
        // Bias
        const biasBadge = document.getElementById('apBias');
        if (biasBadge) {
            const dir = data.structure?.bias || 'neutral';
            biasBadge.className = `ap-badge ${dir}`;
            biasBadge.textContent = dir.toUpperCase();
        }

        // Reasoning
        const reasonEl = document.getElementById('apBiasReason');
        if (reasonEl) {
            reasonEl.textContent = data.analysis?.section_6_direction?.bias_reasoning || '—';
        }

        // Scenarios
        const bullScenario = document.getElementById('apBullScenario');
        const bearScenario = document.getElementById('apBearScenario');

        if (bullScenario) {
            bullScenario.textContent = data.analysis?.section_8_projection?.bullish_scenario || '—';
        }
        if (bearScenario) {
            bearScenario.textContent = data.analysis?.section_8_projection?.bearish_scenario || '—';
        }

    },

    /**
     * Update footer
     */
    _updateFooter(data) {
        const priceEl = document.getElementById('apCurrentPrice');
        const invEl = document.getElementById('apFooterInv');

        if (priceEl) priceEl.textContent = data.current_price != null ? this._formatPrice(data.current_price) : '—';
        if (invEl) invEl.textContent = data.invalidation?.price != null
            ? this._formatPrice(data.invalidation.price)
            : '—';
    },

    /**
     * Format price for display
     */
    _formatPrice(price) {
        if (typeof price !== 'number' || !Number.isFinite(price)) return '—';
        return price.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    },

    /**
     * Format timestamp to "Xm ago" style
     */
    _formatTimeAgo(timestamp) {
        if (!timestamp) return '';
        const now = Date.now();
        const diff = now - timestamp;
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'now';
        if (mins < 60) return `${mins}m`;
        const hours = Math.floor(mins / 60);
        if (hours < 24) return `${hours}h`;
        return `${Math.floor(hours / 24)}d`;
    }
};

// Auto-initialize
if (typeof window !== 'undefined') {
    window.AnalysisPanelV2 = AnalysisPanelV2;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => AnalysisPanelV2.init());
    } else {
        AnalysisPanelV2.init();
    }
}
