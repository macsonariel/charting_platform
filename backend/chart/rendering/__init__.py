"""Rendering Package - Centralized Drawing Control.

This package provides the RenderOrchestrator which controls what drawings
are displayed on the chart based on zone boundaries.

Main Components:
- RenderOrchestrator: Central controller for filtering drawings by zone
- DrawingZone: Zone between external swing points
- ZoneFilter: Utility functions for filtering data by zone boundaries
- ZoneVisibility: Dynamic zone visibility based on price position
- DrawingFilter: Filters drawings by zone and type (extending vs non-extending)

Usage:
    from backend.chart.rendering import RenderOrchestrator, render_for_zone
    
    # Get filtered data for the most recent zone only
    filtered = render_for_zone(snapshot)
"""

from backend.chart.rendering.render_orchestrator import (
    RenderOrchestrator,
    DrawingZone,
    ZoneDirection,
    detect_drawing_zones,
    render_for_zone,
    get_active_zone,
)

from backend.chart.rendering.zone_visibility import (
    calculate_visible_zones,
    get_visible_zone_ids,
    get_zone_visibility_summary,
    VisibleZone,
    VisibilityType,
)

from backend.chart.rendering.drawing_filter import (
    filter_drawings_for_zone,
    filter_all_drawings,
    is_extending_drawing,
    EXTENDING_DRAWING_TYPES,
)

__all__ = [
    'RenderOrchestrator',
    'DrawingZone', 
    'ZoneDirection',
    'detect_drawing_zones',
    'render_for_zone',
    'get_active_zone',
    # Zone visibility
    'calculate_visible_zones',
    'get_visible_zone_ids',
    'get_zone_visibility_summary',
    'VisibleZone',
    'VisibilityType',
    # Drawing filter
    'filter_drawings_for_zone',
    'filter_all_drawings',
    'is_extending_drawing',
    'EXTENDING_DRAWING_TYPES',
]
