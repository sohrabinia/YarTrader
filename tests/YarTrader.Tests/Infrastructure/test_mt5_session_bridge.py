import os
import unittest
from unittest.mock import MagicMock, patch

from src.Infrastructure.mt5_session_bridge import MT5BridgeProxy, MT5SessionBridgeClient, _DictObject


class TestMT5SessionBridge(unittest.TestCase):
    def test_proxy_exposes_remote_account_as_object(self):
        client = MagicMock()
        client.call.return_value = {"login": 52961173, "server": "Alpari-MT5-Demo", "trade_mode": 0, "equity": 1000.0}
        proxy = MT5BridgeProxy(client)
        account = proxy.account_info()
        self.assertEqual(account.login, 52961173)
        self.assertEqual(account.server, "Alpari-MT5-Demo")
        client.call.assert_called_once_with("account_info")

    def test_proxy_forwards_rates_and_serializes_dates(self):
        client = MagicMock()
        client.call.return_value = []
        proxy = MT5BridgeProxy(client)
        proxy.copy_rates_range("XAUUSD", 16385, "2026-09-29T10:00:00", "2026-09-29T11:00:00")
        client.call.assert_called_once_with("copy_rates_range", symbol="XAUUSD", timeframe=16385, date_from="2026-09-29T10:00:00", date_to="2026-09-29T11:00:00")

    def test_client_requires_token(self):
        with patch.dict(os.environ, {}, clear=True):
            client = MT5SessionBridgeClient()
            self.assertFalse(client.configured)
            with self.assertRaisesRegex(RuntimeError, "TOKEN"):
                client.call("health")

    def test_dict_object_supports_asdict(self):
        obj = _DictObject({"connected": True, "login": 52961173})
        self.assertTrue(obj.connected)
        self.assertEqual(obj._asdict()["login"], 52961173)


if __name__ == "__main__":
    unittest.main()
