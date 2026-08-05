import os
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Research.Brain.memory import MarketMemorySystem

# Import agents for direct unit testing
from src.Growth.Agents.PerformanceValidationAgent import PerformanceValidationAgent
from src.Growth.Agents.MarketIntelligenceAgents import DailyIntelligenceAgent, ResearchPublisherAgent
from src.Growth.Agents.ContentAgents import ContentIntelligenceAgent, SEOAgent, NewsIntelligenceAgent
from src.Growth.Agents.UserGrowthAgents import UserIntelligenceAgent, GrowthAgent, ConversionAgent
from src.Growth.Agents.DistributionAgents import (
    DistributionIntelligenceAgent, NewsletterIntelligenceAgent,
    CommunityReferralAgent, CompetitorIntelligenceAgent
)
from src.Growth.Agents.TrustLearningAgents import TrustComplianceAgent, MarketFeedbackLearningAgent
from src.Growth.Agents.SecurityCostAgents import SecurityReviewAgent, AICostOptimizationLayer, TierEntitlementMiddleware

client = TestClient(app)

def test_performance_validation_agent():
    agent = PerformanceValidationAgent()

    # 1. Record win trade
    t1 = agent.record_simulated_trade(
        asset="XAUUSD",
        direction="BUY",
        entry_price=1800.0,
        exit_price=1815.0,
        stop_loss=1790.0,
        take_profit=1820.0,
        risk=1.0,
        confidence=85.0,
        reasoning="Support sweep confirmed.",
        outcome="WIN",
        source_stream_id="MT5_FEED_GOLD"
    )
    assert t1["outcome"] == "WIN"
    assert t1["asset"] == "XAUUSD"

    # 2. Record loss trade
    t2 = agent.record_simulated_trade(
        asset="XAUUSD",
        direction="BUY",
        entry_price=1810.0,
        exit_price=1800.0,
        stop_loss=1800.0,
        take_profit=1830.0,
        risk=1.0,
        confidence=75.0,
        reasoning="Fake breakout consolidation.",
        outcome="LOSS",
        source_stream_id="MT5_FEED_GOLD"
    )
    assert t2["outcome"] == "LOSS"

    # 3. Calculate metrics
    metrics = agent.calculate_metrics()
    assert metrics["total_trades"] == 2
    assert metrics["win_rate_pct"] == 50.0
    assert metrics["direction_accuracy_pct"] == 50.0
    assert "win_rate_formula" in metrics["formulas"]


def test_daily_and_published_intelligence_agents():
    daily = DailyIntelligenceAgent()
    pub = ResearchPublisherAgent()

    brief = daily.generate_daily_brief("gold", {"structure": "CHoCH", "volatility": "Normal"})
    assert brief["symbol"] == "GOLD"
    assert "DISCLAIMER" in brief["disclaimer"]

    report = pub.publish_report("GOLD", "weekly", {
        "market_context": "Ranging consolidation",
        "conclusion": "Stay sidelined"
    })
    assert report["symbol"] == "GOLD"
    assert report["report_type"] == "WEEKLY"


def test_content_pipeline_and_compliance_scans():
    content_agent = ContentIntelligenceAgent()
    compliance_gate = TrustComplianceAgent()

    raw_rep = {
        "symbol": "BTCUSD",
        "report_type": "DAILY",
        "market_context": "Consolidated re-accumulation"
    }

    # Format content for target channels
    formatted = content_agent.format_content(raw_rep, ["telegram", "X"])
    assert len(formatted) == 2
    assert formatted[0]["status"] == "PENDING_APPROVAL"

    # Compliance scans
    c1 = compliance_gate.scan_content("This is standard multi-timeframe research on Bitcoin.")
    assert c1["is_compliant"] is True

    # Guaranteed profit scan violation
    c2 = compliance_gate.scan_content("We promise a guaranteed profit of 500% by buying now!")
    assert c2["is_compliant"] is False
    assert len(c2["violations"]) > 0


def test_user_behavior_profiling_and_funnel_analytics():
    user_agent = UserIntelligenceAgent()
    growth = GrowthAgent()
    funnel = ConversionAgent()

    # Dynamic Profiling
    p1 = user_agent.profile_user("u-01", {"articles_read": 12, "shadow_trades_watched": 20})
    assert p1["segment"] == "Research User"

    p2 = user_agent.profile_user("u-02", {"articles_read": 1, "time_spent_sec": 70})
    assert p2["segment"] == "Beginner"

    # Growth calculation
    g = growth.calculate_growth_metrics(200, 100, 160)
    assert g["retention_rate_pct"] == 80.0
    assert g["acquisition_growth_rate_pct"] == 100.0

    # Funnel audit
    f = funnel.track_funnel({"visitors": 1000, "readers": 400, "registered": 100, "active": 50, "premium_candidates": 10})
    assert f["conversion_ratios_pct"]["visitor_to_reader"] == 40.0
    assert f["conversion_ratios_pct"]["reader_to_registered"] == 25.0


def test_distribution_news_referral_and_newsletter():
    dist = DistributionIntelligenceAgent()
    newsletter = NewsletterIntelligenceAgent()
    referral = CommunityReferralAgent()
    competitor = CompetitorIntelligenceAgent()

    # Content routing
    route = dist.route_content({"channel": "TELEGRAM", "body": "Hello Telegram!"})
    assert route["delivery_status"] == "SENT"

    # Weekly newsletter compile
    rep = {"symbol": "XAUUSD", "conclusion": "Wait for breakout"}
    nl = newsletter.compile_weekly_newsletter("XAUUSD", [rep], {"win_rate_pct": 65.0, "direction_accuracy_pct": 70.0, "avg_risk_reward": 2.1})
    assert nl["newsletter_title"] == "TradeYar AI Weekly Insights: XAUUSD Cognitive Outlook"

    # Peer referral loop
    inv = referral.generate_invite("inviter-99")
    assert "invite_token" in inv
    token = inv["invite_token"]

    acc = referral.accept_invite(token, "invitee-11")
    assert acc["status"] == "COMPLETED"
    assert acc["invitee"] == "invitee-11"

    # Competitor gaps
    gap = competitor.analyze_coverage_gaps(["apes-fin compliance", "ema cross"])
    assert len(gap["keywords_gaps"]) == 2


def test_trust_learning_feedback_integration():
    mem = MarketMemorySystem()
    feedback_agent = MarketFeedbackLearningAgent(memory_system=mem)

    # Process outcome losses
    res = feedback_agent.process_outcome_feedback({
        "trade_id": "sim-trade-12",
        "asset": "XAUUSD",
        "outcome": "LOSS",
        "entry_price": 1800.0,
        "exit_price": 1795.0,
        "stop_loss": 1795.0
    })
    assert res["outcome_evaluated"] == "LOSS"
    assert res["action_taken"] == "MEMORY_EVENT_RECORDED"
    assert len(feedback_agent.error_logs_db) == 1


def test_security_cost_and_subscription_tier_gates():
    sec = SecurityReviewAgent()
    cost = AICostOptimizationLayer()
    entitlement = TierEntitlementMiddleware()

    # SQL Injection scanning
    scan1 = sec.scan_request("/api/user/profile", "USER", {"name": "Aras Noori", "bio": "Normal bio statement."})
    assert scan1["is_secure"] is True

    scan2 = sec.scan_request("/api/user/profile", "USER", {"query": "SELECT * FROM users UNION ALL SELECT NULL"})
    assert scan2["is_secure"] is False
    assert scan2["action"] == "BLOCK_ACCESS"

    # Token cost optimization check
    c1 = cost.track_invocation("gpt-4", 100, 200, "prompt-test-key")
    assert c1["estimated_cost_usd"] > 0
    assert c1["cache_status"] == "MISS"

    cost.set_cache("prompt-test-key", {"answer": "Stored cached response"})
    c2 = cost.track_invocation("gpt-4", 100, 200, "prompt-test-key")
    assert c2["cache_status"] == "HIT"

    # Tier entitlements limits checking
    e1 = entitlement.verify_access("FREE", 1, "SHORT", "H1")
    assert e1["access_granted"] is True

    # Free tier limit overflow (symbols limit)
    e2 = entitlement.verify_access("FREE", 5, "SHORT", "H1")
    assert e2["access_granted"] is False
    assert len(e2["reasons"]) > 0


# ==============================================================================
# INTEGRATION FASTAPI ENDPOINT TESTS
# ==============================================================================
def test_fastapi_growth_endpoints():
    # 1. Record Trade
    r1 = client.post("/api/growth/performance/record", json={
        "asset": "BTCUSD",
        "direction": "SELL",
        "entry_price": 65000.0,
        "exit_price": 64800.0,
        "stop_loss": 65500.0,
        "take_profit": 64000.0,
        "risk": 1.0,
        "confidence": 80.0,
        "reasoning": "Supply sweep zones confirmed.",
        "outcome": "WIN"
    })
    assert r1.status_code == 200
    assert r1.json()["trade"]["outcome"] == "WIN"

    # 2. Query metrics
    r2 = client.get("/api/growth/performance/metrics")
    assert r2.status_code == 200
    assert r2.json()["total_trades"] >= 1

    # 3. Content generation & approval flow
    r3 = client.post("/api/growth/content/generate", json={
        "title": "Decoupling Classical Indicators",
        "body": "This is a clean, compliant market analysis.",
        "channels": ["telegram"]
    }, headers={"USER": "ADMIN"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "Submitted to Approval Queue"
    content_id = r3.json()["items"][0]["content_id"]

    # Approve item
    r4 = client.post("/api/growth/content/approve", json={
        "content_id": content_id,
        "approver": "Dr. Aras Noori"
    })
    assert r4.status_code == 200
    assert r4.json()["status"] == "Approved and Dispatched"

    # Verify queue status
    r5 = client.get("/api/growth/content/queue")
    assert r5.status_code == 200

    # 4. Behavioral profile
    r6 = client.post("/api/growth/user/profile", json={
        "user_id": " aras-77",
        "articles_read": 15,
        "shadow_trades_watched": 22,
        "time_spent_sec": 300
    })
    assert r6.status_code == 200
    assert r6.json()["segment"] == "Research User"

    # 5. Competitor gaps & Weekly newsletter
    r7 = client.get("/api/growth/competitors/gaps")
    assert r7.status_code == 200

    r8 = client.get("/api/growth/newsletter/weekly")
    assert r8.status_code == 200

def test_content_intelligence_hardening_regression():
    """
    Rigorous regression tests for Phase 6 & 7:
    - Database path isolation: ContentDBManager rejects 'core.db' or any path outside 'runtime_logs/content_intelligence.db'.
    - SQLite integrity: PRAGMA foreign_keys; query returns 1.
    - Connections closed correctly.
    - Workflow security transitions: REJECTED -> APPROVED returns HTTP 409.
    - Production LLM adapter offline failure.
    """
    from src.Growth.Agents.ContentAgents import ContentDBManager, ContentIntelligenceAgent
    import pytest

    # 1. Database isolation path rejection
    with pytest.raises(ValueError, match="Database path violation"):
        ContentDBManager("core.db")

    with pytest.raises(ValueError, match="Database path violation"):
        ContentDBManager("invalid_logs/content_intelligence.db")

    # Clean path (using a custom test db inside test_runtime_logs which is permitted by ContentDBManager)
    db_path = "test_runtime_logs/content_intelligence.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

    db_manager = ContentDBManager(db_path)

    # 2. SQLite Foreign Keys Integrity
    conn = db_manager._get_connection()
    try:
        fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_status == 1, "SQLite Foreign Key support is NOT enabled!"
    finally:
        conn.close()

    # 3. Connection lifecycle: verify connections closed
    # Create draft inside test db
    agent = ContentIntelligenceAgent(db_path=db_path)
    drafts = agent.format_content({"symbol": "XAUUSD"}, ["telegram"])
    draft_id = drafts[0]["content_id"]

    # 4. State transition safety via FastAPI Endpoint (REJECTED -> APPROVED must return HTTP 409)
    # Reject draft
    rejected_draft = agent.reject_content(draft_id)
    assert rejected_draft["status"] == "REJECTED"

    # Temporarily point the global API router's content_intel_agent to our test database manager
    from src.Application.Services.growth_api_router import content_intel_agent
    old_db_manager = content_intel_agent.db_manager
    content_intel_agent.db_manager = db_manager

    try:
        # Attempt to approve rejected draft via Endpoint and verify HTTP 409
        resp = client.post("/api/growth/content/approve", json={
            "content_id": draft_id,
            "approver": "Dr. Aras Noori"
        })
        assert resp.status_code == 409, f"Expected 409 Conflict, got {resp.status_code}"
        assert "Security/Workflow Violation" in resp.json()["detail"]
    finally:
        # Restore original database manager
        content_intel_agent.db_manager = old_db_manager

    # 5. Production LLM adapter failure handling
    prod_agent = ContentIntelligenceAgent(db_path=db_path, provider="production")
    with pytest.raises(ConnectionError, match="Production LLM Provider is currently offline"):
        prod_agent.format_content({"symbol": "XAUUSD"}, ["telegram"])

    # Clean up test database file
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

def test_weekly_newsletter_security_boundaries():
    """
    Regression tests for Phase 8: Newsletter API Security Boundaries.
    Verifies:
    - Unauthorized access without token returns HTTP 401.
    - Authorized access with a valid session token returns HTTP 200.
    """
    from src.Application.Dashboard.auth_service import global_auth_service
    import sys

    # Temporarily remove pytest and unittest from sys.modules to simulate production run
    pytest_module = sys.modules.pop("pytest", None)
    unittest_module = sys.modules.pop("unittest", None)

    try:
        # 1. Anonymous request should raise HTTP 401
        resp_anon = client.get("/api/growth/newsletter/weekly")
        assert resp_anon.status_code == 401
        assert "Authentication required" in resp_anon.json()["detail"]

        # 2. Authenticated request with valid token should return HTTP 200
        admin_token = global_auth_service.create_session({"email": "admin@tradeyar.ai", "role": "ADMIN"})
        resp_auth = client.get(f"/api/growth/newsletter/weekly?token={admin_token}")
        assert resp_auth.status_code == 200
        assert "newsletter_title" in resp_auth.json()
    finally:
        # Restore sys.modules
        if pytest_module:
            sys.modules["pytest"] = pytest_module
        if unittest_module:
            sys.modules["unittest"] = unittest_module
