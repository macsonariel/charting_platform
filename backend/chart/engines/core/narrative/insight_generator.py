"""Insight Generator - Generates specific trading insights from market data.

Produces actionable insights like:
- "Watch for pullback to 91,200 FVG"
- "Protected low at 89,500 is key support"
- "CHoCH at 92,100 signals potential reversal"
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from backend.chart.engines.core.schemas import MarketSnapshot


class InsightType(Enum):
    """Types of trading insights."""
    ENTRY_ZONE = "entry_zone"
    EXIT_TARGET = "exit_target"
    STOP_LOSS = "stop_loss"
    KEY_LEVEL = "key_level"
    STRUCTURE_SIGNAL = "structure_signal"
    REVERSAL_WARNING = "reversal_warning"
    TREND_CONFIRMATION = "trend_confirmation"
    LIQUIDITY_TARGET = "liquidity_target"


class InsightPriority(Enum):
    """Priority/importance of insight."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Insight:
    """A single trading insight."""
    type: InsightType
    priority: InsightPriority
    message: str
    level: Optional[float] = None
    direction: Optional[str] = None  # bullish, bearish
    actionable: bool = True
    
    def to_dict(self):
        return {
            "type": self.type.value,
            "priority": self.priority.value,
            "message": self.message,
            "level": self.level,
            "direction": self.direction,
            "actionable": self.actionable,
        }


class InsightGenerator:
    """Generates trading insights from market snapshot."""
    
    def generate(self, snapshot: MarketSnapshot) -> List[Insight]:
        """Generate all insights from snapshot."""
        insights = []
        
        # Structure insights
        insights.extend(self._structure_insights(snapshot))
        
        # FVG insights
        insights.extend(self._fvg_insights(snapshot))
        
        # Level insights
        insights.extend(self._level_insights(snapshot))
        
        # Swing insights
        insights.extend(self._swing_insights(snapshot))
        
        # Sort by priority
        priority_order = {InsightPriority.HIGH: 0, InsightPriority.MEDIUM: 1, InsightPriority.LOW: 2}
        insights.sort(key=lambda x: priority_order[x.priority])
        
        return insights
    
    def _structure_insights(self, snapshot: MarketSnapshot) -> List[Insight]:
        """Generate insights from structure breaks and CHoCHs."""
        insights = []
        
        # Recent structure break
        if snapshot.structure_breaks:
            recent_sb = snapshot.structure_breaks[-1]
            direction = "bullish" if recent_sb.direction == "up" else "bearish"
            insights.append(Insight(
                type=InsightType.STRUCTURE_SIGNAL,
                priority=InsightPriority.HIGH,
                message=f"Recent {direction} BOS @ {recent_sb.break_price:,.2f} confirms trend",
                level=recent_sb.break_price,
                direction=direction,
            ))
        
        # Character change (high priority)
        if snapshot.character_changes:
            recent_cc = snapshot.character_changes[-1]
            direction = "bullish" if recent_cc.direction == "up" else "bearish"
            insights.append(Insight(
                type=InsightType.REVERSAL_WARNING,
                priority=InsightPriority.HIGH,
                message=f"CHoCH detected @ {recent_cc.break_price:,.2f} - potential {direction} reversal",
                level=recent_cc.break_price,
                direction=direction,
            ))
        
        return insights
    
    def _fvg_insights(self, snapshot: MarketSnapshot) -> List[Insight]:
        """Generate insights from Fair Value Gaps."""
        insights = []
        unfilled = [f for f in snapshot.fair_value_gaps if not f.filled]
        
        if not unfilled or not snapshot.current_price:
            return insights
        
        # Find nearest FVG
        nearest = min(unfilled, key=lambda f: abs(f.low - snapshot.current_price))
        distance = abs(nearest.low - snapshot.current_price)
        distance_pct = (distance / snapshot.current_price) * 100
        
        direction = nearest.direction
        
        if distance_pct < 2:  # Within 2% - high priority
            insights.append(Insight(
                type=InsightType.ENTRY_ZONE,
                priority=InsightPriority.HIGH,
                message=f"Price approaching {direction} FVG @ {nearest.low:,.2f}-{nearest.high:,.2f}",
                level=nearest.low,
                direction=direction,
            ))
        elif distance_pct < 5:  # Within 5% - medium priority
            insights.append(Insight(
                type=InsightType.ENTRY_ZONE,
                priority=InsightPriority.MEDIUM,
                message=f"Watch for pullback to {direction} FVG @ {nearest.low:,.2f}",
                level=nearest.low,
                direction=direction,
            ))
        
        # Count unfilled by direction
        bull_fvgs = [f for f in unfilled if f.direction == "bullish"]
        bear_fvgs = [f for f in unfilled if f.direction == "bearish"]
        
        if len(bull_fvgs) >= 3:
            insights.append(Insight(
                type=InsightType.KEY_LEVEL,
                priority=InsightPriority.LOW,
                message=f"{len(bull_fvgs)} bullish FVGs below - strong support structure",
                direction="bullish",
                actionable=False,
            ))
        
        if len(bear_fvgs) >= 3:
            insights.append(Insight(
                type=InsightType.KEY_LEVEL,
                priority=InsightPriority.LOW,
                message=f"{len(bear_fvgs)} bearish FVGs above - strong resistance structure",
                direction="bearish",
                actionable=False,
            ))
        
        return insights
    
    def _level_insights(self, snapshot: MarketSnapshot) -> List[Insight]:
        """Generate insights from protected levels."""
        insights = []
        active = [l for l in snapshot.protected_levels if not l.broken]
        
        if not active or not snapshot.current_price:
            return insights
        
        # Nearest protected levels
        highs = [l for l in active if l.kind == "high"]
        lows = [l for l in active if l.kind == "low"]
        
        if lows:
            nearest_low = min(lows, key=lambda l: abs(l.price - snapshot.current_price))
            distance_pct = ((snapshot.current_price - nearest_low.price) / snapshot.current_price) * 100
            
            if distance_pct < 1:  # Very close
                insights.append(Insight(
                    type=InsightType.STOP_LOSS,
                    priority=InsightPriority.HIGH,
                    message=f"Protected low @ {nearest_low.price:,.2f} - CRITICAL support",
                    level=nearest_low.price,
                    direction="bullish",
                ))
            elif distance_pct < 3:
                insights.append(Insight(
                    type=InsightType.KEY_LEVEL,
                    priority=InsightPriority.MEDIUM,
                    message=f"Protected low @ {nearest_low.price:,.2f} - watch if tested",
                    level=nearest_low.price,
                    direction="bullish",
                ))
        
        if highs:
            nearest_high = min(highs, key=lambda l: abs(l.price - snapshot.current_price))
            distance_pct = ((nearest_high.price - snapshot.current_price) / snapshot.current_price) * 100
            
            if distance_pct < 1:  # Very close
                insights.append(Insight(
                    type=InsightType.EXIT_TARGET,
                    priority=InsightPriority.HIGH,
                    message=f"Protected high @ {nearest_high.price:,.2f} - CRITICAL resistance",
                    level=nearest_high.price,
                    direction="bearish",
                ))
            elif distance_pct < 3:
                insights.append(Insight(
                    type=InsightType.KEY_LEVEL,
                    priority=InsightPriority.MEDIUM,
                    message=f"Protected high @ {nearest_high.price:,.2f} - watch for reaction",
                    level=nearest_high.price,
                    direction="bearish",
                ))
        
        return insights
    
    def _swing_insights(self, snapshot: MarketSnapshot) -> List[Insight]:
        """Generate insights from swing structure."""
        insights = []
        ext_swings = [s for s in snapshot.swings if s.degree == "external"]
        
        if len(ext_swings) < 2:
            return insights
        
        highs = [s for s in ext_swings if s.kind == "high"]
        lows = [s for s in ext_swings if s.kind == "low"]
        
        # Trend confirmation
        if len(highs) >= 2 and len(lows) >= 2:
            hh = highs[-1].price > highs[-2].price
            hl = lows[-1].price > lows[-2].price
            lh = highs[-1].price < highs[-2].price
            ll = lows[-1].price < lows[-2].price
            
            if hh and hl:
                insights.append(Insight(
                    type=InsightType.TREND_CONFIRMATION,
                    priority=InsightPriority.MEDIUM,
                    message="Higher highs + higher lows = confirmed uptrend",
                    direction="bullish",
                    actionable=False,
                ))
            elif lh and ll:
                insights.append(Insight(
                    type=InsightType.TREND_CONFIRMATION,
                    priority=InsightPriority.MEDIUM,
                    message="Lower highs + lower lows = confirmed downtrend",
                    direction="bearish",
                    actionable=False,
                ))
        
        # External swing targets
        if snapshot.external_high:
            insights.append(Insight(
                type=InsightType.EXIT_TARGET,
                priority=InsightPriority.LOW,
                message=f"External high @ {snapshot.external_high.price:,.2f} - major target",
                level=snapshot.external_high.price,
                direction="bullish",
            ))
        
        if snapshot.external_low:
            insights.append(Insight(
                type=InsightType.STOP_LOSS,
                priority=InsightPriority.LOW,
                message=f"External low @ {snapshot.external_low.price:,.2f} - major support",
                level=snapshot.external_low.price,
                direction="bearish",
            ))
        
        return insights


def generate_insights(snapshot: MarketSnapshot) -> List[Insight]:
    """Convenience function to generate insights."""
    generator = InsightGenerator()
    return generator.generate(snapshot)
