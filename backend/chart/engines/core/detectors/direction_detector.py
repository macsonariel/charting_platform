"""Direction Detector - Detects HTF direction from swing pattern.

Finds alternating swings (H-L-H-L) and determines:
- Direction (bullish/bearish/neutral)
- Pattern (HH-HL / LH-LL / mixed)
- Is trending or ranging
"""
from typing import List, Optional

from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.direction import DirectionAnalysis, PatternSwing


def detect_direction(swings: List[SwingPoint], count: int = 4) -> DirectionAnalysis:
    """Detect HTF direction from alternating swings.
    
    Ensures we get H-L-H-L pattern (no consecutive same-type swings).
    
    Args:
        swings: All detected swings
        count: Number of alternating swings to use (default 4)
        
    Returns:
        DirectionAnalysis with direction, pattern, and swing details
    """
    if not swings:
        return DirectionAnalysis(
            direction="neutral",
            direction_detail="No swings detected",
            total_swings_analyzed=0
        )
    
    # Get alternating swings from most recent backwards
    alternating = _get_alternating_swings(swings, count)
    
    if len(alternating) < 2:
        return DirectionAnalysis(
            direction="neutral",
            direction_detail="Insufficient swing data",
            total_swings_analyzed=len(swings)
        )
    
    # Label swings with HH/HL/LH/LL
    pattern_swings = _label_swings(alternating, swings)
    
    # Analyze pattern
    direction, direction_detail, is_trending = _analyze_pattern(pattern_swings)
    
    # Count externals
    external_count = len([s for s in swings if getattr(s, 'degree', 'internal') == 'external'])
    
    # Build flags
    has_hh = any(s.label == "HH" for s in pattern_swings)
    has_hl = any(s.label == "HL" for s in pattern_swings)
    has_lh = any(s.label == "LH" for s in pattern_swings)
    has_ll = any(s.label == "LL" for s in pattern_swings)
    
    return DirectionAnalysis(
        direction=direction,
        direction_detail=direction_detail,
        is_trending=is_trending,
        is_ranging=not is_trending,
        has_higher_high=has_hh,
        has_higher_low=has_hl,
        has_lower_high=has_lh,
        has_lower_low=has_ll,
        pattern_swings=pattern_swings,
        total_swings_analyzed=len(swings),
        external_swings_count=external_count
    )


def _get_alternating_swings(swings: List[SwingPoint], count: int) -> List[SwingPoint]:
    """Get alternating swings (H-L-H-L) from most recent backwards.
    
    This ensures we don't get consecutive highs or consecutive lows.
    """
    sorted_swings = sorted(swings, key=lambda s: s.index)
    alternating = []
    last_kind = None
    
    for swing in reversed(sorted_swings):
        if swing.kind == last_kind:
            continue
        alternating.insert(0, swing)
        last_kind = swing.kind
        if len(alternating) >= count:
            break
    
    return alternating


def _label_swings(alternating: List[SwingPoint], all_swings: List[SwingPoint]) -> List[PatternSwing]:
    """Label swings with HH/HL/LH/LL based on comparison to previous swing of same type."""
    result = []
    
    if not alternating:
        return result
    
    # Get all highs and lows sorted by index
    all_highs = sorted([s for s in all_swings if s.kind == "high"], key=lambda s: s.index)
    all_lows = sorted([s for s in all_swings if s.kind == "low"], key=lambda s: s.index)
    
    # Find the high/low before our selection window for comparison
    first_idx = alternating[0].index
    prev_high = None
    prev_low = None
    
    for h in reversed(all_highs):
        if h.index < first_idx:
            prev_high = h.price
            break
    
    for l in reversed(all_lows):
        if l.index < first_idx:
            prev_low = l.price
            break
    
    # Label each swing
    for swing in alternating:
        label = ""
        if swing.kind == "high":
            if prev_high is None:
                label = "H"
            elif swing.price > prev_high * 1.001:
                label = "HH"
            elif swing.price < prev_high * 0.999:
                label = "LH"
            else:
                label = "EH"
            prev_high = swing.price
        elif swing.kind == "low":
            if prev_low is None:
                label = "L"
            elif swing.price > prev_low * 1.001:
                label = "HL"
            elif swing.price < prev_low * 0.999:
                label = "LL"
            else:
                label = "EL"
            prev_low = swing.price
        
        result.append(PatternSwing(
            index=swing.index,
            timestamp=swing.timestamp,
            price=swing.price,
            kind=swing.kind,
            label=label,
            degree=getattr(swing, 'degree', 'internal')
        ))
    
    return result


def _analyze_pattern(pattern_swings: List[PatternSwing]) -> tuple:
    """Analyze the swing pattern to determine direction.
    
    Returns: (direction, direction_detail, is_trending)
    """
    if len(pattern_swings) < 4:
        # A high-to-low comparison says nothing about trend direction. Require
        # two highs and two lows before assigning a directional structure.
        return ("neutral", "Insufficient alternating swings", False)
    
    # Get the labels
    highs = [s for s in pattern_swings if s.kind == "high"]
    lows = [s for s in pattern_swings if s.kind == "low"]
    
    if len(highs) < 2 or len(lows) < 2:
        return ("neutral", "Incomplete pattern", False)
    
    # Check for HH and HL (bullish)
    has_hh = highs[-1].label == "HH"
    has_hl = lows[-1].label == "HL"
    
    # Check for LH and LL (bearish)
    has_lh = highs[-1].label == "LH"
    has_ll = lows[-1].label == "LL"
    
    # Determine direction
    if has_hh and has_hl:
        return ("bullish", "HH-HL swing structure", True)
    elif has_lh and has_ll:
        return ("bearish", "LH-LL swing structure", True)
    elif has_hh or has_hl:
        return ("bullish", "Higher structure forming", True)
    elif has_lh or has_ll:
        return ("bearish", "Lower structure forming", True)
    else:
        return ("neutral", "Mixed/ranging", False)
