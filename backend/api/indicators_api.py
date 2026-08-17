"""Indicators API - REST endpoints for technical indicators.

Provides endpoints for RSI, MACD, ATR, and Bollinger Bands.
All endpoints accept symbol, timeframe, and periods parameters.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging

from backend.chart.data.chart_data_fetcher import fetch_and_convert
from backend.chart.engines.indicators import (
    RSIAnalyzer, calculate_rsi,
    MACDAnalyzer, calculate_macd,
    ATRAnalyzer, calculate_atr,
    BollingerAnalyzer, calculate_bollinger,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/indicators", tags=["Indicators"])


async def fetch_candles(symbol: str, timeframe: str, periods: int):
    """Fetch candles for indicator calculation."""
    candles = fetch_and_convert(
        symbol=symbol,
        timeframe=timeframe,
        lookback=periods
    )
    if not candles:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol} {timeframe}")
    return candles


@router.get("/rsi")
async def get_rsi(
    symbol: str = Query(..., description="Trading symbol (e.g., BTCUSDT)"),
    timeframe: str = Query(..., description="Chart timeframe (e.g., 1h)"),
    periods: int = Query(100, ge=20, le=1000, description="Number of candles"),
    period: int = Query(14, ge=2, le=50, description="RSI period"),
):
    """Get RSI (Relative Strength Index) values.
    
    RSI measures momentum on a 0-100 scale:
    - > 70: Overbought
    - < 30: Oversold
    """
    try:
        candles = await fetch_candles(symbol, timeframe, periods)
        
        analyzer = RSIAnalyzer(period=period)
        readings = analyzer.calculate(candles)
        
        # Return only the last N readings based on requested periods
        current = readings[-1] if readings else None
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator": "RSI",
            "period": period,
            "current": {
                "value": current.value,
                "zone": current.zone,
                "is_overbought": current.is_overbought,
                "is_oversold": current.is_oversold,
                "direction": current.direction,
                "strength": current.strength,
            } if current else None,
            "readings": [
                {
                    "timestamp": r.timestamp,
                    "value": r.value,
                    "zone": r.zone,
                }
                for r in readings[-50:]  # Last 50 readings
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RSI calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macd")
async def get_macd(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(..., description="Chart timeframe"),
    periods: int = Query(100, ge=30, le=1000, description="Number of candles"),
    fast: int = Query(12, ge=2, le=50, description="Fast EMA period"),
    slow: int = Query(26, ge=5, le=100, description="Slow EMA period"),
    signal: int = Query(9, ge=2, le=50, description="Signal EMA period"),
):
    """Get MACD (Moving Average Convergence Divergence) values.
    
    MACD shows relationship between two EMAs:
    - MACD line = Fast EMA - Slow EMA
    - Signal line = EMA of MACD
    - Histogram = MACD - Signal
    """
    try:
        candles = await fetch_candles(symbol, timeframe, periods)
        
        analyzer = MACDAnalyzer(fast_period=fast, slow_period=slow, signal_period=signal)
        readings = analyzer.calculate(candles)
        crossovers = analyzer.detect_crossovers(candles)
        
        current = readings[-1] if readings else None
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator": "MACD",
            "config": {"fast": fast, "slow": slow, "signal": signal},
            "current": {
                "macd": current.macd,
                "signal": current.signal,
                "histogram": current.histogram,
                "is_positive": current.is_positive,
                "is_bullish_cross": current.is_bullish_cross,
                "is_bearish_cross": current.is_bearish_cross,
                "histogram_rising": current.histogram_rising,
            } if current else None,
            "readings": [
                {
                    "timestamp": r.timestamp,
                    "macd": r.macd,
                    "signal": r.signal,
                    "histogram": r.histogram,
                }
                for r in readings[-50:]
            ],
            "crossovers": [
                {
                    "type": c.crossover_type,
                    "timestamp": c.timestamp,
                    "strength": c.strength,
                }
                for c in crossovers[-10:]  # Last 10 crossovers
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MACD calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/atr")
async def get_atr(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(..., description="Chart timeframe"),
    periods: int = Query(100, ge=20, le=1000, description="Number of candles"),
    period: int = Query(14, ge=2, le=50, description="ATR period"),
):
    """Get ATR (Average True Range) values.
    
    ATR measures volatility:
    - Higher ATR = more volatile market
    - Lower ATR = less volatile / potential squeeze
    """
    try:
        candles = await fetch_candles(symbol, timeframe, periods)
        
        analyzer = ATRAnalyzer(period=period)
        readings = analyzer.calculate(candles)
        
        current = readings[-1] if readings else None
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator": "ATR",
            "period": period,
            "current": {
                "value": current.value,
                "atr_percent": current.atr_percent,
                "percentile": current.percentile,
                "trend": current.trend.value,
                "is_high_volatility": current.is_high_volatility,
                "is_low_volatility": current.is_low_volatility,
                "is_squeeze": current.is_squeeze,
                "stop_loss_distance": current.stop_loss_distance,
                "take_profit_distance": current.take_profit_distance,
            } if current else None,
            "readings": [
                {
                    "timestamp": r.timestamp,
                    "value": r.value,
                    "atr_percent": r.atr_percent,
                    "trend": r.trend.value,
                }
                for r in readings[-50:]
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ATR calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bollinger")
async def get_bollinger(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(..., description="Chart timeframe"),
    periods: int = Query(100, ge=25, le=1000, description="Number of candles"),
    period: int = Query(20, ge=5, le=100, description="SMA period"),
    std_dev: float = Query(2.0, ge=1.0, le=4.0, description="Standard deviation multiplier"),
):
    """Get Bollinger Bands values.
    
    Bollinger Bands show volatility:
    - Upper/Lower bands expand with volatility
    - %B shows where price is relative to bands
    - Squeeze indicates potential breakout
    """
    try:
        candles = await fetch_candles(symbol, timeframe, periods)
        
        analyzer = BollingerAnalyzer(period=period, std_dev_multiplier=std_dev)
        readings = analyzer.calculate(candles)
        squeezes = analyzer.detect_squeezes(candles)
        
        current = readings[-1] if readings else None
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator": "Bollinger",
            "config": {"period": period, "std_dev": std_dev},
            "current": {
                "upper": current.upper,
                "middle": current.middle,
                "lower": current.lower,
                "percent_b": current.percent_b,
                "bandwidth": current.bandwidth,
                "is_above_upper": current.is_above_upper,
                "is_below_lower": current.is_below_lower,
                "is_squeeze": current.is_squeeze,
                "band_touch": current.band_touch,
            } if current else None,
            "readings": [
                {
                    "timestamp": r.timestamp,
                    "upper": r.upper,
                    "middle": r.middle,
                    "lower": r.lower,
                    "percent_b": r.percent_b,
                }
                for r in readings[-50:]
            ],
            "squeezes": [
                {
                    "start_timestamp": s.start_timestamp,
                    "end_timestamp": s.end_timestamp,
                    "duration": s.duration,
                    "breakout_direction": s.breakout_direction,
                }
                for s in squeezes[-5:]  # Last 5 squeezes
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bollinger calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_indicators_summary(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(..., description="Chart timeframe"),
    periods: int = Query(100, ge=30, le=1000, description="Number of candles"),
):
    """Get summary of all indicators for a symbol.
    
    Returns current values for RSI, MACD, ATR, and Bollinger Bands.
    """
    try:
        candles = await fetch_candles(symbol, timeframe, periods)
        
        # Calculate all indicators
        rsi_analyzer = RSIAnalyzer()
        macd_analyzer = MACDAnalyzer()
        atr_analyzer = ATRAnalyzer()
        bb_analyzer = BollingerAnalyzer()
        
        rsi = rsi_analyzer.get_current(candles)
        macd = macd_analyzer.get_current(candles)
        atr = atr_analyzer.get_current(candles)
        bb = bb_analyzer.get_current(candles)
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "rsi": {
                "value": rsi.value if rsi else None,
                "zone": rsi.zone if rsi else None,
            },
            "macd": {
                "macd": macd.macd if macd else None,
                "signal": macd.signal if macd else None,
                "histogram": macd.histogram if macd else None,
                "is_bullish": macd.is_positive if macd else None,
            },
            "atr": {
                "value": atr.value if atr else None,
                "percent": atr.atr_percent if atr else None,
                "trend": atr.trend.value if atr else None,
            },
            "bollinger": {
                "upper": bb.upper if bb else None,
                "middle": bb.middle if bb else None,
                "lower": bb.lower if bb else None,
                "percent_b": bb.percent_b if bb else None,
                "is_squeeze": bb.is_squeeze if bb else None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indicators summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export for registration in main.py
