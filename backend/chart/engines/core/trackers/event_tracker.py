"""Event Tracker - Collects and tracks recent significant events.

This module provides the EventTracker class which collects events
from various sources (structure breaks, sweeps, FVGs, etc.) and
maintains a sorted list of the most recent and significant events.
"""
from typing import List, Optional
from dataclasses import dataclass

from backend.chart.engines.core.schemas.events import RecentEvent


@dataclass
class EventTrackerConfig:
    """Configuration for event tracking."""
    max_events: int = 10         # Maximum events to keep
    lookback_count: int = 50     # Only consider events from last N candles


class EventTracker:
    """Tracks and collects significant market events.
    
    Collects events from:
    - Structure breaks (BOS/CHoCH)
    - Liquidity sweeps
    - FVG creation/filling
    - Protected level tests/breaks
    
    Maintains a sorted list of events by recency and significance.
    """
    
    def __init__(self, config: Optional[EventTrackerConfig] = None):
        self.config = config or EventTrackerConfig()
        self.events: List[RecentEvent] = []
    
    def clear(self):
        """Clear all tracked events."""
        self.events = []
    
    def add_event(self, event: RecentEvent):
        """Add a single event to the tracker."""
        self.events.append(event)
    
    def add_events(self, events: List[RecentEvent]):
        """Add multiple events to the tracker."""
        self.events.extend(events)
    
    def collect_from_structure_breaks(self, structure_breaks: List, character_changes: List = None):
        """Collect events from structure breaks and character changes.
        
        Args:
            structure_breaks: List of StructureBreak objects
            character_changes: List of CharacterChange objects (optional)
        """
        # Structure breaks (BOS)
        for sb in structure_breaks:
            event = RecentEvent.from_structure_break(sb, is_choch=False)
            self.add_event(event)
        
        # Character changes (CHoCH)
        if character_changes:
            for cc in character_changes:
                # CharacterChange has similar structure to StructureBreak
                event = RecentEvent(
                    event_type="CHoCH",
                    direction="bullish" if cc.direction == "up" else "bearish",
                    price=cc.break_price,
                    timestamp=cc.break_timestamp,
                    significance=1.0,  # Highest significance
                    description=f"{'Bullish' if cc.direction == 'up' else 'Bearish'} CHoCH at {cc.break_price:,.2f}",
                    source_id=cc.id,
                    index=cc.break_index
                )
                self.add_event(event)
    
    def collect_from_sweeps(self, sweeps: List):
        """Collect events from liquidity sweeps.
        
        Args:
            sweeps: List of LiquiditySweep objects
        """
        for sweep in sweeps:
            event = RecentEvent.from_sweep(sweep)
            self.add_event(event)
    
    def collect_from_fvgs(self, fvgs: List, previous_fvgs: List = None):
        """Collect events from FVGs.
        
        Tracks both newly created FVGs and recently filled ones.
        
        Args:
            fvgs: Current list of FairValueGap objects
            previous_fvgs: Previous list to detect fills (optional)
        """
        for fvg in fvgs:
            # Track FVG creation (unfilled = newly formed)
            if not fvg.filled:
                event = RecentEvent.from_fvg(fvg, "FVG_CREATED")
                self.add_event(event)
            # Track FVG fill events
            elif fvg.filled and fvg.fill_percentage and fvg.fill_percentage >= 50:
                event = RecentEvent.from_fvg(fvg, "FVG_FILLED")
                self.add_event(event)
    
    def get_recent_events(
        self,
        max_events: Optional[int] = None,
        min_significance: float = 0.0,
        current_index: Optional[int] = None
    ) -> List[RecentEvent]:
        """Get the most recent and significant events.
        
        Args:
            max_events: Maximum number of events to return
            min_significance: Minimum significance threshold
            current_index: Current candle index for lookback filtering
            
        Returns:
            List of RecentEvent sorted by timestamp (most recent first)
        """
        max_events = max_events or self.config.max_events
        
        # Filter by significance
        filtered = [e for e in self.events if e.significance >= min_significance]
        
        # Filter by lookback if current_index provided
        if current_index is not None:
            lookback_start = current_index - self.config.lookback_count
            filtered = [e for e in filtered if e.index is None or e.index >= lookback_start]
        
        # Sort by timestamp (most recent first), then by significance
        def get_timestamp(e):
            # Handle case where timestamp is a method (defensive coding)
            val = e.timestamp
            if callable(val):
                return val()
            return val

        sorted_events = sorted(
            filtered,
            key=lambda e: (get_timestamp(e), e.significance),
            reverse=True
        )
        
        # Return top N
        return sorted_events[:max_events]


def collect_recent_events(
    structure_breaks: List = None,
    character_changes: List = None,
    sweeps: List = None,
    fvgs: List = None,
    max_events: int = 10,
    current_index: Optional[int] = None
) -> List[RecentEvent]:
    """Functional API for collecting recent events.
    
    Convenience function that creates an EventTracker, collects events
    from all sources, and returns the sorted recent events.
    
    Args:
        structure_breaks: List of StructureBreak objects
        character_changes: List of CharacterChange objects
        sweeps: List of LiquiditySweep objects
        fvgs: List of FairValueGap objects
        max_events: Maximum events to return
        current_index: Current candle index for lookback
        
    Returns:
        List of RecentEvent sorted by recency
    """
    tracker = EventTracker()
    
    if structure_breaks or character_changes:
        tracker.collect_from_structure_breaks(
            structure_breaks or [],
            character_changes
        )
    
    if sweeps:
        tracker.collect_from_sweeps(sweeps)
    
    if fvgs:
        tracker.collect_from_fvgs(fvgs)
    
    return tracker.get_recent_events(
        max_events=max_events,
        current_index=current_index
    )
