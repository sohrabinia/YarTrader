import json
from types import SimpleNamespace

from scripts.run_sequential_market_learning_cycle import (
    SYMBOL_ORDER, atomic_json, classify_cycle_status, count_resolved_outcome_experiences, metric_snapshot,
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
