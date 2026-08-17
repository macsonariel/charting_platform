"""ATR (Average True Range) Indicator.

Measures market volatility by decomposing the entire range
of an asset price for a period.
"""

from backend.chart.engines.indicators.atr.schemas import ATRReading, ATRTrend
from backend.chart.engines.indicators.atr.analyzer import (
    ATRAnalyzer,
    calculate_atr,
)

__all__ = [
    'ATRReading',
    'ATRTrend',
    'ATRAnalyzer',
    'calculate_atr',
]
