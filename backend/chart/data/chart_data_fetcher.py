"""
Market Data Fetcher
Fetches real-time OHLCV data from various sources.

This is the SINGLE SOURCE for all market data fetching across all engines.
Use this module instead of engine-specific adapters.

Usage:
    # For raw dict data:
    raw_data = await fetch_ohlcv_data("BTCUSDT", "1h", 400)
    
    # For Core Engine Candle objects:
    candles = await async_fetch_and_convert("BTCUSDT", "1h", 400)
"""

from typing import List, Dict, Optional, TYPE_CHECKING
from datetime import datetime
import os
import asyncio

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, use system env vars

# Lazy import for Candle to avoid circular imports
if TYPE_CHECKING:
    from backend.chart.engines.core.schemas.candle import Candle

# Try to import httpx, but make it optional
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

# Try to import requests as alternative
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

# Try to import polygon client for Massive.com/Polygon.io forex data
try:
    from polygon import RESTClient as PolygonClient
    POLYGON_AVAILABLE = True
except ImportError:
    POLYGON_AVAILABLE = False
    PolygonClient = None

# =============================================================================
# CACHING INFRASTRUCTURE
# =============================================================================

# In-memory cache for API responses
# Structure: {cache_key: {"data": [...], "timestamp": datetime, "ttl": seconds}}
_data_cache: Dict[str, Dict] = {}

# Pending requests for deduplication (prevents duplicate concurrent requests)
_pending_requests: Dict[str, asyncio.Future] = {}

# Default TTL values (in seconds)
CACHE_TTL_REALTIME = 30      # 30s for real-time data (1m, 5m timeframes)
CACHE_TTL_STANDARD = 120     # 2min for standard timeframes (15m, 1h)
CACHE_TTL_HISTORICAL = 300   # 5min for historical data (4h, 1d, 1w)


def _get_cache_key(symbol: str, timeframe: str, lookback: int, source: str) -> str:
    """Generate cache key for a request."""
    return f"{source}_{symbol.upper()}_{timeframe}_{lookback}"


def _get_ttl_for_timeframe(timeframe: str) -> int:
    """Get appropriate TTL based on timeframe."""
    if timeframe in ("1m", "5m"):
        return CACHE_TTL_REALTIME
    elif timeframe in ("15m", "1h"):
        return CACHE_TTL_STANDARD
    else:
        return CACHE_TTL_HISTORICAL


def _get_from_cache(cache_key: str) -> Optional[List[Dict]]:
    """Get data from cache if valid (not expired)."""
    if cache_key not in _data_cache:
        return None
    
    cached = _data_cache[cache_key]
    elapsed = (datetime.now() - cached["timestamp"]).total_seconds()
    
    if elapsed > cached["ttl"]:
        # Cache expired, remove it
        del _data_cache[cache_key]
        return None
    
    return cached["data"]


def _set_cache(cache_key: str, data: List[Dict], ttl: int) -> None:
    """Store data in cache with TTL."""
    _data_cache[cache_key] = {
        "data": data,
        "timestamp": datetime.now(),
        "ttl": ttl
    }


def clear_cache(symbol: Optional[str] = None) -> int:
    """Clear cache entries. If symbol provided, only clear that symbol's entries.
    
    Returns number of entries cleared.
    """
    global _data_cache
    
    if symbol is None:
        count = len(_data_cache)
        _data_cache = {}
        return count
    
    symbol_upper = symbol.upper()
    keys_to_delete = [k for k in _data_cache if f"_{symbol_upper}_" in k]
    for key in keys_to_delete:
        del _data_cache[key]
    return len(keys_to_delete)


async def fetch_ohlcv_data(
    symbol: str,
    timeframe: str = "1h",
    lookback: int = 100,
    source: Optional[str] = None,
    use_cache: bool = True
) -> List[Dict]:
    """
    Fetch OHLCV data from market data provider (real-time when possible)
    
    Args:
        symbol: Trading symbol (e.g., BTCUSD, BTCUSDT, XAUUSD, EURUSD, GBPUSD)
        timeframe: Chart timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        lookback: Number of candles to fetch
        source: Data source ('binance', 'yahoo', 'massive') - auto-detected for forex
        use_cache: Whether to use cached data if available (default: True)
    
    Returns:
        List of OHLCV dictionaries with timestamp, open, high, low, close, volume
    """
    # Forex pairs that should use Massive.com/Polygon.io
    FOREX_PAIRS = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"}
    
    # Auto-detect forex pairs and route to Massive.com
    symbol_upper = symbol.upper()
    if symbol_upper in FOREX_PAIRS or symbol_upper.startswith("C:"):
        source = "massive"
    else:
        source = source or os.getenv("DATA_SOURCE", "binance")
    
    # Generate cache key
    cache_key = _get_cache_key(symbol, timeframe, lookback, source)
    
    # Check cache first
    if use_cache:
        cached_data = _get_from_cache(cache_key)
        if cached_data is not None:
            print(f"📦 Cache hit for {cache_key}")
            return cached_data
    
    # Check for pending request (deduplication)
    if cache_key in _pending_requests:
        print(f"⏳ Waiting for pending request: {cache_key}")
        return await _pending_requests[cache_key]
    
    async def fetch_from_source():
        if source == "binance":
            return await fetch_from_binance(symbol, timeframe, lookback)
        if source == "yahoo":
            return await fetch_from_yahoo(symbol, timeframe, lookback)
        if source == "massive":
            return await fetch_from_massive(symbol, timeframe, lookback)
        raise ValueError(f"Unknown data source: {source}. Supported sources: binance, yahoo, massive")

    # Store the actual task. Leaders and followers now await the same task, so
    # failures are consumed instead of leaving an unobserved Future exception.
    task = asyncio.create_task(fetch_from_source())
    _pending_requests[cache_key] = task

    try:
        data = await task
        
        # Store in cache
        ttl = _get_ttl_for_timeframe(timeframe)
        _set_cache(cache_key, data, ttl)
        print(f"💾 Cached {len(data)} candles for {cache_key} (TTL: {ttl}s)")
        
        return data
    finally:
        # Remove from pending requests
        _pending_requests.pop(cache_key, None)


async def fetch_from_binance(symbol: str, timeframe: str, lookback: int) -> List[Dict]:
    """
    Fetch real-time OHLCV data from Binance API (free, no API key needed)
    Works for crypto pairs: BTCUSDT, ETHUSDT, etc.
    
    Supports pagination for fetching more than 1000 candles.
    """
    try:
        # Convert symbol format (BTCUSD -> BTCUSDT for Binance)
        binance_symbol = symbol.upper()
        if binance_symbol == "BTCUSD":
            binance_symbol = "BTCUSDT"
        elif not binance_symbol.endswith("USDT"):
            # Try to add USDT if it's a crypto symbol
            if len(binance_symbol) <= 6:  # Likely a crypto symbol
                binance_symbol = binance_symbol + "USDT"
        
        # Map timeframe to Binance interval
        timeframe_map = {
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h", "12h": "12h",
            "1d": "1d", "1D": "1d",
            "1w": "1w", "1W": "1w",
            "1M": "1M",
            "3M": "1M"  # Binance doesn't have 3M, use 1M and aggregate
        }
        interval = timeframe_map.get(timeframe, "1h")
        
        # Binance max is 1000 per request - paginate if needed
        all_ohlcv_data = []
        remaining = lookback
        end_time = None  # Start from most recent
        
        while remaining > 0:
            batch_size = min(remaining, 1000)
            
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                "symbol": binance_symbol,
                "interval": interval,
                "limit": batch_size
            }
            
            # Add endTime for pagination (fetch backwards in time)
            if end_time is not None:
                params["endTime"] = end_time - 1  # -1 to avoid duplicate
            
            # Use requests if httpx not available
            if REQUESTS_AVAILABLE:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.get(url, params=params, timeout=10.0)
                )
                response.raise_for_status()
                data = response.json()
            elif HTTPX_AVAILABLE:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
            else:
                raise ImportError("Neither httpx nor requests available")
            
            if not data:
                break  # No more data available
            
            # Prepend to list (since we're fetching backwards)
            for candle in data:
                all_ohlcv_data.insert(0, {
                    "timestamp": datetime.fromtimestamp(candle[0] / 1000).isoformat(),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                })
            
            # Update for next iteration
            remaining -= len(data)
            if len(data) < batch_size:
                break  # No more data available
            
            # Set end_time to the earliest candle's timestamp for next batch
            end_time = data[0][0]  # Open time of earliest candle in this batch
        
        # Sort by timestamp and return requested amount
        all_ohlcv_data.sort(key=lambda x: x["timestamp"])
        return all_ohlcv_data[-lookback:] if len(all_ohlcv_data) > lookback else all_ohlcv_data
        
    except Exception as e:
        print(f"Error fetching from Binance: {e}")
        raise RuntimeError(f"Failed to fetch data from Binance for {symbol}: {e}")


async def fetch_from_yahoo(symbol: str, timeframe: str, lookback: int) -> List[Dict]:
    """
    Fetch real-time OHLCV data from Yahoo Finance (free, no API key needed)
    Works for stocks, forex, and crypto
    """
    try:
        import yfinance as yf
        
        # Convert symbol format for Yahoo Finance
        yahoo_symbol = symbol.upper()
        if yahoo_symbol == "BTCUSD":
            yahoo_symbol = "BTC-USD"  # Yahoo Finance format
        
        # Map timeframe to yfinance period
        period_map = {
            "1m": "1d", "5m": "5d", "15m": "15d",
            "1h": "60d", "4h": "250d", "1d": "1y",
            "1w": "5y", "1M": "10y", "3M": "10y"
        }
        period = period_map.get(timeframe, "60d")
        
        # Map timeframe to yfinance interval
        interval_map = {
            "1m": "1m", "5m": "5m", "15m": "15m",
            "1h": "1h", "4h": "1h", "1d": "1d",  # yfinance doesn't support 4h directly
            "1w": "1wk", "1M": "1mo", "3M": "3mo"
        }
        yf_interval = interval_map.get(timeframe, "1h")
        
        ticker = yf.Ticker(yahoo_symbol)
        hist = ticker.history(period=period, interval=yf_interval)
        
        if hist.empty:
            raise ValueError(f"No data available for {yahoo_symbol}")
        
        # Convert to our format
        ohlcv_data = []
        for idx, row in hist.tail(lookback).iterrows():
            ohlcv_data.append({
                "timestamp": idx.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"])
            })
        
        return ohlcv_data
        
    except Exception as e:
        print(f"Error fetching from Yahoo Finance: {e}")
        raise RuntimeError(f"Failed to fetch data from Yahoo Finance for {symbol}: {e}")


async def fetch_from_massive(symbol: str, timeframe: str, lookback: int) -> List[Dict]:
    """
    Fetch OHLCV data from Massive.com/Polygon.io API for forex pairs.
    
    Requires MASSIVE_API_KEY environment variable to be set.
    Symbol format: EURUSD, GBPUSD (will be converted to C:EURUSD format)
    """
    if not POLYGON_AVAILABLE:
        raise ImportError("polygon-api-client not installed. Run: pip install polygon-api-client")
    
    api_key = os.getenv("MASSIVE_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise ValueError("MASSIVE_API_KEY environment variable not set. Add your API key to .env file.")
    
    try:
        # Convert symbol to Polygon forex format (C:EURUSD)
        symbol_upper = symbol.upper()
        if not symbol_upper.startswith("C:"):
            polygon_symbol = f"C:{symbol_upper}"
        else:
            polygon_symbol = symbol_upper
        
        # Map timeframe to Polygon multiplier and timespan
        timeframe_map = {
            "1m": (1, "minute"),
            "5m": (5, "minute"),
            "15m": (15, "minute"),
            "30m": (30, "minute"),
            "1h": (1, "hour"),
            "4h": (4, "hour"),
            "1d": (1, "day"),
            "1w": (1, "week"),
        }
        multiplier, timespan = timeframe_map.get(timeframe, (1, "hour"))
        
        # Calculate date range
        from datetime import timedelta
        end_date = datetime.now()
        
        # Estimate how many days we need based on timeframe
        if timespan == "minute":
            days_needed = max(1, (lookback * multiplier) // (60 * 24) + 1)
        elif timespan == "hour":
            days_needed = max(1, (lookback * multiplier) // 24 + 1)
        elif timespan == "day":
            days_needed = lookback * multiplier + 1
        elif timespan == "week":
            days_needed = lookback * multiplier * 7 + 1
        else:
            days_needed = lookback
        
        start_date = end_date - timedelta(days=days_needed)
        
        # Use Polygon client to fetch forex data
        client = PolygonClient(api_key)
        
        # Fetch aggregates (forex uses same endpoint)
        aggs = client.get_aggs(
            ticker=polygon_symbol,
            multiplier=multiplier,
            timespan=timespan,
            from_=start_date.strftime("%Y-%m-%d"),
            to=end_date.strftime("%Y-%m-%d"),
            limit=50000
        )
        
        if not aggs:
            raise ValueError(f"No data returned for {polygon_symbol}")
        
        # Convert to our format
        ohlcv_data = []
        for bar in aggs:
            ohlcv_data.append({
                "timestamp": datetime.fromtimestamp(bar.timestamp / 1000).isoformat(),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume) if bar.volume else 0.0
            })
        
        # Sort by timestamp and return requested amount
        ohlcv_data.sort(key=lambda x: x["timestamp"])
        return ohlcv_data[-lookback:] if len(ohlcv_data) > lookback else ohlcv_data
        
    except Exception as e:
        print(f"Error fetching from Massive.com/Polygon: {e}")
        raise RuntimeError(f"Failed to fetch data from Massive.com for {symbol}: {e}")


# =============================================================================
# CANDLE CONVERSION UTILITIES
# =============================================================================

def convert_to_candles(raw_data: List[Dict], timeframe: str = "1h") -> List["Candle"]:
    """Convert raw OHLCV dicts to Core Engine Candle objects.
    
    Args:
        raw_data: List of dicts with timestamp, open, high, low, close, volume
        timeframe: Chart timeframe (for Candle metadata)
        
    Returns:
        List of Core Engine Candle objects
    """
    from backend.chart.engines.core.schemas.candle import Candle
    
    candles = []
    for item in raw_data:
        # Handle timestamp conversion
        timestamp = item.get('timestamp', 0)
        if isinstance(timestamp, str):
            try:
                timestamp = int(datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp() * 1000)
            except:
                timestamp = 0
        elif isinstance(timestamp, (int, float)):
            # If timestamp is in seconds, convert to milliseconds
            if timestamp < 1e12:
                timestamp = int(timestamp * 1000)
            else:
                timestamp = int(timestamp)
        
        candle = Candle(
            timestamp=timestamp,
            open=float(item.get('open', 0)),
            high=float(item.get('high', 0)),
            low=float(item.get('low', 0)),
            close=float(item.get('close', 0)),
            volume=float(item.get('volume', 0)),
        )
        candles.append(candle)
    
    return candles


async def async_fetch_and_convert(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    lookback: int = 200,
    source: Optional[str] = None
) -> List["Candle"]:
    """Async fetch and convert to Core Engine Candle objects.
    
    This is the PRIMARY function for engines to use.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        timeframe: Chart timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        lookback: Number of candles to fetch
        source: Data source ('binance', 'yahoo') - defaults to env or 'binance'
        
    Returns:
        List of Core Engine Candle objects
    """
    raw_data = await fetch_ohlcv_data(symbol, timeframe, lookback, source)
    return convert_to_candles(raw_data, timeframe)


def fetch_and_convert(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    lookback: int = 200,
    source: Optional[str] = None
) -> List["Candle"]:
    """Synchronous wrapper to fetch and convert data to Candles.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        timeframe: Chart timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        lookback: Number of candles to fetch
        source: Data source ('binance', 'yahoo') - defaults to env or 'binance'
        
    Returns:
        List of Core Engine Candle objects
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, use thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                raw_data = pool.submit(
                    lambda: asyncio.run(fetch_ohlcv_data(symbol, timeframe, lookback, source))
                ).result()
        else:
            raw_data = loop.run_until_complete(fetch_ohlcv_data(symbol, timeframe, lookback, source))
    except RuntimeError:
        # No event loop, create new one
        raw_data = asyncio.run(fetch_ohlcv_data(symbol, timeframe, lookback, source))
    
    return convert_to_candles(raw_data, timeframe)
