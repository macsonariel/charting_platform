"""Snapshot - Complete market analysis snapshot."""
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict, TYPE_CHECKING

from .swing import SwingPoint
from .structure import StructureBreak, CharacterChange
from .leg import Leg
from .move import Move
from .liquidity import LiquidityPool, LiquiditySweep, FairValueGap
from .range import PriceRange, ProtectedLevel
from .direction import DirectionAnalysis
from .range_position import RangePosition
from .sr_zone import SRZone, SRAnalysis
from .regime import MarketRegime

if TYPE_CHECKING:
    from .events import RecentEvent
    from .actionable import ActionableContext
    from backend.chart.rendering import DrawingZone


@dataclass
class MarketSnapshot:
    """Complete snapshot of market structure analysis.
    
    Contains all detected facts at a point in time.
    This is the output of the analysis pipeline.
    """
    symbol: str
    timeframe: str
    timestamp: int              # Snapshot time
    current_price: float
    
    # Swings
    swings: List[SwingPoint] = field(default_factory=list)
    external_high: Optional[SwingPoint] = None
    external_low: Optional[SwingPoint] = None
    
    # Structure events
    structure_breaks: List[StructureBreak] = field(default_factory=list)
    character_changes: List[CharacterChange] = field(default_factory=list)
    
    # Legs
    legs: List[Leg] = field(default_factory=list)
    
    # Protected levels
    protected_levels: List[ProtectedLevel] = field(default_factory=list)
    
    # Ranges
    ranges: List[PriceRange] = field(default_factory=list)
    
    # Liquidity
    liquidity_pools: List[LiquidityPool] = field(default_factory=list)
    recent_sweeps: List[LiquiditySweep] = field(default_factory=list)
    
    # Imbalances
    fair_value_gaps: List[FairValueGap] = field(default_factory=list)
    
    # Moves (directional segments)
    moves: List[Move] = field(default_factory=list)
    
    # Current bias
    bias: str = "neutral"       # "bullish", "bearish", "neutral"

    # Canonical interpretation. All public direction/bias/state/phase/confidence
    # values are derived from this object.
    regime: Optional[MarketRegime] = None
    
    # NEW: Direction analysis from alternating swings
    direction_analysis: Optional[DirectionAnalysis] = None
    
    # NEW: Range position (premium/discount/equilibrium)
    range_position: Optional[RangePosition] = None
    
    # NEW: S/R Zone analysis
    sr_analysis: Optional[SRAnalysis] = None
    
    # NEW: Drawing zones (zones between external swings)
    drawing_zones: List = field(default_factory=list)  # List[DrawingZone]
    
    # Recent events - "What just happened?"
    recent_events: List = field(default_factory=list)  # List[RecentEvent]
    
    # Actionable context - "What matters now?"
    actionable: Optional[Any] = None  # ActionableContext
    
    # Market analysis - consolidated Q1-Q9 answers
    analysis: Optional[Any] = None  # MarketAnalysis
    
    # Backward-compatible serialized view of ``regime``. This is not a second
    # interpretation authority.
    interpretation: Optional[Dict[str, Any]] = None
    
    @property
    def has_bullish_bias(self) -> bool:
        return self.bias == "bullish"
    
    @property
    def has_bearish_bias(self) -> bool:
        return self.bias == "bearish"
    
    @property
    def external_swings(self) -> List[SwingPoint]:
        """Get all external swings."""
        return [s for s in self.swings if s.degree == "external"]
    
    @property
    def internal_swings(self) -> List[SwingPoint]:
        """Get all internal swings."""
        return [s for s in self.swings if s.degree == "internal"]
    
    @property
    def active_protected_levels(self) -> List[ProtectedLevel]:
        """Get only unbroken protected levels."""
        return [l for l in self.protected_levels if not l.broken]
    
    @property
    def unfilled_gaps(self) -> List[FairValueGap]:
        """Get unfilled FVGs."""
        return [g for g in self.fair_value_gaps if not g.filled]
    
    @property
    def latest_event(self) -> Optional['RecentEvent']:
        """Get the most recent significant event."""
        if self.recent_events:
            return self.recent_events[0]
        return None
    
    @property
    def what_just_happened(self) -> str:
        """Get a description of what just happened."""
        if self.recent_events:
            return self.recent_events[0].description
        return "No recent significant events"
    
    @property
    def what_matters_now(self) -> str:
        """Get the current thesis from actionable context."""
        if self.actionable:
            return self.actionable.current_thesis
        return "No actionable context available"
    
    @property
    def sr_zones(self) -> List[SRZone]:
        """Get S/R zones from sr_analysis for compatibility with PA Engine.
        
        PA Engine uses sr_zones directly while Core uses sr_analysis.
        This property enables consistent access pattern across both.
        """
        if self.sr_analysis:
            return self.sr_analysis.all_zones
        return []
    
    @property
    def active_move(self) -> Optional[Move]:
        """Get the current active move."""
        active_moves = [m for m in self.moves if m.is_active]
        return active_moves[-1] if active_moves else None
    
    @property
    def move_direction(self) -> str:
        """Get current move direction."""
        if self.active_move:
            return self.active_move.direction
        return "neutral"

