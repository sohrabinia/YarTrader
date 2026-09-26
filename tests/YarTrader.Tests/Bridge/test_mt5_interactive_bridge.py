import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.Infrastructure.Bridge.mt5_bridge import app, get_or_create_bridge_secret_token
from src.Infrastructure.Bridge.client import MT5BridgeClient
from src.Data.Providers.MT5.mt5 import MT5DataProvider, MT5ConnectionHealth


def test_bridge_health_endpoint():
    """Verify unauthenticated GET /health probe returns HTTP 200."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "YarTrader.MT5Bridge"


def test_bridge_auth_required():
    """Verify operational endpoints reject missing or invalid Bearer tokens with HTTP 401."""
    client = TestClient(app)

    # Missing auth
    res_no_auth = client.get("/mt5/status")
    assert res_no_auth.status_code == 401

    # Invalid token
    res_bad_auth = client.get("/mt5/status", headers={"Authorization": "Bearer invalid_secret_token"})
    assert res_bad_auth.status_code == 401


def test_bridge_valid_auth_status():
    """Verify operational endpoints accept valid Bearer tokens and return status."""
    client = TestClient(app)
    valid_token = get_or_create_bridge_secret_token()

    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.get("/mt5/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "connected" in data
    assert "initialized" in data


def test_client_get_mt5_status_healthy():
    """Verify MT5BridgeClient correctly parses healthy HTTP 200 response into MT5ConnectionHealth."""
    client = MT5BridgeClient(token="test_valid_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "connected": True,
        "server": "Alpari-MT5-Demo",
        "login": 52961173,
        "ping_ms": 15.4,
        "last_error": None
    }

    with patch("requests.get", return_value=mock_resp):
        health = client.get_mt5_status()
        assert health.connected is True
        assert health.server == "Alpari-MT5-Demo"
        assert health.ping_ms == 15.4
        assert health.last_error is None


def test_client_get_mt5_status_unauthorized():
    """Verify MT5BridgeClient handles HTTP 401 gracefully returning connected=False."""
    client = MT5BridgeClient(token="invalid_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("requests.get", return_value=mock_resp):
        health = client.get_mt5_status()
        assert health.connected is False
        assert "401 Unauthorized" in health.last_error


def test_client_timeout_fail_closed():
    """Verify timeout in MT5BridgeClient fails closed returning connected=False."""
    import requests
    client = MT5BridgeClient()

    with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
        health = client.get_mt5_status()
        assert health.connected is False
        assert "Timeout" in health.last_error


def test_provider_bridge_integration(monkeypatch):
    """Verify MT5DataProvider delegates connection health to MT5BridgeClient when direct MT5 is disconnected."""
    monkeypatch.setenv("MT5_BRIDGE_ENABLED", "true")

    provider = MT5DataProvider()

    mock_bridge_health = MT5ConnectionHealth(
        connected=True,
        server="Alpari-MT5-Demo",
        ping_ms=12.5,
        last_error=None
    )

    mock_client = MagicMock()
    mock_client.get_mt5_status.return_value = mock_bridge_health

    with patch.object(provider, "_get_bridge_client", return_value=mock_client), \
         patch("src.Data.Providers.MT5.mt5.MT5_AVAILABLE", False):
        health = provider.get_connection_health()
        assert health.connected is True
        assert health.server == "Alpari-MT5-Demo"


def test_no_synthetic_data_in_production_when_bridge_fails(monkeypatch):
    """Verify production MT5DataProvider returns 0 candles when bridge is unreachable."""
    monkeypatch.setenv("YARTRADER_ENV", "production")
    monkeypatch.setenv("MT5_BRIDGE_ENABLED", "true")

    provider = MT5DataProvider()

    mock_disconnected_health = MT5ConnectionHealth(
        connected=False,
        server="Demo-Server",
        ping_ms=0.0,
        last_error="Bridge Connection Timeout"
    )

    mock_client = MagicMock()
    mock_client.get_mt5_status.return_value = mock_disconnected_health

    with patch.object(provider, "_get_bridge_client", return_value=mock_client), \
         patch("src.Data.Providers.MT5.mt5.MT5_AVAILABLE", False), \
         patch("src.Data.Providers.MT5.mt5.is_production", True):

        from src.Data.External.models import ExternalDataRequest
        req = ExternalDataRequest(symbol="XAUUSD", timeframe="H1", start_time="2026-01-01T00:00:00Z", end_time="2026-01-01T05:00:00Z")
        res = provider.fetch_data(req)

        assert res.is_success is False
        assert len(res.raw_data) == 0
