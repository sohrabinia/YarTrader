"""One-symbol autonomous historical acquisition + Brain/backtest runner."""
from __future__ import annotations
import argparse, glob, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from datetime import datetime, timezone

from src.Application.Backtesting.historical_dataset import TIMEFRAMES, run_staged_backtest
from src.Application.Backtesting.mt4_history_acquisition import MT4HistoryAcquisition
from src.Data.Providers.MT4.historical import MT4HistoricalDataProvider
from src.Execution.Adapters.mt4_file_bridge import MT4FileBridge

SIGNAL_LOGIN = "143056202"
SIGNAL_SERVER = "Alpari-Pro.ECN"


def required_bars(tf: str, years: float) -> int:
    minutes = {"M1":1,"M5":5,"M15":15,"M30":30,"H1":60,"H4":240,
               "D1":1440,"W1":10080,"MN1":43200}[tf]
    return max(100, int((years * 366 * 24 * 60) / minutes) + 100)


def find_signal_bridge():
    for common_dir in glob.glob(r"C:\Users\*\AppData\Roaming\MetaQuotes\Terminal\Common\Files"):
        candidate = MT4FileBridge(common_dir=common_dir)
        hb = candidate.heartbeat()
        if hb and hb.get("login") == SIGNAL_LOGIN and hb.get("server") == SIGNAL_SERVER and not hb.get("is_demo"):
            return candidate
    return None


def acquire_all(symbol: str, max_years: float) -> tuple[list[dict], float]:
    bridge = find_signal_bridge()
    hb = bridge.heartbeat() if bridge else None
    if not hb or hb.get("login") != SIGNAL_LOGIN or hb.get("server") != SIGNAL_SERVER:
        raise RuntimeError(
            "Historical acquisition requires the read-only MT4 Signal terminal "
            f"{SIGNAL_LOGIN}/{SIGNAL_SERVER}."
        )
    provider = MT4HistoricalDataProvider()
    acquisition = MT4HistoryAcquisition(bridge, provider)
    manifests = []
    for tf in TIMEFRAMES:
        item = acquisition.acquire(symbol, tf, required_bars(tf, max_years), allow_partial=True)
        actual_days = max(0.0, (item["last_time"] - item["first_time"]) / 86400.0)
        if actual_days < 1.0:
            raise RuntimeError(f"No usable broker history for {symbol}/{tf}.")
        item["requested_max_years"] = max_years
        item["available_days"] = actual_days
        manifests.append(item)
    effective_years = min(
        max_years,
        min(item["available_days"] / 365.0 for item in manifests),
    )
    if effective_years <= 0:
        raise RuntimeError(f"No usable historical learning window for {symbol}.")
    return manifests, effective_years


def run(symbol: str, max_years: float, initial_balance: float, sleep_sec: float,
        max_chunks: int = 0) -> dict:
    root = Path("runtime_logs/backtest_learning")
    manifests, effective_years = acquire_all(symbol.upper(), max_years)
    symbol_dir = root / "historical_staging" / symbol.upper()
    symbol_dir.mkdir(parents=True, exist_ok=True)
    (symbol_dir / "acquisition_manifest.json").write_text(
        json.dumps({
            "schema": 2, "symbol": symbol.upper(),
            "source": "MT4_BROKER_HST",
            "account": SIGNAL_LOGIN, "server": SIGNAL_SERVER,
            "synthetic_data": False, "future_data_injected": False,
            "requested_max_years": max_years,
            "effective_learning_years": effective_years,
            "timeframes": manifests,
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2), encoding="utf-8"
    )
    results = {}
    for tf in TIMEFRAMES:
        result = run_staged_backtest(
            symbol.upper(), tf, effective_years, initial_balance, root,
            max_chunks=max_chunks, sleep_sec=sleep_sec, cleanup_on_success=False
        )
        results[tf] = result
        if result.get("status") != "COMPLETED":
            return {"symbol": symbol.upper(), "status": "INCOMPLETE",
                    "effective_learning_years": effective_years,
                    "timeframes": results, "source_account": SIGNAL_LOGIN,
                    "source_server": SIGNAL_SERVER}
    from src.Application.Backtesting.historical_dataset import cleanup_staged_dataset
    cleanup_staged_dataset(symbol_dir / "dataset.sqlite")
    return {"symbol": symbol.upper(), "status": "COMPLETED",
            "requested_max_years": max_years,
            "effective_learning_years": effective_years,
            "timeframes": results, "source_account": SIGNAL_LOGIN,
            "source_server": SIGNAL_SERVER}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--years", type=float, default=10.0,
                   help="Maximum history window to learn; available history may be shorter.")
    p.add_argument("--initial-balance", type=float, default=10000.0)
    p.add_argument("--sleep", type=float, default=0.5)
    p.add_argument("--max-chunks", type=int, default=0)
    a = p.parse_args()
    if a.years <= 0:
        raise SystemExit("--years must be positive")
    result = run(a.symbol, a.years, a.initial_balance, a.sleep, a.max_chunks)
    assert result.get("status") == "COMPLETED"


if __name__ == "__main__":
    main()
