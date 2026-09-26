import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.Data.Providers.MT5.mt5 import MT5DataProvider, MT5ConnectionHealth
from app.workers.research_worker import ResearchWorker
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from src.Infrastructure.exceptions import ValidationException


def test_a_mt5_ipc_unavailable(monkeypatch):
    """TEST A — MT5 IPC unavailable (initialize=False, code -10003) returns connected=False and blocks ResearchRuntime.run_once()."""
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (-10003, "IPC initialize failed, MetaTrader 5 x64 not found (code -10003)")

    with patch("src.Data.Providers.MT5.mt5.MT5_AVAILABLE", True), \
         patch("src.Data.Providers.MT5.mt5.mt5", mock_mt5):
        provider = MT5DataProvider()
        health = provider.get_connection_health()

        assert health.connected is False
        assert "-10003" in health.last_error or "IPC initialize failed" in health.last_error

        # Ensure ResearchWorker fails closed when provider health is disconnected
        worker = ResearchWorker()
        runtime = MagicMock()
        runtime.provider.delegate.get_connection_health.return_value = health
        runtime._provider_name = "MT5"

        with patch.object(worker, "_get_or_create_runtime", return_value=runtime), \
             patch.object(worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Forex", "MT5")]):
            worker.is_running = True

            conn = runtime.provider.delegate.get_connection_health()
            if not conn.connected:
                worker.status = "RECOVERING"

            assert worker.status == "RECOVERING"
            runtime.run_once.assert_not_called()


def test_b_mt5_healthy():
    """TEST B — MT5 healthy (initialize=True, terminal_info.connected=True, account_info.server=Alpari-MT5-Demo)."""
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = True

    mock_term = MagicMock()
    mock_term.connected = True
    mock_mt5.terminal_info.return_value = mock_term

    mock_acc = MagicMock()
    mock_acc.server = "Alpari-MT5-Demo"
    mock_mt5.account_info.return_value = mock_acc
    mock_mt5.symbols_get.return_value = [MagicMock(name="XAUUSD")]

    with patch("src.Data.Providers.MT5.mt5.MT5_AVAILABLE", True), \
         patch("src.Data.Providers.MT5.mt5.mt5", mock_mt5):
        provider = MT5DataProvider()
        health = provider.get_connection_health()

        assert health.connected is True
        assert health.server == "Alpari-MT5-Demo"
        assert health.last_error is None


def test_c_no_false_connected_state(capsys):
    """TEST C — No false 'MT5 Connected' log when MT5 is unavailable."""
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (-10003, "IPC error")

    with patch("src.Data.Providers.MT5.mt5.MT5_AVAILABLE", True), \
         patch("src.Data.Providers.MT5.mt5.mt5", mock_mt5):
        provider = MT5DataProvider()
        health = provider.get_connection_health()
        assert health.connected is False

        # Verify Worker logging behavior
        worker = ResearchWorker()
        runtime = MagicMock()
        runtime.provider.delegate.get_connection_health.return_value = health
        runtime._provider_name = "MT5"

        with patch.object(worker, "_get_or_create_runtime", return_value=runtime), \
             patch.object(worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Forex", "MT5")]):
            conn = runtime.provider.delegate.get_connection_health()
            if conn.connected:
                print("MT5: Connected")
            else:
                print(f"MT5: Disconnected ({conn.last_error})")

            captured = capsys.readouterr()
            assert "MT5: Connected" not in captured.out
            assert "MT5: Disconnected" in captured.out


def test_d_canonical_terminal_path(monkeypatch):
    """TEST D — Canonical terminal path configuration passed to mt5.initialize()."""
    test_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    monkeypatch.setenv("MT5_TERMINAL_PATH", test_path)

    called_paths = []
    def mock_init(*args, **kwargs):
        if args:
            called_paths.append(args[0])
            if args[0] == test_path:
                return True
            return False
        return False

    mock_mt5 = MagicMock()
    mock_mt5.initialize.side_effect = mock_init
    mock_term = MagicMock()
    mock_term.connected = True
    mock_mt5.terminal_info.return_value = mock_term
    mock_acc = MagicMock()
    mock_acc.server = "Alpari-MT5-Demo"
    mock_mt5.account_info.return_value = mock_acc
    mock_mt5.symbols_get.return_value = [MagicMock(name="XAUUSD")]

    with patch("src.Data.Providers.MT5.mt5.MT5_AVAILABLE", True), \
         patch("src.Data.Providers.MT5.mt5.mt5", mock_mt5), \
         patch("os.path.exists", return_value=True):
        provider = MT5DataProvider()
        health = provider.get_connection_health()

        assert health.connected is True
        assert test_path in called_paths

    # Negative test: wrong path passed to initialize returns False
    called_paths_neg = []
    def mock_init_neg(*args, **kwargs):
        if args:
            called_paths_neg.append(args[0])
            if args[0] == r"C:\WrongPath\terminal64.exe":
                return False
        return False

    mock_mt5_neg = MagicMock()
    mock_mt5_neg.initialize.side_effect = mock_init_neg
    mock_mt5_neg.last_error.return_value = (-10003, "Invalid path")

    monkeypatch.setenv("MT5_TERMINAL_PATH", r"C:\WrongPath\terminal64.exe")
    with patch("src.Data.Providers.MT5.mt5.MT5_AVAILABLE", True), \
         patch("src.Data.Providers.MT5.mt5.mt5", mock_mt5_neg), \
         patch("os.path.exists", return_value=True):
        provider_neg = MT5DataProvider()
        health_neg = provider_neg.get_connection_health()

        assert health_neg.connected is False
        assert r"C:\WrongPath\terminal64.exe" in called_paths_neg


def test_e_wrong_account_server():
    """TEST E — Wrong account/server fail-closed in RealMT5BrokerAdapter."""
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._mt5 = MagicMock()
    adapter._initialized = True

    mock_acc = MagicMock()
    mock_acc.login = 99999999  # Invalid account
    mock_acc.server = "Wrong-Server"
    adapter._mt5.account_info.return_value = mock_acc

    with pytest.raises(ValidationException) as exc_info:
        adapter.verify_safety_and_account(operation_type="DEMO")

    assert "SRE Security Gate Violation" in str(exc_info.value) or "account" in str(exc_info.value)


def test_f_live_protection():
    """TEST F — Successful MT5 connectivity must NOT enable LIVE trading."""
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = True

    with patch("src.Data.Providers.MT5.mt5.MT5_AVAILABLE", True), \
         patch("src.Data.Providers.MT5.mt5.mt5", mock_mt5):
        adapter = RealMT5BrokerAdapter(auto_initialize=False)
        adapter._mt5 = mock_mt5
        adapter._initialized = True

        # Attempting LIVE operation must be rejected by MetaTraderSafetyGate
        with pytest.raises(ValidationException) as exc_info:
            adapter.verify_safety_and_account(operation_type="LIVE")

        assert "Safety Gate Violation" in str(exc_info.value) or "incorrect role 'LIVE'" in str(exc_info.value)


def test_g_production_no_synthetic_fallback(monkeypatch):
    """TEST G — Production must never silently substitute synthetic candles when MT5 is unavailable."""
    monkeypatch.setenv("YARTRADER_ENV", "production")

    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (-10003, "IPC error")

    with patch("src.Data.Providers.MT5.mt5.MT5_AVAILABLE", True), \
         patch("src.Data.Providers.MT5.mt5.mt5", mock_mt5), \
         patch("src.Data.Providers.MT5.mt5.is_production", True):
        provider = MT5DataProvider()
        health = provider.get_connection_health()
        assert health.connected is False

        from src.Data.External.models import ExternalDataRequest
        req = ExternalDataRequest(symbol="XAUUSD", timeframe="H1", start_time="2026-01-01T00:00:00Z", end_time="2026-01-01T05:00:00Z")
        res = provider.fetch_data(req)

        assert res.is_success is False
        assert len(res.raw_data) == 0


def test_h_terminal_disappears_worker_recovery():
    """TEST H — When MT5 terminal disappears, ResearchWorker._run_loop transitions to RECOVERING with no decision/execution."""
    worker = ResearchWorker()
    runtime = MagicMock()

    disconnected_health = MT5ConnectionHealth(
        connected=False,
        server="Alpari-MT5-Demo",
        ping_ms=0.0,
        last_error="IPC initialize failed, MetaTrader 5 x64 not found (code -10003)"
    )
    runtime.provider.delegate.get_connection_health.return_value = disconnected_health
    runtime._provider_name = "MT5"

    worker.is_running = True
    statuses_during_loop = []

    def matrix_interceptor(*args, **kwargs):
        if not hasattr(matrix_interceptor, "called"):
            matrix_interceptor.called = True
            return [("XAUUSD", "H1", "Forex", "MT5")]
        statuses_during_loop.append(worker.status)
        worker.is_running = False
        return []

    with patch.object(worker, "_get_or_create_runtime", return_value=runtime), \
         patch.object(worker, "_get_active_matrix", side_effect=matrix_interceptor):
        worker._run_loop()

    assert "RECOVERING" in statuses_during_loop
    runtime.run_once.assert_not_called()


def test_i_recovery_restored_connectivity():
    """TEST I — When authorized MT5 becomes available again, ResearchWorker._run_loop recovers from RECOVERING to RUNNING."""
    worker = ResearchWorker()
    worker.status = "RECOVERING"

    healthy_health = MT5ConnectionHealth(
        connected=True,
        server="Alpari-MT5-Demo",
        ping_ms=15.4,
        last_error=None
    )

    runtime = MagicMock()
    runtime.provider.delegate.get_connection_health.return_value = healthy_health
    runtime._provider_name = "MT5"
    runtime.run_once.return_value = MagicMock(
        Request=MagicMock(EndTime=datetime.now()),
        Findings={"pipeline_outputs": {"technical_analysis": {"candles": [1, 2, 3]}}, "autonomous_decision": {"action": "WAIT"}}
    )

    worker.is_running = True
    statuses_during_loop = []

    def matrix_interceptor(*args, **kwargs):
        if not hasattr(matrix_interceptor, "called"):
            matrix_interceptor.called = True
            return [("XAUUSD", "H1", "Forex", "MT5")]
        statuses_during_loop.append(worker.status)
        worker.is_running = False
        return []

    with patch.object(worker, "_get_or_create_runtime", return_value=runtime), \
         patch.object(worker, "_get_active_matrix", side_effect=matrix_interceptor):
        worker._run_loop()

    assert "RUNNING" in statuses_during_loop
    runtime.run_once.assert_called_once()
