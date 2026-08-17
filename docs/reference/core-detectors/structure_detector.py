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
from typing import List, Optional

from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.structure import StructureBreak, CharacterChange


def generate_id(prefix: str) -> str:
    """Generate unique ID."""
    import time
    import random
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
    ) -> tuple:
        """Detect structure events with proper CHoCH logic.
        
        CHoCH only occurs when:
        - Bullish CHoCH: Break above protected high during a downtrend
        - Bearish CHoCH: Break below protected low during an uptrend
        
        Returns:
            Tuple of (structure_breaks, character_changes)
        """
        if len(swings) < 3:
            return [], []
        
        structure_breaks: List[StructureBreak] = []
        character_changes: List[CharacterChange] = []
        
        sorted_swings = sorted(swings, key=lambda s: s.index)
        
        # Current trend direction
        current_trend: Optional[str] = None
        
        # Protected levels - breaking these signals CHoCH
        protected_high: Optional[SwingPoint] = None  # Protected in downtrend
        protected_low: Optional[SwingPoint] = None   # Protected in uptrend
        
        # Track most recent swings
        last_high: Optional[SwingPoint] = None
        last_low: Optional[SwingPoint] = None
        
        for swing in sorted_swings:
            if swing.kind == "high":
                if last_high is not None:
                    threshold = last_high.price * (1 + self.min_break_percent)
                    if swing.price > threshold:
                        # Determine if CHoCH: must break protected high in downtrend
                        is_choch = False
                        if current_trend == "down" and protected_high is not None:
                            if swing.price > protected_high.price * (1 + self.min_break_percent):
                                is_choch = True
                        
                        if is_choch:
                            character_changes.append(CharacterChange(
                                id=generate_id("choch"),
                                event_type="choch",
                                direction="up",
                                level=protected_high.price,
                                break_price=swing.price,
                                break_index=swing.index,
                                break_timestamp=swing.timestamp,
                                swing_id=swing.id,
                                strength=(swing.strength + protected_high.strength) / 2,
                                timeframe=timeframe,
                                type="CHoCH"
                            ))
                            # Trend reversed to up
                            current_trend = "up"
                            protected_low = last_low
                            protected_high = None
                        else:
                            structure_breaks.append(StructureBreak(
                                id=generate_id("bos"),
                                event_type="break",
                                direction="up",
                                level=last_high.price,
                                break_price=swing.price,
                                break_index=swing.index,
                                break_timestamp=swing.timestamp,
                                swing_id=swing.id,
                                strength=(swing.strength + last_high.strength) / 2,
                                timeframe=timeframe,
                                type="BOS"
                            ))
                            # Update trend if not in downtrend
                            if current_trend != "down":
                                current_trend = "up"
                                if last_low is not None:
                                    protected_low = last_low
                
                last_high = swing
                
                # In downtrend, track the highest high as protected
                if current_trend == "down":
                    if protected_high is None or swing.price > protected_high.price:
                        protected_high = swing
                
            elif swing.kind == "low":
                if last_low is not None:
                    threshold = last_low.price * (1 - self.min_break_percent)
                    if swing.price < threshold:
                        # Determine if CHoCH: must break protected low in uptrend
                        is_choch = False
                        if current_trend == "up" and protected_low is not None:
                            if swing.price < protected_low.price * (1 - self.min_break_percent):
                                is_choch = True
                        
                        if is_choch:
                            character_changes.append(CharacterChange(
                                id=generate_id("choch"),
                                event_type="choch",
                                direction="down",
                                level=protected_low.price,
                                break_price=swing.price,
                                break_index=swing.index,
                                break_timestamp=swing.timestamp,
                                swing_id=swing.id,
                                strength=(swing.strength + protected_low.strength) / 2,
                                timeframe=timeframe,
                                type="CHoCH"
                            ))
                            # Trend reversed to down
                            current_trend = "down"
                            protected_high = last_high
                            protected_low = None
                        else:
                            structure_breaks.append(StructureBreak(
                                id=generate_id("bos"),
                                event_type="break",
                                direction="down",
                                level=last_low.price,
                                break_price=swing.price,
                                break_index=swing.index,
                                break_timestamp=swing.timestamp,
                                swing_id=swing.id,
                                strength=(swing.strength + last_low.strength) / 2,
                                timeframe=timeframe,
                                type="BOS"
                            ))
                            # Update trend if not in uptrend
                            if current_trend != "up":
                                current_trend = "down"
                                if last_high is not None:
                                    protected_high = last_high
                
                last_low = swing
                
                # In uptrend, track the lowest low as protected
                if current_trend == "up":
                    if protected_low is None or swing.price < protected_low.price:
                        protected_low = swing
        
        return structure_breaks, character_changes


def detect_structure_events(
    candles: List[Candle],
    swings: List[SwingPoint],
    timeframe: str,
    min_break_percent: float = 0.001
) -> tuple:
    """Functional API for structure detection.
    
    Returns:
        Tuple of (structure_breaks, character_changes)
    """
    detector = StructureDetector(min_break_percent)
    return detector.detect(candles, swings, timeframe)
