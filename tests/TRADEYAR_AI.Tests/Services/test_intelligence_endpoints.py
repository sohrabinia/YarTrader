import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app

client = TestClient(app)

def test_intelligence_dashboard_endpoint():
    response = client.get("/api/intelligence/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Healthy"
    assert "mt5_connection" in data
    assert "recent_logs" in data


def test_intelligence_reports_endpoint():
    response = client.get("/api/intelligence/reports")
    assert response.status_code == 200
    data = response.json()
    assert "reports_count" in data
    assert "recent_reports" in data
    assert len(data["recent_reports"]) >= 1


def test_intelligence_validation_endpoint():
    response = client.get("/api/intelligence/validation")
    assert response.status_code == 200
    data = response.json()
    assert "accuracy_pct" in data
    assert "outcomes" in data
    assert len(data["outcomes"]) >= 1


def test_intelligence_shadow_endpoint():
    response = client.get("/api/intelligence/shadow")
    assert response.status_code == 200
    data = response.json()
    assert "virtual_balance" in data
    assert "max_drawdown_pct" in data
    assert "trades" in data
    assert len(data["trades"]) >= 1


def test_intelligence_learning_endpoint():
    response = client.get("/api/intelligence/learning")
    assert response.status_code == 200
    data = response.json()
    assert "concepts_learned" in data
    assert "weakness_areas" in data
    assert "history" in data
    assert len(data["history"]) >= 1


def test_production_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Healthy"
    assert data["intelligence_worker"] == "Not Configured"
    assert data["shadow_worker"] == "Not Configured"
    assert "worker" in data
    assert "research_worker" in data
