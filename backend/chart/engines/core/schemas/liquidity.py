"""Liquidity - Comprehensive liquidity analysis models.

Covers:
- Stop-loss liquidity (swing highs/lows)
- Trend liquidity (building during trends)
- Range liquidity (equal levels at boundaries)
- Inducement (internal swing traps)
- Sweep detection and tracking
- Strength analysis
- Structure interaction
- Liquidity sequencing
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class LiquiditySide(str, Enum):
    """Side of liquidity relative to price."""
    BUY_SIDE = "buy_side"     # Above price (stops for shorts)
    SELL_SIDE = "sell_side"   # Below price (stops for longs)


class LiquidityPoolType(str, Enum):
    """Type/source of liquidity pool."""
    STOP_LOSS = "stop_loss"       # Standard swing high/low
    TREND = "trend"               # Building during trend (HLs, LHs)
    RANGE = "range"               # Equal levels at range bounds
    INDUCEMENT = "inducement"     # Internal swings (traps)
    PROTECTED = "protected"       # Protected structural levels


@dataclass
class LiquidityPool:
    """Liquidity Pool - Area of resting orders.
    
    Buy-side liquidity: Above swing highs (stop losses of shorts)
    Sell-side liquidity: Below swing lows (stop losses of longs)
    """
    id: str
    price: float
    side: str                     # "buy_side" or "sell_side"
    pool_type: str = "stop_loss"  # LiquidityPoolType value
    
    # Source data
    swing_ids: List[str] = field(default_factory=list)
    swing_degree: str = "internal"  # "external" or "internal"
    
    # Strength factors
    touch_count: int = 1          # Times price approached without sweep
    strength: float = 0.5         # 0-1 composite strength
    
    # Metadata
    timestamp: int = 0
    index: int = 0
    timeframe: str = ""
    
    # Sweep status
    swept: bool = False
    sweep_timestamp: Optional[int] = None
    sweep_depth: float = 0.0      # How far past the pool
    
    # Structure context
    above_protected: bool = False   # Is above a protected level
    below_protected: bool = False   # Is below a protected level
    
    @property
    def is_buy_side(self) -> bool:
        return self.side == "buy_side"
    
    @property
    def is_sell_side(self) -> bool:
        return self.side == "sell_side"
    
    @property
    def is_intact(self) -> bool:
        return not self.swept
    
    @property
    def is_external(self) -> bool:
        return self.swing_degree == "external"


@dataclass
class LiquiditySweep:
    """Liquidity Sweep - Taking of resting orders.
    
    Occurs when price moves through a liquidity pool
    and takes out stop losses.
    """
    id: str
    pool_id: str
    sweep_price: float
    direction: str              # "up" or "down"
    sweep_index: int
    sweep_timestamp: int
    depth: float = 0.0
    timeframe: str = ""
    levels_swept: int = 1       # How many liquidity levels were swept in one move
    
    # Post-sweep behavior
    rejected: bool = False      # Price rejected after sweep
    continuation: bool = False  # Price continued through
    
    @property
    def is_bullish_sweep(self) -> bool:
        """Sweep under lows (sell-side taken), leads to bullish."""
        return self.direction == "down"
    
    @property
    def is_bearish_sweep(self) -> bool:
        """Sweep above highs (buy-side taken), leads to bearish."""
        return self.direction == "up"
    
    @property
    def timestamp(self) -> int:
        """Alias for sweep_timestamp for backwards compatibility."""
        return self.sweep_timestamp


@dataclass
class LiquidityAnalysis:
    """Complete liquidity analysis result.
    
    Aggregates all liquidity detection into actionable context.
    """
    # Pools by side
    buy_side_pools: List[LiquidityPool] = field(default_factory=list)
    sell_side_pools: List[LiquidityPool] = field(default_factory=list)
    
    # By status
    intact_pools: List[LiquidityPool] = field(default_factory=list)
    swept_pools: List[LiquidityPool] = field(default_factory=list)
    
    # Recent sweeps
    recent_sweeps: List[LiquiditySweep] = field(default_factory=list)
    
    # Sequencing
    next_target: Optional[LiquidityPool] = None
    sequence: List[LiquidityPool] = field(default_factory=list)
    
    # Context
    structure_context: str = ""     # "above protected low", etc.
    trend_liquidity_side: str = ""  # Which side is building
    
    # Summary
    buy_side_count: int = 0
    sell_side_count: int = 0
    total_intact: int = 0
    total_swept: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "buy_side_count": len(self.buy_side_pools),
            "sell_side_count": len(self.sell_side_pools),
            "intact_count": len(self.intact_pools),
            "swept_count": len(self.swept_pools),
            "next_target": self.next_target.price if self.next_target else None,
            "next_target_side": self.next_target.side if self.next_target else None,
            "structure_context": self.structure_context,
            "trend_liquidity": self.trend_liquidity_side,
        }


@dataclass
class FairValueGap:
    """Fair Value Gap (FVG) - Price imbalance.
    
    Created when price moves so fast it leaves an unfilled gap.
    
    Strength Scoring (0-1):
    - Size relative to price (larger = stronger, capped)
    - Unfilled percentage (100% unfilled = stronger)
    - Recency (newer gaps more relevant)
    """
    id: str
    direction: str              # "bullish" or "bearish"
    high: float
    low: float
    midpoint: float
    timestamp: int
    index: int
    filled: bool = False
    fill_percentage: float = 0.0
    fill_timestamp: Optional[int] = None
    timeframe: str = ""
    strength: float = 0.5       # 0-1 composite score
    
    @property
    def size(self) -> float:
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        return self.direction == "bullish"
    
    @property
    def is_bearish(self) -> bool:
        return self.direction == "bearish"
    
    @property
    def is_intact(self) -> bool:
        """True if gap is not fully filled (< 100%)."""
        return self.fill_percentage < 1.0
    
    @property
    def unfilled_percentage(self) -> float:
        """Percentage of gap still unfilled."""
        return 1.0 - self.fill_percentage

