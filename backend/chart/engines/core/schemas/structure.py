"""Structure - Structure event data models.

REFACTORED per structure_detection_refactoring_guide.md:
- Added broken_swing_ids for multi-swing break tracking
- Added is_primary flag for primary CHoCH
- Added confirmed/invalidated flags for CHoCH

Neutral Terms:
- StructureBreak = Continuation (BOS in SMC)
- CharacterChange = Reversal (CHoCH in SMC)
- FailedBreak = Fakeout, trap
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class StructureEventType(str, Enum):
    """Type of structure event."""
    BREAK = "break"             # Continuation (BOS)
    CHARACTER_CHANGE = "choch"  # Reversal (CHoCH)
    FAILED_BREAK = "failed"     # Fakeout


@dataclass
class StructureEvent:
    """Base class for structure events.
    
    REFACTORED fields:
    - breaking_swing_* : The swing that caused this event
    - broken_swing_ids : All swings broken by this event (multi-swing)
    """
    id: str
    event_type: str             # "break", "choch", "failed"
    direction: str              # "up" or "down"
    
    # The swing that caused this event (REFACTORED)
    breaking_swing_id: str = ""
    breaking_swing_price: float = 0.0
    breaking_swing_index: int = 0
    breaking_swing_timestamp: int = 0
    
    # Swings that were broken (REFACTORED - multi-swing support)
    broken_swing_ids: List[str] = field(default_factory=list)
    broken_swing_prices: List[float] = field(default_factory=list)
    
    # Primary broken swing location (for label positioning)
    broken_swing_timestamp: int = 0
    broken_swing_index: int = 0
    
    # Backward compatibility (deprecated, use breaking_swing_*)
    level: float = 0.0                # Price level that was tested
    break_price: float = 0.0          # Actual break price
    break_index: int = 0              # Candle index of break
    break_timestamp: int = 0          # Timestamp of break
    swing_id: str = ""                # ID of swing that was broken
    
    # Classification
    severity: int = 1                 # Number of swings broken (total)
    protected_severity: int = 0       # Number of protected swings broken
    strength: float = 0.0             # 0-1 strength score
    timeframe: str = ""
    
    # Primary flag (NEW)
    is_primary: bool = False
    
    @property
    def is_bullish(self) -> bool:
        return self.direction == "up"
    
    @property
    def is_bearish(self) -> bool:
        return self.direction == "down"


@dataclass
class StructureBreak(StructureEvent):
    """Structure Break - Continuation event (BOS).
    
    Occurs when:
    - Price breaks above a previous swing high (bullish)
    - Price breaks below a previous swing low (bearish)
    
    Indicates: Trend continuation
    """
    type: str = "BOS"
    levels_broken: float = 0.0
    swings_delayed: int = 0
    candles_delayed: int = 0
    
    def __post_init__(self):
        self.event_type = "break"


@dataclass
class CharacterChange(StructureEvent):
    """Character Change - Reversal event (CHoCH).
    
    REFACTORED:
    - confirmed: BOS has broken the CHoCH swing
    - invalidated: External break canceled the CHoCH
    - also_bos: True when this CHoCH also breaks a recent swing (dual event)
    
    Occurs when:
    - Bearish structure breaks above protected high
    - Bullish structure breaks below protected low
    
    Indicates: Potential trend reversal (needs BOS confirmation)
    """
    type: str = "CHoCH"
    levels_broken: float = 0.0
    swings_delayed: int = 0
    candles_delayed: int = 0
    
    # CHoCH confirmation (NEW)
    confirmed: bool = False
    confirmed_by_id: Optional[str] = None
    
    # CHoCH invalidation (NEW)
    invalidated: bool = False
    invalidated_by_id: Optional[str] = None
    
    # Dual event tracking (CHoCH that also breaks a recent swing)
    also_bos: bool = False
    bos_broken_swing_id: Optional[str] = None
    bos_broken_swing_price: Optional[float] = None
    
    def __post_init__(self):
        self.event_type = "choch"


@dataclass
class FailedBreak(StructureEvent):
    """Failed Break - Trap/Fakeout event.
    
    Occurs when:
    - Price breaks a level but immediately reverses
    - Often a liquidity grab / stop hunt
    """
    type: str = "FAILED"
    
    def __post_init__(self):
        self.event_type = "failed"
