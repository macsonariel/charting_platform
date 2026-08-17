"""Candle - Base price data model."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Candle:
    """Single candlestick data point.
    
    This is the fundamental unit of price data.
    All detection and analysis starts from candles.
    """
    timestamp: int          # Unix timestamp in milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    index: int = 0          # Candle index in sequence
    
    @property
    def spread(self) -> float:
        """Candle range (high - low)."""
        return self.high - self.low
    
    @property
    def body(self) -> float:
        """Candle body size (abs of open - close)."""
        return abs(self.close - self.open)
    
    @property
    def is_bullish(self) -> bool:
        """True if close > open."""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """True if close < open."""
        return self.close < self.open
    
    @property
    def upper_wick(self) -> float:
        """Upper wick size."""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        """Lower wick size."""
        return min(self.open, self.close) - self.low
