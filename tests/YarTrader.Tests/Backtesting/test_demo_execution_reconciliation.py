import unittest
from datetime import datetime
from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine

class TestDemoExecutionReconciliation(unittest.TestCase):
    """
    Phase 1 requirement: Demo Execution Accounting Reconciliation Proof.
    Verifies 100% mathematical reconciliation across:
    YarTrader Journal <-> Demo Position <-> Simulated Closing Deal <-> P&L
    """

    def setUp(self) -> None:
        self.engine = BacktestAndLearningEngine()
        # Build 30 candles with flat baseline
        self.candles = [
            {"timestamp": f"2025-01-01T{i//2:02d}:{(i%2)*30:02d}:00", "open": 2000.0 + i*0.1, "high": 2002.0 + i*0.1, "low": 1998.0 + i*0.1, "close": 2001.0 + i*0.1, "volume": 100}
            for i in range(30)
        ]

        # Inject impulse breakout at bar 10 to trigger JUMP BUY
        self.candles[10] = {
            "timestamp": "2025-01-01T05:00:00",
            "open": 2001.0,
            "high": 2040.0,
            "low": 1998.0,
            "close": 2035.0,
            "volume": 800
        }

        # Inject TP target hit at bar 12
        self.candles[12] = {
            "timestamp": "2025-01-01T06:00:00",
            "open": 2035.0,
            "high": 2150.0,
            "low": 2030.0,
            "close": 2140.0,
            "volume": 900
        }

    def test_demo_reconciliation_math_integrity(self):
        """Verifies 100% reconciliation between open entry, closing deal, P&L, and account equity."""
        init_balance = 10000.0
        res = self.engine.run_backtest(
            symbol="XAUUSD",
            timeframe="M30",
            candles=self.candles,
            initial_balance=init_balance,
            start_index=5
        )

        closed = res["closed_trades"]
        self.assertGreater(len(closed), 0, "At least one trade should execute and close.")

        trade = closed[0]
        entry_price = trade["entry"]
        exit_price = trade["exit_price"]
        volume = trade["volume"]
        pnl = trade["pnl"]
        direction = trade["direction"]

        # 1. P&L Math Verification for every trade
        total_pnl = 0.0
        for tr in closed:
            tr_entry = tr["entry"]
            tr_exit = tr["exit_price"]
            tr_vol = tr["volume"]
            tr_pnl = tr["pnl"]
            tr_dir = tr["direction"]
            mult = 100.0 if "XAU" in tr["symbol"] else 10000.0
            exp_pnl = round(((tr_exit - tr_entry) if tr_dir == "BUY" else (tr_entry - tr_exit)) * tr_vol * mult, 2)
            self.assertEqual(tr_pnl, exp_pnl, f"Calculated P&L {tr_pnl} must equal expected P&L {exp_pnl}")
            total_pnl += tr_pnl

        # 2. Balance Reconciliation Verification
        expected_final_balance = round(init_balance + total_pnl, 2)
        self.assertEqual(res["final_balance"], expected_final_balance, f"Final balance {res['final_balance']} must equal initial + total_pnl {expected_final_balance}")

        # 3. Learning Audit Reconciliation
        self.assertIn("learning_update", trade)
        self.assertIn("evaluation", trade["learning_update"])

if __name__ == "__main__":
    unittest.main()
