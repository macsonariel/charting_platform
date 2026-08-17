"""Comprehensive Liquidity Detector.

Detects and analyzes liquidity across 8 dimensions:
1. Stop-loss liquidity (swing highs/lows)
2. Trend liquidity (building during trends)
3. Range liquidity (equal levels at boundaries)
4. Inducement (internal swing traps)
5. Sweep detection and tracking
6. Strength analysis
7. Structure interaction
8. Liquidity sequencing
"""
from typing import List, Optional, Tuple
from dataclasses import dataclass
import time
import random

from backend.chart.engines.core.schemas.liquidity import (
    LiquidityPool, LiquiditySweep, LiquidityAnalysis,
    LiquiditySide, LiquidityPoolType
)
from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.candle import Candle


def generate_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


@dataclass
class LiquidityConfig:
    """Configuration for liquidity detection."""
    equal_threshold_pct: float = 0.002   # 0.2% for equal levels
    min_touch_count: int = 2             # Min touches for range liquidity
    external_strength_bonus: float = 0.3  # Bonus for external swings
    recency_weight: float = 0.2          # Weight for recent pools


class LiquidityDetector:
    """Comprehensive liquidity detector."""
    
    def __init__(self, config: Optional[LiquidityConfig] = None):
        self.config = config or LiquidityConfig()
    
    # =========================================================================
    # 1. STOP-LOSS LIQUIDITY
    # =========================================================================
    def detect_stop_loss_liquidity(
        self,
        swings: List[SwingPoint],
        timeframe: str
    ) -> List[LiquidityPool]:
        """Detect stop-loss liquidity at all swing points.
        
        Every swing high = buy-side liquidity (shorts' stops)
        Every swing low = sell-side liquidity (longs' stops)
        """
        pools = []
        
        for swing in swings:
            side = LiquiditySide.BUY_SIDE.value if swing.kind == "high" else LiquiditySide.SELL_SIDE.value
            degree = getattr(swing, 'degree', 'internal')
            
            # Base strength
            strength = 0.7 if degree == "external" else 0.4
            
            pools.append(LiquidityPool(
                id=generate_id("lp"),
                price=swing.price,
                side=side,
                pool_type=LiquidityPoolType.STOP_LOSS.value,
                swing_ids=[swing.id],
                swing_degree=degree,
                strength=strength,
                timestamp=swing.timestamp,
                index=swing.index,
                timeframe=timeframe
            ))
        
        return pools
    
    # =========================================================================
    # 2. TREND LIQUIDITY
    # =========================================================================
    def detect_trend_liquidity(
        self,
        swings: List[SwingPoint],
        structure_breaks: List,
        timeframe: str
    ) -> List[LiquidityPool]:
        """Detect liquidity building during trends.
        
        In uptrend: Higher lows = sell-side liquidity building
        In downtrend: Lower highs = buy-side liquidity building
        """
        pools = []
        
        if not structure_breaks:
            return pools
        
        # Determine trend from recent breaks
        recent = structure_breaks[-5:] if len(structure_breaks) >= 5 else structure_breaks
        bullish = sum(1 for b in recent if b.direction == "up")
        bearish = sum(1 for b in recent if b.direction == "down")
        
        if bullish > bearish:
            # Uptrend: HLs are building sell-side liquidity
            lows = [s for s in swings if s.kind == "low"]
            for i in range(1, len(lows)):
                if lows[i].price > lows[i-1].price:  # Higher low
                    pools.append(LiquidityPool(
                        id=generate_id("lp"),
                        price=lows[i].price,
                        side=LiquiditySide.SELL_SIDE.value,
                        pool_type=LiquidityPoolType.TREND.value,
                        swing_ids=[lows[i].id],
                        swing_degree=getattr(lows[i], 'degree', 'internal'),
                        strength=0.5,
                        timestamp=lows[i].timestamp,
                        index=lows[i].index,
                        timeframe=timeframe
                    ))
        
        elif bearish > bullish:
            # Downtrend: LHs are building buy-side liquidity
            highs = [s for s in swings if s.kind == "high"]
            for i in range(1, len(highs)):
                if highs[i].price < highs[i-1].price:  # Lower high
                    pools.append(LiquidityPool(
                        id=generate_id("lp"),
                        price=highs[i].price,
                        side=LiquiditySide.BUY_SIDE.value,
                        pool_type=LiquidityPoolType.TREND.value,
                        swing_ids=[highs[i].id],
                        swing_degree=getattr(highs[i], 'degree', 'internal'),
                        strength=0.5,
                        timestamp=highs[i].timestamp,
                        index=highs[i].index,
                        timeframe=timeframe
                    ))
        
        return pools
    
    # =========================================================================
    # 3. RANGE LIQUIDITY (Equal Levels)
    # =========================================================================
    def detect_range_liquidity(
        self,
        swings: List[SwingPoint],
        timeframe: str
    ) -> List[LiquidityPool]:
        """Detect liquidity at equal highs/lows (range boundaries)."""
        pools = []
        used_ids = set()
        
        for kind in ["high", "low"]:
            swings_of_kind = [s for s in swings if s.kind == kind]
            side = LiquiditySide.BUY_SIDE.value if kind == "high" else LiquiditySide.SELL_SIDE.value
            
            for i, sw1 in enumerate(swings_of_kind):
                if sw1.id in used_ids:
                    continue
                
                cluster = [sw1]
                tolerance = sw1.price * self.config.equal_threshold_pct
                
                for sw2 in swings_of_kind[i + 1:]:
                    if sw2.id not in used_ids and abs(sw2.price - sw1.price) <= tolerance:
                        cluster.append(sw2)
                
                if len(cluster) >= self.config.min_touch_count:
                    avg_price = sum(s.price for s in cluster) / len(cluster)
                    strength = min(1.0, 0.4 + len(cluster) * 0.15)  # More touches = stronger
                    
                    pools.append(LiquidityPool(
                        id=generate_id("lp"),
                        price=avg_price,
                        side=side,
                        pool_type=LiquidityPoolType.RANGE.value,
                        swing_ids=[s.id for s in cluster],
                        swing_degree="external",  # Equal levels are significant
                        touch_count=len(cluster),
                        strength=strength,
                        timestamp=cluster[-1].timestamp,
                        index=cluster[-1].index,
                        timeframe=timeframe
                    ))
                    
                    for s in cluster:
                        used_ids.add(s.id)
        
        return pools
    
    # =========================================================================
    # 4. INDUCEMENT (Internal Swing Traps)
    # =========================================================================
    def detect_inducement(
        self,
        swings: List[SwingPoint],
        timeframe: str
    ) -> List[LiquidityPool]:
        """Detect inducement at internal swings.
        
        Internal swings are traps that lure traders before continuation.
        """
        pools = []
        
        internal = [s for s in swings if getattr(s, 'degree', 'internal') == 'internal']
        
        for swing in internal:
            side = LiquiditySide.BUY_SIDE.value if swing.kind == "high" else LiquiditySide.SELL_SIDE.value
            
            pools.append(LiquidityPool(
                id=generate_id("lp"),
                price=swing.price,
                side=side,
                pool_type=LiquidityPoolType.INDUCEMENT.value,
                swing_ids=[swing.id],
                swing_degree="internal",
                strength=0.3,  # Lower strength than external
                timestamp=swing.timestamp,
                index=swing.index,
                timeframe=timeframe
            ))
        
        return pools
    
    # =========================================================================
    # 5. SWEEP DETECTION
    # =========================================================================
    def detect_sweeps(
        self,
        candles: List[Candle],
        pools: List[LiquidityPool],
        timeframe: str
    ) -> List[LiquiditySweep]:
        """Detect when pools are swept by price."""
        sweeps = []
        
        for pool in pools:
            if pool.swept:
                continue
            
            for i, candle in enumerate(candles):
                if candle.timestamp <= pool.timestamp:
                    continue
                
                swept = False
                depth = 0.0
                
                if pool.side == LiquiditySide.SELL_SIDE.value and candle.low < pool.price:
                    swept = True
                    depth = pool.price - candle.low
                elif pool.side == LiquiditySide.BUY_SIDE.value and candle.high > pool.price:
                    swept = True
                    depth = candle.high - pool.price
                
                if swept:
                    pool.swept = True
                    pool.sweep_timestamp = candle.timestamp
                    pool.sweep_depth = depth
                    
                    # Check for rejection (close back inside)
                    rejected = False
                    if pool.side == LiquiditySide.SELL_SIDE.value:
                        rejected = candle.close > pool.price
                    else:
                        rejected = candle.close < pool.price
                    
                    sweeps.append(LiquiditySweep(
                        id=generate_id("sw"),
                        pool_id=pool.id,
                        sweep_price=candle.low if pool.side == LiquiditySide.SELL_SIDE.value else candle.high,
                        direction="down" if pool.side == LiquiditySide.SELL_SIDE.value else "up",
                        sweep_index=i,
                        sweep_timestamp=candle.timestamp,
                        depth=depth,
                        timeframe=timeframe,
                        rejected=rejected,
                        continuation=not rejected
                    ))
                    break
        
        return sweeps
    
    # =========================================================================
    # 6. STRENGTH ANALYSIS
    # =========================================================================
    def analyze_strength(
        self,
        pool: LiquidityPool,
        current_price: float,
        total_candles: int
    ) -> float:
        """Calculate composite strength score for a pool."""
        strength = 0.0
        
        # Base from swing degree
        if pool.swing_degree == "external":
            strength += 0.4
        else:
            strength += 0.2
        
        # Touch count bonus
        strength += min(0.3, pool.touch_count * 0.1)
        
        # Pool type factor
        type_weights = {
            LiquidityPoolType.RANGE.value: 0.2,
            LiquidityPoolType.STOP_LOSS.value: 0.15,
            LiquidityPoolType.TREND.value: 0.1,
            LiquidityPoolType.INDUCEMENT.value: 0.05,
        }
        strength += type_weights.get(pool.pool_type, 0.1)
        
        # Proximity bonus (closer = more relevant)
        if current_price > 0:
            distance_pct = abs(pool.price - current_price) / current_price
            if distance_pct < 0.01:  # Within 1%
                strength += 0.1
            elif distance_pct < 0.03:  # Within 3%
                strength += 0.05
        
        return min(1.0, strength)
    
    # =========================================================================
    # 7. STRUCTURE INTERACTION
    # =========================================================================
    def analyze_structure_context(
        self,
        pools: List[LiquidityPool],
        protected_levels: List,
        current_price: float
    ) -> str:
        """Analyze how liquidity relates to structure."""
        if not pools or not protected_levels:
            return "No structure context"
        
        # Find nearest protected levels
        above_protected = [l for l in protected_levels if l.price > current_price and not getattr(l, 'broken', False)]
        below_protected = [l for l in protected_levels if l.price < current_price and not getattr(l, 'broken', False)]
        
        nearest_above = min(above_protected, key=lambda l: l.price) if above_protected else None
        nearest_below = max(below_protected, key=lambda l: l.price) if below_protected else None
        
        # Mark pools with structure context
        for pool in pools:
            if nearest_above and pool.price > nearest_above.price:
                pool.above_protected = True
            if nearest_below and pool.price < nearest_below.price:
                pool.below_protected = True
        
        # Build context string
        context_parts = []
        buy_side_intact = [p for p in pools if p.is_buy_side and p.is_intact]
        sell_side_intact = [p for p in pools if p.is_sell_side and p.is_intact]
        
        if buy_side_intact:
            context_parts.append(f"{len(buy_side_intact)} buy-side targets above")
        if sell_side_intact:
            context_parts.append(f"{len(sell_side_intact)} sell-side targets below")
        
        if nearest_below:
            context_parts.append(f"protected low at {nearest_below.price:,.2f}")
        if nearest_above:
            context_parts.append(f"protected high at {nearest_above.price:,.2f}")
        
        return "; ".join(context_parts) if context_parts else "No significant liquidity"
    
    # =========================================================================
    # 8. LIQUIDITY SEQUENCING
    # =========================================================================
    def get_liquidity_sequence(
        self,
        pools: List[LiquidityPool],
        current_price: float
    ) -> List[LiquidityPool]:
        """Order pools by expected sweep sequence."""
        intact = [p for p in pools if not p.swept]
        
        # Sort by distance from current price
        sorted_pools = sorted(intact, key=lambda p: abs(p.price - current_price))
        
        return sorted_pools[:10]  # Top 10 nearest targets
    
    # =========================================================================
    # FULL ANALYSIS
    # =========================================================================
    def analyze(
        self,
        swings: List[SwingPoint],
        candles: List[Candle],
        structure_breaks: List,
        protected_levels: List,
        timeframe: str
    ) -> LiquidityAnalysis:
        """Complete liquidity analysis."""
        current_price = candles[-1].close if candles else 0.0
        
        # Detect all pool types
        stop_loss_pools = self.detect_stop_loss_liquidity(swings, timeframe)
        trend_pools = self.detect_trend_liquidity(swings, structure_breaks, timeframe)
        range_pools = self.detect_range_liquidity(swings, timeframe)
        inducement_pools = self.detect_inducement(swings, timeframe)
        
        # Combine (avoid duplicates by keeping highest strength)
        all_pools = self._deduplicate_pools(
            stop_loss_pools + trend_pools + range_pools + inducement_pools
        )
        
        # Detect sweeps
        sweeps = self.detect_sweeps(candles, all_pools, timeframe)
        
        # Update strength scores
        for pool in all_pools:
            pool.strength = self.analyze_strength(pool, current_price, len(candles))
        
        # Categorize
        buy_side = [p for p in all_pools if p.is_buy_side]
        sell_side = [p for p in all_pools if p.is_sell_side]
        intact = [p for p in all_pools if p.is_intact]
        swept = [p for p in all_pools if p.swept]
        
        # Structure context
        context = self.analyze_structure_context(all_pools, protected_levels, current_price)
        
        # Sequencing
        sequence = self.get_liquidity_sequence(all_pools, current_price)
        next_target = sequence[0] if sequence else None
        
        # Trend liquidity side
        trend_side = ""
        if trend_pools:
            if any(p.is_buy_side for p in trend_pools):
                trend_side = "buy_side building"
            elif any(p.is_sell_side for p in trend_pools):
                trend_side = "sell_side building"
        
        return LiquidityAnalysis(
            buy_side_pools=buy_side,
            sell_side_pools=sell_side,
            intact_pools=intact,
            swept_pools=swept,
            recent_sweeps=sweeps[-5:] if sweeps else [],
            next_target=next_target,
            sequence=sequence,
            structure_context=context,
            trend_liquidity_side=trend_side,
            buy_side_count=len(buy_side),
            sell_side_count=len(sell_side),
            total_intact=len(intact),
            total_swept=len(swept)
        )
    
    def _deduplicate_pools(self, pools: List[LiquidityPool]) -> List[LiquidityPool]:
        """Remove duplicate pools at same price, keeping highest strength."""
        unique = {}
        for pool in pools:
            key = round(pool.price, 2)
            if key not in unique or pool.strength > unique[key].strength:
                unique[key] = pool
        return list(unique.values())


# =============================================================================
# FUNCTIONAL API
# =============================================================================

def detect_stop_loss_liquidity(
    swings: List[SwingPoint],
    timeframe: str
) -> List[LiquidityPool]:
    """Detect stop-loss liquidity at swing points."""
    return LiquidityDetector().detect_stop_loss_liquidity(swings, timeframe)


def detect_trend_liquidity(
    swings: List[SwingPoint],
    structure_breaks: List,
    timeframe: str
) -> List[LiquidityPool]:
    """Detect trend liquidity (HLs/LHs)."""
    return LiquidityDetector().detect_trend_liquidity(swings, structure_breaks, timeframe)


def detect_range_liquidity(
    swings: List[SwingPoint],
    timeframe: str
) -> List[LiquidityPool]:
    """Detect range liquidity at equal levels."""
    return LiquidityDetector().detect_range_liquidity(swings, timeframe)


def detect_inducement(
    swings: List[SwingPoint],
    timeframe: str
) -> List[LiquidityPool]:
    """Detect inducement at internal swings."""
    return LiquidityDetector().detect_inducement(swings, timeframe)


def detect_sweeps(
    candles: List[Candle],
    pools: List[LiquidityPool],
    timeframe: str
) -> List[LiquiditySweep]:
    """Detect liquidity sweeps."""
    return LiquidityDetector().detect_sweeps(candles, pools, timeframe)


def analyze_liquidity(
    swings: List[SwingPoint],
    candles: List[Candle],
    structure_breaks: List,
    protected_levels: List,
    timeframe: str
) -> LiquidityAnalysis:
    """Complete liquidity analysis."""
    return LiquidityDetector().analyze(
        swings, candles, structure_breaks, protected_levels, timeframe
    )
