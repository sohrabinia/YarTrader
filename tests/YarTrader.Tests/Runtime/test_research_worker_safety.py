import os
import math
import time
import pytest
from unittest.mock import MagicMock
from app.workers.research_worker import ResearchWorker
from src.Research.MarketAnalysis.Models.models import ResearchResult, ResearchRequest
from datetime import datetime

class DummyAdapter:
    def __init__(self, account_info=None, symbol_info=None):
        self._account_info = account_info or {
            "equity": 10000.0,
            "free_margin": 8000.0
        }
        self._symbol_info = symbol_info or {
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01
        }

    def get_account_info(self):
        return self._account_info

    def get_symbol_info(self, symbol):
        return self._symbol_info


class DummyDemoEngine:
    def __init__(self, adapter=None):
        self.adapter = adapter or DummyAdapter()
        self.execute_demo_decision = MagicMock()
        self.get_active_positions = MagicMock(return_value=[])


def create_mock_research_result(action="BUY", symbol="XAUUSD", timeframe="H1", entry=2300.0, sl=2290.0, tp=2320.0, rr=2.0, conf=80.0):
    req = ResearchRequest(Asset=symbol, StartTime=datetime.now(), EndTime=datetime.now())
    auto_dec = {
        "action": action,
        "symbol": symbol,
        "timeframe": timeframe,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "risk_reward": rr,
        "confidence": conf,
        "decision_id": "TEST-DEC-123"
    }
    return ResearchResult(
        Request=req,
        Findings={
            "autonomous_decision": auto_dec,
            "pipeline_outputs": {"technical_analysis": {"candles": [{"time": 123}]}}
        },
        ConfidenceScore=0.85,
        CreatedAt=datetime.now()
    )


def setup_worker_for_loop_test(monkeypatch, action="BUY"):
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1", interval_sec=0.1)
    mock_demo_engine = DummyDemoEngine()
    worker.demo_engine = mock_demo_engine

    mock_runtime = MagicMock()
    mock_health = MagicMock()
    mock_health.connected = True
    mock_health.server = "Demo-Server"
    mock_health.ping_ms = 10.0
    mock_runtime.provider.delegate.get_connection_health.return_value = mock_health

    res = create_mock_research_result(action=action)
    mock_runtime.run_once.return_value = res

    worker.runtimes[("XAUUSD", "H1")] = mock_runtime
    return worker, mock_demo_engine, mock_runtime


# --- 1. AUTONOMOUS EXECUTION GATE BEHAVIORAL TESTS ---

def test_autonomous_execution_disabled_prevents_dispatch(monkeypatch):
    for flag in [None, "false", "0", "no", "invalid", ""]:
        if flag is None:
            monkeypatch.delenv("AUTONOMOUS_DEMO_TRADING_ENABLED", raising=False)
        else:
            monkeypatch.setenv("AUTONOMOUS_DEMO_TRADING_ENABLED", flag)

        worker, mock_demo_engine, _ = setup_worker_for_loop_test(monkeypatch, action="BUY")
        worker.is_running = True

        monkeypatch.setattr(worker, "_get_active_matrix", lambda: [("XAUUSD", "H1", "Commodities", "MT5")])

        # Stop loop inside interval sleep
        monkeypatch.setattr(time, "sleep", lambda sec: setattr(worker, "is_running", False))
        worker._run_loop()

        # VERIFY PRODUCTION BOUNDARY: execute_demo_decision MUST NOT be called
        mock_demo_engine.execute_demo_decision.assert_not_called()


# --- 2. CONNECTION HEALTH GATE BEHAVIORAL TESTS ---

def test_unhealthy_connection_health_prevents_dispatch(monkeypatch):
    monkeypatch.setenv("AUTONOMOUS_DEMO_TRADING_ENABLED", "true")
    worker, mock_demo_engine, mock_runtime = setup_worker_for_loop_test(monkeypatch, action="BUY")

    # Mock connection health as disconnected
    mock_health = MagicMock()
    mock_health.connected = False
    mock_health.last_error = "MT5 terminal offline"
    mock_runtime.provider.delegate.get_connection_health.return_value = mock_health

    monkeypatch.setattr(worker, "_get_active_matrix", lambda: [("XAUUSD", "H1", "Commodities", "MT5")])
    worker.is_running = True

    # Stop loop inside interval sleep
    monkeypatch.setattr(time, "sleep", lambda sec: setattr(worker, "is_running", False))
    worker._run_loop()

    # VERIFY PRODUCTION BOUNDARY: Neither run_once nor execute_demo_decision called when health is offline
    mock_runtime.run_once.assert_not_called()
    mock_demo_engine.execute_demo_decision.assert_not_called()


def test_connection_health_exception_prevents_dispatch(monkeypatch):
    monkeypatch.setenv("AUTONOMOUS_DEMO_TRADING_ENABLED", "true")
    worker, mock_demo_engine, mock_runtime = setup_worker_for_loop_test(monkeypatch, action="BUY")

    mock_runtime.provider.delegate.get_connection_health.side_effect = RuntimeError("IPC failure")

    monkeypatch.setattr(worker, "_get_active_matrix", lambda: [("XAUUSD", "H1", "Commodities", "MT5")])
    worker.is_running = True

    # Stop loop inside interval sleep
    monkeypatch.setattr(time, "sleep", lambda sec: setattr(worker, "is_running", False))
    worker._run_loop()

    # VERIFY PRODUCTION BOUNDARY
    mock_runtime.run_once.assert_not_called()
    mock_demo_engine.execute_demo_decision.assert_not_called()


# --- 3. RUNTIME / ERROR SEMANTICS BEHAVIORAL TESTS ---

def test_runtime_exception_prevents_dispatch(monkeypatch):
    monkeypatch.setenv("AUTONOMOUS_DEMO_TRADING_ENABLED", "true")
    worker, mock_demo_engine, mock_runtime = setup_worker_for_loop_test(monkeypatch, action="BUY")

    # Force run_once to raise an exception
    mock_runtime.run_once.side_effect = ValueError("Intelligence processing failure")

    monkeypatch.setattr(worker, "_get_active_matrix", lambda: [("XAUUSD", "H1", "Commodities", "MT5")])
    worker.is_running = True

    # Stop loop inside exception handling sleep
    monkeypatch.setattr(time, "sleep", lambda sec: setattr(worker, "is_running", False))
    worker._run_loop()

    # VERIFY PRODUCTION BOUNDARY: Exception caught safely, state updated to RECOVERING, execution boundary NOT called
    assert worker.status in ["STOPPED", "RECOVERING"]
    mock_demo_engine.execute_demo_decision.assert_not_called()


# --- 4. SAFETY THRESHOLD CONFIGURATION BEHAVIORAL TESTS ---

def test_invalid_safety_thresholds_prevent_dispatch(monkeypatch):
    monkeypatch.setenv("AUTONOMOUS_DEMO_TRADING_ENABLED", "true")

    for bad_rr in ["invalid", "NaN", "-1.5", "0.0"]:
        monkeypatch.setenv("MINIMUM_RR", bad_rr)
        monkeypatch.setenv("MINIMUM_CONFIDENCE", "50.0")

        worker, mock_demo_engine, _ = setup_worker_for_loop_test(monkeypatch, action="BUY")
        worker.is_running = True

        monkeypatch.setattr(worker, "_get_active_matrix", lambda: [("XAUUSD", "H1", "Commodities", "MT5")])
        monkeypatch.setattr(time, "sleep", lambda sec: setattr(worker, "is_running", False))
        worker._run_loop()

        # VERIFY PRODUCTION BOUNDARY
        mock_demo_engine.execute_demo_decision.assert_not_called()

    monkeypatch.setenv("MINIMUM_RR", "1.5")
    for bad_conf in ["invalid", "NaN", "-50.0", "0.0"]:
        monkeypatch.setenv("MINIMUM_CONFIDENCE", bad_conf)

        worker, mock_demo_engine, _ = setup_worker_for_loop_test(monkeypatch, action="BUY")
        worker.is_running = True

        monkeypatch.setattr(worker, "_get_active_matrix", lambda: [("XAUUSD", "H1", "Commodities", "MT5")])
        monkeypatch.setattr(time, "sleep", lambda sec: setattr(worker, "is_running", False))
        worker._run_loop()

        # VERIFY PRODUCTION BOUNDARY
        mock_demo_engine.execute_demo_decision.assert_not_called()


# --- 5. REGISTRY FAILURE BEHAVIORAL TESTS ---

def test_registry_failure_prevents_dispatch(monkeypatch):
    monkeypatch.setenv("AUTONOMOUS_DEMO_TRADING_ENABLED", "true")
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    mock_demo_engine = DummyDemoEngine()
    worker.demo_engine = mock_demo_engine

    from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry
    mock_sr = MagicMock()
    mock_sr.get_all_registered.return_value = {}
    mock_sr.max_symbols = 30
    mock_sr.get_active_matrix.side_effect = RuntimeError("Registry lock error")
    monkeypatch.setattr(SymbolRegistry, "get_instance", lambda: mock_sr)

    # Executing _get_active_matrix returns empty list
    matrix = worker._get_active_matrix()
    assert matrix == []

    worker.is_running = True

    monkeypatch.setattr(time, "sleep", lambda sec: setattr(worker, "is_running", False))
    worker._run_loop()

    # VERIFY PRODUCTION BOUNDARY
    mock_demo_engine.execute_demo_decision.assert_not_called()


# --- 6. EXISTING UNIT / SIZING TESTS ---

def test_missing_risk_config_defaults_to_0_5(monkeypatch):
    monkeypatch.delenv("RISK_PCT_PER_TRADE", raising=False)
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is not None
    assert res["equity"] == 10000.0
    assert res["risk_budget_usd"] == 50.0
    assert res["volume_lots"] > 0


def test_exceeding_max_risk_ceiling_blocked(monkeypatch):
    monkeypatch.setenv("RISK_PCT_PER_TRADE", "2.5")
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is None


def test_valid_buy_tp_accepted():
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is not None
    assert res["tp"] == 2320.0


def test_invalid_buy_tp_rejected():
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2295.0}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is None


def test_valid_sell_tp_accepted():
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()
    dec = {"entry": 2300.0, "stop_loss": 2310.0, "take_profit": 2280.0}
    res = worker._validate_and_size_decision("XAUUSD", "SELL", dec)
    assert res is not None
    assert res["tp"] == 2280.0


def test_invalid_sell_tp_rejected():
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()
    dec = {"entry": 2300.0, "stop_loss": 2310.0, "take_profit": 2305.0}
    res = worker._validate_and_size_decision("XAUUSD", "SELL", dec)
    assert res is None


def test_missing_tp_rejected():
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": None}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is None


def test_nan_or_infinite_tp_rejected():
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()
    for bad_tp in [float("nan"), float("inf"), float("-inf")]:
        dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": bad_tp}
        res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
        assert res is None
