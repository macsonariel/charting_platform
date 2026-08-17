"""RSI Analyzer - Core RSI calculation and analysis logic.

RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss over N periods
"""

from typing import List, Optional, Tuple
from backend.chart.engines.core.schemas import Candle, SwingPoint
from backend.chart.engines.indicators.rsi.schemas import RSIReading, RSIDivergence


class RSIAnalyzer:
    """Analyzer for RSI (Relative Strength Index)."""
    
    def __init__(
        self,
        period: int = 14,
        overbought: float = 70.0,
        oversold: float = 30.0,
    ):
        """Initialize RSI analyzer.
        
        Args:
            period: Lookback period for RSI calculation (default 14)
            overbought: Overbought threshold (default 70)
            oversold: Oversold threshold (default 30)
        """
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def calculate(self, candles: List[Candle]) -> List[RSIReading]:
        """Calculate RSI for all candles.
        
        Args:
            candles: List of candles with close prices
            
        Returns:
            List of RSIReading for each candle (first N-1 will have RSI=50)
        """
        if not candles:
            return []
        
        readings = []
        
        # Calculate price changes
        changes = []
        for i in range(1, len(candles)):
            changes.append(candles[i].close - candles[i-1].close)
        
        # First reading has no RSI (not enough data)
        readings.append(RSIReading(
            index=0,
            timestamp=candles[0].timestamp,
            value=50.0,
            zone="neutral",
            direction="neutral",
            strength=0.0,
        ))
        
        # Calculate RSI using Wilder's smoothing method
        avg_gain = 0.0
        avg_loss = 0.0
        
        for i, change in enumerate(changes):
            candle_index = i + 1
            
            if candle_index < self.period:
                # Not enough data yet, use simple average
                window = changes[:candle_index]
                gains = [c for c in window if c > 0]
                losses = [abs(c) for c in window if c < 0]
                avg_gain = sum(gains) / len(window) if window else 0
                avg_loss = sum(losses) / len(window) if window else 0
            elif candle_index == self.period:
                # First full period - use simple average
                gains = [c for c in changes[:self.period] if c > 0]
                losses = [abs(c) for c in changes[:self.period] if c < 0]
                avg_gain = sum(gains) / self.period
                avg_loss = sum(losses) / self.period
            else:
                # Subsequent periods - use Wilder's smoothing
                gain = max(change, 0)
                loss = abs(min(change, 0))
                avg_gain = (avg_gain * (self.period - 1) + gain) / self.period
                avg_loss = (avg_loss * (self.period - 1) + loss) / self.period
            
            # Calculate RSI
            if avg_loss == 0:
                rsi = 100.0 if avg_gain > 0 else 50.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            
            # Determine zone
            if rsi >= self.overbought:
                zone = "overbought"
                is_overbought = True
                is_oversold = False
            elif rsi <= self.oversold:
                zone = "oversold"
                is_overbought = False
                is_oversold = True
            else:
                zone = "neutral"
                is_overbought = False
                is_oversold = False
            
            # Determine direction from previous RSI
            prev_rsi = readings[-1].value if readings else 50.0
            if rsi > prev_rsi + 1:
                direction = "up"
            elif rsi < prev_rsi - 1:
                direction = "down"
            else:
                direction = "neutral"
            
            # Strength = distance from 50, normalized
            strength = abs(rsi - 50.0) / 50.0
            
            readings.append(RSIReading(
                index=candle_index,
                timestamp=candles[candle_index].timestamp,
                value=round(rsi, 2),
                is_overbought=is_overbought,
                is_oversold=is_oversold,
                zone=zone,
                direction=direction,
                strength=round(strength, 3),
            ))
        
        return readings
    
    def detect_divergence(
        self,
        candles: List[Candle],
        swings: List[SwingPoint],
        lookback: int = 50,
    ) -> List[RSIDivergence]:
        """Detect RSI-price divergences.
        
        Args:
            candles: Candle data
            swings: Swing points for comparison
            lookback: How many candles back to look
            
        Returns:
            List of divergence events
        """
        if len(candles) < self.period + 5 or len(swings) < 2:
            return []
        
        # Calculate RSI
        rsi_readings = self.calculate(candles)
        
        divergences = []
        
        # Get recent swings (within lookback)
        min_index = max(0, len(candles) - lookback)
        recent_lows = [s for s in swings if s.kind == "low" and s.index >= min_index]
        recent_highs = [s for s in swings if s.kind == "high" and s.index >= min_index]
        
        # Check for bullish divergence (lower low in price, higher low in RSI)
        for i in range(1, len(recent_lows)):
            prev_low = recent_lows[i-1]
            curr_low = recent_lows[i]
            
            if curr_low.index >= len(rsi_readings) or prev_low.index >= len(rsi_readings):
                continue
            
            prev_rsi = rsi_readings[prev_low.index].value
            curr_rsi = rsi_readings[curr_low.index].value
            
            # Bullish: price lower, RSI higher
            if curr_low.price < prev_low.price and curr_rsi > prev_rsi:
                strength = min(1.0, (curr_rsi - prev_rsi) / 20.0)
                divergences.append(RSIDivergence(
                    divergence_type="bullish",
                    start_index=prev_low.index,
                    end_index=curr_low.index,
                    start_timestamp=prev_low.timestamp,
                    end_timestamp=curr_low.timestamp,
                    price_start=prev_low.price,
                    price_end=curr_low.price,
                    rsi_start=prev_rsi,
                    rsi_end=curr_rsi,
                    strength=round(strength, 3),
                ))
        
        # Check for bearish divergence (higher high in price, lower high in RSI)
        for i in range(1, len(recent_highs)):
            prev_high = recent_highs[i-1]
            curr_high = recent_highs[i]
            
            if curr_high.index >= len(rsi_readings) or prev_high.index >= len(rsi_readings):
                continue
            
            prev_rsi = rsi_readings[prev_high.index].value
            curr_rsi = rsi_readings[curr_high.index].value
            
            # Bearish: price higher, RSI lower
            if curr_high.price > prev_high.price and curr_rsi < prev_rsi:
                strength = min(1.0, (prev_rsi - curr_rsi) / 20.0)
                divergences.append(RSIDivergence(
                    divergence_type="bearish",
                    start_index=prev_high.index,
                    end_index=curr_high.index,
                    start_timestamp=prev_high.timestamp,
                    end_timestamp=curr_high.timestamp,
                    price_start=prev_high.price,
                    price_end=curr_high.price,
                    rsi_start=prev_rsi,
                    rsi_end=curr_rsi,
                    strength=round(strength, 3),
                ))
        
        return divergences
    
    def get_current(self, candles: List[Candle]) -> Optional[RSIReading]:
        """Get the current (latest) RSI reading.
        
        Args:
            candles: Candle data
            
        Returns:
            Latest RSIReading or None if not enough data
        """
        readings = self.calculate(candles)
        return readings[-1] if readings else None


def calculate_rsi(candles: List[Candle], period: int = 14) -> List[RSIReading]:
    """Convenience function to calculate RSI.
    
    Args:
        candles: Candle data
        period: RSI period (default 14)
        
    Returns:
        List of RSI readings
    """
    analyzer = RSIAnalyzer(period=period)
    return analyzer.calculate(candles)


def detect_rsi_divergence(
    candles: List[Candle],
    swings: List[SwingPoint],
    period: int = 14,
    lookback: int = 50,
) -> List[RSIDivergence]:
    """Convenience function to detect RSI divergence.
    
    Args:
        candles: Candle data
        swings: Swing points
        period: RSI period
        lookback: How far back to look
        
    Returns:
        List of divergence events
    """
    analyzer = RSIAnalyzer(period=period)
    return analyzer.detect_divergence(candles, swings, lookback)
