import pytest
import os
import json
from datetime import datetime
from unittest.mock import patch
import src.Execution.Services.autonomous_demo_trader as demo_trader_module
import scripts.run_honest_walk_forward_backtest as backtest_module
from src.Decision.Models.models import AutonomousTradingDecision
from src.Execution.Services.trade_journal import TradeJournalManager, TradeJournalRecord
from src.Learning.Services.post_trade_analysis import OutcomeAnalyzer, EvidenceBasedAdaptationEngine
from src.Infrastructure.exceptions import ValidationException


def test_autonomous_decision_contract_serialization():
    d = AutonomousTradingDecision(
        decision_id="DEC-TEST-001",
        cycle_id="CYC-TEST-001",
        action="BUY",
        symbol="XAUUSD",
        timeframe="H1",
        entry=2600.0,
        stop_loss=2590.0,
        take_profit=2620.0,
        volume=0.01,
        risk_reward=2.0,
        confidence=85.0,
        reasoning=["Bullish liquidity sweep"],
        evidence={"price": 2600.0},
        risk_status="APPROVED",
        execution_status="PENDING",
        configuration_version="1.2.0",
        timestamp=datetime.now().isoformat()
    )

    d_dict = d.to_dict()
    assert d_dict["decision_id"] == "DEC-TEST-001"
    assert d_dict["action"] == "BUY"
    assert d_dict["symbol"] == "XAUUSD"
    assert d_dict["risk_reward"] == 2.0

    reconstructed = AutonomousTradingDecision.from_dict(d_dict)
    assert reconstructed.decision_id == d.decision_id
    assert reconstructed.action == d.action


def test_trade_journal_persistence(tmp_path):
    journal_file = os.path.join(str(tmp_path), "trade_journal.json")
    mgr = TradeJournalManager(journal_file=journal_file)

    rec = TradeJournalRecord(
        decision_id="DEC-001",
        trade_id="TR-001",
        cycle_id="CYC-001",
        symbol="XAUUSD",
        timeframe="H1",
        direction="BUY",
        planned_entry=2600.0,
        planned_sl=2590.0,
        planned_tp=2620.0,
        planned_rr=2.0,
        actual_entry=2600.0,
        actual_exit=2620.0,
        volume=0.01,
        confidence=85.0,
        reasoning=["Bullish OB retest"],
        evidence={},
        order_ticket="10001",
        deal_ticket="20001",
        open_time="2026-08-22T00:00:00",
        close_time="2026-08-22T01:00:00",
        exit_reason="Take Profit Hit",
        pnl=200.0,
        pnl_percent=2.0,
        mfe=20.0,
        mae=2.0,
        duration=60.0,
        market_regime="BULLISH_TREND",
        result="TARGET_HIT",
        configuration_version="1.2.0",
        trade_type="DEMO",
        strategy_style="BASE_HIERARCHY",
        decision_timeframe="H4",
        entry_timeframe="M5",
        context_timeframes=["H4", "M15", "M5", "M1"],
        data_source="MT5_DEMO_BROKER",
    )

    mgr.add_record(rec)
    assert len(mgr.get_all_records()) == 1
    saved = mgr.get_all_records()[0]
    assert saved.trade_type == "DEMO"
    assert saved.entry_weekday == "Saturday"
    assert saved.entry_day_of_month == 22
    assert saved.entry_month == 8
    assert saved.entry_year == 2026
    assert saved.entry_session == "ASIA"
    assert saved.context_timeframes == ["H4", "M15", "M5", "M1"]
    assert saved.style_transitions == []

    mgr.append_event({
        "event": "trade_review_started", "trade_type": "DEMO", "symbol": "XAUUSD",
        "strategy_style": "BASE_HIERARCHY", "decision_timeframe": "H4",
        "entry_timeframe": "M5", "context_timeframes": ["H4", "M15", "M5", "M1"],
    })
    event_lines = open(mgr.events_file, encoding="utf-8").read().splitlines()
    assert len(event_lines) == 2  # record creation + explicit lifecycle event
    event = json.loads(event_lines[-1])
    assert event["trade_type"] == "DEMO"
    assert event["strategy_style"] == "BASE_HIERARCHY"
    assert event["decision_timeframe"] == "H4"
    assert event["entry_timeframe"] == "M5"
    assert event["weekday_utc"]
    assert event["session_utc"]

    updated = TradeJournalRecord.from_dict({**saved.to_dict(), "conclusion": "Review the M5 entry zone."})
    mgr.update_record(updated)
    event_lines = open(mgr.events_file, encoding="utf-8").read().splitlines()
    update_event = json.loads(event_lines[-1])
    assert len(event_lines) == 3
    assert update_event["event"] == "trade_record_updated"
    assert "conclusion" in update_event["changed_fields"]
    assert update_event["previous_record"]["conclusion"] == ""

    mgr_reload = TradeJournalManager(journal_file=journal_file)
    assert len(mgr_reload.get_all_records()) == 1
    assert mgr_reload.get_all_records()[0].trade_id == "TR-001"
    assert mgr_reload.get_all_records()[0].strategy_style == "BASE_HIERARCHY"
    assert mgr_reload.get_all_records()[0].entry_timeframe == "M5"
    assert mgr_reload.get_all_records()[0].decision_timeframe == "H4"
    assert mgr_reload.get_all_records()[0].conclusion == "Review the M5 entry zone."


def test_corrupt_journal_fails_closed_without_treating_it_as_empty(tmp_path):
    journal_file = tmp_path / "trade_journal.json"
    journal_file.write_text("{broken json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="could not be loaded safely"):
        TradeJournalManager(journal_file=str(journal_file))
    assert journal_file.read_text(encoding="utf-8") == "{broken json"


def test_autonomous_demo_event_keeps_full_canonical_journal_and_compact_runtime_stream(tmp_path):
    trader = demo_trader_module.AutonomousDemoTrader.__new__(demo_trader_module.AutonomousDemoTrader)
    with patch.object(demo_trader_module, "_PROJECT_ROOT", tmp_path):
        trader._log_event({
            "event": "trade_review_started", "symbol": "XAUUSD",
            "trade_type": "DEMO", "strategy_style": "BASE_HIERARCHY",
            "decision_timeframe": "MULTI_TIMEFRAME",
            "hierarchy_structure": {
                "child_timeframe": "M5", "micro_timeframe": "M1",
                "hierarchy_timeframes_considered": ["H4", "H1", "M15", "M5", "M1"],
            },
        })
    runtime_path = tmp_path / "runtime_logs" / "autonomous_demo_trader.jsonl"
    journal_path = tmp_path / "runtime_logs" / "trade_journal_events_v2.jsonl"
    assert runtime_path.exists() and journal_path.exists()
    runtime_event = json.loads(runtime_path.read_text(encoding="utf-8").splitlines()[-1])
    journal_event = json.loads(journal_path.read_text(encoding="utf-8").splitlines()[-1])
    assert runtime_event["event"] == journal_event["event"] == "trade_review_started"
    assert runtime_event["runtime_log_payload"].startswith("COMPACT;")
    assert "hierarchy_structure" not in runtime_event
    assert journal_event["hierarchy_structure"]["child_timeframe"] == "M5"
    assert journal_event["trade_type"] == "DEMO"
    assert journal_event["strategy_style"] == "BASE_HIERARCHY"
    assert journal_event["decision_timeframe"] == "MULTI_TIMEFRAME"
    assert journal_event["setup_timeframe"] == "M5"
    assert journal_event["entry_timeframe"] == "M1"
    assert journal_event["execution_timeframe"] == "M1"
    assert journal_event["context_timeframes"] == ["H4", "H1", "M15", "M5", "M1"]
    assert journal_event["session_utc"]
    assert journal_event["weekday_utc"]


def test_trade_review_state_is_atomically_persisted_with_post_close_followup(tmp_path):
    trader = demo_trader_module.AutonomousDemoTrader.__new__(demo_trader_module.AutonomousDemoTrader)
    trader.adapter = object()
    state = {
        "open_positions": {},
        "processed_position_ids": {"123": {"learning_status": "CONFIRMED"}},
        "post_close_followups": {
            "123": {"symbol": "XAUUSD", "status": "WAITING_FOR_FIVE_CLOSED_M1_BARS"}
        },
        "post_close_followups_completed": {},
    }
    with patch.object(demo_trader_module, "_PROJECT_ROOT", tmp_path):
        trader._save_trade_review_state(state)
        loaded = trader._load_trade_review_state()

    assert loaded["post_close_followups"]["123"]["status"] == "WAITING_FOR_FIVE_CLOSED_M1_BARS"
    assert loaded["processed_position_ids"]["123"]["learning_status"] == "CONFIRMED"
    assert not list((tmp_path / "runtime_logs").glob("*.tmp"))


def test_post_close_followup_records_only_five_closed_m1_bars():
    class FakeMT5:
        TIMEFRAME_M1 = 1

        def copy_rates_range(self, symbol, timeframe, start, end):
            start_epoch = int(start.timestamp())
            return [
                {"time": start_epoch + i * 60, "open": 100.0 + i,
                 "high": 102.0 + i, "low": 99.0 + i,
                 "close": 101.0 + i, "tick_volume": 10}
                for i in range(5)
            ]

    trader = demo_trader_module.AutonomousDemoTrader.__new__(demo_trader_module.AutonomousDemoTrader)
    trader.adapter = type("FakeAdapter", (), {"_mt5": FakeMT5()})()
    logged = []
    trader._log_event = lambda event: logged.append(event)
    close_epoch = 1_700_000_040  # exact M1 boundary
    now = datetime.fromtimestamp(close_epoch + 5 * 60, demo_trader_module.timezone.utc)
    state = {
        "post_close_followups": {
            "123": {"position_id": 123, "symbol": "XAUUSD", "direction": "BUY",
                     "exit_price": 100.0, "closed_at_epoch": close_epoch,
                     "closed_at_utc": now.isoformat(), "exit_reason": "SL"}
        },
        "post_close_followups_completed": {},
    }

    trader._update_post_close_followups(state, "XAUUSD", now)

    assert state["post_close_followups"] == {}
    result = state["post_close_followups_completed"]["123"]
    assert result["stored_closed_m1_bars"] == 5
    assert result["post_close_max_favorable_price_move"] == 6.0
    assert result["post_close_max_adverse_price_move"] == 1.0
    assert result["signed_close_move_after_five_bars"] == 5.0
    assert len(logged) == 1 and logged[0]["event"] == "trade_post_close_m1_followup_completed"


def test_corrupt_trade_review_state_is_not_silently_reset(tmp_path):
    trader = demo_trader_module.AutonomousDemoTrader.__new__(demo_trader_module.AutonomousDemoTrader)
    trader.adapter = object()
    state_path = tmp_path / "runtime_logs" / "autonomous_trade_review_state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{broken json", encoding="utf-8")

    with patch.object(demo_trader_module, "_PROJECT_ROOT", tmp_path):
        with pytest.raises(RuntimeError, match="could not be loaded safely"):
            trader._load_trade_review_state()

    assert state_path.read_text(encoding="utf-8") == "{broken json"


def test_wait_primary_decision_compacts_repeated_structure_in_canonical_journal(tmp_path):
    trader = demo_trader_module.AutonomousDemoTrader.__new__(demo_trader_module.AutonomousDemoTrader)
    with patch.object(demo_trader_module, "_PROJECT_ROOT", tmp_path):
        trader._log_event({
            "event": "hierarchical_base_primary_decision", "symbol": "XAUUSD",
            "base_plan_summary": {"status": "WAIT"},
            "structure": {"parent_timeframe": "H4", "child_timeframe": "M5", "direction": "SELL"},
            "historical_structure_analysis": {
                "status": "OK",
                "timeframes": {"M5": {"levels": [{"type": "SWING_HIGH", "price": 1.5}],
                                      "reaction_summary": {"touches": 2, "rejections": 1}}},
                "current_price_context": {"price": 1.4},
            },
        })
    event_path = tmp_path / "runtime_logs" / "trade_journal_events_v2.jsonl"
    event = json.loads(event_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["event"] == "hierarchical_base_primary_decision"
    assert "historical_structure_analysis" not in event
    assert "structure" not in event
    assert event["structural_level_count"] == 1
    assert event["level_reaction_evidence_summary"]["M5"] == {"touches": 2, "rejections": 1}
    assert event["entry_level_context"] == {"price": 1.4}


def test_backtest_closed_trade_is_saved_with_backtest_type_and_calendar(tmp_path):
    with patch.object(backtest_module, "ROOT", tmp_path):
        written = backtest_module._append_backtest_journal_events(
            [{
                "trade_id": "BT-XAU-M1-001", "symbol": "XAUUSD", "strategy": "BASE_HIERARCHY",
                "direction": "SELL", "setup_timeframe": "M5", "entry": 2500.0,
                "exit_price": 2490.0, "stop_loss": 2510.0, "take_profit": 2480.0,
                "exit_reason": "STOP_LOSS_HIT", "outcome": "LOSS", "pnl": -12.0,
                "r_multiple": -1.0, "mfe": 8.0, "mae": -10.0, "confidence": 75.0,
                "entry_time": "2026-10-15T08:00:00+00:00",
                "exit_time": "2026-10-15T08:05:00+00:00",
                "reasoning": ["Base retest"], "market_context": {"timeframes_considered": ["H4", "M5", "M1"]},
            }],
            run_id="BT-TEST-RUN", symbol="XAUUSD", decision_timeframe="H1",
            cohort="HOLDOUT_LEARNED_FROZEN", data_file="fixture.hst",
        )
    assert written == 1
    event_path = tmp_path / "runtime_logs" / "trade_journal_events_v2.jsonl"
    event = json.loads(event_path.read_text(encoding="utf-8").splitlines()[0])
    assert event["trade_type"] == "BACKTEST"
    assert event["strategy_style"] == "BASE_HIERARCHY"
    assert event["decision_timeframe"] == "H1"
    assert event["setup_timeframe"] == "M5"
    assert event["entry_timeframe"] == "H1"
    assert event["execution_timeframe"] == "H1"
    assert event["entry_weekday"] == "Thursday"
    assert event["entry_session_utc"] == "LONDON"
    assert event["post_trade_review_status"] == "PENDING_RESEARCH_REVIEW"
    assert event["broker_orders_sent"] == 0


def test_outcome_analyzer_classification():
    cls_good = OutcomeAnalyzer.classify_trade_outcome("BUY", 2600.0, 2590.0, 2620.0, 2620.0, 20.0, 1.0, "WIN")
    assert cls_good["classification"] == "GOOD_ENTRY"

    cls_tp_far = OutcomeAnalyzer.classify_trade_outcome("BUY", 2600.0, 2590.0, 2620.0, 2590.0, 18.0, 10.0, "LOSS")
    assert cls_tp_far["classification"] == "TP_TOO_FAR"


def test_evidence_based_learning_protection_gates(tmp_path):
    history_file = os.path.join(str(tmp_path), "learning_adaptations.json")
    engine = EvidenceBasedAdaptationEngine(minimum_sample_size=5, history_file=history_file)

    # 1. Sample Size Protection Gate
    u1 = engine.propose_adaptation("setup_ranking", 1.0, 1.2, ["t1", "t2"], ("2026-08-01", "2026-08-22"), "Sample check")
    assert u1.validation_status == "OBSERVE_ONLY"

    # 2. Validated Adaptation
    u2 = engine.propose_adaptation("setup_ranking", 1.0, 1.2, ["t1", "t2", "t3", "t4", "t5"], ("2026-08-01", "2026-08-22"), "Sample check")
    assert u2.validation_status == "VALIDATED"

    # 3. Absolute Safety Boundary Guard
    with pytest.raises(ValidationException):
        engine.propose_adaptation("LIVE_TRADING_ENABLED", False, True, ["t1", "t2", "t3", "t4", "t5"], ("2026-08-01", "2026-08-22"), "Safety bypass attempt")
