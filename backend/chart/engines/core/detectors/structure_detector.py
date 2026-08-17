"""Structure Detector - Detect StructureBreak and CharacterChange events.

CONTRACT:
- FACT DETECTION ONLY
- NO interpretation
- NO phase decisions

Events:
- StructureBreak (BOS) = Continuation (breaking non-protected swing)
- CharacterChange (CHoCH) = Reversal (breaking protected swing)

CHoCH LOGIC:
- A CHoCH ONLY occurs when breaking a PROTECTED swing level
- Protected swing = the key swing point that must hold for trend to continue
- In uptrend: the protected low is the most recent significant low
- In downtrend: the protected high is the most recent significant high
- Breaking a non-protected swing is always a BOS
"""
from typing import List, Optional, Tuple
import time
import random

from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.structure import StructureBreak, CharacterChange
from backend.chart.engines.core.schemas.move import Move


def generate_id(prefix: str) -> str:
    """Generate unique ID."""
    return f"{prefix}_{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


class StructureDetector:
    """Detect structure breaks and character changes.
    
    StructureBreak (BOS): Continuation
    - Breaking a non-protected swing in the direction of the trend
    
    CharacterChange (CHoCH): Reversal
    - Breaking a PROTECTED swing against the trend
    - In uptrend: Breaking the protected low (bullish to bearish)
    - In downtrend: Breaking the protected high (bearish to bullish)
    
    Protected Swing Tracking:
    - In uptrend: protected_low = last significant low before new high
    - In downtrend: protected_high = last significant high before new low
    """
    
    def __init__(self, min_break_percent: float = 0.001):
        self.min_break_percent = min_break_percent
    
    def detect(
        self,
        candles: List[Candle],
        swings: List[SwingPoint],
        timeframe: str
    ) -> Tuple[List[SwingPoint], List[StructureBreak], List[CharacterChange], List[Move]]:
        """Detect structure events with proper CHoCH logic.
        
        CHoCH only occurs when:
        - Bullish CHoCH: Break above protected high during a downtrend
        - Bearish CHoCH: Break below protected low during an uptrend
        
        Returns:
            Tuple of (swings, structure_breaks, character_changes, moves)
        """
        if len(swings) < 3:
            return swings, [], [], []
        
        structure_breaks: List[StructureBreak] = []
        character_changes: List[CharacterChange] = []
        moves: List[Move] = []
        
        sorted_swings = sorted(swings, key=lambda s: s.index)
        
        # Current trend direction
        current_trend: Optional[str] = None
        
        # Protected levels - breaking these signals CHoCH
        protected_high: Optional[SwingPoint] = None  # Protected in downtrend
        protected_low: Optional[SwingPoint] = None   # Protected in uptrend
        
        # Last swing that was marked as protected (for CHoCH detection)
        # These are the swings that, when broken, trigger CHoCH
        last_protected_high: Optional[SwingPoint] = None  # Last high marked is_protected=True
        last_protected_low: Optional[SwingPoint] = None   # Last low marked is_protected=True
        
        # Track most recent swings
        last_high: Optional[SwingPoint] = None
        last_low: Optional[SwingPoint] = None
        
        # Current move tracking
        current_move: Optional[Move] = None
        move_start_index: int = 0  # Track where the current move started (for severity counting)
        
        # Pending CHoCH - CHoCH signals potential reversal, but trend only changes after BOS confirms
        # When CHoCH occurs, we store the CHoCH swing. When BOS breaks it, trend changes.
        pending_choch_swing: Optional[SwingPoint] = None  # The swing that made the CHoCH
        pending_choch_direction: Optional[str] = None  # "up" or "down" - the new trend direction if confirmed
        
        for swing in sorted_swings:
            if swing.kind == "high":
                if last_high is not None:
                    threshold = last_high.price * (1 + self.min_break_percent)
                    if swing.price > threshold:
                        # Determine if CHoCH: must break LAST protected high in downtrend
                        is_choch = False
                        if current_trend == "down" and last_protected_high is not None:
                            if swing.price > last_protected_high.price * (1 + self.min_break_percent):
                                is_choch = True
                        
                        if is_choch:
                            # Check if this CHoCH also breaks a different swing (dual event)
                            also_breaks_last_high = (
                                last_high is not None and 
                                last_high.id != last_protected_high.id and
                                swing.price > last_high.price * (1 + self.min_break_percent)
                            )
                            
                            # Count highs that this CHoCH breaks (only from current move's origin)
                            broken_high_ids = []
                            broken_high_prices = []
                            protected_count = 0
                            for s in sorted_swings:
                                # Only count non-mitigated swings from the current move (since move_start_index)
                                if s.index >= move_start_index and s.index < swing.index and s.kind == "high" and not s.broken:
                                    if swing.price > s.price * (1 + self.min_break_percent):
                                        broken_high_ids.append(s.id)
                                        broken_high_prices.append(s.price)
                                        if s.is_protected:
                                            protected_count += 1
                            severity = len(broken_high_ids)
                            
                            choch = CharacterChange(
                                id=generate_id("choch"),
                                event_type="choch",
                                direction="up",
                                breaking_swing_id=swing.id,
                                breaking_swing_price=swing.price,
                                breaking_swing_index=swing.index,
                                breaking_swing_timestamp=swing.timestamp,
                                broken_swing_ids=broken_high_ids if broken_high_ids else [last_protected_high.id],
                                broken_swing_prices=broken_high_prices if broken_high_prices else [last_protected_high.price],
                                broken_swing_timestamp=last_protected_high.timestamp,
                                broken_swing_index=last_protected_high.index,
                                level=last_protected_high.price,
                                break_price=swing.price,
                                break_index=swing.index,
                                break_timestamp=swing.timestamp,
                                swing_id=last_protected_high.id,
                                severity=severity if severity > 0 else 1,
                                protected_severity=protected_count if protected_count > 0 else 1,
                                strength=(swing.strength + last_protected_high.strength) / 2,
                                timeframe=timeframe,
                                is_primary=True,
                                confirmed=True,
                                also_bos=also_breaks_last_high,
                                bos_broken_swing_id=last_high.id if also_breaks_last_high else None,
                                bos_broken_swing_price=last_high.price if also_breaks_last_high else None
                            )
                            character_changes.append(choch)
                            swing.is_choch = True
                            
                            # Mark last protected high as broken
                            last_protected_high.broken = True
                            last_protected_high.broken_by_id = swing.id
                            
                            # Set pending CHoCH - trend will change after BOS confirms
                            # The CHoCH swing needs to be broken by a BOS for trend to officially change
                            pending_choch_swing = swing
                            pending_choch_direction = "up"
                            
                            # Clear last_protected_high so no more CHoCHs trigger until confirmed
                            last_protected_high = None
                            
                            # Archive current move (but don't start new one yet)
                            if current_move:
                                current_move.state = "archived"
                                current_move.end_index = swing.index
                                moves.append(current_move)
                                current_move = None
                        else:
                            # Count highs that this BOS breaks (from current move's origin)
                            broken_high_ids = []
                            broken_high_prices = []
                            protected_count = 0
                            for s in sorted_swings:
                                # Only count non-mitigated swings from current move's origin
                                if s.index >= move_start_index and s.index < swing.index and s.kind == "high" and not s.broken:
                                    if swing.price > s.price * (1 + self.min_break_percent):
                                        broken_high_ids.append(s.id)
                                        broken_high_prices.append(s.price)
                                        if s.is_protected:
                                            protected_count += 1
                            severity = len(broken_high_ids) if broken_high_ids else 1
                            
                            bos = StructureBreak(
                                id=generate_id("bos"),
                                event_type="break",
                                direction="up",
                                breaking_swing_id=swing.id,
                                breaking_swing_price=swing.price,
                                breaking_swing_index=swing.index,
                                breaking_swing_timestamp=swing.timestamp,
                                broken_swing_ids=broken_high_ids if broken_high_ids else [last_high.id],
                                broken_swing_prices=broken_high_prices if broken_high_prices else [last_high.price],
                                broken_swing_timestamp=last_high.timestamp,
                                broken_swing_index=last_high.index,
                                level=last_high.price,
                                break_price=swing.price,
                                break_index=swing.index,
                                break_timestamp=swing.timestamp,
                                swing_id=last_high.id,
                                severity=severity,
                                protected_severity=protected_count,
                                strength=(swing.strength + last_high.strength) / 2,
                                timeframe=timeframe,
                                is_primary=True
                            )
                            structure_breaks.append(bos)
                            swing.is_bos = True
                            last_high.broken = True
                            last_high.broken_by_id = swing.id
                            
                            
                            # Check if this BOS confirms a pending upward CHoCH
                            if pending_choch_direction == "up" and pending_choch_swing is not None:
                                # BOS confirms CHoCH - trend officially changes
                                if swing.price > pending_choch_swing.price * (1 + self.min_break_percent):
                                    current_trend = "up"
                                    move_start_index = swing.index
                                    current_move = Move(
                                        id=generate_id("move"),
                                        direction="bullish",
                                        start_index=swing.index
                                    )
                                    if last_low is not None:
                                        protected_low = last_low
                                        protected_low.is_protected = True
                                        last_protected_low = protected_low
                                    protected_high = None
                                    
                                    
                                    # Clear pending CHoCH
                                    pending_choch_swing = None
                                    pending_choch_direction = None
                            # Otherwise, update trend if not in downtrend (normal BOS behavior)
                            elif current_trend != "down":
                                current_trend = "up"
                                if current_move is None:
                                    current_move = Move(
                                        id=generate_id("move"),
                                        direction="bullish",
                                        start_index=swing.index
                                    )
                                if last_low is not None:
                                    protected_low = last_low
                                    protected_low.is_protected = True
                                    last_protected_low = protected_low  # Track for CHoCH
                
                last_high = swing
                
                # In downtrend, track the highest high as protected (skip if pending CHoCH)
                if current_trend == "down" and pending_choch_direction != "up":
                    if protected_high is None or swing.price > protected_high.price:
                        if protected_high:
                            protected_high.is_protected = False
                        protected_high = swing
                        protected_high.is_protected = True
                        last_protected_high = protected_high  # Track for CHoCH
                
            elif swing.kind == "low":
                if last_low is not None:
                    threshold = last_low.price * (1 - self.min_break_percent)
                    if swing.price < threshold:
                        # Determine if CHoCH: must break LAST protected low in uptrend
                        is_choch = False
                        if current_trend == "up" and last_protected_low is not None:
                            if swing.price < last_protected_low.price * (1 - self.min_break_percent):
                                is_choch = True
                        
                        if is_choch:
                            # Check if this CHoCH also breaks a different swing (dual event)
                            also_breaks_last_low = (
                                last_low is not None and 
                                last_low.id != last_protected_low.id and
                                swing.price < last_low.price * (1 - self.min_break_percent)
                            )
                            # Count lows that this CHoCH breaks (only from current move's origin)
                            broken_low_ids = []
                            broken_low_prices = []
                            protected_count = 0
                            for s in sorted_swings:
                                # Only count non-mitigated swings from the current move (since move_start_index)
                                if s.index >= move_start_index and s.index < swing.index and s.kind == "low" and not s.broken:
                                    if swing.price < s.price * (1 - self.min_break_percent):
                                        broken_low_ids.append(s.id)
                                        broken_low_prices.append(s.price)
                                        if s.is_protected:
                                            protected_count += 1
                            severity = len(broken_low_ids)
                            
                            choch = CharacterChange(
                                id=generate_id("choch"),
                                event_type="choch",
                                direction="down",
                                breaking_swing_id=swing.id,
                                breaking_swing_price=swing.price,
                                breaking_swing_index=swing.index,
                                breaking_swing_timestamp=swing.timestamp,
                                broken_swing_ids=broken_low_ids if broken_low_ids else [last_protected_low.id],
                                broken_swing_prices=broken_low_prices if broken_low_prices else [last_protected_low.price],
                                broken_swing_timestamp=last_protected_low.timestamp,
                                broken_swing_index=last_protected_low.index,
                                level=last_protected_low.price,
                                break_price=swing.price,
                                break_index=swing.index,
                                break_timestamp=swing.timestamp,
                                swing_id=last_protected_low.id,
                                severity=severity if severity > 0 else 1,
                                protected_severity=protected_count if protected_count > 0 else 1,
                                strength=(swing.strength + last_protected_low.strength) / 2,
                                timeframe=timeframe,
                                is_primary=True,
                                confirmed=True,
                                also_bos=also_breaks_last_low,
                                bos_broken_swing_id=last_low.id if also_breaks_last_low else None,
                                bos_broken_swing_price=last_low.price if also_breaks_last_low else None
                            )
                            character_changes.append(choch)
                            swing.is_choch = True
                            
                            # Mark last protected low as broken
                            last_protected_low.broken = True
                            last_protected_low.broken_by_id = swing.id
                            
                            # Set pending CHoCH - trend will change after BOS confirms
                            pending_choch_swing = swing
                            pending_choch_direction = "down"
                            
                            # Clear last_protected_low so no more CHoCHs trigger until confirmed
                            last_protected_low = None
                            
                            # Archive current move (but don't start new one yet)
                            if current_move:
                                current_move.state = "archived"
                                current_move.end_index = swing.index
                                moves.append(current_move)
                                current_move = None
                        else:
                            # Count lows that this BOS breaks (from current move's origin)
                            broken_low_ids = []
                            broken_low_prices = []
                            protected_count = 0
                            for s in sorted_swings:
                                # Only count non-mitigated swings from current move's origin
                                if s.index >= move_start_index and s.index < swing.index and s.kind == "low" and not s.broken:
                                    if swing.price < s.price * (1 - self.min_break_percent):
                                        broken_low_ids.append(s.id)
                                        broken_low_prices.append(s.price)
                                        if s.is_protected:
                                            protected_count += 1
                            severity = len(broken_low_ids) if broken_low_ids else 1
                            
                            bos = StructureBreak(
                                id=generate_id("bos"),
                                event_type="break",
                                direction="down",
                                breaking_swing_id=swing.id,
                                breaking_swing_price=swing.price,
                                breaking_swing_index=swing.index,
                                breaking_swing_timestamp=swing.timestamp,
                                broken_swing_ids=broken_low_ids if broken_low_ids else [last_low.id],
                                broken_swing_prices=broken_low_prices if broken_low_prices else [last_low.price],
                                broken_swing_timestamp=last_low.timestamp,
                                broken_swing_index=last_low.index,
                                level=last_low.price,
                                break_price=swing.price,
                                break_index=swing.index,
                                break_timestamp=swing.timestamp,
                                swing_id=last_low.id,
                                severity=severity,
                                protected_severity=protected_count,
                                strength=(swing.strength + last_low.strength) / 2,
                                timeframe=timeframe,
                                is_primary=True
                            )
                            structure_breaks.append(bos)
                            swing.is_bos = True
                            last_low.broken = True
                            last_low.broken_by_id = swing.id
                            
                            
                            # Check if this BOS confirms a pending downward CHoCH
                            if pending_choch_direction == "down" and pending_choch_swing is not None:
                                # BOS confirms CHoCH - trend officially changes
                                if swing.price < pending_choch_swing.price * (1 - self.min_break_percent):
                                    current_trend = "down"
                                    move_start_index = swing.index
                                    current_move = Move(
                                        id=generate_id("move"),
                                        direction="bearish",
                                        start_index=swing.index
                                    )
                                    if last_high is not None:
                                        protected_high = last_high
                                        protected_high.is_protected = True
                                        last_protected_high = protected_high
                                    protected_low = None
                                    
                                    
                                    # Clear pending CHoCH
                                    pending_choch_swing = None
                                    pending_choch_direction = None
                            # Otherwise, update trend if not in uptrend (normal BOS behavior)
                            elif current_trend != "up":
                                current_trend = "down"
                                if current_move is None:
                                    current_move = Move(
                                        id=generate_id("move"),
                                        direction="bearish",
                                        start_index=swing.index
                                    )
                                if last_high is not None:
                                    protected_high = last_high
                                    protected_high.is_protected = True
                                    last_protected_high = protected_high  # Track for CHoCH
                
                last_low = swing
                
                # In uptrend, track the lowest low as protected (skip if pending CHoCH)
                if current_trend == "up" and pending_choch_direction != "down":
                    if protected_low is None or swing.price < protected_low.price:
                        if protected_low:
                            protected_low.is_protected = False
                        protected_low = swing
                        protected_low.is_protected = True
                        last_protected_low = protected_low  # Track for CHoCH
            
            # Associate swing with current move
            if current_move:
                swing.move_id = current_move.id
                current_move.swing_ids.append(swing.id)
        
        # Add final active move
        if current_move and current_move.state == "active":
            moves.append(current_move)
        
        return sorted_swings, structure_breaks, character_changes, moves


def detect_structure_events(
    candles: List[Candle],
    swings: List[SwingPoint],
    timeframe: str,
    min_break_percent: float = 0.001
) -> Tuple[List[SwingPoint], List[StructureBreak], List[CharacterChange], List[Move]]:
    """Functional API for structure detection.
    
    Returns:
        Tuple of (swings, structure_breaks, character_changes, moves)
    """
    detector = StructureDetector(min_break_percent)
    return detector.detect(candles, swings, timeframe)
