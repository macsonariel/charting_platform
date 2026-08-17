"""Zone Visibility Service

Calculates which zones should have visible drawings based on current price position.

Dynamic Zone Visibility Rules:
1. ACTIVE ZONE - Always show all drawings
2. PREVIOUS ZONE - Show all if price within its high/low range
3. SCAN LEFT - If price outside previous, find zones containing price, show extending drawings only
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from enum import Enum


class VisibilityType(str, Enum):
    """Type of visibility for a zone."""
    ACTIVE = "active"       # Current move - show all
    PREVIOUS = "previous"   # Previous move - show all if price in range
    SCANNED = "scanned"     # Older zone found via scan - extending only


@dataclass
class VisibleZone:
    """A zone that should have visible drawings."""
    zone: Any  # DrawingZone
    visibility_type: VisibilityType
    show_all: bool = True  # True = all drawings, False = extending only
    
    def to_dict(self) -> dict:
        return {
            "zone_id": getattr(self.zone, 'id', None),
            "start_index": self.zone.start_index,
            "end_index": self.zone.end_index,
            "zone_high": self.zone.zone_high,
            "zone_low": self.zone.zone_low,
            "visibility_type": self.visibility_type.value,
            "show_all": self.show_all,
        }


def calculate_visible_zones(
    zones: List[Any],  # List[DrawingZone]
    current_price: float,
) -> List[VisibleZone]:
    """
    Determine which zones should have visible drawings based on price position.
    
    Args:
        zones: List of DrawingZone objects (index 0 = most recent/active)
        current_price: Current market price
        
    Returns:
        List of VisibleZone objects indicating which zones to show
    """
    if not zones:
        return []
    
    visible: List[VisibleZone] = []
    
    # 1. Active zone - always show all drawings
    active_zone = zones[0]
    visible.append(VisibleZone(
        zone=active_zone,
        visibility_type=VisibilityType.ACTIVE,
        show_all=True
    ))
    
    # 2. Previous zone - check if price is within its range
    if len(zones) > 1:
        previous_zone = zones[1]
        
        if _price_within_zone(current_price, previous_zone):
            # Price is within previous zone - show all drawings
            visible.append(VisibleZone(
                zone=previous_zone,
                visibility_type=VisibilityType.PREVIOUS,
                show_all=True
            ))
        else:
            # 3. Scan left for zones where price is within range
            # Only show extending drawings from these zones
            for zone in zones[2:]:  # Start from 3rd zone (index 2)
                if _price_within_zone(current_price, zone):
                    visible.append(VisibleZone(
                        zone=zone,
                        visibility_type=VisibilityType.SCANNED,
                        show_all=False  # Extending drawings only
                    ))
                    # Could break here to only show first matching
                    # Or continue to show all matching zones
    
    return visible


def _price_within_zone(price: float, zone: Any) -> bool:
    """Check if price is within zone's high/low range."""
    zone_high = getattr(zone, 'zone_high', 0)
    zone_low = getattr(zone, 'zone_low', 0)
    return zone_low <= price <= zone_high


def get_visible_zone_ids(
    zones: List[Any],
    current_price: float,
) -> List[str]:
    """Get list of zone IDs that should be visible."""
    visible = calculate_visible_zones(zones, current_price)
    return [getattr(vz.zone, 'id', None) for vz in visible if vz.zone]


def is_zone_visible(
    zone_id: str,
    zones: List[Any],
    current_price: float,
) -> bool:
    """Check if a specific zone should be visible."""
    visible_ids = get_visible_zone_ids(zones, current_price)
    return zone_id in visible_ids


def get_zone_visibility_summary(
    zones: List[Any],
    current_price: float,
) -> dict:
    """Get summary of zone visibility for API response."""
    visible = calculate_visible_zones(zones, current_price)
    
    return {
        "current_price": current_price,
        "total_zones": len(zones),
        "visible_zones": len(visible),
        "zones": [vz.to_dict() for vz in visible],
    }
