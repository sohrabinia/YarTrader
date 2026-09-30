"""Resumable multi-timeframe MT5-terminal backtest coordinator."""
import argparse
import bisect
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))
from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine

SCHEMA = 1
PRIMARY_TIMEFRAME = "M5"
MTF_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
PRIMARY_CHUNK_DAYS = 7
CONTEXT_BARS = 500
DECISION_INTERVAL_MINUTES = 15
ROOT = Path("runtime_logs") / "backtest_learning" / "mtf_incremental"
LOCK = ROOT / "mtf_backtest.lock"

def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)
def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

def tf_map(mt5):
    return {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1}

def candles_from_rates(rates):
    return [{
        "timestamp": datetime.fromtimestamp(int(r["time"]), timezone.utc).isoformat(),
        "open": float(r["open"]), "high": float(r["high"]),
        "low": float(r["low"]), "close": float(r["close"]),
        "volume": float(r["tick_volume"]),
    } for r in rates]

def acquire_lock():
    ROOT.mkdir(parents=True, exist_ok=True)
    try:
        with LOCK.open("x", encoding="utf-8") as h:
            h.write(str(os.getpid()))
        return True
    except FileExistsError:
        return False

def release_lock():
    try:
        LOCK.unlink()
    except FileNotFoundError:
        pass
TIMEFRAME_DURATION = {
    "M1": timedelta(minutes=1), "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15), "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1), "H4": timedelta(hours=4), "D1": timedelta(days=1),
}

def closed_context_provider(series, timestamp):
    """Return only fully closed MT5 candles available at the decision time."""
    decision = parse_time(timestamp)
    result = {}
    for tf, candles in series.items():
        duration = TIMEFRAME_DURATION[tf]
        times = [parse_time(c["timestamp"]) + duration for c in candles]
        idx = bisect.bisect_right(times, decision) - 1
        if idx >= 0:
            start = max(0, idx + 1 - CONTEXT_BARS)
            result[tf] = candles[start:idx + 1]
    return result

def run(symbol, years, initial_balance, sleep_sec, max_chunks=0):
    if years < 10:
        raise ValueError("MT5 multi-timeframe backtest requires at least 10 years.")
    import MetaTrader5 as mt5
    base = ROOT / symbol.upper()
    checkpoint_path = base / "checkpoint.json"
    chunks_dir = base / "chunks"
    base.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    requested_start = now - timedelta(days=365 * years + 30)
    minimum_start = now - timedelta(days=365 * years)
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.exists() else None
    if checkpoint and (checkpoint.get("schema") != SCHEMA or checkpoint.get("symbol") != symbol.upper()):
        raise RuntimeError("MTF checkpoint does not match requested job.")
    state = checkpoint.get("state") if checkpoint else None
    next_start = parse_time(checkpoint["next_start"]) if checkpoint else requested_start
    processed_chunks = int(checkpoint.get("processed_chunks", 0)) if checkpoint else 0
    processed_bars = int(checkpoint.get("processed_bars", 0)) if checkpoint else 0
    history_start = checkpoint.get("history_start") if checkpoint else None
    if not mt5.initialize(timeout=15000):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        info = mt5.terminal_info()
        if not info or not getattr(info, "connected", False):
            raise RuntimeError(f"MT5 terminal is not connected: {mt5.last_error()}")
        mapping = tf_map(mt5)
        if checkpoint is None:
            probe = mt5.copy_rates_range(symbol, mapping[PRIMARY_TIMEFRAME], requested_start, now)
            if probe is None or not len(probe):
                raise RuntimeError(f"No MT5 {PRIMARY_TIMEFRAME} history for {symbol}: {mt5.last_error()}")
            first = datetime.fromtimestamp(int(probe[0]["time"]), timezone.utc)
            if first > minimum_start:
                raise RuntimeError(f"MT5 M1 history is shorter than requested: {(now-first).days} days.")
            next_start = first
            history_start = first.isoformat()
        engine = BacktestAndLearningEngine(storage_dir=str(base / "brain_memory"))
        while next_start < now:
            chunk_end = min(next_start + timedelta(days=PRIMARY_CHUNK_DAYS), now)
            series, cursor_map = {}, {}
            context_days = {"M1": 1, "M5": 2, "M15": 6, "M30": 12, "H1": 22, "H4": 85, "D1": 505}
            for tf in MTF_TIMEFRAMES:
                fetch_start = max(requested_start, next_start - timedelta(days=context_days[tf]))
                rates = None
                for attempt in range(4):
                    rates = mt5.copy_rates_range(symbol, mapping[tf], fetch_start, chunk_end)
                    if rates is not None and len(rates):
                        break
                    if not getattr(mt5.terminal_info(), "connected", False):
                        raise RuntimeError(f"MT5 disconnected while fetching {tf}: {mt5.last_error()}")
                    time.sleep(2 ** attempt)
                if rates is None or not len(rates):
                    if tf == PRIMARY_TIMEFRAME:
                        raise RuntimeError(f"MT5 history gap/error {symbol}/{tf}: {mt5.last_error()}")
                    series[tf] = []
                    cursor_map[tf] = None
                    continue
                series[tf] = candles_from_rates(rates)
                cursor_map[tf] = series[tf][-1]["timestamp"]
            primary = series[PRIMARY_TIMEFRAME]
            process_index = 0
            while process_index < len(primary) and parse_time(primary[process_index]["timestamp"]) < next_start:
                process_index += 1
            if process_index >= len(primary):
                raise RuntimeError(f"MT5 returned no new M1 bars for {chunk_end.isoformat()}")
            provider = lambda ts, _series=series: closed_context_provider(_series, ts)
            result = engine.run_backtest(
                symbol, PRIMARY_TIMEFRAME, primary,
                initial_balance=initial_balance, start_index=process_index,
                context_window=CONTEXT_BARS, state=state,
                all_timeframe_candles_provider=provider,
                decision_interval_minutes=DECISION_INTERVAL_MINUTES,
            )
            state = result["state"]
            new_bars = len(primary) - process_index
            processed_bars += new_bars
            processed_chunks += 1
            next_start = parse_time(primary[-1]["timestamp"]) + timedelta(minutes=1)
            payload = {
                "schema": SCHEMA, "status": "RUNNING", "symbol": symbol.upper(),
                "primary_timeframe": PRIMARY_TIMEFRAME, "timeframes": list(MTF_TIMEFRAMES),
                "years_requested": years, "history_start": history_start,
                "history_end": now.isoformat(), "next_start": next_start.isoformat(),
                "processed_chunks": processed_chunks, "processed_bars": processed_bars,
                "decision_interval_minutes": DECISION_INTERVAL_MINUTES,
                "timeframe_cursors": cursor_map, "state": state,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            atomic_json(chunks_dir / f"{processed_chunks:05d}_{next_start.date()}.json", {
                "start": next_start.isoformat(), "end": chunk_end.isoformat(),
                "bars": new_bars, "timeframes": list(MTF_TIMEFRAMES),
                "timeframe_cursors": cursor_map, "result": result,
            })
            atomic_json(checkpoint_path, payload)
            print(f"MTF_BACKTEST_PROGRESS symbol={symbol} chunks={processed_chunks} bars={processed_bars} next={next_start.isoformat()}", flush=True)
            if max_chunks and processed_chunks >= max_chunks:
                return payload
            time.sleep(max(0.2, sleep_sec))
        final = dict(payload if 'payload' in locals() else {})
        final.update({"status": "COMPLETED", "completed_at": datetime.now(timezone.utc).isoformat()})
        atomic_json(checkpoint_path, final)
        atomic_json(base / "final_result.json", final)
        print("MTF_BACKTEST_COMPLETED " + json.dumps(final), flush=True)
        return final
    finally:
        mt5.shutdown()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--initial-balance", type=float, default=10000.0)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--max-chunks", type=int, default=0)
    args = parser.parse_args()
    if not acquire_lock():
        raise SystemExit("Another MT5 multi-timeframe backtest is already active.")
    try:
        run(args.symbol, args.years, args.initial_balance, args.sleep, args.max_chunks)
    finally:
        release_lock()

if __name__ == "__main__":
    main()
