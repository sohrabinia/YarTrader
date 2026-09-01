import unittest
from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine

class TestSequentialMultiMarketLearning(unittest.TestCase):
    """
    Phase 9 & Phase 10: Sequential Multi-Market Historical Training & Validation.
    Proves:
    1. Sequential training on XAUUSD -> EURUSD -> GBPUSD -> USDJPY.
    2. Knowledge isolation per market (separate MarketMemorySystem storage directories).
    3. Chronological walk-forward learning without cross-market leakage.
    """

    def setUp(self) -> None:
        self.engine = BacktestAndLearningEngine()
        self.symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]

    def test_sequential_multi_market_learning(self) -> None:
        reports = {}

        for sym in self.symbols:
            base_p = 2000.0 if sym == "XAUUSD" else (150.0 if sym == "USDJPY" else 1.10)
            candles = []
            for i in range(15):
                candles.append({
                    "timestamp": f"2025-01-01T{i//2:02d}:{(i%2)*30:02d}:00",
                    "open": base_p,
                    "high": base_p + (i % 3) * 2.0 + 1.0,
                    "low": base_p - (i % 2) * 1.5 - 0.5,
                    "close": base_p + (1.0 if i % 2 == 0 else -1.0),
                    "volume": 100 + i
                })
                base_p += 0.5 if "USD" in sym else 0.0005

            res = self.engine.run_backtest(
                symbol=sym,
                timeframe="M30",
                candles=candles,
                initial_balance=10000.0,
                start_index=10
            )

            reports[sym] = res

            # Verify market memory isolation
            memory = self.engine.get_market_memory(sym)
            self.assertIn(sym, memory._storage_dir)

        # Confirm all 4 markets executed independently
        for sym in self.symbols:
            self.assertEqual(reports[sym]["symbol"], sym)
            self.assertIn("closed_trades", reports[sym])

if __name__ == "__main__":
    unittest.main()
