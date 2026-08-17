"""Swing Point Schema - Core swing highs/lows data contract

DATA CONTRACT ONLY - NO LOGIC

This is the core/universal swing point schema.
Engine-specific versions may extend this with additional fields.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class SwingKind(str, Enum):
    """Type of swing point."""
    HIGH = "high"
    LOW = "low"


class SwingDegree(str, Enum):
    """Degree/strength of swing point."""
    INTERNAL = "internal"   # Minor swing (internal structure)
    EXTERNAL = "external"   # Major swing (external structure)


class SwingLabel(str, Enum):
    """Label for swing point (HH, HL, LH, LL)."""
    HH = "HH"   # Higher High
    HL = "HL"   # Higher Low
    LH = "LH"   # Lower High
    LL = "LL"   # Lower Low


@dataclass
class SwingPoint:
    """A swing high or low point in price action.
    
    Swing points are the basic building blocks of market structure.
    They represent local extremes (highs and lows) in price.
    
    Degree Classification:
    - External: Major swing that defines primary structure (default)
    - Internal: Minor swing that failed to break structure (was_demoted=True)
    
    Archive System:
    - archived=False: Live external, can still be demoted within current leg
    - archived=True: Locked external, confirmed by CHoCH, cannot be demoted
    """
    # Identity
    id: str
    index: int              # Bar index in candle array
    timestamp: int          # Unix timestamp
    price: float            # Price level (high for swing high, low for swing low)
    kind: str               # "high" | "low"
    
    # Classification
    label: Optional[str] = None  # "HH", "HL", "LH", "LL" (set after classification)
    
    # Structure fields (set by structure_detector)
    broken: bool = False
    broken_by_id: Optional[str] = None
    broken_by_price: Optional[float] = None
    breaks: List[str] = field(default_factory=list)  # IDs of swings this one breaks
    is_protected: bool = False  # Whether this swing is currently protecting structure
    is_choch: bool = False       # Whether this swing is a CHoCH point
    is_bos: bool = False          # Whether this swing creates a BOS
    is_primary_choch: bool = False  # Whether this is the primary CHoCH
    choch_invalidated: bool = False
    invalidated_by_id: Optional[str] = None
    
    # Degree (set by swing_classifier)
    # Default: external - swings start as major until demoted
    degree: str = "external"  # "internal" | "external"
    was_demoted: bool = False  # True if this swing was demoted from external to internal
    archived: bool = False  # Locked external - confirmed by CHoCH, cannot be demoted
    color: Optional[str] = None  # Custom color override (e.g., "yellow" for archived external)
    
    # Move tracking
    move_id: Optional[str] = None
    
    # Scoring
    strength: float = 0.0   # 0-1 significance score
    valid: bool = True      # Whether swing is valid (for filtering)
    confirmed: bool = True  # Whether the swing is confirmed
    timeframe: str = ""     # Timeframe string (e.g., "1h", "4h")


@dataclass
class BrokenSwingInfo:
    """Information about a broken swing point.
    
    Used by structure detection to track which swings were broken
    and their properties at time of break.
    """
    swing_id: str           # ID of the broken swing
    swing_price: float      # Price of the broken swing
    swing_index: int        # Index of the broken swing
    was_external: bool      # Whether the swing was external degree
    was_choch: bool = False      # Whether the swing was a CHoCH point
    was_primary_choch: bool = False  # Whether it was the primary CHoCH