# Swing-First Core Migration

The application now has one market-structure authority: `backend.chart.engines.core`.

## Current boundaries

| Component | Role |
| --- | --- |
| Core pipeline | Owns swings, structure, direction, regime, levels, and analysis snapshot |
| Core API | Caches and projects one snapshot into all Core HTTP contracts |
| Analysis panel controller | Publishes one summary view model to the right and bottom panels |
| Indicators engine | Optional technical-indicator calculations and overlays |
| Narrative code | Presentation only; it must consume Core output |

The older universal-structure browser pipeline, phase-tuning UI, bottom-panel analyzer, and Python `core_interpreter` state machine were removed because each could produce a conflicting direction or phase.

## Import example

```python
from backend.chart.engines.core import Candle, MarketRegime, MarketSnapshot, run_pipeline

snapshot = run_pipeline(candles, "BTCUSDT", "1h")
regime: MarketRegime = snapshot.regime
```

Use `snapshot.regime` for direction, bias, state, phase, confidence, and provenance. Do not infer those values again from serialized event counts in an API or UI consumer.
