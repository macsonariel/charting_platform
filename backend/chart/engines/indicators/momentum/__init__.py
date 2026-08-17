"""Momentum Indicator - Shared momentum analysis.

Provides momentum analysis that can be used by any engine:
- Rate of change (ROC)
- Momentum direction and strength
- Acceleration/deceleration detection
- Divergence detection
"""

from backend.chart.engines.indicators.momentum.schemas import (
    MomentumReading,
    MomentumDivergence,
)
from backend.chart.engines.indicators.momentum.analyzer import (
    MomentumAnalyzer,
    calculate_momentum,
    detect_momentum_divergence,
)

__all__ = [
    'MomentumReading',
    'MomentumDivergence',
    'MomentumAnalyzer',
    'calculate_momentum',
    'detect_momentum_divergence',
]

