"""One-symbol autonomous historical acquisition + Brain/backtest runner."""
from __future__ import annotations
import argparse, glob, json, os, sys
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
    # Bound terminal history requests on the production host; a 10-year M1 request
    # otherwise asks MT4 for more than five million bars and can starve live research.
    caps = {"M1":100000,"M5":50000,"M15":30000,"M30":20000,"H1":15000,
            "H4":10000,"D1":5000,"W1":2000,"MN1":600}
    requested = max(100, int((years * 366 * 24 * 60) / minutes) + 100)
    return min(requested, caps[tf])


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
    if not hb or hb.get("login") != SIGNAL_LOGIN or hb.get("server") != SIGNAL_SERVER or hb.get("is_demo") is not False:
        raise RuntimeError(
            "Historical acquisition requires the authorized read-only MT4 Signal terminal "
            f"for {symbol}; no order operations are permitted."
        )
    provider = MT4HistoricalDataProvider()
    acquisition = MT4HistoryAcquisition(bridge, provider)
    manifests = []
    for tf in TIMEFRAMES:
        try:
            item = acquisition.acquire(symbol, tf, required_bars(tf, max_years), allow_partial=True)
            actual_days = max(0.0, (item["last_time"] - item["first_time"]) / 86400.0)
            if actual_days < 1.0:
                raise RuntimeError("fewer than two distinct days of bars")
            item["requested_max_years"] = max_years
            item["available_days"] = actual_days
            item["status"] = "READY"
            manifests.append(item)
        except Exception as exc:
            # One unsupported/missing timeframe must not abort learning for every other usable timeframe.
            manifests.append({
                "symbol": symbol.upper(), "timeframe": tf, "source": "MT4_BROKER_HST",
                "status": "SKIPPED", "reason": f"{type(exc).__name__}: {str(exc)[:180]}",
                "available_days": 0.0, "synthetic_data": False, "future_data_injected": False,
            })
    ready = [item for item in manifests if item.get("status") == "READY"]
    if not ready:
        raise RuntimeError(f"No usable broker history for {symbol}; all timeframes were unavailable.")
    # This is the longest available window across acquired timeframes; the selected
    # learning window is computed later after the configured timeframe filter is applied.
    longest_available_years = min(max_years, max(item["available_days"] / 365.0 for item in ready))
    return manifests, longest_available_years


def run(symbol: str, max_years: float, initial_balance: float, sleep_sec: float,
        max_chunks: int = 0) -> dict:
    # Keep this long-running queue's checkpoints/memory separate from manual and supervisor backtests.
    root = Path(os.getenv("YARTRADER_HISTORICAL_LEARNING_ROOT", "runtime_logs/backtest_learning/historical_queue"))
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
    usable_timeframes = {item["timeframe"] for item in manifests if item.get("status") == "READY"}
    skipped_reasons = {item["timeframe"]: item.get("reason", "No usable history")
                       for item in manifests if item.get("status") != "READY"}
    # Run H1 first; allow the production host to limit historical training to a bounded timeframe set.
    learning_order = ("H1", "M15", "M5", "M30", "H4", "D1", "M1", "W1", "MN1")
    raw_timeframes = os.getenv("YARTRADER_HISTORICAL_LEARNING_TIMEFRAMES", "").strip()
    if raw_timeframes:
        requested_timeframes = {tf.strip().upper() for tf in raw_timeframes.replace(";", ",").split(",") if tf.strip()}
        invalid_timeframes = requested_timeframes - set(TIMEFRAMES)
        if invalid_timeframes:
            raise ValueError(f"Unsupported historical learning timeframes: {sorted(invalid_timeframes)}")
        learning_order = tuple(tf for tf in learning_order if tf in requested_timeframes)
    if not learning_order:
        raise RuntimeError("No historical learning timeframes were configured.")
    selected_ready = [item for item in manifests
                      if item.get("timeframe") in learning_order and item.get("status") == "READY"]
    if not selected_ready:
        raise RuntimeError(
            f"None of the configured timeframes have usable broker history for {symbol.upper()}: {list(learning_order)}"
        )
    selected_windows = [max(0.0, float(item.get("available_days", 0.0))) / 365.0
                        for item in selected_ready]
    effective_years = min(max_years, min(selected_windows))
    longest_available_years = min(max_years, max(selected_windows))
    # Rewrite the acquisition report after applying the selected-timeframe filter so
    # `effective_learning_years` cannot misleadingly claim 10 years for short H1/M15 data.
    (symbol_dir / "acquisition_manifest.json").write_text(
        json.dumps({
            "schema": 2, "symbol": symbol.upper(),
            "source": "MT4_BROKER_HST",
            "account": SIGNAL_LOGIN, "server": SIGNAL_SERVER,
            "synthetic_data": False, "future_data_injected": False,
            "requested_max_years": max_years,
            "effective_learning_years": effective_years,
            "longest_available_history_years": longest_available_years,
            "learning_timeframes": list(learning_order),
            "timeframes": manifests,
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2), encoding="utf-8"
    )
    results = {}
    coverage_by_timeframe = {
        item["timeframe"]: max(0.0, float(item.get("available_days", 0.0))) / 365.0
        for item in selected_ready
    }
    for tf in learning_order:
        if tf not in usable_timeframes:
            results[tf] = {"status": "SKIPPED", "reason": skipped_reasons.get(tf, "No usable history")}
            continue
        # Use the actual coverage of this timeframe, not the requested ten-year
        # maximum. This keeps checkpoints/results from claiming a longer backtest
        # window than the source HST data can support.
        timeframe_years = min(max_years, coverage_by_timeframe[tf])
        result = run_staged_backtest(
            symbol.upper(), tf, timeframe_years, initial_balance, root,
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


def _try_acquire_windows_lock(path: Path):
    """Prevent overlapping historical jobs for the same symbol across service restarts."""
    import msvcrt
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return None
    return handle


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
    lock_root = Path(os.getenv("YARTRADER_HISTORICAL_LEARNING_ROOT", "runtime_logs/backtest_learning/historical_queue"))
    lock_handle = _try_acquire_windows_lock(
        lock_root / "historical_staging" / a.symbol.upper() / ".worker.lock"
    )
    if lock_handle is None:
        print(f"Historical worker already active for {a.symbol.upper()}; refusing duplicate run.")
        raise SystemExit(75)
    import msvcrt
    try:
        result = run(a.symbol, a.years, a.initial_balance, a.sleep, a.max_chunks)
        assert result.get("status") == "COMPLETED"
    finally:
        try:
            lock_handle.seek(0)
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            lock_handle.close()


if __name__ == "__main__":
    main()
