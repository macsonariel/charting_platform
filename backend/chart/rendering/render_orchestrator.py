"""Render Orchestrator - Central Control for Chart Drawings.

This module provides the RenderOrchestrator which controls what drawings
are displayed on the chart. It filters all drawings (swings, FVGs, structure
events, liquidity, etc.) to only show within the active zone.

Key Concepts:
- DrawingZone: A zone between two consecutive external swing points
- Active Zone: The zone currently being displayed (default = most recent)
- Filtering: All drawings are filtered to only show within the active zone's boundaries

Usage:
    orchestrator = RenderOrchestrator()
    orchestrator.set_zones(drawing_zones)
    filtered_data = orchestrator.filter_snapshot(snapshot)
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, TypeVar, Callable
from enum import Enum

from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.structure import StructureBreak, CharacterChange
from backend.chart.engines.core.schemas.liquidity import LiquidityPool, LiquiditySweep, FairValueGap
from backend.chart.engines.core.schemas.range import ProtectedLevel


class ZoneDirection(str, Enum):
    """Direction of a drawing zone."""
    BULLISH = "bullish"  # Low to High (green)
    BEARISH = "bearish"  # High to Low (red)


@dataclass
class DrawingZone:
    """A zone between two external swing points.
    
    Represents a directional move from one external swing to another,
    with tracked price extremes of all candles within the zone.
    """
    # Identity
    id: str
    direction: ZoneDirection  # bullish (low→high) or bearish (high→low)
    
    # Start point (first external swing)
    start_timestamp: int
    start_price: float
    start_index: int
    start_swing_id: str
    start_kind: str  # "high" or "low"
    
    # End point (second external swing)
    end_timestamp: int
    end_price: float
    end_index: int
    end_swing_id: str
    end_kind: str  # "high" or "low"
    
    # Price extremes within the zone (from candle data)
    zone_high: float = 0.0  # Highest candle high within zone
    zone_low: float = 0.0   # Lowest candle low within zone
    zone_high_index: int = 0
    zone_low_index: int = 0
    
    # Additional metadata
    candle_count: int = 0  # Number of candles in zone
    swing_count: int = 0   # Number of internal swings in zone
    
    def contains_index(self, index: int) -> bool:
        """Check if an index falls within this zone."""
        return self.start_index <= index <= self.end_index
    
    def contains_timestamp(self, timestamp: int) -> bool:
        """Check if a timestamp falls within this zone."""
        return self.start_timestamp <= timestamp <= self.end_timestamp
    
    def contains_price(self, price: float) -> bool:
        """Check if a price is within the zone's price range."""
        return self.zone_low <= price <= self.zone_high
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "direction": self.direction.value if isinstance(self.direction, ZoneDirection) else self.direction,
            "start_timestamp": self.start_timestamp,
            "start_price": self.start_price,
            "start_index": self.start_index,
            "start_swing_id": self.start_swing_id,
            "start_kind": self.start_kind,
            "end_timestamp": self.end_timestamp,
            "end_price": self.end_price,
            "end_index": self.end_index,
            "end_swing_id": self.end_swing_id,
            "end_kind": self.end_kind,
            "zone_high": self.zone_high,
            "zone_low": self.zone_low,
            "zone_high_index": self.zone_high_index,
            "zone_low_index": self.zone_low_index,
            "candle_count": self.candle_count,
            "swing_count": self.swing_count,
        }


def generate_zone_id(index: int, direction: str) -> str:
    """Generate unique zone ID."""
    import time
    import random
    return f"zone_{direction[:1]}_{index}_{int(time.time() * 1000) % 10000}_{random.randint(100, 999)}"


def detect_drawing_zones(
    swings: List[SwingPoint],
    candles: List[Candle],
) -> List[DrawingZone]:
    """Detect drawing zones between consecutive external swing points.
    
    Args:
        swings: All swing points (will filter to external only)
        candles: Candle data for calculating zone highs/lows
        
    Returns:
        List of DrawingZone objects, most recent first (index 0 = latest zone)
    """
    # Filter to external swings only and sort by index
    external_swings = sorted(
        [s for s in swings if s.degree == "external"],
        key=lambda s: s.index
    )
    
    if len(external_swings) < 2:
        return []
    
    # Build index to candle mapping for efficient lookup
    candle_by_index = {i: c for i, c in enumerate(candles)}
    
    zones: List[DrawingZone] = []
    
    # Create zones between consecutive external swings
    for i in range(len(external_swings) - 1):
        start_swing = external_swings[i]
        end_swing = external_swings[i + 1]
        
        # Determine zone direction
        if start_swing.kind == "low" and end_swing.kind == "high":
            direction = ZoneDirection.BULLISH
        elif start_swing.kind == "high" and end_swing.kind == "low":
            direction = ZoneDirection.BEARISH
        else:
            # Same kind - shouldn't happen with proper alternation, skip
            print(f"[RenderOrchestrator] Warning: Non-alternating externals at indices {start_swing.index} and {end_swing.index}")
            continue
        
        # Calculate zone highs/lows from candle data
        zone_high = 0.0
        zone_low = float('inf')
        zone_high_index = start_swing.index
        zone_low_index = start_swing.index
        candle_count = 0
        
        for idx in range(start_swing.index, end_swing.index + 1):
            candle = candle_by_index.get(idx)
            if candle:
                candle_count += 1
                if candle.high > zone_high:
                    zone_high = candle.high
                    zone_high_index = idx
                if candle.low < zone_low:
                    zone_low = candle.low
                    zone_low_index = idx
        
        # Count all swings within zone (excluding the boundary swings)
        swing_count = sum(
            1 for s in swings
            if s.index > start_swing.index 
            and s.index < end_swing.index
        )
        
        zone = DrawingZone(
            id=generate_zone_id(i, direction.value),
            direction=direction,
            start_timestamp=start_swing.timestamp,
            start_price=start_swing.price,
            start_index=start_swing.index,
            start_swing_id=start_swing.id,
            start_kind=start_swing.kind,
            end_timestamp=end_swing.timestamp,
            end_price=end_swing.price,
            end_index=end_swing.index,
            end_swing_id=end_swing.id,
            end_kind=end_swing.kind,
            zone_high=zone_high,
            zone_low=zone_low if zone_low != float('inf') else 0.0,
            zone_high_index=zone_high_index,
            zone_low_index=zone_low_index,
            candle_count=candle_count,
            swing_count=swing_count,
        )
        
        zones.append(zone)
    
    # === Create live zone from last external swing to current candle ===
    # This ensures the active zone extends to current price
    if external_swings:
        last_swing = external_swings[-1]
        current_index = len(candles) - 1
        
        # Only create live zone if there's actual movement beyond last swing
        if current_index > last_swing.index:
            # Determine zone direction from last swing type
            if last_swing.kind == "low":
                direction = ZoneDirection.BULLISH
            else:  # high
                direction = ZoneDirection.BEARISH
            
            # Calculate zone highs/lows from candles after last swing
            zone_high = 0.0
            zone_low = float('inf')
            zone_high_index = last_swing.index
            zone_low_index = last_swing.index
            candle_count = 0
            
            for idx in range(last_swing.index, current_index + 1):
                candle = candle_by_index.get(idx)
                if candle:
                    candle_count += 1
                    if candle.high > zone_high:
                        zone_high = candle.high
                        zone_high_index = idx
                    if candle.low < zone_low:
                        zone_low = candle.low
                        zone_low_index = idx
            
            # Count swings after last external swing
            swing_count = sum(
                1 for s in swings
                if s.index > last_swing.index
            )
            
            # Get current candle for end details
            current_candle = candles[current_index]
            
            live_zone = DrawingZone(
                id=generate_zone_id(len(zones), f"{direction.value}_live"),
                direction=direction,
                start_timestamp=last_swing.timestamp,
                start_price=last_swing.price,
                start_index=last_swing.index,
                start_swing_id=last_swing.id,
                start_kind=last_swing.kind,
                end_timestamp=current_candle.timestamp,
                end_price=current_candle.close,
                end_index=current_index,
                end_swing_id=None,  # No swing at current position yet
                end_kind=None,
                zone_high=zone_high,
                zone_low=zone_low if zone_low != float('inf') else 0.0,
                zone_high_index=zone_high_index,
                zone_low_index=zone_low_index,
                candle_count=candle_count,
                swing_count=swing_count,
            )
            
            zones.append(live_zone)
    
    # Reverse so most recent zone is at index 0
    zones.reverse()
    
    return zones


def get_active_zone(zones: List[DrawingZone]) -> Optional[DrawingZone]:
    """Get the most recent (active) zone.
    
    Returns:
        The latest zone (index 0), or None if no zones
    """
    return zones[0] if zones else None


class RenderOrchestrator:
    """Central controller for what drawings are displayed on the chart.
    
    The orchestrator manages drawing zones and filters all drawings to only
    show within the currently active zone. This provides a clean, focused view
    of the most relevant market structure.
    
    Attributes:
        zones: List of all detected drawing zones
        active_zone_index: Index of the currently active zone (0 = most recent)
        show_all_zones: If True, show all zones (not just active)
    """
    
    def __init__(self):
        self.zones: List[DrawingZone] = []
        self.active_zone_index: int = 0  # 0 = most recent zone
        self.show_all_zones: bool = False
        self._live_zone: Optional[DrawingZone] = None  # Synthetic live zone
        
    def set_zones(self, zones: List[DrawingZone]) -> None:
        """Set the drawing zones.
        
        Args:
            zones: List of DrawingZone objects (should be sorted most recent first)
        """
        self.zones = zones
        self.active_zone_index = 0  # Reset to most recent
        
    def detect_zones(self, swings: List[SwingPoint], candles: List[Candle]) -> List[DrawingZone]:
        """Detect and set drawing zones from swings and candles.
        
        Args:
            swings: All swing points
            candles: Candle data
            
        Returns:
            List of detected zones
        """
        self.zones = detect_drawing_zones(swings, candles)
        self.active_zone_index = 0
        return self.zones
    
    @property
    def active_zone(self) -> Optional[DrawingZone]:
        """Get the currently active zone."""
        # If live zone is set, return it
        if self._live_zone is not None:
            return self._live_zone
        if 0 <= self.active_zone_index < len(self.zones):
            return self.zones[self.active_zone_index]
        return None
    
    def set_live_zone(self, zone: DrawingZone) -> None:
        """Set a synthetic live zone (from end of prev_zone to current).
        
        Args:
            zone: The synthetic live zone
        """
        self._live_zone = zone
        self.active_zone_index = -1  # -1 indicates live zone
    
    def clear_live_zone(self) -> None:
        """Clear the synthetic live zone."""
        self._live_zone = None
    
    def set_active_zone(self, index: int) -> Optional[DrawingZone]:
        """Set the active zone by index.
        
        Args:
            index: Zone index (0 = most recent)
            
        Returns:
            The newly active zone, or None if invalid index
        """
        if 0 <= index < len(self.zones):
            self.active_zone_index = index
            return self.zones[index]
        return None
    
    def next_zone(self) -> Optional[DrawingZone]:
        """Move to the next (older) zone."""
        if self.active_zone_index < len(self.zones) - 1:
            self.active_zone_index += 1
            return self.active_zone
        return None
    
    def prev_zone(self) -> Optional[DrawingZone]:
        """Move to the previous (newer) zone."""
        if self.active_zone_index > 0:
            self.active_zone_index -= 1
            return self.active_zone
        return None
    
    # ========== FILTERING METHODS ==========
    
    def filter_by_zone(self, items: List, get_index: Callable) -> List:
        """Filter any list of items to only those within the active zone.
        
        Args:
            items: List of items to filter
            get_index: Function to extract index from an item
            
        Returns:
            Filtered list of items within the active zone
        """
        zone = self.active_zone
        if not zone:
            return items  # No zone, return all
            
        return [
            item for item in items
            if zone.contains_index(get_index(item))
        ]
    
    def filter_swings(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """Filter swings to only those within the active zone."""
        zone = self.active_zone
        if not zone:
            return swings
        
        # Include the boundary swings and everything in between
        return [
            s for s in swings
            if zone.start_index <= s.index <= zone.end_index
        ]
    
    def filter_structure_breaks(self, breaks: List[StructureBreak]) -> List[StructureBreak]:
        """Filter BOS events to only those within the active zone."""
        zone = self.active_zone
        if not zone:
            return breaks
            
        return [
            b for b in breaks
            if zone.start_index <= b.break_index <= zone.end_index
        ]
    
    def filter_character_changes(self, chochs: List[CharacterChange]) -> List[CharacterChange]:
        """Filter CHoCH events to only those within the active zone."""
        zone = self.active_zone
        if not zone:
            return chochs
            
        return [
            c for c in chochs
            if zone.start_index <= c.break_index <= zone.end_index
        ]
    
    def filter_fvgs(self, fvgs: List[FairValueGap]) -> List[FairValueGap]:
        """Filter FVGs to only those within the active zone."""
        zone = self.active_zone
        if not zone:
            return fvgs
            
        return [
            f for f in fvgs
            if zone.start_index <= f.index <= zone.end_index
        ]
    
    def filter_liquidity_pools(self, pools: List[LiquidityPool]) -> List[LiquidityPool]:
        """Filter liquidity pools to only those within the active zone."""
        zone = self.active_zone
        if not zone:
            return pools
            
        return [
            p for p in pools
            if zone.start_index <= p.index <= zone.end_index
        ]
    
    def filter_protected_levels(self, levels: List[ProtectedLevel]) -> List[ProtectedLevel]:
        """Filter protected levels to those created within the active zone."""
        zone = self.active_zone
        if not zone:
            return levels
            
        return [
            l for l in levels
            if zone.start_index <= l.index <= zone.end_index
        ]
    
    def filter_snapshot(self, snapshot) -> Dict[str, Any]:
        """Filter an entire MarketSnapshot to only show the active zone's data.
        
        This is the main entry point for filtering. It returns a dictionary
        with all the filtered data ready for the frontend.
        
        Args:
            snapshot: MarketSnapshot object
            
        Returns:
            Dictionary with filtered data for rendering
        """
        from dataclasses import asdict
        
        zone = self.active_zone
        
        # Get the zones to display
        zones_to_show = self.zones if self.show_all_zones else ([zone] if zone else [])
        
        # When show_all_zones is True, return ALL data without filtering (live zone mode)
        should_filter = zone and not self.show_all_zones
        
        # Filter all collections (or return all if show_all_zones)
        filtered_swings = self.filter_swings(snapshot.swings) if should_filter else snapshot.swings
        filtered_bos = self.filter_structure_breaks(snapshot.structure_breaks) if should_filter else snapshot.structure_breaks
        filtered_choch = self.filter_character_changes(snapshot.character_changes) if should_filter else snapshot.character_changes
        filtered_fvgs = self.filter_fvgs(snapshot.fair_value_gaps) if should_filter else snapshot.fair_value_gaps
        filtered_levels = self.filter_protected_levels(snapshot.protected_levels) if should_filter else snapshot.protected_levels
        filtered_pools = self.filter_liquidity_pools(snapshot.liquidity_pools) if should_filter else snapshot.liquidity_pools
        filtered_moves = snapshot.moves
        if should_filter:
            filtered_moves = [
                move for move in snapshot.moves
                if move.start_index <= zone.end_index
                and (move.end_index is None or move.end_index >= zone.start_index)
            ]
        
        return {
            "active_zone": zone.to_dict() if zone else None,
            "active_zone_index": self.active_zone_index,
            "total_zones": len(self.zones),
            "zones": [z.to_dict() for z in zones_to_show],
            "swings": [asdict(s) for s in filtered_swings],
            "structure_breaks": [asdict(b) for b in filtered_bos],
            "character_changes": [asdict(c) for c in filtered_choch],
            "fair_value_gaps": [asdict(f) for f in filtered_fvgs],
            "protected_levels": [asdict(l) for l in filtered_levels],
            "liquidity_pools": [asdict(p) for p in filtered_pools],
            "moves": [asdict(move) for move in filtered_moves],
            # Include metadata
            "current_price": snapshot.current_price,
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe,
            "bias": snapshot.bias,
        }
    
    def get_zone_summary(self) -> Dict[str, Any]:
        """Get a summary of all zones for UI display."""
        return {
            "total_zones": len(self.zones),
            "active_zone_index": self.active_zone_index,
            "active_zone": self.active_zone.to_dict() if self.active_zone else None,
            "zones": [
                {
                    "index": i,
                    "direction": z.direction.value if isinstance(z.direction, ZoneDirection) else z.direction,
                    "candle_count": z.candle_count,
                    "swing_count": z.swing_count,
                    "is_active": i == self.active_zone_index
                }
                for i, z in enumerate(self.zones)
            ]
        }
    
    def get_zone_name(self, index: int) -> str:
        """Get the human-readable name for a zone index.
        
        Naming scheme:
        - "live" = special zone from last external swing to current (index -1)
        - "prev" = most recent completed zone (index 0)
        - "zone_a" = second most recent (index 1)
        - "zone_b" = third most recent (index 2)
        - etc.
        """
        if index == -1:
            return "live"
        elif index == 0:
            return "prev"
        else:
            # Convert index 1 -> 'a', 2 -> 'b', etc.
            letter = chr(ord('a') + index - 1)
            return f"zone_{letter}"
    
    def get_index_from_name(self, name: str) -> int:
        """Convert zone name back to index.
        
        Args:
            name: Zone name ("live", "prev", "zone_a", "zone_b", etc.)
            
        Returns:
            Zone index (-1 for live, 0 for prev, 1 for zone_a, etc.)
        """
        name = name.lower().strip()
        if name == "live":
            return -1
        elif name == "prev":
            return 0
        elif name.startswith("zone_"):
            letter = name.replace("zone_", "")
            if len(letter) == 1 and letter.isalpha():
                return ord(letter) - ord('a') + 1
        return 0  # Default to prev
    
    def get_zone_info(self, candles: List[Candle] = None) -> Dict[str, Any]:
        """Get comprehensive zone information with proper naming.
        
        Returns a dict with:
        - displayed_zone: name and details of currently displayed zone
        - live_zone: info about the live zone (last external to current)
        - all_zones: list of all zones with names
        
        Args:
            candles: Optional candle data to calculate live zone bounds
        """
        # Build named zones list
        named_zones = []
        for i, zone in enumerate(self.zones):
            name = self.get_zone_name(i)
            named_zones.append({
                "name": name,
                "index": i,
                "direction": zone.direction.value if isinstance(zone.direction, ZoneDirection) else zone.direction,
                "start_index": zone.start_index,
                "end_index": zone.end_index,
                "candle_count": zone.candle_count,
                "swing_count": zone.swing_count,
                "is_displayed": i == self.active_zone_index,
            })
        
        # Get displayed zone info
        displayed = None
        if 0 <= self.active_zone_index < len(self.zones):
            zone = self.zones[self.active_zone_index]
            displayed = {
                "name": self.get_zone_name(self.active_zone_index),
                "index": self.active_zone_index,
                "direction": zone.direction.value if isinstance(zone.direction, ZoneDirection) else zone.direction,
                "start_index": zone.start_index,
                "end_index": zone.end_index,
                "candle_count": zone.candle_count,
            }
        
        # Calculate live zone (from end of prev_zone to current candle)
        live_zone = None
        if self.zones and candles:
            prev_zone = self.zones[0]  # Most recent completed zone
            last_candle_index = len(candles) - 1
            
            # Live zone starts where prev_zone ends
            live_zone = {
                "name": "live",
                "start_index": prev_zone.end_index,
                "end_index": last_candle_index,
                "candle_count": last_candle_index - prev_zone.end_index + 1,
                "direction": "developing",  # Not yet determined
            }
        
        return {
            "displayed_zone": displayed,
            "displayed_zone_name": self.get_zone_name(self.active_zone_index) if displayed else None,
            "live_zone": live_zone,
            "total_completed_zones": len(self.zones),
            "all_zones": named_zones,
            "navigation": {
                "can_go_older": self.active_zone_index < len(self.zones) - 1,
                "can_go_newer": self.active_zone_index > 0,
                "can_go_live": self.active_zone_index != -1,
            }
        }
    
    def go_to_zone_by_name(self, name: str) -> Optional[DrawingZone]:
        """Navigate to a zone by name.
        
        Args:
            name: Zone name ("live", "prev", "zone_a", etc.)
            
        Returns:
            The zone if found, None otherwise
        """
        index = self.get_index_from_name(name)
        if index == -1:
            # Live zone - special handling
            self.active_zone_index = -1
            return None  # Live zone is synthetic
        return self.set_active_zone(index)


# ========== CONVENIENCE FUNCTIONS ==========

def render_for_zone(snapshot, zone_index: int = 0) -> Dict[str, Any]:
    """Convenience function to get filtered data for a specific zone.
    
    Args:
        snapshot: MarketSnapshot object
        zone_index: Which zone to filter to (0 = most recent)
        
    Returns:
        Filtered data dictionary ready for frontend rendering
    """
    orchestrator = RenderOrchestrator()
    orchestrator.detect_zones(snapshot.swings, [])  # Zones should already be in snapshot
    
    # Use snapshot's drawing_zones if available
    if hasattr(snapshot, 'drawing_zones') and snapshot.drawing_zones:
        # Convert from dict to DrawingZone if needed
        zones = []
        for z in snapshot.drawing_zones:
            if isinstance(z, DrawingZone):
                zones.append(z)
            elif isinstance(z, dict):
                zones.append(DrawingZone(
                    id=z.get('id', ''),
                    direction=ZoneDirection(z.get('direction', 'bullish')),
                    start_timestamp=z.get('start_timestamp', 0),
                    start_price=z.get('start_price', 0),
                    start_index=z.get('start_index', 0),
                    start_swing_id=z.get('start_swing_id', ''),
                    start_kind=z.get('start_kind', ''),
                    end_timestamp=z.get('end_timestamp', 0),
                    end_price=z.get('end_price', 0),
                    end_index=z.get('end_index', 0),
                    end_swing_id=z.get('end_swing_id', ''),
                    end_kind=z.get('end_kind', ''),
                    zone_high=z.get('zone_high', 0),
                    zone_low=z.get('zone_low', 0),
                    zone_high_index=z.get('zone_high_index', 0),
                    zone_low_index=z.get('zone_low_index', 0),
                    candle_count=z.get('candle_count', 0),
                    swing_count=z.get('swing_count', 0),
                ))
        orchestrator.set_zones(zones)
    
    orchestrator.set_active_zone(zone_index)
    return orchestrator.filter_snapshot(snapshot)
