"""Drawing Filter Service

Filters drawings based on zone visibility and drawing type.
Extending drawings (FVG, protected levels, liquidity) persist from older zones.
"""

from dataclasses import dataclass
from typing import List, Any, Set
from .zone_visibility import VisibleZone, VisibilityType


# Drawing types that extend beyond their zone (persist until mitigated)
EXTENDING_DRAWING_TYPES: Set[str] = {
    "fvg",
    "fair_value_gap",
    "protected_level",
    "protected_high",
    "protected_low",
    "liquidity",
    "liquidity_pool",
    "order_block",
    "breaker_block",
    "trendline",
    "sr_zone",
    "support_zone",
    "resistance_zone",
    "imbalance",
}

# Drawing types that do not extend (only shown in their zone)
NON_EXTENDING_DRAWING_TYPES: Set[str] = {
    "swing",
    "swing_high",
    "swing_low",
    "bos",
    "choch",
    "structure_break",
    "pattern",
    "triangle",
    "wedge",
    "pennant",
    "head_shoulders",
    "double_top",
    "double_bottom",
}


def is_extending_drawing(drawing: Any) -> bool:
    """
    Determine if a drawing type extends beyond its zone.
    
    Extending drawings persist until mitigated/broken:
    - FVGs, protected levels, liquidity pools
    - Order blocks, breaker blocks
    - Trendlines, S/R zones
    
    Non-extending drawings are only shown in their zone:
    - Swings, structure breaks
    - Chart patterns
    """
    # Try to get drawing type from various possible attributes
    drawing_type = (
        getattr(drawing, 'type', None) or
        getattr(drawing, 'drawing_type', None) or
        getattr(drawing, 'pattern_type', None) or
        getattr(drawing, 'kind', None) or
        getattr(drawing, '__class__.__name__', '').lower()
    )
    
    if drawing_type:
        drawing_type = str(drawing_type).lower()
        return drawing_type in EXTENDING_DRAWING_TYPES
    
    # Check for specific attributes that indicate extending drawings
    if hasattr(drawing, 'is_mitigated') or hasattr(drawing, 'is_filled'):
        return True  # Has mitigation tracking = extending
    
    if hasattr(drawing, 'is_protected'):
        return True  # Protected level = extending
    
    return False


def get_drawing_start_index(drawing: Any) -> int:
    """Get the start index of a drawing."""
    return (
        getattr(drawing, 'start_index', None) or
        getattr(drawing, 'index', None) or
        getattr(drawing, 'bar_index', 0)
    )


def drawing_within_zone(drawing: Any, zone: Any) -> bool:
    """Check if drawing starts within zone bounds."""
    start_idx = get_drawing_start_index(drawing)
    zone_start = getattr(zone, 'start_index', 0)
    zone_end = getattr(zone, 'end_index', float('inf'))
    return zone_start <= start_idx <= zone_end


def filter_drawings_for_zone(
    drawings: List[Any],
    visible_zone: VisibleZone,
) -> List[Any]:
    """
    Filter drawings based on zone visibility type.
    
    Args:
        drawings: All drawings to filter
        visible_zone: Zone visibility info
        
    Returns:
        Filtered list of drawings to show
    """
    zone = visible_zone.zone
    filtered: List[Any] = []
    
    for drawing in drawings:
        # Check if drawing starts within this zone
        if not drawing_within_zone(drawing, zone):
            continue
        
        # If show_all, include all drawings from this zone
        if visible_zone.show_all:
            filtered.append(drawing)
            continue
        
        # For scanned zones, only show extending drawings
        if visible_zone.visibility_type == VisibilityType.SCANNED:
            if is_extending_drawing(drawing):
                # Also check if still active (not mitigated)
                if not _is_drawing_mitigated(drawing):
                    filtered.append(drawing)
    
    return filtered


def _is_drawing_mitigated(drawing: Any) -> bool:
    """Check if an extending drawing has been mitigated."""
    # FVGs
    if hasattr(drawing, 'is_filled'):
        return getattr(drawing, 'is_filled', False)
    
    # Protected levels
    if hasattr(drawing, 'is_mitigated'):
        return getattr(drawing, 'is_mitigated', False)
    
    # Levels with broken status
    if hasattr(drawing, 'broken'):
        return getattr(drawing, 'broken', False)
    
    # S/R zones
    if hasattr(drawing, 'invalidated'):
        return getattr(drawing, 'invalidated', False)
    
    return False


def filter_all_drawings(
    drawings: List[Any],
    visible_zones: List[VisibleZone],
) -> List[Any]:
    """
    Filter all drawings against all visible zones.
    
    Args:
        drawings: All drawings
        visible_zones: List of zones to show
        
    Returns:
        Combined filtered drawings from all visible zones
    """
    all_filtered: List[Any] = []
    seen_ids: Set[str] = set()
    
    for visible_zone in visible_zones:
        zone_drawings = filter_drawings_for_zone(drawings, visible_zone)
        
        for drawing in zone_drawings:
            # Avoid duplicates
            drawing_id = getattr(drawing, 'id', id(drawing))
            if drawing_id not in seen_ids:
                all_filtered.append(drawing)
                seen_ids.add(drawing_id)
    
    return all_filtered
