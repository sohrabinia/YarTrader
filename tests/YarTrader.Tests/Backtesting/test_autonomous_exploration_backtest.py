import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine
from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator


class TestAutonomousExplorationBacktest(unittest.TestCase):
    def test_no_rr_or_daily_drawdown_gate_and_exit_on_opposite_signal(self):
        with tempfile.TemporaryDirectory() as storage:
            engine = BacktestAndLearningEngine(storage_dir=storage, memory_autosave_every=500, learning_interval_bars=1)
            candles = []
            start = datetime(2025, 1, 1, tzinfo=timezone.utc)
            for i in range(60):
                close = 100.0 - max(0, i - 50) * 0.1
                opened = close + (0.05 if i >= 50 else 0.0)
                candles.append({
                    "timestamp": (start + timedelta(minutes=i)).isoformat(),
                    "open": opened, "high": max(opened, close) + 0.1,
                    "low": min(opened, close) - 0.1, "close": close, "volume": 100,
                })

            def fake_evaluate(_self, symbol, primary_timeframe, candles, **kwargs):
                direction = "BUY" if len(candles) <= 51 else "SELL"
                entry = float(candles[-1]["close"])
                return {
                    "symbol": symbol, "primary_timeframe": primary_timeframe,
                    "exploration_mode": True,
                    "best_candidate": {
                        "strategy_id": f"TEST-{len(candles)}", "strategy_name": "BASE_HIERARCHY",
                        "symbol": symbol, "timeframe": primary_timeframe, "direction": direction,
                        "entry": entry, "stop_loss": entry - 1.0 if direction == "BUY" else entry + 1.0,
                        "take_profit": None, "risk_reward": 0.0, "confidence": 100.0,
                        "market_context": {"strategy": "IN_BASE_ROTATION", "base_structure": {}},
                        "reasoning": ["test-only autonomous exploration candidate"],
                    },
                }

            with patch.object(StrategyOrchestrator, "evaluate_all_strategies", autospec=True, side_effect=fake_evaluate):
                result = engine.run_backtest(
                    "EURUSD", "M1", candles, initial_balance=10000.0, start_index=50,
                    learn_from_outcomes=False, max_daily_drawdown_pct=0.01,
                    autonomous_exploration_mode=True,
                )

        self.assertGreaterEqual(result["daily_halted_sessions_count"], 1)
        self.assertEqual(len(result["closed_trades"]), 1)
        self.assertEqual(result["closed_trades"][0]["exit_reason"], "OPPOSITE_BASE_SIGNAL")
        self.assertIsNone(result["closed_trades"][0]["take_profit"])
        self.assertEqual(result["state"]["open_position"]["direction"], "SELL")
        self.assertIsNone(result["state"]["open_position"]["take_profit"])
        self.assertEqual(result["state"]["open_position"]["volume"], 0.01)


if __name__ == "__main__":
    unittest.main()
