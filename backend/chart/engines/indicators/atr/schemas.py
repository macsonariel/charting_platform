"""ATR Schemas - Data contracts for ATR indicator."""

from dataclasses import dataclass
from enum import Enum


class ATRTrend(str, Enum):
    """ATR trend direction."""
    EXPANDING = "expanding"     # Volatility increasing
    CONTRACTING = "contracting" # Volatility decreasing
    STABLE = "stable"           # Volatility unchanged


@dataclass
class ATRReading:
    """ATR (Average True Range) reading at a point in time.
    
    ATR measures volatility - higher ATR = more volatile market.
    """
    index: int
    timestamp: int
    value: float              # ATR value (in price units)
    
    # Relative measures
    atr_percent: float = 0.0      # ATR as % of price
    percentile: float = 0.5       # Where current ATR sits historically (0-1)
    
    # Trend
    trend: ATRTrend = ATRTrend.STABLE
    
    # Volatility classification
    is_high_volatility: bool = False   # Above 70th percentile
    is_low_volatility: bool = False    # Below 30th percentile
    is_squeeze: bool = False           # Very low (below 20th percentile)
    
    # Trading implications
    stop_loss_distance: float = 0.0    # Suggested SL based on ATR (1.5x ATR)
    take_profit_distance: float = 0.0  # Suggested TP based on ATR (2x ATR)
