"""Volume schemas - Data models for volume analysis."""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class VolumeCondition(str, Enum):
    """Volume condition relative to average."""
    VERY_LOW = "very_low"       # < 50% of average
    LOW = "low"                 # 50-80% of average
    AVERAGE = "average"         # 80-120% of average
    HIGH = "high"               # 120-200% of average
    VERY_HIGH = "very_high"     # > 200% of average
    CLIMACTIC = "climactic"     # > 300% of average (potential exhaustion)


@dataclass
class VolumeBar:
    """Volume analysis for a single candle."""
    index: int
    timestamp: int
    volume: float
    
    # Relative metrics
    volume_sma: float = 0.0         # Moving average (typically 20)
    relative_volume: float = 1.0    # Volume / SMA ratio
    condition: VolumeCondition = VolumeCondition.AVERAGE
    
    # Price-volume relationship
    price_direction: str = "neutral"  # "up", "down", "neutral"
    is_confirmation: bool = False     # Volume confirms price direction
    is_divergence: bool = False       # Volume diverges from price
    
    # Special conditions
    is_breakout_volume: bool = False  # High volume at key level break
    is_exhaustion: bool = False       # Climactic volume (potential reversal)
    
    @property
    def is_significant(self) -> bool:
        """True if volume is notable (high or very high)."""
        return self.condition in {
            VolumeCondition.HIGH, 
            VolumeCondition.VERY_HIGH, 
            VolumeCondition.CLIMACTIC
        }


@dataclass
class VolumeProfile:
    """Volume analysis over a range of candles.
    
    Provides aggregate volume metrics for trend analysis.
    """
    # Range
    start_index: int = 0
    end_index: int = 0
    
    # Aggregate metrics
    total_volume: float = 0.0
    average_volume: float = 0.0
    max_volume: float = 0.0
    min_volume: float = 0.0
    
    # Trend metrics
    up_volume: float = 0.0          # Volume on up candles
    down_volume: float = 0.0        # Volume on down candles
    volume_ratio: float = 1.0       # up_volume / down_volume
    
    # Distribution
    high_volume_bars: int = 0       # Count of high volume bars
    low_volume_bars: int = 0        # Count of low volume bars
    
    # Analysis
    trend_confirmation: str = "neutral"  # "bullish", "bearish", "neutral"
    exhaustion_detected: bool = False
    accumulation_detected: bool = False
    distribution_detected: bool = False
    
    # Volume clusters (price levels with high volume)
    volume_clusters: List[float] = field(default_factory=list)
    
    @property
    def is_healthy_uptrend(self) -> bool:
        """True if volume confirms uptrend (higher on up moves)."""
        return self.volume_ratio > 1.2 and self.trend_confirmation == "bullish"
    
    @property
    def is_healthy_downtrend(self) -> bool:
        """True if volume confirms downtrend (higher on down moves)."""
        return self.volume_ratio < 0.8 and self.trend_confirmation == "bearish"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "start_index": self.start_index,
            "end_index": self.end_index,
            "total_volume": self.total_volume,
            "average_volume": self.average_volume,
            "volume_ratio": self.volume_ratio,
            "trend_confirmation": self.trend_confirmation,
            "high_volume_bars": self.high_volume_bars,
            "exhaustion_detected": self.exhaustion_detected,
            "accumulation_detected": self.accumulation_detected,
            "distribution_detected": self.distribution_detected,
        }

