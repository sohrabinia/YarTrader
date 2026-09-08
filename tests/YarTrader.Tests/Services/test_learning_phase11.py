import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.Application.Learning.learning_engine import (
    LearningEngine,
    LearningObservation,
    LearningDataset,
    LearningConfig,
    LearningInsight
)
from src.Application.Services.learning_service import LearningService
from src.Application.Backtest.backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestStrategyType,
    BacktestResult,
    BacktestEvaluation,
    BacktestSummary
)
from src.Application.Services.web_dashboard import app, global_auth_service
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.exceptions import ValidationException


def generate_candle_series(count: int, start_price: float = 2300.0, trend: float = 0.5) -> list[MarketDataPoint]:
    base_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    candles = []
    for i in range(count):
        ts = base_time + timedelta(minutes=15 * i)
        c_open = start_price + i * trend
        c_high = c_open + 2.0
        c_low = c_open - 1.0
        c_close = c_open + 1.5
        candles.append(
            MarketDataPoint(
                AssetId="XAUUSD",
                Timestamp=ts,
                Open=c_open,
                High=c_high,
                Low=c_low,
                Close=c_close,
                Volume=100.0
            )
        )
    return candles


# 1. Valid Learning observation creation
def test_1_valid_learning_observation():
    obs = LearningObservation(
        timestamp=datetime.now(timezone.utc),
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        signal_type="TREND_UP",
        metrics={"fast_sma": 2350.0, "slow_sma": 2340.0}
    )
    obs.validate()
    d = obs.to_dict()
    assert d["symbol"] == "XAUUSD"
    assert d["signal_type"] == "TREND_UP"


# 2. Invalid observation handling
def test_2_invalid_learning_observation():
    obs = LearningObservation(
        timestamp=datetime.now(timezone.utc),
        symbol="",
        interval="M15",
        strategy_type="TREND",
        signal_type="TREND_UP",
        metrics={}
    )
    with pytest.raises(ValidationException, match="symbol must be a non-empty string"):
        obs.validate()


# 3. Empty dataset safety
def test_3_empty_dataset_safety():
    engine = LearningEngine()
    dataset = LearningDataset(
        symbol="XAUUSD",
        interval="M15",
        strategy_type="TREND",
        observations=[]
    )
    insight = engine.generate_insight(dataset)
    assert insight.observation_count == 0
    assert insight.sample_sufficiency is False
    assert insight.signal_counts == {}


# 4. Deterministic ordering handling
def test_4_deterministic_ordering():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles)

    dataset = engine.extract_dataset(bt_res)
    assert len(dataset.observations) == 10
    # Confirm strictly ascending timestamps
    timestamps = [o.timestamp for o in dataset.observations]
    assert timestamps == sorted(timestamps)


# 5. Duplicate observation deduplication
def test_5_duplicate_observation_deduplication():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30)
    # Inject duplicate candle
    candles_with_dups = candles[:5] + [candles[4]] + candles[5:]
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles_with_dups)

    dataset = engine.extract_dataset(bt_res)
    assert len(dataset.observations) == 10


# 6. Strategy identification preservation
def test_6_strategy_identification():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30)
    cfg = BacktestConfig(strategy_type=BacktestStrategyType.SPIKE, min_history_bars=15)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles, cfg)

    dataset = engine.extract_dataset(bt_res)
    assert dataset.strategy_type == "SPIKE"


# 7. Spike strategy observation extraction
def test_7_spike_observation_extraction():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30)
    cfg = BacktestConfig(strategy_type=BacktestStrategyType.SPIKE, min_history_bars=15)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles, cfg)

    insight = engine.generate_insight(engine.extract_dataset(bt_res))
    assert insight.strategy_type == "SPIKE"
    assert insight.observation_count == 16


# 8. Range strategy observation extraction
def test_8_range_observation_extraction():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30, trend=0.0)
    cfg = BacktestConfig(strategy_type=BacktestStrategyType.RANGE, min_history_bars=21)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles, cfg)

    insight = engine.generate_insight(engine.extract_dataset(bt_res))
    assert insight.strategy_type == "RANGE"
    assert insight.observation_count == 10


# 9. Trend strategy observation extraction
def test_9_trend_observation_extraction():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30, trend=1.0)
    cfg = BacktestConfig(strategy_type=BacktestStrategyType.TREND, min_history_bars=21)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles, cfg)

    insight = engine.generate_insight(engine.extract_dataset(bt_res))
    assert insight.strategy_type == "TREND"
    assert insight.observation_count == 10


# 10. Statistical aggregation calculation
def test_10_statistical_aggregation():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(40, trend=1.0)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles)

    insight = engine.generate_insight(engine.extract_dataset(bt_res))
    assert insight.observation_count == 20
    assert "TREND_UP" in insight.signal_counts
    assert insight.signal_frequencies["TREND_UP"] == 1.0


# 11. Signal distribution counts
def test_11_signal_counts():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles)

    insight = engine.generate_insight(engine.extract_dataset(bt_res))
    assert sum(insight.signal_counts.values()) == insight.observation_count


# 12. Active signal ratio computation
def test_12_active_signal_ratio():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30, trend=1.0)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles)

    insight = engine.generate_insight(engine.extract_dataset(bt_res))
    rel = insight.reliability_summary
    assert rel["active_signal_count"] == 10
    assert rel["active_signal_ratio"] == 1.0


# 13. Insufficient data sample sufficiency
def test_13_insufficient_data_sufficiency():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(25)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles)

    cfg = LearningConfig(min_sample_threshold=20)
    insight = engine.generate_insight(engine.extract_dataset(bt_res), cfg)
    assert insight.sample_sufficiency is False
    assert insight.reliability_summary["status"] == "INSUFFICIENT_DATA"


# 14. Deterministic output repeatability
def test_14_deterministic_output_repeatability():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(35)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles)

    insight1 = engine.generate_insight(engine.extract_dataset(bt_res)).to_dict()
    insight2 = engine.generate_insight(engine.extract_dataset(bt_res)).to_dict()

    insight1.pop("analyzed_at", None)
    insight2.pop("analyzed_at", None)
    assert insight1 == insight2


# 15. Chronological cutoff preservation
def test_15_chronological_cutoff_preservation():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30)
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles)

    dataset = engine.extract_dataset(bt_res)
    assert dataset.observations[-1].timestamp == candles[-1].Timestamp


# 16. MANDATORY FUTURE-DATA INVARIANCE TEST
def test_16_mandatory_future_data_invariance():
    engine = LearningEngine()
    bt_engine = BacktestEngine()

    candles_base = generate_candle_series(30)
    bt_base = bt_engine.run_backtest("XAUUSD", "M15", candles_base)
    insight_base = engine.generate_insight(engine.extract_dataset(bt_base))

    candles_extended = generate_candle_series(50)
    bt_ext = bt_engine.run_backtest("XAUUSD", "M15", candles_extended)
    dataset_ext = engine.extract_dataset(bt_ext)

    # Sub-dataset up to 30 candles timestamp cutoff
    sub_obs = [o for o in dataset_ext.observations if o.timestamp <= candles_base[-1].Timestamp]
    sub_dataset = LearningDataset("XAUUSD", "M15", "TREND", sub_obs)
    insight_sub = engine.generate_insight(sub_dataset)

    d_base = insight_base.to_dict()
    d_sub = insight_sub.to_dict()
    d_base.pop("analyzed_at", None)
    d_sub.pop("analyzed_at", None)

    assert d_base == d_sub


# 17. MANDATORY STRATEGY IMMUTABILITY TEST
def test_17_mandatory_strategy_immutability():
    engine = LearningEngine()
    bt_engine = BacktestEngine()
    candles = generate_candle_series(30)

    # Evaluate trend strategy before Learning
    res_before = bt_engine.trend_engine.evaluate("XAUUSD", "M15", candles).to_dict()

    # Run full Learning analysis
    bt_res = bt_engine.run_backtest("XAUUSD", "M15", candles)
    engine.generate_insight(engine.extract_dataset(bt_res))

    # Evaluate trend strategy after Learning -> Must be 100% identical
    res_after = bt_engine.trend_engine.evaluate("XAUUSD", "M15", candles).to_dict()
    assert res_before == res_after


# 18. Backtest boundary reuse verification
def test_18_backtest_boundary_reuse():
    svc = LearningService()
    res_dict = svc.analyze_historical_learning(symbol="XAUUSD", interval="M15", strategy="TREND", limit=40)
    assert res_dict["symbol"] == "XAUUSD"
    assert res_dict["strategy_type"] == "TREND"
    assert "observation_count" in res_dict


# Helper to get valid admin session token
def get_valid_token():
    user = global_auth_service.repo.get_user_by_email("admin@yartrader.app")
    if not user:
        reg = global_auth_service.register_user("admin@yartrader.app", "AdminSecret123!", name="Admin", role="ADMIN")
        user = reg["user"]
    user["is_verified"] = True
    global_auth_service.repo.users["admin@yartrader.app"] = user
    return global_auth_service.create_session(user)


# 19. API authentication protection
def test_19_api_authentication():
    client = TestClient(app)
    # Unauthenticated request -> 401
    res_unauth = client.get("/api/learning?symbol=XAUUSD&strategy=TREND")
    assert res_unauth.status_code == 401

    # Invalid token -> 401
    res_invalid = client.get("/api/learning?symbol=XAUUSD&strategy=TREND&token=invalid_token")
    assert res_invalid.status_code == 401

    # Valid token -> 200
    tok = get_valid_token()
    res_valid = client.get(f"/api/learning?symbol=XAUUSD&strategy=TREND&token={tok}")
    assert res_valid.status_code == 200


# 20. API parameter validation
def test_20_api_parameter_validation():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/learning?symbol=XAUUSD&limit=2000&token={tok}")
    assert res.status_code == 400
    assert "limit must be between 1 and 1000" in res.json()["detail"]


# 21. API response schema verification
def test_21_api_response_schema():
    client = TestClient(app)
    tok = get_valid_token()
    res = client.get(f"/api/learning?symbol=XAUUSD&interval=M15&strategy=TREND&limit=30&token={tok}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert "symbol" in data
    assert "interval" in data
    assert "strategy_type" in data
    assert "observation_count" in data
    assert "signal_counts" in data
    assert "signal_frequencies" in data
    assert "reliability_summary" in data


# 22. Numerical safety (NaN / Infinity protection)
def test_22_numerical_safety():
    engine = LearningEngine()
    base_time = datetime.now(timezone.utc)
    flat_candles = [
        MarketDataPoint(
            AssetId="XAUUSD",
            Timestamp=base_time + timedelta(minutes=15 * i),
            Open=100.0, High=100.0, Low=100.0, Close=100.0, Volume=0.0
        )
        for i in range(30)
    ]
    bt_res = BacktestEngine().run_backtest("XAUUSD", "M15", flat_candles)
    insight = engine.generate_insight(engine.extract_dataset(bt_res))

    for freq in insight.signal_frequencies.values():
        assert not (freq != freq)  # Not NaN


# 23. Bounded historical request validation
def test_23_bounded_historical_request():
    svc = LearningService()
    with pytest.raises(ValidationException):
        svc.analyze_historical_learning(symbol="XAUUSD", limit=0)

    with pytest.raises(ValidationException):
        svc.analyze_historical_learning(symbol="XAUUSD", limit=1001)


# 24. Zero ML/Phase 12 leakage verification
def test_24_zero_ml_phase12_leakage():
    svc = LearningService()
    res_dict = svc.analyze_historical_learning(symbol="XAUUSD", interval="M15", strategy="TREND", limit=30)

    # Verify no ML, Agent, or Memory keys exist
    forbidden_keys = ["neural_weights", "agent_memory", "vector_embeddings", "optimizer_state", "llm_prompt"]
    for k in forbidden_keys:
        assert k not in res_dict


# 25. End-to-end Learning application path
def test_25_end_to_end_learning_application_path():
    svc = LearningService()
    res = svc.analyze_historical_learning(symbol="XAUUSD", interval="M15", strategy="TREND", limit=50)

    assert res["symbol"] == "XAUUSD"
    assert res["observation_count"] > 0
    assert "reliability_summary" in res
