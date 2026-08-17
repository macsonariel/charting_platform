"""Canonical market-regime output for the Core Engine.

The regime is the single interpreted result produced from Core facts.  API
adapters and UI code may format this object, but must not independently decide
direction, bias, state, phase, or confidence.
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class MarketRegime:
    """Authoritative interpretation of a :class:`MarketSnapshot`."""

    direction: str = "neutral"
    bias: str = "neutral"
    state: str = "unknown"
    phase: str = "neutral"
    confidence: float = 0.0

    direction_source: str = "unavailable"
    source_timeframe: str = ""
    swing_degree: str = "none"
    fallback_used: bool = False

    reasons: List[str] = field(default_factory=list)
    confidence_factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "bias": self.bias,
            "state": self.state,
            "phase": self.phase,
            "confidence": round(self.confidence, 3),
            "direction_source": self.direction_source,
            "source_timeframe": self.source_timeframe,
            "swing_degree": self.swing_degree,
            "fallback_used": self.fallback_used,
            "reasons": list(self.reasons),
            "confidence_factors": {
                key: round(value, 3)
                for key, value in self.confidence_factors.items()
            },
        }
