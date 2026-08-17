/**
 * Zone Visibility Controller
 * 
 * Dynamically shows/hides drawings based on current price position relative to zones.
 * 
 * Rules:
 * - Active zone: Show ALL drawings
 * - Previous zone: Show ALL if price within its range
 * - Scanned zones (older): Show only EXTENDING drawings (FVG, protected, liquidity)
 */

const ZoneVisibilityController = {
    // Current visibility state
    visibleZones: [],
    currentPrice: 0,
    allZones: [],

    // Drawing type classification
    EXTENDING_TYPES: new Set([
        'fvg', 'fair_value_gap',
        'protected_level', 'protected_high', 'protected_low',
        'liquidity', 'liquidity_pool',
        'order_block', 'breaker_block',
        'trendline',
        'sr_zone', 'support_zone', 'resistance_zone',
        'imbalance'
    ]),

    NON_EXTENDING_TYPES: new Set([
        'swing', 'swing_high', 'swing_low',
        'bos', 'choch', 'structure_break',
        'pattern', 'triangle', 'wedge', 'pennant',
        'head_shoulders', 'double_top', 'double_bottom'
    ]),

    /**
     * Initialize with zones and price
     */
    init(zones, currentPrice) {
        this.allZones = zones || [];
        this.currentPrice = currentPrice;
        this.update();
    },

    /**
     * Update visibility based on current price
     */
    update(newPrice) {
        if (newPrice !== undefined) {
            this.currentPrice = newPrice;
        }
        this.visibleZones = this.calculateVisibleZones();
        this.applyVisibility();
    },

    /**
     * Calculate which zones should be visible
     */
    calculateVisibleZones() {
        const visible = [];

        if (!this.allZones.length) return visible;

        // 1. Active zone - always show all
        const activeZone = this.allZones[0];
        visible.push({
            zone: activeZone,
            type: 'active',
            showAll: true
        });

        // 2. Previous zone - check if price within range
        if (this.allZones.length > 1) {
            const prevZone = this.allZones[1];

            if (this._priceWithinZone(prevZone)) {
                visible.push({
                    zone: prevZone,
                    type: 'previous',
                    showAll: true
                });
            } else {
                // 3. Scan left for zones containing price
                for (let i = 2; i < this.allZones.length; i++) {
                    const zone = this.allZones[i];
                    if (this._priceWithinZone(zone)) {
                        visible.push({
                            zone: zone,
                            type: 'scanned',
                            showAll: false  // Extending drawings only
                        });
                    }
                }
            }
        }

        return visible;
    },

    /**
     * Check if current price is within zone's high/low range
     */
    _priceWithinZone(zone) {
        const high = zone.zone_high || zone.zoneHigh || 0;
        const low = zone.zone_low || zone.zoneLow || 0;
        return this.currentPrice >= low && this.currentPrice <= high;
    },

    /**
     * Check if drawing type extends beyond its zone
     */
    isExtendingType(drawingType) {
        if (!drawingType) return false;
        const type = String(drawingType).toLowerCase();
        return this.EXTENDING_TYPES.has(type);
    },

    /**
     * Check if a drawing should be visible
     */
    shouldShowDrawing(drawing, zoneId) {
        const visibleZone = this.visibleZones.find(vz =>
            vz.zone.id === zoneId || vz.zone.zone_id === zoneId
        );

        if (!visibleZone) return false;
        if (visibleZone.showAll) return true;

        // For scanned zones, only show extending drawings
        const drawingType = drawing.type || drawing.drawing_type || drawing.kind;
        return this.isExtendingType(drawingType);
    },

    /**
     * Apply visibility to DOM elements
     */
    applyVisibility() {
        // Get visible zone IDs
        const visibleIds = new Set(
            this.visibleZones.map(vz => vz.zone.id || vz.zone.zone_id)
        );

        // Hide all zone drawings first
        document.querySelectorAll('[data-zone-id]').forEach(el => {
            const zoneId = el.getAttribute('data-zone-id');
            if (visibleIds.has(zoneId)) {
                el.style.display = '';

                // For scanned zones, hide non-extending drawings
                const visibleZone = this.visibleZones.find(vz =>
                    (vz.zone.id === zoneId || vz.zone.zone_id === zoneId)
                );

                if (visibleZone && !visibleZone.showAll) {
                    const drawingType = el.getAttribute('data-drawing-type');
                    if (!this.isExtendingType(drawingType)) {
                        el.style.display = 'none';
                    }
                }
            } else {
                el.style.display = 'none';
            }
        });

        console.log(`[ZoneVisibility] Updated: ${this.visibleZones.length} zones visible`);
    },

    /**
     * Get visibility summary for debugging
     */
    getSummary() {
        return {
            currentPrice: this.currentPrice,
            totalZones: this.allZones.length,
            visibleZones: this.visibleZones.length,
            zones: this.visibleZones.map(vz => ({
                id: vz.zone.id,
                type: vz.type,
                showAll: vz.showAll
            }))
        };
    },

    /**
     * Fetch visibility info from backend API
     */
    async fetchFromAPI(symbol, timeframe, periods = 200) {
        try {
            const url = `/api/core/zone-visibility?symbol=${symbol}&timeframe=${timeframe}&periods=${periods}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (data.success) {
                this.currentPrice = data.current_price;
                this.visibleZones = data.visibility.zones || [];
                console.log('[ZoneVisibility] Fetched from API:', this.getSummary());
            }
            return data;
        } catch (error) {
            console.error('[ZoneVisibility] API error:', error);
            return null;
        }
    }
};

// Export to window
window.ZoneVisibilityController = ZoneVisibilityController;
