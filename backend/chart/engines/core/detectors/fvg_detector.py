"""FVG Detector - Detect Fair Value Gaps (imbalances).

CONTRACT:
- FACT DETECTION ONLY
- NO interpretation
"""
from typing import List, Optional

from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.liquidity import FairValueGap


def generate_id(prefix: str) -> str:
    import time
    import random
    return f"{prefix}_{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


class FVGDetector:
    """Detect Fair Value Gaps.
    
    FVG = Price imbalance created by rapid movement.
    
    Bullish FVG: Current candle low > 2 candles ago high
    Bearish FVG: Current candle high < 2 candles ago low
    """
    
    def __init__(self, min_gap_atr_ratio: float = 0.1):
        self.min_gap_atr_ratio = min_gap_atr_ratio
    
    def detect(
        self,
        candles: List[Candle],
        timeframe: str
    ) -> List[FairValueGap]:
        """Detect all FVGs in candle sequence."""
        if len(candles) < 3:
            return []
        
        fvgs: List[FairValueGap] = []
        atr = self._calculate_atr(candles)
        min_gap = atr * self.min_gap_atr_ratio
        
        for i in range(2, len(candles)):
            c0 = candles[i - 2]  # First candle
            c1 = candles[i - 1]  # Middle candle (impulse)
            c2 = candles[i]      # Third candle
            
            # Bullish FVG: gap between c0 high and c2 low
            if c2.low > c0.high:
                gap = c2.low - c0.high
                if gap >= min_gap:
                    fvgs.append(FairValueGap(
                        id=generate_id("fvg"),
                        direction="bullish",
                        high=c2.low,
                        low=c0.high,
                        midpoint=(c2.low + c0.high) / 2,
                        timestamp=c1.timestamp,
                        index=i - 1,
                        timeframe=timeframe
                    ))
            
            # Bearish FVG: gap between c0 low and c2 high
            if c2.high < c0.low:
                gap = c0.low - c2.high
                if gap >= min_gap:
                    fvgs.append(FairValueGap(
                        id=generate_id("fvg"),
                        direction="bearish",
                        high=c0.low,
                        low=c2.high,
                        midpoint=(c0.low + c2.high) / 2,
                        timestamp=c1.timestamp,
                        index=i - 1,
                        timeframe=timeframe
                    ))
        
        # Check which FVGs are filled
        fvgs = self._update_fill_status(candles, fvgs)
        
        return fvgs
    
    def _update_fill_status(
        self,
        candles: List[Candle],
        fvgs: List[FairValueGap]
    ) -> List[FairValueGap]:
        """Check if FVGs have been filled."""
        for fvg in fvgs:
            for c in candles:
                if c.timestamp <= fvg.timestamp:
                    continue
                
                if fvg.direction == "bullish":
                    # Filled if price returns to gap
                    if c.low <= fvg.midpoint:
                        fvg.filled = True
                        fill_depth = min(c.low, fvg.high) - fvg.low
                        fvg.fill_percentage = min(1.0, (fill_depth / fvg.size))
                        fvg.fill_timestamp = c.timestamp
                        break
                else:
                    if c.high >= fvg.midpoint:
                        fvg.filled = True
                        fill_depth = fvg.high - max(c.high, fvg.low)
                        fvg.fill_percentage = min(1.0, (fill_depth / fvg.size))
                        fvg.fill_timestamp = c.timestamp
                        break
        
        # Calculate strength for each FVG
        atr = self._calculate_atr(candles)
        total_candles = len(candles)
        for fvg in fvgs:
            fvg.strength = self._calculate_strength(fvg, atr, total_candles)
        
        return fvgs
    
    def _calculate_strength(
        self,
        fvg: FairValueGap,
        atr: float,
        total_candles: int
    ) -> float:
        """Calculate composite strength score (0-1) for FVG.
        
        Factors:
        - Size relative to ATR (larger = stronger, capped at 0.3)
        - Unfilled percentage (100% = 0.4, 0% = 0)
        - Recency (newer = stronger, up to 0.3)
        """
        strength = 0.0
        
        # Size factor (0-0.3): Larger gaps are more significant
        if atr > 0:
            size_ratio = min(fvg.size / atr, 3.0)  # Cap at 3x ATR
            strength += (size_ratio / 3.0) * 0.3
        else:
            strength += 0.15  # Default if no ATR
        
        # Fill factor (0-0.4): Unfilled gaps are stronger
        unfilled = 1.0 - fvg.fill_percentage
        strength += unfilled * 0.4
        
        # Recency factor (0-0.3): Newer gaps are more relevant
        if total_candles > 0:
            age = total_candles - fvg.index
            recency = max(0, 1.0 - (age / total_candles))
            strength += recency * 0.3
        
        return min(1.0, strength)
    
    def _calculate_atr(self, candles: List[Candle], period: int = 14) -> float:
        if len(candles) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, min(len(candles), period + 1)):
            tr = max(
                candles[i].high - candles[i].low,
                abs(candles[i].high - candles[i - 1].close),
                abs(candles[i].low - candles[i - 1].close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0


def detect_fvgs(candles: List[Candle], timeframe: str) -> List[FairValueGap]:
    """Functional API for FVG detection."""
    detector = FVGDetector()
    return detector.detect(candles, timeframe)
