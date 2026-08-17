"""Range Detector - Detect consolidation ranges.

CONTRACT:
- FACT DETECTION ONLY
- NO interpretation
"""
from typing import List, Optional

from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.range import PriceRange
from backend.chart.engines.core.schemas.swing import SwingPoint


class RangeDetector:
    """Detect consolidation ranges.
    
    A range is detected when:
    - Price oscillates between high and low bounds
    - Multiple touches on each bound
    - No breakout (yet)
    """
    
    def __init__(
        self,
        min_touches: int = 2,
        touch_tolerance_pct: float = 0.005
    ):
        self.min_touches = min_touches
        self.touch_tolerance_pct = touch_tolerance_pct
    
    def detect(
        self,
        candles: List[Candle],
        timeframe: str,
        swings: Optional[List[SwingPoint]] = None,
        lookback: int = 50
    ) -> List[PriceRange]:
        """Detect a range from repeated swing boundaries.

        Candle extrema alone cannot prove a range: the latest close is almost
        always inside its own lookback high/low. A structural range therefore
        requires at least two clustered swing highs and two clustered swing
        lows, without both boundaries progressing directionally.
        """
        if not candles or not swings:
            return []

        lookback = min(lookback, len(candles))
        # A structural touch is sparse by definition. Allow up to twice the
        # candle lookback so two high/low cycles are not discarded at the
        # boundary of the window.
        start_index = max(0, len(candles) - lookback * 2)
        recent_swings = sorted(
            (
                swing for swing in swings
                if swing.valid and swing.index >= start_index
            ),
            key=lambda swing: swing.index,
        )
        highs = [swing for swing in recent_swings if swing.kind == "high"][-3:]
        lows = [swing for swing in recent_swings if swing.kind == "low"][-3:]

        if len(highs) < self.min_touches or len(lows) < self.min_touches:
            return []

        candidate_high = max(swing.price for swing in highs)
        candidate_low = min(swing.price for swing in lows)
        width = candidate_high - candidate_low
        if width <= 0:
            return []

        midpoint = (candidate_high + candidate_low) / 2
        cluster_tolerance = max(
            midpoint * self.touch_tolerance_pct,
            width * 0.12,
        )

        high_spread = max(swing.price for swing in highs) - min(swing.price for swing in highs)
        low_spread = max(swing.price for swing in lows) - min(swing.price for swing in lows)
        if high_spread > cluster_tolerance or low_spread > cluster_tolerance:
            return []

        # Reject orderly HH+HL or LH+LL progression. Those are trends, not
        # consolidations, even if all values fit inside a wide candle box.
        if len(highs) >= 2 and len(lows) >= 2:
            high_delta = highs[-1].price - highs[-2].price
            low_delta = lows[-1].price - lows[-2].price
            if (
                high_delta > cluster_tolerance and low_delta > cluster_tolerance
            ) or (
                high_delta < -cluster_tolerance and low_delta < -cluster_tolerance
            ):
                return []
        
        ranges: List[PriceRange] = []
        range_start_index = min(swing.index for swing in [*highs, *lows])
        range_start_index = max(0, min(range_start_index, len(candles) - 1))
        last_candle = candles[-1]
        breakout_buffer = cluster_tolerance * 0.25
        active = (
            candidate_low - breakout_buffer
            <= last_candle.close
            <= candidate_high + breakout_buffer
        )
        equilibrium = midpoint
        duration_candles = len(candles) - range_start_index
        boundary_touches = len(highs) + len(lows)
        strength = self._calculate_strength(
            duration_candles=duration_candles,
            boundary_touches=boundary_touches,
            is_active=active,
            total_candles=len(candles),
        )

        ranges.append(PriceRange(
            id=f"rng_{timeframe}_{range_start_index}_{candles[-1].index}",
            high=candidate_high,
            low=candidate_low,
            equilibrium=equilibrium,
            premium_zone=equilibrium + (candidate_high - equilibrium) * 0.5,
            discount_zone=equilibrium - (equilibrium - candidate_low) * 0.5,
            start_timestamp=candles[range_start_index].timestamp,
            start_index=range_start_index,
            active=active,
            timeframe=timeframe,
            duration_candles=duration_candles,
            boundary_touches=boundary_touches,
            strength=strength,
        ))
        
        return ranges
    
    def _calculate_strength(
        self,
        duration_candles: int,
        boundary_touches: int,
        is_active: bool,
        total_candles: int
    ) -> float:
        """Calculate strength score (0-1) for range.
        
        Factors:
        - Duration relative to lookback (longer = 0.3)
        - Boundary touches (more = 0.4, capped at 10)
        - Active status (0.3)
        """
        strength = 0.0
        
        # Duration factor (0-0.3)
        if total_candles > 0:
            duration_ratio = min(1.0, duration_candles / 50)  # Cap at 50 candles
            strength += duration_ratio * 0.3
        
        # Touch factor (0-0.4)
        touch_score = min(1.0, boundary_touches / 10)  # Cap at 10 touches
        strength += touch_score * 0.4
        
        # Active factor (0-0.3)
        if is_active:
            strength += 0.3
        
        return min(1.0, strength)
    
    def _count_touches(
        self,
        candles: List[Candle],
        level: float,
        level_type: str
    ) -> int:
        """Count touches of a price level."""
        tolerance = level * self.touch_tolerance_pct
        touches = 0
        
        for c in candles:
            if level_type == "high":
                if abs(c.high - level) <= tolerance:
                    touches += 1
            else:
                if abs(c.low - level) <= tolerance:
                    touches += 1
        
        return touches


def detect_ranges(
    candles: List[Candle],
    timeframe: str,
    swings: Optional[List[SwingPoint]] = None,
) -> List[PriceRange]:
    """Functional API for range detection."""
    detector = RangeDetector()
    return detector.detect(candles, timeframe, swings=swings)


# =============================================================================
# Range Position Detection (Premium/Discount/Equilibrium)
# =============================================================================
from backend.chart.engines.core.schemas.range_position import RangePosition


def detect_range_position(
    current_price: float,
    external_high: Optional['SwingPoint'] = None,
    external_low: Optional['SwingPoint'] = None,
    swings: Optional[List['SwingPoint']] = None,
    range_high: Optional[float] = None,
    range_low: Optional[float] = None,
) -> RangePosition:
    """Detect current price position within the external range.
    
    Args:
        current_price: Current market price
        external_high: Highest external swing (if pre-computed)
        external_low: Lowest external swing (if pre-computed)
        swings: All swings (fallback if external_high/low not provided)
        
    Returns:
        RangePosition with zone classification
    """
    # Prefer the active detected range, then structural swing boundaries.
    if range_high is not None:
        high_price = range_high
    elif external_high:
        high_price = external_high.price
    elif swings:
        highs = [s for s in swings if s.kind == 'high']
        high_price = max(s.price for s in highs) if highs else 0.0
    else:
        high_price = 0.0
    
    # Get low price
    if range_low is not None:
        low_price = range_low
    elif external_low:
        low_price = external_low.price
    elif swings:
        lows = [s for s in swings if s.kind == 'low']
        low_price = min(s.price for s in lows) if lows else 0.0
    else:
        low_price = 0.0
    
    # Use the factory method
    return RangePosition.from_prices(current_price, high_price, low_price)
