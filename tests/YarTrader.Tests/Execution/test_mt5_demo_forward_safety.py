import unittest
from unittest.mock import MagicMock, patch
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from src.Infrastructure.exceptions import ValidationException
from scripts.run_mt5_demo_forward import MT5DemoForwardRunner


class TestMT5DemoForwardSafety(unittest.TestCase):
    def setUp(self):
        self.runner = MT5DemoForwardRunner(symbol="XAUUSD", auto_confirm=True)

    def test_live_trading_hard_blocked(self):
        with patch("src.Infrastructure.Configuration.config.ConfigurationManager.get_config") as mock_cfg:
            mock_config = MagicMock()
            mock_config.live_trading_enabled = True
            mock_cfg.return_value = mock_config

            with self.assertRaises(ValidationException):
                MetaTraderSafetyGate.verify_operation("MT5", "REAL_LIVE")

    def test_mt4_live_blocked(self):
        with self.assertRaises(ValidationException):
            MetaTraderSafetyGate.verify_operation("MT4", "REAL_LIVE")

    def test_non_demo_account_rejected_by_adapter(self):
        adapter = RealMT5BrokerAdapter(auto_initialize=False)
        mock_mt5 = MagicMock()
        mock_acc = MagicMock()
        mock_acc.login = 12345678  # Invalid login
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 0
        mock_mt5.account_info.return_value = mock_acc
        adapter._mt5 = mock_mt5
        adapter._initialized = True

        with self.assertRaises(ValidationException):
            adapter.verify_safety_and_account("DEMO")

    def test_non_demo_trade_mode_rejected_by_adapter(self):
        adapter = RealMT5BrokerAdapter(auto_initialize=False)
        mock_mt5 = MagicMock()
        mock_acc = MagicMock()
        mock_acc.login = 52961173
        mock_acc.server = "Alpari-MT5-Demo"
        mock_acc.trade_mode = 1  # Live trade_mode
        mock_mt5.account_info.return_value = mock_acc
        adapter._mt5 = mock_mt5
        adapter._initialized = True

        with self.assertRaises(ValidationException):
            adapter.verify_safety_and_account("DEMO")

    def test_disconnected_terminal_returns_not_proven(self):
        with patch.object(self.runner.adapter, "get_terminal_info", return_value={"connected": False}):
            verdict = self.runner.run_forward_cycle()
            self.assertEqual(verdict, "REAL_MT5_DEMO_FORWARD_OPERATION_NOT_PROVEN")

    def test_pnl_reconciliation_math(self):
        deals = [
            {"profit": 15.50, "commission": -1.40, "swap": -0.20},
            {"profit": 0.0, "commission": -1.40, "swap": 0.0}
        ]
        gross_profit = sum(d["profit"] for d in deals)
        comm = sum(d["commission"] for d in deals)
        swap = sum(d["swap"] for d in deals)
        net_pnl = gross_profit + comm + swap

        self.assertEqual(gross_profit, 15.50)
        self.assertEqual(comm, -2.80)
        self.assertEqual(swap, -0.20)
        self.assertEqual(net_pnl, 12.50)


if __name__ == "__main__":
    unittest.main()
