"""Executable, fail-closed market-regime strategies built from closed OHLC bars."""
from __future__ import annotations
from typing import Any, Dict, List, Mapping
import math
from src.Decision.Intelligence.market_behavior_policy import MarketBehaviorPolicy
from src.Decision.Intelligence.pending_order_planner import PendingOrderPlanner


def evaluate_market_behavior_strategy(symbol: str, timeframe_candles: Mapping[str, Any],
                                      quote: Mapping[str, float], now: float,
                                      spread_allowance: float = 0.0) -> Dict[str, Any]:
    """Build one causal RANGE/TREND/SPIKE candidate; never chase a breakout."""
    wait = {"strategy_name": "MARKET_BEHAVIOR", "status": "WAIT", "direction": "WAIT",
            "confidence": 0.0, "order_plan": None, "execution_enabled": False,
            "reason": "Market behavior has not produced a qualified entry."}
    bars = timeframe_candles.get("M5", []) or timeframe_candles.get("M15", []) or []
    clean: List[Dict[str, float]] = []
    for row in bars:
        try:
            b = {k: float(row[k]) for k in ("open", "high", "low", "close")}
            stamp = float(row.get("timestamp", row.get("time", 0)) or 0)
            if (stamp <= now and all(math.isfinite(v) for v in b.values())
                    and b["low"] > 0 and b["low"] <= min(b["open"], b["close"])
                    and b["high"] >= max(b["open"], b["close"]) and b["high"] > b["low"]):
                b["timestamp"] = stamp
                clean.append(b)
        except (TypeError, ValueError, KeyError, OverflowError):
            continue
    clean.sort(key=lambda b: b["timestamp"])
    if len(clean) < 25:
        wait["reason"] = "Market-behavior strategy requires at least 25 valid closed M5/M15 bars."
        return wait
    behavior = MarketBehaviorPolicy(lookback=20).evaluate(clean)
    regime_slot = ("RANGE" if behavior.regime == "RANGE" else
                   "TREND" if behavior.regime in ("TREND_UP", "TREND_DOWN") else
                   "SPIKE" if behavior.regime == "SPIKE" else "MARKET_BEHAVIOR")
    wait.update({"strategy_name": regime_slot, "regime": behavior.regime, "direction": behavior.direction,
                 "confidence": behavior.confidence * 100.0,
                 "market_behavior": behavior.to_dict(), "reason": behavior.reason,
                 "setup_timeframe": "M5" if timeframe_candles.get("M5") else "M15"})
    if behavior.direction not in ("BUY", "SELL") or behavior.regime in ("UNCERTAIN", "TRANSITION"):
        return wait
    bid, ask = float(quote.get("bid", 0) or 0), float(quote.get("ask", 0) or 0)
    if bid <= 0 or ask < bid or behavior.atr <= 0:
        wait["reason"] = "Invalid live quote or ATR; market-behavior entry blocked."
        return wait
    direction = behavior.direction
    low, high, atr = behavior.channel_low, behavior.channel_high, behavior.atr
    width = high-low
    if not math.isfinite(width) or width <= 0:
        wait["reason"] = "Invalid regime channel; entry blocked."
        return wait
    # All entries are retests/edge fades. A spike is never chased: wait for a
    # pullback to the prior channel boundary, with an ATR-sized analytical target.
    if behavior.regime == "RANGE":
        edge = low if direction == "BUY" else high
        zone_low, zone_high = ((edge, edge + 0.20*width) if direction == "BUY"
                               else (edge - 0.20*width, edge))
        entry = (zone_low+zone_high)/2
        stop = low - 0.25*atr if direction == "BUY" else high + 0.25*atr
        target = (low+high)/2
        rationale = "RANGE mean reversion only at a confirmed channel edge; target is range equilibrium."
    elif behavior.regime in ("TREND_UP", "TREND_DOWN"):
        level = high if direction == "BUY" else low
        zone_low, zone_high = (level-0.15*atr, level+0.05*atr) if direction == "BUY" else (level-0.05*atr, level+0.15*atr)
        entry = (zone_low+zone_high)/2
        stop = zone_low-0.75*atr if direction == "BUY" else zone_high+0.75*atr
        target = entry + behavior.spike_target_distance if direction == "BUY" else entry-behavior.spike_target_distance
        # In trend mode require a meaningful analytical reward estimate.
        target = (high + 1.5*atr) if direction == "BUY" else (low - 1.5*atr)
        rationale = "TREND continuation on pullback/retest; no market-order chasing."
    elif behavior.regime == "SPIKE":
        level = high if direction == "BUY" else low
        zone_low, zone_high = (level-0.10*atr, level+0.10*atr)
        entry = (zone_low+zone_high)/2
        stop = zone_low-0.75*atr if direction == "BUY" else zone_high+0.75*atr
        target = entry + 2.5*atr if direction == "BUY" else entry-2.5*atr
        rationale = "SPIKE breakout detected on a closed candle; entry waits for a boundary retest, never chases."
    else:
        return wait
    if direction == "BUY" and not (stop < entry < target):
        wait["reason"] = "Market-behavior BUY geometry invalid; waiting."
        return wait
    if direction == "SELL" and not (target < entry < stop):
        wait["reason"] = "Market-behavior SELL geometry invalid; waiting."
        return wait
    plan = PendingOrderPlanner(min_confidence=60.0, max_spread_base_width_ratio=0.20,
                               enforce_min_net_rr=True).plan(
        {"direction": direction, "setup_type": "RETEST", "zone_low": zone_low,
         "zone_high": zone_high, "entry_price": entry, "invalidation": stop,
         "target": target, "base_width": max(zone_high-zone_low, atr*0.1),
         "confidence": max(60.0, behavior.confidence*100.0),
         "expires_at": now + 8*300, "slippage_allowance": max(0.0, spread_allowance*0.25)},
        quote, now)
    wait.update({"direction": direction, "order_plan": plan.to_dict(),
                 "status": "ENTRY_PROPOSAL" if plan.status == "PROPOSED" else "WAIT",
                 "confidence": behavior.confidence*100.0, "reason": rationale,
                 "zone": {"low": zone_low, "high": zone_high},
                 "execution_enabled": False})
    return wait
