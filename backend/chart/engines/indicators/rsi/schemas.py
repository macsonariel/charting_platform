"""RSI Schemas - Data contracts for RSI indicator."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class RSIReading:
    """RSI (Relative Strength Index) reading at a point in time.
    
    RSI ranges from 0-100:
    - > 70: Overbought (potential reversal down)
    - < 30: Oversold (potential reversal up)
    - 50: Neutral/midpoint
    """
    index: int
    timestamp: int
    value: float              # RSI value (0-100)
    
    # Zone classification
    is_overbought: bool = False   # RSI > 70
    is_oversold: bool = False     # RSI < 30
    zone: str = "neutral"         # "overbought", "oversold", "neutral"
    
    # Trend
    direction: str = "neutral"    # "up", "down", "neutral" (based on RSI movement)
    strength: float = 0.0         # Distance from 50 (0-50 scale, normalized to 0-1)


@dataclass
class RSIDivergence:
    """RSI-Price divergence event.
    
    Bullish divergence: Price makes lower low, RSI makes higher low
    Bearish divergence: Price makes higher high, RSI makes lower high
    """
    divergence_type: str          # "bullish", "bearish"
    start_index: int              # First swing point
    end_index: int                # Second swing point
    start_timestamp: int
    end_timestamp: int
    
    # Price data
    price_start: float
    price_end: float
    
    # RSI data
    rsi_start: float
    rsi_end: float
    
    strength: float = 0.5         # Divergence strength (0-1)
    confirmed: bool = False       # If the divergence led to a reversal
