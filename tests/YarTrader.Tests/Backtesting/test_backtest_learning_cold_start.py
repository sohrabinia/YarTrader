import tempfile
import unittest
from datetime import datetime, timedelta

from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine


class _FakeBrain:
    def __init__(self):
        self.observation_brain = self
        self.simulation_brain = __import__(
            "src.Research.Brain.simulation", fromlist=["SimulationBrain"]
        ).SimulationBrain("XAUUSD", "M15")
        self.calls = 0

    def configure_historical_performance(self, *_args):
        return None

    def process_live_candle(self, *_args, **_kwargs):
        self.calls += 1
        action = "BUY" if self.calls == 1 else "WAIT"
        return type(
            "Report",
            (),
            {
                "to_dict": lambda _self: {
                    "active_hypotheses": [{
                        "hypothesis_id": "hyp-test",
                        "suggested_virtual_action": action,
                        "hypothesis_confidence": 60.0 if action == "BUY" else 0.0,
                        "trade_parameters": {},
                        "sequence_signature": [1.0, 2.0],
                        "matched_pattern_ids": [],
                        "context": {},
                    }]
                }
            },
        )()


class TestBacktestLearningColdStart(unittest.TestCase):
    def test_brain_decision_can_enter_simulation_before_three_learned_outcomes(self):
        with tempfile.TemporaryDirectory() as storage:
            engine = BacktestAndLearningEngine(storage_dir=storage)
            fake = _FakeBrain()
            engine.get_live_brain = lambda _symbol, _timeframe: fake

            candles = []
            base = datetime(2026, 1, 1)
            for i in range(6):
                price = 2000.0 + (20.0 if i >= 3 else 0.0)
                # Entry is made after the decision bar closes, so the outcome must
                # come from a subsequent bar rather than the entry bar's own high.
                post_entry_high = 45.0 if i == 3 else 1.0
                candles.append({
                    "timestamp": (base + timedelta(minutes=15 * i)).isoformat(),
                    "open": price,
                    "high": price + post_entry_high,
                    "low": price - 1.0,
                    "close": price,
                    "volume": 100.0,
                })

            result = engine.run_backtest(
                "XAUUSD",
                "M15",
                candles,
                initial_balance=10000.0,
                start_index=2,
            )

            self.assertGreaterEqual(result["total_trades"], 1)
            self.assertGreaterEqual(result["learning_updates_count"], 1)
            self.assertEqual(result["rejection_counts"], {})

    def test_rejection_reasons_are_reported(self):
        with tempfile.TemporaryDirectory() as storage:
            engine = BacktestAndLearningEngine(storage_dir=storage)
            fake = _FakeBrain()

            def wait_brain(*_args, **_kwargs):
                fake.calls += 1
                return type(
                    "Report",
                    (),
                    {
                        "to_dict": lambda _self: {
                            "active_hypotheses": [{
                                "hypothesis_id": "hyp-test",
                                "suggested_virtual_action": "WAIT",
                                "hypothesis_confidence": 0.0,
                                "trade_parameters": {},
                                "sequence_signature": [],
                                "matched_pattern_ids": [],
                                "context": {},
                            }]
                        }
                    },
                )()

            fake.process_live_candle = wait_brain
            engine.get_live_brain = lambda _symbol, _timeframe: fake
            candles = [{
                "timestamp": (datetime(2026, 1, 1) + timedelta(minutes=15 * i)).isoformat(),
                "open": 2000.0,
                "high": 2001.0,
                "low": 1999.0,
                "close": 2000.0,
                "volume": 100.0,
            } for i in range(4)]

            result = engine.run_backtest("XAUUSD", "M15", candles, start_index=1)
            self.assertGreater(result["rejection_counts"].get("NO_ACTION", 0), 0)


if __name__ == "__main__":
    unittest.main()
