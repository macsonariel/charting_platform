# Adding Order Blocks Indicator to TradingView Chart

## Quick Setup

The Order Blocks indicator is ready to be added to your TradingView chart, just like RSI and MA. However, since it's a custom indicator, you need to publish it on TradingView first.

## Steps to Add Order Blocks

### Option 1: Publish and Use Script ID (Recommended)

1. **Publish the Pine Script:**
   - Go to [TradingView.com](https://www.tradingview.com)
   - Open Pine Editor
   - Copy the code from `pine_scripts/order_blocks.pine`
   - Paste it into Pine Editor
   - Click "Publish" and make it public
   - Copy the published script ID (format: `PUB;username/scriptname`)

2. **Add to Chart:**
   - Open `script/dashboard/simple-chart.js`
   - Find the `studies` array (around line 56)
   - Uncomment the Order Blocks entry
   - Replace `"PUB;your_username/order_blocks"` with your actual published script ID
   - Save and refresh the chart

### Option 2: Manual Addition

1. Open the TradingView chart
2. Click "Pine Editor" at the bottom
3. Copy code from `pine_scripts/order_blocks.pine`
4. Paste into Pine Editor
5. Click "Add to Chart"

## Current Status

The Order Blocks indicator is:
- ✅ Created in `backend/indicators/order_blocks.py`
- ✅ Pine Script ready in `pine_scripts/order_blocks.pine`
- ✅ API endpoint available at `/api/indicators/order-blocks`
- ⏳ Waiting to be added to chart (needs publishing or manual addition)

Once published and added, it will appear automatically on the chart just like RSI and MA!















