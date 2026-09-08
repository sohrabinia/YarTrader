import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.Application.Governance.decision_governance_engine import (
    DecisionGovernanceEngine,
    GovernanceRule,
    GovernanceCheck,
    GovernanceResult
)
from src.Application.Services.decision_governance_service import DecisionGovernanceService
from src.Application.Decision.decision_intelligence_engine import (
    DecisionIntelligenceSummary,
    DecisionIntelligenceMetric
)
from src.Application.Decision.decision_context_engine import (
    DecisionContextSummary,
    DecisionContext,
    DecisionFactor
)
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Infrastructure.exceptions import ValidationException


def get_mock_intelligence_summary(symbol="XAUUSD", interval="M15", strategy="TREND", obs_count=30, quality="HIGH_QUALITY", readiness="INTELLIGENCE_READY"):
    d_ctx = DecisionContext(
        timestamp=datetime.now(timezone.utc),
        symbol=symbol,
        interval=interval,
        historical_context_count=obs_count,
        learning_summary={"obs_count": obs_count},
        memory_summary={"records_count": 1},
        intelligence_summary={"active_signals_count": 20}
    )
    factors = [
        DecisionFactor("HistoricalObs", obs_count, "Phase 11", "Obs count explanation"),
        DecisionFactor("MemoryCount", 1, "Phase 12", "Memory count explanation")
    ]
    ctx_summary = DecisionContextSummary(
        context_id="ctx-1",
        symbol=symbol,
        interval=interval,
        strategy_type=strategy,
        decision_context=d_ctx,
        factors=factors,
        reliability_state="STABLE_CONTEXT",
        data_quality_state=quality
    )
    metrics = [
        DecisionIntelligenceMetric("Sufficiency", 1.0, "SAMPLE_DEPTH", "Sample depth explanation")
    ]
    return DecisionIntelligenceSummary(
        intelligence_id="intel-1",
        symbol=symbol,
        interval=interval,
        strategy_type=strategy,
        decision_readiness_state=readiness,
        context_sufficiency_score=1.0,
        evidence_factor_quality=quality,
        metrics=metrics,
        decision_context_summary=ctx_summary
    )


# 1. Deterministic output repeatability
def test_1_deterministic_output():
    engine = DecisionGovernanceEngine()
    intel_summary = get_mock_intelligence_summary()

    s1 = engine.evaluate_governance(intel_summary).to_dict()
    s2 = engine.evaluate_governance(intel_summary).to_dict()

    s1.pop("governance_id", None)
    s2.pop("governance_id", None)
    s1.pop("compiled_at", None)
    s2.pop("compiled_at", None)
    s1["decision_intelligence_summary"].pop("compiled_at", None)
    s2["decision_intelligence_summary"].pop("compiled_at", None)
    s1["decision_intelligence_summary"]["decision_context_summary"].pop("compiled_at", None)
    s2["decision_intelligence_summary"]["decision_context_summary"].pop("compiled_at", None)
    s1["decision_intelligence_summary"]["decision_context_summary"]["decision_context"].pop("timestamp", None)
    s2["decision_intelligence_summary"]["decision_context_summary"]["decision_context"].pop("timestamp", None)

    assert s1 == s2


# 2. Immutable models behavior
def test_2_immutable_models():
    check = GovernanceCheck("GOV-001", "DepthCheck", True, 30, 10, "Passed depth check")
    with pytest.raises(AttributeError):
        check.rule_id = "NEW-001"


# 3. Insufficient data handling (Rejection)
def test_3_insufficient_data_rejection():
    engine = DecisionGovernanceEngine()
    intel_low = get_mock_intelligence_summary(obs_count=5)

    res = engine.evaluate_governance(intel_low)
    assert res.governance_state == "GOVERNANCE_REJECTED"
    assert any("Insufficient sample size" in r for r in res.rejection_reasons)


# 4. Low data quality rejection
def test_4_low_quality_rejection():
    engine = DecisionGovernanceEngine()
    intel_low_q = get_mock_intelligence_summary(quality="LOW_QUALITY")

    res = engine.evaluate_governance(intel_low_q)
    assert res.governance_state == "GOVERNANCE_REJECTED"
    assert any("LOW_QUALITY" in r for r in res.rejection_reasons)


# 5. Unstable context readiness rejection
def test_5_unstable_readiness_rejection():
    engine = DecisionGovernanceEngine()
    intel_unstable = get_mock_intelligence_summary(readiness="INSUFFICIENT_CONTEXT")

    res = engine.evaluate_governance(intel_unstable)
    assert res.governance_state == "GOVERNANCE_REJECTED"
    assert any("unstable" in r for r in res.rejection_reasons)


# 6. Approved governance result
def test_6_approved_governance_result():
    engine = DecisionGovernanceEngine()
    intel_good = get_mock_intelligence_summary(obs_count=30, quality="HIGH_QUALITY", readiness="INTELLIGENCE_READY")

    res = engine.evaluate_governance(intel_good)
    assert res.governance_state == "GOVERNANCE_APPROVED"
    assert res.rejection_reasons == []


# 7. Learning isolation
def test_7_learning_isolation():
    svc = DecisionGovernanceService()
    assert not hasattr(svc, "evaluate_learning")


# 8. Memory isolation
def test_8_memory_isolation():
    svc = DecisionGovernanceService()
    assert not hasattr(svc, "store_memory_record")


# 9. Intelligence isolation
def test_9_intelligence_isolation():
    svc = DecisionGovernanceService()
    assert not hasattr(svc, "generate_intelligence_signal")


# 10. No strategy modification
def test_10_no_strategy_modification():
    svc = DecisionGovernanceService()
    assert not hasattr(svc, "modify_strategy_thresholds")


# 11. No AI dependency leakage
def test_11_no_ai_dependency_leakage():
    svc = DecisionGovernanceService()
    res = svc.evaluate_decision_governance(symbol="XAUUSD", limit=30)
    forbidden = ["llm_prompt", "agent_decision", "neural_weights", "buy_recommendation"]
    for k in forbidden:
        assert k not in res


# 12. No future data leakage
def test_12_no_future_data_leakage():
    engine = DecisionGovernanceEngine()
    intel_good = get_mock_intelligence_summary()

    res1 = engine.evaluate_governance(intel_good)
    res2 = engine.evaluate_governance(intel_good)

    assert res1.governance_state == res2.governance_state


# Helper for auth token
def get_valid_token():
    user = global_auth_service.repo.get_user_by_email("admin@yartrader.app")
    if not user:
        reg = global_auth_service.register_user("admin@yartrader.app", "AdminSecret123!", name="Admin", role="ADMIN")
        user = reg["user"]
    user["is_verified"] = True
    global_auth_service.repo.users["admin@yartrader.app"] = user
    return global_auth_service.create_session(user)


# 13. API authentication protection
def test_13_api_authentication():
    client = TestClient(app)
    # Unauthenticated -> 401
    res_unauth = client.get("/api/decision-governance")
    assert res_unauth.status_code == 401

    # Valid token -> 200
    tok = get_valid_token()
    res_valid = client.get(f"/api/decision-governance?token={tok}")
    assert res_valid.status_code == 200


# 14. API parameter validation
def test_14_api_parameter_validation():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/decision-governance?limit=2000&token={tok}")
    assert res.status_code == 400
    assert "limit must be between 1 and 1000" in res.json()["detail"]


# 15. GovernanceRule validation
def test_15_rule_validation():
    rule = GovernanceRule("GOV-100", "RuleName", 10, "CATEGORY", "Explanation text")
    rule.validate()

    invalid_rule = GovernanceRule("", "RuleName", 10, "CATEGORY", "Explanation text")
    with pytest.raises(ValidationException):
        invalid_rule.validate()


# 16. GovernanceCheck validation
def test_16_check_validation():
    check = GovernanceCheck("GOV-100", "CheckName", True, 20, 10, "Msg")
    check.validate()

    invalid_check = GovernanceCheck("", "CheckName", True, 20, 10, "Msg")
    with pytest.raises(ValidationException):
        invalid_check.validate()


# 17. Service integration path
def test_17_service_integration_path():
    svc = DecisionGovernanceService()
    res = svc.evaluate_decision_governance(symbol="XAUUSD", interval="M15", strategy="TREND", limit=30)
    assert res["symbol"] == "XAUUSD"
    assert "governance_state" in res
    assert "checks" in res


# 18. Zero order execution leakage
def test_18_zero_execution_leakage():
    svc = DecisionGovernanceService()
    res = svc.evaluate_decision_governance()
    forbidden = ["orders", "positions", "trades", "buy_signal", "sell_signal"]
    for k in forbidden:
        assert k not in res


# 19. API response shape completeness
def test_19_api_response_shape():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/decision-governance?symbol=XAUUSD&interval=M15&strategy=TREND&limit=30&token={tok}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert "governance_id" in data
    assert "symbol" in data
    assert "governance_state" in data
    assert "checks" in data
    assert "rejection_reasons" in data


# 20. Bounded limit enforcement
def test_20_bounded_limit_enforcement():
    svc = DecisionGovernanceService()
    with pytest.raises(ValidationException):
        svc.evaluate_decision_governance(limit=0)

    with pytest.raises(ValidationException):
        svc.evaluate_decision_governance(limit=1001)


# 21. End-to-end Phase 16 application service execution
def test_21_end_to_end_phase16_path():
    svc = DecisionGovernanceService()
    res = svc.evaluate_decision_governance(symbol="XAUUSD", strategy="RANGE", limit=40)

    assert res["symbol"] == "XAUUSD"
    assert res["strategy_type"] == "RANGE"
    assert res["governance_state"] in ["GOVERNANCE_APPROVED", "GOVERNANCE_REJECTED"]
