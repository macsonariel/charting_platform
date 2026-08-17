"""MACD Analyzer - Core MACD calculation and analysis logic.

MACD = EMA(fast) - EMA(slow)
Signal = EMA(MACD, signal_period)
Histogram = MACD - Signal
"""

from typing import List, Optional
from backend.chart.engines.core.schemas import Candle
from backend.chart.engines.indicators.macd.schemas import MACDReading, MACDCrossover


class MACDAnalyzer:
    """Analyzer for MACD (Moving Average Convergence Divergence)."""
    
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        """Initialize MACD analyzer.
        
        Args:
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate(self, candles: List[Candle]) -> List[MACDReading]:
        """Calculate MACD for all candles.
        
        Args:
            candles: List of candles with close prices
            
        Returns:
            List of MACDReading for each candle
        """
        if not candles:
            return []
        
        closes = [c.close for c in candles]
        
        # Calculate EMAs
        fast_ema = self._calculate_ema(closes, self.fast_period)
        slow_ema = self._calculate_ema(closes, self.slow_period)
        
        # Calculate MACD line
        macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
        
        # Calculate signal line (EMA of MACD)
        signal_line = self._calculate_ema(macd_line, self.signal_period)
        
        # Calculate histogram
        histogram = [m - s for m, s in zip(macd_line, signal_line)]
        
        readings = []
        prev_reading = None
        
        for i in range(len(candles)):
            macd = macd_line[i]
            signal = signal_line[i]
            hist = histogram[i]
            
            # Determine zones
            is_positive = macd > 0
            is_negative = macd < 0
            
            # Detect crossovers
            is_bullish_cross = False
            is_bearish_cross = False
            
            if prev_reading is not None:
                # Bullish: MACD crosses above signal
                if macd > signal and prev_reading.macd <= prev_reading.signal:
                    is_bullish_cross = True
                # Bearish: MACD crosses below signal
                elif macd < signal and prev_reading.macd >= prev_reading.signal:
                    is_bearish_cross = True
            
            # Histogram direction
            histogram_rising = hist > prev_reading.histogram if prev_reading else False
            histogram_falling = hist < prev_reading.histogram if prev_reading else False
            
            reading = MACDReading(
                index=i,
                timestamp=candles[i].timestamp,
                macd=round(macd, 4),
                signal=round(signal, 4),
                histogram=round(hist, 4),
                is_positive=is_positive,
                is_negative=is_negative,
                is_bullish_cross=is_bullish_cross,
                is_bearish_cross=is_bearish_cross,
                histogram_rising=histogram_rising,
                histogram_falling=histogram_falling,
            )
            
            readings.append(reading)
            prev_reading = reading
        
        return readings
    
    def detect_crossovers(self, candles: List[Candle]) -> List[MACDCrossover]:
        """Detect MACD crossover events.
        
        Args:
            candles: Candle data
            
        Returns:
            List of crossover events
        """
        readings = self.calculate(candles)
        crossovers = []
        
        for reading in readings:
            if reading.is_bullish_cross:
                crossovers.append(MACDCrossover(
                    crossover_type="bullish",
                    index=reading.index,
                    timestamp=reading.timestamp,
                    macd_value=reading.macd,
                    signal_value=reading.signal,
                    strength=min(1.0, abs(reading.histogram) * 10),
                ))
            elif reading.is_bearish_cross:
                crossovers.append(MACDCrossover(
                    crossover_type="bearish",
                    index=reading.index,
                    timestamp=reading.timestamp,
                    macd_value=reading.macd,
                    signal_value=reading.signal,
                    strength=min(1.0, abs(reading.histogram) * 10),
                ))
        
        return crossovers
    
    def get_current(self, candles: List[Candle]) -> Optional[MACDReading]:
        """Get the current (latest) MACD reading.
        
        Args:
            candles: Candle data
            
        Returns:
            Latest MACDReading or None if not enough data
        """
        readings = self.calculate(candles)
        return readings[-1] if readings else None
    
    def _calculate_ema(self, values: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average.
        
        Args:
            values: List of values to smooth
            period: EMA period
            
        Returns:
            List of EMA values
        """
        if not values:
            return []
        
        multiplier = 2.0 / (period + 1)
        ema = [values[0]]  # Start with first value
        
        for i in range(1, len(values)):
            if i < period:
                # Not enough data, use SMA
                ema.append(sum(values[:i+1]) / (i + 1))
            else:
                ema.append((values[i] - ema[-1]) * multiplier + ema[-1])
        
        return ema


def calculate_macd(
    candles: List[Candle],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> List[MACDReading]:
    """Convenience function to calculate MACD.
    
    Args:
        candles: Candle data
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal EMA period
        
    Returns:
        List of MACD readings
    """
    analyzer = MACDAnalyzer(fast_period=fast, slow_period=slow, signal_period=signal)
    return analyzer.calculate(candles)
