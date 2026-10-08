"""Low-priority, resumable MT5-terminal historical backtest worker."""
import argparse
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
from src.Application.Backtesting.historical_dataset import run_staged_backtest

SCHEMA = 1
CONTEXT_BARS = 100
ROOT = Path("runtime_logs") / "backtest_learning"
LOCK = ROOT / "mt5_backtest.lock"

def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)

def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

def chunk_days(timeframe):
    tf = timeframe.upper()
    if tf == "M1":
        return 7
    if tf in {"M5", "M15", "M30"}:
        return 30
    if tf in {"H1", "H4"}:
        return 90
    return 365

def overlap_days(timeframe):
    days = chunk_days(timeframe)
    return min(days, max(2, int(days * 0.15)))

def tf_map(mt5):
    return {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }

def acquire_lock():
    ROOT.mkdir(parents=True, exist_ok=True)
    try:
        with LOCK.open("x", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        return True
    except FileExistsError:
        return False

def release_lock():
    try:
        LOCK.unlink()
    except FileNotFoundError:
        pass

def make_paths(symbol, timeframe):
    stem = f"{symbol.upper()}_{timeframe.upper()}"
    base = ROOT / "mt5_incremental" / stem
    return base, base / "checkpoint.json", base / "chunks"

def candles_from_rates(rates):
    from datetime import datetime, timezone
    candles = []
    for r in rates:
        candles.append({
            "timestamp": datetime.fromtimestamp(int(r["time"]), timezone.utc).isoformat(),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": float(r["tick_volume"]),
        })
    return candles

def new_state(initial_balance):
    return {
        "balance": initial_balance, "equity": initial_balance,
        "open_position": None, "total_trades": 0,
        "wins": 0, "losses": 0, "breakevens": 0,
        "learning_updates_count": 0,
    }

def run(symbol, timeframe, years, initial_balance, sleep_sec, max_chunks=0):
    if years < 10:
        raise ValueError("MT5 historical backtest requires at least 10 years.")
    # Historical research is staged once from MT4 HST and then consumed from local disk.
    # MT5 is intentionally not touched by this backtest worker.
    return run_staged_backtest(symbol, timeframe, years, initial_balance, ROOT, max_chunks, sleep_sec)


def run_legacy_mt5(symbol, timeframe, years, initial_balance, sleep_sec, max_chunks=0):
    if years < 10:
        raise ValueError("MT5 historical backtest requires at least 10 years.")
    import MetaTrader5 as mt5

    base, checkpoint_path, chunks_dir = make_paths(symbol, timeframe)
    base.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    requested_start = now - timedelta(days=365 * years + 30)
    minimum_start = now - timedelta(days=365 * years)
    checkpoint = None
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint.get("schema") != SCHEMA:
            raise RuntimeError("Unsupported checkpoint schema.")
        if checkpoint["symbol"] != symbol.upper() or checkpoint["timeframe"] != timeframe.upper():
            raise RuntimeError("Checkpoint does not match requested job.")

    state = checkpoint.get("state", new_state(initial_balance)) if checkpoint else new_state(initial_balance)
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
        tf = timeframe.upper()
        if tf not in mapping:
            raise ValueError(f"Unsupported MT5 timeframe: {timeframe}")

        # Probe the requested window before processing: MT5 terminal history is authoritative.
        if checkpoint is None:
            probe = mt5.copy_rates_range(symbol, mapping[tf], requested_start, now)
            if probe is None or len(probe) == 0:
                raise RuntimeError(f"No MT5 history for {symbol}/{tf}: {mt5.last_error()}")
            first = datetime.fromtimestamp(int(probe[0]["time"]), timezone.utc)
            if first > minimum_start:
                raise RuntimeError(
                    f"MT5 history is shorter than requested: {(now-first).days} days."
                )
            next_start = first
            history_start = first.isoformat()
            atomic_json(checkpoint_path, {
                "schema": SCHEMA, "status": "RUNNING",
                "symbol": symbol.upper(), "timeframe": tf,
                "years_requested": years, "history_start": history_start,
                "history_end": now.isoformat(), "next_start": next_start.isoformat(),
                "processed_chunks": 0, "processed_bars": 0, "state": state,
            })

        step = timedelta(days=chunk_days(tf))
        overlap = timedelta(days=overlap_days(tf))
        engine = BacktestAndLearningEngine(storage_dir=str(base / "brain_memory"))

        while next_start < now:
            chunk_end = min(next_start + step, now)
            fetch_start = max(requested_start, next_start - overlap)
            rates = None
            for attempt in range(4):
                rates = mt5.copy_rates_range(symbol, mapping[tf], fetch_start, chunk_end)
                if rates is not None and len(rates):
                    break
                if not getattr(mt5.terminal_info(), "connected", False):
                    raise RuntimeError(f"MT5 disconnected: {mt5.last_error()}")
                time.sleep(2 ** attempt)
            if rates is None or len(rates) == 0:
                raise RuntimeError(f"MT5 history gap/error {fetch_start}..{chunk_end}: {mt5.last_error()}")

            candles = candles_from_rates(rates)
            process_index = 0
            while process_index < len(candles) and parse_time(candles[process_index]["timestamp"]) < next_start:
                process_index += 1
            if process_index >= len(candles):
                last_available = parse_time(candles[-1]["timestamp"])
                grace = {
                    "M1": timedelta(minutes=2), "M5": timedelta(minutes=10),
                    "M15": timedelta(minutes=30), "M30": timedelta(hours=1),
                    "H1": timedelta(hours=2), "H4": timedelta(hours=8),
                    "D1": timedelta(days=2), "W1": timedelta(days=14),
                    "MN1": timedelta(days=45),
                }[tf]
                if chunk_end >= now and last_available >= now - grace:
                    final = {
                        "schema": SCHEMA, "status": "COMPLETED",
                        "symbol": symbol.upper(), "timeframe": tf,
                        "years_requested": years, "history_start": history_start,
                        "history_end": now.isoformat(), "processed_chunks": processed_chunks,
                        "processed_bars": processed_bars, "state": state,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    atomic_json(checkpoint_path, final)
                    atomic_json(base / "final_result.json", final)
                    print("BACKTEST_COMPLETED " + json.dumps(final), flush=True)
                    return final
                raise RuntimeError(f"MT5 returned no new bars for chunk ending {chunk_end.isoformat()}")

            result = engine.run_backtest(
                symbol, tf, candles, initial_balance=initial_balance,
                start_index=process_index, context_window=CONTEXT_BARS, state=state,
            )
            state = result["state"]
            new_bars = len(candles) - process_index
            processed_bars += new_bars
            processed_chunks += 1

            chunk_name = f"{processed_chunks:05d}_{next_start.date()}_{chunk_end.date()}.json"
            atomic_json(chunks_dir / chunk_name, {
                "schema": SCHEMA, "symbol": symbol.upper(), "timeframe": tf,
                "start": next_start.isoformat(), "end": chunk_end.isoformat(),
                "bars": new_bars, "result": result,
            })

            last_ts = parse_time(candles[-1]["timestamp"])
            next_start = last_ts + timedelta(microseconds=1)
            checkpoint_payload = {
                "schema": SCHEMA, "status": "RUNNING",
                "symbol": symbol.upper(), "timeframe": tf,
                "years_requested": years, "history_start": history_start,
                "history_end": now.isoformat(), "next_start": next_start.isoformat(),
                "processed_chunks": processed_chunks, "processed_bars": processed_bars,
                "state": state, "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            atomic_json(checkpoint_path, checkpoint_payload)
            print(
                f"BACKTEST_PROGRESS symbol={symbol} tf={tf} chunks={processed_chunks} "
                f"bars={processed_bars} next={next_start.isoformat()} balance={state['balance']:.2f}",
                flush=True,
            )
            if max_chunks and processed_chunks >= max_chunks:
                return checkpoint_payload
            time.sleep(max(0.2, sleep_sec))

        final = {
            "schema": SCHEMA, "status": "COMPLETED",
            "symbol": symbol.upper(), "timeframe": tf, "years_requested": years,
            "history_start": history_start, "history_end": now.isoformat(),
            "processed_chunks": processed_chunks, "processed_bars": processed_bars,
            "state": state, "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_json(checkpoint_path, final)
        atomic_json(base / "final_result.json", final)
        print("BACKTEST_COMPLETED " + json.dumps(final), flush=True)
        return final
    finally:
        mt5.shutdown()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="D1")
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--initial-balance", type=float, default=10000.0)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--max-chunks", type=int, default=0)
    args = parser.parse_args()

    if not acquire_lock():
        raise SystemExit("Another MT5 backtest is already running.")
    try:
        result = run(args.symbol, args.timeframe, args.years, args.initial_balance, args.sleep, args.max_chunks)
        print(json.dumps(result, default=str), flush=True)
    finally:
        release_lock()

if __name__ == "__main__":
    main()
