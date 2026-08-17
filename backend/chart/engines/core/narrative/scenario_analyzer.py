"""Narrative scenario projection of the canonical Core market regime.

This module does not classify direction or state. It maps the already-derived
`MarketRegime` into the legacy narrative scenario vocabulary.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from backend.chart.engines.core.schemas import MarketSnapshot


class MarketScenario(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    REVERSAL_UP = "reversal_up"
    REVERSAL_DOWN = "reversal_down"
    BREAKOUT_UP = "breakout_up"
    BREAKOUT_DOWN = "breakout_down"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    UNKNOWN = "unknown"


@dataclass
class ScenarioFactor:
    """Explanatory evidence copied from the canonical regime."""

    name: str
    weight: float
    bullish: bool
    description: str


@dataclass
class ScenarioResult:
    scenario: MarketScenario
    confidence: float
    bias: str
    factors: List[ScenarioFactor] = field(default_factory=list)
    key_levels: Dict[str, float] = field(default_factory=dict)
    summary: str = ""

    @property
    def is_bullish(self) -> bool:
        return self.bias == "bullish"

    @property
    def is_bearish(self) -> bool:
        return self.bias == "bearish"


class ScenarioAnalyzer:
    """Projects a `MarketRegime` into human-readable scenario fields."""

    def analyze(self, snapshot: MarketSnapshot) -> ScenarioResult:
        regime = snapshot.regime
        if regime is None:
            return ScenarioResult(
                scenario=MarketScenario.UNKNOWN,
                confidence=0.0,
                bias="neutral",
                key_levels=self._extract_key_levels(snapshot),
                summary="Market regime is unavailable.",
            )

        scenario = self._scenario_from_regime(regime.state, regime.phase, regime.bias)
        factors = self._explain_regime(regime)
        return ScenarioResult(
            scenario=scenario,
            confidence=round(regime.confidence * 100, 1),
            bias=regime.bias,
            factors=factors,
            key_levels=self._extract_key_levels(snapshot),
            summary=self._generate_summary(scenario, factors),
        )

    @staticmethod
    def _scenario_from_regime(state: str, phase: str, bias: str) -> MarketScenario:
        if phase == "accumulation":
            return MarketScenario.ACCUMULATION
        if phase == "distribution":
            return MarketScenario.DISTRIBUTION
        if state == "reversal":
            if bias == "bullish":
                return MarketScenario.REVERSAL_UP
            if bias == "bearish":
                return MarketScenario.REVERSAL_DOWN
        if state == "trending":
            if bias == "bullish":
                return MarketScenario.TRENDING_UP
            if bias == "bearish":
                return MarketScenario.TRENDING_DOWN
        if state == "ranging":
            return MarketScenario.RANGING
        return MarketScenario.UNKNOWN

    @staticmethod
    def _explain_regime(regime: Any) -> List[ScenarioFactor]:
        bullish = regime.bias == "bullish"
        factors = [
            ScenarioFactor(
                name=name.replace("_", " ").title(),
                weight=round(float(score) * 100, 1),
                bullish=bullish,
                description=f"{name.replace('_', ' ').title()}: {float(score) * 100:.0f}%",
            )
            for name, score in regime.confidence_factors.items()
        ]
        factors.extend(
            ScenarioFactor(
                name="Regime Evidence",
                weight=0.0,
                bullish=bullish,
                description=reason,
            )
            for reason in regime.reasons
        )
        return factors

    @staticmethod
    def _extract_key_levels(snapshot: MarketSnapshot) -> Dict[str, float]:
        levels: Dict[str, float] = {}
        if snapshot.external_high:
            levels["resistance"] = snapshot.external_high.price
        if snapshot.external_low:
            levels["support"] = snapshot.external_low.price

        unfilled = [gap for gap in snapshot.fair_value_gaps if not gap.filled]
        if unfilled and snapshot.current_price:
            closest = min(unfilled, key=lambda gap: abs(gap.midpoint - snapshot.current_price))
            levels["fvg_entry"] = closest.low
            levels["fvg_target"] = closest.high

        active = [level for level in snapshot.protected_levels if not level.broken]
        highs = [level for level in active if level.kind == "high"]
        lows = [level for level in active if level.kind == "low"]
        if highs:
            levels["protected_high"] = max(level.price for level in highs)
        if lows:
            levels["protected_low"] = min(level.price for level in lows)
        return levels

    @staticmethod
    def _generate_summary(
        scenario: MarketScenario,
        factors: List[ScenarioFactor],
    ) -> str:
        names = {
            MarketScenario.TRENDING_UP: "bullish trending",
            MarketScenario.TRENDING_DOWN: "bearish trending",
            MarketScenario.RANGING: "ranging/consolidating",
            MarketScenario.REVERSAL_UP: "reversing to bullish",
            MarketScenario.REVERSAL_DOWN: "reversing to bearish",
            MarketScenario.ACCUMULATION: "in accumulation",
            MarketScenario.DISTRIBUTION: "in distribution",
            MarketScenario.UNKNOWN: "unclear",
        }
        evidence = ". ".join(
            factor.description for factor in factors if factor.name == "Regime Evidence"
        )
        if not evidence:
            evidence = "No additional regime evidence is available."
        return f"Market is {names.get(scenario, 'unclear')}. {evidence}"
