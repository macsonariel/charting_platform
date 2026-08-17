"""Timeframe Configuration - Recommended candle counts and settings per timeframe.

Provides optimal candle counts for each timeframe to ensure
sufficient lookback for structural analysis.
"""


# Recommended candle counts by timeframe
# Based on: higher timeframes need fewer candles, lower timeframes need more
TIMEFRAME_CANDLE_COUNTS = {
    # Monthly/Weekly - fewer candles needed
    "1M": 150,      # 150 months = ~12.5 years
    "1W": 300,      # 300 weeks = ~5.7 years
    
    # Daily to 4H - medium candle counts
    "1D": 1000,     # 1000 days = ~2.7 years
    "12h": 1000,    # 1000 * 12h = ~500 days
    "8h": 1000,     # 1000 * 8h = ~333 days
    "4h": 1500,     # 1500 * 4h = ~250 days
    
    # 2H to 30m - more candles needed
    "2h": 2000,     # 2000 * 2h = ~166 days
    "1h": 2500,     # 2500 * 1h = ~104 days
    "30m": 3000,    # 3000 * 30m = ~62 days
    
    # Lower timeframes - maximum candles
    "15m": 4000,    # 4000 * 15m = ~42 days
    "5m": 5000,     # 5000 * 5m = ~17 days
    "3m": 5000,     # 5000 * 3m = ~10 days
    "1m": 6000,     # 6000 * 1m = ~4 days
}

# Default if timeframe not found
DEFAULT_CANDLE_COUNT = 1000


def get_recommended_candle_count(timeframe: str) -> int:
    """Get the recommended candle count for a timeframe.
    
    Args:
        timeframe: Timeframe string (e.g., "1h", "4h", "1D")
        
    Returns:
        Recommended number of candles to fetch
    """
    # Normalize timeframe to lowercase for matching
    tf_lower = timeframe.lower()
    tf_upper = timeframe.upper()
    
    # Try exact match first
    if timeframe in TIMEFRAME_CANDLE_COUNTS:
        return TIMEFRAME_CANDLE_COUNTS[timeframe]
    if tf_lower in TIMEFRAME_CANDLE_COUNTS:
        return TIMEFRAME_CANDLE_COUNTS[tf_lower]
    if tf_upper in TIMEFRAME_CANDLE_COUNTS:
        return TIMEFRAME_CANDLE_COUNTS[tf_upper]
    
    # Return default
    return DEFAULT_CANDLE_COUNT


def get_all_timeframe_configs() -> dict:
    """Get all timeframe configurations.
    
    Returns:
        Dict mapping timeframes to their recommended candle counts
    """
    return TIMEFRAME_CANDLE_COUNTS.copy()
