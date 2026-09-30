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

def log(message):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {message}\n")

def load_job():
    if not JOB.exists():
        return None
    try:
        return json.loads(JOB.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"JOB_READ_ERROR {type(exc).__name__}: {exc}")
        return None

def checkpoint(job):
    path = ROOT / "runtime_logs" / "backtest_learning" / "mt5_incremental" / f"{job['symbol'].upper()}_{job['timeframe'].upper()}" / "checkpoint.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def run_forever():
    log("SUPERVISOR_STARTED")
    while True:
        job = load_job()
        if not job or not job.get("enabled", False):
            time.sleep(10)
            continue

        symbol = str(job.get("symbol", "XAUUSD")).upper()
        timeframe = str(job.get("timeframe", "D1")).upper()
        years = int(job.get("years", 10))
        balance = float(job.get("initial_balance", 10000.0))
        sleep_sec = float(job.get("sleep", 1.0))

        cp = checkpoint(job)
        if cp and cp.get("status") == "COMPLETED":
            log(f"JOB_COMPLETED {symbol}/{timeframe}")
            job["enabled"] = False
            JOB.write_text(json.dumps(job, indent=2), encoding="utf-8")
            continue

        cmd = [
            sys.executable, str(WORKER),
            "--symbol", symbol,
            "--timeframe", timeframe,
            "--years", str(years),
            "--initial-balance", str(balance),
            "--sleep", str(sleep_sec),
            "--max-chunks", "1",
        ]
        log(f"CHUNK_START {symbol}/{timeframe}")
        try:
            result = subprocess.run(
                cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=None,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in result.stdout.splitlines()[-8:]:
                log(line)
            log(f"CHUNK_EXIT rc={result.returncode}")
        except Exception as exc:
            log(f"CHUNK_EXCEPTION {type(exc).__name__}: {exc}")
        time.sleep(max(2.0, sleep_sec))

if __name__ == "__main__":
    run_forever()
