"""
Simple Chart Data API
Fetches OHLCV data for charts (real-time when available)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict
from datetime import datetime
import sys
import os

# Add project root to path (parent of backend directory)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.chart.data import chart_data_fetcher

router = APIRouter()


@router.get("/api/chart-data")
async def get_chart_data(
    symbol: str = Query("BTCUSD", description="Trading symbol (e.g., BTCUSD, BTCUSDT, XAUUSD)"),
    periods: int = Query(100, description="Number of candles"),
    timeframe: str = Query("1h", description="Chart timeframe (1m, 5m, 15m, 1h, 4h, 1d)"),
    source: Optional[str] = Query(None, description="Data source (binance, yahoo, dummy). Defaults to env var or binance")
):
    """
    Get OHLCV data for chart display (real-time when available)
    
    Args:
        symbol: Trading symbol
        periods: Number of candles to return
        timeframe: Chart timeframe
        source: Data source override
    
    Returns:
        JSON with OHLCV data formatted for TradingView charts
    """
    try:
        # Fetch real-time data (falls back to dummy if API fails)
        ohlcv_data = await chart_data_fetcher.fetch_ohlcv_data(
            symbol=symbol,
            timeframe=timeframe,
            lookback=periods,
            source=source
        )
        
        # Convert to TradingView format
        chart_data = []
        for item in ohlcv_data:
            # Convert ISO timestamp to Unix timestamp
            try:
                if isinstance(item['timestamp'], str):
                    timestamp = int(datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')).timestamp())
                else:
                    timestamp = int(item['timestamp'])
            except:
                # Fallback: use current time if timestamp parsing fails
                timestamp = int(datetime.now().timestamp())
            
            chart_data.append({
                "time": timestamp,
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": float(item.get("volume", 0))
            })
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": chart_data,
            "count": len(chart_data),
            "source": source or os.getenv("DATA_SOURCE", "binance")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching chart data: {str(e)}"
        )

