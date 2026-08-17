"""S/R Detector - Detect Support/Resistance Zones.

CONTRACT:
- FACT DETECTION ONLY
- NO interpretation

Algorithm:
1. Collect swing highs → potential resistance points
2. Collect swing lows → potential support points
3. Cluster nearby swings within tolerance
4. Calculate zone bounds (min/max of cluster)
5. Score by touch count, swing degree, recency, volume, momentum
6. Filter to top N zones
"""
from typing import List, Optional
from dataclasses import dataclass

from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.sr_zone import SRZone, SRAnalysis

# Import indicators for volume and momentum analysis
from backend.chart.engines.indicators.volume import VolumeAnalyzer
from backend.chart.engines.indicators.momentum import MomentumAnalyzer


def generate_id(prefix: str) -> str:
    import time
    import random
    return f"{prefix}_{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


@dataclass
class SRConfig:
    """Configuration for S/R detection."""
    cluster_threshold_pct: float = 0.003   # 0.3% price tolerance for clustering
    min_touches: int = 2                    # Min swings to form a zone
    max_zones: int = 10                     # Max zones per side
    recency_weight: float = 0.2            # Weight for recent zones
    max_break_count: int = 5               # Invalidate zone after this many breaks
    min_strength: float = 0.4              # Minimum strength to include zone (0-1)
    # Round number settings
    include_round_numbers: bool = True      # Include psychological levels
    round_number_strength: float = 0.5     # Base strength for round numbers


class SRDetector:
    """Detect Support/Resistance zones by clustering swing points.
    
    Support zones: Formed from clustered swing lows
    Resistance zones: Formed from clustered swing highs
    """
    
    def __init__(self, config: Optional[SRConfig] = None):
        self.config = config or SRConfig()
    
    def detect(
        self,
        swings: List[SwingPoint],
        candles: List[Candle],
        timeframe: str
    ) -> SRAnalysis:
        """Detect all S/R zones.
        
        Priority:
        1. Protected swings (unbroken structural levels) - highest priority
        2. External swings (major structure points)
        3. Clustered swings (multiple touches at same level)
        """
        if not swings:
            return SRAnalysis()
        
        current_price = candles[-1].close if candles else 0.0
        total_candles = len(candles)
        
        # Pre-calculate volume and momentum data for strength scoring
        self._volume_bars = []
        self._momentum_readings = []
        if candles:
            try:
                vol_analyzer = VolumeAnalyzer()
                _, self._volume_bars = vol_analyzer.analyze(candles)
            except Exception:
                pass
            
            try:
                mom_analyzer = MomentumAnalyzer()
                # analyze() returns single MomentumReading for current state
                self._momentum_reading = mom_analyzer.analyze(candles)
            except Exception:
                self._momentum_reading = None
        
        # Store candles reference for use in zone creation
        self._candles = candles
        
        # Separate by type
        highs = [s for s in swings if s.kind == "high" and s.valid]
        lows = [s for s in swings if s.kind == "low" and s.valid]
        
        # === 1. Create zones from PROTECTED swings (unbroken structural levels) ===
        protected_resistance = self._create_structural_zones(
            [s for s in highs if s.is_protected and not s.broken],
            "resistance", timeframe, current_price, total_candles, strength_boost=0.3
        )
        protected_support = self._create_structural_zones(
            [s for s in lows if s.is_protected and not s.broken],
            "support", timeframe, current_price, total_candles, strength_boost=0.3
        )
        
        # === 2. Create zones from EXTERNAL swings (major structure) ===
        # Exclude already used protected swings
        protected_ids = {s.id for s in highs if s.is_protected} | {s.id for s in lows if s.is_protected}
        
        external_resistance = self._create_structural_zones(
            [s for s in highs if s.degree == "external" and s.id not in protected_ids],
            "resistance", timeframe, current_price, total_candles, strength_boost=0.2
        )
        external_support = self._create_structural_zones(
            [s for s in lows if s.degree == "external" and s.id not in protected_ids],
            "support", timeframe, current_price, total_candles, strength_boost=0.2
        )
        
        # === 3. Add clustered zones (multiple touches at same level) ===
        clustered_resistance = self._cluster_swings(
            highs, "resistance", timeframe, current_price, total_candles
        )
        clustered_support = self._cluster_swings(
            lows, "support", timeframe, current_price, total_candles
        )
        
        # Combine: structural zones first, then clustered
        resistance_zones = protected_resistance + external_resistance + clustered_resistance
        support_zones = protected_support + external_support + clustered_support
        
        # Remove duplicates (zones at very similar prices)
        resistance_zones = self._deduplicate_zones(resistance_zones, current_price)
        support_zones = self._deduplicate_zones(support_zones, current_price)
        
        # Check which zones are broken
        resistance_zones = self._check_broken(resistance_zones, candles)
        support_zones = self._check_broken(support_zones, candles)
        
        # Sort by strength and limit
        resistance_zones = sorted(resistance_zones, key=lambda z: z.strength, reverse=True)
        support_zones = sorted(support_zones, key=lambda z: z.strength, reverse=True)
        
        # Filter by minimum strength threshold
        resistance_zones = [z for z in resistance_zones if z.strength >= self.config.min_strength]
        support_zones = [z for z in support_zones if z.strength >= self.config.min_strength]
        
        # Limit to max zones
        resistance_zones = resistance_zones[:self.config.max_zones]
        support_zones = support_zones[:self.config.max_zones]
        
        # Find nearest to current price
        nearest_support = self._find_nearest(support_zones, current_price, "below")
        nearest_resistance = self._find_nearest(resistance_zones, current_price, "above")
        
        # Combine all zones
        all_zones = resistance_zones + support_zones
        
        # Add round number levels if enabled
        if self.config.include_round_numbers and current_price > 0:
            round_zones = self._detect_round_numbers(
                current_price, timeframe, len(candles)
            )
            all_zones.extend(round_zones)
        
        intact = [z for z in all_zones if z.is_intact]
        broken = [z for z in all_zones if z.broken]
        
        return SRAnalysis(
            support_zones=support_zones,
            resistance_zones=resistance_zones,
            all_zones=all_zones,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            support_count=len(support_zones),
            resistance_count=len(resistance_zones),
            intact_count=len(intact),
            broken_count=len(broken)
        )
    
    def _create_structural_zones(
        self,
        swings: List[SwingPoint],
        zone_type: str,
        timeframe: str,
        current_price: float,
        total_candles: int,
        strength_boost: float = 0.0
    ) -> List[SRZone]:
        """Create S/R zones directly from structural swings (protected or external).
        
        Each swing becomes its own zone, with a small buffer around the price.
        """
        zones = []
        
        for swing in swings:
            # Create a small zone around the swing price (0.2% buffer)
            buffer = swing.price * 0.002
            
            # Calculate base strength with enhanced scoring
            base_strength = self._calculate_strength(
                touch_count=1,
                external_count=1 if swing.degree == "external" else 0,
                zone_width=buffer * 2,
                current_price=current_price,
                avg_index=swing.index,
                total_candles=total_candles,
                cluster=[swing],  # Single swing as cluster
                zone_type=zone_type,
                zone_midpoint=swing.price
            )
            
            zone = SRZone(
                id=generate_id(zone_type[:3]),
                zone_type=zone_type,
                high=swing.price + buffer,
                low=swing.price - buffer,
                midpoint=swing.price,
                swing_ids=[swing.id],
                touch_count=1,
                external_count=1 if swing.degree == "external" else 0,
                strength=min(1.0, base_strength + strength_boost),  # Boost for structural importance
                timestamp=swing.timestamp,
                last_touch_timestamp=swing.timestamp,
                index=swing.index,
                timeframe=timeframe,
                broken=swing.broken,
            )
            zones.append(zone)
        
        return zones
    
    def _deduplicate_zones(
        self,
        zones: List[SRZone],
        current_price: float
    ) -> List[SRZone]:
        """Remove duplicate zones at similar price levels.
        
        Keeps the zone with higher strength when two zones overlap significantly.
        """
        if not zones:
            return zones
        
        # Sort by strength (strongest first)
        zones = sorted(zones, key=lambda z: z.strength, reverse=True)
        
        result = []
        used_levels = []
        
        for zone in zones:
            # Check if this zone is too close to an already-added zone
            too_close = False
            tolerance = current_price * self.config.cluster_threshold_pct
            
            for used_price in used_levels:
                if abs(zone.midpoint - used_price) <= tolerance:
                    too_close = True
                    break
            
            if not too_close:
                result.append(zone)
                used_levels.append(zone.midpoint)
        
        return result
    
    def _cluster_swings(
        self,
        swings: List[SwingPoint],
        zone_type: str,
        timeframe: str,
        current_price: float,
        total_candles: int
    ) -> List[SRZone]:
        """Cluster swings at similar price levels into zones."""
        if not swings:
            return []
        
        zones: List[SRZone] = []
        used_ids = set()
        
        # Sort by price for easier clustering
        sorted_swings = sorted(swings, key=lambda s: s.price)
        
        for swing in sorted_swings:
            if swing.id in used_ids:
                continue
            
            # Find all swings within tolerance of this one
            tolerance = swing.price * self.config.cluster_threshold_pct
            cluster = [swing]
            
            for other in sorted_swings:
                if other.id != swing.id and other.id not in used_ids:
                    if abs(other.price - swing.price) <= tolerance:
                        cluster.append(other)
            
            # Only create zone if meets minimum touches
            if len(cluster) >= self.config.min_touches:
                zone = self._create_zone(
                    cluster, zone_type, timeframe, current_price, total_candles
                )
                zones.append(zone)
                
                # Mark all clustered swings as used
                for s in cluster:
                    used_ids.add(s.id)
        
        return zones
    
    def _create_zone(
        self,
        cluster: List[SwingPoint],
        zone_type: str,
        timeframe: str,
        current_price: float,
        total_candles: int
    ) -> SRZone:
        """Create a zone from a cluster of swings."""
        prices = [s.price for s in cluster]
        zone_high = max(prices)
        zone_low = min(prices)
        midpoint = (zone_high + zone_low) / 2
        
        # Count external swings in cluster
        external_count = sum(1 for s in cluster if getattr(s, 'degree', 'internal') == 'external')
        
        # Timestamps
        timestamps = [s.timestamp for s in cluster]
        oldest_ts = min(timestamps)
        newest_ts = max(timestamps)
        
        # Index
        indices = [s.index for s in cluster]
        avg_index = sum(indices) // len(indices)
        
        # Calculate strength with enhanced scoring
        strength = self._calculate_strength(
            touch_count=len(cluster),
            external_count=external_count,
            zone_width=zone_high - zone_low,
            current_price=current_price,
            avg_index=avg_index,
            total_candles=total_candles,
            cluster=cluster,
            zone_type=zone_type,
            zone_midpoint=midpoint
        )
        
        return SRZone(
            id=generate_id("sr"),
            zone_type=zone_type,
            high=zone_high,
            low=zone_low,
            midpoint=midpoint,
            swing_ids=[s.id for s in cluster],
            touch_count=len(cluster),
            external_count=external_count,
            strength=strength,
            timestamp=oldest_ts,
            last_touch_timestamp=newest_ts,
            index=avg_index,
            timeframe=timeframe
        )
    
    def _calculate_strength(
        self,
        touch_count: int,
        external_count: int,
        zone_width: float,
        current_price: float,
        avg_index: int,
        total_candles: int,
        cluster: List[SwingPoint] = None,
        zone_type: str = None,
        zone_midpoint: float = None
    ) -> float:
        """Calculate composite strength score (0-1).
        
        Enhanced scoring system based on professional S/R analysis:
        
        Core Factors (55%):
        - Touch count: 2-3 optimal, diminishes after 4+ (15%)
        - External swings: Major structure points matter (10%)
        - Zone width: Tighter = more precise (10%)
        - Recency: Newer zones more relevant (10%)
        - Reaction strength: Large wick rejections (10%)
        
        Bonus Factors (45%):
        - Round numbers: Psychological levels (10%)
        - Volume at touches: High volume rejections (10%)
        - Momentum into zone: Strong momentum before zone = strong (10%)
        - Role reversal: Support→Resistance flip (15%)
        """
        strength = 0.0
        
        # ===== CORE FACTORS (55%) =====
        
        # 1. Touch count (15%): 2-3 is optimal, diminishes after
        if touch_count == 1:
            touch_score = 0.5  # Fresh zone - could be strong for breakouts
        elif touch_count <= 3:
            touch_score = 1.0  # Optimal
        elif touch_count <= 5:
            touch_score = 0.8  # Still strong
        else:
            touch_score = 0.6  # Overused, prone to breaking
        strength += touch_score * 0.15
        
        # 2. External swings factor (10%): Major structure matters
        if external_count > 0:
            external_score = min(1.0, external_count / 2)
            strength += external_score * 0.10
        
        # 3. Zone width factor (10%): Tighter = stronger
        if current_price > 0:
            width_pct = zone_width / current_price
            if width_pct < 0.002:  # < 0.2% = very tight
                width_score = 1.0
            elif width_pct < 0.005:  # < 0.5% = tight
                width_score = 0.8
            elif width_pct < 0.01:  # < 1% = normal
                width_score = 0.5
            else:  # > 1% = wide (less reliable)
                width_score = 0.2
            strength += width_score * 0.10
        
        # 4. Recency factor (10%): Newer zones more relevant
        if total_candles > 0:
            age = total_candles - avg_index
            age_ratio = age / total_candles
            if age_ratio < 0.1:  # Very recent (10% of chart)
                recency_score = 1.0
            elif age_ratio < 0.3:  # Recent (30%)
                recency_score = 0.8
            elif age_ratio < 0.5:  # Middle-aged (50%)
                recency_score = 0.6
            else:  # Old (but may still be valid if untested)
                recency_score = 0.4
            strength += recency_score * 0.10
        
        # 5. Reaction strength (10%): Analyze wick size at zone touches
        reaction_score = 0.0
        if cluster and hasattr(self, '_candles') and self._candles:
            wick_sizes = []
            for swing in cluster:
                if 0 <= swing.index < len(self._candles):
                    candle = self._candles[swing.index]
                    body = abs(candle.close - candle.open)
                    total_range = candle.high - candle.low
                    if total_range > 0:
                        wick_ratio = (total_range - body) / total_range
                        wick_sizes.append(wick_ratio)
            
            if wick_sizes:
                avg_wick = sum(wick_sizes) / len(wick_sizes)
                # High wick ratio = strong rejection
                reaction_score = min(1.0, avg_wick * 2)  # 0.5 wick ratio = 1.0 score
        strength += reaction_score * 0.10
        
        # ===== BONUS FACTORS (45%) =====
        
        # 6. Round number bonus (10%): Psychological levels
        round_score = 0.0
        if zone_midpoint and zone_midpoint > 0:
            # Check if near a round number
            price_str = str(int(zone_midpoint))
            
            # Major round numbers (ends in 000 or 0000)
            if zone_midpoint >= 1000 and int(zone_midpoint) % 1000 < 50:
                round_score = 1.0
            elif zone_midpoint >= 100 and int(zone_midpoint) % 100 < 10:
                round_score = 0.7
            elif zone_midpoint >= 10 and int(zone_midpoint) % 50 < 5:
                round_score = 0.5
        strength += round_score * 0.10
        
        # 7. Volume at touches (10%): High volume rejections = stronger
        volume_score = 0.0
        if cluster and hasattr(self, '_volume_bars') and self._volume_bars:
            vol_conditions = []
            for swing in cluster:
                if 0 <= swing.index < len(self._volume_bars):
                    vol_bar = self._volume_bars[swing.index]
                    # Check for high/climactic volume at touch
                    if hasattr(vol_bar, 'relative_volume'):
                        if vol_bar.relative_volume >= 2.0:  # Climactic
                            vol_conditions.append(1.0)
                        elif vol_bar.relative_volume >= 1.5:  # Very high
                            vol_conditions.append(0.8)
                        elif vol_bar.relative_volume >= 1.2:  # High
                            vol_conditions.append(0.5)
                        else:
                            vol_conditions.append(0.2)
            
            if vol_conditions:
                volume_score = sum(vol_conditions) / len(vol_conditions)
        strength += volume_score * 0.10
        
        # 8. Momentum context (10%): Current market momentum affects zone likelihood
        momentum_score = 0.5  # Default neutral
        if hasattr(self, '_momentum_reading') and self._momentum_reading:
            # Use current overall momentum reading
            reading = self._momentum_reading
            if hasattr(reading, 'strength'):
                # Lower overall momentum = zones more likely to hold
                # Higher momentum = zones more likely to break
                mom_strength = reading.strength
                if mom_strength < 0.3:
                    momentum_score = 0.9  # Low momentum market = zones hold
                elif mom_strength < 0.5:
                    momentum_score = 0.7
                elif mom_strength < 0.7:
                    momentum_score = 0.5
                else:
                    momentum_score = 0.3  # High momentum = zones at risk
        strength += momentum_score * 0.10
        
        # 9. Role reversal bonus (15%): Add in post-processing if zone flipped
        # This is handled separately when zone.is_flipped is detected
        # (added to strength after zone creation if applicable)
        
        return min(1.0, strength)
    
    def _check_broken(
        self,
        zones: List[SRZone],
        candles: List[Candle]
    ) -> List[SRZone]:
        """Check if zones have been broken.
        
        Tracks multiple breaks per zone:
        - break_count: How many times the zone was broken
        - invalidated: True if break_count >= max_break_count
        
        A zone can be broken, recaptured, and broken again.
        This counts each time price closes through the zone boundary.
        """
        for zone in zones:
            # Skip already invalidated zones
            if zone.invalidated:
                continue
                
            is_broken = False  # Track if price is currently OUTSIDE/broken from zone
            
            for candle in candles:
                if candle.timestamp <= zone.timestamp:
                    continue
                
                if zone.is_support:
                    # Check if price is in or above zone (not broken)
                    price_ok = candle.close >= zone.low
                    
                    if candle.close < zone.low:
                        # Price is below zone - this is a break
                        if not is_broken:  # Only count first candle of the break
                            zone.break_count += 1
                            zone.broken = True
                            
                            if zone.break_timestamp is None:
                                zone.break_timestamp = candle.timestamp
                            zone.last_break_timestamp = candle.timestamp
                            
                            # Check if invalidated
                            if zone.break_count >= self.config.max_break_count:
                                zone.invalidated = True
                                break
                        is_broken = True
                    else:
                        # Price is back at or above zone low - reset broken state
                        is_broken = False
                        
                elif zone.is_resistance:
                    if candle.close > zone.high:
                        # Price is above zone - this is a break
                        if not is_broken:  # Only count first candle of the break
                            zone.break_count += 1
                            zone.broken = True
                            
                            if zone.break_timestamp is None:
                                zone.break_timestamp = candle.timestamp
                            zone.last_break_timestamp = candle.timestamp
                            
                            # Check if invalidated
                            if zone.break_count >= self.config.max_break_count:
                                zone.invalidated = True
                                break
                        is_broken = True
                    else:
                        # Price is back at or below zone high - reset broken state
                        is_broken = False
        
        return zones
    
    def _find_nearest(
        self,
        zones: List[SRZone],
        current_price: float,
        direction: str
    ) -> Optional[SRZone]:
        """Find nearest intact zone above or below current price."""
        intact = [z for z in zones if z.is_intact]
        
        if direction == "above":
            above = [z for z in intact if z.midpoint > current_price]
            if above:
                return min(above, key=lambda z: z.midpoint)
        else:
            below = [z for z in intact if z.midpoint < current_price]
            if below:
                return max(below, key=lambda z: z.midpoint)
        
        return None
    
    def _detect_round_numbers(
        self,
        current_price: float,
        timeframe: str,
        total_candles: int
    ) -> List[SRZone]:
        """
        Detect round number / psychological levels as S/R zones.
        
        For crypto (BTC-like prices):
        - Major: $100,000, $50,000 multiples
        - Minor: $10,000, $5,000 multiples
        - Micro: $1,000, $500 multiples
        
        For lower prices:
        - Major: $100, $50 multiples
        - Minor: $10, $5 multiples
        - Micro: $1, $0.50 multiples
        """
        zones = []
        
        # Determine appropriate round number intervals based on price
        if current_price >= 10000:
            # High value assets (BTC)
            intervals = [
                (100000, 0.7, "major"),   # $100k levels
                (50000, 0.6, "major"),    # $50k levels
                (10000, 0.5, "minor"),    # $10k levels
                (5000, 0.4, "minor"),     # $5k levels
            ]
        elif current_price >= 100:
            # Medium value assets (ETH, etc)
            intervals = [
                (1000, 0.7, "major"),     # $1k levels
                (500, 0.6, "major"),      # $500 levels
                (100, 0.5, "minor"),      # $100 levels
                (50, 0.4, "minor"),       # $50 levels
            ]
        elif current_price >= 1:
            # Low value assets
            intervals = [
                (10, 0.7, "major"),       # $10 levels
                (5, 0.6, "major"),        # $5 levels
                (1, 0.5, "minor"),        # $1 levels
            ]
        else:
            # Sub-dollar assets
            intervals = [
                (0.1, 0.7, "major"),      # $0.10 levels
                (0.05, 0.6, "major"),     # $0.05 levels
                (0.01, 0.5, "minor"),     # $0.01 levels
            ]
        
        # Range to check: 20% above and below current price
        price_range = current_price * 0.20
        min_price = current_price - price_range
        max_price = current_price + price_range
        
        seen_prices = set()
        
        for interval, strength_mult, level_type in intervals:
            # Find nearest round number below
            level = (current_price // interval) * interval
            
            # Generate levels within range
            while level <= max_price:
                if level >= min_price and level not in seen_prices:
                    seen_prices.add(level)
                    
                    # Determine zone type based on position relative to price
                    zone_type = "resistance" if level > current_price else "support"
                    
                    # Calculate strength (base * multiplier)
                    strength = self.config.round_number_strength * strength_mult
                    
                    # Zone width based on price (0.5%)
                    zone_width = level * 0.005
                    
                    zone = SRZone(
                        id=generate_id("rn"),
                        zone_type=zone_type,
                        high=level + zone_width / 2,
                        low=level - zone_width / 2,
                        midpoint=level,
                        swing_ids=[],  # No actual swings
                        touch_count=0,
                        external_count=0,
                        strength=strength,
                        timestamp=0,
                        last_touch_timestamp=0,
                        index=0,
                        timeframe=timeframe,
                        is_round_number=True,
                        round_number_type=level_type
                    )
                    zones.append(zone)
                
                level += interval
        
        return zones


# =============================================================================
# FUNCTIONAL API
# =============================================================================

def detect_sr_zones(
    swings: List[SwingPoint],
    candles: List[Candle],
    timeframe: str,
    config: Optional[SRConfig] = None
) -> SRAnalysis:
    """Detect S/R zones from swing points."""
    detector = SRDetector(config)
    return detector.detect(swings, candles, timeframe)
