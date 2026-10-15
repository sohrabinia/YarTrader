"""Unit tests for historical learning queue retry, failure classification, migration, and concurrency."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.workers.historical_learning_queue import (
    QueueLock,
    classify_failure,
    load_or_migrate_state,
    run_queue,
    save_state,
)


def test_transient_failure_followed_by_successful_retry(tmp_path):
    """1. A transient failure followed by a successful retry."""
    state_file = tmp_path / "state.json"
    lock_file = tmp_path / "queue.lock"
    symbols = ["EURUSD"]

    # First run fails transiently
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Temporary connection timeout", stdout="")
        st1 = run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
            backoff_sec=0.01,
        )

    assert st1["status"] == "RETRY_PENDING"
    assert st1["symbol_states"]["EURUSD"]["status"] == "RETRY_PENDING"
    assert st1["symbol_states"]["EURUSD"]["attempts"] == 1
    assert st1["counts"]["retryable_failed"] == 1
    assert st1["counts"]["succeeded"] == 0

    time.sleep(0.02)  # Wait for backoff to pass

    # Second run succeeds
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        st2 = run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
        )

    assert st2["status"] == "COMPLETED"
    assert st2["symbol_states"]["EURUSD"]["status"] == "COMPLETED"
    assert st2["symbol_states"]["EURUSD"]["attempts"] == 2
    assert st2["counts"]["succeeded"] == 1
    assert "EURUSD" in st2["completed_symbols"]


def test_permanent_failure_never_counts_as_success(tmp_path):
    """2. A permanent failure that never counts as success."""
    state_file = tmp_path / "state.json"
    lock_file = tmp_path / "queue.lock"
    symbols = ["INVALID_SYM"]

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="No usable broker history for INVALID_SYM/M1", stdout="")
        st = run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
        )

    assert st["status"] == "COMPLETED_WITH_ERRORS"
    assert st["symbol_states"]["INVALID_SYM"]["status"] == "PERMANENTLY_FAILED"
    assert st["symbol_states"]["INVALID_SYM"]["failure_classification"] == "PERMANENT"
    assert st["counts"]["permanently_failed"] == 1
    assert st["counts"]["succeeded"] == 0
    assert "INVALID_SYM" not in st["completed_symbols"]
    assert "INVALID_SYM" in st["failed_symbols"]


def test_no_completed_state_when_required_symbol_unresolved(tmp_path):
    """3. No COMPLETED state when a required symbol remains unresolved."""
    state_file = tmp_path / "state.json"
    lock_file = tmp_path / "queue.lock"
    symbols = ["EURUSD", "GBPUSD"]

    # EURUSD succeeds, GBPUSD fails transiently
    def mock_subprocess(cmd, **kwargs):
        sym = cmd[3]
        if sym == "EURUSD":
            return MagicMock(returncode=0, stderr="", stdout="")
        return MagicMock(returncode=1, stderr="Network glitch", stdout="")

    with patch("subprocess.run", side_effect=mock_subprocess):
        st = run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
            backoff_sec=10.0,
        )

    assert st["status"] != "COMPLETED"
    assert st["status"] == "RETRY_PENDING"
    assert st["counts"]["succeeded"] == 1
    assert st["counts"]["retryable_failed"] == 1


def test_recovery_of_failed_symbol_on_later_run(tmp_path):
    """4. Recovery of a previously failed symbol on a later run."""
    state_file = tmp_path / "state.json"
    lock_file = tmp_path / "queue.lock"
    symbols = ["USDJPY"]

    # Run 1: Fails transiently
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Busy resource", stdout="")
        run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
            backoff_sec=0.01,
        )

    time.sleep(0.02)

    # Run 2: Retry succeeds
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        st2 = run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
        )

    assert st2["status"] == "COMPLETED"
    assert st2["symbol_states"]["USDJPY"]["status"] == "COMPLETED"
    assert st2["symbol_states"]["USDJPY"]["attempts"] == 2


def test_interruption_and_restart_with_safe_resume(tmp_path):
    """5. Interruption and restart with safe resume."""
    state_file = tmp_path / "state.json"
    lock_file = tmp_path / "queue.lock"
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]

    call_count = 0

    def mock_interrupted_run(cmd, **kwargs):
        nonlocal call_count
        call_count += 1
        sym = cmd[3]
        if sym == "EURUSD":
            return MagicMock(returncode=0, stderr="", stdout="")
        raise KeyboardInterrupt("Process interrupted")

    # Run 1: Interrupted at GBPUSD
    with pytest.raises(KeyboardInterrupt):
        with patch("subprocess.run", side_effect=mock_interrupted_run):
            run_queue(
                symbols_override=symbols,
                state_path=state_file,
                lock_path=lock_file,
                skip_signal_bridge=True,
            )

    # Run 2: Resume
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        st2 = run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
        )

    assert st2["status"] == "COMPLETED"
    # EURUSD was already completed in Run 1, so mock_run in Run 2 only executes for GBPUSD and USDJPY
    assert mock_run.call_count == 2


def test_no_duplicate_work_for_verified_complete_symbols(tmp_path):
    """6. No duplicate work for verified-complete symbols."""
    state_file = tmp_path / "state.json"
    lock_file = tmp_path / "queue.lock"
    symbols = ["EURUSD", "GBPUSD"]

    # Initial completion
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        st1 = run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
        )

    assert st1["status"] == "COMPLETED"

    # Subsequent run
    with patch("subprocess.run") as mock_run:
        st2 = run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
        )
        assert mock_run.call_count == 0

    assert st2["status"] == "COMPLETED"


def test_corrupted_state_surfaced_without_silent_reset(tmp_path):
    """7. Corrupted or partial state surfaced without silently resetting it."""
    state_file = tmp_path / "state.json"
    state_file.write_text("{ corrupted json payload ...", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        load_or_migrate_state(state_file, ["EURUSD"], 10)

    assert "Corrupted or unreadable queue state" in str(exc_info.value)
    # File content preserved
    assert state_file.read_text(encoding="utf-8") == "{ corrupted json payload ..."


def test_two_concurrent_instances_cannot_process_simultaneously(tmp_path):
    """8. Two concurrent instances cannot process the same queue simultaneously."""
    state_file = tmp_path / "state.json"
    lock_file = tmp_path / "queue.lock"

    # Simulate active process running with PID os.getppid()
    lock_file.write_text(
        json.dumps({"pid": os.getppid(), "acquired_at": "2026-10-11T00:00:00Z"}),
        encoding="utf-8",
    )

    with patch("subprocess.run") as mock_run:
        st2 = run_queue(
            symbols_override=["EURUSD"],
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
        )

    assert st2.get("status") == "LOCKED"
    assert mock_run.call_count == 0


def test_stale_lock_recovery(tmp_path):
    """8b. Stale lock from non-existent PID is automatically recovered."""
    lock_file = tmp_path / "queue.lock"
    lock_file.write_text(json.dumps({"pid": 9999999, "acquired_at": "2020-01-01T00:00:00Z"}), encoding="utf-8")

    lock = QueueLock(lock_file)
    assert lock.acquire() is True
    lock.release()


def test_migration_of_old_state_format_without_data_loss(tmp_path):
    """9. Migration of the old state format without data loss."""
    state_file = tmp_path / "state.json"
    old_state = {
        "schema": 1,
        "status": "FAILED",
        "years": 10,
        "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
        "completed_symbols": ["EURUSD"],
        "failed_symbol": "GBPUSD",
        "current_symbol": "GBPUSD",
    }
    state_file.write_text(json.dumps(old_state), encoding="utf-8")

    migrated = load_or_migrate_state(state_file, ["EURUSD", "GBPUSD", "USDJPY"], 10)

    assert migrated["schema"] == 2
    assert "EURUSD" in migrated["completed_symbols"]
    assert migrated["symbol_states"]["EURUSD"]["status"] == "COMPLETED"
    assert migrated["symbol_states"]["GBPUSD"]["status"] == "RETRY_PENDING"
    assert migrated["symbol_states"]["USDJPY"]["status"] == "PENDING"
    assert migrated["counts"]["succeeded"] == 1
    assert migrated["counts"]["retryable_failed"] == 1


def test_all_success_run_reaches_completed_with_accurate_counts(tmp_path):
    """10. An all-success run reaches COMPLETED with accurate counts."""
    state_file = tmp_path / "state.json"
    lock_file = tmp_path / "queue.lock"
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        st = run_queue(
            symbols_override=symbols,
            state_path=state_file,
            lock_path=lock_file,
            skip_signal_bridge=True,
        )

    assert st["status"] == "COMPLETED"
    assert len(st["completed_symbols"]) == 3
    assert st["counts"]["total"] == 3
    assert st["counts"]["succeeded"] == 3
    assert st["counts"]["skipped"] == 0
    assert st["counts"]["retryable_failed"] == 0
    assert st["counts"]["permanently_failed"] == 0
