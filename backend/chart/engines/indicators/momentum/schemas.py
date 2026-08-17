"""Momentum schemas - Data models for momentum analysis."""

from dataclasses import dataclass
from enum import Enum


class MomentumDivergence(str, Enum):
    """Types of momentum divergence."""
    NONE = "none"
    BULLISH = "bullish"      # Price lower low, momentum higher low
    BEARISH = "bearish"      # Price higher high, momentum lower high
    HIDDEN_BULLISH = "hidden_bullish"  # Price higher low, momentum lower low (trend continuation)
    HIDDEN_BEARISH = "hidden_bearish"  # Price lower high, momentum higher high (trend continuation)


@dataclass
class MomentumReading:
    """Momentum analysis result for a point in time."""
    # Direction and strength
    direction: str = "neutral"    # "bullish", "bearish", "neutral"
    strength: float = 0.0         # 0-1 scale
    
    # Rate of change
    roc: float = 0.0              # Rate of change (percentage)
    roc_smoothed: float = 0.0     # Smoothed ROC (less noisy)
    
    # Acceleration
    is_accelerating: bool = False  # Momentum getting stronger
    is_decelerating: bool = False  # Momentum getting weaker
    acceleration_rate: float = 0.0 # How fast it's accelerating/decelerating
    
    # Divergence
    divergence: MomentumDivergence = MomentumDivergence.NONE
    divergence_strength: float = 0.0  # 0-1 how significant the divergence is
    
    # Extremes
    is_overbought: bool = False   # Momentum at extreme high
    is_oversold: bool = False     # Momentum at extreme low
    
    @property
    def is_bullish(self) -> bool:
        return self.direction == "bullish"
    
    @property
    def is_bearish(self) -> bool:
        return self.direction == "bearish"
    
    @property
    def has_divergence(self) -> bool:
        return self.divergence != MomentumDivergence.NONE
    
    @property
    def has_reversal_signal(self) -> bool:
        """True if momentum suggests potential reversal."""
        return (
            self.divergence in {MomentumDivergence.BULLISH, MomentumDivergence.BEARISH} or
            self.is_overbought or
            self.is_oversold
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "direction": self.direction,
            "strength": self.strength,
            "roc": self.roc,
            "is_accelerating": self.is_accelerating,
            "is_decelerating": self.is_decelerating,
            "divergence": self.divergence.value,
            "is_overbought": self.is_overbought,
            "is_oversold": self.is_oversold,
        }

