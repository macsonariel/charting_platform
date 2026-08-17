"""Move - Discrete market move data model.

A Move represents a directional segment of market structure:
- BULLISH: Low → Higher Highs until CHoCH
- BEARISH: High → Lower Lows until CHoCH

Each move tracks:
- External high and low references
- Primary CHoCH (if any)
- State (active or archived)
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Move:
    """A discrete market move with its own external structure."""
    id: str
    direction: str  # "bullish" or "bearish"
    state: str = "active"  # "active" or "archived"
    
    # External references (swing IDs) - origin points of the move
    external_high_id: Optional[str] = None
    external_high_price: float = 0.0
    external_low_id: Optional[str] = None
    external_low_price: float = 0.0  # Changed from inf - 0 means not set
    
    # Protected references - most recent internal structure (for CHoCH detection)
    # In bullish: protected_low = most recent HL (pullback low) that led to HH
    # In bearish: protected_high = most recent LH (pullback high) that led to LL
    protected_high_id: Optional[str] = None
    protected_high_price: float = 0.0
    protected_low_id: Optional[str] = None
    protected_low_price: float = 0.0  # Changed from inf - 0 means not set
    
    # Candidate protected levels - awaiting confirmation by next swing
    # HL becomes protected only after HH confirms it (bullish)
    # LH becomes protected only after LL confirms it (bearish)
    candidate_protected_high_id: Optional[str] = None
    candidate_protected_high_price: float = 0.0
    candidate_protected_low_id: Optional[str] = None
    candidate_protected_low_price: float = 0.0  # Changed from inf - 0 means not set
    
    # Primary CHoCH tracking
    primary_choch_id: Optional[str] = None
    primary_choch_price: Optional[float] = None
    primary_choch_broken: bool = False
    primary_choch_invalidated: bool = False
    
    # Boundaries
    start_index: int = 0
    end_index: Optional[int] = None  # None = ongoing
    start_timestamp: int = 0
    end_timestamp: Optional[int] = None
    
    # Relationships
    previous_move_id: Optional[str] = None
    swing_ids: List[str] = field(default_factory=list)
    
    @property
    def is_bullish(self) -> bool:
        return self.direction == "bullish"
    
    @property
    def is_bearish(self) -> bool:
        return self.direction == "bearish"
    
    @property
    def is_active(self) -> bool:
        return self.state == "active"
    
    @property
    def is_archived(self) -> bool:
        return self.state == "archived"
    
    @property
    def has_choch(self) -> bool:
        return self.primary_choch_id is not None
    
    @property
    def choch_confirmed(self) -> bool:
        return self.primary_choch_broken and not self.primary_choch_invalidated
