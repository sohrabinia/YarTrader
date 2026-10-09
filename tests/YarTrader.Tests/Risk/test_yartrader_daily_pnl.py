import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.Risk.Services.daily_loss_kill_switch import (
    DailyLossKillSwitch,
    calculate_yartrader_daily_pnl,
)


class TestYarTraderOnlyDailyPnl(unittest.TestCase):
    def test_manual_trades_and_cash_operations_are_excluded(self):
        now = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
        bot_open_time = int((now - timedelta(minutes=50)).timestamp())
        bot_close_time = int((now - timedelta(minutes=10)).timestamp())
        manual_time = int((now - timedelta(minutes=5)).timestamp())

        bot_open = {
            "time": bot_open_time, "type": 0, "entry": 0, "position_id": 101,
            "magic": 143056, "comment": "YarTraderAutoDE", "profit": 0,
            "commission": -0.25, "swap": 0, "fee": 0,
        }
        bot_close = {
            "time": bot_close_time, "type": 1, "entry": 1, "position_id": 101,
            "magic": 0, "comment": "", "profit": -4.0,
            "commission": -0.25, "swap": -0.1, "fee": 0,
        }
        manual_trade = {
            "time": manual_time, "type": 1, "entry": 1, "position_id": 202,
            "magic": 0, "comment": "manual", "profit": -500.0,
            "commission": -1.0, "swap": 0, "fee": 0,
        }
        deposit = {
            "time": manual_time, "type": 2, "entry": 0, "position_id": 0,
            "magic": 0, "comment": "deposit", "profit": 5000.0,
            "commission": 0, "swap": 0, "fee": 0,
        }

        adapter = MagicMock()
        adapter._initialized = True
        adapter._mt5.history_deals_get.return_value = [bot_open, bot_close, manual_trade, deposit]
        adapter._mt5.last_error.return_value = (1, "Success")
        adapter.get_positions.return_value = [
            {"ticket": 303, "magic": 143056, "comment": "YarTraderAutoDE", "profit": -2.0, "swap": -0.1},
            {"ticket": 404, "magic": 0, "comment": "manual", "profit": -99.0, "swap": 0},
        ]

        with tempfile.TemporaryDirectory() as temp:
            guard = DailyLossKillSwitch(persistence_path=temp + "\\kill.json")
            previous = DailyLossKillSwitch._instance
            DailyLossKillSwitch._instance = guard
            try:
                result = calculate_yartrader_daily_pnl(adapter, now_utc=now)
            finally:
                DailyLossKillSwitch._instance = previous

        self.assertAlmostEqual(result["realized_pnl"], -4.6, places=2)
        self.assertAlmostEqual(result["floating_pnl"], -2.1, places=2)
        self.assertAlmostEqual(result["total_pnl"], -6.7, places=2)
        self.assertEqual(result["owned_open_positions"], 1)

    def test_daily_drawdown_uses_current_wallet_equity_not_old_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            guard = DailyLossKillSwitch(persistence_path=temp + "\\kill.json")
            now = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
            guard.set_session_baseline(10000.0, "2026-10-09")
            allowed, reason, meta = guard.evaluate_daily_loss(
                1000.0, now_utc=now, bot_daily_pnl=-10.0
            )
            self.assertTrue(allowed)
            self.assertIsNone(reason)
            self.assertEqual(meta["baseline_equity"], 1000.0)
            self.assertEqual(meta["loss_pct"], 1.0)

            allowed, reason, meta = guard.evaluate_daily_loss(
                1000.0, now_utc=now, bot_daily_pnl=-80.0
            )
            self.assertFalse(allowed)
            self.assertEqual(reason, "DAILY_LOSS_LIMIT_REACHED")
            self.assertEqual(meta["loss_pct"], 8.0)


if __name__ == "__main__":
    unittest.main()
