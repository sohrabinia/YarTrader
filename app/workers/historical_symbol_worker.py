"""One-symbol autonomous historical acquisition + Brain/backtest runner."""
from __future__ import annotations
import argparse
from pathlib import Path
from datetime import datetime, timezone

from src.Application.Backtesting.historical_dataset import (
    TIMEFRAMES, run_staged_backtest
)
from src.Application.Backtesting.mt4_history_acquisition import MT4HistoryAcquisition
from src.Data.Providers.MT4.historical import MT4HistoricalDataProvider
from src.Execution.Adapters.mt4_file_bridge import MT4FileBridge

SIGNAL_LOGIN = "143056202"
SIGNAL_SERVER = "Alpari-Pro.ECN"


def required_bars(tf: str, years: int) -> int:
    minutes = {"M1":1,"M5":5,"M15":15,"M30":30,"H1":60,"H4":240,
               "D1":1440,"W1":10080,"MN1":43200}[tf]
    return int((years * 366 * 24 * 60) / minutes) + 100


def acquire_all(symbol: str, years: int) -> list[dict]:
    bridge = MT4FileBridge()
    hb = bridge.heartbeat()
    if not hb or hb.get("login") != SIGNAL_LOGIN or hb.get("server") != SIGNAL_SERVER:
        raise RuntimeError(
            "Historical acquisition requires the read-only MT4 Signal terminal "
            f"{SIGNAL_LOGIN}/{SIGNAL_SERVER}."
        )
    provider = MT4HistoricalDataProvider()
    acquisition = MT4HistoryAcquisition(bridge, provider)
    manifests = []
    for tf in TIMEFRAMES:
        item = acquisition.acquire(symbol, tf, required_bars(tf, years))
        actual_days = (item["last_time"] - item["first_time"]) / 86400.0
        if actual_days < years * 365:
            raise RuntimeError(
                f"Broker history shorter than requested {years} years: "
                f"{symbol}/{tf}={actual_days:.1f} days"
            )
        item["requested_years"] = years
        manifests.append(item)
    return manifests


def run(symbol: str, years: int, initial_balance: float, sleep_sec: float,
        max_chunks: int = 0) -> dict:
    root = Path("runtime_logs/backtest_learning")
    manifests = acquire_all(symbol.upper(), years)
    symbol_dir = root / "historical_staging" / symbol.upper()
    symbol_dir.mkdir(parents=True, exist_ok=True)
    (symbol_dir / "acquisition_manifest.json").write_text(
        __import__("json").dumps({
            "schema": 1, "symbol": symbol.upper(),
            "source": "MT4_BROKER_HST",
            "account": SIGNAL_LOGIN, "server": SIGNAL_SERVER,
            "synthetic_data": False, "future_data_injected": False,
            "timeframes": manifests,
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2), encoding="utf-8"
    )
    results = {}
    for tf in TIMEFRAMES:
        result = run_staged_backtest(
            symbol.upper(), tf, years, initial_balance, root,
            max_chunks=max_chunks, sleep_sec=sleep_sec, cleanup_on_success=False
        )
        results[tf] = result
        if result.get("status") != "COMPLETED":
            return {"symbol": symbol.upper(), "status": "INCOMPLETE",
                    "timeframes": results, "source_account": SIGNAL_LOGIN,
                    "source_server": SIGNAL_SERVER}
    from src.Application.Backtesting.historical_dataset import cleanup_staged_dataset
    cleanup_staged_dataset(symbol_dir / "dataset.sqlite")
    return {"symbol": symbol.upper(), "status": "COMPLETED",
            "timeframes": results, "source_account": SIGNAL_LOGIN,
            "source_server": SIGNAL_SERVER}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--years", type=int, default=10)
    p.add_argument("--initial-balance", type=float, default=10000.0)
    p.add_argument("--sleep", type=float, default=0.5)
    p.add_argument("--max-chunks", type=int, default=0)
    a = p.parse_args()
    result = run(a.symbol, a.years, a.initial_balance, a.sleep, a.max_chunks)
    if result.get("status") != "COMPLETED":
        return 2


if __name__ == "__main__":
    main()

