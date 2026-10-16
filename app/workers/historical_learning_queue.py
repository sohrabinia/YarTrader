"""Crash-safe, resumable historical-learning queue with bounded retries."""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.Execution.Adapters.mt4_file_bridge import MT4FileBridge

CONFIG = ROOT / "config" / "historical_learning_symbols.json"
DEFAULT_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")
SCHEMA_VERSION = 2
MAX_RETRIES = 3
BACKOFF_SEC = 5.0
PERMANENT_FAILURE = "PERMANENT"
TRANSIENT_FAILURE = "TRANSIENT"


def _state_path() -> Path:
    return ROOT / "runtime_logs" / "backtest_learning" / "historical_queue_state.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _parse_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def load_symbols():
    raw_override = os.getenv("YARTRADER_HISTORICAL_LEARNING_SYMBOLS", "").strip()
    if raw_override:
        symbols = raw_override.replace(";", ",").split(",")
    else:
        payload = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
        symbols = payload.get("symbols", [])
    result = []
    for symbol in symbols:
        symbol = str(symbol).strip().upper()
        if symbol and symbol not in result:
            result.append(symbol)
    if not result:
        raise RuntimeError("Historical learning queue is empty.")
    allowed = {"XAUUSD", "EURUSD"}
    disallowed = sorted(set(result) - allowed)
    if disallowed:
        raise ValueError(
            "Historical learning is restricted to authorized DEMO symbols XAUUSD/EURUSD; "
            f"rejected: {disallowed}"
        )
    if "XAUUSD" in result:
        result = ["XAUUSD", *[symbol for symbol in result if symbol != "XAUUSD"]]
    return result


def _new_symbol_state(status="PENDING", **extra):
    result = {
        "status": status,
        "attempts": 0,
        "last_error": None,
        "last_attempt_at": None,
        "next_retry_at": None,
        "failure_classification": None,
    }
    result.update(extra)
    return result


def _counts(state: dict, symbols: Optional[list[str]] = None) -> dict:
    names = list(symbols if symbols is not None else state.get("symbols", []))
    per_symbol = state.get("symbol_states", {})
    statuses = [per_symbol.get(name, {}).get("status", "PENDING") for name in names]
    return {
        "total": len(names),
        "succeeded": sum(status == "COMPLETED" for status in statuses),
        "skipped": sum(status == "SKIPPED" for status in statuses),
        "retryable_failed": sum(status == "RETRY_PENDING" for status in statuses),
        "permanently_failed": sum(status == "FAILED" for status in statuses),
    }


def save_state(state: dict, path: Optional[Path] = None):
    """Persist state atomically, retaining the last readable JSON as a backup."""
    p = Path(path) if path is not None else _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(state)
    payload["schema"] = SCHEMA_VERSION
    payload["updated_at"] = _iso_now()
    payload["counts"] = _counts(payload)
    tmp = p.with_suffix(p.suffix + ".tmp")
    backup = p.with_suffix(p.suffix + ".bak")
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if p.exists():
        # Do not replace the backup with unreadable state.
        try:
            json.loads(p.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            raise ValueError(f"Refusing to overwrite corrupted queue state: {p}")
        shutil.copy2(p, backup)
    os.replace(tmp, p)
    # Best-effort directory sync on platforms that support opening directories.
    try:
        fd = os.open(str(p.parent), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except (OSError, AttributeError):
        pass
    state.clear()
    state.update(payload)
    return payload


def load_or_migrate_state(path: Optional[Path] = None, symbols: Optional[list[str]] = None,
                          years: Optional[float] = None) -> dict:
    """Load Schema 2, or migrate Schema 1 without discarding historical symbol outcomes."""
    p = Path(path) if path is not None else _state_path()
    if not p.exists():
        return {
            "schema": SCHEMA_VERSION, "status": "WAITING_FOR_SIGNAL", "years": years,
            "symbols": list(symbols or []), "current_symbol": None, "current_index": None,
            "symbol_states": {s: _new_symbol_state() for s in (symbols or [])},
            "completed_symbols": [], "failed_symbols": [],
        }
    try:
        raw = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"Unable to read historical queue state at {p}; refusing silent reset: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid historical queue state at {p}: root must be an object")
    schema = raw.get("schema", 1)
    if schema not in (1, SCHEMA_VERSION):
        raise ValueError(f"Unsupported historical queue state schema {schema} at {p}")
    legacy_symbols = list(raw.get("symbols") or [])
    completed = set(raw.get("completed_symbols") or [])
    failed = set(raw.get("failed_symbols") or [])
    if schema == 1:
        states = {}
        for symbol in legacy_symbols:
            if symbol in completed:
                states[symbol] = _new_symbol_state("COMPLETED", failure_classification=None)
            elif symbol in failed:
                # Schema 1 did not retain failure type; allow a bounded recovery attempt.
                states[symbol] = _new_symbol_state(
                    "RETRY_PENDING", failure_classification="TRANSIENT_LEGACY",
                    last_error="Migrated legacy failed symbol; failure type was not recorded.",
                )
            else:
                states[symbol] = _new_symbol_state()
        raw["symbol_states"] = states
        raw["schema"] = SCHEMA_VERSION
    else:
        states = raw.get("symbol_states")
        if not isinstance(states, dict):
            raise ValueError(f"Invalid Schema 2 historical queue state at {p}: symbol_states must be an object")
        for symbol, item in states.items():
            if not isinstance(item, dict) or "status" not in item:
                raise ValueError(f"Invalid state record for {symbol} in {p}")
            defaults = _new_symbol_state()
            defaults.update(item)
            states[symbol] = defaults
        raw["symbol_states"] = states

    # Keep prior symbols and outcomes even if today's queue configuration changed.
    for symbol in symbols or []:
        raw["symbol_states"].setdefault(symbol, _new_symbol_state())
    raw["completed_symbols"] = sorted(
        symbol for symbol, item in raw["symbol_states"].items() if item.get("status") == "COMPLETED"
    )
    raw["failed_symbols"] = sorted(
        symbol for symbol, item in raw["symbol_states"].items() if item.get("status") == "FAILED"
    )
    if symbols is not None:
        raw["symbols"] = list(symbols)
    if years is not None:
        raw["years"] = years
    raw.setdefault("status", "WAITING_FOR_SIGNAL")
    raw.setdefault("current_symbol", None)
    raw.setdefault("current_index", None)
    raw["schema"] = SCHEMA_VERSION
    return raw


def classify_failure(error: Any) -> str:
    """Classify by domain meaning; missing history/config is permanent, infrastructure is transient."""
    message = str(error or "").lower()
    permanent_markers = (
        "no usable broker history", "invalid symbol", "unknown symbol",
        "unsupported symbol", "unsupported historical learning timeframes",
        "invalid timeframe", "schema error", "invalid schema", "format error",
        "historical learning queue is empty", "none of the configured timeframes",
    )
    transient_markers = (
        "timeout", "timed out", "temporarily unavailable", "connection reset",
        "network", "file is locked", "permission denied", "sharing violation",
        "bridge unavailable", "no authorized signal heartbeat", "connection error",
        "try again", "resource busy", "broken pipe",
    )
    if any(marker in message for marker in permanent_markers):
        return PERMANENT_FAILURE
    if any(marker in message for marker in transient_markers):
        return TRANSIENT_FAILURE
    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return TRANSIENT_FAILURE
    if isinstance(error, (ValueError, TypeError, KeyError, json.JSONDecodeError)):
        return PERMANENT_FAILURE
    # Unknown subprocess failures are retryable rather than silently treated as success.
    return TRANSIENT_FAILURE


class QueueLock:
    """Cross-platform process singleton lock; the OS releases the lock after process death."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.handle = None
        self.acquired = False

    @staticmethod
    def pid_is_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except PermissionError:
            return True
        except OSError:
            return False

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.handle = open(self.path, "r+b")
        except FileNotFoundError:
            try:
                self.handle = open(self.path, "x+b")
            except FileExistsError:
                self.handle = open(self.path, "r+b")
        self.handle.seek(0, os.SEEK_END)
        if self.handle.tell() < 64:
            self.handle.write(b" " * (64 - self.handle.tell()))
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            self.handle.close()
            self.handle = None
            return False
        self.acquired = True
        self.handle.seek(0)
        self.handle.write((str(os.getpid()) + "\n").encode("ascii")[:64].ljust(64, b" "))
        self.handle.flush()
        os.fsync(self.handle.fileno())
        return True

    def release(self):
        if not self.handle:
            return
        try:
            if self.acquired:
                self.handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None
            self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("Historical learning queue already active.")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()


def _try_acquire_windows_lock(path: Path):
    """Backward-compatible wrapper retained for callers that expect a lock handle."""
    lock = QueueLock(path)
    if not lock.acquire():
        return None
    return lock


def _wait_for_demo_bridge(poll_sec=5.0):
    while True:
        for common_dir in glob.glob(r"C:\Users\*\AppData\Roaming\MetaQuotes\Terminal\Common\Files"):
            bridge = MT4FileBridge(common_dir=common_dir)
            hb = bridge.heartbeat()
            # Historical acquisition is restricted to the authorized DEMO account.
            if (hb and str(hb.get("login", "")) == "252031952"
                    and hb.get("server") == "Alpari-Pro.ECN-Demo"
                    and hb.get("is_demo") is True):
                return bridge
        time.sleep(poll_sec)


def run_queue(years=10, initial_balance=10000.0, sleep_sec=0.5, max_symbols=0,
              max_retries: int = MAX_RETRIES, backoff_sec: float = BACKOFF_SEC):
    symbols = load_symbols()[:max_symbols or None]
    state_path = _state_path()
    # Load the stored configuration before applying today's arguments so we can
    # detect a changed horizon or symbol set without losing the old per-symbol record.
    state = load_or_migrate_state(state_path)
    previous_symbols = set(state.get("symbols", []))
    # Completed records from the same queue/config are reusable. A changed learning
    # horizon must rerun those symbols, while the old outcome remains in previous_run.
    same_config = state.get("years") == years and previous_symbols == set(symbols)
    for symbol in symbols:
        state["symbol_states"].setdefault(symbol, _new_symbol_state())
    if not same_config:
        for symbol in symbols:
            item = state["symbol_states"].setdefault(symbol, _new_symbol_state())
            if item.get("status") in ("COMPLETED", "FAILED", "RETRY_PENDING", "SKIPPED"):
                item["previous_run"] = {k: item.get(k) for k in (
                    "status", "attempts", "last_error", "last_attempt_at",
                    "next_retry_at", "failure_classification")}
                item.update(_new_symbol_state())
    state.update(schema=SCHEMA_VERSION, status="WAITING_FOR_DEMO",
                 years=years, symbols=symbols, current_symbol=None, current_index=None)
    save_state(state, state_path)

    now = _utc_now()
    eligible = []
    for symbol in symbols:
        item = state["symbol_states"].setdefault(symbol, _new_symbol_state())
        if item.get("status") == "COMPLETED" or item.get("status") == "FAILED":
            continue
        if item.get("status") == "RETRY_PENDING":
            due = _parse_time(item.get("next_retry_at"))
            if due and due > now:
                continue
        eligible.append(symbol)
    if not eligible:
        counts = _counts(state, symbols)
        if counts["retryable_failed"]:
            state["status"] = "RETRY_PENDING"
        elif counts["permanently_failed"]:
            state["status"] = "COMPLETED_WITH_ERRORS" if counts["succeeded"] else "FAILED"
        else:
            state["status"] = "COMPLETED"
        save_state(state, state_path)
        return state

    _wait_for_demo_bridge()
    worker = ROOT / "app" / "workers" / "historical_symbol_worker.py"
    for index, symbol in enumerate(symbols):
        item = state["symbol_states"][symbol]
        if symbol not in eligible:
            continue
        state["current_index"] = index
        state["current_symbol"] = symbol
        attempts_this_run = 0
        while True:
            item["attempts"] = int(item.get("attempts", 0)) + 1
            item["last_attempt_at"] = _iso_now()
            item["next_retry_at"] = None
            item["status"] = "RUNNING"
            state["status"] = "RUNNING"
            save_state(state, state_path)
            cmd = [sys.executable, str(worker), "--symbol", symbol, "--years", str(years),
                   "--initial-balance", str(initial_balance), "--sleep", str(sleep_sec)]
            try:
                result = subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)
                rc = result.returncode
                detail = (result.stderr or result.stdout or "").strip()[-1200:]
                error = None if rc == 0 else (detail or f"historical worker exited with code {rc}")
            except (OSError, subprocess.SubprocessError) as exc:
                rc = -1
                error = f"{type(exc).__name__}: {exc}"
            if rc == 0:
                item.update(status="COMPLETED", last_error=None, next_retry_at=None,
                            failure_classification=None, completed_at=_iso_now())
                state["completed_symbols"] = sorted(
                    set(state.get("completed_symbols", [])) | {symbol})
                state["failed_symbols"] = sorted(
                    set(state.get("failed_symbols", [])) - {symbol})
                state["current_symbol"] = None
                save_state(state, state_path)
                break

            classification = classify_failure(error)
            item["last_error"] = error
            item["failure_classification"] = classification
            attempts_this_run += 1
            if classification == PERMANENT_FAILURE:
                item.update(status="FAILED", next_retry_at=None, failed_at=_iso_now())
                state["failed_symbols"] = sorted(set(state.get("failed_symbols", [])) | {symbol})
                state["current_symbol"] = None
                save_state(state, state_path)
                break

            if attempts_this_run < max_retries and int(item["attempts"]) < max_retries:
                delay = max(0.0, float(backoff_sec)) * (2 ** max(0, attempts_this_run - 1))
                item["status"] = "RETRY_PENDING"
                item["next_retry_at"] = (_utc_now() + timedelta(seconds=delay)).isoformat()
                save_state(state, state_path)
                time.sleep(delay)
                continue

            delay = max(0.0, float(backoff_sec)) * (2 ** max(0, min(int(item["attempts"]) - 1, 20)))
            item["status"] = "RETRY_PENDING"
            item["next_retry_at"] = (_utc_now() + timedelta(seconds=delay)).isoformat()
            state["current_symbol"] = None
            save_state(state, state_path)
            break

    counts = _counts(state, symbols)
    if counts["retryable_failed"]:
        state["status"] = "RETRY_PENDING"
    elif counts["permanently_failed"]:
        state["status"] = "COMPLETED_WITH_ERRORS" if counts["succeeded"] else "FAILED"
    else:
        state["status"] = "COMPLETED"
    state["current_symbol"] = None
    state["current_index"] = None
    state["completed_symbols"] = sorted(
        symbol for symbol, item in state["symbol_states"].items() if item.get("status") == "COMPLETED")
    state["failed_symbols"] = sorted(
        symbol for symbol, item in state["symbol_states"].items() if item.get("status") == "FAILED")
    save_state(state, state_path)
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--initial-balance", type=float, default=10000.0)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES)
    parser.add_argument("--backoff-sec", type=float, default=BACKOFF_SEC)
    args = parser.parse_args()
    lock_root = Path(os.getenv("YARTRADER_HISTORICAL_LEARNING_ROOT",
                               "runtime_logs/backtest_learning/historical_queue"))
    lock = QueueLock(lock_root / ".queue.lock")
    if not lock.acquire():
        print("Historical learning queue already active; duplicate launch skipped.")
        return
    try:
        run_queue(args.years, args.initial_balance, args.sleep, args.max_symbols,
                  args.max_retries, args.backoff_sec)
    finally:
        lock.release()


if __name__ == "__main__":
    main()
