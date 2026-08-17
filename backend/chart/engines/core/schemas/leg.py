"""Leg - Price movement between swings.

A Leg = Movement from one swing to the next swing.
- Swing Low → Swing High = Bullish leg
- Swing High → Swing Low = Bearish leg

Types:
- ImpulseLeg: Strong directional move (expansion)
- CorrectiveLeg: Counter-directional move (retracement)
"""
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class LegType(str, Enum):
    """Classification of leg behavior."""
    IMPULSE = "impulse"         # Expansion, displacement
    CORRECTIVE = "corrective"   # Pullback, retracement


class LegDirection(str, Enum):
    """Direction of price movement."""
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class Leg:
    """A price leg - movement between two swings.
    
    Legs are the building blocks of trends and ranges.
    Almost all higher-level concepts are built from legs:
    - HH/HL/LL/LH patterns
    - BOS/CHoCH events
    - Trends and ranges
    - Pullbacks and continuations
    
    Scope:
    - "swing": Movement between any consecutive swings (granular)
    - "structural": Movement between external/structural swings only (HTF structure)
    
    Status:
    - "complete": Both start and end swings are confirmed
    - "developing": End swing is current price (not yet confirmed)
    """
    id: str
    start_swing_id: str                  # Starting swing point
    end_swing_id: Optional[str] = None   # Ending swing (None if developing)
    start_price: float = 0.0
    end_price: float = 0.0
    start_index: int = 0
    end_index: int = 0
    start_timestamp: int = 0
    end_timestamp: int = 0
    high_price: float = 0.0              # Highest price within leg (for visualization)
    low_price: float = 0.0               # Lowest price within leg (for visualization)
    direction: str = ""                  # "bullish" or "bearish"
    leg_type: str = "impulse"            # "impulse", "corrective", "consolidation", "compression", "post_sweep"
    scope: str = "swing"                 # "swing" (any swing) or "structural" (external swings only)
    status: str = "complete"             # "complete" or "developing"
    
    # Characteristics
    size: float = 0.0           # Price distance
    candle_count: int = 0       # Number of candles
    momentum: float = 0.0       # Speed of move (size / candles)
    overlap_ratio: float = 0.0  # How much candles overlap
    
    # Enhanced metrics
    retracement_depth: float = 0.0   # 0.0-1.0 of previous leg
    candle_aggression: float = 0.0   # Ratio of body to total range (0-1)
    impulse_correction_ratio: float = 0.0  # Impulse moves vs corrections inside
    
    # Internal structure
    internal_swings: int = 0    # Swing points inside leg
    internal_breaks: int = 0    # Structure breaks inside leg
    
    timeframe: str = ""
    
    def __post_init__(self):
        """Calculate derived properties."""
        self.size = abs(self.end_price - self.start_price)
        self.candle_count = self.end_index - self.start_index
        if self.candle_count > 0:
            self.momentum = self.size / self.candle_count
        
        # Set high/low if not explicitly provided
        if self.high_price == 0.0:
            self.high_price = max(self.start_price, self.end_price)
        if self.low_price == 0.0:
            self.low_price = min(self.start_price, self.end_price)
    
    @property
    def is_bullish(self) -> bool:
        return self.direction == "bullish"
    
    @property
    def is_bearish(self) -> bool:
        return self.direction == "bearish"
    
    @property
    def is_impulse(self) -> bool:
        return self.leg_type == "impulse"
    
    @property
    def is_corrective(self) -> bool:
        return self.leg_type == "corrective"
    
    @property
    def is_swing_leg(self) -> bool:
        """True if this is a swing leg (any consecutive swings)."""
        return self.scope == "swing"
    
    @property
    def is_structural_leg(self) -> bool:
        """True if this is a structural leg (external/structural swings only)."""
        return self.scope == "structural"
    
    @property
    def is_developing(self) -> bool:
        """True if this leg is still developing (endpoint not confirmed)."""
        return self.status == "developing"
    
    @property
    def is_complete(self) -> bool:
        """True if this leg is complete (both endpoints confirmed)."""
        return self.status == "complete"
    
    def complete(self, end_swing_id: str, end_price: float, end_index: int, end_timestamp: int):
        """Mark this leg as complete with confirmed end swing."""
        self.end_swing_id = end_swing_id
        self.end_price = end_price
        self.end_index = end_index
        self.end_timestamp = end_timestamp
        self.status = "complete"
        # Recalculate derived properties
        self.size = abs(self.end_price - self.start_price)
        self.candle_count = self.end_index - self.start_index
        if self.candle_count > 0:
            self.momentum = self.size / self.candle_count


# Type aliases for clarity
@dataclass
class ImpulseLeg(Leg):
    """Impulse (expansion) leg.
    
    Characteristics:
    - Large candles
    - Strong closes
    - Little overlap
    - High momentum
    
    Used to:
    - Define trend direction
    - Cause BOS
    - Create imbalance / FVG
    """
    def __post_init__(self):
        super().__post_init__()
        self.leg_type = "impulse"


@dataclass  
class CorrectiveLeg(Leg):
    """Corrective (retracement) leg.
    
    Characteristics:
    - Smaller candles
    - Overlapping price
    - Slower movement
    - Lower momentum
    
    Used to:
    - Form higher lows / lower highs
    - Create entry opportunities
    - Test zones
    """
    def __post_init__(self):
        super().__post_init__()
        self.leg_type = "corrective"
