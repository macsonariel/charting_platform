"""Level Tracker - Track protected levels.

CONTRACT:
- FACT DETECTION ONLY
- NO interpretation

A protected level remains valid ONLY until price breaks it.
"""
from typing import List, Optional

from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.structure import StructureBreak
from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.range import ProtectedLevel


def generate_id(prefix: str) -> str:
    import time
    import random
    return f"{prefix}_{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


class LevelTracker:
    """Track protected highs and lows.
    
    Protected High: Broken when price closes above
    Protected Low: Broken when price closes below
    """
    
    def __init__(self, price_tolerance_pct: float = 0.001):
        self.price_tolerance_pct = price_tolerance_pct
    
    def track(
        self,
        swings: List[SwingPoint],
        structure_breaks: List[StructureBreak],
        candles: List[Candle],
        timeframe: str
    ) -> List[ProtectedLevel]:
        """Track protected levels with strength scoring."""
        levels: List[ProtectedLevel] = []
        
        break_info = self._build_break_map(structure_breaks)
        total_candles = len(candles)
        
        for swing in swings:
            if not swing.valid:
                continue
            
            # Check structure break
            is_struct_broken, break_ts = self._check_structure_break(swing, break_info)
            
            # Check price break
            is_price_broken, price_break_ts = self._check_price_break(swing, candles)
            
            is_broken = is_struct_broken or is_price_broken
            final_break_ts = break_ts if is_struct_broken else price_break_ts
            
            # Get swing degree for strength calculation
            swing_degree = getattr(swing, 'degree', 'internal')
            
            # Calculate strength
            strength = self._calculate_strength(
                swing_degree=swing_degree,
                is_broken=is_broken,
                swing_index=swing.index,
                total_candles=total_candles
            )
            
            levels.append(ProtectedLevel(
                id=generate_id("pl"),
                price=swing.price,
                kind=swing.kind,
                swing_id=swing.id,
                index=swing.index,
                timestamp=swing.timestamp,
                timeframe=timeframe,
                broken=is_broken,
                break_timestamp=final_break_ts,
                swing_degree=swing_degree,
                strength=strength
            ))
        
        return levels
    
    def _calculate_strength(
        self,
        swing_degree: str,
        is_broken: bool,
        swing_index: int,
        total_candles: int
    ) -> float:
        """Calculate strength score (0-1) for protected level.
        
        Factors:
        - Swing degree (external = 0.4, internal = 0.2)
        - Valid (not broken) = 0.3
        - Recency (newer = stronger, up to 0.3)
        """
        strength = 0.0
        
        # Degree factor (0-0.4)
        if swing_degree == "external":
            strength += 0.4
        else:
            strength += 0.2
        
        # Valid factor (0-0.3)
        if not is_broken:
            strength += 0.3
        
        # Recency factor (0-0.3)
        if total_candles > 0:
            age = total_candles - swing_index
            recency = max(0, 1.0 - (age / total_candles))
            strength += recency * 0.3
        
        return min(1.0, strength)
    
    def _build_break_map(self, breaks: List[StructureBreak]) -> List[dict]:
        return [
            {'level': sb.level, 'timestamp': sb.break_timestamp}
            for sb in breaks
        ]
    
    def _check_structure_break(self, swing: SwingPoint, break_info: List[dict]) -> tuple:
        tolerance = swing.price * self.price_tolerance_pct
        for info in break_info:
            if abs(info['level'] - swing.price) <= tolerance:
                return True, info['timestamp']
        return False, None
    
    def _check_price_break(self, swing: SwingPoint, candles: List[Candle]) -> tuple:
        for candle in candles:
            if candle.timestamp <= swing.timestamp:
                continue
            
            if swing.kind == "low" and candle.close < swing.price:
                return True, candle.timestamp
            elif swing.kind == "high" and candle.close > swing.price:
                return True, candle.timestamp
        
        return False, None


def track_levels(
    swings: List[SwingPoint],
    structure_breaks: List[StructureBreak],
    candles: List[Candle],
    timeframe: str
) -> List[ProtectedLevel]:
    """Functional API for level tracking."""
    tracker = LevelTracker()
    return tracker.track(swings, structure_breaks, candles, timeframe)
