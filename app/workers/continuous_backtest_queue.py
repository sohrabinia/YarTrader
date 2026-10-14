"""Always-on resumable MTF backtest queue for configured MT5 symbols.

Runs in the interactive MT5 session alongside mt5_backtest_supervisor.py. It
only schedules historical backtests; it never submits broker orders.
"""
from __future__ import annotations
import json, os, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JOB = ROOT / "runtime_logs" / "backtest_learning" / "active_job.json"
STATE = ROOT / "runtime_logs" / "backtest_learning" / "continuous_queue_state.json"
LOG = ROOT / "runtime_logs" / "backtest_learning" / "continuous_queue.log"
CONFIG = ROOT / "config" / "historical_learning_symbols.json"
SUMMARY_ROOT = ROOT / "runtime_logs" / "backtest_learning" / "mtf_incremental"
EXCLUDED_DEFAULT = {"BTCUSD"}  # absent from the current MT5 broker symbol catalog
_LOCK = None

def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {message}\n")

def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default

def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def symbols() -> list[str]:
    override = os.getenv("YARTRADER_BACKTEST_SYMBOLS", "").strip()
    if override:
        items = override.replace(";", ",").split(",")
    else:
        payload = read_json(CONFIG, {}) or {}
        items = payload.get("symbols", [])
    excluded = {x.strip().upper() for x in os.getenv("YARTRADER_BACKTEST_EXCLUDED_SYMBOLS", ",".join(EXCLUDED_DEFAULT)).split(",") if x.strip()}
    result = []
    for item in items:
        symbol = str(item).strip().upper()
        if symbol and symbol not in excluded and symbol not in result:
            result.append(symbol)
    if not result:
        raise RuntimeError("Continuous backtest queue has no configured symbols.")
    return result

def summary_complete(symbol: str) -> bool:
    payload = read_json(SUMMARY_ROOT / symbol / "summary.json", {}) or {}
    windows = payload.get("timeframe_windows") or {}
    return bool(windows) and all(str(x.get("status", "")).upper() == "COMPLETED" for x in windows.values())

def _acquire_lock():
    global _LOCK
    import msvcrt
    path = ROOT / "runtime_logs" / "backtest_learning" / ".continuous_queue.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0"); handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close(); return False
    _LOCK = handle
    return True

def run_forever():
    items = symbols()
    state = read_json(STATE, {}) or {}
    index = int(state.get("next_index", 0)) % len(items)
    current = state.get("current_symbol")
    started = float(state.get("started_epoch", 0) or 0)
    log(f"QUEUE_STARTED symbols={len(items)} timeframes=MTF years=10")
    while True:
        if current not in items:
            existing_job = read_json(JOB, {}) or {}
            if existing_job.get("enabled", False):
                # Recover the queue's own in-flight job after a process restart; never
                # overwrite a different active/manual backtest job.
                existing_symbol = str(existing_job.get("symbol", "")).upper()
                if str(existing_job.get("timeframe", "")).upper() == "MTF" and existing_symbol in items:
                    current = existing_symbol
                    started = started or time.time()
                    write_json(STATE, {"status": "RUNNING", "symbols_count": len(items),
                                       "next_index": items.index(current), "current_symbol": current,
                                       "started_epoch": started,
                                       "updated_at": datetime.now(timezone.utc).isoformat()})
                    log(f"SYMBOL_RECOVERED {current}")
                else:
                    time.sleep(10)
                    continue
            else:
                current = items[index]
                started = time.time()
                summary = SUMMARY_ROOT / current / "summary.json"
                summary.unlink(missing_ok=True)  # preserve per-timeframe checkpoints for incremental continuation
                write_json(JOB, {"symbol": current, "timeframe": "MTF", "years": 10,
                                 "initial_balance": 10000.0, "sleep": 0.5,
                                 "chunk_timeout_sec": 900, "enabled": True})
                write_json(STATE, {"status": "RUNNING", "symbols_count": len(items), "next_index": index,
                                   "current_symbol": current, "started_epoch": started,
                                   "updated_at": datetime.now(timezone.utc).isoformat()})
                log(f"SYMBOL_START {current} index={index+1}/{len(items)}")
        job = read_json(JOB, {}) or {}
        if job.get("symbol", "").upper() == current and str(job.get("timeframe", "")).upper() == "MTF":
            if not job.get("enabled", False) and summary_complete(current):
                log(f"SYMBOL_COMPLETED {current}")
                index = (items.index(current) + 1) % len(items)
                write_json(STATE, {"status": "ADVANCING", "symbols_count": len(items), "next_index": index,
                                   "current_symbol": None, "started_epoch": 0,
                                   "updated_at": datetime.now(timezone.utc).isoformat()})
                current = None; started = 0
                continue
            if not job.get("enabled", False):
                # A restarted queue resumes incomplete work instead of waiting for the timeout.
                summary_path = SUMMARY_ROOT / current / "summary.json"
                summary_path.unlink(missing_ok=True)
                job["enabled"] = True
                write_json(JOB, job)
                log(f"SYMBOL_RESUMED {current}")
            if time.time() - started > 48 * 3600:
                log(f"SYMBOL_TIMEOUT {current}; marking this symbol skipped and continuing the queue")
                job["enabled"] = False; write_json(JOB, job)
                index = (items.index(current) + 1) % len(items)
                write_json(STATE, {"status": "SKIPPED_TIMEOUT", "symbols_count": len(items), "next_index": index,
                                   "current_symbol": None, "started_epoch": 0,
                                   "updated_at": datetime.now(timezone.utc).isoformat()})
                current = None; started = 0
                continue
        else:
            # Do not overwrite a manually submitted or unrelated active job.
            if job.get("enabled", False):
                time.sleep(10); continue
            if summary_complete(current):
                log(f"SYMBOL_COMPLETED {current}")
                index = (items.index(current) + 1) % len(items)
                current = None; started = 0
                write_json(STATE, {"status": "ADVANCING", "symbols_count": len(items), "next_index": index,
                                   "current_symbol": None, "started_epoch": 0,
                                   "updated_at": datetime.now(timezone.utc).isoformat()})
                continue
        time.sleep(10)

if __name__ == "__main__":
    if os.name == "nt" and not _acquire_lock():
        log("DUPLICATE_QUEUE_SKIPPED"); raise SystemExit(0)
    run_forever()
