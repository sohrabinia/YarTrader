import sys
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, resolve_candles_for_context

client = TestClient(app)

def test_resolve_candles_never_generates_synthetic_candles():
    """Verifies that resolve_candles_for_context strictly returns real market candles and never synthetic ones."""
    with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=[]):
        with patch("src.Application.Services.web_dashboard.generate_active_ohlcv_candles") as mock_synth:
            candles = resolve_candles_for_context("XAUUSD", "H1")
            assert candles == []
            mock_synth.assert_not_called()

def test_execution_plans_endpoint_degraded_mode_when_offline():
    """Verifies that /api/execution/plans returns UNAVAILABLE when real market data is missing."""
    with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=[]):
        resp = client.get("/api/execution/plans?symbol=XAUUSD&timeframe=H1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "WAIT"
        assert data["decision"] == "NO_TRADE"
        assert data["data_mode"] == "UNAVAILABLE"

def test_execution_confidence_endpoint_zero_when_offline():
    """Verifies that /api/execution/confidence returns 0.0 when real market data is missing."""
    with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=[]):
        resp = client.get("/api/execution/confidence?symbol=XAUUSD&timeframe=H1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence"] == 0.0

def test_fractal_status_endpoint_disconnected_observability_when_offline():
    """Verifies that /api/fractal/status returns DISCONNECTED with 0 scores when offline."""
    with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=[]):
        resp = client.get("/api/fractal/status?symbol=XAUUSD&timeframe=H1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DISCONNECTED"
        obs = data["observability"]
        assert obs["fractal_score"] == 0.0
        assert obs["similarity_score"] == 0.0
        assert obs["market_regime"] == "UNKNOWN"
