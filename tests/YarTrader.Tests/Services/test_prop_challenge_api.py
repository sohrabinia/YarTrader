import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app

client = TestClient(app)

def test_get_prop_challenge_unconfigured():
    response = client.get("/api/prop/challenge")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "configured" in data

def test_configure_prop_challenge_valid():
    payload = {
        "account_size": 100000.0,
        "daily_loss_limit_percent": 5.0,
        "max_drawdown_percent": 10.0,
        "risk_per_trade_percent": 1.0,
        "max_concurrent_positions": 3,
        "session_rules": "Strict news rule"
    }
    response = client.post("/api/prop/config", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["config"]["account_size"] == 100000.0
    assert data["config"]["daily_loss_limit_percent"] == 5.0
    assert "disclaimer" in data

def test_configure_prop_challenge_invalid():
    payload = {
        "account_size": -50000.0,
        "daily_loss_limit_percent": 5.0
    }
    response = client.post("/api/prop/config", json=payload)
    assert response.status_code == 400
    assert "account_size must be positive" in response.json()["detail"]
