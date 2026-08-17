"""MACD (Moving Average Convergence Divergence) Indicator.

Trend-following momentum indicator showing relationship between
two moving averages of a security's price.
"""

from backend.chart.engines.indicators.macd.schemas import MACDReading, MACDCrossover
from backend.chart.engines.indicators.macd.analyzer import (
    MACDAnalyzer,
    calculate_macd,
)

__all__ = [
    'MACDReading',
    'MACDCrossover',
    'MACDAnalyzer',
    'calculate_macd',
]
