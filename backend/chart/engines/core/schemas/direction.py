"""Direction analysis schema with explicit swing-source provenance.

Contains the result of direction detection from alternating swings.
"""
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.chart.engines.core.schemas.swing import SwingPoint


@dataclass
class PatternSwing:
    """A swing point with its HH/HL/LH/LL label."""
    index: int
    timestamp: int
    price: float
    kind: str  # "high" or "low"
    label: str  # "H", "HH", "EH", "LH", "L", "HL", "EL", "LL"
    degree: str = "internal"  # "external" or "internal"


@dataclass
class DirectionAnalysis:
    """Direction analysis from an alternating swing pattern.
    
    Computed from 4 alternating swings (H-L-H-L pattern).
    """
    
    # Core direction
    direction: str = "neutral"  # bullish / bearish / neutral
    direction_detail: str = "Consolidating"  # "HH-HL swing structure", etc.
    
    # State
    is_trending: bool = False  # True if HH-HL or LH-LL pattern
    is_ranging: bool = True  # True if mixed pattern
    
    # Pattern details
    has_higher_high: bool = False  # HH
    has_higher_low: bool = False   # HL
    has_lower_high: bool = False   # LH
    has_lower_low: bool = False    # LL
    
    # The swings used for analysis
    pattern_swings: List[PatternSwing] = field(default_factory=list)
    
    # Counts
    total_swings_analyzed: int = 0
    external_swings_count: int = 0

    # Provenance. A direction is only HTF-derived when matched external swings
    # from a higher timeframe were actually sufficient for the calculation.
    source: str = "unavailable"
    source_timeframe: str = ""
    swing_degree: str = "none"
    fallback_used: bool = False
    quality: str = "insufficient"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "direction": self.direction,
            "direction_detail": self.direction_detail,
            "is_trending": self.is_trending,
            "is_ranging": self.is_ranging,
            "has_higher_high": self.has_higher_high,
            "has_higher_low": self.has_higher_low,
            "has_lower_high": self.has_lower_high,
            "has_lower_low": self.has_lower_low,
            "pattern_swings": [
                {
                    "index": s.index,
                    "timestamp": s.timestamp,
                    "price": s.price,
                    "kind": s.kind,
                    "label": s.label,
                    "degree": s.degree
                } for s in self.pattern_swings
            ],
            "total_swings_analyzed": self.total_swings_analyzed,
            "external_swings_count": self.external_swings_count,
            "source": self.source,
            "source_timeframe": self.source_timeframe,
            "swing_degree": self.swing_degree,
            "fallback_used": self.fallback_used,
            "quality": self.quality,
        }
