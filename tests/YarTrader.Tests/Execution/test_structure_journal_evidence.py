import json

from src.Execution.Services.trade_journal import TradeJournalRecord
from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader


def _record(**extra):
    payload = dict(
        decision_id="DEC-1", trade_id="TR-1", cycle_id="CYC-1", symbol="XAUUSD",
        timeframe="M5", direction="BUY", planned_entry=2300.0, planned_sl=2290.0,
        planned_tp=2320.0, planned_rr=2.0, actual_entry=2300.0, actual_exit=2320.0,
        volume=0.01, confidence=50.0, reasoning=[], evidence={}, order_ticket="1",
        deal_ticket="2", open_time="2026-10-16T12:00:00+00:00",
        close_time="2026-10-16T12:05:00+00:00", exit_reason="TP", pnl=1.0,
        pnl_percent=1.0, mfe=20.0, mae=2.0, duration=300.0, market_regime="RANGE",
        result="WIN", configuration_version="test",
    )
    payload.update(extra)
    return TradeJournalRecord(**payload)


def test_trade_journal_record_persists_structure_research_fields():
    analysis = {
        "status": "OK",
        "timeframes": {
            "H1": {
                "latest_swing_high": {"type": "SWING_HIGH", "price": 2310.0},
                "reaction_summary": {"historical_rejection_count": 3},
                "levels": [{"type": "SWING_HIGH", "price": 2310.0, "touch_count_after_confirmation": 4}],
            }
        },
    }
    record = _record(
        historical_structure_analysis=analysis,
        structural_levels=[{"source_timeframe": "H1", "price": 2310.0}],
        structural_hierarchy={"parent_base_id": "parent-1", "child_base_id": "child-2"},
        level_reaction_evidence={"H1": {"historical_rejection_count": 3}},
        entry_level_context={"H1": {"nearest_swing_levels": [{"price": 2310.0}]}},
        breakout_rejection_outcome={"classification": "PENDING"},
    )
    restored = TradeJournalRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert restored.historical_structure_analysis["timeframes"]["H1"]["latest_swing_high"]["price"] == 2310.0
    assert restored.structural_levels[0]["source_timeframe"] == "H1"
    assert restored.structural_hierarchy["child_base_id"] == "child-2"
    assert restored.level_reaction_evidence["H1"]["historical_rejection_count"] == 3
    assert restored.entry_level_context["H1"]["nearest_swing_levels"][0]["price"] == 2310.0
    assert restored.breakout_rejection_outcome["classification"] == "PENDING"


def test_autonomous_journal_event_includes_multitimeframe_level_evidence(tmp_path, monkeypatch):
    import src.Execution.Services.autonomous_demo_trader as module

    monkeypatch.setattr(module, "_PROJECT_ROOT", tmp_path)
    trader = AutonomousDemoTrader.__new__(AutonomousDemoTrader)
    trader.adapter = object()
    analysis = {
        "status": "OK",
        "timeframes": {
            "H1": {
                "levels": [{"type": "SWING_HIGH", "price": 2310.0, "rejection_count": 2}],
                "reaction_summary": {"historical_rejection_count": 2},
            }
        },
        "current_price_context": {"H1": {"nearest_swing_levels": [{"price": 2310.0}]}},
    }
    trader._log_event({
        "event": "strategy_decision",
        "symbol": "XAUUSD",
        "base_plan": {
            "historical_structure_analysis": analysis,
            "hierarchy": {"structure": {"parent_base_id": "p1", "child_base_id": "c1"}},
        },
    })
    path = tmp_path / "runtime_logs" / "trade_journal_events_v2.jsonl"
    event = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert event["historical_structure_analysis"]["timeframes"]["H1"]["levels"][0]["price"] == 2310.0
    assert event["structural_levels"][0]["source_timeframe"] == "H1"
    assert event["level_reaction_evidence"]["H1"]["historical_rejection_count"] == 2
    assert event["entry_level_context"]["H1"]["nearest_swing_levels"][0]["price"] == 2310.0
    assert event["structural_hierarchy"]["child_base_id"] == "c1"
    assert event["structure_context_inherited"] is False

    trader._log_event({"event": "position_closed", "symbol": "XAUUSD", "trade_id": "TR-1"})
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    close_event = events[-1]
    assert close_event["structure_context_inherited"] is True
    assert close_event["historical_structure_analysis"]["timeframes"]["H1"]["levels"][0]["price"] == 2310.0
    assert close_event["structural_levels"][0]["source_timeframe"] == "H1"


def test_entry_execution_reconciliation_always_journals_final_outcome():
    trader = AutonomousDemoTrader.__new__(AutonomousDemoTrader)
    events = []
    trader._log_event = events.append
    trader._reconcile_base_pending_order_impl = lambda *args, **kwargs: {
        "status": "RISK_BLOCKED", "reason": "minimum lot exceeds budget",
        "risk": {"risk_budget_usd": 2.5, "minimum_lot_risk_usd": 7.0},
    }
    plan = {
        "status": "ORDER_PROPOSAL", "selected_strategy": "BASE_HIERARCHY",
        "order_plan": {"direction": "SELL", "order_type": "SELL_LIMIT", "entry": 2300.0,
                        "stop_loss": 2310.0, "take_profit": 2280.0},
        "structure": {"parent_base_id": "p1", "child_base_id": "c1"},
        "historical_structure_analysis": {"status": "OK"},
    }
    result = trader._reconcile_base_pending_order(
        "XAUUSD", plan, {"bid": 2301.0, "ask": 2301.2}, {}, {}, per_tf=None
    )
    assert result["status"] == "RISK_BLOCKED"
    outcome = events[-1]
    assert outcome["event"] == "entry_execution_outcome"
    assert outcome["status"] == "RISK_BLOCKED"
    assert outcome["broker_confirmed"] is False
    assert outcome["reason"] == "minimum lot exceeds budget"
    assert outcome["execution_details"]["risk"]["minimum_lot_risk_usd"] == 7.0
    assert outcome["structure"]["child_base_id"] == "c1"
    assert outcome["historical_structure_analysis"]["status"] == "OK"


def test_existing_broker_pending_order_is_journaled_as_confirmed_not_new_submission():
    trader = AutonomousDemoTrader.__new__(AutonomousDemoTrader)
    events = []
    trader._log_event = events.append
    trader._reconcile_base_pending_order_impl = lambda *args, **kwargs: {
        "status": "PENDING_ORDER_ACTIVE", "ticket": 987654,
        "order_type": "SELL_LIMIT", "entry": 2300.0,
        "reason": "Broker snapshot confirms existing order remains active.",
    }
    plan = {
        "status": "ORDER_PROPOSAL", "selected_strategy": "BASE_HIERARCHY",
        "order_plan": {"direction": "SELL", "order_type": "SELL_LIMIT", "entry": 2300.0,
                        "stop_loss": 2310.0, "take_profit": 2280.0},
    }
    result = trader._reconcile_base_pending_order(
        "XAUUSD", plan, {"bid": 2301.0, "ask": 2301.2}, {}, {}, per_tf=None
    )
    assert result["status"] == "PENDING_ORDER_ACTIVE"
    event = events[-1]
    assert event["event"] == "entry_execution_outcome"
    assert event["broker_ticket"] == 987654
    assert event["broker_status"] == "Active"
    assert event["broker_confirmed"] is True
    assert event["execution_enabled"] is True
