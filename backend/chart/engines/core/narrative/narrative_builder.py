"""Narrative Builder - Generates human-readable market analysis.

Takes a MarketSnapshot and produces structured narrative text.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from backend.chart.engines.core.schemas import MarketSnapshot
from backend.chart.engines.core.narrative.scenario_analyzer import ScenarioAnalyzer, ScenarioResult
from backend.chart.engines.core.narrative.templates import get_template, NarrativeTemplate


@dataclass
class Narrative:
    """Complete narrative output."""
    symbol: str
    timeframe: str
    scenario: str
    confidence: float
    bias: str
    
    # Text sections
    summary: str
    details: str
    action: str
    risk: str
    price_context: str = ""  # NEW: What price is doing now
    
    # Key levels
    key_levels: Dict[str, float] = field(default_factory=dict)
    
    # Factors that led to this analysis
    factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "scenario": self.scenario,
            "confidence": self.confidence,
            "bias": self.bias,
            "summary": self.summary,
            "details": self.details,
            "action": self.action,
            "risk": self.risk,
            "price_context": self.price_context,
            "key_levels": self.key_levels,
            "factors": self.factors,
        }
    
    def to_text(self) -> str:
        """Convert to full text output."""
        lines = [
            f"{'='*60}",
            f"  {self.symbol} {self.timeframe} ANALYSIS",
            f"  Scenario: {self.scenario.upper()} | Bias: {self.bias.upper()}",
            f"  Confidence: {self.confidence:.0f}%",
            f"{'='*60}",
            "",
            self.summary,
            "",
            "CURRENT PRICE ACTION:",
            self.price_context,
            "",
            self.details,
            "",
            self.action,
            "",
            self.risk,
            "",
            f"{'='*60}",
        ]
        return "\n".join(lines)


class NarrativeBuilder:
    """Builds human-readable narratives from market data."""
    
    def __init__(self):
        self.analyzer = ScenarioAnalyzer()
    
    def build(self, snapshot: MarketSnapshot) -> Narrative:
        """Build complete narrative from snapshot."""
        # Analyze scenario
        result = self.analyzer.analyze(snapshot)
        
        # Get template
        template = get_template(result.scenario.value)
        
        # Prepare template variables
        variables = self._prepare_variables(snapshot, result)
        
        # Render sections
        summary = self._render_section(template.summary_template, variables)
        details = self._render_section(template.detail_template, variables)
        action = self._render_section(template.action_template, variables)
        risk = self._render_section(template.risk_template, variables)
        
        # Build price context (NEW)
        price_context = self._build_price_context(snapshot, result)
        
        # Extract factor descriptions
        factors = [f.description for f in result.factors]
        
        return Narrative(
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            scenario=result.scenario.value,
            confidence=result.confidence,
            bias=result.bias,
            summary=summary,
            details=details,
            action=action,
            risk=risk,
            price_context=price_context,
            key_levels=result.key_levels,
            factors=factors,
        )
    
    def _prepare_variables(
        self, 
        snapshot: MarketSnapshot, 
        result: ScenarioResult
    ) -> Dict[str, Any]:
        """Prepare variables for template rendering."""
        # Count structure breaks by direction
        bullish_bos = sum(1 for sb in snapshot.structure_breaks if sb.direction == "up")
        bearish_bos = sum(1 for sb in snapshot.structure_breaks if sb.direction == "down")
        
        # Count FVGs
        unfilled_fvgs = [f for f in snapshot.fair_value_gaps if not f.filled]
        bullish_fvgs = [f for f in unfilled_fvgs if f.direction == "bullish"]
        bearish_fvgs = [f for f in unfilled_fvgs if f.direction == "bearish"]
        
        # Get swing pattern description
        ext_swings = [s for s in snapshot.swings if s.degree == "external"]
        swing_pattern = self._describe_swings(ext_swings)
        
        # FVG status
        fvg_status = self._describe_fvgs(unfilled_fvgs)
        
        # Level status
        active_levels = [l for l in snapshot.protected_levels if not l.broken]
        level_status = self._describe_levels(active_levels, snapshot.current_price)
        
        # Key levels with defaults
        key_levels = result.key_levels
        
        return {
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe,
            "current_price": snapshot.current_price or 0,
            "bullish_bos": bullish_bos,
            "bearish_bos": bearish_bos,
            "external_high": key_levels.get("resistance", snapshot.external_high.price if snapshot.external_high else 0),
            "external_low": key_levels.get("support", snapshot.external_low.price if snapshot.external_low else 0),
            "protected_high": key_levels.get("protected_high", 0),
            "protected_low": key_levels.get("protected_low", 0),
            "fvg_entry": key_levels.get("fvg_entry", 0),
            "fvg_target": key_levels.get("fvg_target", 0),
            "target": self._calculate_target(snapshot, result.bias),
            "pivot_level": self._find_pivot(snapshot),
            "range_high": key_levels.get("resistance", 0),
            "range_low": key_levels.get("support", 0),
            "equilibrium": self._calculate_equilibrium(snapshot),
            "swing_pattern": swing_pattern,
            "fvg_status": fvg_status,
            "level_status": level_status,
        }
    
    def _render_section(self, template: str, variables: Dict[str, Any]) -> str:
        """Render a template section with variables."""
        try:
            return template.format(**variables)
        except KeyError as e:
            # Handle missing variables gracefully
            return template.replace("{" + str(e).strip("'") + "}", "N/A")
        except Exception:
            return template
    
    def _describe_swings(self, swings: List) -> str:
        """Describe swing pattern."""
        if not swings:
            return "No external swings detected"
        
        highs = [s for s in swings if s.kind == "high"]
        lows = [s for s in swings if s.kind == "low"]
        
        if len(highs) >= 2:
            if highs[-1].price > highs[-2].price:
                return "Higher highs forming - bullish structure"
            else:
                return "Lower highs forming - bearish pressure"
        
        if len(lows) >= 2:
            if lows[-1].price > lows[-2].price:
                return "Higher lows forming - bullish support"
            else:
                return "Lower lows forming - bearish continuation"
        
        return f"{len(swings)} external swings detected"
    
    def _describe_fvgs(self, fvgs: List) -> str:
        """Describe FVG status."""
        if not fvgs:
            return "No unfilled FVGs - price is balanced"
        
        bullish = sum(1 for f in fvgs if f.direction == "bullish")
        bearish = sum(1 for f in fvgs if f.direction == "bearish")
        
        if bullish > bearish:
            return f"{bullish} bullish FVGs below - potential support zones"
        elif bearish > bullish:
            return f"{bearish} bearish FVGs above - potential resistance zones"
        else:
            return f"{len(fvgs)} balanced FVGs - watch for reaction"
    
    def _describe_levels(self, levels: List, current_price: float) -> str:
        """Describe protected levels."""
        if not levels:
            return "No active protected levels"
        
        if not current_price:
            return f"{len(levels)} protected levels active"
        
        above = sum(1 for l in levels if l.price > current_price)
        below = sum(1 for l in levels if l.price < current_price)
        
        if below > above:
            return f"{below} protected levels below price - strong support structure"
        elif above > below:
            return f"{above} protected levels above price - strong resistance structure"
        else:
            return f"Balanced levels: {above} above, {below} below"
    
    def _calculate_target(self, snapshot: MarketSnapshot, bias: str) -> float:
        """Calculate potential target level."""
        if bias == "bullish" and snapshot.external_high:
            # Target is extension above external high
            if snapshot.external_low:
                range_size = snapshot.external_high.price - snapshot.external_low.price
                return snapshot.external_high.price + (range_size * 0.618)
            return snapshot.external_high.price * 1.02
        
        elif bias == "bearish" and snapshot.external_low:
            # Target is extension below external low
            if snapshot.external_high:
                range_size = snapshot.external_high.price - snapshot.external_low.price
                return snapshot.external_low.price - (range_size * 0.618)
            return snapshot.external_low.price * 0.98
        
        return 0
    
    def _find_pivot(self, snapshot: MarketSnapshot) -> float:
        """Find the reversal pivot level."""
        if snapshot.character_changes:
            return snapshot.character_changes[-1].break_price
        if snapshot.structure_breaks:
            return snapshot.structure_breaks[-1].break_price
        return snapshot.current_price or 0
    
    def _calculate_equilibrium(self, snapshot: MarketSnapshot) -> float:
        """Calculate range equilibrium."""
        if snapshot.external_high and snapshot.external_low:
            return (snapshot.external_high.price + snapshot.external_low.price) / 2
        return snapshot.current_price or 0
    
    def _build_price_context(self, snapshot: MarketSnapshot, result: ScenarioResult) -> str:
        """Build contextual analysis of what price is currently doing."""
        if not snapshot.current_price:
            return "Current price data not available."
        
        price = snapshot.current_price
        lines = []
        
        # Price position in structure
        if snapshot.external_high and snapshot.external_low:
            high = snapshot.external_high.price
            low = snapshot.external_low.price
            range_size = high - low
            position = (price - low) / range_size if range_size > 0 else 0.5
            
            if position > 0.75:
                lines.append(f"📍 Price at {price:,.2f} is in **PREMIUM** territory (top 25% of range)")
                lines.append(f"   Trading {((position - 0.5) * 2 * 100):.0f}% above equilibrium")
            elif position < 0.25:
                lines.append(f"📍 Price at {price:,.2f} is in **DISCOUNT** territory (bottom 25% of range)")
                lines.append(f"   Trading {((0.5 - position) * 2 * 100):.0f}% below equilibrium")
            else:
                lines.append(f"📍 Price at {price:,.2f} is near **EQUILIBRIUM** (middle of range)")
        
        # Distance to key levels
        key_levels = result.key_levels
        level_distances = []
        
        # External high/low
        if snapshot.external_high:
            dist = abs(snapshot.external_high.price - price) / price * 100
            if dist < 3:
                level_distances.append(f"  🔴 {dist:.1f}% from External High @ {snapshot.external_high.price:,.2f} - MAJOR RESISTANCE")
            elif dist < 5:
                level_distances.append(f"  ↗️ {dist:.1f}% from External High @ {snapshot.external_high.price:,.2f} - approaching resistance")
        
        if snapshot.external_low:
            dist = abs(price - snapshot.external_low.price) / price * 100
            if dist < 3:
                level_distances.append(f"  🟢 {dist:.1f}% from External Low @ {snapshot.external_low.price:,.2f} - MAJOR SUPPORT")
            elif dist < 5:
                level_distances.append(f"  ↘️ {dist:.1f}% from External Low @ {snapshot.external_low.price:,.2f} - approaching support")
        
        # Protected levels
        active_levels = [l for l in snapshot.protected_levels if not l.broken]
        for level in active_levels:
            dist = abs(level.price - price) / price * 100
            if dist < 1:
                kind = "Protected High (resistance)" if level.kind == "high" else "Protected Low (support)"
                level_distances.append(f"  ⚠️ TOUCHING {kind} @ {level.price:,.2f} - CRITICAL!")
            elif dist < 2:
                kind = "resistance" if level.kind == "high" else "support"
                level_distances.append(f"  📍 {dist:.1f}% from protected {kind} @ {level.price:,.2f}")
        
        if level_distances:
            lines.append("\n**Nearby Significant Levels:**")
            lines.extend(level_distances[:5])  # Top 5 nearest
        
        # FVG proximity
        unfilled = [f for f in snapshot.fair_value_gaps if not f.filled]
        if unfilled:
            nearest = min(unfilled, key=lambda f: abs((f.high + f.low) / 2 - price))
            fvg_mid = (nearest.high + nearest.low) / 2
            dist = abs(fvg_mid - price) / price * 100
            
            if dist < 1:
                lines.append(f"\n🎯 Price is **INSIDE** {nearest.direction} FVG @ {nearest.low:,.2f}-{nearest.high:,.2f}")
                lines.append("   Watch for reaction or rejection")
            elif dist < 2:
                direction = "above" if price > fvg_mid else "below"
                lines.append(f"\n📦 {nearest.direction.upper()} FVG {dist:.1f}% {direction} @ {nearest.low:,.2f}-{nearest.high:,.2f}")
                if nearest.direction == "bullish" and price > fvg_mid:
                    lines.append("   ↘️ May pull back to fill gap (bullish entry)")
                elif nearest.direction == "bearish" and price < fvg_mid:
                    lines.append("   ↗️ May rally to fill gap (bearish entry)")
        
        # Recent structure breaks
        if snapshot.structure_breaks:
            recent = snapshot.structure_breaks[-1]
            dist = abs(recent.break_price - price) / price * 100
            direction = "bullish ↑" if recent.direction == "up" else "bearish ↓"
            
            if dist < 1:
                lines.append(f"\n⚡ Price just broke structure {direction} @ {recent.break_price:,.2f}")
                lines.append("   Structure break is FRESH - momentum in play")
            elif dist < 3:
                lines.append(f"\n⚡ Recent {direction} BOS @ {recent.break_price:,.2f} ({dist:.1f}% away)")
        
        # Character changes (reversals)
        if snapshot.character_changes:
            recent_cc = snapshot.character_changes[-1]
            dist = abs(recent_cc.break_price - price) / price * 100
            direction = "bullish ↑" if recent_cc.direction == "up" else "bearish ↓"
            
            lines.append(f"\n🔄 CHoCH (Character Change) detected: {direction}")
            lines.append(f"   Reversal pivot @ {recent_cc.break_price:,.2f} ({dist:.1f}% from current)")
            if dist < 2:
                lines.append("   ⚠️ Price near reversal point - watch for rejection")
        
        if not lines:
            lines.append(f"Price at {price:,.2f} - analyzing market structure...")
        
        return "\n".join(lines)


def build_narrative(snapshot: MarketSnapshot) -> Narrative:
    """Convenience function to build narrative."""
    builder = NarrativeBuilder()
    return builder.build(snapshot)

