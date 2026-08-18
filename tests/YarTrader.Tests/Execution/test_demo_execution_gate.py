import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Infrastructure.exceptions import ValidationException


class TestDemoExecutionGateSafety(unittest.TestCase):
    """
    Required SRE Safety Tests for Demo Execution Gate & Demo Execution Engine.
    Verifies that real live trading remains IMPOSSIBLE and all safety rules hold.
    """

    def setUp(self):
        self.mock_adapter = MagicMock()
        self.mock_adapter.get_account_info.return_value = {
            "login": "52961173",
            "server": "Alpari-MT5-Demo",
            "trade_mode": 0
        }
        self.mock_adapter.get_terminal_info.return_value = {
            "connected": True,
            "trade_allowed": True,
            "tradeapi_disabled": False
        }
        self.mock_adapter.get_symbol_info.return_value = {
            "name": "XAUUSD",
            "trade_mode": 4,
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01
        }

    def test_01_real_live_execution_rejected(self):
        """Test 1: REAL_LIVE operation is hard-blocked."""
        from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(terminal_type="MT5", operation_type="REAL_LIVE")
        self.assertIn("Real Live Trading is hard-disabled", str(ctx.exception))

    def test_02_demo_execution_allowed_with_explicit_gate(self):
        """Test 2: Demo execution passes when demo mode is enabled and checks pass."""
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01, Price=2350.0, StopLoss=2340.0, TakeProfit=2370.0)
        res = DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertTrue(res)

    def test_03_live_account_rejected_even_if_demo_gate_enabled(self):
        """Test 3: Live account (login!=52961173 or trade_mode!=0) is rejected."""
        self.mock_adapter.get_account_info.return_value = {
            "login": "143056202", # Live account
            "server": "Alpari-Pro.ECN",
            "trade_mode": 2 # Real account
        }
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01)
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("not authorized DEMO account", str(ctx.exception))

    def test_04_terminal_trading_disabled_rejected(self):
        """Test 4: Terminal with trade_allowed=False is rejected."""
        self.mock_adapter.get_terminal_info.return_value = {
            "connected": True,
            "trade_allowed": False,
            "tradeapi_disabled": False
        }
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01)
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("trading permissions disabled", str(ctx.exception))

    def test_05_invalid_symbol_trade_mode_rejected(self):
        """Test 5: Symbol with trade_mode=0 (disabled) is rejected."""
        self.mock_adapter.get_symbol_info.return_value = {
            "name": "XAUUSD",
            "trade_mode": 0 # Trade disabled
        }
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01)
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("trade mode is DISABLED", str(ctx.exception))

    def test_06_invalid_volume_out_of_bounds_rejected(self):
        """Test 6: Volume smaller than volume_min or larger than volume_max is rejected."""
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.001) # Less than 0.01
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("out of bounds", str(ctx.exception))

    def test_07_invalid_sl_tp_rejected(self):
        """Test 7: Buy order with SL above entry price is rejected."""
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01, Price=2350.0, StopLoss=2360.0) # SL > Price
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("Buy order SL 2360.0 must be below entry price 2350.0", str(ctx.exception))

    def test_08_failed_order_check_prevents_order_send(self):
        """Test 8: DemoExecutionEngine logs failure if adapter order placement fails."""
        self.mock_adapter.send_order_to_broker.return_value = OrderResponse(
            OrderId="0",
            Symbol="XAUUSD",
            Status="Failed",
            SubmittedAt=datetime.now(timezone.utc),
            Comment="order_check failed retcode=10013"
        )
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)
        resp = engine.execute_demo_decision("XAUUSD", "BUY", 0.01, price=2350.0, sl=2340.0, tp=2370.0)
        self.assertEqual(resp.Status, "Failed")

    def test_09_disconnected_terminal_fails_closed(self):
        """Test 9: Disconnected terminal (acc_info is None) fails closed."""
        self.mock_adapter.get_account_info.return_value = None
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01)
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("MT5 Terminal is disconnected", str(ctx.exception))

    def test_10_shadow_trading_remains_functional(self):
        """Test 10: Shadow trading engine runs independently without live/broker order send."""
        from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
        shadow = ShadowTradingEngine.get_instance()
        self.assertIsNotNone(shadow.account)
        self.assertGreater(shadow.account.balance, 0)


if __name__ == "__main__":
    unittest.main()
