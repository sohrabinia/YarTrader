import pytest

from app.workers import historical_learning_queue as queue


def test_primary_symbol_override_is_respected_and_xauusd_is_prioritized(monkeypatch):
    monkeypatch.setenv("YARTRADER_HISTORICAL_LEARNING_SYMBOLS", "EURUSD, XAUUSD")
    assert queue.load_symbols() == ["XAUUSD", "EURUSD"]


def test_symbol_override_cannot_expand_authorized_demo_universe(monkeypatch):
    monkeypatch.setenv("YARTRADER_HISTORICAL_LEARNING_SYMBOLS", "XAUUSD, GBPUSD")
    with pytest.raises(ValueError, match="restricted to authorized DEMO symbols"):
        queue.load_symbols()


def test_empty_symbol_override_falls_back_to_config(monkeypatch):
    monkeypatch.delenv("YARTRADER_HISTORICAL_LEARNING_SYMBOLS", raising=False)
    monkeypatch.setattr(queue, "CONFIG", type("Config", (), {
        "read_text": lambda self, encoding=None: '{"symbols": ["EURUSD", "XAUUSD"]}'
    })())
    assert queue.load_symbols() == ["XAUUSD", "EURUSD"]


def test_history_queue_accepts_only_authorized_demo_heartbeat(monkeypatch):
    demo = {"login": "252031952", "server": "Alpari-Pro.ECN-Demo", "is_demo": True}
    monkeypatch.setattr(queue.glob, "glob", lambda pattern: ["common-files"])
    monkeypatch.setattr(queue, "MT4FileBridge", lambda common_dir=None: type("Bridge", (), {"heartbeat": lambda self: demo})())
    bridge = queue._wait_for_demo_bridge(poll_sec=0)
    assert bridge is not None


def test_history_queue_rejects_signal_or_wrong_server_heartbeat(monkeypatch):
    invalid = {"login": "143056202", "server": "Alpari-Pro.ECN", "is_demo": False}
    monkeypatch.setattr(queue.glob, "glob", lambda pattern: ["common-files"])
    monkeypatch.setattr(queue, "MT4FileBridge", lambda common_dir=None: type("Bridge", (), {"heartbeat": lambda self: invalid})())
    def stop_waiting(_seconds):
        raise TimeoutError("no authorized DEMO heartbeat")
    monkeypatch.setattr(queue.time, "sleep", stop_waiting)
    with pytest.raises(TimeoutError, match="no authorized DEMO heartbeat"):
        queue._wait_for_demo_bridge(poll_sec=0)


import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


def _fake_worker_success(*args, **kwargs):
    return SimpleNamespace(returncode=0, stdout="ok", stderr="")


def _configure_queue_run(monkeypatch, tmp_path, symbols):
    monkeypatch.setattr(queue, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "load_symbols", lambda: list(symbols))
    monkeypatch.setattr(queue, "_wait_for_demo_bridge", lambda: object())
    monkeypatch.setattr(queue.time, "sleep", lambda _seconds: None)
    return tmp_path / "runtime_logs" / "backtest_learning" / "historical_queue_state.json"


def test_schema1_migration_preserves_completed_and_failed_symbols(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({
        "schema": 1, "status": "FAILED", "years": 10,
        "symbols": ["XAUUSD", "EURUSD"],
        "completed_symbols": ["XAUUSD"], "failed_symbols": ["EURUSD"],
    }))
    migrated = queue.load_or_migrate_state(path)
    assert migrated["schema"] == 2
    assert migrated["symbol_states"]["XAUUSD"]["status"] == "COMPLETED"
    assert migrated["symbol_states"]["EURUSD"]["status"] == "RETRY_PENDING"
    assert set(migrated["symbol_states"]) == {"XAUUSD", "EURUSD"}


def test_corrupted_state_raises_without_silent_reset(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not valid json")
    with pytest.raises(ValueError, match="refusing silent reset"):
        queue.load_or_migrate_state(path)
    assert path.read_text() == "{not valid json"


def test_atomic_save_retains_previous_json_backup(tmp_path):
    path = tmp_path / "state.json"
    first = {"schema": 2, "status": "COMPLETED", "symbols": ["XAUUSD"],
             "symbol_states": {"XAUUSD": queue._new_symbol_state("COMPLETED")}}
    queue.save_state(first, path)
    second = {"schema": 2, "status": "FAILED", "symbols": ["XAUUSD"],
              "symbol_states": {"XAUUSD": queue._new_symbol_state("FAILED")}}
    queue.save_state(second, path)
    assert json.loads(path.read_text())["status"] == "FAILED"
    assert json.loads(path.with_suffix(".json.bak").read_text())["status"] == "COMPLETED"
    assert not path.with_suffix(".json.tmp").exists()


def test_failure_classification_distinguishes_permanent_and_transient():
    assert queue.classify_failure("No usable broker history for XAUUSD") == queue.PERMANENT_FAILURE
    assert queue.classify_failure("network timeout while reading history") == queue.TRANSIENT_FAILURE
    assert queue.classify_failure(ValueError("invalid schema")) == queue.PERMANENT_FAILURE


def test_queue_lock_blocks_second_process_lock_and_releases_cleanly(tmp_path):
    path = tmp_path / ".queue.lock"
    first = queue.QueueLock(path)
    second = queue.QueueLock(path)
    assert first.acquire() is True
    try:
        assert second.acquire() is False
    finally:
        first.release()
    assert second.acquire() is True
    second.release()


def test_queue_lock_recovers_stale_dead_pid(tmp_path):
    path = tmp_path / ".queue.lock"
    path.write_text("99999999\n")
    lock = queue.QueueLock(path)
    assert lock.pid_is_alive(99999999) is False
    assert lock.acquire() is True
    lock.release()


def test_transient_failure_retries_and_then_completes(monkeypatch, tmp_path):
    state_path = _configure_queue_run(monkeypatch, tmp_path, ["XAUUSD"])
    calls = []
    def fake_run(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return SimpleNamespace(returncode=1, stdout="", stderr="network timeout")
        return _fake_worker_success()
    monkeypatch.setattr(queue.subprocess, "run", fake_run)
    state = queue.run_queue(max_retries=3, backoff_sec=0)
    assert len(calls) == 2
    assert state["status"] == "COMPLETED"
    assert state["symbol_states"]["XAUUSD"]["attempts"] == 2
    assert json.loads(state_path.read_text())["counts"]["succeeded"] == 1


def test_transient_failure_is_bounded_and_remains_retryable(monkeypatch, tmp_path):
    state_path = _configure_queue_run(monkeypatch, tmp_path, ["XAUUSD"])
    calls = []
    def fake_run(*args, **kwargs):
        calls.append(1)
        return SimpleNamespace(returncode=1, stdout="", stderr="network timeout")
    monkeypatch.setattr(queue.subprocess, "run", fake_run)
    state = queue.run_queue(max_retries=3, backoff_sec=0)
    assert len(calls) == 3
    assert state["status"] == "RETRY_PENDING"
    assert state["symbol_states"]["XAUUSD"]["attempts"] == 3
    assert state["symbol_states"]["XAUUSD"]["next_retry_at"]


def test_permanent_failure_does_not_block_later_symbols(monkeypatch, tmp_path):
    _configure_queue_run(monkeypatch, tmp_path, ["BAD", "GOOD"])
    def fake_run(cmd, **kwargs):
        symbol = cmd[cmd.index("--symbol") + 1]
        if symbol == "BAD":
            return SimpleNamespace(returncode=1, stdout="", stderr="invalid symbol")
        return _fake_worker_success()
    monkeypatch.setattr(queue.subprocess, "run", fake_run)
    state = queue.run_queue(max_retries=3, backoff_sec=0)
    assert state["symbol_states"]["BAD"]["status"] == "FAILED"
    assert state["symbol_states"]["BAD"]["attempts"] == 1
    assert state["symbol_states"]["GOOD"]["status"] == "COMPLETED"
    assert state["status"] == "COMPLETED_WITH_ERRORS"
    assert state["counts"]["permanently_failed"] == 1
    assert state["counts"]["succeeded"] == 1


def test_completed_symbols_are_not_processed_twice(monkeypatch, tmp_path):
    state_path = _configure_queue_run(monkeypatch, tmp_path, ["XAUUSD"])
    initial = {"schema": 2, "status": "COMPLETED", "years": 10, "symbols": ["XAUUSD"],
               "completed_symbols": ["XAUUSD"], "failed_symbols": [],
               "symbol_states": {"XAUUSD": queue._new_symbol_state("COMPLETED", attempts=1)}}
    queue.save_state(initial, state_path)
    monkeypatch.setattr(queue.subprocess, "run", lambda *a, **k: pytest.fail("completed symbol reran"))
    state = queue.run_queue(years=10)
    assert state["status"] == "COMPLETED"
    assert state["symbol_states"]["XAUUSD"]["attempts"] == 1


def test_later_run_recovers_due_retry_pending_symbol(monkeypatch, tmp_path):
    state_path = _configure_queue_run(monkeypatch, tmp_path, ["XAUUSD"])
    old = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    initial = {"schema": 2, "status": "RETRY_PENDING", "years": 10, "symbols": ["XAUUSD"],
               "symbol_states": {"XAUUSD": queue._new_symbol_state(
                   "RETRY_PENDING", attempts=1, last_error="timeout",
                   failure_classification=queue.TRANSIENT_FAILURE, next_retry_at=old)}}
    queue.save_state(initial, state_path)
    monkeypatch.setattr(queue.subprocess, "run", _fake_worker_success)
    state = queue.run_queue(years=10)
    assert state["symbol_states"]["XAUUSD"]["status"] == "COMPLETED"
    assert state["symbol_states"]["XAUUSD"]["attempts"] == 2


def test_counts_and_terminal_state_are_truthful_for_mixed_results(monkeypatch, tmp_path):
    _configure_queue_run(monkeypatch, tmp_path, ["OK", "BAD"])
    def fake_run(cmd, **kwargs):
        if cmd[cmd.index("--symbol") + 1] == "BAD":
            return SimpleNamespace(returncode=1, stdout="", stderr="invalid symbol")
        return _fake_worker_success()
    monkeypatch.setattr(queue.subprocess, "run", fake_run)
    state = queue.run_queue(max_retries=1, backoff_sec=0)
    assert state["status"] == "COMPLETED_WITH_ERRORS"
    assert state["counts"] == {
        "total": 2, "succeeded": 1, "skipped": 0,
        "retryable_failed": 0, "permanently_failed": 1,
    }
