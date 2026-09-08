import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.Application.Decision.decision_intelligence_engine import (
    DecisionIntelligenceEngine,
    DecisionIntelligenceMetric,
    DecisionIntelligenceSummary
)
from src.Application.Services.decision_intelligence_service import DecisionIntelligenceService
from src.Application.Decision.decision_context_engine import (
    DecisionContextSummary,
    DecisionContext,
    DecisionFactor
)
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Infrastructure.exceptions import ValidationException


def get_mock_context_summary(symbol="XAUUSD", interval="M15", strategy="TREND"):
    d_ctx = DecisionContext(
        timestamp=datetime.now(timezone.utc),
        symbol=symbol,
        interval=interval,
        historical_context_count=30,
        learning_summary={"obs_count": 30},
        memory_summary={"records_count": 1},
        intelligence_summary={"active_signals_count": 20}
    )
    factors = [
        DecisionFactor("HistoricalObs", 30, "Phase 11", "Obs count explanation"),
        DecisionFactor("MemoryCount", 1, "Phase 12", "Memory count explanation")
    ]
    return DecisionContextSummary(
        context_id="ctx-1",
        symbol=symbol,
        interval=interval,
        strategy_type=strategy,
        decision_context=d_ctx,
        factors=factors,
        reliability_state="STABLE_CONTEXT",
        data_quality_state="HIGH_QUALITY"
    )


# 1. Deterministic output repeatability
def test_1_deterministic_output():
    engine = DecisionIntelligenceEngine()
    ctx_summary = get_mock_context_summary()

    s1 = engine.compile_intelligence_summary(ctx_summary).to_dict()
    s2 = engine.compile_intelligence_summary(ctx_summary).to_dict()

    s1.pop("intelligence_id", None)
    s2.pop("intelligence_id", None)
    s1.pop("compiled_at", None)
    s2.pop("compiled_at", None)
    s1["decision_context_summary"]["decision_context"].pop("timestamp", None)
    s2["decision_context_summary"]["decision_context"].pop("timestamp", None)

    assert s1 == s2


# 2. Immutable models behavior
def test_2_immutable_models():
    m = DecisionIntelligenceMetric("Sufficiency", 1.0, "SAMPLE_DEPTH", "Sample depth explanation")
    with pytest.raises(AttributeError):
        m.metric_name = "NewMetric"


# 3. Empty input handling
def test_3_empty_input_handling():
    engine = DecisionIntelligenceEngine()
    empty_ctx_obj = DecisionContext(datetime.now(timezone.utc), "XAUUSD", "M15", 0, {}, {}, {})
    empty_summary = DecisionContextSummary(
        context_id="ctx-0",
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        decision_context=empty_ctx_obj,
        factors=[],
        reliability_state="INSUFFICIENT_CONTEXT",
        data_quality_state="LOW_QUALITY"
    )

    s = engine.compile_intelligence_summary(empty_summary)
    assert s.context_sufficiency_score == 0.0
    assert s.decision_readiness_state == "INSUFFICIENT_CONTEXT"


# 4. Context aggregation correctness
def test_4_context_aggregation():
    engine = DecisionIntelligenceEngine()
    ctx_summary = get_mock_context_summary()

    summary = engine.compile_intelligence_summary(ctx_summary)
    assert summary.symbol == "XAUUSD"
    assert summary.context_sufficiency_score == 1.0
    assert summary.decision_readiness_state == "INTELLIGENCE_READY"


# 5. Learning isolation
def test_5_learning_isolation():
    svc = DecisionIntelligenceService()
    assert not hasattr(svc, "evaluate_learning")


# 6. Memory isolation
def test_6_memory_isolation():
    svc = DecisionIntelligenceService()
    assert not hasattr(svc, "store_memory_record")


# 7. Intelligence isolation
def test_7_intelligence_isolation():
    svc = DecisionIntelligenceService()
    assert not hasattr(svc, "generate_intelligence_signal")


# 8. Decision Context isolation
def test_8_decision_context_isolation():
    svc = DecisionIntelligenceService()
    assert not hasattr(svc, "create_decision_factor")


# 9. No strategy modification
def test_9_no_strategy_modification():
    svc = DecisionIntelligenceService()
    assert not hasattr(svc, "modify_strategy_thresholds")


# 10. No AI dependency leakage
def test_10_no_ai_dependency_leakage():
    svc = DecisionIntelligenceService()
    res = svc.get_decision_intelligence_summary(symbol="XAUUSD", limit=30)
    forbidden = ["llm_prompt", "agent_decision", "neural_weights", "buy_recommendation"]
    for k in forbidden:
        assert k not in res


# 11. No future data leakage
def test_11_no_future_data_leakage():
    engine = DecisionIntelligenceEngine()
    ctx_summary = get_mock_context_summary()

    s1 = engine.compile_intelligence_summary(ctx_summary)
    s2 = engine.compile_intelligence_summary(ctx_summary)

    assert s1.context_sufficiency_score == s2.context_sufficiency_score


# Helper for auth token
def get_valid_token():
    user = global_auth_service.repo.get_user_by_email("admin@yartrader.app")
    if not user:
        reg = global_auth_service.register_user("admin@yartrader.app", "AdminSecret123!", name="Admin", role="ADMIN")
        user = reg["user"]
    user["is_verified"] = True
    global_auth_service.repo.users["admin@yartrader.app"] = user
    return global_auth_service.create_session(user)


# 12. API authentication protection
def test_12_api_authentication():
    client = TestClient(app)
    # Unauthenticated -> 401
    res_unauth = client.get("/api/decision-intelligence")
    assert res_unauth.status_code == 401

    # Valid token -> 200
    tok = get_valid_token()
    res_valid = client.get(f"/api/decision-intelligence?token={tok}")
    assert res_valid.status_code == 200


# 13. API parameter validation
def test_13_api_parameter_validation():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/decision-intelligence?limit=2000&token={tok}")
    assert res.status_code == 400
    assert "limit must be between 1 and 1000" in res.json()["detail"]


# 14. DecisionIntelligenceMetric validation
def test_14_metric_validation():
    m = DecisionIntelligenceMetric("Sufficiency", 1.0, "SAMPLE_DEPTH", "Depth explanation")
    m.validate()

    invalid_m = DecisionIntelligenceMetric("", 1.0, "SAMPLE_DEPTH", "Depth explanation")
    with pytest.raises(ValidationException):
        invalid_m.validate()


# 15. Service integration path
def test_15_service_integration_path():
    svc = DecisionIntelligenceService()
    res = svc.get_decision_intelligence_summary(symbol="XAUUSD", interval="M15", strategy="TREND", limit=30)
    assert res["symbol"] == "XAUUSD"
    assert "metrics" in res
    assert "decision_readiness_state" in res


# 16. Zero order execution leakage
def test_16_zero_execution_leakage():
    svc = DecisionIntelligenceService()
    res = svc.get_decision_intelligence_summary()
    forbidden = ["orders", "positions", "trades", "buy_signal", "sell_signal"]
    for k in forbidden:
        assert k not in res


# 17. API response shape completeness
def test_17_api_response_shape():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/decision-intelligence?symbol=XAUUSD&interval=M15&strategy=TREND&limit=30&token={tok}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert "intelligence_id" in data
    assert "symbol" in data
    assert "decision_readiness_state" in data
    assert "context_sufficiency_score" in data
    assert "metrics" in data


# 18. Bounded limit enforcement
def test_18_bounded_limit_enforcement():
    svc = DecisionIntelligenceService()
    with pytest.raises(ValidationException):
        svc.get_decision_intelligence_summary(limit=0)

    with pytest.raises(ValidationException):
        svc.get_decision_intelligence_summary(limit=1001)


# 19. Readiness state categorization
def test_19_readiness_state_categorization():
    engine = DecisionIntelligenceEngine()
    c_summary = get_mock_context_summary()

    s = engine.compile_intelligence_summary(c_summary)
    assert s.decision_readiness_state == "INTELLIGENCE_READY"


# 20. End-to-end Phase 15 application service execution
def test_20_end_to_end_phase15_path():
    svc = DecisionIntelligenceService()
    res = svc.get_decision_intelligence_summary(symbol="XAUUSD", strategy="SPIKE", limit=40)

    assert res["symbol"] == "XAUUSD"
    assert res["strategy_type"] == "SPIKE"
    assert res["decision_readiness_state"] in ["INTELLIGENCE_READY", "INSUFFICIENT_CONTEXT"]
