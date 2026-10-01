"""Autonomous historical-learning queue; intentionally independent of the 30-symbol production limit."""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path

from src.Execution.Adapters.mt4_file_bridge import MT4FileBridge
ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "historical_learning_symbols.json"
DEFAULT_TIMEFRAMES = ("M1","M5","M15","M30","H1","H4","D1","W1","MN1")

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

def _wait_for_signal_bridge(poll_sec=5.0):
    bridge = MT4FileBridge()
    while True:
        hb = bridge.heartbeat()
        if hb and hb.get("login") == "143056202" and hb.get("server") == "Alpari-Pro.ECN" and not hb.get("is_demo"):
            return
        time.sleep(poll_sec)

def run_queue(years=10, initial_balance=10000.0, sleep_sec=0.5, max_symbols=0):
    symbols=load_symbols()[:max_symbols or None]
    state_path=ROOT/"runtime_logs"/"backtest_learning"/"historical_queue_state.json"
    existing=None
    if state_path.exists():
        try:
            existing=json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            existing=None
    completed = existing.get("completed_symbols", []) if existing and existing.get("symbols")==symbols and existing.get("years")==years else []
    state={"schema":1,"status":"WAITING_FOR_SIGNAL","years":years,"symbols":symbols,
           "completed_symbols":completed,"current_symbol":None}
    save_state(state)
    _wait_for_signal_bridge()
    state["status"]="RUNNING"; save_state(state)
    worker=ROOT/"app"/"workers"/"historical_symbol_worker.py"
    for index,symbol in enumerate(symbols):
        if symbol in completed:
            continue
        state["current_index"]=index; state["current_symbol"]=symbol; save_state(state)
        cmd=[sys.executable,str(worker),"--symbol",symbol,"--years",str(years),
             "--initial-balance",str(initial_balance),"--sleep",str(sleep_sec)]
        rc=subprocess.run(cmd,cwd=str(ROOT),check=False).returncode
        if rc!=0:
            state.update(status="FAILED",failed_symbol=symbol)
            save_state(state)
            raise RuntimeError(f"Historical learning stopped at {symbol}; next symbol blocked.")
        state["completed_symbols"].append(symbol); state["current_symbol"]=None; save_state(state)
    state["status"]="COMPLETED"; save_state(state); return state

def main():
    p=argparse.ArgumentParser(); p.add_argument("--years",type=int,default=10)
    p.add_argument("--initial-balance",type=float,default=10000.0)
    p.add_argument("--sleep",type=float,default=0.5); p.add_argument("--max-symbols",type=int,default=0)
    a=p.parse_args(); run_queue(a.years,a.initial_balance,a.sleep,a.max_symbols)
if __name__=="__main__": main()

