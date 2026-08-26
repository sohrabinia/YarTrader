import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app

client = TestClient(app)

def test_admin_financial_endpoints():
    """Verifies that financial admin endpoints respond with valid schemas for admin users."""
    # Test GET /api/admin/financial/summary
    res = client.get("/api/admin/financial/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["financial_status"] == "REAL_VERIFIED_DATA"
    assert data["currency"] == "USD"
    assert "gross_revenue_usd" in data
    assert "total_invoices_count" in data

    # Test GET /api/admin/financial/revenue
    res_rev = client.get("/api/admin/financial/revenue")
    assert res_rev.status_code == 200
    rev_data = res_rev.json()
    assert "revenue_by_tier" in rev_data

    # Test GET /api/admin/financial/transactions
    res_tx = client.get("/api/admin/financial/transactions")
    assert res_tx.status_code == 200
    tx_data = res_tx.json()
    assert "transactions" in tx_data

def test_user_financial_reports_endpoint():
    """Verifies user financial reports endpoint."""
    res = client.get("/api/user/financial/reports")
    assert res.status_code == 200
    data = res.json()
    assert "subscription" in data
    assert "payment_history" in data
