"""Pending Level - Structural levels awaiting potential breaks.

A PendingLevel represents a structural level (swing high or low) that 
could be broken in the future. This enables tracking breaks that occur
2, 3, 4+ swings after the level was established.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class LevelStatus(str, Enum):
    """Status of a pending level."""
    ACTIVE = "active"       # Level is still valid, not yet broken
    BROKEN = "broken"       # Level was broken by price
    INVALIDATED = "invalidated"  # Level no longer relevant (e.g., trend changed)


@dataclass
class PendingLevel:
    """A structural level that could be broken in the future.
    
    Tracks:
    - The price level from a swing point
    - How many swings have passed since creation
    - When/how it was broken (if applicable)
    """
    id: str
    price: float
    kind: str               # "high" or "low"
    swing_id: str           # ID of the swing that created this level
    created_index: int      # Candle index when level was created
    created_timestamp: int  # Timestamp when level was created
    timeframe: str = ""
    
    # Tracking
    status: LevelStatus = LevelStatus.ACTIVE
    swings_since_creation: int = 0  # How many swings have passed
    candles_since_creation: int = 0  # How many candles have passed
    
    # Break information (populated when broken)
    broken_at_index: Optional[int] = None
    broken_at_timestamp: Optional[int] = None
    broken_by_swing_id: Optional[str] = None
    broken_by_price: Optional[float] = None
    
    # Classification
    is_external: bool = False  # Was this an external swing?
    
    @property
    def is_active(self) -> bool:
        return self.status == LevelStatus.ACTIVE
    
    @property
    def is_broken(self) -> bool:
        return self.status == LevelStatus.BROKEN
    
    @property
    def break_delay_swings(self) -> int:
        """How many swings passed before the break."""
        return self.swings_since_creation if self.is_broken else 0


@dataclass 
class LevelBreakEvent:
    """Event when a pending level is broken.
    
    Contains both the break information and delay metrics.
    """
    level_id: str
    level_price: float
    level_kind: str         # "high" or "low"
    break_direction: str    # "up" or "down"
    break_price: float
    break_index: int
    break_timestamp: int
    swing_id: str           # Swing that created the level
    breaking_swing_id: str  # Swing that broke the level
    
    # Delay metrics
    swings_delayed: int = 0    # How many swings after level creation
    candles_delayed: int = 0   # How many candles after level creation
    
    # Context
    is_external_break: bool = False  # Was the broken level external?
    timeframe: str = ""
