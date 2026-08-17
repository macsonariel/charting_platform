"""Momentum Analyzer - Core momentum analysis logic.

Analyzes:
- Rate of change (ROC)
- Momentum direction and strength
- Acceleration/deceleration
- Price-momentum divergence
"""

from typing import List, Optional
from backend.chart.engines.core.schemas import Candle, SwingPoint
from backend.chart.engines.indicators.momentum.schemas import (
    MomentumReading,
    MomentumDivergence,
)


class MomentumAnalyzer:
    """Analyzer for price momentum."""
    
    def __init__(
        self,
        period: int = 10,
        smoothing_period: int = 3,
        overbought_threshold: float = 0.8,
        oversold_threshold: float = 0.2,
    ):
        """Initialize momentum analyzer.
        
        Args:
            period: Lookback period for ROC calculation
            smoothing_period: Period for smoothing ROC
            overbought_threshold: Percentile for overbought (0-1)
            oversold_threshold: Percentile for oversold (0-1)
        """
        self.period = period
        self.smoothing_period = smoothing_period
        self.overbought_threshold = overbought_threshold
        self.oversold_threshold = oversold_threshold
    
    def analyze(self, candles: List[Candle]) -> MomentumReading:
        """Analyze momentum for the given candles.
        
        Args:
            candles: List of candles to analyze
            
        Returns:
            MomentumReading with analysis
        """
        if len(candles) < self.period:
            return MomentumReading()
        
        # Calculate ROC
        roc = self._calculate_roc(candles)
        roc_smoothed = self._calculate_smoothed_roc(candles)
        
        # Determine direction and strength
        direction, strength = self._determine_direction(roc)
        
        # Check acceleration
        is_accelerating, is_decelerating, accel_rate = self._check_acceleration(candles)
        
        # Check for extremes (overbought/oversold)
        is_overbought, is_oversold = self._check_extremes(candles, roc)
        
        return MomentumReading(
            direction=direction,
            strength=strength,
            roc=roc,
            roc_smoothed=roc_smoothed,
            is_accelerating=is_accelerating,
            is_decelerating=is_decelerating,
            acceleration_rate=accel_rate,
            divergence=MomentumDivergence.NONE,  # Set separately via detect_divergence
            is_overbought=is_overbought,
            is_oversold=is_oversold,
        )
    
    def detect_divergence(
        self,
        candles: List[Candle],
        swings: List[SwingPoint],
        lookback: int = 20,
    ) -> tuple[MomentumDivergence, float]:
        """Detect momentum-price divergence using swing points.
        
        Args:
            candles: Candle data
            swings: Swing points for comparison
            lookback: How many candles back to look
            
        Returns:
            Tuple of (divergence type, strength)
        """
        if len(candles) < lookback or len(swings) < 2:
            return MomentumDivergence.NONE, 0.0
        
        # Get recent swing highs and lows
        recent_swings = [s for s in swings if s.index >= len(candles) - lookback]
        
        highs = sorted([s for s in recent_swings if s.kind == "high"], key=lambda s: s.index)
        lows = sorted([s for s in recent_swings if s.kind == "low"], key=lambda s: s.index)
        
        # Check for bullish divergence (price lower low, momentum higher low)
        if len(lows) >= 2:
            prev_low = lows[-2]
            curr_low = lows[-1]
            
            # Get momentum at each low
            prev_mom = self._get_roc_at_index(candles, prev_low.index)
            curr_mom = self._get_roc_at_index(candles, curr_low.index)
            
            if curr_low.price < prev_low.price and curr_mom > prev_mom:
                strength = min(abs(curr_mom - prev_mom) / 0.05, 1.0)
                return MomentumDivergence.BULLISH, strength
            
            # Hidden bullish (trend continuation)
            if curr_low.price > prev_low.price and curr_mom < prev_mom:
                strength = min(abs(curr_mom - prev_mom) / 0.05, 1.0)
                return MomentumDivergence.HIDDEN_BULLISH, strength
        
        # Check for bearish divergence (price higher high, momentum lower high)
        if len(highs) >= 2:
            prev_high = highs[-2]
            curr_high = highs[-1]
            
            prev_mom = self._get_roc_at_index(candles, prev_high.index)
            curr_mom = self._get_roc_at_index(candles, curr_high.index)
            
            if curr_high.price > prev_high.price and curr_mom < prev_mom:
                strength = min(abs(curr_mom - prev_mom) / 0.05, 1.0)
                return MomentumDivergence.BEARISH, strength
            
            # Hidden bearish (trend continuation)
            if curr_high.price < prev_high.price and curr_mom > prev_mom:
                strength = min(abs(curr_mom - prev_mom) / 0.05, 1.0)
                return MomentumDivergence.HIDDEN_BEARISH, strength
        
        return MomentumDivergence.NONE, 0.0
    
    def _calculate_roc(self, candles: List[Candle]) -> float:
        """Calculate Rate of Change."""
        if len(candles) < self.period:
            return 0.0
        
        current = candles[-1].close
        past = candles[-self.period].close
        
        return (current - past) / past if past > 0 else 0.0
    
    def _calculate_smoothed_roc(self, candles: List[Candle]) -> float:
        """Calculate smoothed ROC using SMA."""
        if len(candles) < self.period + self.smoothing_period:
            return self._calculate_roc(candles)
        
        rocs = []
        for i in range(self.smoothing_period):
            idx = len(candles) - i - 1
            if idx >= self.period:
                current = candles[idx].close
                past = candles[idx - self.period].close
                roc = (current - past) / past if past > 0 else 0.0
                rocs.append(roc)
        
        return sum(rocs) / len(rocs) if rocs else 0.0
    
    def _get_roc_at_index(self, candles: List[Candle], index: int) -> float:
        """Calculate ROC at a specific candle index."""
        if index < self.period or index >= len(candles):
            return 0.0
        
        current = candles[index].close
        past = candles[index - self.period].close
        
        return (current - past) / past if past > 0 else 0.0
    
    def _determine_direction(self, roc: float) -> tuple[str, float]:
        """Determine momentum direction and strength from ROC."""
        # Normalize ROC to strength (0-1)
        # Typical ROC range is -10% to +10% for most timeframes
        strength = min(abs(roc) / 0.05, 1.0)  # 5% = full strength
        
        if roc > 0.01:  # 1% threshold
            return "bullish", strength
        elif roc < -0.01:
            return "bearish", strength
        else:
            return "neutral", strength
    
    def _check_acceleration(self, candles: List[Candle]) -> tuple[bool, bool, float]:
        """Check if momentum is accelerating or decelerating."""
        if len(candles) < self.period * 2:
            return False, False, 0.0
        
        # Compare ROC of first half vs second half
        mid = len(candles) // 2
        
        first_half = candles[:mid]
        second_half = candles[mid:]
        
        if len(first_half) >= self.period and len(second_half) >= self.period:
            roc_first = self._calculate_roc(first_half)
            roc_second = self._calculate_roc(second_half)
            
            accel_rate = abs(roc_second - roc_first)
            
            # Same sign and second is larger = accelerating
            if roc_first * roc_second > 0:  # Same sign
                if abs(roc_second) > abs(roc_first) * 1.2:
                    return True, False, accel_rate
                elif abs(roc_second) < abs(roc_first) * 0.8:
                    return False, True, accel_rate
            
            return False, False, accel_rate
        
        return False, False, 0.0
    
    def _check_extremes(self, candles: List[Candle], current_roc: float) -> tuple[bool, bool]:
        """Check if momentum is at overbought/oversold extremes."""
        if len(candles) < 50:
            return False, False
        
        # Calculate historical ROC values
        rocs = []
        for i in range(self.period, len(candles)):
            roc = self._get_roc_at_index(candles, i)
            rocs.append(roc)
        
        if not rocs:
            return False, False
        
        # Find percentile of current ROC
        below = sum(1 for r in rocs if r < current_roc)
        percentile = below / len(rocs)
        
        is_overbought = percentile > self.overbought_threshold
        is_oversold = percentile < self.oversold_threshold
        
        return is_overbought, is_oversold


def calculate_momentum(candles: List[Candle], period: int = 10) -> MomentumReading:
    """Convenience function to calculate momentum.
    
    Args:
        candles: Candle data
        period: Lookback period
        
    Returns:
        MomentumReading with analysis
    """
    analyzer = MomentumAnalyzer(period=period)
    return analyzer.analyze(candles)


def detect_momentum_divergence(
    candles: List[Candle],
    swings: List[SwingPoint],
    period: int = 10,
    lookback: int = 20,
) -> tuple[MomentumDivergence, float]:
    """Convenience function to detect momentum divergence.
    
    Args:
        candles: Candle data
        swings: Swing points for comparison
        period: Momentum period
        lookback: How far back to look for swings
        
    Returns:
        Tuple of (divergence type, strength)
    """
    analyzer = MomentumAnalyzer(period=period)
    return analyzer.detect_divergence(candles, swings, lookback)

