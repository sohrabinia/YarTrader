import importlib

import pytest


def _load_provider_module():
    module = importlib.import_module("src.Data.Providers.MT5.mt5")
    return importlib.reload(module)


def test_production_uses_session2_bridge_before_native_mt5(monkeypatch):
    module = _load_provider_module()
    monkeypatch.setattr(module, "is_production", True)

    class NativeMT5:
        def initialize(self):
            raise AssertionError("native Session-0 MT5 must not be initialized in production")

    class BridgeClient:
        def __init__(self, *args, **kwargs):
            self.configured = True

        def call(self, method, **params):
            assert method == "health"
            return {
                "connected": True,
                "login": "52961173",
                "server": "Alpari-MT5-Demo",
                "trade_mode": 0,
            }

    class BridgeProxy:
        def __init__(self, client):
            self.client = client

        def terminal_info(self):
            return type("TerminalInfo", (), {"connected": True})()

        def symbols_get(self):
            return ["XAUUSD"]

        def account_info(self):
            return type(
                "AccountInfo",
                (),
                {"server": "Alpari-MT5-Demo"},
            )()

    import src.Infrastructure.mt5_session_bridge as bridge_module

    monkeypatch.setattr(bridge_module, "MT5SessionBridgeClient", BridgeClient)
    monkeypatch.setattr(bridge_module, "MT5BridgeProxy", BridgeProxy)
    monkeypatch.setattr(module, "MT5_AVAILABLE", True)
    monkeypatch.setattr(module, "mt5", NativeMT5())

    provider = module.MT5DataProvider(server="Demo-Server")

    assert provider._bridge_active is True
    assert provider._initialized is True
    health = provider.get_connection_health()
    assert health.connected is True
    assert health.server == "Alpari-MT5-Demo"


def test_production_fails_closed_when_session2_bridge_is_unavailable(monkeypatch):
    module = _load_provider_module()
    monkeypatch.setattr(module, "is_production", True)

    class NativeMT5:
        def initialize(self):
            raise AssertionError("native Session-0 MT5 must not be used as a production fallback")

    class BridgeClient:
        def __init__(self, *args, **kwargs):
            self.configured = False

    import src.Infrastructure.mt5_session_bridge as bridge_module

    monkeypatch.setattr(bridge_module, "MT5SessionBridgeClient", BridgeClient)
    monkeypatch.setattr(module, "MT5_AVAILABLE", True)
    monkeypatch.setattr(module, "mt5", NativeMT5())

    provider = module.MT5DataProvider(server="Demo-Server")
    health = provider.get_connection_health()

    assert provider._bridge_active is False
    assert provider._initialized is False
    assert health.connected is False
    assert "Session-2 bridge" in (health.last_error or "")
