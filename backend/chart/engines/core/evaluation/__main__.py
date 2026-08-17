"""Command-line entry point for reproducible Core Engine replays."""

from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Optional

from backend.chart.data.chart_data_fetcher import async_fetch_and_convert
from backend.chart.engines.core.evaluation import ReplayConfig, run_replay
from backend.chart.engines.core.schemas.candle import Candle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replay the real Core Engine candle by candle and save a "
            "no-lookahead JSON evaluation report."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Optional OHLCV CSV. If omitted, candles are fetched from the configured provider.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON report")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--source", default=None, help="Market-data provider when --input is omitted")
    parser.add_argument("--periods", type=int, default=500, help="Candles to fetch")
    parser.add_argument("--warmup", type=int, default=80, help="Candles before the first prediction")
    parser.add_argument("--step", type=int, default=1, help="Candles between prediction checkpoints")
    parser.add_argument(
        "--horizons",
        type=_parse_horizons,
        default=(1, 3, 6, 12),
        help="Comma-separated forward horizons in candles (default: 1,3,6,12)",
    )
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument(
        "--neutral-threshold-atr",
        type=float,
        default=0.25,
        help="Close moves within this many origin ATRs are labelled neutral",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.periods < 1:
            raise ValueError("periods must be positive")
        candles = (
            load_candles_from_csv(args.input)
            if args.input
            else asyncio.run(async_fetch_and_convert(
                symbol=args.symbol,
                timeframe=args.timeframe,
                lookback=args.periods,
                source=args.source,
            ))
        )
        config = ReplayConfig(
            warmup_candles=args.warmup,
            step=args.step,
            horizons=args.horizons,
            atr_period=args.atr_period,
            neutral_threshold_atr=args.neutral_threshold_atr,
        )
        report = run_replay(candles, args.symbol, args.timeframe, config)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report.to_dict(), indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"Replay failed: {exc}\n")

    scored = report.summary["fully_scored_record_count"]
    print(
        f"Saved {len(report.records)} predictions "
        f"({scored} fully scored) to {args.output.resolve()}"
    )
    return 0


def load_candles_from_csv(path: Path) -> list[Candle]:
    """Load timestamp/open/high/low/close/volume columns from a CSV file."""
    if not path.is_file():
        raise ValueError(f"CSV file does not exist: {path}")
    candles = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        required = {"timestamp", "open", "high", "low", "close"}
        missing = required - set(field_map)
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
        for index, row in enumerate(reader):
            try:
                candles.append(Candle(
                    timestamp=_parse_timestamp(row[field_map["timestamp"]]),
                    open=float(row[field_map["open"]]),
                    high=float(row[field_map["high"]]),
                    low=float(row[field_map["low"]]),
                    close=float(row[field_map["close"]]),
                    volume=(
                        float(row[field_map["volume"]])
                        if "volume" in field_map and row[field_map["volume"]]
                        else 0.0
                    ),
                    index=index,
                ))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid CSV value on data row {index + 2}: {exc}") from exc
    if not candles:
        raise ValueError("CSV contains no candle rows")
    return candles


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        horizons = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("horizons must be comma-separated integers") from exc
    if not horizons or any(horizon < 1 for horizon in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive integers")
    return horizons


def _parse_timestamp(value: str) -> int:
    text = str(value).strip()
    try:
        numeric = float(text)
    except ValueError:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    return int(numeric * 1000) if abs(numeric) < 1_000_000_000_000 else int(numeric)


if __name__ == "__main__":
    raise SystemExit(main())
