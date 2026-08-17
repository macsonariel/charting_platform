"""Volume Analyzer - Core volume analysis logic.

Analyzes:
- Relative volume (vs SMA)
- Volume conditions
- Volume-price confirmation/divergence
- Accumulation/Distribution patterns
"""

from typing import List, Tuple
from backend.chart.engines.core.schemas import Candle
from backend.chart.engines.indicators.volume.schemas import (
    VolumeProfile,
    VolumeBar,
    VolumeCondition,
)


class VolumeAnalyzer:
    """Analyzer for volume characteristics."""
    
    def __init__(self, sma_period: int = 20):
        """Initialize volume analyzer.
        
        Args:
            sma_period: Period for volume SMA calculation (default 20)
        """
        self.sma_period = sma_period
    
    def analyze(self, candles: List[Candle]) -> Tuple[VolumeProfile, List[VolumeBar]]:
        """Analyze volume for the given candles.
        
        Args:
            candles: List of candles with volume data
            
        Returns:
            Tuple of (VolumeProfile, List[VolumeBar])
        """
        if not candles:
            return VolumeProfile(), []
        
        # Analyze individual bars
        volume_bars = self._analyze_bars(candles)
        
        # Build aggregate profile
        profile = self._build_profile(candles, volume_bars)
        
        return profile, volume_bars
    
    def analyze_bar(self, candle: Candle, volume_sma: float) -> VolumeBar:
        """Analyze a single candle's volume.
        
        Args:
            candle: Candle to analyze
            volume_sma: Current volume SMA for comparison
            
        Returns:
            VolumeBar with analysis
        """
        rel_vol = candle.volume / volume_sma if volume_sma > 0 else 1.0
        condition = self._get_condition(rel_vol)
        
        # Price direction
        if candle.close > candle.open:
            price_dir = "up"
        elif candle.close < candle.open:
            price_dir = "down"
        else:
            price_dir = "neutral"
        
        is_confirm = self._check_confirmation(candle, rel_vol)
        is_diverge = self._check_divergence(candle, rel_vol)
        
        return VolumeBar(
            index=0,  # Will be set by caller
            timestamp=candle.timestamp,
            volume=candle.volume,
            volume_sma=volume_sma,
            relative_volume=rel_vol,
            condition=condition,
            price_direction=price_dir,
            is_confirmation=is_confirm,
            is_divergence=is_diverge,
            is_exhaustion=condition == VolumeCondition.CLIMACTIC,
        )
    
    def _analyze_bars(self, candles: List[Candle]) -> List[VolumeBar]:
        """Analyze volume for each candle."""
        bars = []
        
        for i, candle in enumerate(candles):
            # Calculate SMA for this position
            start_idx = max(0, i - self.sma_period + 1)
            window = candles[start_idx:i+1]
            sma = sum(c.volume for c in window) / len(window) if window else 0
            
            bar = self.analyze_bar(candle, sma)
            bar.index = i
            bars.append(bar)
        
        return bars
    
    def _get_condition(self, relative_volume: float) -> VolumeCondition:
        """Determine volume condition from relative volume."""
        if relative_volume < 0.5:
            return VolumeCondition.VERY_LOW
        elif relative_volume < 0.8:
            return VolumeCondition.LOW
        elif relative_volume < 1.2:
            return VolumeCondition.AVERAGE
        elif relative_volume < 2.0:
            return VolumeCondition.HIGH
        elif relative_volume < 3.0:
            return VolumeCondition.VERY_HIGH
        else:
            return VolumeCondition.CLIMACTIC
    
    def _check_confirmation(self, candle: Candle, rel_vol: float) -> bool:
        """Check if volume confirms the price move."""
        price_move = abs(candle.close - candle.open) / candle.open if candle.open > 0 else 0
        return rel_vol > 1.2 and price_move > 0.005  # 0.5% move with above avg volume
    
    def _check_divergence(self, candle: Candle, rel_vol: float) -> bool:
        """Check if volume diverges from price."""
        price_move = abs(candle.close - candle.open) / candle.open if candle.open > 0 else 0
        
        # Big move on low volume = divergence
        if price_move > 0.01 and rel_vol < 0.8:
            return True
        # Small move on very high volume = potential reversal
        if price_move < 0.003 and rel_vol > 2.0:
            return True
        return False
    
    def _build_profile(self, candles: List[Candle], bars: List[VolumeBar]) -> VolumeProfile:
        """Build aggregate volume profile."""
        if not candles or not bars:
            return VolumeProfile()
        
        volumes = [c.volume for c in candles]
        
        # Calculate aggregate metrics
        up_vol = sum(c.volume for c in candles if c.close > c.open)
        down_vol = sum(c.volume for c in candles if c.close < c.open)
        
        # Count high/low volume bars
        high_count = sum(1 for b in bars if b.condition in {
            VolumeCondition.HIGH, VolumeCondition.VERY_HIGH, VolumeCondition.CLIMACTIC
        })
        low_count = sum(1 for b in bars if b.condition in {
            VolumeCondition.LOW, VolumeCondition.VERY_LOW
        })
        
        # Determine trend confirmation
        vol_ratio = up_vol / down_vol if down_vol > 0 else 2.0
        if vol_ratio > 1.3:
            trend_conf = "bullish"
        elif vol_ratio < 0.7:
            trend_conf = "bearish"
        else:
            trend_conf = "neutral"
        
        # Detect patterns
        exhaustion = any(b.is_exhaustion for b in bars[-5:])
        
        # Simple accumulation/distribution detection
        recent_bars = bars[-20:] if len(bars) >= 20 else bars
        recent_candles = candles[-20:] if len(candles) >= 20 else candles
        
        price_change = (recent_candles[-1].close - recent_candles[0].open) / recent_candles[0].open if recent_candles[0].open > 0 else 0
        accumulation = price_change < 0.02 and vol_ratio > 1.2
        distribution = price_change > -0.02 and vol_ratio < 0.8
        
        return VolumeProfile(
            start_index=0,
            end_index=len(candles) - 1,
            total_volume=sum(volumes),
            average_volume=sum(volumes) / len(volumes),
            max_volume=max(volumes),
            min_volume=min(volumes),
            up_volume=up_vol,
            down_volume=down_vol,
            volume_ratio=vol_ratio,
            high_volume_bars=high_count,
            low_volume_bars=low_count,
            trend_confirmation=trend_conf,
            exhaustion_detected=exhaustion,
            accumulation_detected=accumulation,
            distribution_detected=distribution,
        )


def analyze_volume(candles: List[Candle], sma_period: int = 20) -> Tuple[VolumeProfile, List[VolumeBar]]:
    """Convenience function to analyze volume.
    
    Args:
        candles: List of candles with volume data
        sma_period: Period for volume SMA calculation
        
    Returns:
        Tuple of (VolumeProfile, List[VolumeBar])
    """
    analyzer = VolumeAnalyzer(sma_period=sma_period)
    return analyzer.analyze(candles)

