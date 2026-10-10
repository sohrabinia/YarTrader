"""Sequential real-history research cycle: XAUUSD first, then EURUSD.

For each market: baseline on a held-out chronological segment -> learn only on
the earlier training segment -> re-run the same held-out segment with learned
memory. This is research/backtesting only; it never submits broker orders.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SYMBOL_ORDER = ("XAUUSD", "EURUSD")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(tmp, path)


def fetch_mt5_history(symbol: str, timeframe: str, years: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch actual candles from the local MT5 terminal; fail closed on missing data."""
    import MetaTrader5 as mt5

    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    tf = timeframe.upper()
    if tf not in tf_map:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if not mt5.initialize():
        raise RuntimeError(f"MT5 terminal unavailable: {mt5.last_error()}")
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=365 * years + 30)
        rates = mt5.copy_rates_range(symbol, tf_map[tf], start, end)
        if rates is None or len(rates) < 120:
            raise RuntimeError(
                f"Insufficient real MT5 history for {symbol}/{tf}: "
                f"{0 if rates is None else len(rates)} bars; last_error={mt5.last_error()}"
            )
        candles = [{
            "timestamp": datetime.fromtimestamp(int(row["time"]), timezone.utc).isoformat(),
            "open": float(row["open"]), "high": float(row["high"]),
            "low": float(row["low"]), "close": float(row["close"]),
            "volume": float(row["tick_volume"]),
        } for row in rates]
        return candles, {
            "data_source": "MT5_TERMINAL_HISTORY",
            "history_start": candles[0]["timestamp"],
            "history_end": candles[-1]["timestamp"],
            "history_years_requested": years,
            "history_bars": len(candles),
        }
    finally:
        mt5.shutdown()


def metric_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    trades = result.get("closed_trades") or []
    wins = sum(1 for t in trades if t.get("outcome") == "WIN")
    losses = sum(1 for t in trades if t.get("outcome") == "LOSS")
    net_r = []
    for trade in trades:
        try:
            net_r.append(float(trade.get("r_multiple", 0.0)))
        except (TypeError, ValueError):
            continue
    gross_profit = sum(max(0.0, float(t.get("pnl", 0.0))) for t in trades)
    gross_loss = abs(sum(min(0.0, float(t.get("pnl", 0.0))) for t in trades))
    return {
        "total_trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(100.0 * wins / len(trades), 2) if trades else 0.0,
        "net_pnl": result.get("net_pnl"),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (None if not gross_profit else "infinite"),
        "mean_r_multiple": round(sum(net_r) / len(net_r), 5) if net_r else None,
        "learning_updates_count": result.get("learning_updates_count", 0),
    }


def classify_cycle_status(results: list[dict[str, Any]]) -> dict[str, Any]:
    execution_completed = all(r.get("status") in {
        "COMPLETED_WITH_LEARNING", "COMPLETED_EXPERIENCE_LEARNING_NO_PATTERN_PROMOTION",
        "LEARNING_UPDATES_REPORTED_MEMORY_DELTA_UNCONFIRMED", "COMPLETED_NO_LEARNING_UPDATES",
    } for r in results)
    learning_verified = bool(results) and all(
        r.get("status") == "COMPLETED_WITH_LEARNING" for r in results
    )
    if learning_verified:
        overall_status = "COMPLETED_WITH_VERIFIED_LEARNING"
    elif execution_completed:
        overall_status = "COMPLETED_EXECUTION_LEARNING_UNVERIFIED"
    else:
        overall_status = "PARTIALLY_BLOCKED"
    return {
        "status": overall_status,
        "execution_completed": execution_completed,
        "learning_verified_for_all_symbols": learning_verified,
    }


def run_symbol_cycle(symbol: str, timeframe: str, years: int, train_fraction: float,
                     initial_balance: float, run_root: Path) -> dict[str, Any]:
    from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine

    started = datetime.now(timezone.utc).isoformat()
    try:
        candles, source = fetch_mt5_history(symbol, timeframe, years)
    except Exception as exc:
        return {"symbol": symbol, "status": "BLOCKED_NO_REAL_HISTORY", "error": str(exc),
                "started_at": started, "broker_orders_submitted": 0}

    split = int(len(candles) * train_fraction)
    training, heldout = candles[:split], candles[split:]
    if len(training) < 100 or len(heldout) < 60:
        return {"symbol": symbol, "status": "BLOCKED_INSUFFICIENT_SPLIT",
                "history": source, "training_bars": len(training), "heldout_bars": len(heldout),
                "started_at": started, "broker_orders_submitted": 0}

    # Baseline and learned evaluation have isolated memories; held-out candles are identical.
    baseline = BacktestAndLearningEngine(storage_dir=str(run_root / f"baseline_{symbol}"), memory_autosave_every=250)
    baseline_result = baseline.run_backtest(
        symbol, timeframe, heldout, initial_balance=initial_balance,
        learn_from_outcomes=False,
    )
    baseline.get_market_memory(symbol).flush_event_persistence()
    baseline_metrics = metric_snapshot(baseline_result)

    learner = BacktestAndLearningEngine(storage_dir=str(ROOT / "runtime_logs" / "sequential_learning_memory" / f"learned_{symbol}"), memory_autosave_every=250)
    memory = learner.get_market_memory(symbol)
    memory_before = memory.get_learning_statistics()
    training_result = learner.run_backtest(
        symbol, timeframe, training, initial_balance=initial_balance,
        learn_from_outcomes=True,
    )
    memory_after_training = memory.get_learning_statistics()

    # Freeze a copy of the post-training state for held-out evaluation. The evaluation
    # must not mutate the persistent training memory with held-out observations.
    import shutil
    memory.flush_event_persistence()
    evaluation_storage = run_root / f"evaluation_learned_{symbol}"
    shutil.copytree(learner.storage_dir, evaluation_storage)
    evaluator = BacktestAndLearningEngine(storage_dir=str(evaluation_storage), memory_autosave_every=250)
    learned_result = evaluator.run_backtest(
        symbol, timeframe, heldout, initial_balance=initial_balance,
        learn_from_outcomes=False,
    )
    learned_metrics = metric_snapshot(learned_result)
    updates = int(training_result.get("learning_updates_count", 0))
    changed_experiences = (
        int(memory_after_training.get("total_experiences", 0))
        - int(memory_before.get("total_experiences", 0))
    )
    new_patterns = (
        int(memory_after_training.get("patterns_created", 0))
        - int(memory_before.get("patterns_created", 0))
    )
    new_concepts = (
        int(memory_after_training.get("concepts_learned", 0))
        - int(memory_before.get("concepts_learned", 0))
    )
    if updates > 0 and changed_experiences > 0 and (new_patterns > 0 or new_concepts > 0):
        status = "COMPLETED_WITH_LEARNING"
    elif updates > 0 and changed_experiences > 0:
        status = "COMPLETED_EXPERIENCE_LEARNING_NO_PATTERN_PROMOTION"
    elif updates > 0:
        status = "LEARNING_UPDATES_REPORTED_MEMORY_DELTA_UNCONFIRMED"
    else:
        status = "COMPLETED_NO_LEARNING_UPDATES"

    return {
        "symbol": symbol, "status": status, "started_at": started,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "data_source": source["data_source"], "history": source,
        "train_window": {"bars": len(training), "start": training[0]["timestamp"], "end": training[-1]["timestamp"]},
        "heldout_window": {"bars": len(heldout), "start": heldout[0]["timestamp"], "end": heldout[-1]["timestamp"]},
        "baseline_heldout": baseline_metrics,
        "training": metric_snapshot(training_result),
        "memory_before": memory_before,
        "memory_after_training": memory_after_training,
        "new_experiences": changed_experiences,
        "new_patterns_created": new_patterns,
        "new_concepts_learned": new_concepts,
        "learning_updates_count": updates,
        "learned_heldout": learned_metrics,
        "heldout_delta": {
            "net_pnl": (learned_metrics["net_pnl"] - baseline_metrics["net_pnl"])
                if isinstance(learned_metrics.get("net_pnl"), (int, float)) and isinstance(baseline_metrics.get("net_pnl"), (int, float)) else None,
            "trades_delta": learned_metrics["total_trades"] - baseline_metrics["total_trades"],
            "win_rate_percentage_points": round(learned_metrics["win_rate_pct"] - baseline_metrics["win_rate_pct"], 2),
        },
        "validation_note": "Improvement is not assumed; compare held-out metrics and require repeatable out-of-sample evidence.",
        "broker_orders_submitted": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--initial-balance", type=float, default=10000.0)
    parser.add_argument("--output-dir", default="runtime_logs/sequential_learning_cycles")
    args = parser.parse_args()
    if args.years < 1 or not 0.5 <= args.train_fraction <= 0.85:
        parser.error("--years must be >= 1 and --train-fraction must be between 0.50 and 0.85")

    run_id = "cycle-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_root = ROOT / args.output_dir / run_id
    results = []
    cycle_started = datetime.now(timezone.utc).isoformat()
    # Strictly sequential: finish and persist gold's result before starting EURUSD.
    # A failure on one symbol is recorded and must not silently skip the next symbol.
    for symbol in SYMBOL_ORDER:
        try:
            result = run_symbol_cycle(symbol, args.timeframe, args.years, args.train_fraction,
                                      args.initial_balance, run_root)
        except Exception as exc:
            result = {
                "symbol": symbol, "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "broker_orders_submitted": 0,
            }
        results.append(result)
        atomic_json(run_root / f"{symbol}_result.json", result)
        print(f"{symbol}: {result['status']}", flush=True)

    status_summary = classify_cycle_status(results)
    report = {
        "run_id": run_id, **status_summary,
        "started_at": cycle_started,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "symbol_order": list(SYMBOL_ORDER), "timeframe": args.timeframe.upper(),
        "years_requested": args.years, "train_fraction": args.train_fraction,
        "market_data_fabricated": False, "broker_orders_submitted": 0,
        "results": results,
    }
    atomic_json(run_root / "cycle_report.json", report)
    print(f"Report: {run_root / 'cycle_report.json'}", flush=True)
    return 0 if status_summary["learning_verified_for_all_symbols"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
