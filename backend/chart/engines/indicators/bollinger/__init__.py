"""Bollinger Bands Indicator.

Volatility bands placed above and below a moving average.
Bandwidth and %B help identify price extremes and squeezes.
"""

from backend.chart.engines.indicators.bollinger.schemas import BollingerReading, BollingerSqueeze
from backend.chart.engines.indicators.bollinger.analyzer import (
    BollingerAnalyzer,
    calculate_bollinger,
)

__all__ = [
    'BollingerReading',
    'BollingerSqueeze',
    'BollingerAnalyzer',
    'calculate_bollinger',
]
