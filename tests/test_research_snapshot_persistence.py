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
                    "reasoning": ["unit-test"]
                }
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


def test_signal_api_surfaces_brain_candidate_without_resurrecting_older_active_signal(tmp_path, monkeypatch):
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
        assert len(signals) == 1
        assert signals[0]["direction"] == "SELL"
        assert signals[0]["status"] == "CANDIDATE"
        assert signals[0]["execution_action"] == "WAIT"
        assert signals[0]["entry_zone"] is None
        assert signals[0]["confidence"] == 72.44
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


def test_demo_sizing_uses_fresh_executable_quote(monkeypatch):
    monkeypatch.setenv("RISK_PCT_PER_TRADE", "1.0")
    monkeypatch.setenv("MAX_DEMO_ENTRY_DRIFT_PCT", "0.5")
    worker = _worker_with_demo_quote(monkeypatch)

    sized = worker._validate_and_size_decision(
        "XAUUSD", "BUY", {"entry": 2500.0, "stop_loss": 2490.0, "take_profit": 2520.0}
    )
    assert sized is not None
    assert sized["price"] == 2500.1
    assert sized["sl"] == 2490.0
    assert sized["tp"] == 2520.0
    assert 0 < sized["volume_lots"] <= 100


def test_demo_sizing_blocks_stale_model_entry(monkeypatch):
    monkeypatch.setenv("RISK_PCT_PER_TRADE", "1.0")
    monkeypatch.setenv("MAX_DEMO_ENTRY_DRIFT_PCT", "0.5")
    worker = _worker_with_demo_quote(monkeypatch, bid=4142.68, ask=4142.82)

    sized = worker._validate_and_size_decision(
        "XAUUSD", "BUY", {"entry": 2367.17, "stop_loss": 2363.42, "take_profit": 2375.42}
    )
    assert sized is None


def test_live_brain_bootstrap_is_bounded_and_subsequent_cycles_are_incremental(monkeypatch):
    from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine

    monkeypatch.setenv("YARTRADER_LIVE_BRAIN_BOOTSTRAP_BARS", "3")
    engine = PrimitiveMarketResearchEngine(data_provider=MagicMock(), base_engine=MagicMock())
    key = ("XAUUSD", "H1")
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    points = [SimpleNamespace(Timestamp=base + timedelta(hours=i)) for i in range(5)]

    bootstrap = engine._select_brain_points(key, points)
    assert bootstrap == points[-3:]
    engine._last_processed_candle_timestamps[key] = points[-1].Timestamp
    assert engine._select_brain_points(key, points) == []
    points.append(SimpleNamespace(Timestamp=base + timedelta(hours=5)))
    assert engine._select_brain_points(key, points) == [points[-1]]


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
