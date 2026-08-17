"""Price Behavior - Rejections and compression detection.

Analyzes:
- Price rejections at key levels
- Price compression (volatility squeeze)

Note: Volume and Momentum are now in their own folders.
"""

from dataclasses import dataclass, field
from typing import List, Tuple
from backend.chart.engines.core.schemas import Candle


@dataclass
class Rejection:
    """A price rejection event at a key level."""
    index: int
    timestamp: int
    price_level: float
    rejection_type: str      # "wick_rejection", "close_rejection", "false_break"
    direction: str           # "bullish" (rejected down), "bearish" (rejected up)
    strength: float = 0.5    # 0-1
    wick_size: float = 0.0


@dataclass
class CompressionReading:
    """Price compression (volatility squeeze) analysis."""
    is_compressed: bool = False
    compression_bars: int = 0
    atr: float = 0.0
    atr_percentile: float = 0.5  # Current ATR vs historical (0-1)
    squeeze_strength: float = 0.0  # How tight the compression is (0-1)


class PriceBehaviorAnalyzer:
    """Analyzer for price behavior (rejections and compression)."""
    
    def __init__(self, atr_period: int = 14):
        """Initialize price behavior analyzer.
        
        Args:
            atr_period: Period for ATR calculation
        """
        self.atr_period = atr_period
    
    def detect_rejections(
        self,
        candles: List[Candle],
        key_levels: List[float],
        atr: float = None,
    ) -> List[Rejection]:
        """Detect price rejections at key levels.
        
        Args:
            candles: Candle data
            key_levels: S/R levels to check
            atr: Average True Range (calculated if not provided)
            
        Returns:
            List of rejection events
        """
        if not candles or not key_levels:
            return []
        
        if atr is None:
            atr = self._calculate_atr(candles)
        
        rejections = []
        tolerance = atr * 0.3  # Level proximity tolerance
        
        for i, candle in enumerate(candles):
            for level in key_levels:
                # Check for wick rejection from above (bearish)
                if (candle.high > level - tolerance and 
                    candle.high < level + tolerance and
                    candle.close < level):
                    wick = candle.high - max(candle.open, candle.close)
                    if wick > atr * 0.3:  # Significant wick
                        rejections.append(Rejection(
                            index=i,
                            timestamp=candle.timestamp,
                            price_level=level,
                            rejection_type="wick_rejection",
                            direction="bearish",
                            strength=min(wick / atr, 1.0),
                            wick_size=wick,
                        ))
                
                # Check for wick rejection from below (bullish)
                if (candle.low > level - tolerance and
                    candle.low < level + tolerance and
                    candle.close > level):
                    wick = min(candle.open, candle.close) - candle.low
                    if wick > atr * 0.3:
                        rejections.append(Rejection(
                            index=i,
                            timestamp=candle.timestamp,
                            price_level=level,
                            rejection_type="wick_rejection",
                            direction="bullish",
                            strength=min(wick / atr, 1.0),
                            wick_size=wick,
                        ))
        
        return rejections
    
    def detect_compression(self, candles: List[Candle]) -> CompressionReading:
        """Detect price compression (volatility squeeze).
        
        Args:
            candles: Candle data
            
        Returns:
            CompressionReading with analysis
        """
        if len(candles) < self.atr_period:
            return CompressionReading()
        
        atr = self._calculate_atr(candles)
        atr_percentile = self._atr_percentile(candles, atr)
        
        # Check for compression
        is_compressed, compression_bars = self._check_compression(candles, atr)
        
        # Calculate squeeze strength (lower percentile = tighter squeeze)
        squeeze_strength = 1.0 - atr_percentile if is_compressed else 0.0
        
        return CompressionReading(
            is_compressed=is_compressed,
            compression_bars=compression_bars,
            atr=atr,
            atr_percentile=atr_percentile,
            squeeze_strength=squeeze_strength,
        )
    
    def _calculate_atr(self, candles: List[Candle]) -> float:
        """Calculate Average True Range."""
        if len(candles) < 2:
            return candles[0].high - candles[0].low if candles else 0
        
        tr_values = []
        for i in range(1, min(len(candles), self.atr_period + 1)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i-1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_values.append(tr)
        
        return sum(tr_values) / len(tr_values) if tr_values else 0
    
    def _atr_percentile(self, candles: List[Candle], current_atr: float) -> float:
        """Calculate where current ATR sits historically (0-1)."""
        if len(candles) < self.atr_period * 2:
            return 0.5
        
        atrs = []
        for i in range(self.atr_period, len(candles)):
            window = candles[i-self.atr_period:i]
            tr_sum = 0
            for j in range(1, len(window)):
                tr = max(
                    window[j].high - window[j].low,
                    abs(window[j].high - window[j-1].close),
                    abs(window[j].low - window[j-1].close)
                )
                tr_sum += tr
            atrs.append(tr_sum / len(window))
        
        if not atrs:
            return 0.5
        
        below = sum(1 for a in atrs if a < current_atr)
        return below / len(atrs)
    
    def _check_compression(self, candles: List[Candle], atr: float) -> Tuple[bool, int]:
        """Check if price is in compression."""
        if len(candles) < 10:
            return False, 0
        
        compression_bars = 0
        threshold = atr * 0.5  # Compressed if range < 50% of ATR
        
        for candle in reversed(candles[-20:]):
            if candle.high - candle.low < threshold:
                compression_bars += 1
            else:
                break
        
        is_compressed = compression_bars >= 5
        return is_compressed, compression_bars


def detect_rejections(
    candles: List[Candle],
    key_levels: List[float],
    atr: float = None,
) -> List[Rejection]:
    """Convenience function to detect rejections.
    
    Args:
        candles: Candle data
        key_levels: S/R levels to check
        atr: Average True Range (optional)
        
    Returns:
        List of rejection events
    """
    analyzer = PriceBehaviorAnalyzer()
    return analyzer.detect_rejections(candles, key_levels, atr)


def detect_compression(candles: List[Candle]) -> CompressionReading:
    """Convenience function to detect compression.
    
    Args:
        candles: Candle data
        
    Returns:
        CompressionReading with analysis
    """
    analyzer = PriceBehaviorAnalyzer()
    return analyzer.detect_compression(candles)
