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

    def test_mt5_provider_bridge_fallback(self) -> None:
        """Verifies MT5DataProvider queries local User-Session bridge when direct MT5 initialization fails."""
        from src.Data.Providers.MT5.mt5 import MT5DataProvider
        provider = MT5DataProvider(provider_id="test-bridge-provider")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = b'{"status": "healthy", "connected": true, "bridge": "active"}'
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            # Force provider._initialized to False to trigger fallback
            provider._initialized = False
            health = provider.get_connection_health()
            self.assertTrue(health.connected)
            self.assertIsNone(health.last_error)
