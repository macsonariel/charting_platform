"""Shared Indicators - Reusable analysis modules.

These indicators can be used by any engine:
- Volume: Volume analysis, confirmation/divergence
- Momentum: ROC, acceleration, divergence detection
- Price Behavior: Rejections, compression
- RSI: Relative Strength Index, overbought/oversold
- MACD: Moving Average Convergence Divergence
- ATR: Average True Range, volatility measurement
- Bollinger: Bollinger Bands, volatility envelopes

Each indicator is in its own folder with schemas and analyzer.
"""

# Volume indicator
from backend.chart.engines.indicators.volume import (
    VolumeCondition,
    VolumeBar,
    VolumeProfile,
    VolumeAnalyzer,
    analyze_volume,
)

# Momentum indicator
from backend.chart.engines.indicators.momentum import (
    MomentumReading,
    MomentumDivergence,
    MomentumAnalyzer,
    calculate_momentum,
    detect_momentum_divergence,
)

# Price behavior (rejections, compression)
from backend.chart.engines.indicators.price_behavior import (
    Rejection,
    CompressionReading,
    PriceBehaviorAnalyzer,
    detect_rejections,
    detect_compression,
)

# RSI indicator
from backend.chart.engines.indicators.rsi import (
    RSIReading,
    RSIDivergence,
    RSIAnalyzer,
    calculate_rsi,
    detect_rsi_divergence,
)

# MACD indicator
from backend.chart.engines.indicators.macd import (
    MACDReading,
    MACDCrossover,
    MACDAnalyzer,
    calculate_macd,
)

# ATR indicator
from backend.chart.engines.indicators.atr import (
    ATRReading,
    ATRTrend,
    ATRAnalyzer,
    calculate_atr,
)

# Bollinger Bands indicator
from backend.chart.engines.indicators.bollinger import (
    BollingerReading,
    BollingerSqueeze,
    BollingerAnalyzer,
    calculate_bollinger,
)

__all__ = [
    # Volume
    'VolumeCondition',
    'VolumeBar',
    'VolumeProfile',
    'VolumeAnalyzer',
    'analyze_volume',
    
    # Momentum (ROC-based)
    'MomentumReading',
    'MomentumDivergence',
    'MomentumAnalyzer',
    'calculate_momentum',
    'detect_momentum_divergence',
    
    # Price Behavior
    'Rejection',
    'CompressionReading',
    'PriceBehaviorAnalyzer',
    'detect_rejections',
    'detect_compression',
    
    # RSI
    'RSIReading',
    'RSIDivergence',
    'RSIAnalyzer',
    'calculate_rsi',
    'detect_rsi_divergence',
    
    # MACD
    'MACDReading',
    'MACDCrossover',
    'MACDAnalyzer',
    'calculate_macd',
    
    # ATR
    'ATRReading',
    'ATRTrend',
    'ATRAnalyzer',
    'calculate_atr',
    
    # Bollinger Bands
    'BollingerReading',
    'BollingerSqueeze',
    'BollingerAnalyzer',
    'calculate_bollinger',
]
