"""Single-symbol historical dataset staging for YarTrader backtests.

Stages MT4 HST history into a temporary SQLite dataset so Brain/backtest code
reads local historical candles instead of repeatedly calling a terminal API.
Raw staged rows are deleted after a successful symbol run; derived evidence is kept.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

TIMEFRAMES = ("M1","M5","M15","M30","H1","H4","D1","W1","MN1")
SCHEMA = 1

class HistoricalDataset:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS candles(
            timeframe TEXT NOT NULL, ts INTEGER NOT NULL, open REAL NOT NULL,
            high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
            volume REAL NOT NULL, PRIMARY KEY(timeframe, ts))""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS ix_candles_tf_ts ON candles(timeframe, ts)")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS metadata(
            key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
        self.conn.commit()

    def put(self, timeframe: str, rows: Iterable[dict]) -> int:
        tf = timeframe.upper()
        values = ((tf, int(r["time"]), float(r["open"]), float(r["high"]),
                   float(r["low"]), float(r["close"]), float(r.get("volume", 0))) for r in rows)
        self.conn.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?)", values)
        self.conn.commit()
        return self.conn.execute("SELECT COUNT(*) FROM candles WHERE timeframe=?", (tf,)).fetchone()[0]

    def range(self, timeframe: str, start_ts: int, end_ts: int) -> Iterator[dict]:
        cur = self.conn.execute("""SELECT ts,open,high,low,close,volume FROM candles
            WHERE timeframe=? AND ts BETWEEN ? AND ? ORDER BY ts""",
            (timeframe.upper(), int(start_ts), int(end_ts)))
        for ts,o,h,l,c,v in cur:
            yield {"timestamp": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                   "time": ts, "open": o, "high": h, "low": l, "close": c, "volume": v}

    def first_last(self, timeframe: str):
        return self.conn.execute("SELECT MIN(ts),MAX(ts),COUNT(*) FROM candles WHERE timeframe=?",
                                 (timeframe.upper(),)).fetchone()

    def set_metadata(self, **values):
        self.conn.executemany("INSERT OR REPLACE INTO metadata VALUES (?,?)",
                              ((k, json.dumps(v, default=str)) for k,v in values.items()))
        self.conn.commit()

    def close(self):
        self.conn.close()
    def manifest(self) -> dict:
        frames = {}
        for tf in TIMEFRAMES:
            first,last,count = self.first_last(tf)
            if count:
                frames[tf] = {"first": first, "last": last, "bars": count}
        return {"schema": SCHEMA, "frames": frames}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def stage_symbol_from_mt4(symbol: str, destination: Path, provider) -> HistoricalDataset:
    """Build one symbol dataset from the authoritative MT4 HST provider."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    dataset = HistoricalDataset(destination)
    try:
        for tf in TIMEFRAMES:
            path = provider._history_file(symbol, tf)
            if not path.exists():
                continue
            rows = provider._read_hst(path)
            dataset.put(tf, rows)
        manifest = dataset.manifest()
        if not manifest["frames"]:
            raise RuntimeError(f"No MT4 historical data available for {symbol}.")
        dataset.set_metadata(symbol=symbol.upper(), source="MT4_HST", manifest=manifest,
                             staged_at=datetime.now(timezone.utc).isoformat())
        return dataset
    except Exception:
        dataset.close()
        try: destination.unlink()
        except FileNotFoundError: pass
        raise


def cleanup_staged_dataset(path: Path) -> None:
    """Delete only the temporary staged dataset; never delete broker terminal history."""
    path = Path(path)
    for suffix in ("", "-wal", "-shm"):
        try: path.with_name(path.name + suffix).unlink()
        except FileNotFoundError: pass
def dataset_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def run_staged_backtest(symbol: str, timeframe: str, years: int, initial_balance: float,
                        root: Path, max_chunks: int = 0, sleep_sec: float = 0.5,
                        cleanup_on_success: bool = True) -> dict:
    """Stage one symbol once, resume Brain processing from disk, then clean raw staging."""
    from src.Data.Providers.MT4.historical import MT4HistoricalDataProvider
    from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine
    if years < 10:
        raise ValueError("Historical backtest requires at least 10 years.")
    provider = MT4HistoricalDataProvider()
    stage_dir = Path(root) / "historical_staging" / symbol.upper()
    stage_path = stage_dir / "dataset.sqlite"
    manifest_path = stage_dir / "manifest.json"
    checkpoint_path = stage_dir / f"{timeframe.upper()}_checkpoint.json"
    dataset = None
    try:
        if stage_path.exists() and manifest_path.exists():
            dataset = HistoricalDataset(stage_path)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            dataset = stage_symbol_from_mt4(symbol, stage_path, provider)
            manifest = dataset.manifest()
            manifest_path.write_text(json.dumps({**manifest, "symbol": symbol.upper(),
                "requested_years": years, "timeframe": timeframe.upper()}, indent=2), encoding="utf-8")
        first,last,bars = dataset.first_last(timeframe)
        if not bars:
            raise RuntimeError(f"MT4 history unavailable for {symbol}/{timeframe}.")
        requested_first = int(last - years * 365 * 86400)
        if first > requested_first:
            raise RuntimeError(f"MT4 history shorter than requested 10 years for {symbol}/{timeframe}.")
        cp = json.loads(checkpoint_path.read_text(encoding="utf-8-sig")) if checkpoint_path.exists() else None
        if cp and (cp.get("symbol") != symbol.upper() or cp.get("timeframe") != timeframe.upper()):
            raise RuntimeError("Historical checkpoint does not match requested job.")
        cursor = int(cp.get("next_ts", requested_first)) if cp else requested_first
        state = cp.get("state") if cp else None
        engine = BacktestAndLearningEngine(storage_dir=str(stage_dir / "brain_memory"))
        duration_sec = {"M1":60,"M5":300,"M15":900,"M30":1800,"H1":3600,"H4":14400,
                        "D1":86400,"W1":604800,"MN1":2592000}.get(timeframe.upper(), 3600)
        chunk_seconds = 30 * 86400
        processed = int(cp.get("processed_bars", 0)) if cp else 0
        chunks = int(cp.get("processed_chunks", 0)) if cp else 0
        while cursor <= last:
            chunk_end = min(last, cursor + chunk_seconds)
            context_start = max(first, cursor - 500 * duration_sec)
            candles = list(dataset.range(timeframe, context_start, chunk_end))
            process_index = next((i for i,c in enumerate(candles) if int(c["time"]) >= cursor), len(candles))
            if process_index >= len(candles):
                cursor = chunk_end + 1
                continue
            result = engine.run_backtest(symbol, timeframe, candles, initial_balance=initial_balance,
                                          start_index=process_index, context_window=500, state=state)
            state = result["state"]
            processed += len(candles) - process_index
            chunks += 1
            cursor = chunk_end + 1
            payload = {"schema": SCHEMA, "status": "RUNNING", "symbol": symbol.upper(),
                       "timeframe": timeframe.upper(), "years_requested": years, "next_ts": cursor,
                       "processed_bars": processed, "processed_chunks": chunks, "state": state}
            checkpoint_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            if max_chunks and chunks >= max_chunks:
                return payload
            time.sleep(max(0.05, sleep_sec))
        final = {"schema": SCHEMA, "status": "COMPLETED", "symbol": symbol.upper(),
                 "timeframe": timeframe.upper(), "years_requested": years,
                 "data_source": "MT4_HST_STAGED_SQLITE", "history_start": first,
                 "history_end": last, "processed_bars": processed, "processed_chunks": chunks,
                 "state": state, "dataset_manifest": manifest,
                 "completed_at": datetime.now(timezone.utc).isoformat()}
        (stage_dir / "final_result.json").write_text(json.dumps(final, indent=2, default=str), encoding="utf-8")
        checkpoint_path.write_text(json.dumps(final, indent=2, default=str), encoding="utf-8")
        return final
    finally:
        if dataset is not None:
            dataset.close()
        if checkpoint_path.exists():
            try:
                terminal = json.loads(checkpoint_path.read_text(encoding="utf-8-sig"))
                if cleanup_on_success and terminal.get("status") == "COMPLETED" and stage_path.exists():
                    cleanup_staged_dataset(stage_path)
            except Exception:
                pass
