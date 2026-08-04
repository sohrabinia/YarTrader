import pytest
import sqlite3
import os
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Growth.ContentIntelligence.database import ContentDBManager
from src.Content.Generators.ArticleGenerator import ArticleGenerator

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_p1_test_db():
    # Set up isolated test database path
    test_db_path = "runtime_logs/test_article_intelligence.db"
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


def test_article_generator_output_schemas():
    generator = ArticleGenerator()

    # 1. Market Research (English)
    p_mr = {
        "source_intelligence_id": "intel-mr-001",
        "symbols": ["XAUUSD"],
        "category": "MARKET_RESEARCH",
        "market_context": "D1 order block holding.",
        "technical_analysis": "M15 zone retest confirmed."
    }
    art_mr = generator.generate_draft(p_mr, language="en")
    assert art_mr["format"] == "ARTICLE"
    assert art_mr["language"] == "en"
    assert art_mr["metadata"]["category"] == "MARKET_RESEARCH"
    assert "Market Context" in art_mr["body"]
    assert "<h1>" in art_mr["html"]

    # 2. Educational (Persian)
    p_edu = {
        "source_intelligence_id": "intel-edu-001",
        "category": "EDUCATIONAL",
        "concept_explanation": "نفوذ نوسان‌های نامتقارن.",
        "title": "نوسان‌های زمانی"
    }
    art_edu = generator.generate_draft(p_edu, language="fa")
    assert art_edu["language"] == "fa"
    assert art_edu["metadata"]["category"] == "EDUCATIONAL"
    assert "مفهوم پایه" in art_edu["body"]


def test_article_approval_workflow_and_api():
    # 1. Generate compliant article (English)
    res1 = client.post("/api/content/articles/generate", json={
        "source_intelligence_id": "intel-sre-771",
        "symbols": ["XAUUSD"],
        "category": "MARKET_RESEARCH",
        "market_context": "Simulation displays range consolidation inside NYC boundaries.",
        "technical_analysis": "FVG zone retests verified.",
        "language": "en"
    })
    assert res1.status_code == 200
    art1 = res1.json()["article"]
    art_id = art1["id"]
    assert art1["status"] == "PENDING_REVIEW"
    assert art1["version"] == "v1.0"
    assert len(art1["audit_history"]) == 1

    # 2. Verify queue lists this pending article
    res2 = client.get("/api/content/articles/pending")
    assert res2.status_code == 200
    assert any(a["id"] == art_id for a in res2.json())

    # 3. Action: Request Revision
    res3 = client.post(f"/api/content/articles/{art_id}/review", json={
        "action": "REQUEST_REVISION",
        "actor_id": "admin-review-sre",
        "comment": "Provide more data regarding structural invalidation levels."
    })
    assert res3.status_code == 200
    art3 = res3.json()["article"]
    assert art3["status"] == "NEEDS_REVISION"
    assert len(art3["audit_history"]) == 2

    # 4. Action: Save human modifications and edit (Triggers version increment v1.0 -> v1.1)
    res4 = client.put(f"/api/content/articles/{art_id}/edit", json={
        "title": "Updated Structural Swing Brief",
        "body": "This represents the modified safe content block. Invalidation stands below the NYC baseline swing.",
        "actor_id": "analyst-aras"
    })
    assert res4.status_code == 200
    art4 = res4.json()["article"]
    assert art4["status"] == "PENDING_REVIEW"
    assert art4["version"] == "v1.1" # Correctly incremented version number
    assert len(art4["audit_history"]) == 3

    # 5. Action: Approve Article (Auto transitions PENDING_REVIEW -> APPROVED -> PUBLISH_READY)
    res5 = client.post(f"/api/content/articles/{art_id}/review", json={
        "action": "APPROVE",
        "actor_id": "admin-review-sre"
    })
    assert res5.status_code == 200
    art5 = res5.json()["article"]
    assert art5["status"] == "PUBLISH_READY"
    assert any(record["new_state"] == "PUBLISH_READY" for record in art5["audit_history"])


def test_article_api_rejection_flow():
    # Unsafe daily guaranteed profit input
    res = client.post("/api/content/articles/generate", json={
        "source_intelligence_id": "intel-sre-772",
        "symbols": ["BTCUSD"],
        "category": "SUMMARY",
        "observations": "Our neural net guarantees 25% profit gains daily on buying bitcoin immediately.",
        "language": "en"
    })
    assert res.status_code == 200
    art = res.json()["article"]
    assert art["status"] == "REJECTED"
    assert len(art["review"]["violations"]) > 0
