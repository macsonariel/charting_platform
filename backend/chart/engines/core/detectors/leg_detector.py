"""Leg Detector - Detect price legs (impulse vs corrective).

CONTRACT:
- FACT DETECTION ONLY
- NO interpretation

A Leg = Movement from one swing to the next.
"""
from typing import List, Optional
from dataclasses import dataclass

from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.leg import Leg
from backend.chart.engines.core.schemas.candle import Candle


def generate_id(prefix: str) -> str:
    import time
    import random
    return f"{prefix}_{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


class LegDetector:
    """Detect and classify price legs.
    
    Impulse = Strong directional move (expansion)
    Corrective = Counter-directional move (retracement)
    
    Classification based on:
    - Momentum (size / time)
    - Candle overlap ratio
    - Body vs wick ratio
    """
    
    def __init__(
        self,
        impulse_momentum_threshold: float = 0.5,
        max_overlap_ratio: float = 0.4
    ):
        self.impulse_momentum_threshold = impulse_momentum_threshold
        self.max_overlap_ratio = max_overlap_ratio
    
    def detect(
        self,
        candles: List[Candle],
        swings: List[SwingPoint],
        timeframe: str
    ) -> List[Leg]:
        """Detect legs from consecutive swings.
        
        Produces two types of legs:
        - Swing legs (scope="swing"): Every swing-to-swing movement
        - Structural legs (scope="structural"): External/structural-to-structural movements only
        """
        if len(swings) < 2:
            return []
        
        # Calculate ATR for normalization
        atr = self._calculate_atr(candles)
        
        # Detect swing legs (all swings)
        swing_legs = self._detect_legs_from_swings(
            candles, swings, timeframe, atr, scope="swing"
        )
        
        # Detect structural legs (external/structural swings only)
        structural_swings = [s for s in swings if s.degree == "external"]
        structural_legs = self._detect_legs_from_swings(
            candles, structural_swings, timeframe, atr, scope="structural"
        )
        
        # Combine and return
        return swing_legs + structural_legs
    
    def _detect_legs_from_swings(
        self,
        candles: List[Candle],
        swings: List[SwingPoint],
        timeframe: str,
        atr: float,
        scope: str
    ) -> List[Leg]:
        """Detect legs from a list of swings."""
        if len(swings) < 2:
            return []
        
        sorted_swings = sorted(swings, key=lambda s: s.index)
        legs: List[Leg] = []
        
        for i in range(len(sorted_swings) - 1):
            start = sorted_swings[i]
            end = sorted_swings[i + 1]
            
            # Determine direction
            if start.kind == "low" and end.kind == "high":
                direction = "bullish"
            elif start.kind == "high" and end.kind == "low":
                direction = "bearish"
            else:
                continue  # Skip same-type (shouldn't happen with alternation)
            
            # Calculate characteristics
            size = abs(end.price - start.price)
            candle_count = end.index - start.index
            momentum = size / candle_count if candle_count > 0 else 0
            
            # Calculate overlap ratio
            overlap_ratio = self._calculate_overlap(
                candles, start.index, end.index
            )
            
            # Classify leg type
            normalized_momentum = momentum / atr if atr > 0 else 0
            is_impulse = (
                normalized_momentum > self.impulse_momentum_threshold and
                overlap_ratio < self.max_overlap_ratio
            )
            leg_type = "impulse" if is_impulse else "corrective"
            
            legs.append(Leg(
                id=generate_id(f"leg_{scope}"),
                start_swing_id=start.id,
                end_swing_id=end.id,
                start_price=start.price,
                end_price=end.price,
                start_index=start.index,
                end_index=end.index,
                start_timestamp=start.timestamp,
                end_timestamp=end.timestamp,
                direction=direction,
                leg_type=leg_type,
                scope=scope,  # "swing" or "external"
                size=size,
                candle_count=candle_count,
                momentum=momentum,
                overlap_ratio=overlap_ratio,
                timeframe=timeframe
            ))
        
        return legs
    
    def _calculate_atr(self, candles: List[Candle], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(candles) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, min(len(candles), period + 1)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i - 1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
    
    def _calculate_overlap(
        self,
        candles: List[Candle],
        start_idx: int,
        end_idx: int
    ) -> float:
        """Calculate overlap ratio of candles in leg."""
        if end_idx <= start_idx:
            return 0.0
        
        leg_candles = candles[start_idx:end_idx + 1]
        if len(leg_candles) < 2:
            return 0.0
        
        overlap_count = 0
        for i in range(1, len(leg_candles)):
            prev = leg_candles[i - 1]
            curr = leg_candles[i]
            
            # Check if bodies overlap
            prev_body_high = max(prev.open, prev.close)
            prev_body_low = min(prev.open, prev.close)
            curr_body_high = max(curr.open, curr.close)
            curr_body_low = min(curr.open, curr.close)
            
            if curr_body_low < prev_body_high and curr_body_high > prev_body_low:
                overlap_count += 1
        
        return overlap_count / (len(leg_candles) - 1)


def detect_legs(
    candles: List[Candle],
    swings: List[SwingPoint],
    timeframe: str
) -> List[Leg]:
    """Functional API for leg detection."""
    detector = LegDetector()
    return detector.detect(candles, swings, timeframe)
