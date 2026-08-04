import pytest
import sqlite3
import os
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Growth.ContentIntelligence.database import ContentDBManager
from src.Growth.ContentIntelligence.repository import ContentRepository
from src.Growth.ContentIntelligence.providers import MockProviderAdapter, ProductionLLMProviderAdapter
from src.Growth.ContentIntelligence.trust_engine import TrustReviewEngine

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # Set up isolated test database path
    test_db_path = "runtime_logs/test_content_intelligence.db"
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass

    # Override the repository database manager
    from src.Application.Services.content_api_router import repo
    db_manager = ContentDBManager(test_db_path)
    repo.db_manager = db_manager
    repo.db_manager.up()

    yield

    # Clean up test database safely
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass


def test_trust_review_engine_claim_violations():
    engine = TrustReviewEngine()

    # 1. Guaranteed Profit Violation (Rejected)
    draft1 = {
        "title": "Unsafe Report",
        "body": "This system guarantees a 20% daily profit for all gold buyers.",
        "language": "en",
        "source_intelligence_id": "src-101"
    }
    review1 = engine.scan_draft(draft1)
    assert review1["status"] == "REJECTED"
    assert any(v["rule_id"] == "FinancialClaimRules" for v in review1["violations"])

    # 2. Paid signals Violation (Rejected)
    draft2 = {
        "title": "Signal Promo",
        "body": "Buy now immediately and register for our paid signals channel.",
        "language": "en",
        "source_intelligence_id": "src-102"
    }
    review2 = engine.scan_draft(draft2)
    assert review2["status"] == "REJECTED"
    assert any(v["rule_id"] == "SignalLanguageRules" for v in review2["violations"])

    # 3. Missing Source Violation (Flagged)
    draft3 = {
        "title": "Healthy Report",
        "body": "We observe structural liquidity shifts under neutral trend parameters.",
        "language": "en",
        "source_intelligence_id": "" # Missing
    }
    review3 = engine.scan_draft(draft3)
    assert review3["status"] == "REJECTED" or "FLAG" in [v["severity"] for v in review3["violations"]]


def test_trust_review_engine_safe_language():
    engine = TrustReviewEngine()

    # Safe research language should pass cleanly and append disclaimers
    draft = {
        "title": "Market Report",
        "body": "Historical simulation analysis shows accumulation above the 5-minute fair-value gap levels.",
        "language": "en",
        "source_intelligence_id": "src-valid-99"
    }
    review = engine.scan_draft(draft)
    assert review["status"] == "APPROVED"
    assert len(review["violations"]) == 0
    assert "DISCLAIMER:" in review["appended_body"]


def test_multilingual_provider_adapters():
    provider = MockProviderAdapter()

    # 1. English Brief Generation
    payload_en = {
        "source_intelligence_id": "src-intel-en",
        "symbols": ["BTCUSD", "ETHUSD"],
        "title": "Trend Shift",
        "body": "Upward momentum consolidation."
    }
    draft_en = provider.generate_draft(payload_en, language="en")
    assert draft_en["language"] == "en"
    assert "TradeYar AI Intelligent Brief:" in draft_en["title"]
    assert "Source intelligence traceability" in draft_en["body"]

    # 2. Persian Brief Generation
    payload_fa = {
        "source_intelligence_id": "src-intel-fa",
        "symbols": ["XAUUSD"],
        "title": "روند بازار",
        "body": "فشار خرید در حال افزایش است."
    }
    draft_fa = provider.generate_draft(payload_fa, language="fa")
    assert draft_fa["language"] == "fa"
    assert "گزارش هوشمند TradeYar AI:" in draft_fa["title"]
    assert "شناسه مرجع اطلاعاتی منبع:" in draft_fa["body"]


def test_reversibility_of_migrations():
    test_db_path = "runtime_logs/test_migration_reversibility.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    db_manager = ContentDBManager(test_db_path)

    # 1. Run Migrations Up
    db_manager.up()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        # Verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ContentDraft'")
        assert cursor.fetchone() is not None

    # 2. Rollback Migrations Down
    db_manager.down()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ContentDraft'")
        assert cursor.fetchone() is None

    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_end_to_end_rest_api_flow():
    # 1. Generate compliant English draft
    res1 = client.post("/api/content/drafts/generate", json={
        "source_intelligence_id": "src-sre-990",
        "symbols": ["XAUUSD", "GOLD"],
        "title": "Weekly Structural Sync",
        "body": "Historical simulation analysis indicates consolidation inside NYC liquidity zones.",
        "language": "en"
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "PROCESSED"
    draft_id = data1["draft"]["id"]
    assert data1["draft"]["status"] == "APPROVED"
    assert "DISCLAIMER" in data1["draft"]["body"]

    # 2. Generate non-compliant Persian draft
    res2 = client.post("/api/content/drafts/generate", json={
        "source_intelligence_id": "src-sre-991",
        "symbols": ["BTCUSD"],
        "title": "روند سوددهی",
        "body": "ما سود تضمینی ۲۰ درصد روزانه را برای همه معامله گران تضمین میکنیم.",
        "language": "fa"
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["draft"]["status"] == "REJECTED"
    assert len(data2["draft"]["review"]["violations"]) > 0

    # 3. Retrieve drafts list
    res3 = client.get("/api/content/drafts")
    assert res3.status_code == 200
    assert len(res3.json()) >= 2

    # 4. Filter drafts by status
    res4 = client.get("/api/content/drafts?status=APPROVED")
    assert res4.status_code == 200
    assert all(d["status"] == "APPROVED" for d in res4.json())

    # 5. Filter drafts by symbol
    res5 = client.get("/api/content/drafts?symbol=BTCUSD")
    assert res5.status_code == 200
    assert len(res5.json()) == 1

    # 6. Fetch specific draft details & trace matrix
    res6 = client.get(f"/api/content/drafts/{draft_id}")
    assert res6.status_code == 200
    data6 = res6.json()
    assert data6["source_intelligence_id"] == "src-sre-990"
    assert "XAUUSD" in data6["symbols"]
    assert data6["review"]["status"] == "APPROVED"
