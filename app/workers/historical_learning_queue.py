"""Autonomous historical-learning queue; intentionally independent of the 30-symbol production limit."""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.Execution.Adapters.mt4_file_bridge import MT4FileBridge

CONFIG = ROOT / "config" / "historical_learning_symbols.json"
DEFAULT_STATE_PATH = ROOT / "runtime_logs" / "backtest_learning" / "historical_queue_state.json"
DEFAULT_LOCK_PATH = ROOT / "runtime_logs" / "backtest_learning" / "historical_queue.lock"
DEFAULT_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x0010
        process = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if process:
            kernel32.CloseHandle(process)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False


class QueueLock:
    """Windows and Unix compatible singleton process lock with stale lock recovery."""

    def __init__(self, lock_path: Path | str | None = None) -> None:
        self.lock_path = Path(lock_path) if lock_path else DEFAULT_LOCK_PATH
        self._fd: int | None = None

    def acquire(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lock_path.exists():
            try:
                content = json.loads(self.lock_path.read_text(encoding="utf-8"))
                lock_pid = content.get("pid")
                if lock_pid == os.getpid():
                    return True
                if lock_pid and is_process_running(lock_pid):
                    return False
            except Exception:
                pass

            # Stale lock cleanup
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError:
                pass

        try:
            fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            payload = json.dumps({
                "pid": os.getpid(),
                "acquired_at": datetime.now(timezone.utc).isoformat(),
            }).encode("utf-8")
            os.write(fd, payload)
            os.fsync(fd)
            self._fd = fd

            if fcntl is not None and hasattr(fcntl, "flock"):
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    pass
            elif msvcrt is not None and hasattr(msvcrt, "locking"):
                try:
                    msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
                except OSError:
                    pass
            return True
        except OSError:
            return False

    def release(self) -> None:
        if self._fd is not None:
            try:
                if fcntl is not None and hasattr(fcntl, "flock"):
                    try:
                        fcntl.flock(self._fd, fcntl.LOCK_UN)
                    except OSError:
                        pass
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            if self.lock_path.exists():
                try:
                    content = json.loads(self.lock_path.read_text(encoding="utf-8"))
                    if content.get("pid") == os.getpid():
                        self.lock_path.unlink(missing_ok=True)
                except Exception:
                    self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def load_symbols(config_path: Path | str | None = None) -> list[str]:
    path = Path(config_path) if config_path else CONFIG
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    symbols = payload.get("symbols", [])
    result = []
    for s in symbols:
        s = str(s).strip().upper()
        if s and s not in result:
            result.append(s)
    if not result:
        raise RuntimeError("Historical learning queue is empty.")
    return result


def classify_failure(error_msg: str | Exception | None) -> str:
    if not error_msg:
        return "TRANSIENT"
    msg = str(error_msg).lower()
    permanent_patterns = [
        "no usable broker history",
        "no usable historical learning window",
        "invalid symbol",
        "symbol not found",
        "schema mismatch",
        "corrupted dataset",
        "unrecoverable data format",
        "unsupported timeframe",
    ]
    for pattern in permanent_patterns:
        if pattern in msg:
            return "PERMANENT"
    return "TRANSIENT"


def _update_summary_counts(state: dict) -> dict:
    symbol_states = state.get("symbol_states", {})
    total = len(state.get("symbols", []))
    succeeded = sum(1 for st in symbol_states.values() if st.get("status") == "COMPLETED")
    permanently_failed = sum(1 for st in symbol_states.values() if st.get("status") == "PERMANENTLY_FAILED")
    retryable_failed = sum(1 for st in symbol_states.values() if st.get("status") == "RETRY_PENDING")
    skipped = sum(1 for st in symbol_states.values() if st.get("status") in ("SKIPPED", "PENDING"))

    state["completed_symbols"] = [s for s, st in symbol_states.items() if st.get("status") == "COMPLETED"]
    state["failed_symbols"] = [s for s, st in symbol_states.items() if st.get("status") == "PERMANENTLY_FAILED"]

    counts = {
        "total": total,
        "succeeded": succeeded,
        "skipped": skipped,
        "retryable_failed": retryable_failed,
        "permanently_failed": permanently_failed,
    }
    state["counts"] = counts
    return counts


def save_state(state: dict, state_path: Path | str | None = None) -> None:
    p = Path(state_path) if state_path else DEFAULT_STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)

    _update_summary_counts(state)

    if p.exists():
        bak_path = p.with_suffix(".json.bak")
        try:
            shutil.copy2(p, bak_path)
        except OSError:
            pass

    tmp_path = p.with_suffix(".tmp")
    data_bytes = json.dumps(state, indent=2, ensure_ascii=False).encode("utf-8")
    with open(tmp_path, "wb") as f:
        f.write(data_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, p)


def load_or_migrate_state(state_path: Path | str, symbols: list[str], years: int) -> dict | None:
    p = Path(state_path)
    if not p.exists():
        return None

    raw_data = None
    read_err = None
    try:
        content = p.read_text(encoding="utf-8")
        raw_data = json.loads(content)
    except Exception as e:
        read_err = e

    if raw_data is None:
        bak_path = p.with_suffix(".json.bak")
        if bak_path.exists():
            try:
                content = bak_path.read_text(encoding="utf-8")
                raw_data = json.loads(content)
            except Exception:
                pass

    if raw_data is None or not isinstance(raw_data, dict):
        raise ValueError(
            f"Corrupted or unreadable queue state at '{p}': {read_err or 'Invalid state format'}. "
            "Queue state preserved without silent reset."
        )

    existing_completed = raw_data.get("completed_symbols", [])
    if not isinstance(existing_completed, list):
        existing_completed = []

    existing_failed = raw_data.get("failed_symbols", [])
    if not isinstance(existing_failed, list):
        existing_failed = []
    if raw_data.get("failed_symbol") and raw_data["failed_symbol"] not in existing_failed:
        existing_failed.append(raw_data["failed_symbol"])

    symbol_states = raw_data.get("symbol_states")
    if not isinstance(symbol_states, dict):
        symbol_states = {}

    target_symbols = list(symbols)
    for s in raw_data.get("symbols", []):
        if s not in target_symbols:
            target_symbols.append(s)

    migrated_states = {}
    for sym in target_symbols:
        if sym in symbol_states and isinstance(symbol_states[sym], dict):
            st = symbol_states[sym]
            migrated_states[sym] = {
                "status": st.get("status", "PENDING"),
                "attempts": int(st.get("attempts", 0)),
                "last_error": st.get("last_error"),
                "last_attempt_at": st.get("last_attempt_at"),
                "next_retry_at": st.get("next_retry_at"),
                "failure_classification": st.get("failure_classification"),
            }
        else:
            if sym in existing_completed:
                migrated_states[sym] = {
                    "status": "COMPLETED",
                    "attempts": 1,
                    "last_error": None,
                    "last_attempt_at": None,
                    "next_retry_at": None,
                    "failure_classification": None,
                }
            elif sym in existing_failed:
                migrated_states[sym] = {
                    "status": "RETRY_PENDING",
                    "attempts": 1,
                    "last_error": raw_data.get("last_error", "Previous run failure"),
                    "last_attempt_at": None,
                    "next_retry_at": None,
                    "failure_classification": "TRANSIENT",
                }
            else:
                migrated_states[sym] = {
                    "status": "PENDING",
                    "attempts": 0,
                    "last_error": None,
                    "last_attempt_at": None,
                    "next_retry_at": None,
                    "failure_classification": None,
                }

    completed_list = [s for s, st in migrated_states.items() if st["status"] == "COMPLETED"]
    failed_list = [s for s, st in migrated_states.items() if st["status"] == "PERMANENTLY_FAILED"]

    state = {
        "schema": 2,
        "status": raw_data.get("status", "WAITING_FOR_SIGNAL"),
        "years": years or raw_data.get("years", 10),
        "symbols": target_symbols,
        "symbol_states": migrated_states,
        "completed_symbols": completed_list,
        "failed_symbols": failed_list,
        "current_symbol": raw_data.get("current_symbol"),
        "counts": {},
    }
    _update_summary_counts(state)
    return state


def _wait_for_signal_bridge(poll_sec: float = 5.0) -> MT4FileBridge:
    while True:
        for common_dir in glob.glob(r"C:\Users\*\AppData\Roaming\MetaQuotes\Terminal\Common\Files"):
            bridge = MT4FileBridge(common_dir=common_dir)
            hb = bridge.heartbeat()
            if hb and hb.get("login") == "143056202" and hb.get("server") == "Alpari-Pro.ECN" and not hb.get("is_demo"):
                return bridge
        time.sleep(poll_sec)


def run_queue(
    years: int = 10,
    initial_balance: float = 10000.0,
    sleep_sec: float = 0.5,
    max_symbols: int = 0,
    max_retries: int = 3,
    backoff_sec: float = 5.0,
    state_path: Path | str | None = None,
    lock_path: Path | str | None = None,
    symbols_override: list[str] | None = None,
    skip_signal_bridge: bool = False,
) -> dict:
    s_path = Path(state_path) if state_path else DEFAULT_STATE_PATH
    l_path = Path(lock_path) if lock_path else DEFAULT_LOCK_PATH

    lock = QueueLock(l_path)
    if not lock.acquire():
        print("Another active queue instance is running. Exiting cleanly.")
        if s_path.exists():
            try:
                return json.loads(s_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"status": "LOCKED", "message": "Another instance is active."}

    try:
        symbols = symbols_override if symbols_override is not None else load_symbols()
        if max_symbols > 0:
            symbols = symbols[:max_symbols]

        state = load_or_migrate_state(s_path, symbols, years)
        if state is None:
            state = {
                "schema": 2,
                "status": "WAITING_FOR_SIGNAL",
                "years": years,
                "symbols": symbols,
                "symbol_states": {
                    s: {
                        "status": "PENDING",
                        "attempts": 0,
                        "last_error": None,
                        "last_attempt_at": None,
                        "next_retry_at": None,
                        "failure_classification": None,
                    }
                    for s in symbols
                },
                "completed_symbols": [],
                "failed_symbols": [],
                "current_symbol": None,
                "counts": {},
            }
            _update_summary_counts(state)

        save_state(state, s_path)

        if not skip_signal_bridge:
            bridge = _wait_for_signal_bridge()

        state["status"] = "RUNNING"
        save_state(state, s_path)

        worker = ROOT / "app" / "workers" / "historical_symbol_worker.py"

        for index, symbol in enumerate(symbols):
            sym_state = state["symbol_states"][symbol]
            status = sym_state.get("status")

            if status == "COMPLETED":
                continue

            if status in ("PERMANENTLY_FAILED", "SKIPPED"):
                continue

            if status == "RETRY_PENDING":
                next_retry_at_str = sym_state.get("next_retry_at")
                if next_retry_at_str:
                    try:
                        next_retry_dt = datetime.fromisoformat(next_retry_at_str)
                        if datetime.now(timezone.utc) < next_retry_dt:
                            continue
                    except ValueError:
                        pass

            state["current_index"] = index
            state["current_symbol"] = symbol
            sym_state["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
            sym_state["attempts"] += 1
            save_state(state, s_path)

            cmd = [
                sys.executable,
                str(worker),
                "--symbol",
                symbol,
                "--years",
                str(years),
                "--initial-balance",
                str(initial_balance),
                "--sleep",
                str(sleep_sec),
            ]

            try:
                proc = subprocess.run(
                    cmd, cwd=str(ROOT), capture_output=True, text=True, check=False
                )
                rc = proc.returncode
                err_output = str(proc.stderr or proc.stdout or "").strip()
            except Exception as exc:
                rc = -1
                err_output = str(exc)

            if rc == 0:
                sym_state["status"] = "COMPLETED"
                sym_state["last_error"] = None
                sym_state["next_retry_at"] = None
                sym_state["failure_classification"] = None
            else:
                err_msg = err_output or f"Historical symbol worker exited with code {rc}"
                classification = classify_failure(err_msg)
                sym_state["last_error"] = err_msg
                sym_state["failure_classification"] = classification

                if classification == "PERMANENT" or sym_state["attempts"] >= max_retries:
                    sym_state["status"] = "PERMANENTLY_FAILED"
                    sym_state["next_retry_at"] = None
                else:
                    sym_state["status"] = "RETRY_PENDING"
                    delay = backoff_sec * (2 ** (sym_state["attempts"] - 1))
                    next_retry_time = datetime.now(timezone.utc) + timedelta(seconds=delay)
                    sym_state["next_retry_at"] = next_retry_time.isoformat()

            state["current_symbol"] = None
            save_state(state, s_path)

        counts = _update_summary_counts(state)
        if counts["succeeded"] == counts["total"]:
            state["status"] = "COMPLETED"
        elif counts["retryable_failed"] > 0:
            state["status"] = "RETRY_PENDING"
        elif counts["permanently_failed"] > 0 or counts["skipped"] > 0:
            state["status"] = "COMPLETED_WITH_ERRORS"
        else:
            state["status"] = "COMPLETED_WITH_ERRORS"

        save_state(state, s_path)
        return state
    finally:
        lock.release()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=int, default=10)
    p.add_argument("--initial-balance", type=float, default=10000.0)
    p.add_argument("--sleep", type=float, default=0.5)
    p.add_argument("--max-symbols", type=int, default=0)
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument("--backoff-sec", type=float, default=5.0)
    a = p.parse_args()
    run_queue(
        years=a.years,
        initial_balance=a.initial_balance,
        sleep_sec=a.sleep,
        max_symbols=a.max_symbols,
        max_retries=a.max_retries,
        backoff_sec=a.backoff_sec,
    )


if __name__ == "__main__":
    main()
