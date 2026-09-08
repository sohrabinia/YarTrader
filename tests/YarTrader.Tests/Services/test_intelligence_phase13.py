import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.Application.Intelligence.intelligence_engine import (
    IntelligenceEngine,
    IntelligenceContext,
    IntelligenceSignal,
    IntelligenceSummary
)
from src.Application.Services.intelligence_service import IntelligenceService
from src.Application.Learning.learning_engine import LearningInsight, LearningConfig
from src.Application.Memory.memory_engine import MemoryRecord
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Infrastructure.exceptions import ValidationException


def get_mock_learning_insight(symbol="XAUUSD", interval="M15", strategy="TREND", obs_count=30):
    return LearningInsight(
        symbol=symbol,
        interval=interval,
        strategy_type=strategy,
        observation_count=obs_count,
        signal_counts={"TREND_UP": 20, "NO_SIGNAL": 10},
        signal_frequencies={"TREND_UP": 0.6667, "NO_SIGNAL": 0.3333},
        sample_sufficiency=True,
        reliability_summary={"status": "VALID_SAMPLE", "active_signal_ratio": 0.6667},
        config=LearningConfig(symbol=symbol, interval=interval, strategy_type=strategy)
    )


# 1. Deterministic output repeatability
def test_1_deterministic_output():
    engine = IntelligenceEngine()
    l_insight = get_mock_learning_insight()
    mem_records = [
        MemoryRecord(
            id="m1",
            timestamp=datetime.now(timezone.utc),
            symbol="XAUUSD",
            interval="M15",
            strategy_type="TREND",
            observation_type="INSIGHT",
            metrics={},
            confidence=0.8
        )
    ]
    s1 = engine.compile_summary(l_insight, mem_records).to_dict()
    s2 = engine.compile_summary(l_insight, mem_records).to_dict()

    s1.pop("compiled_at", None)
    s2.pop("compiled_at", None)
    assert s1 == s2


# 2. Immutable models behavior
def test_2_immutable_models():
    ctx = IntelligenceContext("XAUUSD", "M15", "TREND", 30, 20, {"TREND_UP": 20}, {"TREND_UP": 0.6667})
    with pytest.raises(AttributeError):
        ctx.symbol = "BTCUSD"


# 3. Empty data handling
def test_3_empty_data_handling():
    engine = IntelligenceEngine()
    empty_insight = LearningInsight(
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        observation_count=0,
        signal_counts={},
        signal_frequencies={},
        sample_sufficiency=False,
        reliability_summary={"status": "INSUFFICIENT_DATA", "active_signal_ratio": 0.0},
        config=LearningConfig()
    )
    summary = engine.compile_summary(empty_insight, [])
    assert summary.historical_context_count == 0
    assert summary.memory_records_count == 0
    assert summary.sample_sufficiency_status == "INSUFFICIENT_DATA"


# 4. Historical aggregation correctness
def test_4_historical_aggregation():
    engine = IntelligenceEngine()
    l_insight = get_mock_learning_insight(obs_count=40)
    summary = engine.compile_summary(l_insight, [])

    assert summary.historical_context_count == 40
    assert summary.context.active_signals_count == 20
    assert summary.statistical_confidence_score == 1.0


# 5. No strategy mutation
def test_5_no_strategy_mutation():
    svc = IntelligenceService()
    assert not hasattr(svc, "evaluate_strategy")
    assert not hasattr(svc, "update_thresholds")


# 6. No learning mutation
def test_6_no_learning_mutation():
    svc = IntelligenceService()
    assert not hasattr(svc, "update_learning_weights")


# 7. No memory mutation
def test_7_no_memory_mutation():
    svc = IntelligenceService()
    assert not hasattr(svc, "clear_memory_store")


# 8. No AI dependency leakage
def test_8_no_ai_dependency_leakage():
    svc = IntelligenceService()
    res = svc.get_historical_intelligence_summary(symbol="XAUUSD", limit=30)
    forbidden = ["neural_network", "agent_brain", "prompt_template", "vector_embedding"]
    for k in forbidden:
        assert k not in res


# 9. No future data leakage
def test_9_no_future_data_leakage():
    engine = IntelligenceEngine()
    l1 = get_mock_learning_insight(obs_count=30)
    s1 = engine.compile_summary(l1, [])

    # Adding a future memory record should only increment memory count, not distort historical context count
    future_record = MemoryRecord(
        id="m2",
        timestamp=datetime.now(timezone.utc) + timedelta(days=10),
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        observation_type="INSIGHT",
        metrics={},
        confidence=0.8
    )
    s2 = engine.compile_summary(l1, [future_record])

    assert s1.historical_context_count == s2.historical_context_count


# Helper for auth token
def get_valid_token():
    user = global_auth_service.repo.get_user_by_email("admin@yartrader.app")
    if not user:
        reg = global_auth_service.register_user("admin@yartrader.app", "AdminSecret123!", name="Admin", role="ADMIN")
        user = reg["user"]
    user["is_verified"] = True
    global_auth_service.repo.users["admin@yartrader.app"] = user
    return global_auth_service.create_session(user)


# 10. API authentication protection
def test_10_api_authentication_protection():
    client = TestClient(app)
    # Unauthenticated -> 401
    res_unauth = client.get("/api/intelligence")
    assert res_unauth.status_code == 401

    # Valid token -> 200
    tok = get_valid_token()
    res_valid = client.get(f"/api/intelligence?token={tok}")
    assert res_valid.status_code == 200


# 11. API parameter validation
def test_11_api_parameter_validation():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/intelligence?limit=2000&token={tok}")
    assert res.status_code == 400
    assert "limit must be between 1 and 1000" in res.json()["detail"]


# 12. IntelligenceContext validation
def test_12_context_validation():
    ctx = IntelligenceContext("XAUUSD", "M15", "TREND", 10, 5, {}, {})
    ctx.validate()

    invalid_ctx = IntelligenceContext("", "M15", "TREND", 10, 5, {}, {})
    with pytest.raises(ValidationException):
        invalid_ctx.validate()


# 13. IntelligenceSignal validation
def test_13_signal_validation():
    sig = IntelligenceSignal("TREND_UP", 10, 0.5, "HIGH_SAMPLE")
    sig.validate()

    invalid_sig = IntelligenceSignal("TREND_UP", -1, 0.5, "HIGH_SAMPLE")
    with pytest.raises(ValidationException):
        invalid_sig.validate()


# 14. Sample confidence state categorization
def test_14_sample_confidence_states():
    engine = IntelligenceEngine()
    insight_high = get_mock_learning_insight(obs_count=30)
    summary = engine.compile_summary(insight_high, [])

    trend_sig = next(s for s in summary.signal_summaries if s.signal_name == "TREND_UP")
    assert trend_sig.sample_confidence_state == "HIGH_SAMPLE"


# 15. Statistical confidence score capping
def test_15_statistical_confidence_capping():
    engine = IntelligenceEngine()
    insight_large = get_mock_learning_insight(obs_count=500)
    summary = engine.compile_summary(insight_large, [])

    assert summary.statistical_confidence_score == 1.0


# 16. Service integration path
def test_16_service_integration():
    svc = IntelligenceService()
    res = svc.get_historical_intelligence_summary(symbol="XAUUSD", interval="M15", strategy="TREND", limit=40)

    assert res["symbol"] == "XAUUSD"
    assert "context" in res
    assert "signal_summaries" in res


# 17. Zero order execution leakage
def test_17_zero_execution_leakage():
    svc = IntelligenceService()
    res = svc.get_historical_intelligence_summary()
    forbidden = ["orders", "positions", "trades", "wallet_balance", "broker_session"]
    for k in forbidden:
        assert k not in res


# 18. API response shape completeness
def test_18_api_response_shape():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/intelligence?symbol=XAUUSD&interval=M15&strategy=TREND&limit=30&token={tok}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert "symbol" in data
    assert "historical_context_count" in data
    assert "context" in data
    assert "statistical_confidence_score" in data


# 19. Bounded limit enforcement
def test_19_bounded_limit_enforcement():
    svc = IntelligenceService()
    with pytest.raises(ValidationException):
        svc.get_historical_intelligence_summary(limit=0)

    with pytest.raises(ValidationException):
        svc.get_historical_intelligence_summary(limit=1001)


# 20. End-to-end Phase 13 application service execution
def test_20_end_to_end_phase13_path():
    svc = IntelligenceService()
    res = svc.get_historical_intelligence_summary(symbol="XAUUSD", strategy="SPIKE", limit=50)

    assert res["symbol"] == "XAUUSD"
    assert res["strategy_type"] == "SPIKE"
    assert res["sample_sufficiency_status"] in ["VALID_SAMPLE", "INSUFFICIENT_DATA"]
