"""Candle-by-candle replay and outcome evaluation for the Core Engine.

The analysis at candle ``i`` is always produced from ``candles[:i + 1]``.
Candles after ``i`` are inspected only after the snapshot has been frozen, and
only to calculate labelled forward outcomes. This deliberately preserves the
confirmation delay of the symmetric swing detector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.chart.engines.core.pipeline import Pipeline
from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.snapshot import MarketSnapshot


REPORT_SCHEMA_VERSION = "1.0"
_DIRECTIONS = {"bullish", "bearish", "neutral"}


@dataclass(frozen=True)
class ReplayConfig:
    """Controls replay checkpoints and volatility-normalized labels."""

    warmup_candles: int = 80
    step: int = 1
    horizons: Tuple[int, ...] = (1, 3, 6, 12)
    atr_period: int = 14
    neutral_threshold_atr: float = 0.25

    def __post_init__(self) -> None:
        normalized_horizons = tuple(sorted(set(self.horizons)))
        object.__setattr__(self, "horizons", normalized_horizons)
        if self.warmup_candles < 2:
            raise ValueError("warmup_candles must be at least 2")
        if self.step < 1:
            raise ValueError("step must be at least 1")
        if not normalized_horizons or any(horizon < 1 for horizon in normalized_horizons):
            raise ValueError("horizons must contain positive candle counts")
        if self.atr_period < 1:
            raise ValueError("atr_period must be at least 1")
        if self.neutral_threshold_atr < 0:
            raise ValueError("neutral_threshold_atr cannot be negative")

    def to_dict(self) -> dict:
        return {
            "warmup_candles": self.warmup_candles,
            "step": self.step,
            "horizons": list(self.horizons),
            "atr_period": self.atr_period,
            "neutral_threshold_atr": self.neutral_threshold_atr,
        }


@dataclass(frozen=True)
class ForwardOutcome:
    """Observed price movement after one frozen Core prediction."""

    horizon_candles: int
    target_index: int
    target_timestamp: int
    target_close: float
    return_pct: float
    return_atr: Optional[float]
    max_up_pct: float
    max_down_pct: float
    observed_direction: str
    direction_correct: bool
    bias_correct: bool

    def to_dict(self) -> dict:
        return {
            "horizon_candles": self.horizon_candles,
            "target_index": self.target_index,
            "target_timestamp": self.target_timestamp,
            "target_close": _rounded(self.target_close, 8),
            "return_pct": _rounded(self.return_pct, 6),
            "return_atr": _rounded(self.return_atr, 6),
            "max_up_pct": _rounded(self.max_up_pct, 6),
            "max_down_pct": _rounded(self.max_down_pct, 6),
            "observed_direction": self.observed_direction,
            "direction_correct": self.direction_correct,
            "bias_correct": self.bias_correct,
        }


@dataclass
class ReplayRecord:
    """A frozen Core output and any outcomes available after it."""

    origin_index: int
    timestamp: int
    candle_count: int
    current_price: float
    atr: Optional[float]
    latest_confirmable_swing_index: int
    prediction: Dict[str, Any]
    structure: Dict[str, Any]
    outcomes: Dict[int, ForwardOutcome] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "origin_index": self.origin_index,
            "timestamp": self.timestamp,
            "candle_count": self.candle_count,
            "current_price": _rounded(self.current_price, 8),
            "atr": _rounded(self.atr, 8),
            "latest_confirmable_swing_index": self.latest_confirmable_swing_index,
            "prediction": self.prediction,
            "structure": self.structure,
            "outcomes": {
                str(horizon): outcome.to_dict()
                for horizon, outcome in sorted(self.outcomes.items())
            },
        }


@dataclass
class ReplayReport:
    """Serializable output of one historical replay."""

    symbol: str
    timeframe: str
    config: ReplayConfig
    records: List[ReplayRecord]
    data_fingerprint: str
    data_start_timestamp: int
    data_end_timestamp: int
    candle_count: int
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def summary(self) -> dict:
        return summarize_records(self.records, self.config.horizons)

    def to_dict(self) -> dict:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "methodology": {
                "no_lookahead": True,
                "analysis_input": "candles through and including each origin_index",
                "future_data_usage": "forward outcome labels only",
                "confidence_target": "exact direction-label correctness",
            },
            "dataset": {
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "candle_count": self.candle_count,
                "start_timestamp": self.data_start_timestamp,
                "end_timestamp": self.data_end_timestamp,
                "sha256": self.data_fingerprint,
            },
            "config": self.config.to_dict(),
            "summary": self.summary,
            "records": [record.to_dict() for record in self.records],
        }


def run_replay(
    candles: Sequence[Candle],
    symbol: str,
    timeframe: str,
    config: Optional[ReplayConfig] = None,
) -> ReplayReport:
    """Replay the real Core pipeline over incrementally revealed candles."""
    replay_config = config or ReplayConfig()
    normalized = _normalize_and_validate_candles(candles)
    if len(normalized) < replay_config.warmup_candles:
        raise ValueError(
            f"Replay needs at least {replay_config.warmup_candles} candles; "
            f"received {len(normalized)}"
        )

    pipeline = Pipeline()
    swing_lookback = pipeline._get_lookback_for_timeframe(timeframe)
    records: List[ReplayRecord] = []

    for origin_index in range(
        replay_config.warmup_candles - 1,
        len(normalized),
        replay_config.step,
    ):
        available_candles = normalized[: origin_index + 1]
        snapshot = pipeline.run(available_candles, symbol, timeframe)
        atr = calculate_atr(available_candles, replay_config.atr_period)
        record = ReplayRecord(
            origin_index=origin_index,
            timestamp=available_candles[-1].timestamp,
            candle_count=len(available_candles),
            current_price=available_candles[-1].close,
            atr=atr,
            latest_confirmable_swing_index=max(-1, origin_index - swing_lookback),
            prediction=_snapshot_prediction(snapshot),
            structure=_snapshot_structure(snapshot),
        )

        for horizon in replay_config.horizons:
            if origin_index + horizon >= len(normalized):
                continue
            record.outcomes[horizon] = evaluate_forward_outcome(
                candles=normalized,
                origin_index=origin_index,
                horizon=horizon,
                predicted_direction=record.prediction["direction"],
                predicted_bias=record.prediction["bias"],
                atr=atr,
                neutral_threshold_atr=replay_config.neutral_threshold_atr,
            )
        records.append(record)

    return ReplayReport(
        symbol=symbol,
        timeframe=timeframe,
        config=replay_config,
        records=records,
        data_fingerprint=_fingerprint(normalized),
        data_start_timestamp=normalized[0].timestamp,
        data_end_timestamp=normalized[-1].timestamp,
        candle_count=len(normalized),
    )


def calculate_atr(candles: Sequence[Candle], period: int = 14) -> Optional[float]:
    """Calculate a simple rolling ATR using only the supplied candles."""
    if not candles:
        return None
    start = max(0, len(candles) - period)
    true_ranges = []
    for index in range(start, len(candles)):
        candle = candles[index]
        if index == 0:
            true_range = candle.high - candle.low
        else:
            previous_close = candles[index - 1].close
            true_range = max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        true_ranges.append(true_range)
    return mean(true_ranges) if true_ranges else None


def evaluate_forward_outcome(
    candles: Sequence[Candle],
    origin_index: int,
    horizon: int,
    predicted_direction: str,
    predicted_bias: str,
    atr: Optional[float],
    neutral_threshold_atr: float,
) -> ForwardOutcome:
    """Label a frozen prediction from future prices.

    A close move within ``neutral_threshold_atr * origin ATR`` is labelled
    neutral. ATR must have been calculated from the origin prefix.
    """
    target_index = origin_index + horizon
    if horizon < 1 or origin_index < 0 or target_index >= len(candles):
        raise ValueError("origin_index and horizon must identify an available future candle")

    origin_price = candles[origin_index].close
    if origin_price == 0:
        raise ValueError("Cannot calculate percentage outcomes from a zero close")
    target = candles[target_index]
    forward_window = candles[origin_index + 1 : target_index + 1]
    price_change = target.close - origin_price
    threshold = (atr or 0.0) * neutral_threshold_atr
    if price_change > threshold:
        observed_direction = "bullish"
    elif price_change < -threshold:
        observed_direction = "bearish"
    else:
        observed_direction = "neutral"

    return ForwardOutcome(
        horizon_candles=horizon,
        target_index=target_index,
        target_timestamp=target.timestamp,
        target_close=target.close,
        return_pct=(price_change / origin_price) * 100,
        return_atr=(price_change / atr) if atr and atr > 0 else None,
        max_up_pct=((max(candle.high for candle in forward_window) - origin_price) / origin_price) * 100,
        max_down_pct=((min(candle.low for candle in forward_window) - origin_price) / origin_price) * 100,
        observed_direction=observed_direction,
        direction_correct=_normalize_direction(predicted_direction) == observed_direction,
        bias_correct=_normalize_direction(predicted_bias) == observed_direction,
    )


def summarize_records(records: Sequence[ReplayRecord], horizons: Sequence[int]) -> dict:
    """Aggregate accuracy, coverage, and confidence calibration by horizon."""
    summaries: Dict[str, dict] = {}
    for horizon in horizons:
        samples = [
            (record, record.outcomes[horizon])
            for record in records
            if horizon in record.outcomes
        ]
        if not samples:
            summaries[str(horizon)] = _empty_horizon_summary()
            continue

        direction_correct = [outcome.direction_correct for _, outcome in samples]
        bias_correct = [outcome.bias_correct for _, outcome in samples]
        directional_samples = [
            (record, outcome)
            for record, outcome in samples
            if record.prediction["direction"] != "neutral"
        ]
        directional_bias_samples = [
            (record, outcome)
            for record, outcome in samples
            if record.prediction["bias"] != "neutral"
        ]
        confidence_pairs = [
            (float(record.prediction["confidence"]), float(outcome.direction_correct))
            for record, outcome in samples
        ]
        summaries[str(horizon)] = {
            "sample_count": len(samples),
            "direction_accuracy": _rounded(mean(direction_correct), 4),
            "bias_accuracy": _rounded(mean(bias_correct), 4),
            "directional_coverage": _rounded(len(directional_samples) / len(samples), 4),
            "bias_directional_coverage": _rounded(len(directional_bias_samples) / len(samples), 4),
            "directional_accuracy": _accuracy(directional_samples, "direction_correct"),
            "bias_directional_accuracy": _accuracy(directional_bias_samples, "bias_correct"),
            "average_return_pct": _rounded(mean(outcome.return_pct for _, outcome in samples), 6),
            "confidence_brier_score": _rounded(
                mean((confidence - correct) ** 2 for confidence, correct in confidence_pairs),
                6,
            ),
            "confidence_calibration": _calibration_bins(confidence_pairs),
            "by_state": _group_accuracy(samples, "state"),
            "by_direction": _group_accuracy(samples, "direction"),
        }

    return {
        "record_count": len(records),
        "fully_scored_record_count": sum(
            all(horizon in record.outcomes for horizon in horizons)
            for record in records
        ),
        "horizons": summaries,
    }


def _snapshot_prediction(snapshot: MarketSnapshot) -> Dict[str, Any]:
    regime = snapshot.regime
    if regime is None:
        raise ValueError("Core pipeline returned a snapshot without a canonical regime")
    return {
        "direction": _normalize_direction(regime.direction),
        "bias": _normalize_direction(regime.bias),
        "state": regime.state,
        "phase": regime.phase,
        "confidence": _rounded(regime.confidence, 6),
        "direction_source": regime.direction_source,
        "source_timeframe": regime.source_timeframe,
        "swing_degree": regime.swing_degree,
        "fallback_used": regime.fallback_used,
        "reasons": list(regime.reasons),
        "confidence_factors": {
            key: _rounded(value, 6)
            for key, value in regime.confidence_factors.items()
        },
    }


def _snapshot_structure(snapshot: MarketSnapshot) -> Dict[str, Any]:
    direction_analysis = snapshot.direction_analysis
    structure_events = [*snapshot.structure_breaks, *snapshot.character_changes]
    latest_event = max(
        structure_events,
        key=lambda event: (event.break_timestamp, event.break_index),
        default=None,
    )
    active_ranges = [price_range for price_range in snapshot.ranges if price_range.active]
    active_range = max(active_ranges, key=lambda value: value.start_index, default=None)

    return {
        "swing_count": len(snapshot.swings),
        "external_swing_count": len(snapshot.external_swings),
        "internal_swing_count": len(snapshot.internal_swings),
        "structure_break_count": len(snapshot.structure_breaks),
        "character_change_count": len(snapshot.character_changes),
        "active_protected_level_count": len(snapshot.active_protected_levels),
        "active_range_count": len(active_ranges),
        "direction_quality": direction_analysis.quality if direction_analysis else "insufficient",
        "direction_pattern": (
            direction_analysis.to_dict()["pattern_swings"]
            if direction_analysis
            else []
        ),
        "latest_event": _structure_event(latest_event),
        "active_range": (
            {
                "high": _rounded(active_range.high, 8),
                "low": _rounded(active_range.low, 8),
                "start_index": active_range.start_index,
                "start_timestamp": active_range.start_timestamp,
                "duration_candles": active_range.duration_candles,
                "strength": _rounded(active_range.strength, 6),
            }
            if active_range
            else None
        ),
    }


def _structure_event(event: Any) -> Optional[dict]:
    if event is None:
        return None
    return {
        "type": getattr(event, "type", event.event_type),
        "direction": event.direction,
        "break_index": event.break_index,
        "break_timestamp": event.break_timestamp,
        "level": _rounded(event.level, 8),
        "break_price": _rounded(event.break_price, 8),
        "strength": _rounded(event.strength, 6),
        "confirmed": getattr(event, "confirmed", None),
        "invalidated": getattr(event, "invalidated", None),
    }


def _normalize_and_validate_candles(candles: Sequence[Candle]) -> List[Candle]:
    if not candles:
        raise ValueError("Replay requires candle data")
    normalized: List[Candle] = []
    previous_timestamp: Optional[int] = None
    for index, candle in enumerate(candles):
        values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError(f"Candle {index} contains a non-finite OHLCV value")
        if candle.high < max(candle.open, candle.close) or candle.low > min(candle.open, candle.close):
            raise ValueError(f"Candle {index} has inconsistent OHLC bounds")
        if candle.high < candle.low:
            raise ValueError(f"Candle {index} has high below low")
        timestamp = int(candle.timestamp)
        if previous_timestamp is not None and timestamp <= previous_timestamp:
            raise ValueError("Candle timestamps must be strictly increasing")
        previous_timestamp = timestamp
        normalized.append(Candle(
            timestamp=timestamp,
            open=float(candle.open),
            high=float(candle.high),
            low=float(candle.low),
            close=float(candle.close),
            volume=float(candle.volume),
            index=index,
        ))
    return normalized


def _fingerprint(candles: Sequence[Candle]) -> str:
    payload = [
        [
            candle.timestamp,
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
        ]
        for candle in candles
    ]
    encoded = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def _normalize_direction(value: str) -> str:
    normalized = str(value).lower()
    aliases = {"up": "bullish", "down": "bearish"}
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in _DIRECTIONS else "neutral"


def _accuracy(samples: Sequence[Tuple[ReplayRecord, ForwardOutcome]], field_name: str) -> Optional[float]:
    if not samples:
        return None
    return _rounded(mean(getattr(outcome, field_name) for _, outcome in samples), 4)


def _group_accuracy(
    samples: Sequence[Tuple[ReplayRecord, ForwardOutcome]],
    prediction_field: str,
) -> Dict[str, dict]:
    groups: Dict[str, list] = {}
    for record, outcome in samples:
        key = str(record.prediction[prediction_field])
        groups.setdefault(key, []).append((record, outcome))
    return {
        key: {
            "sample_count": len(values),
            "direction_accuracy": _accuracy(values, "direction_correct"),
            "bias_accuracy": _accuracy(values, "bias_correct"),
            "average_return_pct": _rounded(mean(value.return_pct for _, value in values), 6),
        }
        for key, values in sorted(groups.items())
    }


def _calibration_bins(pairs: Sequence[Tuple[float, float]]) -> List[dict]:
    bins = []
    for bin_index in range(5):
        lower = bin_index / 5
        upper = (bin_index + 1) / 5
        values = [
            (confidence, correct)
            for confidence, correct in pairs
            if confidence >= lower and (confidence < upper or bin_index == 4)
        ]
        if not values:
            continue
        average_confidence = mean(confidence for confidence, _ in values)
        accuracy = mean(correct for _, correct in values)
        bins.append({
            "lower": lower,
            "upper": upper,
            "sample_count": len(values),
            "average_confidence": _rounded(average_confidence, 4),
            "accuracy": _rounded(accuracy, 4),
            "calibration_gap": _rounded(abs(average_confidence - accuracy), 4),
        })
    return bins


def _empty_horizon_summary() -> dict:
    return {
        "sample_count": 0,
        "direction_accuracy": None,
        "bias_accuracy": None,
        "directional_coverage": None,
        "bias_directional_coverage": None,
        "directional_accuracy": None,
        "bias_directional_accuracy": None,
        "average_return_pct": None,
        "confidence_brier_score": None,
        "confidence_calibration": [],
        "by_state": {},
        "by_direction": {},
    }


def _rounded(value: Optional[float], digits: int) -> Optional[float]:
    return round(float(value), digits) if value is not None else None
