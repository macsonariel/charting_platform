"""Swing Strength - Quality scoring for swings.

CONTRACT:
- FACT DETECTION ONLY  
- NO interpretation

Scoring:
- Calculates swing strength based on price prominence
- Higher strength = more significant swing
"""
from typing import List

from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.swing import SwingPoint


class SwingStrengthScorer:
    """Score swing quality based on prominence."""
    
    def score(
        self,
        candles: List[Candle],
        swings: List[SwingPoint]
    ) -> List[SwingPoint]:
        """Score swing strength."""
        if not swings or not candles:
            return swings
        
        sorted_swings = sorted(swings, key=lambda s: s.index)
        
        price_range = max(c.high for c in candles) - min(c.low for c in candles)
        if price_range == 0:
            price_range = 1
        
        scored: List[SwingPoint] = []
        
        for swing in sorted_swings:
            strength = self._calculate_strength(candles, swing, price_range)
            
            scored.append(SwingPoint(
                id=swing.id,
                index=swing.index,
                timestamp=swing.timestamp,
                price=swing.price,
                kind=swing.kind,
                degree=swing.degree,  # Preserve existing degree (set by swing_classifier)
                strength=strength,
                label=swing.label,
                valid=swing.valid,
                timeframe=swing.timeframe
            ))
        
        return scored
    
    def _calculate_strength(
        self,
        candles: List[Candle],
        swing: SwingPoint,
        price_range: float
    ) -> float:
        """Calculate swing strength based on prominence."""
        lookback = min(5, swing.index)
        lookahead = min(5, len(candles) - swing.index - 1)
        
        if swing.kind == "high":
            neighbors = [
                candles[swing.index - i].high for i in range(1, lookback + 1)
            ] + [
                candles[swing.index + i].high for i in range(1, lookahead + 1)
            ]
            prominence = swing.price - max(neighbors) if neighbors else 0
        else:
            neighbors = [
                candles[swing.index - i].low for i in range(1, lookback + 1)
            ] + [
                candles[swing.index + i].low for i in range(1, lookahead + 1)
            ]
            prominence = min(neighbors) - swing.price if neighbors else 0
        
        strength = min(1.0, max(0.0, prominence / price_range * 10))
        return round(strength, 3)


def score_swings(
    candles: List[Candle],
    swings: List[SwingPoint]
) -> List[SwingPoint]:
    """Functional API for swing scoring."""
    scorer = SwingStrengthScorer()
    return scorer.score(candles, swings)
