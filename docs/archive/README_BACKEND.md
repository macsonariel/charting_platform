# Trading Buddy - Backend Setup

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the backend server:**
   ```bash
   python backend/main.py
   ```
   
   The API will be available at `http://localhost:8000`

3. **Test the API:**
   - Health check: `http://localhost:8000/api/health`
   - Get highs/lows: `http://localhost:8000/api/chart/highs-lows?symbol=XAUUSD&timeframe=1h&lookback=100`

## Project Structure

All Python files are organized in the `backend/` folder:

```
backend/
├── main.py                 # FastAPI application entry point
├── dummy_analysis.py       # Mock market analysis functions
└── api/
    └── chart_analysis.py  # Chart analysis endpoints
```

## Features

- **Chart Analysis API**: Detects major highs and lows from market data
- **Swing Detection**: Identifies swing highs and lows using a period-based algorithm
- **Major Levels**: Filters and returns the most significant support/resistance levels

## API Endpoints

### `/api/chart/highs-lows`
Returns major highs and lows for drawing horizontal lines on the chart.

**Parameters:**
- `symbol` (required): Trading symbol (e.g., XAUUSD, EURUSD)
- `timeframe` (optional): Chart timeframe (default: "1h")
- `lookback` (optional): Number of candles to analyze (default: 100)

**Response:**
```json
{
  "symbol": "XAUUSD",
  "timeframe": "1h",
  "majorHighs": [2050.50, 2045.20, 2040.10],
  "majorLows": [1980.30, 1985.50, 1990.20],
  "timestamp": "2024-01-15T10:30:00"
}
```

## Frontend Integration

The frontend automatically fetches highs/lows when the home page loads and draws horizontal lines on the TradingView chart. Make sure the backend is running before opening the dashboard.
























