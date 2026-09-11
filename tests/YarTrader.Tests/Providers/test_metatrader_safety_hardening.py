import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.Infrastructure.exceptions import ValidationException
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.Configuration.settings import BaseSettings
from src.Application.Services.web_dashboard import app

class TestMetaTraderSafetyHardening(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_safety_gate_permits_authorized_mt5_data_operation(self) -> None:
        """Verifies that Safety Gate allows valid read-only MT5 operations."""
        res = MetaTraderSafetyGate.verify_operation(
            terminal_type="MT5",
            operation_type="DATA",
            account_id="52961173",
            server_name="Alpari-MT5-Demo"
        )
        self.assertTrue(res)

    def test_safety_gate_rejects_unauthorized_mt5_account(self) -> None:
        """Verifies that Safety Gate blocks unauthorized accounts on MT5."""
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(
                terminal_type="MT5",
                operation_type="DATA",
                account_id="99999999",  # Unauthorized account
                server_name="Alpari-MT5-Demo"
            )
        self.assertIn("unauthorized account", str(ctx.exception))

    def test_safety_gate_rejects_unauthorized_mt5_server(self) -> None:
        """Verifies that Safety Gate blocks unauthorized servers on MT5."""
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(
                terminal_type="MT5",
                operation_type="DATA",
                account_id="52961173",
                server_name="Insecure-Live-Server"  # Unauthorized server
            )
        self.assertIn("unauthorized server", str(ctx.exception))

    def test_safety_gate_rejects_live_trading_operation_completely(self) -> None:
        """Verifies that SRE Safety Gate completely blocks real live trading execution."""
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(
                terminal_type="MT5",
                operation_type="REAL_LIVE"
            )
        self.assertIn("Real Live Trading is hard-disabled", str(ctx.exception))

    def test_safety_gate_rejects_live_trading_enabled_config_manipulation(self) -> None:
        """Verifies that even if config flag is enabled, SRE Safety Gate blocks real live operations."""
        with patch("src.Infrastructure.Configuration.config.ConfigurationManager.get_config") as mock_get_config:
            mock_conf = MagicMock()
            mock_conf.live_trading_enabled = True
            mock_get_config.return_value = mock_conf

            with self.assertRaises(ValidationException) as ctx:
                MetaTraderSafetyGate.verify_operation(
                    terminal_type="MT4",
                    operation_type="REAL_LIVE"
                )
            self.assertIn("Real Live Trading is hard-disabled", str(ctx.exception))

    def test_safety_gate_allows_mt4_live_simulation(self) -> None:
        """Verifies that MT4 can perform simulated live operations under the official account."""
        res = MetaTraderSafetyGate.verify_operation(
            terminal_type="MT4",
            operation_type="LIVE_SIMULATION",
            account_id="143056202",
            server_name="Alpari-Pro.ECN"
        )
        self.assertTrue(res)

    def test_safety_gate_rejects_mt4_unauthorized_server(self) -> None:
        """Verifies that MT4 live simulation fails if connected to unauthorized broker servers."""
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(
                terminal_type="MT4",
                operation_type="LIVE_SIMULATION",
                account_id="143056202",
                server_name="Real-Live-Server"
            )
        self.assertIn("unauthorized server", str(ctx.exception))

    def test_health_endpoint_details_isolation(self) -> None:
        """Verifies that the /health API endpoint reports correct segregated MT5/MT4 schemas without credential leakage or account/broker disclosure."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("mt5_details", data)
        self.assertIn("mt4_details", data)

        mt5_det = data["mt5_details"]
        self.assertNotIn("account", mt5_det)
        self.assertNotIn("server", mt5_det)
        self.assertEqual(mt5_det["trading_allowed"], False)
        self.assertEqual(mt5_det["role"], "DEMO")

        mt4_det = data["mt4_details"]
        self.assertNotIn("account", mt4_det)
        self.assertNotIn("server", mt4_det)
        self.assertEqual(mt4_det["live_trading_enabled"], False)
        self.assertEqual(mt4_det["role"], "LIVE_SIMULATION")

        # Confirm sensitive details, account numbers, and servers are not exposed publicly
        self.assertNotIn("52961173", str(data))
        self.assertNotIn("143056202", str(data))
        self.assertNotIn("Alpari", str(data))
        self.assertNotIn("password", str(data))
        self.assertNotIn("token", str(data))
        self.assertNotIn("secret", str(data))

    def test_risk_approved_volume_invariant_in_mt5_adapter(self) -> None:
        """Verifies that RealMT5BrokerAdapter strictly enforces risk-approved volume without silent alteration."""
        from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter, OrderRequest

        adapter = RealMT5BrokerAdapter()
        mock_mt5 = MagicMock()
        adapter._mt5 = mock_mt5
        adapter._initialized = True

        # Mock account info
        acc_info = MagicMock()
        acc_info.login = int(adapter.TARGET_ACCOUNT)
        acc_info.server = adapter.TARGET_SERVER
        acc_info.trade_mode = 0  # DEMO
        acc_info.trade_allowed = True
        mock_mt5.account_info.return_value = acc_info

        # Mock symbol info with min=0.01, max=100.0, step=0.01
        sym_info = MagicMock()
        sym_info.volume_min = 0.01
        sym_info.volume_max = 100.0
        sym_info.volume_step = 0.01
        sym_info.filling_mode = 1
        mock_mt5.symbol_info.return_value = sym_info

        # Mock tick
        tick = MagicMock()
        tick.bid = 2000.00
        tick.ask = 2000.50
        tick.volume = 100
        tick.time = 1700000000
        mock_mt5.symbol_info_tick.return_value = tick

        # Mock order check
        check_res = MagicMock()
        check_res.retcode = 0  # Success
        mock_mt5.order_check.return_value = check_res

        # Mock order result
        res = MagicMock()
        res.retcode = 10009  # TRADE_RETCODE_DONE
        res.order = 12345
        res.deal = 67890
        res.price = 2000.50
        res.volume = 0.05
        res.comment = "Success"
        mock_mt5.order_send.return_value = res

        # 1. Exact conforming volume (0.05) -> passes unchanged to order_send
        req_valid = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.05, Price=2000.50)
        res_valid = adapter.send_order_to_broker(req_valid)
        self.assertIn(res_valid.Status, ["Placed", "Closed", "SUCCESS", "PLACED"])
        sent_trade_req = mock_mt5.order_send.call_args[0][0]
        self.assertEqual(sent_trade_req["volume"], 0.05)

        # 2. Below minimum volume (0.005) -> fails closed with ValidationException
        req_below = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.005, Price=2000.50)
        with self.assertRaises(ValidationException) as ctx_below:
            adapter.send_order_to_broker(req_below)
        self.assertIn("below broker minimum", str(ctx_below.exception))

        # 3. Above maximum volume (150.0) -> fails closed with ValidationException
        req_above = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=150.0, Price=2000.50)
        with self.assertRaises(ValidationException) as ctx_above:
            adapter.send_order_to_broker(req_above)
        self.assertIn("exceeds broker maximum", str(ctx_above.exception))

        # 4. Step mismatch (0.015 with step=0.01) -> fails closed with ValidationException
        req_step = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.015, Price=2000.50)
        with self.assertRaises(ValidationException) as ctx_step:
            adapter.send_order_to_broker(req_step)
        self.assertIn("not aligned with broker volume step", str(ctx_step.exception))
