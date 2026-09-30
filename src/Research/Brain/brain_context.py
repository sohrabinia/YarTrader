"""Point-in-time context discovery for the YarTrader Brain.

This module deliberately contains no trading strategy. It converts only data that was
known at a decision timestamp into deterministic context fingerprints. Future candles
are never admitted to the observation side of the context.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.Research.Brain.models import MarketObservation


TIMEFRAME_DELTAS = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
    "W1": timedelta(weeks=1),
}


def _iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat()


def _price_direction(a: float, b: float) -> str:
    if b > a:
        return "UP"
    if b < a:
        return "DOWN"
    return "FLAT"


def _swing_points(observations: List[MarketObservation], window: int = 2) -> List[Dict[str, Any]]:
    """Return only confirmed pivots; the pivot candle must be strictly in the past."""
    ordered = sorted(observations, key=lambda o: o.timestamp)
    points: List[Dict[str, Any]] = []
    if len(ordered) < 2 * window + 1:
        return points
    for i in range(window, len(ordered) - window):
        cur = ordered[i]
        left = ordered[i - window:i]
        right = ordered[i + 1:i + window + 1]
        if cur.high > max(x.high for x in left + right):
            points.append({"type": "SWING_HIGH", "timestamp": _iso(cur.timestamp), "price": cur.high, "index": i})
        if cur.low < min(x.low for x in left + right):
            points.append({"type": "SWING_LOW", "timestamp": _iso(cur.timestamp), "price": cur.low, "index": i})
    return points


def _structure_snapshot(observations: List[MarketObservation]) -> Dict[str, Any]:
    ordered = sorted(observations, key=lambda o: o.timestamp)
    if not ordered:
        return {"confirmed_swings": [], "latest_swing_high": None, "latest_swing_low": None, "labels": [], "breaks": []}

    swings = _swing_points(ordered)
    highs = [p for p in swings if p["type"] == "SWING_HIGH"]
    lows = [p for p in swings if p["type"] == "SWING_LOW"]

    labels: List[Dict[str, Any]] = []
    for kind, pts in (("HIGH", highs), ("LOW", lows)):
        for prev, cur in zip(pts, pts[1:]):
            if kind == "HIGH":
                label = "HH" if cur["price"] > prev["price"] else "LH"
            else:
                label = "HL" if cur["price"] > prev["price"] else "LL"
            labels.append({"label": label, "timestamp": cur["timestamp"], "price": cur["price"]})

    latest = ordered[-1]
    breaks: List[Dict[str, Any]] = []
    if highs and latest.close_price > highs[-1]["price"]:
        breaks.append({"type": "BREAK_ABOVE_LAST_SWING_HIGH", "reference": highs[-1]["price"], "timestamp": _iso(latest.timestamp)})
    if lows and latest.close_price < lows[-1]["price"]:
        breaks.append({"type": "BREAK_BELOW_LAST_SWING_LOW", "reference": lows[-1]["price"], "timestamp": _iso(latest.timestamp)})

    def enrich(point: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not point:
            return None
        age = max(0, (latest.timestamp - datetime.fromisoformat(point["timestamp"])).total_seconds())
        return {**point, "age_seconds": age, "distance_from_current": latest.close_price - point["price"]}

    return {
        "confirmed_swings": swings[-12:],
        "latest_swing_high": enrich(highs[-1] if highs else None),
        "latest_swing_low": enrich(lows[-1] if lows else None),
        "labels": labels[-12:],
        "breaks": breaks,
        "current_direction": _price_direction(ordered[0].close_price, latest.close_price),
    }


def _tf_snapshot(observations: List[MarketObservation], decision_time: datetime) -> Dict[str, Any]:
    """Snapshot is strictly point-in-time: timestamp <= decision_time."""
    ordered = sorted(
        [o for o in observations if o.timestamp <= decision_time],
        key=lambda o: o.timestamp,
    )
    if not ordered:
        return {"available": False}
    recent = ordered[-20:]
    first = recent[0]
    last = recent[-1]
    return {
        "available": True,
        "count": len(ordered),
        "last_timestamp": _iso(last.timestamp),
        "last_open": last.open_price,
        "last_high": last.high,
        "last_low": last.low,
        "last_close": last.close_price,
        "direction": _price_direction(first.close_price, last.close_price),
        "structure": _structure_snapshot(ordered),
    }


def _corr(xs: List[float], ys: List[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 3:
        return 0.0
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (denx * deny) if denx and deny else 0.0


def discover_cross_symbol_relations(
    observations_by_symbol: Dict[str, List[MarketObservation]],
    decision_time: datetime,
    primary_timeframe: str,
    max_lag: int = 5,
    min_samples: int = 6,
    min_abs_correlation: float = 0.75,
) -> List[Dict[str, Any]]:
    """Discover temporal relationships; no symbol pair is predefined."""
    aligned: Dict[str, List[MarketObservation]] = {}
    for symbol, observations in observations_by_symbol.items():
        eligible = sorted([o for o in observations if o.timestamp <= decision_time], key=lambda o: o.timestamp)
        if len(eligible) >= min_samples:
            aligned[symbol.upper()] = eligible

    result: List[Dict[str, Any]] = []
    symbols = sorted(aligned)
    for i, source in enumerate(symbols):
        for target in symbols[i + 1:]:
            a, b = aligned[source], aligned[target]
            amap = {o.timestamp: o.close_price for o in a}
            bmap = {o.timestamp: o.close_price for o in b}
            common = sorted(set(amap) & set(bmap))
            if len(common) < min_samples:
                continue
            ar = [amap[t] - amap[common[k - 1]] for k, t in enumerate(common) if k]
            br = [bmap[t] - bmap[common[k - 1]] for k, t in enumerate(common) if k]
            if len(ar) < min_samples - 1:
                continue
            for lag in range(0, max_lag + 1):
                if lag >= len(ar):
                    break
                corr_ab = _corr(ar[:-lag] if lag else ar, br[lag:] if lag else br)
                corr_ba = _corr(br[:-lag] if lag else br, ar[lag:] if lag else ar)
                if abs(corr_ab) >= min_abs_correlation:
                    result.append({
                        "source_symbol": source,
                        "target_symbol": target,
                        "direction": "SOURCE_TO_TARGET",
                        "lag_bars": lag,
                        "correlation": round(corr_ab, 6),
                        "timeframe": primary_timeframe.upper(),
                        "samples": len(ar) - lag,
                    })
                if lag and abs(corr_ba) >= min_abs_correlation:
                    result.append({
                        "source_symbol": target,
                        "target_symbol": source,
                        "direction": "SOURCE_TO_TARGET",
                        "lag_bars": lag,
                        "correlation": round(corr_ba, 6),
                        "timeframe": primary_timeframe.upper(),
                        "samples": len(ar) - lag,
                    })
    result.sort(key=lambda x: (-abs(x["correlation"]), x["source_symbol"], x["target_symbol"], x["lag_bars"]))
    return result[:32]


def build_brain_context(
    symbol: str,
    primary_timeframe: str,
    decision_time: datetime,
    observations_by_tf: Dict[str, List[MarketObservation]],
    observations_by_symbol: Optional[Dict[str, List[MarketObservation]]] = None,
) -> Dict[str, Any]:
    """Build deterministic point-in-time MTF + structure + cross-symbol context."""
    context: Dict[str, Any] = {
        "decision_time": _iso(decision_time),
        "primary_timeframe": primary_timeframe.upper(),
        "symbol": symbol.upper(),
        "history": {},
        "future_excluded": True,
        "cross_symbol_relations": [],
    }
    for tf, observations in sorted(observations_by_tf.items()):
        context["history"][tf.upper()] = _tf_snapshot(observations, decision_time)

    if observations_by_symbol:
        context["cross_symbol_relations"] = discover_cross_symbol_relations(
            observations_by_symbol, decision_time, primary_timeframe
        )

    canonical = json.dumps(context, sort_keys=True, separators=(",", ":"), default=str)
    context["context_id"] = "ctx-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    return context
