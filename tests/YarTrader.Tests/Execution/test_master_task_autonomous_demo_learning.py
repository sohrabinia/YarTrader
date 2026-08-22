import pytest
import os
from datetime import datetime
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
        configuration_version="1.2.0"
    )

    mgr.add_record(rec)
    assert len(mgr.get_all_records()) == 1

    mgr_reload = TradeJournalManager(journal_file=journal_file)
    assert len(mgr_reload.get_all_records()) == 1
    assert mgr_reload.get_all_records()[0].trade_id == "TR-001"


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
