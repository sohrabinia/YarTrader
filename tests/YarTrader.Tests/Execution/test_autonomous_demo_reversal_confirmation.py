import unittest
from unittest.mock import MagicMock, patch

from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader


class TestAutonomousDemoReversalConfirmation(unittest.TestCase):
    def setUp(self):
        # These cases validate legacy reversal behavior with multi-position mode disabled.
        env_patch = patch.dict("os.environ", {"YARTRADER_DEMO_ALLOW_MULTIPLE_POSITIONS": "false"})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.adapter = MagicMock()
        self.trader = AutonomousDemoTrader(adapter=self.adapter)

    def test_opposite_entry_may_be_reassessed_only_after_broker_confirms_flat(self):
        self.adapter.get_positions.return_value = []
        result = self.trader._confirm_position_flat("XAUUSD", 12345)
        self.assertTrue(result["confirmed"])

    def test_existing_position_blocks_opposite_entry_even_after_successful_close_response(self):
        self.adapter.get_positions.return_value = [{"ticket": 12345, "symbol": "XAUUSD"}]
        result = self.trader._confirm_position_flat("XAUUSD", 12345)
        self.assertFalse(result["confirmed"])
        self.assertIn("still open", result["reason"])

    def test_unknown_broker_state_blocks_opposite_entry(self):
        self.adapter.get_positions.return_value = None
        result = self.trader._confirm_position_flat("XAUUSD", 12345)
        self.assertFalse(result["confirmed"])
        self.assertIn("unknown", result["reason"])

    def test_broker_query_exception_blocks_opposite_entry(self):
        self.adapter.get_positions.side_effect = RuntimeError("connection lost")
        result = self.trader._confirm_position_flat("XAUUSD", 12345)
        self.assertFalse(result["confirmed"])
        self.assertIn("re-query failed", result["reason"])

    def _configure_cycle(self, positions, plan):
        # These tests exercise reversal/position reconciliation, not the market calendar.
        market_gate_patch = patch(
            "src.Execution.Services.autonomous_demo_trader.MarketSessionEngine.live_activity_status",
            return_value={"allowed": True, "state": "OPEN", "reason": "TEST_MARKET_OPEN"},
        )
        market_gate_patch.start()
        self.addCleanup(market_gate_patch.stop)
        self.adapter.verify_safety_and_account.return_value = None
        self.adapter.get_account_info.return_value = {"trade_mode": 0, "balance": 10000, "equity": 10000}
        self.adapter.get_terminal_info.return_value = {
            "connected": True, "trade_allowed": True, "tradeapi_disabled": False
        }
        self.adapter.get_symbol_info.return_value = {"digits": 2, "volume_min": 0.01, "volume_max": 10, "volume_step": 0.01}
        self.adapter.get_symbol_tick.return_value = {"time": 1000, "bid": 2000.0, "ask": 2000.2}
        self.adapter.get_positions.return_value = positions
        self.adapter._mt5.POSITION_TYPE_BUY = 0
        self.adapter._mt5.POSITION_TYPE_SELL = 1
        bars = [{"timestamp": 1000, "open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.5}]
        self.trader._fetch_candles = MagicMock(return_value=bars)
        self.trader._evaluate_daily_risk = MagicMock(return_value={"allowed": True, "meta": {}})
        self.trader._evaluate_hierarchical_base_plan = MagicMock(return_value=plan)
        self.trader._log_event = MagicMock()

    def test_confirmed_opposite_setup_closes_open_position_without_waiting_for_reverse_fill(self):
        from unittest.mock import patch
        old_buy = {"ticket": 101, "type": 0, "volume": 0.01, "magic": 100001,
                   "comment": "YarBase", "time": 100}
        plan = {"status": "ORDER_PROPOSAL", "structure": {},
                "order_plan": {"status": "PROPOSED", "direction": "SELL"}}
        self._configure_cycle([old_buy], plan)
        self.adapter.get_active_orders.return_value = []
        self.adapter.get_positions.side_effect = [[old_buy], []]
        close_response = MagicMock(Status="Executed", Retcode=10009, Comment="closed")
        self.adapter.send_order_to_broker.return_value = close_response
        with patch("src.Execution.Services.autonomous_demo_trader._read_flag", return_value=True):
            result = self.trader.run_once("XAUUSD")
        self.assertEqual(result["status"], "POSITION_CLOSED_BASE_EXIT")
        request = self.adapter.send_order_to_broker.call_args.args[0]
        self.assertEqual(request.OrderType, "CLOSE")
        self.assertEqual(request.PositionTicket, 101)

    def test_legacy_position_tp_is_preserved_as_broker_side_protection(self):
        from unittest.mock import patch
        old_buy = {"ticket": 101, "type": 0, "volume": 0.01, "magic": 100001,
                   "comment": "YarBase", "time": 100, "sl": 1990.0, "tp": 2050.0}
        plan = {"status": "WAIT", "structure": {},
                "order_plan": {"status": "WAIT", "direction": "WAIT"}}
        self._configure_cycle([old_buy], plan)
        self.adapter.get_positions.side_effect = [[old_buy], [{**old_buy, "tp": 0.0}]]
        self.adapter.clear_position_take_profit.return_value = MagicMock(Status="Modified", Retcode=10009)
        self.trader._reconcile_base_pending_order = MagicMock(return_value={"status": "WAIT"})
        with patch("src.Execution.Services.autonomous_demo_trader._read_flag", return_value=True):
            result = self.trader.run_once("XAUUSD")
        self.adapter.clear_position_take_profit.assert_not_called()
        self.adapter.update_position_take_profit.assert_not_called()
        self.adapter.send_order_to_broker.assert_not_called()
        self.assertEqual(result["status"], "POSITION_HELD_BASE_STRUCTURE")

    def test_old_position_closes_only_after_opposite_position_is_broker_visible(self):
        from unittest.mock import patch
        old_buy = {"ticket": 101, "type": 0, "volume": 0.01, "magic": 100001,
                   "comment": "YarBase", "time": 100}
        new_sell = {"ticket": 202, "type": 1, "volume": 0.01, "magic": 100001,
                    "comment": "YarBase", "time": 200}
        plan = {"status": "ORDER_PROPOSAL", "structure": {},
                "order_plan": {"status": "PROPOSED", "direction": "SELL"}}
        self._configure_cycle([old_buy, new_sell], plan)
        self.adapter.get_positions.side_effect = [[old_buy, new_sell], [new_sell]]
        self.adapter.get_active_orders.return_value = []
        close_response = MagicMock()
        close_response.Status = "Executed"
        close_response.Retcode = 10009
        close_response.Comment = "closed"
        self.adapter.send_order_to_broker.return_value = close_response
        with patch("src.Execution.Services.autonomous_demo_trader._read_flag", return_value=True):
            result = self.trader.run_once("XAUUSD")
        self.assertEqual(result["status"], "POSITION_CLOSED_BASE_EXIT")
        request = self.adapter.send_order_to_broker.call_args.args[0]
        self.assertEqual(request.OrderType, "CLOSE")
        self.assertEqual(request.PositionTicket, 101)


if __name__ == "__main__":
    unittest.main()
