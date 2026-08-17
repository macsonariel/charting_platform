"""Level Break Tracker - Track pending levels and delayed breaks.

This module tracks structural levels that could be broken in the future,
enabling detection of breaks that occur 2, 3, 4+ swings after the level
was established.

Uses structure_detector as the source of truth for CHoCH/BOS context.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.structure import StructureBreak, CharacterChange
from backend.chart.engines.core.schemas.pending_level import (
    PendingLevel, LevelStatus, LevelBreakEvent
)


def generate_id(prefix: str) -> str:
    """Generate unique ID."""
    import time
    import random
    return f"{prefix}_{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


class LevelBreakTracker:
    """Track pending structural levels and detect delayed breaks.
    
    Unlike immediate break detection, this tracks ALL swing levels
    and detects when they're broken even if it happens many swings later.
    
    Features:
    - Tracks how many swings/candles passed before break
    - Supports external-only or all swing tracking
    - Integrates with structure_detector for CHoCH/BOS classification
    """
    
    def __init__(self, external_only: bool = True):
        """Initialize tracker.
        
        Args:
            external_only: If True, only track external swings as pending levels
        """
        self.external_only = external_only
        self.pending_levels: List[PendingLevel] = []
        self._swing_count = 0
    
    def track(
        self,
        candles: List[Candle],
        swings: List[SwingPoint],
        timeframe: str = ""
    ) -> Tuple[List[LevelBreakEvent], List[PendingLevel]]:
        """Track levels and detect breaks.
        
        Args:
            candles: Price candles
            swings: Swing points (should be sorted by index)
            timeframe: Timeframe string
            
        Returns:
            Tuple of (break_events, pending_levels)
        """
        if not swings:
            return [], []
        
        sorted_swings = sorted(swings, key=lambda s: s.index)
        break_events: List[LevelBreakEvent] = []
        
        for swing in sorted_swings:
            # Increment swing count for all active pending levels
            for level in self.pending_levels:
                if level.is_active:
                    level.swings_since_creation += 1
                    level.candles_since_creation = swing.index - level.created_index
            
            # Check if this swing breaks any pending levels
            breaks = self._check_breaks(swing)
            break_events.extend(breaks)
            
            # Add new pending level for this swing (if applicable)
            should_track = (
                not self.external_only or 
                swing.degree == "external"
            )
            
            if should_track:
                self._add_pending_level(swing, timeframe)
        
        return break_events, self.pending_levels
    
    def _check_breaks(self, swing: SwingPoint) -> List[LevelBreakEvent]:
        """Check if a swing breaks any pending levels."""
        breaks: List[LevelBreakEvent] = []
        
        for level in self.pending_levels:
            if not level.is_active:
                continue
            
            # Check for break
            is_break = False
            break_direction = ""
            
            if level.kind == "high" and swing.price > level.price:
                # Price broke above the high level
                is_break = True
                break_direction = "up"
                
            elif level.kind == "low" and swing.price < level.price:
                # Price broke below the low level
                is_break = True
                break_direction = "down"
            
            if is_break:
                # Mark level as broken
                level.status = LevelStatus.BROKEN
                level.broken_at_index = swing.index
                level.broken_at_timestamp = swing.timestamp
                level.broken_by_swing_id = swing.id
                level.broken_by_price = swing.price
                
                # Create break event
                breaks.append(LevelBreakEvent(
                    level_id=level.id,
                    level_price=level.price,
                    level_kind=level.kind,
                    break_direction=break_direction,
                    break_price=swing.price,
                    break_index=swing.index,
                    break_timestamp=swing.timestamp,
                    swing_id=level.swing_id,
                    breaking_swing_id=swing.id,
                    swings_delayed=level.swings_since_creation,
                    candles_delayed=level.candles_since_creation,
                    is_external_break=level.is_external,
                    timeframe=level.timeframe
                ))
        
        return breaks
    
    def _add_pending_level(self, swing: SwingPoint, timeframe: str) -> None:
        """Add a new pending level from a swing."""
        level = PendingLevel(
            id=generate_id("lvl"),
            price=swing.price,
            kind=swing.kind,
            swing_id=swing.id,
            created_index=swing.index,
            created_timestamp=swing.timestamp,
            timeframe=timeframe,
            is_external=swing.degree == "external"
        )
        self.pending_levels.append(level)
    
    def get_active_levels(self) -> List[PendingLevel]:
        """Get all levels that haven't been broken yet."""
        return [l for l in self.pending_levels if l.is_active]
    
    def get_broken_levels(self) -> List[PendingLevel]:
        """Get all levels that have been broken."""
        return [l for l in self.pending_levels if l.is_broken]
    
    def clear(self) -> None:
        """Clear all tracked levels."""
        self.pending_levels = []


def track_level_breaks(
    candles: List[Candle],
    swings: List[SwingPoint],
    timeframe: str = "",
    external_only: bool = True
) -> Tuple[List[LevelBreakEvent], List[PendingLevel]]:
    """Functional API for level break tracking.
    
    Args:
        candles: Price candles
        swings: Swing points to track
        timeframe: Timeframe string
        external_only: If True, only track external swings
        
    Returns:
        Tuple of (break_events, pending_levels)
    """
    tracker = LevelBreakTracker(external_only=external_only)
    return tracker.track(candles, swings, timeframe)
