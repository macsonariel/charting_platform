import math
import unittest

from backend.api.core_api import _build_core_view_model
from backend.chart.data.chart_data_fetcher import _get_cache_key
from backend.chart.engines.core.detectors.direction_detector import detect_direction
from backend.chart.engines.core.narrative import ScenarioAnalyzer
from backend.chart.engines.core.pipeline import run_pipeline, select_direction_analysis
from backend.chart.engines.core.schemas.candle import Candle
from backend.chart.engines.core.schemas.events import RecentEvent
from backend.chart.engines.core.schemas.liquidity import LiquiditySweep
from backend.chart.engines.core.schemas.swing import SwingPoint


def synthetic_candles(count=160):
    candles = []
    for index in range(count):
        midpoint = 100 + index * 0.12 + 4 * math.sin(index / 4)
        candles.append(Candle(
            timestamp=index * 3_600_000,
            open=midpoint - 0.2,
            high=midpoint + 1,
            low=midpoint - 1,
            close=midpoint + 0.2,
            volume=1000,
            index=index,
        ))
    return candles


def ranging_candles(count=160):
    candles = []
    for index in range(count):
        midpoint = 100 + 2 * math.sin(index / 4)
        candles.append(Candle(
            timestamp=index * 3_600_000,
            open=midpoint - 0.1,
            high=midpoint + 0.5,
            low=midpoint - 0.5,
            close=midpoint + 0.1,
            volume=1000,
            index=index,
        ))
    return candles


class CoreEngineContractTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = run_pipeline(synthetic_candles(), 'TEST', '1h')

    def test_compatibility_interpretation_matches_regime(self):
        interpretation = self.snapshot.interpretation
        context = interpretation['full_state']['context']

        self.assertEqual(context['current_price'], self.snapshot.current_price)
        self.assertEqual(context['timestamp'], self.snapshot.timestamp)
        self.assertEqual(interpretation['bias'].lower(), self.snapshot.bias)
        self.assertNotEqual(interpretation['state'], 'NEUTRAL')

    def test_core_view_model_is_versioned_and_shared(self):
        mtf = {
            'status': 'ready',
            'timeframes': {},
            'alignment_percentage': 0,
            'aligned_count': 0,
            'total_analyzed': 0,
        }
        model = _build_core_view_model(self.snapshot, mtf)

        self.assertEqual(model['schema_version'], '1.0')
        self.assertEqual(model['engine'], 'core')
        self.assertEqual(model['source'], 'market_snapshot')
        self.assertEqual(model['status'], 'ready')
        self.assertIn('analysis', model)
        self.assertIn('recent_events', model)
        self.assertEqual(model['quick_overview']['bias'], model['structure']['bias'])
        self.assertEqual(model['quick_overview']['current_price'], model['current_price'])
        self.assertEqual(model['confidence']['score'], round(self.snapshot.regime.confidence * 100))
        self.assertEqual(
            model['direction_swings']['swings'],
            self.snapshot.direction_analysis.to_dict()['pattern_swings'],
        )

    def test_regime_is_the_only_published_interpretation(self):
        model = _build_core_view_model(self.snapshot)
        regime = self.snapshot.regime

        self.assertEqual(model['structure']['direction'], regime.direction)
        self.assertEqual(model['structure']['bias'], regime.bias)
        self.assertEqual(model['structure']['state'], regime.state)
        self.assertEqual(model['structure']['phase'], regime.phase)
        self.assertEqual(model['confidence']['source'], 'core_regime')
        self.assertEqual(self.snapshot.analysis.market_state.lower(), regime.state)
        self.assertEqual(self.snapshot.interpretation['state'].lower(), regime.state)

    def test_trending_structure_is_not_mislabeled_as_active_range(self):
        self.assertEqual(self.snapshot.regime.state, 'trending')
        self.assertFalse(any(price_range.active for price_range in self.snapshot.ranges))

    def test_narrative_projects_canonical_regime(self):
        result = ScenarioAnalyzer().analyze(self.snapshot)

        self.assertEqual(result.bias, self.snapshot.regime.bias)
        self.assertEqual(result.confidence, round(self.snapshot.regime.confidence * 100, 1))
        self.assertEqual(result.scenario.value, 'trending_up')

    def test_swing_confirmed_range_becomes_canonical_ranging_state(self):
        snapshot = run_pipeline(ranging_candles(), 'RANGE', '1h')

        self.assertEqual(snapshot.direction_analysis.direction, 'neutral')
        self.assertTrue(any(price_range.active for price_range in snapshot.ranges))
        self.assertEqual(snapshot.regime.state, 'ranging')
        self.assertEqual(snapshot.regime.phase, 'consolidation')

    def test_direction_falls_back_when_external_pattern_is_incomplete(self):
        swings = [
            SwingPoint('l1', 1, 1, 100, 'low', degree='internal'),
            SwingPoint('h1', 2, 2, 110, 'high', degree='internal'),
            SwingPoint('l2', 3, 3, 105, 'low', degree='external'),
            SwingPoint('h2', 4, 4, 115, 'high', degree='external'),
        ]
        result = select_direction_analysis(
            swings,
            [swing for swing in swings if swing.degree == 'external'],
            '1h',
            '4h',
        )

        self.assertEqual(result.direction, 'bullish')
        self.assertEqual(result.source, 'all_structural_swings')
        self.assertTrue(result.fallback_used)

    def test_sweep_event_direction_matches_liquidity_semantics(self):
        sell_side_sweep = LiquiditySweep('down', 'pool', 90, 'down', 2, 2000)
        buy_side_sweep = LiquiditySweep('up', 'pool', 110, 'up', 3, 3000)

        self.assertEqual(RecentEvent.from_sweep(sell_side_sweep).direction, 'bullish')
        self.assertEqual(RecentEvent.from_sweep(buy_side_sweep).direction, 'bearish')

    def test_moves_are_anchored_to_candle_timestamps(self):
        move = self.snapshot.moves[0]

        self.assertGreater(move.start_timestamp, 0)
        self.assertEqual(
            move.start_timestamp,
            synthetic_candles()[move.start_index].timestamp,
        )

    def test_incomplete_alternating_swings_are_neutral(self):
        swings = [
            SwingPoint('high', 1, 1, 110, 'high'),
            SwingPoint('low', 2, 2, 100, 'low'),
        ]

        result = detect_direction(swings)

        self.assertEqual(result.direction, 'neutral')
        self.assertFalse(result.is_trending)

    def test_market_data_cache_separates_providers(self):
        binance = _get_cache_key('BTCUSDT', '1h', 100, 'binance')
        yahoo = _get_cache_key('BTCUSDT', '1h', 100, 'yahoo')

        self.assertNotEqual(binance, yahoo)


if __name__ == '__main__':
    unittest.main()
