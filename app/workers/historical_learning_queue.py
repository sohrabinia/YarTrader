"""Autonomous historical-learning queue for the configured market universe."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.Execution.Adapters.mt4_file_bridge import MT4FileBridge

CONFIG = ROOT / "config" / "historical_learning_symbols.json"
DEFAULT_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")
MARKET_GROUPS = {"forex": {"XAUUSD", "EURUSD"}}


def load_symbols():
    payload = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    symbols = payload.get("symbols", [])
    result = []
    for symbol in symbols:
        symbol = str(symbol).strip().upper()
        if symbol and symbol not in result:
            result.append(symbol)
    if not result:
        raise RuntimeError("Historical learning queue is empty.")
    return result


def save_state(state):
    path = ROOT / "runtime_logs" / "backtest_learning" / "historical_queue_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def _find_demo_bridge():
    """Find only the authorized, fresh MT4 DEMO bridge; never accept a real account."""
    import glob

    for common_dir in glob.glob(r"C:\Users\*\AppData\Roaming\MetaQuotes\Terminal\Common\Files"):
        bridge = MT4FileBridge(common_dir=common_dir)
        heartbeat = bridge.heartbeat()
        if (
            heartbeat
            and heartbeat.get("login") == "252031952"
            and heartbeat.get("server") == "Alpari-Pro.ECN-Demo"
            and heartbeat.get("is_demo") is True
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
        state = {
            "schema": 4,
            "status": "DISABLED",
            "years": years,
            "symbols": load_symbols(),
            "queues": {},
        }
        save_state(state)
        return state

    symbols = load_symbols()[:max_symbols or None]
    grouped = {
        name: [symbol for symbol in symbols if symbol in members]
        for name, members in MARKET_GROUPS.items()
    }
    assigned = set().union(*MARKET_GROUPS.values())
    grouped["other"] = [symbol for symbol in symbols if symbol not in assigned]

    state_path = ROOT / "runtime_logs" / "backtest_learning" / "historical_queue_state.json"
    existing = None
    if state_path.exists():
        try:
            existing = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            existing = None

    old_completed = set(existing.get("completed_symbols", [])) if existing else set()
    if existing and existing.get("queues"):
        for lane in existing["queues"].values():
            old_completed.update(lane.get("completed_symbols", []))

    state = {
        "schema": 4,
        "status": "WAITING_FOR_DEMO",
        "years": years,
        "symbols": symbols,
        "queues": {
            name: {
                "symbols": items,
                "status": "WAITING",
                "completed_symbols": [symbol for symbol in items if symbol in old_completed],
                "current_symbol": None,
                "failed_symbols": [],
            }
            for name, items in grouped.items()
            if items
        },
    }
    save_state(state)

    _wait_for_demo_bridge()
    state["status"] = "RUNNING"
    save_state(state)

    worker = ROOT / "app" / "workers" / "historical_symbol_worker.py"

    # All lanes share the same FILE_COMMON request/response channel. Run them
    # sequentially so independent worker processes cannot race on the single
    # request file and consume each other's responses.
    for name, lane in state["queues"].items():
        lane["status"] = "RUNNING"
        save_state(state)

        for symbol in lane["symbols"]:
            if symbol in lane["completed_symbols"]:
                continue

            lane["current_symbol"] = symbol
            save_state(state)

            command = [
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
            return_code = subprocess.run(command, cwd=str(ROOT), check=False).returncode

            lane["current_symbol"] = None
            if return_code == 0:
                lane["completed_symbols"].append(symbol)
            else:
                lane["failed_symbols"].append(symbol)
            save_state(state)

        lane["status"] = (
            "COMPLETED" if not lane["failed_symbols"] else "COMPLETED_WITH_FAILURES"
        )
        save_state(state)

    state["status"] = (
        "COMPLETED"
        if all(lane["status"] == "COMPLETED" for lane in state["queues"].values())
        else "COMPLETED_WITH_FAILURES"
    )
    save_state(state)
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--initial-balance", type=float, default=10000.0)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--max-symbols", type=int, default=0)
    args = parser.parse_args()
    run_queue(args.years, args.initial_balance, args.sleep, args.max_symbols)


if __name__ == "__main__":
    main()
