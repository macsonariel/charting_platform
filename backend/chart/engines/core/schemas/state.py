"""State - Structural state classifications.

These describe the BEHAVIOR of market structure.

Neutral Terms:
- TrendingStructure (Directional)
- RangingStructure (Consolidation)
- TransitionalStructure (Distribution/Accumulation)
- ExpandingStructure (Volatility widening)
- ContractingStructure (Compression)
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class StructuralStateType(str, Enum):
    """Types of structural states."""
    TRENDING = "trending"
    RANGING = "ranging"
    TRANSITIONAL = "transitional"
    EXPANDING = "expanding"
    CONTRACTING = "contracting"


@dataclass
class StructuralState:
    """Base structural state classification."""
    state_type: str
    direction: Optional[str] = None  # "bullish", "bearish", or None
    confidence: float = 0.0          # 0-100 confidence
    start_index: int = 0
    start_timestamp: int = 0
    
    @property
    def is_bullish(self) -> bool:
        return self.direction == "bullish"
    
    @property
    def is_bearish(self) -> bool:
        return self.direction == "bearish"


@dataclass
class TrendingStructure(StructuralState):
    """Trending (directional) structure.
    
    Characteristics:
    - Clear HH/HL (bullish) or LL/LH (bearish)
    - Consistent swing progression
    - Impulse legs larger than corrections
    
    Bullish: HH + HL pattern
    Bearish: LL + LH pattern
    """
    hh_count: int = 0  # Higher highs
    hl_count: int = 0  # Higher lows
    ll_count: int = 0  # Lower lows
    lh_count: int = 0  # Lower highs
    
    def __post_init__(self):
        self.state_type = "trending"


@dataclass
class RangingStructure(StructuralState):
    """Ranging (consolidation) structure.
    
    Characteristics:
    - Balanced highs and lows
    - No clear directional bias
    - Similar-sized legs
    
    Also called: Consolidation, Equilibrium
    """
    range_high: float = 0.0
    range_low: float = 0.0
    range_size: float = 0.0
    
    def __post_init__(self):
        self.state_type = "ranging"
        self.direction = None
        self.range_size = self.range_high - self.range_low


@dataclass
class TransitionalStructure(StructuralState):
    """Transitional (shift) structure.
    
    Characteristics:
    - Structure changing from one state to another
    - Mixed signals
    - May contain character changes
    
    Wyckoff equivalents:
    - Accumulation (bearish → bullish transition)
    - Distribution (bullish → bearish transition)
    """
    from_state: Optional[str] = None  # Previous state type
    to_state: Optional[str] = None    # Emerging state type
    
    def __post_init__(self):
        self.state_type = "transitional"


@dataclass
class ExpandingStructure(StructuralState):
    """Expanding (volatile) structure.
    
    Characteristics:
    - Range widening
    - Increasing volatility
    - Larger swings
    
    Often seen during breakouts or news events.
    """
    expansion_rate: float = 0.0  # Rate of range expansion
    
    def __post_init__(self):
        self.state_type = "expanding"


@dataclass
class ContractingStructure(StructuralState):
    """Contracting (compression) structure.
    
    Characteristics:
    - Range tightening
    - Decreasing volatility
    - Smaller swings
    
    Often precedes breakouts.
    """
    compression_rate: float = 0.0  # Rate of range compression
    
    def __post_init__(self):
        self.state_type = "contracting"
