"""Bollinger Bands Schemas - Data contracts for Bollinger Bands indicator."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BollingerReading:
    """Bollinger Bands reading at a point in time.
    
    Upper Band = SMA + (std_dev * multiplier)
    Lower Band = SMA - (std_dev * multiplier)
    Middle Band = SMA
    
    %B tells you where price is relative to the bands:
    - %B > 1.0: Price above upper band
    - %B = 1.0: Price at upper band
    - %B = 0.5: Price at middle
    - %B = 0.0: Price at lower band
    - %B < 0.0: Price below lower band
    
    Bandwidth measures volatility:
    - High bandwidth = high volatility
    - Low bandwidth = squeeze (potential breakout)
    """
    index: int
    timestamp: int
    
    upper: float              # Upper band
    middle: float             # Middle band (SMA)
    lower: float              # Lower band
    
    # Derived measures
    percent_b: float = 0.5    # Where price is in the bands (0-1+)
    bandwidth: float = 0.0    # Band width as % of middle
    
    # Classification
    is_above_upper: bool = False    # Price > upper band
    is_below_lower: bool = False    # Price < lower band
    is_squeeze: bool = False        # Low bandwidth (potential breakout)
    is_expansion: bool = False      # High bandwidth
    
    # Trading signals
    band_touch: Optional[str] = None  # "upper", "lower", or None


@dataclass
class BollingerSqueeze:
    """Bollinger Bands squeeze event (low volatility)."""
    start_index: int
    end_index: int
    start_timestamp: int
    end_timestamp: int
    duration: int             # Number of bars in squeeze
    min_bandwidth: float      # Minimum bandwidth during squeeze
    breakout_direction: Optional[str] = None  # "up", "down", or None if ongoing
