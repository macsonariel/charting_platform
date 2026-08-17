from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from backend.chart.engines.core.evaluation import (
    ReplayConfig,
    evaluate_forward_outcome,
    run_replay,
)
from backend.chart.engines.core.evaluation.__main__ import main as replay_main
from backend.chart.engines.core.schemas.candle import Candle
from tests.test_core_engine import synthetic_candles


def shifted_future(candles, after_index, amount):
    shifted = []
    for index, candle in enumerate(candles):
        offset = amount if index > after_index else 0.0
        shifted.append(Candle(
            timestamp=candle.timestamp,
            open=candle.open + offset,
            high=candle.high + offset,
            low=candle.low + offset,
            close=candle.close + offset,
            volume=candle.volume,
            index=index,
        ))
    return shifted


class CoreReplayTests(unittest.TestCase):
    def test_future_candles_cannot_change_a_frozen_prediction(self):
        candles = synthetic_candles(110)
        changed = shifted_future(candles, after_index=79, amount=40)
        config = ReplayConfig(warmup_candles=50, step=10, horizons=(10,))

        original_report = run_replay(candles, "TEST", "1h", config)
        changed_report = run_replay(changed, "TEST", "1h", config)
        original = next(record for record in original_report.records if record.origin_index == 79)
        replayed = next(record for record in changed_report.records if record.origin_index == 79)

        self.assertEqual(original.prediction, replayed.prediction)
        self.assertEqual(original.structure, replayed.structure)
        self.assertNotEqual(
            original.outcomes[10].target_close,
            replayed.outcomes[10].target_close,
        )
        self.assertTrue(all(
            swing["index"] <= original.latest_confirmable_swing_index
            for swing in original.structure["direction_pattern"]
        ))

    def test_forward_label_uses_origin_atr_threshold(self):
        candles = [
            Candle(0, 100, 101, 99, 100, index=0),
            Candle(1, 100, 102, 99.5, 101, index=1),
            Candle(2, 101, 104, 100.5, 103, index=2),
        ]

        outcome = evaluate_forward_outcome(
            candles=candles,
            origin_index=0,
            horizon=2,
            predicted_direction="bullish",
            predicted_bias="neutral",
            atr=2,
            neutral_threshold_atr=0.25,
        )

        self.assertEqual(outcome.observed_direction, "bullish")
        self.assertTrue(outcome.direction_correct)
        self.assertFalse(outcome.bias_correct)
        self.assertEqual(outcome.return_atr, 1.5)
        self.assertEqual(outcome.return_pct, 3.0)
        self.assertEqual(outcome.max_up_pct, 4.0)

    def test_report_is_reproducible_and_counts_only_available_outcomes(self):
        candles = synthetic_candles(100)
        config = ReplayConfig(warmup_candles=60, step=10, horizons=(1, 5))

        first = run_replay(candles, "TEST", "1h", config)
        second = run_replay(candles, "TEST", "1h", config)

        self.assertEqual(first.data_fingerprint, second.data_fingerprint)
        self.assertEqual(len(first.records), 5)
        self.assertEqual(first.summary["fully_scored_record_count"], 4)
        self.assertEqual(first.summary["horizons"]["1"]["sample_count"], 4)
        self.assertEqual(first.summary["horizons"]["5"]["sample_count"], 4)
        self.assertEqual(first.to_dict()["methodology"]["no_lookahead"], True)
        self.assertIn("direction_pattern", first.records[0].structure)

    def test_replay_rejects_non_chronological_data(self):
        candles = synthetic_candles(20)
        candles[10].timestamp = candles[9].timestamp

        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            run_replay(
                candles,
                "TEST",
                "1h",
                ReplayConfig(warmup_candles=10, horizons=(1,)),
            )

    def test_csv_cli_writes_a_complete_json_contract(self):
        candles = synthetic_candles(30)
        rows = ["timestamp,open,high,low,close,volume"]
        rows.extend(
            f"{c.timestamp},{c.open},{c.high},{c.low},{c.close},{c.volume}"
            for c in candles
        )
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "candles.csv"
            output_path = Path(directory) / "report.json"
            input_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                exit_code = replay_main([
                    "--input", str(input_path),
                    "--output", str(output_path),
                    "--symbol", "TEST",
                    "--timeframe", "1h",
                    "--warmup", "20",
                    "--step", "5",
                    "--horizons", "1,3",
                ])

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["schema_version"], "1.0")
            self.assertEqual(payload["dataset"]["candle_count"], 30)
            self.assertTrue(payload["records"])
            self.assertIn("confidence_calibration", payload["summary"]["horizons"]["1"])


if __name__ == "__main__":
    unittest.main()
