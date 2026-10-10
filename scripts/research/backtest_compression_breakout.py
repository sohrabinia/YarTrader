"""Fixed-rule, gap-aware XAUUSD M1 breakout backtest. Research only; no order routing."""
import csv
import json
import time
from array import array
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"
SOURCE = DATA / "M1.csv"
OUT = DATA / "xauusd_compression_breakout_pnl_backtest_20261010.json"

LOOKBACK = 24
ATR_LENGTH = 24
HOLD_BARS = 24
BREAK_BUFFER_ATR = 0.10
STOP_ATR = 1.0
TARGET_ATR = 1.5
MAX_GAP_SECONDS = 90
POINT_SIZE_ASSUMPTION = 0.01  # OHLC is exported to two decimals; verify against broker symbol specs.
SLIPPAGE_ROUND_TRIP_ATR = 0.05


def load_arrays():
    t, o, h, l, c, spread = array("q"), array("d"), array("d"), array("d"), array("d"), array("d")
    with SOURCE.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            try:
                ti = int(float(row["time"]))
                op, hi, lo, cl = (float(row[k]) for k in ("open", "high", "low", "close"))
                sp = float(row.get("spread") or 0)
            except (ValueError, TypeError, KeyError):
                continue
            if ti <= 0 or min(op, hi, lo, cl) <= 0 or hi < max(op, cl, lo) or lo > min(op, cl, hi):
                continue
            t.append(ti); o.append(op); h.append(hi); l.append(lo); c.append(cl); spread.append(max(0.0, sp))
    return tuple(np.frombuffer(a, dtype=np.int64 if a.typecode == "q" else np.float64) for a in (t, o, h, l, c, spread))


def build_features(times, opens, highs, lows, closes):
    n = len(times)
    atr = np.full(n, np.nan)
    prior_high = np.full(n, np.nan)
    prior_low = np.full(n, np.nan)
    compression = np.full(n, np.nan)
    gaps = np.flatnonzero(np.diff(times) > MAX_GAP_SECONDS) + 1
    bounds = [0, *gaps.tolist(), n]
    segments = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1) if bounds[i + 1] - bounds[i] > LOOKBACK + HOLD_BARS + 1]
    tr = highs - lows
    for start, end in segments:
        for i in range(start + 1, end):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        cumulative = np.concatenate(([0.0], np.cumsum(tr[start:end])))
        high_q, low_q = deque(), deque()
        for i in range(start + 1, end):
            add = i - 1
            while high_q and highs[high_q[-1]] <= highs[add]:
                high_q.pop()
            high_q.append(add)
            while low_q and lows[low_q[-1]] >= lows[add]:
                low_q.pop()
            low_q.append(add)
            oldest = i - LOOKBACK
            while high_q and high_q[0] < oldest:
                high_q.popleft()
            while low_q and low_q[0] < oldest:
                low_q.popleft()
            if i - start < LOOKBACK:
                continue
            local_i = i - start
            atr_i = (cumulative[local_i] - cumulative[local_i - LOOKBACK]) / ATR_LENGTH
            if not np.isfinite(atr_i) or atr_i <= 0:
                continue
            atr[i] = atr_i
            prior_high[i] = highs[high_q[0]]
            prior_low[i] = lows[low_q[0]]
            compression[i] = (prior_high[i] - prior_low[i]) / atr_i
    return atr, prior_high, prior_low, compression, segments


def simulate(times, opens, highs, lows, closes, spreads, atr, prior_high, prior_low, compression,
             segments, cutoff_index, compression_cut, use_compression, spread_multiplier):
    trades = []
    for start, end in segments:
        i = max(start + LOOKBACK, cutoff_index)
        next_free = i
        while i < end - 1:
            if i < next_free or not np.isfinite(atr[i]):
                i += 1
                continue
            if use_compression and not (compression[i] <= compression_cut):
                i += 1
                continue
            long_signal = closes[i] > prior_high[i] + BREAK_BUFFER_ATR * atr[i]
            short_signal = closes[i] < prior_low[i] - BREAK_BUFFER_ATR * atr[i]
            if long_signal == short_signal:
                i += 1
                continue
            direction = 1 if long_signal else -1
            entry_i = i + 1
            entry = opens[entry_i]
            risk = STOP_ATR * atr[i]
            stop = entry - direction * risk
            target = entry + direction * TARGET_ATR * atr[i]
            last_i = min(end - 1, entry_i + HOLD_BARS - 1)
            exit_i, exit_price, exit_reason = last_i, closes[last_i], "time"
            for j in range(entry_i, last_i + 1):
                if direction > 0:
                    stop_hit = lows[j] <= stop
                    target_hit = highs[j] >= target
                    if stop_hit:
                        exit_i = j
                        exit_price = min(opens[j], stop) if opens[j] < stop else stop
                        exit_reason = "stop" if not target_hit else "both_stop_first"
                        break
                    if target_hit:
                        exit_i, exit_price, exit_reason = j, target, "target"
                        break
                else:
                    stop_hit = highs[j] >= stop
                    target_hit = lows[j] <= target
                    if stop_hit:
                        exit_i = j
                        exit_price = max(opens[j], stop) if opens[j] > stop else stop
                        exit_reason = "stop" if not target_hit else "both_stop_first"
                        break
                    if target_hit:
                        exit_i, exit_price, exit_reason = j, target, "target"
                        break
            gross_r = direction * (exit_price - entry) / atr[i]
            spread_index = entry_i if direction > 0 else exit_i
            spread_cost_r = spreads[spread_index] * POINT_SIZE_ASSUMPTION / atr[i]
            trades.append({
                "signal_time": int(times[i]), "entry_time": int(times[entry_i]),
                "exit_time": int(times[exit_i]), "direction": "long" if direction > 0 else "short",
                "gross_r": float(gross_r), "spread_cost_r": float(spread_cost_r),
                "slippage_r": SLIPPAGE_ROUND_TRIP_ATR, "hold_bars": int(exit_i - entry_i + 1),
                "exit_reason": exit_reason,
            })
            next_free = exit_i + 1
            i = next_free
    return trades


def summarize(trades, spread_multiplier):
    if not trades:
        return {"trades": 0}
    net = np.asarray([
        t["gross_r"] - spread_multiplier * t["spread_cost_r"] - t["slippage_r"]
        for t in trades
    ], dtype=float)
    gross = np.asarray([t["gross_r"] for t in trades], dtype=float)
    wins = net > 0
    gross_profit = float(net[net > 0].sum())
    gross_loss = float(-net[net < 0].sum())
    equity = np.cumsum(net)
    peak = np.maximum.accumulate(np.concatenate(([0.0], equity)))[1:]
    drawdown = peak - equity
    return {
        "trades": len(trades),
        "net_win_rate": float(wins.mean()),
        "gross_mean_r": float(gross.mean()),
        "net_mean_r": float(net.mean()),
        "gross_total_r": float(gross.sum()),
        "net_total_r": float(net.sum()),
        "profit_factor_net": gross_profit / gross_loss if gross_loss > 0 else None,
        "max_drawdown_r": float(drawdown.max()) if len(drawdown) else 0.0,
        "median_hold_bars": float(np.median([t["hold_bars"] for t in trades])),
        "target_exit_rate": float(np.mean([t["exit_reason"] == "target" for t in trades])),
        "stop_exit_rate": float(np.mean([t["exit_reason"] in ("stop", "both_stop_first") for t in trades])),
        "average_spread_cost_r": float(np.mean([t["spread_cost_r"] for t in trades])),
        "slippage_assumption_r_per_round_trip": SLIPPAGE_ROUND_TRIP_ATR,
        "spread_multiplier": spread_multiplier,
    }


def main():
    started = time.time()
    times, opens, highs, lows, closes, spreads = load_arrays()
    atr, prior_high, prior_low, compression, segments = build_features(times, opens, highs, lows, closes)
    cutoff_index = len(times) // 2
    train_compression = compression[:cutoff_index]
    train_compression = train_compression[np.isfinite(train_compression)]
    if len(train_compression) < 1000:
        raise SystemExit(f"Insufficient training compression values: {len(train_compression)}")
    compression_cut = float(np.quantile(train_compression, 0.25))

    report = {
        "status": "RESEARCH_ONLY_NO_ORDER_ROUTING",
        "symbol": "XAUUSD",
        "source": str(SOURCE),
        "data": {
            "bars": len(times), "segments": len(segments),
            "first_time": int(times[0]), "last_time": int(times[-1]),
            "train_bars": cutoff_index, "test_bars": len(times) - cutoff_index,
        },
        "rule": {
            "lookback_bars": LOOKBACK, "atr_bars": ATR_LENGTH,
            "compression": "prior 24-bar high-low width / prior 24-bar ATR",
            "compression_threshold": "25th percentile fitted on first half only",
            "compression_cut": compression_cut,
            "breakout": "current close beyond prior 24-bar high/low by 0.10 ATR",
            "entry": "next bar open; one position at a time; no overlapping trades",
            "stop_atr": STOP_ATR, "target_atr": TARGET_ATR, "max_hold_bars": HOLD_BARS,
            "same_bar_stop_target": "stop first",
            "gap_policy_seconds": MAX_GAP_SECONDS,
            "costs": {
                "spread_source": "MT5 CSV spread column",
                "point_size_assumption": POINT_SIZE_ASSUMPTION,
                "point_size_warning": "Must be verified against broker XAUUSD symbol specs before treating costs as exact.",
                "slippage_round_trip_atr": SLIPPAGE_ROUND_TRIP_ATR,
                "sensitivity": "net metrics reported at 1x and 2x observed spread plus fixed 0.05 ATR round-trip slippage",
            },
        },
        "test_period": "Only the later half of the history; compression threshold frozen from the first half.",
        "strategies": {},
        "limitations": [
            "This is a fixed research rule, not a tuned or approved trading system.",
            "OHLC bars cannot reveal exact intrabar order; simultaneous stop/target hits are resolved conservatively as stop first.",
            "Point size is assumed from two-decimal OHLC and must be verified against broker symbol metadata.",
            "Results are in R/ATR units, not account currency; no lot sizing or margin model.",
        ],
    }
    for label, use_compression in (("compression_filtered_breakout", True), ("unfiltered_range_breakout", False)):
        trades = simulate(times, opens, highs, lows, closes, spreads, atr, prior_high, prior_low, compression,
                          segments, cutoff_index, compression_cut, use_compression, 1.0)
        report["strategies"][label] = {
            "trade_counts": len(trades),
            "cost_sensitivity": {
                "spread_1x": summarize(trades, 1.0),
                "spread_2x": summarize(trades, 2.0),
            },
            "trades_sample_first_20": trades[:20],
        }
    report["elapsed_seconds"] = round(time.time() - started, 2)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT), "data": report["data"], "rule": report["rule"],
        "strategies": {name: result["cost_sensitivity"] for name, result in report["strategies"].items()},
        "elapsed_seconds": report["elapsed_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
