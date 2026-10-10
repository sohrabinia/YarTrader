import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.Application.Backtesting.backtest_learning_engine import (
    BacktestAndLearningEngine, build_research_fallback_signal,
)
from scripts.run_sequential_market_learning_cycle import (
    SYMBOL_ORDER, atomic_json, classify_cycle_status, count_pattern_outcomes, count_resolved_outcome_experiences, metric_snapshot,
)


def test_market_order_is_gold_then_eurusd():
    assert SYMBOL_ORDER == ("XAUUSD", "EURUSD")


def test_metric_snapshot_uses_closed_trade_pnl_and_r_multiple():
    result = metric_snapshot({
        "net_pnl": 5.0,
        "learning_updates_count": 2,
        "closed_trades": [
            {"outcome": "WIN", "pnl": 10.0, "r_multiple": 1.5},
            {"outcome": "LOSS", "pnl": -5.0, "r_multiple": -1.0},
        ],
    })

    assert result["total_trades"] == 2
    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["win_rate_pct"] == 50.0
    assert result["profit_factor"] == 2.0
    assert result["mean_r_multiple"] == 0.25
    assert result["learning_updates_count"] == 2


def test_atomic_json_persists_parseable_report(tmp_path):
    path = tmp_path / "report.json"
    atomic_json(path, {"status": "ok", "broker_orders_submitted": 0})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "status": "ok", "broker_orders_submitted": 0
    }
    assert not path.with_suffix(".json.tmp").exists()


def test_no_learning_updates_are_not_reported_as_verified_success():
    result = classify_cycle_status([
        {"symbol": "XAUUSD", "status": "COMPLETED_WITH_LEARNING"},
        {"symbol": "EURUSD", "status": "COMPLETED_NO_LEARNING_UPDATES"},
    ])

    assert result["execution_completed"] is True
    assert result["learning_verified_for_all_symbols"] is False
    assert result["status"] == "COMPLETED_EXECUTION_LEARNING_UNVERIFIED"


def test_experience_growth_without_pattern_or_concept_is_not_verified_learning():
    result = classify_cycle_status([
        {"symbol": "XAUUSD", "status": "COMPLETED_OUTCOME_EXPERIENCES_NO_PATTERN_PROMOTION"},
        {"symbol": "EURUSD", "status": "COMPLETED_WITH_LEARNING"},
    ])

    assert result["execution_completed"] is True
    assert result["learning_verified_for_all_symbols"] is False
    assert result["status"] == "COMPLETED_EXECUTION_LEARNING_UNVERIFIED"


def test_resolved_outcome_count_excludes_observation_only_and_unlabeled_records():
    memory = SimpleNamespace(experiences={
        "win": SimpleNamespace(outcome_result="SUCCESS", meta={}),
        "loss": SimpleNamespace(outcome_result="FAILURE", meta={}),
        "observed": SimpleNamespace(outcome_result="SUCCESS", meta={"is_observed_event_only": True}),
        "unlabeled": SimpleNamespace(outcome_result="UNLABELED", meta={}),
    })

    assert count_resolved_outcome_experiences(memory) == 2


def test_research_fallback_generates_causal_signal_from_trending_closed_candles():
    candles = []
    for index in range(100):
        close = 100.0 + 0.05 * index
        candles.append({
            "timestamp": f"bar-{index}", "open": close - 0.02,
            "high": close + 0.15, "low": close - 0.15,
            "close": close, "volume": 1.0,
        })

    signal = build_research_fallback_signal(candles)

    assert signal is not None
    assert signal["action"] == "BUY"
    assert signal["trade_parameters"]["source"] == "RESEARCH_FALLBACK_EMA_TREND"
    assert signal["trade_parameters"]["risk_reward"] == 1.5
    assert len(signal["sequence_signature"]) == 4


def test_research_fallback_rejects_flat_market_and_short_history():
    flat = [{
        "timestamp": f"bar-{index}", "open": 100.0,
        "high": 100.1, "low": 99.9, "close": 100.0, "volume": 1.0,
    } for index in range(100)]

    assert build_research_fallback_signal(flat) is None
    assert build_research_fallback_signal(flat[:50]) is None


def test_backtest_opt_in_fallback_records_research_strategy_trades(tmp_path):
    candles = []
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(180):
        close = 100.0 + 0.05 * index
        candles.append({
            "timestamp": (start + timedelta(hours=index)).isoformat(),
            "open": close - 0.02, "high": close + 0.15,
            "low": close - 0.15, "close": close, "volume": 1.0,
        })

    engine = BacktestAndLearningEngine(
        storage_dir=str(tmp_path / "backtest"), memory_autosave_every=1000,
    )
    result = engine.run_backtest(
        "XAUUSD", "H1", candles, initial_balance=10000.0,
        learn_from_outcomes=False, research_fallback_enabled=True,
    )

    assert any(
        trade.get("strategy") == "RESEARCH_FALLBACK_EMA_TREND"
        for trade in result["closed_trades"]
    )


def test_pattern_outcome_count_detects_updates_to_existing_patterns():
    memory = SimpleNamespace(patterns={
        "a": SimpleNamespace(occurrences_count=5),
        "b": SimpleNamespace(occurrences_count=2),
    })

    assert count_pattern_outcomes(memory) == 7
