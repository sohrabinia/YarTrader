"""MT4 terminal-triggered history acquisition with provenance checks.

The terminal is asked to load broker history (iBars/iTime); Python then reads
the resulting HST files. No synthetic candles, interpolation, resampling, or
future-looking data are permitted.
"""
from __future__ import annotations
import hashlib, json, time
from pathlib import Path

from src.Data.Providers.MT4.historical import MT4HistoricalDataProvider

class MT4HistoryAcquisition:
    def __init__(self, bridge, provider=None):
        self.bridge = bridge
        self.provider = provider or MT4HistoricalDataProvider()

    def acquire(self, symbol: str, timeframe: str, bars: int, allow_partial: bool = False) -> dict:
        symbol, timeframe = symbol.upper(), timeframe.upper()
        before = self.provider._history_file(symbol, timeframe)
        result = self.bridge.request("HISTORY", symbol, timeframe, int(bars))
        if not result or result[0] != "OK":
            raise RuntimeError(f"MT4 history acquisition failed for {symbol}/{timeframe}: {result}")
        path = self.provider._history_file(symbol, timeframe)
        if not path.exists():
            raise RuntimeError("MT4 reported history but the HST file is unavailable.")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        rows = self.provider._read_hst(path)
        if not rows:
            raise RuntimeError("MT4 HST contains no valid candles.")
        times=[int(r["time"]) for r in rows]
        if times != sorted(set(times)):
            raise RuntimeError("MT4 HST failed chronological/duplicate validation.")
        for r in rows:
            if not (r["low"] <= r["open"] <= r["high"] and
                    r["low"] <= r["close"] <= r["high"] and
                    r["high"] >= r["low"]):
                raise RuntimeError("MT4 HST failed OHLC integrity validation.")
        return {"symbol":symbol,"timeframe":timeframe,"source":"MT4_BROKER_HST",
                "path":str(path),"sha256":digest,"bars":len(rows),
                "first_time":times[0],"last_time":times[-1],
                "synthetic_data":False,"future_data_injected":False,
                "acquired_at":time.time()}

    def manifest(self, symbol: str, timeframe: str, bars: int) -> dict:
        return self.acquire(symbol,timeframe,bars)
