# Real-Time Data Setup Guide

## Quick Start - Enable Real-Time Data

### Option 1: Finnhub (Recommended - Free Tier Available)

1. **Get free API key:**
   - Visit: https://finnhub.io/
   - Sign up for free account
   - Get your API key

2. **Set environment variable:**
   ```bash
   # Windows PowerShell
   $env:FINNHUB_API_KEY="your_api_key_here"
   
   # Windows CMD
   set FINNHUB_API_KEY=your_api_key_here
   
   # Or create .env file in project root:
   FINNHUB_API_KEY=your_api_key_here
   ```

3. **Set data source:**
   ```bash
   $env:DATA_SOURCE="finnhub"
   ```

4. **Restart backend:**
   ```bash
   python backend/main.py
   ```

### Option 2: Alpha Vantage (Free Tier)

1. **Get free API key:**
   - Visit: https://www.alphavantage.co/support/#api-key
   - Get your free API key

2. **Set environment variable:**
   ```bash
   $env:ALPHAVANTAGE_API_KEY="your_api_key_here"
   $env:DATA_SOURCE="alphavantage"
   ```

3. **Restart backend**

### Option 3: Binance (Free, No API Key Needed)

1. **Set data source:**
   ```bash
   $env:DATA_SOURCE="binance"
   ```

2. **Note:** Works for crypto pairs (BTCUSDT, ETHUSDT, etc.)
   - For forex like XAUUSD, use Finnhub or Alpha Vantage

## How Real-Time Updates Work

1. **Backend fetches real-time data** from your chosen API
2. **Frontend automatically refreshes** based on timeframe:
   - 1m charts: Refresh every 60 seconds
   - 5m charts: Refresh every 5 minutes
   - 15m charts: Refresh every 15 minutes
   - 1h charts: Refresh every hour
   - 4h charts: Refresh every 4 hours
   - 1d charts: Refresh daily

3. **Arrows update automatically** when new data arrives
4. **Swing detection recalculates** with fresh data

## Verify Real-Time Data

1. **Check backend logs:**
   - Should show "Fetching from Finnhub" (or your chosen source)
   - Should NOT show "using dummy data"

2. **Check frontend log panel:**
   - Should show "Refreshing market data..." periodically
   - Should show updated swing counts

3. **Watch arrows:**
   - New arrows should appear as new swings are detected
   - Arrows should move with price changes

## Troubleshooting

### Still seeing dummy data?

1. **Check environment variable:**
   ```bash
   echo $env:DATA_SOURCE  # PowerShell
   echo %DATA_SOURCE%     # CMD
   ```

2. **Check API key:**
   ```bash
   echo $env:FINNHUB_API_KEY
   ```

3. **Check backend logs** for error messages

### API rate limits?

- **Finnhub Free:** 60 calls/minute
- **Alpha Vantage Free:** 5 calls/minute, 500/day
- **Binance:** Very high limits

If you hit limits, the system falls back to dummy data automatically.

## Current Status

The system is now configured to:
- ✅ Fetch real-time data (when API keys are set)
- ✅ Auto-refresh based on timeframe
- ✅ Update arrows with new swings
- ✅ Fallback to dummy data if API fails

**Default:** Uses Finnhub (no API key needed for basic forex data, but limited)























