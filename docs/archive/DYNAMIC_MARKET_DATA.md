# Dynamic Market Data System

This system provides **fully dynamic** market analysis that works with any symbol, timeframe, or lookback period. Everything is computed on-demand from real market data.

## Architecture

### 1. Backend - Data Fetching & Analysis

**`backend/data_fetcher.py`**
- Fetches OHLCV data from multiple sources (Binance, Twelve Data, Yahoo Finance, or dummy data)
- Supports any symbol and timeframe
- Configurable via environment variables

**`backend/api/chart_analysis.py`**
- Detects swing highs and lows dynamically
- Configurable swing detection period
- Returns detailed data with prices, timestamps, and indices

### 2. Frontend - Dynamic Rendering

**`script/dashboard/chart_lines.js`**
- Fetches data based on current configuration
- Renders lines accurately using price range from API
- Supports dynamic updates when symbol/timeframe changes

## API Endpoint

### `GET /api/chart/highs-lows`

**Parameters:**
- `symbol` (required): Trading symbol (e.g., XAUUSD, EURUSD, BTCUSDT)
- `timeframe` (optional): Chart timeframe (1m, 5m, 15m, 1h, 4h, 1d) - default: "1h"
- `lookback` (optional): Number of candles to analyze - default: 100
- `period` (optional): Swing detection period (candles on each side) - default: 5
- `max_levels` (optional): Maximum number of major levels - default: 10

**Example:**
```
GET /api/chart/highs-lows?symbol=XAUUSD&timeframe=1h&lookback=200&period=7&max_levels=15
```

**Response:**
```json
{
  "symbol": "XAUUSD",
  "timeframe": "1h",
  "lookback": 200,
  "period": 7,
  "dataPoints": 200,
  "swingHighs": [
    {
      "price": 2050.50,
      "index": 45,
      "timestamp": "2024-01-15T10:30:00"
    }
  ],
  "swingLows": [...],
  "majorHighs": [2050.50, 2045.20, ...],
  "majorLows": [1980.30, 1985.50, ...],
  "majorHighsDetailed": [...],
  "majorLowsDetailed": [...],
  "priceRange": {
    "min": 1980.30,
    "max": 2050.50,
    "current": 2020.00
  },
  "timestamp": "2024-01-15T12:00:00"
}
```

## Data Sources

### Current: Dummy Data
Uses `backend/dummy_analysis.py` to generate realistic mock data.

### Real Data Sources (Ready to Use)

#### Binance
```bash
export DATA_SOURCE=binance
```
- Supports crypto pairs (BTCUSDT, ETHUSDT, etc.)
- Free, no API key required for public endpoints
- High rate limits

#### Twelve Data
```bash
export DATA_SOURCE=twelvedata
export TWELVEDATA_API_KEY=your_api_key
```
- Supports stocks, forex, crypto
- Requires free API key from https://twelvedata.com
- Good for forex pairs (XAUUSD, EURUSD, etc.)

#### Yahoo Finance
```bash
export DATA_SOURCE=yahoo
pip install yfinance
```
- Supports stocks, forex, crypto
- Free, no API key required
- Good for stocks and major forex pairs

## Usage

### Backend

1. **Start the backend:**
   ```bash
   python backend/main.py
   ```

2. **Test the API:**
   ```bash
   curl "http://localhost:8000/api/chart/highs-lows?symbol=XAUUSD&timeframe=1h&lookback=100"
   ```

### Frontend

1. **Automatic Loading:**
   - Chart automatically fetches data when it loads
   - Uses default config: XAUUSD, 1h, 100 candles

2. **Dynamic Updates:**
   ```javascript
   // Update symbol
   updateChartConfig({ symbol: 'EURUSD' });
   
   // Update timeframe
   updateChartConfig({ timeframe: '4h' });
   
   // Update lookback
   updateChartConfig({ lookback: 200 });
   
   // Update swing detection sensitivity
   updateChartConfig({ period: 7 }); // Higher = fewer, more significant swings
   
   // Update max levels
   updateChartConfig({ maxLevels: 15 });
   ```

3. **Get Current Config:**
   ```javascript
   const config = getChartConfig();
   console.log(config);
   ```

## Swing Detection

### How It Works

A **swing high** is a candle where:
- Its high is higher than `period` candles on each side

A **swing low** is a candle where:
- Its low is lower than `period` candles on each side

### Period Parameter

- **Lower period (3-5)**: More swings detected, more sensitive
- **Higher period (7-10)**: Fewer swings, only major pivots

### Major Levels Filtering

The system filters swing points to return only "major" levels:
- Removes levels too close together (< 0.5% of price range)
- Returns top N most significant levels
- Sorted by price (highs descending, lows ascending)

## Integration with Real APIs

### Step 1: Choose Data Source

Set environment variable:
```bash
export DATA_SOURCE=binance  # or twelvedata, yahoo
```

### Step 2: Add API Keys (if needed)

For Twelve Data:
```bash
export TWELVEDATA_API_KEY=your_key_here
```

### Step 3: Install Dependencies

```bash
pip install httpx  # For Binance/Twelve Data
pip install yfinance  # For Yahoo Finance
```

### Step 4: Test

The system will automatically use the selected data source. If it fails, it falls back to dummy data.

## Customization

### Adding New Data Sources

1. Add function to `backend/data_fetcher.py`:
   ```python
   async def fetch_from_your_source(symbol, timeframe, lookback):
       # Your implementation
       pass
   ```

2. Add to `fetch_ohlcv_data()`:
   ```python
   elif source == "yoursource":
       return await fetch_from_your_source(symbol, timeframe, lookback)
   ```

### Adjusting Swing Detection

Modify `detect_swing_highs()` and `detect_swing_lows()` in `backend/api/chart_analysis.py` to:
- Change period calculation
- Add volume filters
- Add trend filters
- Add time-based filters

### Frontend Customization

Modify `script/dashboard/chart_lines.js` to:
- Change line colors/styles
- Add markers instead of lines
- Add zones/rectangles
- Add labels/tooltips

## Benefits

✅ **Fully Dynamic**: Works with any symbol, timeframe, or period  
✅ **No Hardcoding**: All levels computed from data  
✅ **Scalable**: Easy to add new data sources  
✅ **Configurable**: Adjust sensitivity, lookback, max levels  
✅ **Real-time Ready**: Can be extended for live data streaming  
✅ **Frontend Agnostic**: JSON data works with any chart library  

## Next Steps

1. **Add Real Data Source**: Choose Binance, Twelve Data, or Yahoo Finance
2. **Add WebSocket Support**: For real-time updates
3. **Add Caching**: Cache API responses to reduce API calls
4. **Add Historical Storage**: Store analysis results in database
5. **Add User Preferences**: Save user's preferred symbols/timeframes























