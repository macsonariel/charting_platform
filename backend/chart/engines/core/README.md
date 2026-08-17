# Core Engine

The Core Engine is the single authority for Trading Buddy's market-structure view. Its decisions begin with confirmed swing points derived from OHLCV candles. The right analysis panel, bottom Quick Overview strip, and Core chart layers consume projections of the same cached `MarketSnapshot`.

## Authority and data flow

```text
market-data provider
    -> Candle[]
    -> swing detection, scoring, and classification
    -> structure events, moves, protected levels, and swing-bounded ranges
    -> DirectionAnalysis
    -> MarketRegime
    -> MarketSnapshot
    -> /api/core/summary, /render, /analysis, /analyze
    -> chart and panels
```

`MarketRegime` is the only source of direction, bias, state, phase, and regime confidence. `MarketAnalysis` and the compatibility `snapshot.interpretation` are presentation views; they must not independently reclassify those fields.

Direction provenance is explicit:

- Complete external swing structure is preferred.
- If there are not enough external swings, the engine falls back to all classified structural swings.
- `direction_source`, `source_timeframe`, `swing_degree`, and `fallback_used` disclose which path was used.

## Package layout

```text
core/
  analyzers/     Canonical regime plus actionable/presentation analysis
  detectors/     Swing-first fact detection
  evaluation/    No-lookahead historical replay and outcome scoring
  pipeline/      Ordered construction of MarketSnapshot
  schemas/       Dataclasses and serialized contracts
  trackers/      Recent-event tracking
```

The former `core_interpreter` state machine was removed because it duplicated regime authority. Narrative helpers may describe a snapshot, but cannot define a competing market state.

## Pipeline order

1. Detect, score, and classify swings.
2. Derive structure events and directional moves from those swings.
3. Track protected levels and legs.
4. Detect supplementary Core facts: liquidity, FVGs, and zones.
5. Detect ranges from repeated swing boundaries.
6. Select authoritative direction swings and record provenance.
7. Build the fact-only `MarketSnapshot`.
8. Derive one canonical `MarketRegime`.
9. Build actionable and human-readable presentation fields from that regime.

Supplementary candle facts can raise or lower confidence, but they do not replace swing structure as the directional authority.

## Usage

```python
from backend.chart.data.chart_data_fetcher import async_fetch_and_convert
from backend.chart.engines.core.pipeline import run_pipeline

candles = await async_fetch_and_convert("BTCUSDT", "1h", 400)
snapshot = run_pipeline(candles, "BTCUSDT", "1h")

print(snapshot.regime.direction)
print(snapshot.regime.state)
print(snapshot.regime.direction_source)
print(snapshot.direction_analysis.pattern_swings)
```

## HTTP contracts

All Core endpoints use the shared snapshot loader and a short-lived cache keyed by data source, symbol, timeframe, and period count.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/core/summary` | Compact, versioned view model for both panels; also exposes the exact direction swing pattern |
| `GET /api/core/render` | Chart drawing data from the same snapshot |
| `GET /api/core/analysis` | Detailed compatibility response |
| `GET /api/core/analyze` | Raw snapshot for development and diagnostics |
| `GET /api/core/mtf-confluence` | Regime direction from several independently analyzed timeframes |
| `GET /api/core/zone-visibility` | Visible Core zones for the current price |

Provider failures return an unavailable response; endpoints must not invent sample analysis.

## Browser consumers

- `app/js/analysis-panel/panel-controller.js` owns the summary request.
- `analysis-panel-v2.js` writes the right panel and bottom Quick Overview.
- `core-engine.js` renders raw Core facts.
- `market-chart.js` obtains direction markers from the Core summary contract.

Technical indicators are optional overlays. They are not a source of Core direction or regime.

## Historical replay and evaluation

The evaluation package runs the real `Pipeline` repeatedly over expanding candle prefixes. At checkpoint `i`, Core receives only `candles[:i + 1]`. Later candles are read only after that snapshot is frozen and are used to label forward outcomes. This keeps the swing detector's normal confirmation lag instead of backdating a swing decision to the candle where the high or low occurred.

Replay a local CSV for the most reproducible result:

```powershell
python -m backend.chart.engines.core.evaluation `
  --input .\data\btcusdt-1h.csv `
  --symbol BTCUSDT `
  --timeframe 1h `
  --warmup 100 `
  --horizons 1,3,6,12 `
  --output .\test_output_core_replay.json
```

The CSV must contain `timestamp,open,high,low,close`; `volume` is optional. Timestamps may be Unix seconds, Unix milliseconds, or ISO-8601 values. Rows must be strictly chronological.

To fetch a current provider window instead:

```powershell
python -m backend.chart.engines.core.evaluation `
  --symbol BTCUSDT `
  --timeframe 1h `
  --source binance `
  --periods 500 `
  --output .\test_output_core_replay.json
```

Each JSON record preserves:

- the canonical direction, bias, state, phase, confidence, and provenance;
- the exact swing pattern used for direction;
- structure-event, protected-level, and active-range facts available at that checkpoint;
- origin ATR and the latest candle that could have produced a confirmed swing;
- forward return, ATR-normalized return, excursion, observed label, and correctness at each horizon.

The report includes a SHA-256 fingerprint of the full OHLCV input. Summary metrics separate structural-direction accuracy from short-term-bias accuracy and include directional coverage, state/direction breakdowns, Brier score, and confidence bins. A future close inside `neutral_threshold_atr * origin ATR` is labelled neutral, so the label adapts to volatility without reading future volatility.

This is a classification evaluation, not a trading backtest. It does not model entries, exits, sizing, fees, slippage, funding, or execution. It currently evaluates one timeframe at a time; HTF swing inputs are deliberately omitted until they can also be replayed without lookahead. Do not tune detector parameters on the same date range used for final reporting—reserve later, untouched periods for validation.
