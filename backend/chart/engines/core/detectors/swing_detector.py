"""Swing Detector - Detect raw swing points.

CONTRACT:
- FACT DETECTION ONLY
- NO interpretation
- NO phase decisions
"""
from dataclasses import dataclass
from typing import List, Optional

from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.swing import SwingPoint


def generate_id(prefix: str) -> str:
    """Generate unique ID."""
    import time
    import random
    return f"{prefix}_{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


@dataclass
class SwingDetectorConfig:
    """Configuration for swing detection."""
    lookback: int = 3           # Candles to look back/forward
    min_swing_size: float = 0.0 # Minimum swing size (0 = no limit)


class SwingDetector:
    """Detect swing highs and lows from candles.
    
    CONTRACT: DETECT ONLY
    - Input: Candles
    - Output: SwingPoint list
    - NO interpretation of what swings mean
    """
    
    def __init__(self, config: Optional[SwingDetectorConfig] = None):
        self.config = config or SwingDetectorConfig()
    
    def detect(
        self,
        candles: List[Candle],
        timeframe: str
    ) -> List[SwingPoint]:
        """Detect all swing points with enforced alternation."""
        if len(candles) < (self.config.lookback * 2 + 1):
            return []
        
        swings: List[SwingPoint] = []
        lookback = self.config.lookback
        
        for i in range(lookback, len(candles) - lookback):
            # Check swing high
            if self._is_swing_high(candles, i, lookback):
                swings.append(SwingPoint(
                    id=generate_id("sw_h"),
                    index=i,
                    timestamp=candles[i].timestamp,
                    price=candles[i].high,
                    kind="high",
                    degree="internal",  # Default to internal, HTF classifier sets external
                    strength=0.0,
                    timeframe=timeframe
                ))
            
            # Check swing low
            if self._is_swing_low(candles, i, lookback):
                swings.append(SwingPoint(
                    id=generate_id("sw_l"),
                    index=i,
                    timestamp=candles[i].timestamp,
                    price=candles[i].low,
                    kind="low",
                    degree="internal",  # Default to internal, HTF classifier sets external
                    strength=0.0,
                    timeframe=timeframe
                ))
        
        # Enforce alternation: H-L-H-L pattern
        return self._enforce_alternation(swings)
    
    def _enforce_alternation(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """Enforce H-L-H-L alternation by keeping most extreme when consecutive same types.
        
        When we have consecutive swings of the same type:
        - For highs: keep the highest one
        - For lows: keep the lowest one
        
        This ensures structure is always H, L, H, L, etc.
        """
        if len(swings) <= 1:
            return swings
        
        # Sort by index first
        swings = sorted(swings, key=lambda s: s.index)
        
        result: List[SwingPoint] = []
        
        for swing in swings:
            if not result:
                result.append(swing)
                continue
            
            last = result[-1]
            
            if swing.kind == last.kind:
                # Same type as last - keep the more extreme one
                if swing.kind == "high":
                    # Keep the higher high
                    if swing.price > last.price:
                        result[-1] = swing
                    # else: keep the existing one (it's higher)
                else:  # swing.kind == "low"
                    # Keep the lower low
                    if swing.price < last.price:
                        result[-1] = swing
                    # else: keep the existing one (it's lower)
            else:
                # Different type - add it (this maintains alternation)
                result.append(swing)
        
        return result
    
    def _is_swing_high(
        self,
        candles: List[Candle],
        index: int,
        lookback: int
    ) -> bool:
        """Check if candle at index is a swing high."""
        current = candles[index].high
        
        for i in range(1, lookback + 1):
            if candles[index - i].high >= current:
                return False
            if candles[index + i].high >= current:
                return False
        
        return True
    
    def _is_swing_low(
        self,
        candles: List[Candle],
        index: int,
        lookback: int
    ) -> bool:
        """Check if candle at index is a swing low."""
        current = candles[index].low
        
        for i in range(1, lookback + 1):
            if candles[index - i].low <= current:
                return False
            if candles[index + i].low <= current:
                return False
        
        return True


def detect_swings(
    candles: List[Candle],
    timeframe: str,
    config: Optional[SwingDetectorConfig] = None
) -> List[SwingPoint]:
    """Functional API for swing detection with enforced alternation."""
    detector = SwingDetector(config)
    return detector.detect(candles, timeframe)
