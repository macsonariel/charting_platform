"""Core Pipeline - Orchestrates all detection stages.

This module provides the core analysis pipeline that runs all
detectors and produces a MarketSnapshot containing all detected facts.
"""
from typing import List, Optional
from dataclasses import dataclass

from backend.chart.engines.core.schemas import (
    Candle, MarketSnapshot, SwingPoint, StructureBreak, CharacterChange,
    Leg, ProtectedLevel, PriceRange, LiquidityPool, LiquiditySweep, FairValueGap
)
from backend.chart.engines.core.detectors import (
    detect_swings, score_swings, classify_swings,
    detect_structure_events, detect_legs, track_levels,
    detect_fvgs, detect_ranges,
)
from backend.chart.engines.core.detectors.swing_detector import SwingDetectorConfig
from backend.chart.engines.core.detectors.direction_detector import detect_direction
from backend.chart.engines.core.detectors.range_detector import detect_range_position
from backend.chart.engines.core.detectors.sr_detector import detect_sr_zones
from backend.chart.engines.core.detectors.htf_swing_classifier import (
    classify_swings_from_htf, get_htf_for_timeframe
)
from backend.chart.rendering import detect_drawing_zones
from backend.chart.engines.core.trackers import collect_recent_events
from backend.chart.engines.core.analyzers import (
    analyze_actionable,
    analyze_market,
    analyze_regime,
    regime_interpretation,
)


class Pipeline:
    """Core analysis pipeline.
    
    Runs all detection stages in the correct order and produces
    a complete MarketSnapshot.
    
    Stage Order:
    1. Swings (no dependencies)
    2. Structure (depends on swings)  
    3. Levels (depends on swings, structure)
    4. Legs (depends on swings)
    5. Liquidity (depends on swings)
    6. FVGs (no dependencies)
    7. Ranges (no dependencies)
    8. Recent Events (depends on structure, sweeps, fvgs)
    9. Canonical Regime (single interpretation of detected facts)
    10. Actionable Context and presentation analysis (consume regime)
    """
    
    def _get_lookback_for_timeframe(self, timeframe: str) -> int:
        """Get appropriate lookback for timeframe.
        
        This matches the PA Engine's configuration to ensure consistent
        swing detection across both engines.
        """
        lookback_map = {
            "1m": 3,
            "5m": 3,
            "15m": 3,
            "30m": 4,
            "1h": 4,
            "4h": 5,
            "1d": 5,
            "1w": 7,
            "1M": 7
        }
        return lookback_map.get(timeframe, 3)
    
    def run(
        self,
        candles: List[Candle],
        symbol: str,
        timeframe: str,
        htf_swings: Optional[List[SwingPoint]] = None
    ) -> MarketSnapshot:
        """Run the full analysis pipeline.
        
        Args:
            candles: Input candle data
            symbol: Trading symbol (e.g., "BTCUSDT")
            timeframe: Timeframe string (e.g., "1h")
            htf_swings: Optional higher timeframe swings for external classification
            
        Returns:
            MarketSnapshot with all detected elements
        """
        if not candles:
            return MarketSnapshot(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=0,
                current_price=0.0
            )
        
        # Get current price and timestamp
        current_price = candles[-1].close
        timestamp = candles[-1].timestamp
        current_index = len(candles) - 1
        
        # Stage 1: Swings - use timeframe-appropriate lookback
        lookback = self._get_lookback_for_timeframe(timeframe)
        config = SwingDetectorConfig(lookback=lookback)
        swings = detect_swings(candles, timeframe, config)
        swings = score_swings(candles, swings)
        
        # Stage 1b: Classify swings (HH/HL/LH/LL labels)
        from backend.chart.engines.core.detectors.swing_classifier import classify_swings
        swings = classify_swings(swings)
        
        # Stage 1c: HTF-based external classification
        # If HTF swings are provided, classify LTF swings as external/internal
        htf = get_htf_for_timeframe(timeframe)
        if htf_swings and htf:
            swings = classify_swings_from_htf(swings, htf_swings, htf, ltf_timeframe=timeframe)
        
        # Stage 2: Structure (depends on swings) - detects BOS, CHoCH, moves
        swings, structure_breaks, character_changes, moves = detect_structure_events(
            candles, swings, timeframe
        )
        for move in moves:
            if 0 <= move.start_index < len(candles):
                move.start_timestamp = candles[move.start_index].timestamp
            if move.end_index is not None and 0 <= move.end_index < len(candles):
                move.end_timestamp = candles[move.end_index].timestamp
        
        
        # Stage 3: Levels (depends on swings, structure)
        protected_levels = track_levels(
            swings, structure_breaks, candles, timeframe
        )
        
        # Stage 4: Legs (depends on swings)
        legs = detect_legs(candles, swings, timeframe)
        
        # Stage 5: Liquidity (depends on swings, structure, protected_levels)
        from backend.chart.engines.core.detectors.liquidity_detector import analyze_liquidity
        liquidity_result = analyze_liquidity(
            swings=swings,
            candles=candles,
            structure_breaks=structure_breaks,
            protected_levels=protected_levels,
            timeframe=timeframe
        )
        liquidity_pools = liquidity_result.intact_pools + liquidity_result.swept_pools
        sweeps = liquidity_result.recent_sweeps
        
        # Stage 6: FVGs (no dependencies)
        fvgs = detect_fvgs(candles, timeframe)
        
        # Stage 7: Ranges (no dependencies)
        ranges = detect_ranges(candles, timeframe, swings=swings)
        
        # Stage 7b: S/R Zones (depends on swings)
        sr_analysis = detect_sr_zones(swings, candles, timeframe)
        
        # Find external swings (highest/lowest significance)
        external_high = None
        external_low = None
        external_swings = [s for s in swings if s.degree == "external"]
        if external_swings:
            highs = [s for s in external_swings if s.kind == "high"]
            lows = [s for s in external_swings if s.kind == "low"]
            if highs:
                external_high = max(highs, key=lambda s: s.index)
            if lows:
                external_low = max(lows, key=lambda s: s.index)
        
        # Stage 7c: Drawing Zones (depends on external swings)
        drawing_zones = detect_drawing_zones(swings, candles)
        
        # Stage 8a: Direction Analysis (from alternating structural swings).
        # External swings are authoritative only when they form a complete
        # pattern. Otherwise the result explicitly falls back to all swings.
        direction_analysis = select_direction_analysis(
            swings=swings,
            external_swings=external_swings,
            timeframe=timeframe,
            htf_timeframe=htf if htf_swings else None,
        )
        direction_swings = (
            external_swings
            if direction_analysis.swing_degree == "external"
            else swings
        )
        
        # NEW Stage 8b: Range Position (premium/discount/equilibrium)
        active_ranges = [price_range for price_range in ranges if price_range.active]
        if active_ranges:
            active_range = max(active_ranges, key=lambda price_range: price_range.start_index)
            range_position = detect_range_position(
                current_price=current_price,
                range_high=active_range.high,
                range_low=active_range.low,
            )
        else:
            range_position = detect_range_position(
                current_price=current_price,
                external_high=external_high,
                external_low=external_low,
                swings=direction_swings,
            )
        
        # Stage 8: Collect recent events ("What just happened?")
        recent_events = collect_recent_events(
            structure_breaks=structure_breaks,
            character_changes=character_changes,
            sweeps=sweeps,
            fvgs=fvgs,
            max_events=10,
            current_index=current_index
        )
        
        # Build the fact snapshot before interpretation.
        snapshot = MarketSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            current_price=current_price,
            swings=swings,
            external_high=external_high,
            external_low=external_low,
            structure_breaks=structure_breaks,
            character_changes=character_changes,
            legs=legs,
            protected_levels=protected_levels,
            ranges=ranges,
            liquidity_pools=liquidity_pools,
            recent_sweeps=sweeps,
            fair_value_gaps=fvgs,
            moves=moves,                              # Market moves
            bias="neutral",
            direction_analysis=direction_analysis,
            range_position=range_position,
            sr_analysis=sr_analysis,
            drawing_zones=drawing_zones,              # Drawing zones
            recent_events=recent_events,
        )

        # Stage 9: one canonical interpretation of the completed Core facts.
        regime = analyze_regime(snapshot)
        snapshot.regime = regime
        snapshot.bias = regime.bias
        snapshot.interpretation = regime_interpretation(snapshot, regime)

        # Stage 10: consumers of the canonical regime.
        snapshot.actionable = analyze_actionable(
            current_price=current_price,
            bias=regime.bias,
            structure_breaks=structure_breaks,
            character_changes=character_changes,
            protected_levels=protected_levels,
            fair_value_gaps=fvgs,
            liquidity_pools=liquidity_pools,
        )
        analysis = analyze_market(snapshot)
        snapshot.analysis = analysis

        return snapshot


def select_direction_analysis(
    swings: List[SwingPoint],
    external_swings: List[SwingPoint],
    timeframe: str,
    htf_timeframe: Optional[str] = None,
):
    """Select a complete structural direction and record its provenance."""
    if external_swings:
        external_result = detect_direction(external_swings, count=4)
        if len(external_result.pattern_swings) >= 4:
            external_result.source = (
                "htf_matched_external" if htf_timeframe else "structural_external"
            )
            external_result.source_timeframe = htf_timeframe or timeframe
            external_result.swing_degree = "external"
            external_result.fallback_used = False
            external_result.quality = (
                "high" if external_result.direction != "neutral" else "mixed"
            )
            return external_result

    result = detect_direction(swings, count=4)
    result.source = "all_structural_swings"
    result.source_timeframe = timeframe
    result.swing_degree = "mixed"
    result.fallback_used = bool(external_swings)
    result.quality = (
        "medium"
        if len(result.pattern_swings) >= 4 and result.direction != "neutral"
        else "mixed"
        if len(result.pattern_swings) >= 4
        else "insufficient"
    )
    return result


def run_pipeline(
    candles: List[Candle],
    symbol: str,
    timeframe: str,
    htf_swings: Optional[List[SwingPoint]] = None
) -> MarketSnapshot:
    """Functional API for running the core pipeline.
    
    Args:
        candles: Input candle data
        symbol: Trading symbol
        timeframe: Timeframe string
        htf_swings: Optional HTF swings for external classification
        
    Returns:
        MarketSnapshot with all detected elements
    """
    pipeline = Pipeline()
    return pipeline.run(candles, symbol, timeframe, htf_swings)


__all__ = ["Pipeline", "run_pipeline", "select_direction_analysis"]
