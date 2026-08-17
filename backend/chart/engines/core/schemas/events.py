"""Events - Recent market event tracking.

This module provides the RecentEvent dataclass for tracking
what just happened in the market - capturing significant events
like structure breaks, character changes, sweeps, and FVG fills.

Usage:
    from backend.chart.engines.core.schemas import RecentEvent
    
    event = RecentEvent(
        event_type="BOS",
        direction="bullish",
        price=95420.50,
        timestamp=1704567890000,
        significance=0.7,
        description="Bullish BOS at 95,420",
        source_id="sb_123456_789"
    )
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class EventType(str, Enum):
    """Types of significant market events."""
    BOS = "BOS"                     # Break of Structure
    CHOCH = "CHoCH"                 # Change of Character
    SWEEP = "SWEEP"                 # Liquidity sweep
    FVG_CREATED = "FVG_CREATED"     # Fair value gap formed
    FVG_FILLED = "FVG_FILLED"       # Fair value gap filled/mitigated
    LEVEL_TESTED = "LEVEL_TESTED"   # Protected level tested
    LEVEL_BROKEN = "LEVEL_BROKEN"   # Protected level broken
    SWING_FORMED = "SWING_FORMED"   # New external swing formed


# Significance scores for each event type
EVENT_SIGNIFICANCE = {
    EventType.CHOCH: 1.0,           # Highest - reversal signal
    EventType.SWEEP: 0.9,           # High - liquidity taken
    EventType.BOS: 0.7,             # Moderate - continuation
    EventType.LEVEL_BROKEN: 0.7,    # Moderate - structure change
    EventType.LEVEL_TESTED: 0.6,    # Moderate - reaction zone
    EventType.FVG_CREATED: 0.5,     # Lower - imbalance
    EventType.FVG_FILLED: 0.5,      # Lower - rebalancing
    EventType.SWING_FORMED: 0.4,    # Lower - structure point
}


@dataclass
class RecentEvent:
    """A significant market event.
    
    Used to track "what just happened" - the most recent
    and important events that traders should be aware of.
    
    Attributes:
        event_type: Type of event (BOS, CHoCH, SWEEP, etc.)
        direction: Direction of the event ("bullish" or "bearish")
        price: Price level where event occurred
        timestamp: Unix timestamp in milliseconds
        significance: Importance score 0.0-1.0
        description: Human-readable event description
        source_id: ID of the source object (e.g., structure break ID)
        index: Candle index where event occurred (optional)
    """
    event_type: str
    direction: str
    price: float
    timestamp: int
    significance: float
    description: str
    source_id: str
    index: Optional[int] = None
    
    @classmethod
    def from_structure_break(cls, sb, is_choch: bool = False) -> 'RecentEvent':
        """Create event from a structure break."""
        # Check if this is a CHoCH by flag or type (handle both "CHoCH" and "CHOCH" strings)
        sb_type = getattr(sb, 'type', 'BOS')
        is_choch_event = is_choch or sb_type in ("CHoCH", "CHOCH", "choch")
        
        event_type_enum = EventType.CHOCH if is_choch_event else EventType.BOS
        event_type_str = event_type_enum.value  # "CHoCH" or "BOS"
        
        direction = "bullish" if sb.direction == "up" else "bearish"
        significance = EVENT_SIGNIFICANCE.get(event_type_enum, 0.5)
        
        return cls(
            event_type=event_type_str,
            direction=direction,
            price=sb.break_price,
            timestamp=sb.break_timestamp,
            significance=significance,
            description=f"{direction.title()} {event_type_str} at {sb.break_price:,.2f}",
            source_id=sb.id,
            index=sb.break_index
        )
    
    @classmethod
    def from_sweep(cls, sweep) -> 'RecentEvent':
        """Create event from a liquidity sweep."""
        # Sweeping below lows takes sell-side liquidity and is bullish;
        # sweeping above highs takes buy-side liquidity and is bearish.
        direction = "bullish" if sweep.direction == "down" else "bearish"
        
        # Handle both PA LiquiditySweep (timestamp) and Core LiquiditySweep (sweep_timestamp)
        ts = getattr(sweep, 'sweep_timestamp', None) or getattr(sweep, 'timestamp', 0)
        
        return cls(
            event_type="SWEEP",
            direction=direction,
            price=sweep.sweep_price,
            timestamp=ts,
            significance=EVENT_SIGNIFICANCE[EventType.SWEEP],
            description=f"{direction.title()} sweep at {sweep.sweep_price:,.2f}",
            source_id=sweep.id
        )
    
    @classmethod
    def from_fvg(cls, fvg, event_type: str = "FVG_CREATED") -> 'RecentEvent':
        """Create event from an FVG (created or filled)."""
        is_fill = event_type == "FVG_FILLED"
        direction = fvg.direction
        price = (fvg.high + fvg.low) / 2  # Midpoint
        
        action = "filled" if is_fill else "formed"
        
        return cls(
            event_type=event_type,
            direction=direction,
            price=price,
            timestamp=fvg.timestamp,
            significance=EVENT_SIGNIFICANCE[EventType[event_type]],
            description=f"{direction.title()} FVG {action} at {price:,.2f}",
            source_id=fvg.id
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type,
            "direction": self.direction,
            "price": self.price,
            "timestamp": self.timestamp,
            "significance": self.significance,
            "description": self.description,
            "source_id": self.source_id,
            "index": self.index
        }
