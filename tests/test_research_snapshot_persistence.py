import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.Application.Deployment.storage import (
    YarTraderStorageManager,
    is_research_snapshot_fresh,
)


def test_research_snapshot_freshness_rejects_stale_and_future_data():
    now = datetime.now(timezone.utc)
    fresh = {"timestamp": (now - timedelta(minutes=30)).isoformat(), "timeframe": "H1"}
    stale = {"timestamp": (now - timedelta(hours=4)).isoformat(), "timeframe": "H1"}
    future = {"timestamp": (now + timedelta(minutes=20)).isoformat(), "timeframe": "H1"}

    assert is_research_snapshot_fresh(fresh, now=now)
    assert not is_research_snapshot_fresh(stale, now=now)
    assert not is_research_snapshot_fresh(future, now=now)
    assert not is_research_snapshot_fresh({"timeframe": "H1"}, now=now)


def test_signal_api_reads_canonical_storage_and_maps_entry_field(tmp_path, monkeypatch):
    monkeypatch.setenv("YarTraderStorageRoot", str(tmp_path))
    monkeypatch.delenv("TradeYarStorageRoot", raising=False)
    os.makedirs(tmp_path / "Runtime" / "research_logs" / "research_snapshots", exist_ok=True)
    YarTraderStorageManager.reset()
    try:
        manager = YarTraderStorageManager.get_manager()
        snapshot_dir = manager.get_research_snapshots_dir()
        now = datetime.now(timezone.utc).isoformat()
        snapshot = {
            "report_id": "test-fresh-snapshot",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "timestamp": now,
            "findings": {
                "autonomous_decision": {
                    "decision_id": "test-signal-1",
                    "action": "BUY",
                    "entry": 2500.1,
                    "stop_loss": 2490.0,
                    "take_profit": 2520.0,
                    "risk_reward": 1.97,
                    "confidence": 80.0,
                    "reasoning": ["unit-test"],
                    "evidence": {"decision_authority": "BASE_HIERARCHY"},
                },
                "intel_summary": {"decision_authority": "BASE_HIERARCHY", "candidate_available": True}
            }
        }
        with open(os.path.join(snapshot_dir, "fresh-test.json"), "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle)

        from src.Application.Services.user_api_router import _snapshot_signals
        signals = _snapshot_signals()
        assert len(signals) == 1
        assert signals[0]["entry_zone"] == 2500.1
        assert signals[0]["symbol"] == "XAUUSD"
        assert signals[0]["status"] == "ACTIVE"
    finally:
        YarTraderStorageManager.reset()


def test_signal_api_rejects_brain_only_candidate_without_resurrecting_older_active_signal(tmp_path, monkeypatch):
    monkeypatch.setenv("YarTraderStorageRoot", str(tmp_path))
    monkeypatch.delenv("TradeYarStorageRoot", raising=False)
    snapshot_dir = tmp_path / "Runtime" / "research_logs" / "research_snapshots"
    os.makedirs(snapshot_dir, exist_ok=True)
    YarTraderStorageManager.reset()
    try:
        now = datetime.now(timezone.utc)
        candidate = {
            "report_id": "candidate-current",
            "symbol": "XAUUSD", "timeframe": "H1", "timestamp": now.isoformat(),
            "findings": {
                "autonomous_decision": {"decision_id": "candidate-current", "action": "WAIT", "confidence": 0.0, "reasoning": []},
                "intel_summary": {"plan": {"action": "WAIT", "brain_suggested_action": "SELL", "brain_report_consumed": True}},
                "newborn_brain_report": {"active_hypotheses": [{"suggested_virtual_action": "SELL", "hypothesis_confidence": 72.44, "evidence_status": "VALIDATED_OUTCOMES", "successful_outcomes": 3, "failed_outcomes": 1, "trade_parameters": {}}]},
            },
        }
        older_active = {
            "report_id": "older-active",
            "symbol": "XAUUSD", "timeframe": "H1", "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "findings": {"autonomous_decision": {"decision_id": "older-active", "action": "BUY", "entry": 2500.0, "stop_loss": 2490.0, "take_profit": 2520.0, "risk_reward": 2.0, "confidence": 80.0}},
        }
        current_path = snapshot_dir / "rpt-XAUUSD-H1-snapshot_2000000002.json"
        older_path = snapshot_dir / "rpt-XAUUSD-H1-snapshot_2000000001.json"
        current_path.write_text(json.dumps(candidate), encoding="utf-8")
        older_path.write_text(json.dumps(older_active), encoding="utf-8")
        old_epoch = now.timestamp() - 600
        os.utime(older_path, (old_epoch, old_epoch))

        from src.Application.Services.user_api_router import _snapshot_signals
        signals = _snapshot_signals()
        # The latest Brain-only WAIT snapshot suppresses older signals; it may not
        # synthesize a customer-facing SELL candidate from a learned hypothesis.
        assert signals == []
    finally:
        YarTraderStorageManager.reset()


def test_hypothesis_blocks_failure_only_patterns_despite_directional_consensus(monkeypatch):
    from types import SimpleNamespace
    from src.Research.Brain.discovery import PatternDiscoveryEngine
    from src.Research.Brain.hypothesis import HypothesisEngine
    from src.Research.Brain.live_brain import LiveAnalysisBrain
    from src.Research.Brain.models import PatternMemory

    failed_sell = PatternMemory(
        pattern_id="failed-sell", sequence_signature=[1.0], occurrences_count=3,
        continuation_count=0, reversal_count=3,
        outcomes=[{"predicted_action": "SELL", "outcome": "FAILURE", "favorable_excursion": 5.0, "adverse_excursion": 2.0} for _ in range(3)],
        symbol="XAUUSD", timeframe="H1",
    )
    failed_buy = PatternMemory(
        pattern_id="failed-buy", sequence_signature=[1.0], occurrences_count=1,
        continuation_count=1, reversal_count=0,
        outcomes=[{"predicted_action": "BUY", "outcome": "FAILURE", "favorable_excursion": 5.0, "adverse_excursion": 2.0}],
        symbol="XAUUSD", timeframe="H1",
    )
    discovery = PatternDiscoveryEngine()
    matches = [(failed_sell, 0.9), (failed_buy, 0.8)]
    monkeypatch.setattr(discovery, "find_matches", lambda *args, **kwargs: matches)

    hypothesis = HypothesisEngine(discovery).formulate_hypothesis(
        current_signature=[1.0], historical_patterns=[failed_sell, failed_buy],
        symbol="XAUUSD", timeframe="H1",
    )
    assert hypothesis.expected_direction == "WAIT"
    assert hypothesis.confidence == 0.0
    assert hypothesis.meta["evidence_status"] == "FAILURE_ONLY"
    assert hypothesis.meta["blocked_direction"] == "BUY"
    assert hypothesis.meta["blocked_direction_confidence"] >= 70.0

    params = LiveAnalysisBrain._derive_learned_trade_parameters(
        None, SimpleNamespace(expected_direction="SELL", confidence=80.0), matches, 2500.0
    )
    assert params == {}


def test_learned_trade_parameters_require_three_successful_outcomes():
    from types import SimpleNamespace
    from src.Research.Brain.live_brain import LiveAnalysisBrain
    from src.Research.Brain.models import PatternMemory

    pattern = PatternMemory(
        pattern_id="successful-pattern", sequence_signature=[1.0], occurrences_count=3,
        continuation_count=3, reversal_count=0,
        outcomes=[{"predicted_action": "BUY", "outcome": "SUCCESS", "favorable_excursion": 6.0, "adverse_excursion": 2.0, "judge_vetted_accuracy": 1.0} for _ in range(3)],
        symbol="XAUUSD", timeframe="H1",
    )
    params = LiveAnalysisBrain._derive_learned_trade_parameters(
        None, SimpleNamespace(expected_direction="BUY", confidence=80.0), [(pattern, 0.9)], 2500.0
    )
    assert params["sample_size"] == 3
    assert params["risk_reward"] == 3.0
    assert params["entry"] == 2500.0


def _worker_with_demo_quote(monkeypatch, bid=2499.9, ask=2500.1):
    from app.workers.research_worker import ResearchWorker
    from src.Risk.Services.daily_loss_kill_switch import DailyLossKillSwitch

    kill_switch = DailyLossKillSwitch.get_instance()
    monkeypatch.setattr(kill_switch, "evaluate_daily_loss", lambda equity, **kwargs: (True, "OK", {"loss_pct": 0.0}))
    adapter = MagicMock()
    adapter.get_account_info.return_value = {
        "login": "52961173", "server": "Alpari-MT5-Demo",
        "balance": 100000.0, "equity": 100000.0, "free_margin": 100000.0
    }
    adapter.get_symbol_info.return_value = {
        "name": "XAUUSD", "digits": 2, "point": 0.01,
        "volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01,
        "trade_mode": 4
    }
    adapter.get_symbol_tick.return_value = {"bid": bid, "ask": ask}

    class _FakeMT5Profit:
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1

        @staticmethod
        def order_calc_profit(order_type, symbol, volume, entry, stop_loss):
            return -abs(float(entry) - float(stop_loss)) * 100.0 * float(volume)

    adapter._mt5 = _FakeMT5Profit()
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = SimpleNamespace(adapter=adapter)
    return worker


def test_demo_sizing_uses_broker_authoritative_stop_risk(monkeypatch):
    from src.Execution.Services.autonomous_demo_trader import calculate_demo_volume_by_risk

    class FakeMT5:
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1

        @staticmethod
        def order_calc_profit(order_type, symbol, volume, entry, stop_loss):
            return -abs(float(entry) - float(stop_loss)) * 100.0 * float(volume)

    sized = calculate_demo_volume_by_risk(
        FakeMT5(), "XAUUSD", "BUY", 2500.1, 2490.0,
        {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01},
        balance=100000.0, equity=100000.0, risk_pct=1.0,
    )
    assert sized["allowed"] is True
    assert sized["estimated_risk_usd"] <= sized["risk_budget_usd"]


def test_demo_sizing_blocks_crossed_pending_trigger(monkeypatch):
    from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader

    adapter = MagicMock()
    adapter.get_active_orders.return_value = []
    trader = AutonomousDemoTrader(adapter=adapter)
    now = int(datetime.now(timezone.utc).timestamp())
    plan = {
        "status": "ORDER_PROPOSAL",
        "order_plan": {
            "status": "PROPOSED", "direction": "BUY", "order_type": "BUY_LIMIT",
            "entry": 2500.3, "stop_loss": 2490.3, "take_profit": 2520.3,
            "expires_at": now + 300,
        },
    }
    result = trader._reconcile_base_pending_order(
        "XAUUSD", plan, {"bid": 2500.0, "ask": 2500.2, "time": now},
        {"balance": 100000.0, "equity": 100000.0}, {"digits": 2},
    )
    assert result["status"] == "BLOCKED"
    assert "trigger is no longer valid" in result["reason"]
    adapter.send_order_to_broker.assert_not_called()


def test_base_only_engine_does_not_bootstrap_live_brains(monkeypatch):
    from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine

    engine = PrimitiveMarketResearchEngine(data_provider=MagicMock(), base_engine=MagicMock())
    assert engine._live_brains == {}
    assert not hasattr(engine, "_select_brain_points")
    assert not hasattr(engine, "_get_live_brain")


def test_demo_order_check_failure_keeps_true_retcode_and_request_diagnostics(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from src.Execution.Models.models import OrderResponse
    from src.Execution.Services.demo_execution_engine import DemoExecutionEngine

    monkeypatch.setattr(
        "src.Execution.Services.demo_execution_engine.DemoExecutionGate.verify_demo_execution_eligibility",
        lambda **kwargs: None,
    )
    adapter = MagicMock()
    adapter.send_order_to_broker.return_value = OrderResponse(
        OrderId="0", Symbol="XAUUSD", Status="Failed",
        SubmittedAt=datetime.now(timezone.utc), Retcode=0,
        Comment="order_check failed retcode=10013",
        RawResponse={
            "retcode": 10013,
            "comment": "Invalid request",
            "trade_req": {
                "symbol": "XAUUSD", "type": 0, "volume": 0.01,
                "price": 2500.1, "sl": 2490.0, "tp": 2520.0,
                "deviation": 20, "type_filling": 0, "type_time": 0,
            },
        },
    )
    engine = DemoExecutionEngine(adapter=adapter, demo_mode=True, log_dir=str(tmp_path))
    response = engine.execute_demo_decision(
        "XAUUSD", "BUY", 0.01, price=2500.1, sl=2490.0, tp=2520.0,
        decision_id="diagnostic-test",
    )
    assert response.Status == "Failed"
    files = list(tmp_path.glob("demo_order_*.json"))
    assert len(files) == 1
    with open(files[0], encoding="utf-8") as handle:
        evidence = json.load(handle)
    assert evidence["order_check_retcode"] == 10013
    assert evidence["order_send_retcode"] is None
    assert evidence["retcode_classification"] == "INVALID_REQUEST"
    assert evidence["request_diagnostics"]["price"] == 2500.1
