"""Core Schemas Package - Neutral Market Structure Data Models.

This package contains all data models using neutral terminology.
Concept-specific aliases (SMC, ICT, Wyckoff) are mapped in their
respective concept packages.

Canonical Naming:
- SwingPoint (External/Internal degree)
- StructureBreak (BOS in concepts)
- CharacterChange (CHoCH in concepts)
- ImpulseLeg / CorrectiveLeg
- TrendingStructure / RangingStructure / TransitionalStructure
"""

from .swing import (
    SwingPoint, SwingDegree, SwingKind, SwingLabel, BrokenSwingInfo
)
from .structure import (
    StructureBreak, CharacterChange, StructureEvent
)
from .leg import (
    Leg, LegType, ImpulseLeg, CorrectiveLeg
)
from .state import (
    StructuralState, TrendingStructure, RangingStructure,
    TransitionalStructure, ExpandingStructure, ContractingStructure
)
from .liquidity import (
    LiquidityPool, LiquiditySweep, FairValueGap
)
from .range import (
    PriceRange, ProtectedLevel
)
from .zone import (
    SupplyDemandZone, ZoneType, ZoneStatus
)
from .sr_zone import SRZone
from .candle import Candle
from .snapshot import MarketSnapshot
from .move import Move
from .events import RecentEvent, EventType
from .actionable import ActionableLevel, ActionableContext
from .analysis import MarketAnalysis
from .regime import MarketRegime

__all__ = [
    # Swings
    "SwingPoint", "SwingDegree", "SwingKind", "SwingLabel", "BrokenSwingInfo",
    # Structure events
    "StructureBreak", "CharacterChange", "StructureEvent",
    # Legs
    "Leg", "LegType", "ImpulseLeg", "CorrectiveLeg",
    # States
    "StructuralState", "TrendingStructure", "RangingStructure",
    "TransitionalStructure", "ExpandingStructure", "ContractingStructure",
    # Liquidity
    "LiquidityPool", "LiquiditySweep", "FairValueGap",
    # Range
    "PriceRange", "ProtectedLevel",
    # Zones
    "SupplyDemandZone", "ZoneType", "ZoneStatus",
    # S/R Zones
    "SRZone",
    # Base
    "Candle", "MarketSnapshot", "Move",
    # Events
    "RecentEvent", "EventType",
    # Actionable
    "ActionableLevel", "ActionableContext",
    # Analysis
    "MarketAnalysis", "MarketRegime"
]
