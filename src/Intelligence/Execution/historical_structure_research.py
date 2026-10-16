"""Causal multi-timeframe swing levels and historical reaction study.

Only closed OHLC bars are used. Swing points become available after right-side
confirmation bars; outcome measurements begin after that confirmation, avoiding look-ahead.
This is descriptive research, not a claim of profitability.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping
import math

TIMEFRAMES = ("MN1", "W1", "D1", "H4", "H1", "M15", "M5", "M1")


def _stamp(row: Mapping[str, Any]) -> int:
    value = row.get("timestamp", row.get("time", 0))
    try:
        if isinstance(value, (int, float)):
            return int(value)
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError, OverflowError):
        return 0


def _session(epoch: int) -> str:
    hour = datetime.fromtimestamp(epoch, timezone.utc).hour
    if 0 <= hour < 7:
        return "ASIA"
    if 7 <= hour < 12:
        return "LONDON"
    if 12 <= hour < 16:
        return "NEW_YORK"
    if 16 <= hour < 21:
        return "NEW_YORK_LATE"
    return "ROLLOVER"


def _bar_close_time(ts: int, timeframe: str) -> int:
    if timeframe == "MN1":
        dt = datetime.fromtimestamp(ts, timezone.utc)
        if dt.month == 12:
            return int(datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc).timestamp())
        return int(datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc).timestamp())
    seconds = {"W1": 604800, "D1": 86400, "H4": 14400, "H1": 3600,
               "M15": 900, "M5": 300, "M1": 60}.get(timeframe, 60)
    return ts + seconds


def _clean(rows: Any, now: int, timeframe: str) -> List[Dict[str, float]]:
    out = []
    for row in rows or []:
        try:
            b = {key: float(row[key]) for key in ("open", "high", "low", "close")}
            ts = _stamp(row)
            close_time = _bar_close_time(ts, timeframe) if ts > 0 else 0
            if (ts > 0 and close_time <= now and all(math.isfinite(v) for v in b.values())
                    and b["low"] > 0 and b["low"] <= min(b["open"], b["close"])
                    and b["high"] >= max(b["open"], b["close"]) and b["high"] > b["low"]):
                out.append({"time": ts, "close_time": close_time, **b})
        except (TypeError, ValueError, KeyError, OverflowError):
            continue
    out.sort(key=lambda x: x["time"])
    # Duplicate timestamps distort touches and reaction counts.
    unique = {}
    for bar in out:
        unique[bar["time"]] = bar
    return list(unique.values())


def _level_research(bars: List[Dict[str, float]], pivot_index: int, kind: str,
                    timeframe: str, now: int, left: int, right: int) -> Dict[str, Any]:
    pivot = bars[pivot_index]
    is_high = kind == "SWING_HIGH"
    price = pivot["high"] if is_high else pivot["low"]
    confirmed_at = int(bars[pivot_index + right]["close_time"])
    post = bars[pivot_index + right + 1:]
    touches = rejections = breakouts = 0
    max_continuation = max_rejection = 0.0
    touch_hours: Dict[str, int] = defaultdict(int)
    touch_sessions: Dict[str, int] = defaultdict(int)
    # A touch is a later candle whose range includes the level within a small
    # local range tolerance; classify close-through separately from rejection.
    in_touch_episode = False
    for i, bar in enumerate(post):
        span = max(bar["high"] - bar["low"], price * 1e-7)
        tolerance = max(span * 0.08, price * 1e-7)
        touched = bar["low"] - tolerance <= price <= bar["high"] + tolerance
        # Count one visit episode, not every consecutive candle sitting at a level.
        if touched and not in_touch_episode:
            touches += 1
            touch_hours[str(datetime.fromtimestamp(bar["time"], timezone.utc).hour)] += 1
            touch_sessions[_session(int(bar["time"]))] += 1
            if is_high:
                if bar["close"] < price and bar["high"] >= price:
                    rejections += 1
                elif bar["close"] > price:
                    breakouts += 1
            else:
                if bar["close"] > price and bar["low"] <= price:
                    rejections += 1
                elif bar["close"] < price:
                    breakouts += 1
            # Measure the following 20 bars from the actual level visit, rather
            # than measuring arbitrary bars that never touched the level.
            future = post[i:i+20]
            if future:
                if is_high:
                    max_continuation = max(max_continuation,
                                           max(0.0, max(x["high"] for x in future) - price))
                    max_rejection = max(max_rejection,
                                        max(0.0, price - min(x["low"] for x in future)))
                else:
                    max_continuation = max(max_continuation,
                                           max(0.0, price - min(x["low"] for x in future)))
                    max_rejection = max(max_rejection,
                                        max(0.0, max(x["high"] for x in future) - price))
        in_touch_episode = touched
    return {
        "timeframe": timeframe, "type": kind, "price": round(price, 8),
        "pivot_time": pivot["time"], "confirmed_at": confirmed_at,
        "bars_left_right": {"left": left, "right": right},
        "touch_count_after_confirmation": touches, "rejection_count": rejections,
        "breakout_count": breakouts,
        "max_continuation_distance_20_bars": round(max_continuation, 8),
        "max_rejection_distance_20_bars": round(max_rejection, 8),
        "touches_by_utc_hour": dict(touch_hours),
        "touches_by_session_utc": dict(touch_sessions),
        "sample_is_descriptive_not_a_trade_win_rate": True,
    }


def analyze_historical_structure_levels(
    timeframe_candles: Mapping[str, Any], now: int | None = None,
    current_prices: Mapping[str, float] | None = None, pivot_left: int = 2,
    pivot_right: int = 2, max_levels_per_side: int = 8,
) -> Dict[str, Any]:
    """Return last confirmed swing highs/lows, candle-range extremes, and outcome samples."""
    if now is None:
        now = max((_stamp(row) for rows in timeframe_candles.values() for row in (rows or [])), default=0)
    now = int(now or 0)
    if now <= 0:
        return {"status": "NO_VALID_CLOSED_CANDLES", "timeframes": {}, "current_price_context": {}}
    result: Dict[str, Any] = {}
    for tf in TIMEFRAMES:
        bars = _clean(timeframe_candles.get(tf, timeframe_candles.get(tf.lower(), [])), now, tf)
        if not bars:
            result[tf] = {"status": "NO_DATA", "bars": 0, "latest_swing_high": None,
                          "latest_swing_low": None, "levels": [], "reaction_summary": {}}
            continue
        pivots = []
        for i in range(pivot_left, len(bars) - pivot_right):
            high = bars[i]["high"]
            low = bars[i]["low"]
            left = bars[i-pivot_left:i]
            right = bars[i+1:i+1+pivot_right]
            # Strictly confirm against bars on both sides; confirmation time is
            # the last right-side bar, never the pivot bar itself.
            if all(high > x["high"] for x in left + right):
                pivots.append(_level_research(bars, i, "SWING_HIGH", tf, now, pivot_left, pivot_right))
            if all(low < x["low"] for x in left + right):
                pivots.append(_level_research(bars, i, "SWING_LOW", tf, now, pivot_left, pivot_right))
        highs = sorted((p for p in pivots if p["type"] == "SWING_HIGH"), key=lambda p: p["confirmed_at"])
        lows = sorted((p for p in pivots if p["type"] == "SWING_LOW"), key=lambda p: p["confirmed_at"])
        recent_levels = sorted(pivots, key=lambda p: p["confirmed_at"], reverse=True)[:max_levels_per_side*2]
        last = bars[-1]
        result[tf] = {
            "status": "OK", "bars": len(bars),
            "latest_swing_high": highs[-1] if highs else None,
            "latest_swing_low": lows[-1] if lows else None,
            "rolling_history_high": max(b["high"] for b in bars),
            "rolling_history_low": min(b["low"] for b in bars),
            "last_candle_time": last["time"], "last_candle_high": last["high"],
            "last_candle_low": last["low"], "levels": recent_levels,
            "reaction_summary": {
                "confirmed_swing_high_count": len(highs), "confirmed_swing_low_count": len(lows),
                "historical_touch_count": sum(p["touch_count_after_confirmation"] for p in pivots),
                "historical_rejection_count": sum(p["rejection_count"] for p in pivots),
                "historical_breakout_count": sum(p["breakout_count"] for p in pivots),
                "by_utc_session": {
                    session: sum(p["touches_by_session_utc"].get(session, 0) for p in pivots)
                    for session in ("ASIA", "LONDON", "NEW_YORK", "NEW_YORK_LATE", "ROLLOVER")
                },
                "sample_note": "Counts are overlapping level-touch observations, not independent trades or a validated win rate.",
            },
        }
    context = {}
    for tf, price in (current_prices or {}).items():
        try:
            px = float(price)
            if math.isfinite(px) and px > 0:
                tf_result = result.get(tf.upper(), {})
                levels = tf_result.get("levels", [])
                context[tf.upper()] = {
                    "price": px,
                    "nearest_swing_levels": sorted(
                        ({"type": p["type"], "price": p["price"], "distance": round(px-p["price"], 8),
                          "confirmed_at": p["confirmed_at"]} for p in levels),
                        key=lambda item: abs(item["distance"]))[:6],
                }
        except (TypeError, ValueError, OverflowError):
            continue
    return {"status": "OK", "as_of": now, "timezone_for_sessions": "UTC",
            "timeframes": result, "current_price_context": context,
            "method": {"swing_confirmation": f"{pivot_left} left / {pivot_right} right closed bars",
                       "lookahead_control": "A swing is usable only after its right-side confirmation candle closes.",
                       "reaction_horizon_bars": 20}}
