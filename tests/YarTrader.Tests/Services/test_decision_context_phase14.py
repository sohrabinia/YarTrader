import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.Application.Decision.decision_context_engine import (
    DecisionContextEngine,
    DecisionContext,
    DecisionFactor,
    DecisionContextSummary
)
from src.Application.Services.decision_context_service import DecisionContextService
from src.Application.Intelligence.intelligence_engine import (
    IntelligenceSummary,
    IntelligenceContext,
    IntelligenceSignal
)
from src.Application.Learning.learning_engine import LearningInsight, LearningConfig
from src.Application.Memory.memory_engine import MemoryRecord
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Infrastructure.exceptions import ValidationException


def get_mock_intelligence_summary(symbol="XAUUSD", interval="M15", strategy="TREND"):
    i_ctx = IntelligenceContext(
        symbol=symbol,
        interval=interval,
        strategy_type=strategy,
        total_observations=30,
        active_signals_count=20,
        signal_distribution={"TREND_UP": 20, "NO_SIGNAL": 10},
        signal_frequencies={"TREND_UP": 0.6667, "NO_SIGNAL": 0.3333}
    )
    i_sigs = [
        IntelligenceSignal("TREND_UP", 20, 0.6667, "HIGH_SAMPLE"),
        IntelligenceSignal("NO_SIGNAL", 10, 0.3333, "HIGH_SAMPLE")
    ]
    return IntelligenceSummary(
        symbol=symbol,
        interval=interval,
        strategy_type=strategy,
        historical_context_count=30,
        memory_records_count=1,
        context=i_ctx,
        signal_summaries=i_sigs,
        sample_sufficiency_status="VALID_SAMPLE",
        statistical_confidence_score=1.0
    )


def get_mock_learning_insight(symbol="XAUUSD", interval="M15", strategy="TREND"):
    return LearningInsight(
        symbol=symbol,
        interval=interval,
        strategy_type=strategy,
        observation_count=30,
        signal_counts={"TREND_UP": 20, "NO_SIGNAL": 10},
        signal_frequencies={"TREND_UP": 0.6667, "NO_SIGNAL": 0.3333},
        sample_sufficiency=True,
        reliability_summary={"status": "VALID_SAMPLE", "active_signal_ratio": 0.6667},
        config=LearningConfig(symbol=symbol, interval=interval, strategy_type=strategy)
    )


# 1. Deterministic output repeatability
def test_1_deterministic_output():
    engine = DecisionContextEngine()
    i_summary = get_mock_intelligence_summary()
    l_insight = get_mock_learning_insight()
    mem_records = [
        MemoryRecord("m1", datetime.now(timezone.utc), "XAUUSD", "M15", "TREND", "INSIGHT", {}, 0.8)
    ]

    s1 = engine.compile_context_summary(i_summary, l_insight, mem_records).to_dict()
    s2 = engine.compile_context_summary(i_summary, l_insight, mem_records).to_dict()

    s1.pop("context_id", None)
    s2.pop("context_id", None)
    s1.pop("compiled_at", None)
    s2.pop("compiled_at", None)
    s1["decision_context"].pop("timestamp", None)
    s2["decision_context"].pop("timestamp", None)

    assert s1 == s2


# 2. Immutable models behavior
def test_2_immutable_models():
    factor = DecisionFactor("SampleFactor", 10, "TestPhase", "Test factor explanation")
    with pytest.raises(AttributeError):
        factor.factor_name = "NewName"


# 3. Empty input handling
def test_3_empty_input_handling():
    engine = DecisionContextEngine()
    empty_intel = IntelligenceSummary(
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        historical_context_count=0,
        memory_records_count=0,
        context=IntelligenceContext("XAUUSD", "M15", "TREND", 0, 0, {}, {}),
        signal_summaries=[],
        sample_sufficiency_status="INSUFFICIENT_DATA",
        statistical_confidence_score=0.0
    )
    empty_learning = LearningInsight(
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        observation_count=0,
        signal_counts={},
        signal_frequencies={},
        sample_sufficiency=False,
        reliability_summary={},
        config=LearningConfig()
    )

    summary = engine.compile_context_summary(empty_intel, empty_learning, [])
    assert summary.data_quality_state == "LOW_QUALITY"
    assert summary.reliability_state == "INSUFFICIENT_CONTEXT"


# 4. Context aggregation correctness
def test_4_context_aggregation():
    engine = DecisionContextEngine()
    i_summary = get_mock_intelligence_summary()
    l_insight = get_mock_learning_insight()

    summary = engine.compile_context_summary(i_summary, l_insight, [])
    assert summary.symbol == "XAUUSD"
    assert summary.data_quality_state == "HIGH_QUALITY"
    assert len(summary.factors) == 4


# 5. Learning isolation
def test_5_learning_isolation():
    svc = DecisionContextService()
    assert not hasattr(svc, "evaluate_learning")


# 6. Memory isolation
def test_6_memory_isolation():
    svc = DecisionContextService()
    assert not hasattr(svc, "store_memory_record")


# 7. Intelligence isolation
def test_7_intelligence_isolation():
    svc = DecisionContextService()
    assert not hasattr(svc, "generate_intelligence_signal")


# 8. No strategy modification
def test_8_no_strategy_modification():
    svc = DecisionContextService()
    assert not hasattr(svc, "modify_strategy_thresholds")


# 9. No AI dependency leakage
def test_9_no_ai_dependency_leakage():
    svc = DecisionContextService()
    res = svc.get_decision_context_summary(symbol="XAUUSD", limit=30)
    forbidden = ["llm_prompt", "agent_decision", "neural_weights", "buy_recommendation"]
    for k in forbidden:
        assert k not in res


# 10. No future data leakage
def test_10_no_future_data_leakage():
    engine = DecisionContextEngine()
    i_summary = get_mock_intelligence_summary()
    l_insight = get_mock_learning_insight()

    s1 = engine.compile_context_summary(i_summary, l_insight, [])

    future_mem = MemoryRecord("m2", datetime.now(timezone.utc) + timedelta(days=10), "XAUUSD", "M15", "TREND", "INSIGHT", {}, 0.8)
    s2 = engine.compile_context_summary(i_summary, l_insight, [future_mem])

    assert s1.decision_context.historical_context_count == s2.decision_context.historical_context_count


# Helper for auth token
def get_valid_token():
    user = global_auth_service.repo.get_user_by_email("admin@yartrader.app")
    if not user:
        reg = global_auth_service.register_user("admin@yartrader.app", "AdminSecret123!", name="Admin", role="ADMIN")
        user = reg["user"]
    user["is_verified"] = True
    global_auth_service.repo.users["admin@yartrader.app"] = user
    return global_auth_service.create_session(user)


# 11. API authentication protection
def test_11_api_authentication():
    client = TestClient(app)
    # Unauthenticated -> 401
    res_unauth = client.get("/api/decision-context")
    assert res_unauth.status_code == 401

    # Valid token -> 200
    tok = get_valid_token()
    res_valid = client.get(f"/api/decision-context?token={tok}")
    assert res_valid.status_code == 200


# 12. API parameter validation
def test_12_api_parameter_validation():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/decision-context?limit=2000&token={tok}")
    assert res.status_code == 400
    assert "limit must be between 1 and 1000" in res.json()["detail"]


# 13. DecisionContext validation
def test_13_decision_context_validation():
    ctx = DecisionContext(datetime.now(timezone.utc), "XAUUSD", "M15", 10, {}, {}, {})
    ctx.validate()

    invalid_ctx = DecisionContext(datetime.now(timezone.utc), "", "M15", 10, {}, {}, {})
    with pytest.raises(ValidationException):
        invalid_ctx.validate()


# 14. DecisionFactor validation
def test_14_decision_factor_validation():
    f = DecisionFactor("Fact", 10, "Source", "Exp")
    f.validate()

    invalid_f = DecisionFactor("", 10, "Source", "Exp")
    with pytest.raises(ValidationException):
        invalid_f.validate()


# 15. Service integration path
def test_15_service_integration_path():
    svc = DecisionContextService()
    res = svc.get_decision_context_summary(symbol="XAUUSD", interval="M15", strategy="TREND", limit=30)
    assert res["symbol"] == "XAUUSD"
    assert "factors" in res
    assert "reliability_state" in res


# 16. Zero order execution leakage
def test_16_zero_execution_leakage():
    svc = DecisionContextService()
    res = svc.get_decision_context_summary()
    forbidden = ["orders", "positions", "trades", "buy_signal", "sell_signal"]
    for k in forbidden:
        assert k not in res


# 17. API response shape completeness
def test_17_api_response_shape():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/decision-context?symbol=XAUUSD&interval=M15&strategy=TREND&limit=30&token={tok}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert "context_id" in data
    assert "symbol" in data
    assert "decision_context" in data
    assert "factors" in data
    assert "reliability_state" in data


# 18. Bounded limit enforcement
def test_18_bounded_limit_enforcement():
    svc = DecisionContextService()
    with pytest.raises(ValidationException):
        svc.get_decision_context_summary(limit=0)

    with pytest.raises(ValidationException):
        svc.get_decision_context_summary(limit=1001)


# 19. Quality state categorization
def test_19_quality_state_categorization():
    engine = DecisionContextEngine()
    i_high = get_mock_intelligence_summary()
    l_high = get_mock_learning_insight()

    s = engine.compile_context_summary(i_high, l_high, [])
    assert s.data_quality_state == "HIGH_QUALITY"


# 20. End-to-end Phase 14 application service execution
def test_20_end_to_end_phase14_path():
    svc = DecisionContextService()
    res = svc.get_decision_context_summary(symbol="XAUUSD", strategy="RANGE", limit=40)

    assert res["symbol"] == "XAUUSD"
    assert res["strategy_type"] == "RANGE"
    assert res["reliability_state"] in ["STABLE_CONTEXT", "INSUFFICIENT_CONTEXT"]
