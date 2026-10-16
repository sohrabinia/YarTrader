from unittest.mock import patch

from src.Application.Services.public_api_router import get_public_metrics, get_supported_markets
from src.Application.Services.user_api_router import get_user_session_and_enforce_tier
from src.Market.Universe.symbol_registry import SymbolRegistry
import src.Application.Services.user_api_router as user_api_router


class FakeRegistry:
    def __init__(self):
        self.symbols = {
            "XAUUSD": {"active": True, "provider": "MT5", "asset_class": "Commodities", "timeframes": ["M15", "H1"]},
            "EURUSD": {"active": True, "provider": "MT5", "asset_class": "Forex", "timeframes": ["M15", "H1"]},
            "GBPUSD": {"active": False, "provider": "MT5", "asset_class": "Forex", "timeframes": ["M15", "H1"]},
            "BTCUSD": {"active": False, "provider": "Crypto", "asset_class": "Crypto", "timeframes": ["M15", "H1"]},
        }

    def get_all_registered(self):
        return self.symbols.copy()

    def get_active_matrix(self):
        return [
            ("XAUUSD", "M15", "Commodities", "MT5"),
            ("XAUUSD", "H1", "Commodities", "MT5"),
            ("EURUSD", "M15", "Forex", "MT5"),
            ("EURUSD", "H1", "Forex", "MT5"),
        ]


def test_public_metrics_use_registry_and_never_invent_performance_or_uptime():
    registry = FakeRegistry()
    with patch.object(SymbolRegistry, "get_instance", return_value=registry):
        metrics = get_public_metrics()

    assert metrics["symbols_supported_count"] == 4
    assert metrics["active_markets_count"] == 4  # supported-symbol card, not enabled count
    assert metrics["symbols_active"] == 2
    assert metrics["timeframes_active"] == 2
    assert metrics["research_contexts"] == 4
    assert metrics["providers"] == {"mt5": "ENABLED", "crypto_provider": "DISABLED"}
    assert metrics["historical_simulated_trades"] is None
    assert metrics["platform_uptime_pct"] is None
    assert metrics["apes_fin_compliant"] is None
    assert metrics["metrics_status"] == "LIVE_REGISTRY"


def test_supported_market_catalog_separates_supported_from_enabled_symbols():
    registry = FakeRegistry()
    with patch.object(SymbolRegistry, "get_instance", return_value=registry):
        markets = get_supported_markets()

    forex = next(group for group in markets if group["category"] == "Forex")
    assert forex["symbols"] == ["EURUSD", "GBPUSD"]
    assert forex["active_symbols"] == ["EURUSD"]


def test_free_tier_gate_counts_enabled_symbols_not_full_catalog(monkeypatch):
    registry = FakeRegistry()
    captured = {}

    def allow_tier(tier, symbol_count, horizon, timeframe):
        captured["symbol_count"] = symbol_count
        return {"access_granted": True, "reasons": []}

    monkeypatch.setenv("YARTRADER_ENV", "production")
    monkeypatch.setattr(user_api_router.global_auth_service, "validate_session", lambda token: {
        "email": "test@example.com", "role": "USER", "tier": "FREE"
    })
    monkeypatch.setattr(SymbolRegistry, "get_instance", lambda: registry)
    monkeypatch.setattr(user_api_router.entitlement_middleware, "verify_access", allow_tier)

    session = get_user_session_and_enforce_tier(authorization="Bearer test-token")
    assert session["tier"] == "FREE"
    assert captured["symbol_count"] == 2
