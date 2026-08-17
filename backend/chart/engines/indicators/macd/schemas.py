"""MACD Schemas - Data contracts for MACD indicator."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MACDReading:
    """MACD (Moving Average Convergence Divergence) reading.
    
    MACD = Fast EMA - Slow EMA (typically 12 - 26)
    Signal = EMA of MACD (typically 9 periods)
    Histogram = MACD - Signal
    """
    index: int
    timestamp: int
    
    macd: float               # MACD line value
    signal: float             # Signal line value  
    histogram: float          # MACD - Signal (bar chart)
    
    # Zone classification
    is_positive: bool = False     # MACD > 0 (bullish momentum)
    is_negative: bool = False     # MACD < 0 (bearish momentum)
    
    # Crossover signals
    is_bullish_cross: bool = False    # MACD crosses above signal
    is_bearish_cross: bool = False    # MACD crosses below signal
    histogram_rising: bool = False    # Histogram increasing
    histogram_falling: bool = False   # Histogram decreasing
    
    # Divergence
    divergence: Optional[str] = None  # "bullish", "bearish", or None


@dataclass
class MACDCrossover:
    """MACD crossover event."""
    crossover_type: str       # "bullish", "bearish"
    index: int
    timestamp: int
    macd_value: float
    signal_value: float
    strength: float = 0.5     # Based on histogram magnitude
    confirmed: bool = False   # If price followed through
