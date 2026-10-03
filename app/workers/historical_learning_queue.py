"""Autonomous historical-learning queue for the configured market universe."""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path
from threading import Thread, Lock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.Execution.Adapters.mt4_file_bridge import MT4FileBridge
CONFIG = ROOT / "config" / "historical_learning_symbols.json"
DEFAULT_TIMEFRAMES = ("M1","M5","M15","M30","H1","H4","D1","W1","MN1")

MARKET_GROUPS = {"forex": {"XAUUSD", "EURUSD"}}

def load_symbols():
    payload = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    symbols = payload.get("symbols", [])
    result=[]
    for s in symbols:
        s=str(s).strip().upper()
        if s and s not in result: result.append(s)
    if not result: raise RuntimeError("Historical learning queue is empty.")
    return result

def save_state(state):
    p=ROOT/"runtime_logs"/"backtest_learning"/"historical_queue_state.json"
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(".tmp"); tmp.write_text(json.dumps(state,indent=2),encoding="utf-8"); tmp.replace(p)

def _find_demo_bridge():
    """Find only the authorized, fresh MT4 DEMO bridge; never accept a real account."""
    for common_dir in __import__("glob").glob(r"C:\Users\*\AppData\Roaming\MetaQuotes\Terminal\Common\Files"):
        bridge = MT4FileBridge(common_dir=common_dir)
        hb = bridge.heartbeat()
        if (
            hb
            and hb.get("login") == "252031952"
            and hb.get("server") == "Alpari-Pro.ECN-Demo"
            and hb.get("is_demo") is True
        ):
            return bridge
    return None

def _wait_for_demo_bridge(poll_sec=5.0):
    while True:
        bridge = _find_demo_bridge()
        if bridge is not None:
            return bridge
        time.sleep(poll_sec)

def run_queue(years=10, initial_balance=10000.0, sleep_sec=0.5, max_symbols=0):
    from src.Infrastructure.Configuration.config import ConfigurationManager
    config = ConfigurationManager.get_config()
    if not config.historical_learning_enabled:
        state = {"schema": 3, "status": "DISABLED", "years": years, "symbols": load_symbols(), "queues": {}}
        save_state(state)
        return state
    symbols = load_symbols()[:max_symbols or None]
    grouped = {name: [s for s in symbols if s in members] for name, members in MARKET_GROUPS.items()}
    assigned = set().union(*MARKET_GROUPS.values())
    grouped["other"] = [s for s in symbols if s not in assigned]
    state_path = ROOT/"runtime_logs"/"backtest_learning"/"historical_queue_state.json"
    existing = None
    if state_path.exists():
        try: existing = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError): existing = None
    old_completed = set(existing.get("completed_symbols", [])) if existing else set()
    state = {
        "schema": 3, "status": "WAITING_FOR_DEMO",
        "years": years, "symbols": symbols,
        "queues": {
            name: {"symbols": items, "status": "WAITING",
                    "completed_symbols": [s for s in items if s in old_completed],
                    "current_symbol": None, "failed_symbols": []}
            for name, items in grouped.items() if items
        },
    }
    save_state(state)
    _wait_for_demo_bridge()
    state["status"] = "RUNNING"; save_state(state)
    worker = ROOT/"app"/"workers"/"historical_symbol_worker.py"
    state_lock = Lock()
    def run_lane(name, lane):
        for symbol in lane["symbols"]:
            if symbol in lane["completed_symbols"]: continue
            with state_lock:
                lane["current_symbol"] = symbol; lane["status"] = "RUNNING"; save_state(state)
            cmd = [sys.executable, str(worker), "--symbol", symbol, "--years", str(years),
                   "--initial-balance", str(initial_balance), "--sleep", str(sleep_sec)]
            rc = subprocess.run(cmd, cwd=str(ROOT), check=False).returncode
            with state_lock:
                lane["current_symbol"] = None
                if rc == 0: lane["completed_symbols"].append(symbol)
                else: lane["failed_symbols"].append(symbol)
                save_state(state)
        with state_lock:
            lane["status"] = "COMPLETED" if not lane["failed_symbols"] else "COMPLETED_WITH_FAILURES"; save_state(state)
    threads = []
    for name, lane in state["queues"].items():
        t = Thread(target=run_lane, args=(name, lane), name=f"HistoricalLearning-{name}", daemon=True)
        t.start(); threads.append(t)
    for t in threads: t.join()
    state["status"] = "COMPLETED" if all(lane["status"] == "COMPLETED" for lane in state["queues"].values()) else "COMPLETED_WITH_FAILURES"
    save_state(state)
    return state

def main():
    p=argparse.ArgumentParser(); p.add_argument("--years",type=int,default=10)
    p.add_argument("--initial-balance",type=float,default=10000.0); p.add_argument("--sleep",type=float,default=0.5)
    p.add_argument("--max-symbols",type=int,default=0)
    a=p.parse_args(); run_queue(a.years,a.initial_balance,a.sleep,a.max_symbols)
if __name__=="__main__": main()
