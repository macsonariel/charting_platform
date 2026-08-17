"""Core Detectors Package - Fact Detection Only.

All detectors follow the contract:
- FACT DETECTION ONLY
- NO interpretation
- NO phase decisions
- NO concept-specific terminology

Detectors output neutral data models that can be
interpreted by concept-specific interpreters.
"""

from .swing_detector import SwingDetector, detect_swings
from .swing_strength import SwingStrengthScorer, score_swings
from .swing_classifier import SwingClassifier, classify_swings
from .structure_detector import StructureDetector, detect_structure_events
from .leg_detector import LegDetector, detect_legs
from .level_tracker import LevelTracker, track_levels
from .fvg_detector import FVGDetector, detect_fvgs
from .range_detector import RangeDetector, detect_ranges
from .time_levels_detector import TimeLevelsDetector, detect_time_levels

# Note: zone_detector and pattern_detector were moved to backend/chart/_other/


# Lazy loading for liquidity_detector to avoid circular imports
# (liquidity_detector imports schema types which may trigger core/__init__)
def _get_liquidity_detector():
    from .liquidity_detector import LiquidityDetector as LD, LiquidityConfig as LC
    return LD, LC


def _get_liquidity_functions():
    from .liquidity_detector import (
        detect_stop_loss_liquidity as dsl,
        detect_trend_liquidity as dtl,
        detect_range_liquidity as drl,
        detect_inducement as di,
        detect_sweeps as ds,
        analyze_liquidity as al
    )
    return dsl, dtl, drl, di, ds, al


# Convenience wrappers that defer import
def detect_stop_loss_liquidity(*args, **kwargs):
    funcs = _get_liquidity_functions()
    return funcs[0](*args, **kwargs)


def detect_trend_liquidity(*args, **kwargs):
    funcs = _get_liquidity_functions()
    return funcs[1](*args, **kwargs)


def detect_range_liquidity(*args, **kwargs):
    funcs = _get_liquidity_functions()
    return funcs[2](*args, **kwargs)


def detect_inducement(*args, **kwargs):
    funcs = _get_liquidity_functions()
    return funcs[3](*args, **kwargs)


def detect_sweeps(*args, **kwargs):
    funcs = _get_liquidity_functions()
    return funcs[4](*args, **kwargs)


def analyze_liquidity(*args, **kwargs):
    funcs = _get_liquidity_functions()
    return funcs[5](*args, **kwargs)


# Lazy class accessors
class LiquidityDetector:
    """Lazy wrapper for LiquidityDetector class."""
    def __new__(cls, *args, **kwargs):
        LD, _ = _get_liquidity_detector()
        return LD(*args, **kwargs)


class LiquidityConfig:
    """Lazy wrapper for LiquidityConfig class."""
    def __new__(cls, *args, **kwargs):
        _, LC = _get_liquidity_detector()
        return LC(*args, **kwargs)


__all__ = [
    # Swings
    "SwingDetector", "detect_swings",
    "SwingStrengthScorer", "score_swings",
    "SwingClassifier", "classify_swings",
    # Structure
    "StructureDetector", "detect_structure_events",
    # Legs
    "LegDetector", "detect_legs",
    # Levels
    "LevelTracker", "track_levels",
    # Liquidity (lazy loaded)
    "LiquidityDetector", "LiquidityConfig",
    "detect_stop_loss_liquidity", "detect_trend_liquidity",
    "detect_range_liquidity", "detect_inducement",
    "detect_sweeps", "analyze_liquidity",
    # FVG
    "FVGDetector", "detect_fvgs",
    # Ranges
    "RangeDetector", "detect_ranges",
    # Time-based levels
    "TimeLevelsDetector", "detect_time_levels",
]


