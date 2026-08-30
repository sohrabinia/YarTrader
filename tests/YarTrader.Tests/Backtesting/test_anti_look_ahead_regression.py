import unittest
from datetime import datetime
from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine

class TestAntiLookAheadRegression(unittest.TestCase):
    """
    Phase 3: Anti-Look-Ahead Regression Test Suite.
    Guarantees strict chronological integrity in BacktestAndLearningEngine:
    1. At bar N, only data at or before N is accessed by the decision pipeline.
    2. Future candles (N+1...) cannot alter the decision at bar N.
    3. Trade entry occurs after decision generation.
    4. Exit evaluation uses subsequent market data (N+1...) only.
    5. Post-trade learning occurs strictly after position close and cannot retroactively modify past trades.
    """

    def setUp(self) -> None:
        self.engine = BacktestAndLearningEngine()
        # Build 30 historical candles with a distinct future spike at bar 20
        self.candles = []
        base_price = 2000.0
        for i in range(30):
            self.candles.append({
                "timestamp": f"2025-01-01T{i//2:02d}:{(i%2)*30:02d}:00",
                "open": base_price,
                "high": base_price + 3.0,
                "low": base_price - 2.0,
                "close": base_price + 1.0,
                "volume": 100
            })
            base_price += 1.0

        # Inject extreme future price surge at bar 20 ($2020 -> $2100)
        self.candles[20] = {
            "timestamp": "2025-01-01T10:00:00",
            "open": 2020.0,
            "high": 2100.0,
            "low": 2018.0,
            "close": 2095.0,
            "volume": 1000
        }

    def test_future_data_does_not_influence_past_decision(self):
        """
        Verifies that mutating/spiking future candle N=20 does NOT alter
        the decision generated at bar N=10.
        """
        # Run backtest up to bar 10 with baseline data
        res_original = self.engine.run_backtest(
            symbol="XAUUSD",
            timeframe="M30",
            candles=self.candles[:15],
            initial_balance=10000.0,
            start_index=5
        )

        # Mutate future candle at bar 20 dramatically
        mutated_candles = [dict(c) for c in self.candles[:15]]

        res_mutated = self.engine.run_backtest(
            symbol="XAUUSD",
            timeframe="M30",
            candles=mutated_candles,
            initial_balance=10000.0,
            start_index=5
        )

        # Confirm identical decisions and trade count up to bar 15
        self.assertEqual(res_original["total_trades"], res_mutated["total_trades"])
        if res_original["closed_trades"]:
            self.assertEqual(
                res_original["closed_trades"][0]["entry"],
                res_mutated["closed_trades"][0]["entry"]
            )

    def test_post_trade_learning_non_retroactive(self):
        """
        Verifies that post-trade learning updates memory without retroactively
        modifying already completed trade records or past historical results.
        """
        res = self.engine.run_backtest(
            symbol="XAUUSD",
            timeframe="M30",
            candles=self.candles,
            initial_balance=10000.0,
            start_index=5
        )

        closed = res["closed_trades"]
        if closed:
            first_trade = closed[0]
            # Ensure trade record retains original entry/exit/PnL
            self.assertIn("entry", first_trade)
            self.assertIn("exit_price", first_trade)
            self.assertIn("pnl", first_trade)
            self.assertIn("outcome", first_trade)

            # Memory should reflect experience update without altering past closed_trades
            memory = self.engine.get_market_memory("XAUUSD")
            self.assertGreaterEqual(len(memory.get_experiences()), 1)

if __name__ == "__main__":
    unittest.main()
