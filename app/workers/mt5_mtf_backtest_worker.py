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
MAX_HISTORY_YEARS = 10
ANALYSIS_TIMEFRAMES = ("MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1")
MTF_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")
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
            "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1, "MN1": mt5.TIMEFRAME_MN1}

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
    "W1": timedelta(days=7), "MN1": timedelta(days=31),
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

def _probe_history(mt5, symbol, mapping, tf, max_history_years, now):
    target_start = now - timedelta(days=365 * max_history_years + 30)
    rates = mt5.copy_rates_range(symbol, mapping[tf], target_start, now)
    if rates is None or not len(rates):
        return None
    first = datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc)
    return {"max_history_years": max_history_years, "target_start": target_start, "first": first, "rates": rates}

def run(symbol, years, initial_balance, sleep_sec, max_chunks=0):
    import MetaTrader5 as mt5
    symbol = symbol.upper()
    base = ROOT / symbol
    base.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    if not mt5.initialize(timeout=15000):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        info = mt5.terminal_info()
        if not info or not getattr(info, "connected", False):
            raise RuntimeError(f"MT5 terminal is not connected: {mt5.last_error()}")
        mapping = tf_map(mt5)
        availability = {}
        for tf in ANALYSIS_TIMEFRAMES:
            probe = _probe_history(mt5, symbol, mapping, tf, MAX_HISTORY_YEARS, now)
            if probe:
                availability[tf] = probe
        if not availability:
            raise RuntimeError(f"No MT5 history available for {symbol}: {mt5.last_error()}")
        engine = BacktestAndLearningEngine(storage_dir=str(base / "brain_memory"))
        summaries = {}
        for primary_tf in ANALYSIS_TIMEFRAMES:
            probe = availability.get(primary_tf)
            if not probe:
                continue
            tf_start = probe["first"]
            target_start = probe["target_start"]
            checkpoint_path = base / primary_tf / "checkpoint.json"
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8-sig")) if checkpoint_path.exists() else None
            if checkpoint and (checkpoint.get("schema") != SCHEMA or checkpoint.get("symbol") != symbol or checkpoint.get("timeframe") != primary_tf):
                raise RuntimeError(f"Checkpoint mismatch for {symbol}/{primary_tf}")
            next_start = parse_time(checkpoint["next_start"]) if checkpoint else tf_start
            state = checkpoint.get("state") if checkpoint else None
            processed_chunks = int(checkpoint.get("processed_chunks", 0)) if checkpoint else 0
            processed_bars = int(checkpoint.get("processed_bars", 0)) if checkpoint else 0
            history_start = checkpoint.get("history_start") if checkpoint else tf_start.isoformat()
            primary_chunk_days = {"M1": 3, "M5": 7, "M15": 14, "M30": 21, "H1": 30, "H4": 60, "D1": 180, "W1": 365, "MN1": 730}[primary_tf]
            while next_start < now:
                chunk_end = min(next_start + timedelta(days=primary_chunk_days), now)
                series = {}
                cursor_map = {}
                for tf in MTF_TIMEFRAMES:
                    context = max(TIMEFRAME_DURATION[tf] * CONTEXT_BARS, timedelta(days=2))
                    tf_first = availability[tf]["first"] if tf in availability else target_start
                    fetch_start = max(tf_first, next_start - context)
                    rates = mt5.copy_rates_range(symbol, mapping[tf], fetch_start, chunk_end)
                    if rates is None or not len(rates):
                        series[tf] = []
                        cursor_map[tf] = None
                        continue
                    series[tf] = candles_from_rates(rates)
                    cursor_map[tf] = series[tf][-1]["timestamp"]
                primary = series[primary_tf]
                process_index = 0
                while process_index < len(primary) and parse_time(primary[process_index]["timestamp"]) < next_start:
                    process_index += 1
                if process_index >= len(primary):
                    next_start = chunk_end
                    continue
                provider = lambda ts, _series=series: closed_context_provider(_series, ts)
                result = engine.run_backtest(symbol, primary_tf, primary, initial_balance=initial_balance, start_index=process_index, context_window=CONTEXT_BARS, state=state, all_timeframe_candles_provider=provider, decision_interval_minutes=15)
                state = result["state"]
                new_bars = len(primary) - process_index
                processed_bars += new_bars
                processed_chunks += 1
                next_start = parse_time(primary[-1]["timestamp"]) + TIMEFRAME_DURATION[primary_tf]
                atomic_json(checkpoint_path, {"schema": SCHEMA, "status": "RUNNING", "symbol": symbol, "timeframe": primary_tf, "max_history_years": MAX_HISTORY_YEARS, "history_start": history_start, "history_end": now.isoformat(), "next_start": next_start.isoformat(), "processed_chunks": processed_chunks, "processed_bars": processed_bars, "state": state, "timeframe_cursors": cursor_map, "updated_at": datetime.now(timezone.utc).isoformat()})
                print(f"MTF_PROGRESS {symbol}/{primary_tf} max_years={MAX_HISTORY_YEARS} actual_days={(now-tf_start).days} chunks={processed_chunks} bars={processed_bars}", flush=True)
                if max_chunks and processed_chunks >= max_chunks:
                    break
                time.sleep(max(0.2, sleep_sec))
            completed = next_start >= now
            final = {"status": "COMPLETED" if completed else "RUNNING", "symbol": symbol, "timeframe": primary_tf, "max_history_years": MAX_HISTORY_YEARS, "actual_history_start": history_start, "actual_history_end": now.isoformat(), "actual_history_days": (now-parse_time(history_start)).days, "processed_bars": processed_bars, "state": state}
            atomic_json(checkpoint_path, final)
            atomic_json(base / primary_tf / "final_result.json", final)
            summaries[primary_tf] = final
            if max_chunks:
                break
        atomic_json(base / "summary.json", {"schema": SCHEMA, "symbol": symbol, "generated_at": now.isoformat(), "timeframe_windows": summaries})
        return summaries
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
