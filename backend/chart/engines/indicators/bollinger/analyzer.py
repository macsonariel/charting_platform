"""Bollinger Bands Analyzer - Core Bollinger Bands calculation logic.

Upper Band = SMA(close, period) + (std_dev(close, period) * multiplier)
Lower Band = SMA(close, period) - (std_dev(close, period) * multiplier)
%B = (close - lower) / (upper - lower)
Bandwidth = (upper - lower) / middle * 100
"""

from typing import List, Optional
import math
from backend.chart.engines.core.schemas import Candle
from backend.chart.engines.indicators.bollinger.schemas import BollingerReading, BollingerSqueeze


class BollingerAnalyzer:
    """Analyzer for Bollinger Bands."""
    
    def __init__(
        self,
        period: int = 20,
        std_dev_multiplier: float = 2.0,
        squeeze_threshold: float = 4.0,  # Bandwidth % below this = squeeze
    ):
        """Initialize Bollinger Bands analyzer.
        
        Args:
            period: SMA period (default 20)
            std_dev_multiplier: Standard deviation multiplier (default 2.0)
            squeeze_threshold: Bandwidth % below this indicates squeeze
        """
        self.period = period
        self.std_dev_multiplier = std_dev_multiplier
        self.squeeze_threshold = squeeze_threshold
    
    def calculate(self, candles: List[Candle]) -> List[BollingerReading]:
        """Calculate Bollinger Bands for all candles.
        
        Args:
            candles: List of candles with close prices
            
        Returns:
            List of BollingerReading for each candle
        """
        if not candles:
            return []
        
        closes = [c.close for c in candles]
        readings = []
        
        # Track historical bandwidths for percentile comparison
        all_bandwidths = []
        
        for i in range(len(candles)):
            if i < self.period - 1:
                # Not enough data, use available data
                window = closes[:i+1]
            else:
                window = closes[i-self.period+1:i+1]
            
            # Calculate SMA (middle band)
            middle = sum(window) / len(window)
            
            # Calculate standard deviation
            variance = sum((p - middle) ** 2 for p in window) / len(window)
            std_dev = math.sqrt(variance)
            
            # Calculate bands
            upper = middle + (std_dev * self.std_dev_multiplier)
            lower = middle - (std_dev * self.std_dev_multiplier)
            
            # Calculate %B
            band_range = upper - lower
            if band_range > 0:
                percent_b = (candles[i].close - lower) / band_range
            else:
                percent_b = 0.5
            
            # Calculate bandwidth as percentage of middle
            bandwidth = (band_range / middle) * 100 if middle > 0 else 0
            all_bandwidths.append(bandwidth)
            
            # Determine squeeze/expansion based on historical percentile
            if len(all_bandwidths) > 20:
                bandwidth_percentile = sum(1 for b in all_bandwidths[:-1] if b < bandwidth) / (len(all_bandwidths) - 1)
            else:
                bandwidth_percentile = 0.5
            
            is_squeeze = bandwidth < self.squeeze_threshold or bandwidth_percentile < 0.2
            is_expansion = bandwidth_percentile > 0.8
            
            # Classification
            price = candles[i].close
            is_above_upper = price > upper
            is_below_lower = price < lower
            
            # Band touch detection
            touch_threshold = band_range * 0.02  # Within 2% of band
            if abs(price - upper) <= touch_threshold:
                band_touch = "upper"
            elif abs(price - lower) <= touch_threshold:
                band_touch = "lower"
            else:
                band_touch = None
            
            reading = BollingerReading(
                index=i,
                timestamp=candles[i].timestamp,
                upper=round(upper, 4),
                middle=round(middle, 4),
                lower=round(lower, 4),
                percent_b=round(percent_b, 4),
                bandwidth=round(bandwidth, 4),
                is_above_upper=is_above_upper,
                is_below_lower=is_below_lower,
                is_squeeze=is_squeeze,
                is_expansion=is_expansion,
                band_touch=band_touch,
            )
            readings.append(reading)
        
        return readings
    
    def detect_squeezes(self, candles: List[Candle]) -> List[BollingerSqueeze]:
        """Detect Bollinger Band squeeze events.
        
        A squeeze is when bandwidth contracts significantly,
        often preceding a volatility expansion/breakout.
        
        Args:
            candles: Candle data
            
        Returns:
            List of squeeze events
        """
        readings = self.calculate(candles)
        squeezes = []
        
        in_squeeze = False
        squeeze_start = None
        squeeze_min_bw = float('inf')
        
        for i, reading in enumerate(readings):
            if reading.is_squeeze:
                if not in_squeeze:
                    # Start of new squeeze
                    in_squeeze = True
                    squeeze_start = i
                    squeeze_min_bw = reading.bandwidth
                else:
                    squeeze_min_bw = min(squeeze_min_bw, reading.bandwidth)
            else:
                if in_squeeze and squeeze_start is not None:
                    # End of squeeze
                    # Determine breakout direction
                    if i > 0:
                        prev_close = candles[i-1].close
                        curr_close = candles[i].close
                        if curr_close > prev_close:
                            direction = "up"
                        elif curr_close < prev_close:
                            direction = "down"
                        else:
                            direction = None
                    else:
                        direction = None
                    
                    squeezes.append(BollingerSqueeze(
                        start_index=squeeze_start,
                        end_index=i-1,
                        start_timestamp=candles[squeeze_start].timestamp,
                        end_timestamp=candles[i-1].timestamp,
                        duration=i - squeeze_start,
                        min_bandwidth=round(squeeze_min_bw, 4),
                        breakout_direction=direction,
                    ))
                    
                    in_squeeze = False
                    squeeze_start = None
                    squeeze_min_bw = float('inf')
        
        return squeezes
    
    def get_current(self, candles: List[Candle]) -> Optional[BollingerReading]:
        """Get the current (latest) Bollinger Bands reading.
        
        Args:
            candles: Candle data
            
        Returns:
            Latest BollingerReading or None
        """
        readings = self.calculate(candles)
        return readings[-1] if readings else None


def calculate_bollinger(
    candles: List[Candle],
    period: int = 20,
    std_dev: float = 2.0,
) -> List[BollingerReading]:
    """Convenience function to calculate Bollinger Bands.
    
    Args:
        candles: Candle data
        period: SMA period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
        
    Returns:
        List of Bollinger Bands readings
    """
    analyzer = BollingerAnalyzer(period=period, std_dev_multiplier=std_dev)
    return analyzer.calculate(candles)
