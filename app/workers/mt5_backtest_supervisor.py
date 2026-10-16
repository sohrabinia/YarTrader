"""Persistent low-priority supervisor for resumable MT5 backtest chunks."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
JOB = ROOT / "runtime_logs" / "backtest_learning" / "active_job.json"
LOG = ROOT / "runtime_logs" / "backtest_learning" / "supervisor.log"
WORKER = ROOT / "app" / "workers" / "mt5_backtest_worker.py"
MTF_WORKER = ROOT / "app" / "workers" / "mt5_mtf_backtest_worker.py"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
_SUPERVISOR_MUTEX_HANDLE = None

def _acquire_singleton() -> bool:
    """Use a cross-session OS file lock so multiple Windows sessions cannot duplicate supervisors."""
    global _SUPERVISOR_MUTEX_HANDLE
    if os.name != "nt":
        return True
    import msvcrt
    lock_path = ROOT / "runtime_logs" / "backtest_learning" / ".supervisor.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return False
    _SUPERVISOR_MUTEX_HANDLE = handle
    return True

def _rotate_log_if_needed():
    """Bound supervisor log growth while retaining the three most recent files."""
    if not LOG.exists() or LOG.stat().st_size < LOG_MAX_BYTES:
        return
    oldest = LOG.with_name(f"{LOG.name}.{LOG_BACKUP_COUNT}")
    oldest.unlink(missing_ok=True)
    for index in range(LOG_BACKUP_COUNT - 1, 0, -1):
        source = LOG.with_name(f"{LOG.name}.{index}")
        if source.exists():
            source.replace(LOG.with_name(f"{LOG.name}.{index + 1}"))
    LOG.replace(LOG.with_name(f"{LOG.name}.1"))

def log(message):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    _rotate_log_if_needed()
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {message}\n")

def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def load_job():
    if not JOB.exists():
        return None
    try:
        return _read_json(JOB)
    except Exception as exc:
        log(f"JOB_READ_ERROR {type(exc).__name__}: {exc}")
        return None

def checkpoint(job):
    if str(job.get("timeframe", "")).upper() == "MTF":
        # The MTF worker stores a checkpoint per primary timeframe and writes a
        # consolidated summary; there is no symbol-level checkpoint.json.
        path = ROOT / "runtime_logs" / "backtest_learning" / "mtf_incremental" / job["symbol"].upper() / "summary.json"
        if not path.exists():
            return None
        try:
            payload = _read_json(path)
            windows = payload.get("timeframe_windows") or {}
            if windows and all(str(item.get("status", "")).upper() == "COMPLETED" for item in windows.values()):
                return {"status": "COMPLETED", "timeframe_windows": windows}
            return {"status": "RUNNING", "timeframe_windows": windows}
        except Exception as exc:
            log(f"CHECKPOINT_READ_ERROR {type(exc).__name__}: {exc}")
            return None
    path = ROOT / "runtime_logs" / "backtest_learning" / "mt5_incremental" / f"{job['symbol'].upper()}_{job['timeframe'].upper()}" / "checkpoint.json"
    if not path.exists():
        return None
    try:
        return _read_json(path)
    except Exception as exc:
        log(f"CHECKPOINT_READ_ERROR {type(exc).__name__}: {exc}")
        return None

def run_forever():
    log("SUPERVISOR_STARTED")
    while True:
        job = load_job()
        if not job or not job.get("enabled", False):
            time.sleep(10)
            continue

        symbol = str(job.get("symbol", "XAUUSD")).upper()
        timeframe = str(job.get("timeframe", "MTF")).upper()
        years = int(job.get("years", 10))
        balance = float(job.get("initial_balance", 10000.0))
        sleep_sec = float(job.get("sleep", 1.0))
        chunk_timeout_sec = max(60.0, float(job.get("chunk_timeout_sec", 900.0)))

        cp = checkpoint(job)
        if cp and cp.get("status") == "COMPLETED":
            log(f"JOB_COMPLETED {symbol}/{timeframe}")
            job["enabled"] = False
            JOB.write_text(json.dumps(job, indent=2), encoding="utf-8")
            continue

        if timeframe == "MTF":
            cmd = [
                sys.executable, str(MTF_WORKER),
                "--symbol", symbol,
                "--years", str(years),
            ]
        else:
            cmd = [
                sys.executable, str(WORKER),
                "--symbol", symbol,
                "--timeframe", timeframe,
                "--years", str(years),
            ]
        cmd += [
            "--initial-balance", str(balance),
            "--sleep", str(sleep_sec),
            "--max-chunks", "1",
        ]
        log(f"CHUNK_START {symbol}/{timeframe}")
        try:
            result = subprocess.run(
                cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=chunk_timeout_sec,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in result.stdout.splitlines()[-8:]:
                log(line)
            log(f"CHUNK_EXIT rc={result.returncode}")
        except subprocess.TimeoutExpired:
            log(f"CHUNK_TIMEOUT seconds={chunk_timeout_sec:.0f}")
        except Exception as exc:
            log(f"CHUNK_EXCEPTION {type(exc).__name__}: {exc}")
        time.sleep(max(2.0, sleep_sec))

if __name__ == "__main__":
    if not _acquire_singleton():
        print("Another MT5 backtest supervisor already owns the singleton mutex; exiting.", flush=True)
        raise SystemExit(0)
    run_forever()
