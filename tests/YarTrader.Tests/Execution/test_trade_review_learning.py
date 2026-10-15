import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader
from src.Execution.Services import autonomous_demo_trader as trader_module


def _base_plan():
    return {
        "status": "ORDER_PROPOSAL", "selected_strategy": "BASE_HIERARCHY",
        "decision_authority": "BASE_HIERARCHY", "reason": "fresh structural setup",
        "structure": {"parent_base_id": "H1:A", "child_base_id": "M5:B", "micro_base_id": "M1:C"},
        "order_plan": {"status": "PROPOSED", "direction": "BUY", "entry": 100.0,
                       "stop_loss": 95.0, "take_profit": 110.0},
    }


def test_open_position_is_reviewed_and_closed_outcome_reaches_brain_once(tmp_path):
    now = int(time.time())
    adapter = MagicMock()
    adapter._mt5 = SimpleNamespace(
        POSITION_TYPE_BUY=0, DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1,
        DEAL_ENTRY_IN=0, DEAL_ENTRY_OUT=1, DEAL_ENTRY_OUT_BY=3,
        DEAL_REASON_SL=4, DEAL_REASON_TP=5,
    )
    entry = {"ticket": 10, "position_id": 99, "symbol": "XAUUSD", "magic": 100001,
             "entry": 0, "type": 0, "reason": 0, "time": now-120, "price": 100.0,
             "profit": 0.0, "commission": -0.5, "swap": 0.0, "fee": 0.0}
    exit_deal = {"ticket": 11, "position_id": 99, "symbol": "XAUUSD", "magic": 100001,
                 "entry": 1, "type": 1, "reason": 4, "time": now, "price": 95.0,
                 "profit": -50.0, "commission": -0.5, "swap": 0.0, "fee": 0.0}
    adapter.get_history_deals.side_effect = [[entry], [entry, exit_deal]]
    trader = AutonomousDemoTrader(adapter=adapter)
    position = {"ticket": 99, "identifier": 99, "symbol": "XAUUSD", "magic": 100001,
                "comment": "YarBase", "type": 0, "price_open": 100.0, "sl": 95.0,
                "tp": 110.0, "volume": 0.1, "time": now-120}
    with patch.object(trader_module, "_PROJECT_ROOT", tmp_path), \
         patch("src.Research.Brain.learning_bridge.BrainLearningBridge") as bridge:
        bridge.return_value.record_demo_outcome.return_value = {"source": "DEMO", "outcome": "FAILURE"}
        trader._sync_trade_review("XAUUSD", [position], {"bid": 105.0, "ask": 105.2}, _base_plan())
        saved_open = json.loads((tmp_path / "runtime_logs" / "autonomous_trade_review_state.json").read_text())
        assert saved_open["open_positions"]["99"]["max_favorable_excursion"] == 5.0
        assert saved_open["open_positions"]["99"]["analysis_reviews"]
        trader._sync_trade_review("XAUUSD", [], {"bid": 95.0, "ask": 95.2}, _base_plan())
        trader._sync_trade_review("XAUUSD", [], {"bid": 95.0, "ask": 95.2}, _base_plan())
        saved_closed = json.loads((tmp_path / "runtime_logs" / "autonomous_trade_review_state.json").read_text())
    bridge.return_value.record_demo_outcome.assert_called_once()
    kwargs = bridge.return_value.record_demo_outcome.call_args.kwargs
    assert kwargs["pnl"] == -51.0
    assert kwargs["mfe"] == 5.0
    assert kwargs["context"]["exit_reason"] == "STOP_LOSS"
    assert kwargs["context"]["stop_loss"] == 95.0
    assert "99" in saved_closed["processed_position_ids"]
    assert "99" not in saved_closed["open_positions"]
    assert saved_closed["last_closed_setup_by_symbol"]["XAUUSD"]["signature"]


def test_identical_setup_is_blocked_after_closed_trade(tmp_path):
    adapter = MagicMock()
    adapter.get_active_orders.return_value = []
    adapter._mt5 = SimpleNamespace()
    trader = AutonomousDemoTrader(adapter=adapter)
    plan = _base_plan()
    with patch.object(trader_module, "_PROJECT_ROOT", tmp_path):
        state = trader._load_trade_review_state()
        state["last_closed_setup_by_symbol"]["XAUUSD"] = {
            "signature": trader._setup_signature("XAUUSD", plan), "position_id": 99,
            "exit_reason": "STOP_LOSS", "pnl": -51.0,
        }
        trader._save_trade_review_state(state)
        result = trader._reconcile_base_pending_order(
            "XAUUSD", plan, {"bid": 99.9, "ask": 100.0, "time": int(time.time())},
            {"balance": 10000.0, "equity": 10000.0},
            {"digits": 2, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 10.0},
        )
    assert result["status"] == "REVIEW_REQUIRED"
    adapter.send_order_to_broker.assert_not_called()


def test_repeated_losses_are_not_approved_as_learning_concepts(tmp_path):
    from src.Research.Brain.memory import MarketMemorySystem
    from src.Research.Brain.models import PatternMemory

    memory = MarketMemorySystem(storage_dir=str(tmp_path / "brain"))
    pattern = PatternMemory(
        pattern_id="pat-all-losses", sequence_signature=[100.0, 95.0, 90.0],
        occurrences_count=8, continuation_count=0, reversal_count=8,
        outcomes=[{"outcome": "FAILURE", "judge_vetted_accuracy": 1.0} for _ in range(8)],
    )
    memory.patterns[pattern.pattern_id] = pattern
    assert memory.consolidate_patterns_to_concepts(min_samples=4, min_validation_score=0.70) == []
    assert memory.get_concepts() == []


def test_closed_historical_trade_without_tracked_setup_is_not_learned(tmp_path):
    now = int(time.time())
    adapter = MagicMock()
    adapter._mt5 = SimpleNamespace(DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1, DEAL_ENTRY_IN=0,
                                   DEAL_ENTRY_OUT=1, DEAL_ENTRY_OUT_BY=3,
                                   DEAL_REASON_SL=4, DEAL_REASON_TP=5)
    adapter.get_history_deals.return_value = [
        {"ticket": 100, "position_id": 200, "symbol": "XAUUSD", "magic": 100001,
         "entry": 0, "type": 0, "reason": 0, "time": now-120, "price": 100.0, "profit": 0.0},
        {"ticket": 101, "position_id": 200, "symbol": "XAUUSD", "magic": 100001,
         "entry": 1, "type": 1, "reason": 4, "time": now-60, "price": 95.0, "profit": -50.0},
    ]
    trader = AutonomousDemoTrader(adapter=adapter)
    with patch.object(trader_module, "_PROJECT_ROOT", tmp_path), \
         patch("src.Research.Brain.learning_bridge.BrainLearningBridge") as bridge:
        trader._sync_trade_review("XAUUSD", [], {"bid": 95.0, "ask": 95.2}, _base_plan())
        saved = json.loads((tmp_path / "runtime_logs" / "autonomous_trade_review_state.json").read_text())
    bridge.return_value.record_demo_outcome.assert_not_called()
    assert "200" in saved["ignored_untracked_position_ids"]
    assert not saved["processed_position_ids"]


def test_setup_signature_changes_when_analytical_target_changes():
    trader = AutonomousDemoTrader(adapter=MagicMock())
    plan = _base_plan()
    plan["order_plan"]["take_profit"] = None
    plan["reaction_analysis"] = {"scenario": {"target": 112.0}}
    first = trader._setup_signature("XAUUSD", plan)
    assert trader._planned_target(plan) == 112.0
    plan["reaction_analysis"]["scenario"]["target"] = 115.0
    assert trader._setup_signature("XAUUSD", plan) != first
