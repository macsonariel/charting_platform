# Trading Buddy Backend

Backend API for Trading Buddy using FastAPI.

## Project Structure

```
backend/
├── __init__.py
├── main.py                 # Main FastAPI application
├── chart/
│   ├── config/             # Timeframe configuration
│   ├── data/               # Data fetching utilities
│   └── engines/            # Analysis engines
│       └── core/           # Core analysis engine (main)
├── api/
│   ├── __init__.py
│   ├── chart_data.py       # Chart data endpoints
│   ├── core_api.py         # Core analysis endpoints
│   └── narrative_api.py    # Narrative generation endpoints
└── README.md
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the backend:
```bash
python backend/main.py
```

Or using uvicorn directly:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check
- `GET /api/health` - Health check endpoint

### Chart Data
- `GET /api/chart/ohlcv?symbol=BTCUSDT&timeframe=1h&lookback=100` - Fetch OHLCV data from Binance
- `GET /api/chart/highs-lows?symbol=BTCUSDT&timeframe=1h&lookback=100` - Get major highs and lows

## Data Sources

The backend fetches real market data from:
- **Binance** (default) - Free API, no key required for crypto pairs (BTCUSDT, ETHUSDT, etc.)
- **Yahoo Finance** - Stocks, forex, and crypto

## Development

All Python files are organized in the `backend/` directory:
- `main.py` - FastAPI app entry point
- `chart/chart_data_fetcher.py` - Real-time market data fetching
- `api/` - API route handlers























