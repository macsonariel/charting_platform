"""S/R Zone - Support/Resistance zone models.

Neutral terminology for the Core Engine.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SRZone:
    """Support/Resistance Zone - Price area where reversals occur.
    
    Unlike a single price level, a zone has high/low bounds.
    Formed by clustering swing points at similar prices.
    
    Strength Scoring (0-1):
    - Touch count (more = stronger)
    - Swing degrees (external swings = stronger)
    - Recency (newer = more relevant)
    - Zone width (tighter = stronger)
    """
    id: str
    zone_type: str              # "support" or "resistance"
    high: float                 # Upper bound of zone
    low: float                  # Lower bound of zone
    midpoint: float             # Center of zone
    
    # Source data
    swing_ids: List[str] = field(default_factory=list)
    touch_count: int = 1        # Times price reacted at this zone
    external_count: int = 0     # How many external swings in zone
    
    # Scoring
    strength: float = 0.5       # 0-1 composite score
    
    # Metadata
    timestamp: int = 0          # Oldest swing in zone
    last_touch_timestamp: int = 0  # Most recent touch
    index: int = 0
    timeframe: str = ""
    
    # Status
    broken: bool = False        # If price closed through (at least once)
    break_count: int = 0        # How many times zone has been broken
    break_timestamp: Optional[int] = None  # First break
    last_break_timestamp: Optional[int] = None  # Most recent break
    invalidated: bool = False   # True if zone was broken too many times
    
    # Flip tracking (support↔resistance)
    flipped_from: Optional[str] = None  # ID of original zone if flipped
    is_flipped: bool = False
    original_type: Optional[str] = None  # Original zone type before flip
    
    # Round number (psychological level) tracking
    is_round_number: bool = False           # If this is a round number level
    round_number_type: Optional[str] = None  # "major", "minor", or None
    
    @property
    def size(self) -> float:
        """Zone width in price."""
        return self.high - self.low
    
    @property
    def is_support(self) -> bool:
        return self.zone_type == "support"
    
    @property
    def is_resistance(self) -> bool:
        return self.zone_type == "resistance"
    
    @property
    def is_intact(self) -> bool:
        return not self.broken
    
    @property
    def has_external(self) -> bool:
        """True if zone contains at least one external swing."""
        return self.external_count > 0


@dataclass  
class SRAnalysis:
    """Complete S/R Zone analysis result."""
    support_zones: List[SRZone] = field(default_factory=list)
    resistance_zones: List[SRZone] = field(default_factory=list)
    all_zones: List[SRZone] = field(default_factory=list)
    
    # Summary
    nearest_support: Optional[SRZone] = None
    nearest_resistance: Optional[SRZone] = None
    
    # Counts
    support_count: int = 0
    resistance_count: int = 0
    intact_count: int = 0
    broken_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "support_count": self.support_count,
            "resistance_count": self.resistance_count,
            "intact_count": self.intact_count,
            "broken_count": self.broken_count,
            "nearest_support": self.nearest_support.midpoint if self.nearest_support else None,
            "nearest_resistance": self.nearest_resistance.midpoint if self.nearest_resistance else None,
        }
