"""ATR Analyzer - Core ATR calculation and analysis logic.

ATR = Average of True Range over N periods
True Range = max(high-low, |high-prev_close|, |low-prev_close|)
"""

from typing import List, Optional
from backend.chart.engines.core.schemas import Candle
from backend.chart.engines.indicators.atr.schemas import ATRReading, ATRTrend


class ATRAnalyzer:
    """Analyzer for ATR (Average True Range)."""
    
    def __init__(
        self,
        period: int = 14,
        sl_multiplier: float = 1.5,
        tp_multiplier: float = 2.0,
    ):
        """Initialize ATR analyzer.
        
        Args:
            period: ATR calculation period (default 14)
            sl_multiplier: Stop loss multiplier for ATR
            tp_multiplier: Take profit multiplier for ATR
        """
        self.period = period
        self.sl_multiplier = sl_multiplier
        self.tp_multiplier = tp_multiplier
    
    def calculate(self, candles: List[Candle]) -> List[ATRReading]:
        """Calculate ATR for all candles.
        
        Args:
            candles: List of candles with OHLC data
            
        Returns:
            List of ATRReading for each candle
        """
        if not candles:
            return []
        
        # Calculate True Range for each candle
        tr_values = []
        for i, candle in enumerate(candles):
            if i == 0:
                # First candle: TR = high - low
                tr = candle.high - candle.low
            else:
                prev_close = candles[i-1].close
                tr = max(
                    candle.high - candle.low,
                    abs(candle.high - prev_close),
                    abs(candle.low - prev_close)
                )
            tr_values.append(tr)
        
        # Calculate ATR using Wilder's smoothing
        atr_values = []
        for i in range(len(candles)):
            if i < self.period:
                # Not enough data, use simple average
                atr = sum(tr_values[:i+1]) / (i + 1)
            elif i == self.period:
                # First full period
                atr = sum(tr_values[:self.period]) / self.period
            else:
                # Wilder's smoothing
                atr = (atr_values[-1] * (self.period - 1) + tr_values[i]) / self.period
            atr_values.append(atr)
        
        # Calculate historical ATR percentiles for comparison
        readings = []
        
        for i in range(len(candles)):
            atr = atr_values[i]
            price = candles[i].close
            
            # Calculate percentile (where this ATR sits historically)
            window_start = max(0, i - 100)
            historical_atrs = atr_values[window_start:i+1]
            
            if len(historical_atrs) > 1:
                below_count = sum(1 for a in historical_atrs[:-1] if a < atr)
                percentile = below_count / (len(historical_atrs) - 1)
            else:
                percentile = 0.5
            
            # Determine trend
            if i >= 3:
                prev_atr = atr_values[i-3]
                if atr > prev_atr * 1.1:
                    trend = ATRTrend.EXPANDING
                elif atr < prev_atr * 0.9:
                    trend = ATRTrend.CONTRACTING
                else:
                    trend = ATRTrend.STABLE
            else:
                trend = ATRTrend.STABLE
            
            # Volatility classification
            is_high = percentile > 0.7
            is_low = percentile < 0.3
            is_squeeze = percentile < 0.2
            
            reading = ATRReading(
                index=i,
                timestamp=candles[i].timestamp,
                value=round(atr, 4),
                atr_percent=round((atr / price) * 100, 4) if price > 0 else 0,
                percentile=round(percentile, 3),
                trend=trend,
                is_high_volatility=is_high,
                is_low_volatility=is_low,
                is_squeeze=is_squeeze,
                stop_loss_distance=round(atr * self.sl_multiplier, 4),
                take_profit_distance=round(atr * self.tp_multiplier, 4),
            )
            readings.append(reading)
        
        return readings
    
    def get_current(self, candles: List[Candle]) -> Optional[ATRReading]:
        """Get the current (latest) ATR reading.
        
        Args:
            candles: Candle data
            
        Returns:
            Latest ATRReading or None
        """
        readings = self.calculate(candles)
        return readings[-1] if readings else None


def calculate_atr(candles: List[Candle], period: int = 14) -> List[ATRReading]:
    """Convenience function to calculate ATR.
    
    Args:
        candles: Candle data
        period: ATR period (default 14)
        
    Returns:
        List of ATR readings
    """
    analyzer = ATRAnalyzer(period=period)
    return analyzer.calculate(candles)
