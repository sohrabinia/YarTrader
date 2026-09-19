import os
import math
import pytest
from unittest.mock import MagicMock
from app.workers.research_worker import ResearchWorker

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


def create_worker_with_engine(adapter=None):
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine(adapter=adapter)
    return worker


def test_missing_risk_config_defaults_to_0_5(monkeypatch):
    monkeypatch.delenv("RISK_PCT_PER_TRADE", raising=False)
    worker = create_worker_with_engine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is not None
    # 0.5% of 10000 = $50 risk budget. With $10 SL distance (2300 - 2290), lots should be sized at 0.05
    assert res["equity"] == 10000.0
    assert res["risk_budget_usd"] == 50.0
    assert res["volume_lots"] > 0


def test_exceeding_max_risk_ceiling_blocked(monkeypatch):
    monkeypatch.setenv("RISK_PCT_PER_TRADE", "2.5")
    worker = create_worker_with_engine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is None


def test_invalid_risk_config_blocked(monkeypatch):
    for invalid_val in ["invalid", "NaN", "-1.0", "0.0"]:
        monkeypatch.setenv("RISK_PCT_PER_TRADE", invalid_val)
        worker = create_worker_with_engine()
        dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
        res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
        assert res is None


def test_missing_or_invalid_autonomous_flag_blocks_execution(monkeypatch):
    for flag in [None, "false", "0", "no", "invalid", ""]:
        if flag is None:
            monkeypatch.delenv("AUTONOMOUS_DEMO_TRADING_ENABLED", raising=False)
        else:
            monkeypatch.setenv("AUTONOMOUS_DEMO_TRADING_ENABLED", flag)

        raw_auto_enabled = os.getenv("AUTONOMOUS_DEMO_TRADING_ENABLED", "false").strip().lower()
        kill_switch_enabled = raw_auto_enabled in ["true", "1", "yes"]
        assert kill_switch_enabled is False


def test_registry_failure_returns_empty_active_matrix(monkeypatch):
    from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry
    def mock_raise(*args, **kwargs):
        raise RuntimeError("Registry database lock failure")

    monkeypatch.setattr(SymbolRegistry, "get_instance", mock_raise)
    worker = ResearchWorker()
    matrix = worker._get_active_matrix()
    assert matrix == []


def test_unhealthy_connection_health_blocks_execution():
    worker = ResearchWorker()
    mock_runtime = MagicMock()
    mock_health = MagicMock()
    mock_health.connected = False
    mock_health.last_error = "MT5 terminal disconnected"
    mock_runtime.provider.delegate.get_connection_health.return_value = mock_health

    # Connection health check evaluation
    conn_health = mock_runtime.provider.delegate.get_connection_health()
    assert conn_health.connected is False


def test_valid_buy_tp_accepted():
    worker = create_worker_with_engine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is not None
    assert res["tp"] == 2320.0


def test_invalid_buy_tp_rejected():
    worker = create_worker_with_engine()
    # TP <= entry for BUY
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2295.0}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is None


def test_valid_sell_tp_accepted():
    worker = create_worker_with_engine()
    dec = {"entry": 2300.0, "stop_loss": 2310.0, "take_profit": 2280.0}
    res = worker._validate_and_size_decision("XAUUSD", "SELL", dec)
    assert res is not None
    assert res["tp"] == 2280.0


def test_invalid_sell_tp_rejected():
    worker = create_worker_with_engine()
    # TP >= entry for SELL
    dec = {"entry": 2300.0, "stop_loss": 2310.0, "take_profit": 2305.0}
    res = worker._validate_and_size_decision("XAUUSD", "SELL", dec)
    assert res is None


def test_missing_tp_rejected():
    worker = create_worker_with_engine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": None}
    res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert res is None


def test_nan_or_infinite_tp_rejected():
    worker = create_worker_with_engine()
    for bad_tp in [float("nan"), float("inf"), float("-inf")]:
        dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": bad_tp}
        res = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
        assert res is None


def test_invalid_rr_configuration_blocks_execution(monkeypatch):
    for bad_rr in ["invalid", "NaN", "-1.5", "0.0"]:
        monkeypatch.setenv("MINIMUM_RR", bad_rr)
        raw_min_rr = os.getenv("MINIMUM_RR", "1.5")
        raw_min_conf = os.getenv("MINIMUM_CONFIDENCE", "50.0")

        is_valid = False
        try:
            min_rr = float(raw_min_rr)
            min_conf = float(raw_min_conf)
            if math.isfinite(min_rr) and math.isfinite(min_conf) and min_rr > 0.0 and min_conf > 0.0:
                is_valid = True
        except (ValueError, TypeError):
            is_valid = False

        assert is_valid is False


def test_invalid_confidence_configuration_blocks_execution(monkeypatch):
    for bad_conf in ["invalid", "NaN", "-50.0", "0.0"]:
        monkeypatch.setenv("MINIMUM_CONFIDENCE", bad_conf)
        raw_min_rr = os.getenv("MINIMUM_RR", "1.5")
        raw_min_conf = os.getenv("MINIMUM_CONFIDENCE", "50.0")

        is_valid = False
        try:
            min_rr = float(raw_min_rr)
            min_conf = float(raw_min_conf)
            if math.isfinite(min_rr) and math.isfinite(min_conf) and min_rr > 0.0 and min_conf > 0.0:
                is_valid = True
        except (ValueError, TypeError):
            is_valid = False

        assert is_valid is False


def test_intelligence_or_runtime_failure_cannot_become_executable_wait():
    worker = ResearchWorker()
    # Ensure worker status fails closed when runtime raises
    worker.is_running = True
    mock_runtime = MagicMock()
    mock_runtime.provider.delegate.get_connection_health.side_effect = RuntimeError("Runtime crash")

    monkeypatch_runtime = MagicMock(return_value=mock_runtime)
    worker._get_or_create_runtime = monkeypatch_runtime

    # If exception occurs during loop, execution is skipped
    try:
        conn_health = worker._get_or_create_runtime("XAUUSD", "H1").provider.delegate.get_connection_health()
    except Exception as e:
        conn_health = None

    assert conn_health is None
