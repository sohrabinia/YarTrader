"""Honest chronological training/holdout evaluation; never sends broker orders.

The first 70% of each real MT4 HST series is used for adaptive learning. The
last 30% is evaluated with outcome-learning disabled. Reports are isolated
from production memories and include raw-data hashes and exact date boundaries.
"""
from __future__ import annotations
import argparse
from bisect import bisect_right
import hashlib
import json
import math
import os
import sys
import uuid
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.Application.Backtesting.backtest_learning_engine import BacktestAndLearningEngine
from src.Data.Providers.MT4.historical import MT4HistoricalDataProvider
from src.Risk.Services.professional_risk_engine import ProductionRiskPolicy
from src.Application.Deployment.sqlite_event_store import SQLiteEventStore


def iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), timezone.utc).isoformat()


def _append_backtest_journal_events(
    trades: list[dict], *, run_id: str, symbol: str, decision_timeframe: str,
    cohort: str, data_file: str,
) -> int:
    """Persist each simulated closed trade to the shared append-only journal."""
    if not trades:
        return 0
    store = SQLiteEventStore(ROOT / "runtime_logs" / "yartrader_events.sqlite3")
    written = 0
    for trade in trades:
        def parse_time(value):
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(float(value), timezone.utc)
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)

        try:
            entry_dt = parse_time(trade.get("entry_time"))
            exit_dt = parse_time(trade.get("exit_time"))
        except (TypeError, ValueError, OverflowError, OSError):
            # Never fabricate timestamps for a trade whose source timestamps are missing.
            entry_dt = exit_dt = None
        event = {
            "event": "backtest_trade_closed",
            "trade_type": "BACKTEST",
            "backtest_run_id": run_id,
            "backtest_cohort": cohort,
            "trade_id": trade.get("trade_id"),
            "symbol": str(trade.get("symbol") or symbol).upper(),
            "strategy_style": str(trade.get("strategy") or "UNKNOWN").upper(),
            "direction": trade.get("direction"),
            "decision_timeframe": decision_timeframe.upper(),
            "setup_timeframe": str(trade.get("setup_timeframe") or "UNKNOWN").upper(),
            "entry_timeframe": decision_timeframe.upper(),
            "execution_timeframe": decision_timeframe.upper(),
            "context_timeframes": (
                trade.get("market_context", {}).get("timeframes_considered", [])
                if isinstance(trade.get("market_context"), dict) else []
            ),
            "entry_price": trade.get("entry"),
            "exit_price": trade.get("exit_price"),
            "stop_loss": trade.get("stop_loss"),
            "take_profit": trade.get("take_profit"),
            "exit_reason": trade.get("exit_reason"),
            "result": trade.get("outcome"),
            "pnl_net_usd": trade.get("pnl"),
            "r_multiple": trade.get("r_multiple"),
            "mfe": trade.get("mfe"),
            "mae": trade.get("mae"),
            "confidence": trade.get("confidence"),
            "reasoning": trade.get("reasoning") or [],
            "market_context": trade.get("market_context") or {},
            "data_source": "LOCAL_MT4_BROKER_HST_REAL_HISTORY",
            "data_file": data_file,
            "synthetic_data": False,
            "broker_orders_sent": 0,
            "entry_time_utc": entry_dt.isoformat() if entry_dt else None,
            "exit_time_utc": exit_dt.isoformat() if exit_dt else None,
            "entry_weekday": entry_dt.strftime("%A") if entry_dt else None,
            "entry_day_of_month": entry_dt.day if entry_dt else None,
            "entry_month": entry_dt.month if entry_dt else None,
            "entry_year": entry_dt.year if entry_dt else None,
            "entry_session_utc": (
                "ASIA" if entry_dt.hour * 60 + entry_dt.minute < 420 else
                "LONDON" if entry_dt.hour * 60 + entry_dt.minute < 720 else
                "NEW_YORK_OVERLAP" if entry_dt.hour * 60 + entry_dt.minute < 960 else
                "NEW_YORK" if entry_dt.hour * 60 + entry_dt.minute < 1260 else
                "LATE_US_OR_ROLLOVER"
            ) if entry_dt else None,
            "post_trade_conclusion": (
                f"Backtest outcome={trade.get('outcome')}; net PnL after the simulator's configured "
                f"friction={trade.get('pnl')}; cohort={cohort}. This is a simulated result, not a broker fill."
            ),
            "post_trade_review_status": "PENDING_RESEARCH_REVIEW",
            "alternative_entry_analysis": (
                "Not evaluated automatically. Replay candidate entry locations and stop placement "
                "against the recorded setup; do not infer improvement without a cost-aware replay."
            ),
            "journaled_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        store.append_important_event(event, source=f"backtest:{run_id}")
        written += 1
    return written


def metrics(trades: list[dict], initial: float, final: float) -> dict:
    pnls = [float(t.get("pnl", 0.0)) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    curve = [float(initial)]
    for pnl in pnls:
        curve.append(curve[-1] + pnl)
    peak = curve[0]
    max_dd = 0.0
    for value in curve:
        peak = max(peak, value)
        if peak > 0:
            max_dd = max(max_dd, (peak - value) / peak * 100.0)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(trades) * 100.0, 3) if trades else 0.0,
        "initial_balance": round(initial, 2),
        "final_balance": round(final, 2),
        "net_pnl": round(final - initial, 2),
        "return_pct": round((final / initial - 1.0) * 100.0, 4) if initial else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (None if not wins else "infinite_no_losses"),
        "expectancy_usd_per_trade": round(sum(pnls) / len(pnls), 4) if pnls else 0.0,
        "max_closed_trade_drawdown_pct": round(max_dd, 4),
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
    }


def run_symbol(symbol: str, timeframe: str, initial_balance: float, output_root: Path, train_fraction: float) -> dict:
    provider = MT4HistoricalDataProvider()
    source_path = provider._history_file(symbol, timeframe)
    if not source_path.exists():
        raise RuntimeError(f"No real broker HST history for {symbol}/{timeframe}: {source_path}")
    raw = source_path.read_bytes()
    candles = provider._read_hst(source_path)
    candles = sorted({int(c["time"]): c for c in candles}.values(), key=lambda c: int(c["time"]))
    for candle in candles:
        candle["timestamp"] = iso(int(candle["time"]))
    if len(candles) < 300:
        raise RuntimeError(f"Insufficient real history for {symbol}/{timeframe}: {len(candles)} bars")
    split = int(len(candles) * train_fraction)
    if split < 150 or len(candles) - split < 100:
        raise RuntimeError(f"Insufficient bars for chronological train/holdout split: {len(candles)}")
    train, test = candles[:split], candles[split:]

    # Load real broker history for the full Base hierarchy once. Each decision
    # receives only bars whose close time is <= the decision cutoff (no look-ahead).
    tf_seconds = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}
    mtf_rows = {}
    mtf_closed_epochs = {}
    for tf, seconds in tf_seconds.items():
        tf_path = provider._history_file(symbol, tf)
        if not tf_path.exists():
            continue
        tf_raw = provider._read_hst(tf_path)
        tf_raw = sorted({int(row["time"]): row for row in tf_raw}.values(), key=lambda row: int(row["time"]))
        normalized = []
        closed = []
        for row in tf_raw:
            stamp = int(row["time"])
            normalized.append({
                "timestamp": iso(stamp), "time": stamp,
                "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
                "volume": float(row.get("tick_volume", row.get("volume", 0)) or 0),
            })
            closed.append(stamp + seconds)
        mtf_rows[tf] = normalized
        mtf_closed_epochs[tf] = closed
    if not all(tf in mtf_rows and len(mtf_rows[tf]) >= 50 for tf in ("M1", "M5", "M15", "M30", "H1", "H4", "D1")):
        missing = [tf for tf in tf_seconds if tf not in mtf_rows or len(mtf_rows[tf]) < 50]
        raise RuntimeError(f"Insufficient real multi-timeframe HST history for Base hierarchy: {missing}")

    def all_timeframe_provider(cutoff_time):
        cutoff = cutoff_time if isinstance(cutoff_time, datetime) else datetime.fromisoformat(str(cutoff_time).replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        cutoff_epoch = cutoff.timestamp()
        result = {}
        for tf, rows in mtf_rows.items():
            count = bisect_right(mtf_closed_epochs[tf], cutoff_epoch)
            if count >= 50:
                result[tf] = rows[max(0, count - 500):count]
        return result

    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{symbol}_{uuid.uuid4().hex[:8]}"
    memory_dir = output_root / run_id / "isolated_brain_memory"
    memory_dir.mkdir(parents=True, exist_ok=False)
    engine = BacktestAndLearningEngine(storage_dir=str(memory_dir), memory_autosave_every=500, learning_interval_bars=1)
    print(f"[{symbol}] source bars={len(candles)} train={len(train)} holdout={len(test)}; training adaptive model", flush=True)

    train_result = engine.run_backtest(
        symbol, timeframe, train, initial_balance=initial_balance,
        start_index=50, context_window=500, all_timeframe_candles_provider=all_timeframe_provider, learn_from_outcomes=True,
        autonomous_exploration_mode=True,
    )
    trained_state = dict(train_result.get("state") or {})
    trained_balance = float(trained_state.get("balance", initial_balance))
    train_trades = train_result.get("closed_trades") or []
    train_journal_events = _append_backtest_journal_events(
        train_trades, run_id=run_id, symbol=symbol, decision_timeframe=timeframe,
        cohort="TRAIN_LEARNED", data_file=str(source_path),
    )
    print(f"[{symbol}] training complete: trades={len(train_trades)} journaled={train_journal_events} pnl={train_result.get('net_pnl')}; checking bootstrap viability", flush=True)
    if not train_trades:
        return {
            "run_id": run_id, "symbol": symbol.upper(), "timeframe": timeframe.upper(),
            "status": "INCONCLUSIVE_NO_TRAINING_TRADES", "evaluation_conclusive": False,
            "data_source": "LOCAL_MT4_BROKER_HST_REAL_HISTORY", "data_file": str(source_path),
            "data_sha256": hashlib.sha256(raw).hexdigest(), "synthetic_data": False,
            "future_data_injected": False, "train_fraction": train_fraction,
            "train_start_utc": iso(int(train[0]["time"])), "train_end_utc": iso(int(train[-1]["time"])),
            "holdout_start_utc": iso(int(test[0]["time"])), "holdout_end_utc": iso(int(test[-1]["time"])),
            "total_bars": len(candles), "train_bars": len(train), "holdout_bars": len(test),
            "initial_balance_usd": initial_balance, "canonical_risk_pct": ProductionRiskPolicy.TARGET_RISK_PCT,
            "daily_drawdown_limit_pct": None, "daily_drawdown_gate": "BYPASSED_IN_AUTONOMOUS_EXPLORATION", "exploration_mode": True,
            "train": metrics(train_trades, initial_balance, trained_balance),
            "holdout_learned_model_frozen": None, "holdout_untrained_baseline_frozen": None,
            "holdout_learning_updates": None, "holdout_learning_frozen": None,
            "train_learning_updates": int(trained_state.get("learning_updates_count", 0)),
            "reason": "No trades passed the real multi-timeframe Base hierarchy, M1 retest/rejection, structural destination, and net reward/risk gates in the training segment. This run is inconclusive; no synthetic trades or fallback strategy were injected.",
            "broker_orders_sent": 0, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    print(f"[{symbol}] training has outcomes; warming untrained baseline", flush=True)
    # A fair baseline sees the same chronological market history for warm-up but
    # never learns from outcomes. It gets a separate empty memory and a fresh wallet.
    baseline_dir = output_root / run_id / "isolated_baseline_memory"
    baseline_dir.mkdir(parents=True, exist_ok=False)
    baseline_engine = BacktestAndLearningEngine(
        storage_dir=str(baseline_dir), memory_autosave_every=500, learning_interval_bars=1
    )
    baseline_engine.run_backtest(
        symbol, timeframe, train, initial_balance=initial_balance,
        start_index=50, context_window=500, all_timeframe_candles_provider=all_timeframe_provider, learn_from_outcomes=False,
        autonomous_exploration_mode=True,
    )
    trained_state = dict(train_result.get("state") or {})
    trained_balance = float(trained_state.get("balance", initial_balance))
    # Purge an open train-period position at the boundary; it is neither carried
    # into the holdout nor counted as a closed train/holdout trade.
    test_state = {
        "balance": trained_balance,
        "equity": trained_balance,
        "open_position": None,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "breakevens": 0,
        "learning_updates_count": 0,
    }
    test_result = engine.run_backtest(
        symbol, timeframe, candles, initial_balance=trained_balance,
        start_index=split, context_window=500, state=test_state,
        all_timeframe_candles_provider=all_timeframe_provider, learn_from_outcomes=False,
        autonomous_exploration_mode=True,
    )
    baseline_test_state = {
        "balance": initial_balance, "equity": initial_balance, "open_position": None,
        "total_trades": 0, "wins": 0, "losses": 0, "breakevens": 0,
        "learning_updates_count": 0,
    }
    baseline_result = baseline_engine.run_backtest(
        symbol, timeframe, candles, initial_balance=initial_balance,
        start_index=split, context_window=500, state=baseline_test_state,
        all_timeframe_candles_provider=all_timeframe_provider, learn_from_outcomes=False,
        autonomous_exploration_mode=True,
    )
    print(f"[{symbol}] holdout complete: learned_pnl={test_result.get('net_pnl')} baseline_pnl={baseline_result.get('net_pnl')}", flush=True)
    test_trades = test_result.get("closed_trades") or []
    baseline_trades = baseline_result.get("closed_trades") or []
    learned_holdout_journal_events = _append_backtest_journal_events(
        test_trades, run_id=run_id, symbol=symbol, decision_timeframe=timeframe,
        cohort="HOLDOUT_LEARNED_FROZEN", data_file=str(source_path),
    )
    baseline_holdout_journal_events = _append_backtest_journal_events(
        baseline_trades, run_id=run_id, symbol=symbol, decision_timeframe=timeframe,
        cohort="HOLDOUT_UNTRAINED_BASELINE", data_file=str(source_path),
    )
    frozen_learning_updates = sum(
        1 for t in test_trades
        if (t.get("learning_update") or {}).get("status") != "FROZEN_EVALUATION_NO_LEARNING"
    )
    baseline_learning_updates = sum(
        1 for t in baseline_trades
        if (t.get("learning_update") or {}).get("status") != "FROZEN_EVALUATION_NO_LEARNING"
    )
    final_balance = float((test_result.get("state") or {}).get("balance", trained_balance))
    baseline_final_balance = float((baseline_result.get("state") or {}).get("balance", initial_balance))
    sample_adequate = len(test_trades) >= 30 and len(baseline_trades) >= 30
    return {
        "run_id": run_id,
        "journal_events_written": train_journal_events + learned_holdout_journal_events + baseline_holdout_journal_events,
        "status": "COMPLETED" if sample_adequate and frozen_learning_updates == 0 and baseline_learning_updates == 0 else "INCONCLUSIVE_SMALL_SAMPLE_OR_LEARNING_LEAK",
        "evaluation_conclusive": sample_adequate and frozen_learning_updates == 0 and baseline_learning_updates == 0,
        "symbol": symbol.upper(),
        "timeframe": timeframe.upper(),
        "data_source": "LOCAL_MT4_BROKER_HST_REAL_HISTORY",
        "data_file": str(source_path),
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "synthetic_data": False,
        "future_data_injected": False,
        "train_fraction": train_fraction,
        "train_start_utc": iso(int(train[0]["time"])),
        "train_end_utc": iso(int(train[-1]["time"])),
        "holdout_start_utc": iso(int(test[0]["time"])),
        "holdout_end_utc": iso(int(test[-1]["time"])),
        "total_bars": len(candles),
        "train_bars": len(train),
        "holdout_bars": len(test),
        "initial_balance_usd": initial_balance,
        "canonical_risk_pct": ProductionRiskPolicy.TARGET_RISK_PCT,
        "daily_drawdown_limit_pct": None, "daily_drawdown_gate": "BYPASSED_IN_AUTONOMOUS_EXPLORATION", "exploration_mode": True,
        "train": metrics(train_result.get("closed_trades") or [], initial_balance, trained_balance),
        "holdout_learned_model_frozen": metrics(test_trades, trained_balance, final_balance),
        "holdout_untrained_baseline_frozen": metrics(
            baseline_trades, initial_balance,
            float((baseline_result.get("state") or {}).get("balance", initial_balance)),
        ),
        "holdout_return_delta_percentage_points": round(
            metrics(test_trades, trained_balance, final_balance)["return_pct"]
            - metrics(baseline_trades, initial_balance,
                      float((baseline_result.get("state") or {}).get("balance", initial_balance)))["return_pct"], 4
        ),
        "holdout_learning_updates": frozen_learning_updates,
        "holdout_learning_frozen": frozen_learning_updates == 0,
        "baseline_holdout_learning_updates": sum(
            1 for t in baseline_trades
            if (t.get("learning_update") or {}).get("status") != "FROZEN_EVALUATION_NO_LEARNING"
        ),
        "train_learning_updates": int((train_result.get("state") or {}).get("learning_updates_count", 0)),
        "boundary_open_train_position_discarded": bool(trained_state.get("open_position")),
        "execution_model_caveat": "OHLC-bar simulation with configured asset-class friction; historical tick-level bid/ask spread, slippage, swap, broker-specific commission, historical contract changes and broker minimum lot/step are not reconstructed. Do not treat this report alone as live-profit proof.",
        "broker_orders_sent": 0,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="EURUSD,XAUUSD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--initial-balance", type=float, default=10000.0)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--output", default="runtime_logs/backtest_validation")
    args = parser.parse_args()
    if not 0.5 <= args.train_fraction <= 0.9:
        raise SystemExit("--train-fraction must be between 0.50 and 0.90")
    if not math.isfinite(args.initial_balance) or args.initial_balance <= 0:
        raise SystemExit("--initial-balance must be positive")
    reports = []
    errors = []
    root = (ROOT / args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for symbol in [s.strip().upper() for s in args.symbols.split(",") if s.strip()]:
        try:
            reports.append(run_symbol(symbol, args.timeframe.upper(), args.initial_balance, root, args.train_fraction))
        except Exception as exc:
            traceback.print_exc()
            errors.append({"symbol": symbol, "error": f"{type(exc).__name__}: {exc}"})
    payload = {
        "schema": 1,
        "method": "CHRONOLOGICAL_70_30_ADAPTIVE_TRAIN_FROZEN_HOLDOUT",
        "risk_policy_pct": ProductionRiskPolicy.TARGET_RISK_PCT,
        "lookahead_control": "Train ends before holdout starts; holdout outcome-learning and scheduled learning cycles disabled.",
        "reports": reports,
        "errors": errors,
        "complete": bool(reports) and not errors,
        "evaluation_conclusive": bool(reports) and not errors and all(r.get("evaluation_conclusive", False) for r in reports),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    out = root / f"honest_walk_forward_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"report_path": str(out), "complete": payload["complete"],
        "evaluation_conclusive": payload["evaluation_conclusive"], "reports": [
        {"symbol": r["symbol"], "status": r.get("status"), "bars": r["total_bars"], "train": r["train"],
         "holdout_learned": r.get("holdout_learned_model_frozen"),
         "holdout_baseline": r.get("holdout_untrained_baseline_frozen"),
         "holdout_return_delta_pp": r.get("holdout_return_delta_percentage_points"),
         "reason": r.get("reason"), "data_sha256": r["data_sha256"]} for r in reports
    ], "errors": errors}, indent=2, ensure_ascii=False))
    if not payload["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
