"""
Time-Based Level Detector

Detects key price levels based on time periods:
- Previous Day High/Low (PDH/PDL)
- Previous Week High/Low (PWH/PWL)
- Previous Month High/Low (PMH/PML)
- Session Highs/Lows (Asian, London, NY)

These are critical levels for price action trading as they
often act as support/resistance due to high visibility.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import time

from backend.chart.engines.core.schemas.candle import Candle


@dataclass
class TimeLevel:
    """A time-based price level (PDH, PDL, etc.)"""
    id: str
    level_type: str         # "pdh", "pdl", "pwh", "pwl", "pmh", "pml"
    price: float
    timestamp: int          # When this level was formed
    period_start: int       # Start of the period
    period_end: int         # End of the period
    is_high: bool           # True if high, False if low
    strength: float = 0.7   # Base strength for time levels
    broken: bool = False
    break_timestamp: Optional[int] = None
    
    @property
    def zone_type(self) -> str:
        """Return S/R type for compatibility."""
        return "resistance" if self.is_high else "support"


@dataclass
class TimeLevelsAnalysis:
    """Complete time-based levels analysis."""
    previous_day_high: Optional[TimeLevel] = None
    previous_day_low: Optional[TimeLevel] = None
    previous_week_high: Optional[TimeLevel] = None
    previous_week_low: Optional[TimeLevel] = None
    previous_month_high: Optional[TimeLevel] = None
    previous_month_low: Optional[TimeLevel] = None
    all_levels: List[TimeLevel] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        levels = {}
        if self.previous_day_high:
            levels["pdh"] = self.previous_day_high.price
        if self.previous_day_low:
            levels["pdl"] = self.previous_day_low.price
        if self.previous_week_high:
            levels["pwh"] = self.previous_week_high.price
        if self.previous_week_low:
            levels["pwl"] = self.previous_week_low.price
        if self.previous_month_high:
            levels["pmh"] = self.previous_month_high.price
        if self.previous_month_low:
            levels["pml"] = self.previous_month_low.price
        return levels


def generate_id(prefix: str) -> str:
    import random
    return f"{prefix}_{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


class TimeLevelsDetector:
    """Detects time-based price levels like PDH, PDL, PWH, etc."""
    
    def __init__(
        self,
        include_daily: bool = True,
        include_weekly: bool = True,
        include_monthly: bool = True,
    ):
        self.include_daily = include_daily
        self.include_weekly = include_weekly
        self.include_monthly = include_monthly
    
    def detect(
        self,
        candles: List[Candle],
        timeframe: str,
    ) -> TimeLevelsAnalysis:
        """
        Detect time-based levels from candle data.
        
        Args:
            candles: List of candles
            timeframe: Current timeframe string
            
        Returns:
            TimeLevelsAnalysis with all detected levels
        """
        if not candles:
            return TimeLevelsAnalysis()
        
        result = TimeLevelsAnalysis()
        current_time = candles[-1].timestamp
        
        # Calculate period boundaries
        current_ms = current_time
        
        # Daily levels (need at least 1 full day of data)
        if self.include_daily:
            day_ms = 86400000  # 24 hours in ms
            prev_day_end = (current_ms // day_ms) * day_ms  # Start of today
            prev_day_start = prev_day_end - day_ms
            
            pdh, pdl = self._find_period_hl(candles, prev_day_start, prev_day_end)
            
            if pdh is not None:
                result.previous_day_high = TimeLevel(
                    id=generate_id("pdh"),
                    level_type="pdh",
                    price=pdh,
                    timestamp=current_time,
                    period_start=prev_day_start,
                    period_end=prev_day_end,
                    is_high=True,
                    strength=0.7,
                )
                result.all_levels.append(result.previous_day_high)
            
            if pdl is not None:
                result.previous_day_low = TimeLevel(
                    id=generate_id("pdl"),
                    level_type="pdl",
                    price=pdl,
                    timestamp=current_time,
                    period_start=prev_day_start,
                    period_end=prev_day_end,
                    is_high=False,
                    strength=0.7,
                )
                result.all_levels.append(result.previous_day_low)
        
        # Weekly levels
        if self.include_weekly:
            week_ms = 604800000  # 7 days in ms
            # Find start of current week (Monday)
            prev_week_end = (current_ms // week_ms) * week_ms
            prev_week_start = prev_week_end - week_ms
            
            pwh, pwl = self._find_period_hl(candles, prev_week_start, prev_week_end)
            
            if pwh is not None:
                result.previous_week_high = TimeLevel(
                    id=generate_id("pwh"),
                    level_type="pwh",
                    price=pwh,
                    timestamp=current_time,
                    period_start=prev_week_start,
                    period_end=prev_week_end,
                    is_high=True,
                    strength=0.8,
                )
                result.all_levels.append(result.previous_week_high)
            
            if pwl is not None:
                result.previous_week_low = TimeLevel(
                    id=generate_id("pwl"),
                    level_type="pwl",
                    price=pwl,
                    timestamp=current_time,
                    period_start=prev_week_start,
                    period_end=prev_week_end,
                    is_high=False,
                    strength=0.8,
                )
                result.all_levels.append(result.previous_week_low)
        
        # Monthly levels
        if self.include_monthly:
            month_ms = 2592000000  # ~30 days in ms
            prev_month_end = (current_ms // month_ms) * month_ms
            prev_month_start = prev_month_end - month_ms
            
            pmh, pml = self._find_period_hl(candles, prev_month_start, prev_month_end)
            
            if pmh is not None:
                result.previous_month_high = TimeLevel(
                    id=generate_id("pmh"),
                    level_type="pmh",
                    price=pmh,
                    timestamp=current_time,
                    period_start=prev_month_start,
                    period_end=prev_month_end,
                    is_high=True,
                    strength=0.9,
                )
                result.all_levels.append(result.previous_month_high)
            
            if pml is not None:
                result.previous_month_low = TimeLevel(
                    id=generate_id("pml"),
                    level_type="pml",
                    price=pml,
                    timestamp=current_time,
                    period_start=prev_month_start,
                    period_end=prev_month_end,
                    is_high=False,
                    strength=0.9,
                )
                result.all_levels.append(result.previous_month_low)
        
        # Check for broken levels
        self._check_broken(result.all_levels, candles)
        
        return result
    
    def _find_period_hl(
        self,
        candles: List[Candle],
        period_start: int,
        period_end: int,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Find the high and low for a specific time period.
        
        Returns:
            (high, low) or (None, None) if no candles in period
        """
        period_candles = [
            c for c in candles
            if period_start <= c.timestamp < period_end
        ]
        
        if not period_candles:
            return None, None
        
        high = max(c.high for c in period_candles)
        low = min(c.low for c in period_candles)
        
        return high, low
    
    def _check_broken(
        self,
        levels: List[TimeLevel],
        candles: List[Candle],
    ):
        """Check if any levels have been broken by recent price action."""
        for level in levels:
            for candle in candles:
                if candle.timestamp <= level.period_end:
                    continue
                
                # High levels broken when price closes above
                if level.is_high and candle.close > level.price:
                    level.broken = True
                    level.break_timestamp = candle.timestamp
                    break
                
                # Low levels broken when price closes below
                if not level.is_high and candle.close < level.price:
                    level.broken = True
                    level.break_timestamp = candle.timestamp
                    break


def detect_time_levels(
    candles: List[Candle],
    timeframe: str,
    include_daily: bool = True,
    include_weekly: bool = True,
    include_monthly: bool = True,
) -> TimeLevelsAnalysis:
    """
    Convenience function to detect time-based levels.
    
    Args:
        candles: List of candles
        timeframe: Current timeframe
        include_daily: Include PDH/PDL
        include_weekly: Include PWH/PWL
        include_monthly: Include PMH/PML
        
    Returns:
        TimeLevelsAnalysis with detected levels
    """
    detector = TimeLevelsDetector(
        include_daily=include_daily,
        include_weekly=include_weekly,
        include_monthly=include_monthly,
    )
    return detector.detect(candles, timeframe)
