"""Core Package - Universal Market Structure Analysis.

This is the shared foundation for ALL analysis engines.
Uses neutral terminology - concept-specific names are mapped
in their respective engine packages.

Structure:
- schemas/: Data models (SwingPoint, StructureBreak, etc.)
- detectors/: Fact detection (no interpretation)
- pipeline/: Orchestration and data flow
- analyzers/: Canonical swing-derived regime and presentation analysis

Canonical Naming:
- External/Internal (not macro/micro)
- StructureBreak (not BOS)
- CharacterChange (not CHoCH)
- ImpulseLeg/CorrectiveLeg (not displacement/pullback)
- TrendingStructure/RangingStructure

NOTE: Detectors are lazy-loaded to avoid circular imports.
Use: from backend.chart.engines.core.detectors import detect_swings
"""

# Import schemas from direct files (not package) to avoid circular import
from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.snapshot import MarketSnapshot
from backend.chart.engines.core.schemas.swing import SwingPoint, SwingDegree, SwingKind
from backend.chart.engines.core.schemas.structure import StructureBreak, CharacterChange, StructureEvent
from backend.chart.engines.core.schemas.leg import Leg, LegType, ImpulseLeg, CorrectiveLeg
from backend.chart.engines.core.schemas.state import (
    StructuralState, TrendingStructure, RangingStructure,
    TransitionalStructure, ExpandingStructure, ContractingStructure
)
from backend.chart.engines.core.schemas.liquidity import LiquidityPool, LiquiditySweep, FairValueGap
from backend.chart.engines.core.schemas.range import PriceRange, ProtectedLevel
from backend.chart.engines.core.schemas.zone import SupplyDemandZone, ZoneType, ZoneStatus
from backend.chart.engines.core.schemas.regime import MarketRegime


# Lazy loading for detectors to avoid circular imports
def _get_detectors():
    from backend.chart.engines.core import detectors
    return detectors


def detect_swings(*args, **kwargs):
    return _get_detectors().detect_swings(*args, **kwargs)


def score_swings(*args, **kwargs):
    return _get_detectors().score_swings(*args, **kwargs)


def classify_swings(*args, **kwargs):
    return _get_detectors().classify_swings(*args, **kwargs)


def detect_structure_events(*args, **kwargs):
    return _get_detectors().detect_structure_events(*args, **kwargs)


def detect_legs(*args, **kwargs):
    return _get_detectors().detect_legs(*args, **kwargs)


def track_levels(*args, **kwargs):
    return _get_detectors().track_levels(*args, **kwargs)


def analyze_liquidity(*args, **kwargs):
    return _get_detectors().analyze_liquidity(*args, **kwargs)


def detect_fvgs(*args, **kwargs):
    return _get_detectors().detect_fvgs(*args, **kwargs)


def detect_ranges(*args, **kwargs):
    return _get_detectors().detect_ranges(*args, **kwargs)


# Lazy loading for pipeline
def _get_pipeline():
    from backend.chart.engines.core import pipeline
    return pipeline


def run_pipeline(*args, **kwargs):
    return _get_pipeline().run_pipeline(*args, **kwargs)


class Pipeline:
    def __new__(cls, *args, **kwargs):
        return _get_pipeline().Pipeline(*args, **kwargs)


__all__ = [
    # Models
    "Candle", "MarketSnapshot", "MarketRegime",
    "SwingPoint", "SwingDegree", "SwingKind",
    "StructureBreak", "CharacterChange", "StructureEvent",
    "Leg", "LegType", "ImpulseLeg", "CorrectiveLeg",
    "StructuralState", "TrendingStructure", "RangingStructure",
    "TransitionalStructure", "ExpandingStructure", "ContractingStructure",
    "LiquidityPool", "LiquiditySweep", "FairValueGap",
    "PriceRange", "ProtectedLevel",
    "SupplyDemandZone", "ZoneType", "ZoneStatus",
    # Detectors (lazy loaded)
    "detect_swings", "score_swings", "classify_swings",
    "detect_structure_events", "detect_legs", "track_levels",
    "analyze_liquidity", "detect_fvgs", "detect_ranges",
    # Pipeline (lazy loaded)
    "Pipeline", "run_pipeline",
]
