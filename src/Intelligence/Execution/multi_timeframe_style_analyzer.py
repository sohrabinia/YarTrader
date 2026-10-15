"""Independent multi-timeframe RTM and pure price-action analyzers.

These detectors use only completed OHLC bars. They produce research proposals;
the execution service remains responsible for account/broker/risk validation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional
import math

from src.Decision.Intelligence.pending_order_planner import PendingOrderPlanner
from src.Research.Brain.multitimeframe_base_transition_engine import TIMEFRAME_ORDER, TIMEFRAME_SECONDS


def _clean_bars(rows: Any) -> List[Dict[str, float]]:
    out = []
    if not isinstance(rows, (list, tuple)):
        return out
    for row in rows:
        try:
            bar = {k: float(row[k]) for k in ("open", "high", "low", "close")}
            stamp = row.get("timestamp", row.get("time"))
            if isinstance(stamp, str):
                from datetime import datetime
                stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
            bar["time"] = float(stamp)
            if (all(math.isfinite(bar[k]) for k in ("open", "high", "low", "close", "time"))
                    and bar["low"] <= min(bar["open"], bar["close"])
                    and bar["high"] >= max(bar["open"], bar["close"])
                    and bar["high"] > bar["low"]):
                out.append(bar)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return sorted(out, key=lambda x: x["time"])


def _swing_bias(bars: List[Dict[str, float]]) -> int:
    """Closed-bar structural bias from the most recent confirmed swing sequence."""
    if len(bars) < 12:
        return 0
    highs, lows = [], []
    # Only swings with both neighboring candles already closed are accepted.
    for i in range(max(1, len(bars)-80), len(bars)-1):
        if bars[i]["high"] > bars[i-1]["high"] and bars[i]["high"] >= bars[i+1]["high"]:
            highs.append((i, bars[i]["high"]))
        if bars[i]["low"] < bars[i-1]["low"] and bars[i]["low"] <= bars[i+1]["low"]:
            lows.append((i, bars[i]["low"]))
    if len(highs) >= 2 and len(lows) >= 2:
        hh = highs[-1][1] > highs[-2][1]
        hl = lows[-1][1] > lows[-2][1]
        lh = highs[-1][1] < highs[-2][1]
        ll = lows[-1][1] < lows[-2][1]
        if hh and hl:
            return 1
        if lh and ll:
            return -1
    return 0


def _candle_trigger(bars: List[Dict[str, float]]) -> int:
    """Directional rejection/engulfing trigger from the last completed candle."""
    if len(bars) < 3:
        return 0
    p, b = bars[-2], bars[-1]
    rng = b["high"] - b["low"]
    if rng <= 0:
        return 0
    body = abs(b["close"] - b["open"])
    lower = min(b["open"], b["close"]) - b["low"]
    upper = b["high"] - max(b["open"], b["close"])
    bull_engulf = (b["close"] > b["open"] and p["close"] < p["open"]
                   and b["open"] <= p["close"] and b["close"] >= p["open"])
    bear_engulf = (b["close"] < b["open"] and p["close"] > p["open"]
                   and b["open"] >= p["close"] and b["close"] <= p["open"])
    if bull_engulf or (lower >= max(body * 1.5, rng * 0.45) and b["close"] >= b["low"] + 0.65*rng):
        return 1
    if bear_engulf or (upper >= max(body * 1.5, rng * 0.45) and b["close"] <= b["high"] - 0.65*rng):
        return -1
    return 0


def _rtm_zone(bars: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
    """Find the latest compact 2-5 candle base followed by decisive displacement."""
    if len(bars) < 20:
        return None
    start = max(5, len(bars)-50)
    best = None
    for departure in range(start+5, len(bars)):
        # departure is a completed candle; the zone is strictly older.
        for length in (2, 3, 4, 5):
            end = departure - 1
            begin = end - length + 1
            if begin < 1:
                continue
            base = bars[begin:end+1]
            lo = min(x["low"] for x in base)
            hi = max(x["high"] for x in base)
            width = hi-lo
            if width <= 0:
                continue
            mean_body = sum(abs(x["close"]-x["open"]) for x in base)/length
            disp = bars[departure]
            displacement = disp["close"] - (hi if disp["close"] > hi else lo if disp["close"] < lo else (hi+lo)/2)
            if mean_body > 0.55*width or abs(displacement) < 1.0*width:
                continue
            direction = 1 if disp["close"] > hi + 0.05*width else -1 if disp["close"] < lo - 0.05*width else 0
            if not direction:
                continue
            # Current price must have revisited the old zone after departure.
            revisits = [x for x in bars[departure+1:] if x["low"] <= hi and x["high"] >= lo]
            if not revisits:
                continue
            latest = bars[-1]
            if not (latest["low"] <= hi and latest["high"] >= lo):
                continue
            if best is None or departure > best["departure_index"]:
                best = {"direction": direction, "low": lo, "high": hi, "width": width,
                        "departure_index": departure, "zone_time": base[-1]["time"],
                        "revisit_time": revisits[-1]["time"]}
    return best


def _base_engulf_reversal(bars: List[Dict[str, float]], now: float) -> Dict[str, Any]:
    """Detect a completed trend -> compact Base -> departure -> opposite engulf.

    This is a research hypothesis, not an assertion that all engulfed Bases reverse.
    The Base and trend must precede the engulf candle; only closed bars are used.
    """
    wait = {"status": "WAIT", "direction": "WAIT", "signal_time": None,
            "observation_time": bars[-1]["time"] if bars else None,
            "observation_close": bars[-1]["close"] if bars else None,
            "base": None, "trend_direction": 0, "engulfed": False,
            "reason": "No confirmed trend-ending Base engulf reversal."}
    if len(bars) < 24 or bars[-1]["time"] > now:
        wait["reason"] = "BASE_ENGULF_REVERSAL needs at least 24 closed bars and rejects future candles."
        return wait
    # Use the newest qualifying Base, with enough pre-Base trend and post-Base
    # bars to confirm both displacement and a later engulf event.
    start = max(9, len(bars) - 55)
    candidates = []
    for length in (2, 3, 4, 5):
        for begin in range(start, len(bars) - length - 2):
            end = begin + length - 1
            base = bars[begin:end + 1]
            lo = min(x["low"] for x in base)
            hi = max(x["high"] for x in base)
            width = hi - lo
            if width <= 0:
                continue
            mean_body = sum(abs(x["close"] - x["open"]) for x in base) / length
            if mean_body > 0.55 * width:
                continue
            prior = bars[max(0, begin - 10):begin]
            if len(prior) < 8:
                continue
            trend_move = prior[-1]["close"] - prior[0]["close"]
            trend_direction = 1 if trend_move > 0 else -1 if trend_move < 0 else 0
            if not trend_direction or abs(trend_move) < 1.5 * width:
                continue
            departures = []
            for j in range(end + 1, min(len(bars), end + 6)):
                candle = bars[j]
                if trend_direction > 0 and candle["close"] > hi + 0.25 * width:
                    departures.append(j)
                elif trend_direction < 0 and candle["close"] < lo - 0.25 * width:
                    departures.append(j)
            if not departures:
                continue
            departure = departures[0]
            # Only an engulf event in the last three completed bars is actionable.
            for j in range(max(departure + 1, len(bars) - 3), len(bars)):
                candle = bars[j]
                covers_base = candle["high"] >= hi and candle["low"] <= lo
                bearish_reversal = (trend_direction > 0 and covers_base
                                    and candle["close"] < lo and candle["close"] < candle["open"])
                bullish_reversal = (trend_direction < 0 and covers_base
                                    and candle["close"] > hi and candle["close"] > candle["open"])
                if bearish_reversal or bullish_reversal:
                    direction = -1 if bearish_reversal else 1
                    # Require the most recent close to remain outside the Base in
                    # the reversal direction; otherwise the signal is already stale.
                    latest = bars[-1]
                    remains_confirmed = latest["close"] < lo if direction < 0 else latest["close"] > hi
                    candidates.append({
                        "status": "ENTRY_CANDIDATE" if remains_confirmed else "WAIT",
                        "direction": "SELL" if direction < 0 else "BUY",
                        "signal_time": candle["time"], "base": {"low": lo, "high": hi, "width": width,
                            "start_time": base[0]["time"], "end_time": base[-1]["time"]},
                        "trend_direction": trend_direction, "departure_time": bars[departure]["time"],
                        "engulfed": True, "engulf_time": candle["time"],
                        "observation_time": candle["time"], "observation_close": candle["close"],
                        "engulf_high": candle["high"], "engulf_low": candle["low"],
                        "reason": "Closed candle engulfed the Base range after a same-direction trend departure; reversal direction is opposite the prior trend.",
                    })
    if not candidates:
        # Keep a diagnostic for the newest compact Base even when it was not
        # engulfed; the backtest can compare engulfed vs non-engulfed occurrences.
        for length in (2, 3, 4, 5):
            for begin in range(start, len(bars) - length - 1):
                end = begin + length - 1
                base = bars[begin:end + 1]
                lo, hi = min(x["low"] for x in base), max(x["high"] for x in base)
                width = hi - lo
                prior = bars[max(0, begin - 10):begin]
                if width <= 0 or len(prior) < 8:
                    continue
                if sum(abs(x["close"]-x["open"]) for x in base)/length > 0.55*width:
                    continue
                move = prior[-1]["close"]-prior[0]["close"]
                td = 1 if move > 0 else -1 if move < 0 else 0
                if not td or abs(move) < 1.5*width:
                    continue
                departures = [j for j in range(end+1, min(len(bars), end+6))
                              if (td > 0 and bars[j]["close"] > hi+0.25*width)
                              or (td < 0 and bars[j]["close"] < lo-0.25*width)]
                if departures:
                    wait.update({"base": {"low":lo,"high":hi,"width":width,
                                           "start_time":base[0]["time"],"end_time":base[-1]["time"]},
                                 "trend_direction":td,"departure_time":bars[departures[0]]["time"],
                                 "observation_time":bars[-1]["time"], "observation_close":bars[-1]["close"],
                                 "reason":"A trend-ending Base/departure was found, but no recent closed candle engulfed the Base range in the opposite direction."})
                    return wait
        return wait
    # Highest timeframe is chosen by the caller; within one timeframe use the
    # most recent completed engulf event and require a still-confirmed close.
    return max(candidates, key=lambda x: (x["signal_time"], x["status"] == "ENTRY_CANDIDATE"))


class MultiTimeframeStyleAnalyzer:
    """Evaluate RTM and Price Action independently across available timeframes."""
    STRATEGIES = ("BASE_HIERARCHY", "RTM", "PRICE_ACTION", "BASE_ENGULF_REVERSAL")
    CONTEXT_TFS = ("MN1", "W1", "D1", "H4", "H1")
    SETUP_TFS = ("M30", "M15", "M5")
    TRIGGER_TFS = ("M1", "M5")
    BASE_TFS = ("MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1")

    def evaluate(self, symbol: str, timeframe_candles: Mapping[str, Any],
                 quote: Mapping[str, float], now: float,
                 spread_allowance: float = 0.0) -> Dict[str, Dict[str, Any]]:
        bars = {str(tf).upper(): _clean_bars(rows) for tf, rows in timeframe_candles.items()}
        available = {tf: rows for tf, rows in bars.items() if rows and rows[-1]["time"] <= now}
        biases = {tf: _swing_bias(rows) for tf, rows in available.items()}
        results: Dict[str, Dict[str, Any]] = {}
        for strategy in ("RTM", "PRICE_ACTION"):
            results[strategy] = self._evaluate_one(strategy, available, biases, quote, now, spread_allowance)
        results["SCALP"] = self._evaluate_scalp(available, biases, quote, now, spread_allowance)
        results["BASE_ENGULF_REVERSAL"] = self._evaluate_base_engulf_reversal(available, quote, now, spread_allowance)
        return results

    def _evaluate_base_engulf_reversal(self, bars: Mapping[str, List[Dict[str, float]]],
                                       quote: Mapping[str, float], now: float,
                                       spread_allowance: float) -> Dict[str, Any]:
        """Evaluate the independent Base-engulf reversal hypothesis on every timeframe."""
        timeframe_results = {}
        actionable = []
        tf_rank = {tf: i for i, tf in enumerate(self.BASE_TFS)}
        for tf in self.BASE_TFS:
            rows = bars.get(tf, [])
            detected = _base_engulf_reversal(rows, now) if rows else {
                "status": "WAIT", "direction": "WAIT", "engulfed": False,
                "reason": "No closed bars available for this timeframe."}
            item = {**detected, "timeframe": tf, "execution_enabled": False, "order_plan": None}
            base = detected.get("base")
            if detected.get("status") == "ENTRY_CANDIDATE" and base:
                low, high = float(base["low"]), float(base["high"])
                width = float(base["width"])
                direction = str(detected["direction"])
                stop_buffer = max(0.10 * width, 1.5 * max(0.0, spread_allowance))
                if direction == "BUY":
                    # Invalidate below both the Base and the actual engulf candle.
                    # Never manufacture a stop from ATR alone; if this real structure
                    # is still too tight/wide, the independent DEMO risk gate may block it.
                    stop = min(low, float(detected.get("engulf_low", low))) - stop_buffer
                    entry = (low + high) / 2.0
                    target = entry + 2.0 * (entry - stop)
                else:
                    stop = max(high, float(detected.get("engulf_high", high))) + stop_buffer
                    entry = (low + high) / 2.0
                    target = entry - 2.0 * (stop - entry)
                planner = PendingOrderPlanner(min_confidence=70.0,
                                              max_spread_base_width_ratio=0.20,
                                              enforce_min_net_rr=True)
                plan = planner.plan({"direction": direction, "setup_type": "RETEST",
                                     "zone_low": low, "zone_high": high,
                                     "entry_price": entry, "invalidation": stop,
                                     "target": target, "base_width": width,
                                     "confidence": 72.0,
                                     "expires_at": now + 3 * TIMEFRAME_SECONDS.get(tf, 60),
                                     "slippage_allowance": max(0.0, spread_allowance * 0.25)}, quote, now)
                item.update({"confidence": 72.0, "research_target": target,
                             "research_reward_risk": 2.0, "order_plan": plan.to_dict(),
                             "status": "ENTRY_PROPOSAL" if plan.status == "PROPOSED" else "WAIT",
                             "reason": (detected.get("reason", "") + " Conditional Base retest; "
                                        "strategy remains experimental until forward outcomes validate the edge.")})
                if plan.status == "PROPOSED":
                    actionable.append(item)
            else:
                item.update({"confidence": 0.0, "status": "WAIT", "reason": detected.get("reason", "")})
            timeframe_results[tf] = item
        # Prefer the highest timeframe with a valid proposal; each timeframe is
        # still recorded separately so research can compare all Base scales.
        selected = next((timeframe_results[tf] for tf in self.BASE_TFS
                         if timeframe_results[tf]["status"] == "ENTRY_PROPOSAL"), None)
        if selected:
            return {**selected, "strategy_name": "BASE_ENGULF_REVERSAL",
                    "setup_timeframe": selected.get("timeframe"),
                    "timeframe_results": timeframe_results,
                    "reason": selected["reason"]}
        best_diag = next((timeframe_results[tf] for tf in self.BASE_TFS
                          if timeframe_results[tf].get("base") is not None), None)
        return {"strategy_name": "BASE_ENGULF_REVERSAL", "status": "WAIT", "direction": "WAIT",
                "confidence": 0.0, "timeframe_analysis": {},
                "setup_timeframe": (best_diag or {}).get("timeframe"),
                "order_plan": None, "timeframe_results": timeframe_results,
                "execution_enabled": False,
                "reason": (best_diag or {}).get("reason", "No recent trend-ending Base candidate on any available timeframe.")}

    def _evaluate_scalp(self, bars: Mapping[str, List[Dict[str, float]]],
                        biases: Mapping[str, int], quote: Mapping[str, float],
                        now: float, spread_allowance: float) -> Dict[str, Any]:
        """Short-horizon M1 break/retest scalp, confirmed by closed M5 structure."""
        wait = {"strategy_name": "SCALP", "status": "WAIT", "direction": "WAIT",
                "confidence": 0.0, "timeframe_analysis": dict(biases),
                "execution_enabled": False, "order_plan": None,
                "reason": "Scalp setup has not met its closed-bar and cost filters."}
        m1, m5 = bars.get("M1", []), bars.get("M5", [])
        if len(m1) < 35 or len(m5) < 12 or m1[-1]["time"] > now or m5[-1]["time"] > now:
            wait["reason"] = "SCALP requires at least 35 closed M1 bars and 12 closed M5 bars."
            return wait
        bias = biases.get("M5", 0)
        if not bias:
            wait["reason"] = "SCALP waits for a confirmed M5 swing direction."
            return wait
        trs = []
        for i in range(max(1, len(m1)-15), len(m1)):
            b, prev = m1[i], m1[i-1]
            trs.append(max(b["high"]-b["low"], abs(b["high"]-prev["close"]), abs(b["low"]-prev["close"])))
        atr = sum(trs)/len(trs) if trs else 0.0
        if not math.isfinite(atr) or atr <= 0:
            wait["reason"] = "SCALP ATR is invalid; no entry proposed."
            return wait
        prior = m1[-12:-2]
        last = m1[-1]
        direction = bias
        if direction > 0:
            level = max(x["high"] for x in prior)
            valid = last["close"] > level and last["low"] <= level + 0.20*atr
            entry_zone = (level-0.05*atr, level+0.05*atr)
            stop = min(min(x["low"] for x in m1[-5:]), entry_zone[0]) - 0.10*atr
            entry = sum(entry_zone)/2
            target = entry + 2.0*(entry-stop)
            direction_name = "BUY"
            quote_valid = entry < float(quote.get("ask", 0) or 0)
        else:
            level = min(x["low"] for x in prior)
            valid = last["close"] < level and last["high"] >= level - 0.20*atr
            entry_zone = (level-0.05*atr, level+0.05*atr)
            stop = max(max(x["high"] for x in m1[-5:]), entry_zone[1]) + 0.10*atr
            entry = sum(entry_zone)/2
            target = entry - 2.0*(stop-entry)
            direction_name = "SELL"
            quote_valid = entry > float(quote.get("bid", 0) or 0)
        if not valid or not quote_valid:
            wait["reason"] = "SCALP requires a closed M1 breakout/retest aligned with M5; no chasing."
            return wait
        width = entry_zone[1]-entry_zone[0]
        planner = PendingOrderPlanner(min_confidence=70.0, max_spread_base_width_ratio=0.20,
                                      enforce_min_net_rr=True)
        plan = planner.plan({"direction": direction_name, "setup_type": "RETEST",
                             "zone_low": entry_zone[0], "zone_high": entry_zone[1],
                             "entry_price": entry, "invalidation": stop, "target": target,
                             "base_width": max(width, 0.1*atr), "confidence": 70.0,
                             "expires_at": now + 10*60,
                             "slippage_allowance": max(0.0, spread_allowance*0.25)}, quote, now)
        wait.update({"direction": direction_name, "confidence": 70.0,
                     "setup_timeframe": "M1", "trigger_timeframe": "M1",
                     "order_plan": plan.to_dict(),
                     "status": "ENTRY_PROPOSAL" if plan.status == "PROPOSED" else "WAIT",
                     "reason": "SCALP closed-M1 breakout/retest aligned to M5 swing; structural stop and cost-adjusted RR validated."})
        return wait

    def _evaluate_one(self, strategy: str, bars: Mapping[str, List[Dict[str, float]]],
                      biases: Mapping[str, int], quote: Mapping[str, float],
                      now: float, spread_allowance: float) -> Dict[str, Any]:
        wait = {"strategy_name": strategy, "status": "WAIT", "direction": "WAIT",
                "confidence": 0.0, "timeframe_analysis": dict(biases),
                "execution_enabled": False, "order_plan": None, "reason": ""}
        context = [biases.get(tf, 0) for tf in self.CONTEXT_TFS if biases.get(tf, 0)]
        context_available = sum(1 for tf in self.CONTEXT_TFS if len(bars.get(tf, [])) >= 12)
        setup_tf = next((tf for tf in self.SETUP_TFS if len(bars.get(tf, [])) >= 30), None)
        trigger_tf = next((tf for tf in self.TRIGGER_TFS if len(bars.get(tf, [])) >= 3), None)
        if context_available < 2 or len(context) < 1 or not setup_tf or not trigger_tf:
            wait["reason"] = "Multi-timeframe setup requires at least two macro/context frames, a directional context bias, a setup frame, and a lower-timeframe trigger frame."
            return wait
        setup_bars = bars[setup_tf]
        trigger_bars = bars[trigger_tf]
        if setup_bars[-1]["time"] > now or trigger_bars[-1]["time"] > now:
            wait["reason"] = "Future candle detected; evaluation rejected."
            return wait
        trigger = _candle_trigger(trigger_bars)
        if strategy == "RTM":
            zone = _rtm_zone(setup_bars)
            if not zone:
                wait["reason"] = "No confirmed compact-base displacement and subsequent zone revisit on setup timeframe."
                return wait
            direction = int(zone["direction"])
            aligned_context = sum(1 for value in context if value == direction)
            opposed_context = sum(1 for value in context if value == -direction)
            if opposed_context > aligned_context:
                wait["reason"] = "Higher-timeframe structure opposes the RTM zone-departure direction."
                return wait
            # Require a confirmed directional trigger; absence of a trigger is not confirmation.
            latest = setup_bars[-1]
            in_zone = latest["low"] <= zone["high"] and latest["high"] >= zone["low"]
            if not in_zone or trigger != direction:
                wait["reason"] = "RTM zone revisit lacks a confirmed direction-aligned lower-timeframe rejection/engulfing trigger."
                return wait
            zone_low, zone_high, width = zone["low"], zone["high"], zone["width"]
            setup_type = "RETEST"
            confidence = 70.0 + (10.0 if trigger == direction else 0.0)
            rationale = "RTM compact base + displacement + return-to-origin zone; lower-timeframe confirmation required."
        else:
            bias = biases.get(setup_tf, 0)
            if not bias or trigger != bias:
                wait["reason"] = "Price Action requires a confirmed swing-structure bias and matching closed-candle rejection/engulfing trigger."
                return wait
            aligned_context = sum(1 for value in context if value == bias)
            opposed_context = sum(1 for value in context if value == -bias)
            if opposed_context > aligned_context:
                wait["reason"] = "Higher-timeframe structure opposes the Price Action trigger."
                return wait
            recent = setup_bars[-20:]
            zone_low = min(x["low"] for x in recent)
            zone_high = max(x["high"] for x in recent)
            width = zone_high-zone_low
            if width <= 0:
                wait["reason"] = "Invalid price-action structure range."
                return wait
            # Enter on a retest of a broken swing level, not at market after a chase.
            pivots = [x for x in setup_bars[-30:-1]]
            level = max(x["high"] for x in pivots) if bias > 0 else min(x["low"] for x in pivots)
            latest = setup_bars[-1]
            if bias > 0 and not (latest["close"] > level and latest["low"] <= level + 0.15*width):
                wait["reason"] = "No causal bullish break-and-retest of a confirmed swing level."
                return wait
            if bias < 0 and not (latest["close"] < level and latest["high"] >= level - 0.15*width):
                wait["reason"] = "No causal bearish break-and-retest of a confirmed swing level."
                return wait
            zone_low, zone_high = (level-0.05*width, level+0.05*width)
            width = zone_high-zone_low
            setup_type = "RETEST"
            confidence = min(90.0, 68.0 + 4.0*sum(1 for value in context if value == bias))
            rationale = "Pure price action: confirmed swing break/retest, multi-timeframe structure, and closed-candle trigger."
            direction = bias
        mid = (float(quote.get("bid", 0.0))+float(quote.get("ask", 0.0)))/2
        entry = (zone_low+zone_high)/2
        stop = zone_low-0.15*width if direction > 0 else zone_high+0.15*width
        target = (zone_high+2.0*abs(entry-stop)) if direction > 0 else (zone_low-2.0*abs(entry-stop))
        if direction > 0 and not (entry < float(quote.get("ask", 0))):
            wait["reason"] = "Buy retest entry is not below the current ask; do not chase."
            return wait
        if direction < 0 and not (entry > float(quote.get("bid", 0))):
            wait["reason"] = "Sell retest entry is not above the current bid; do not chase."
            return wait
        planner = PendingOrderPlanner(min_confidence=68.0, max_spread_base_width_ratio=0.12,
                                       enforce_min_net_rr=True)
        plan = planner.plan({"direction": "BUY" if direction > 0 else "SELL",
                             "setup_type": setup_type, "zone_low": zone_low, "zone_high": zone_high,
                             "entry_price": entry, "invalidation": stop, "target": target,
                             "base_width": width, "confidence": confidence,
                             "expires_at": now + 8*TIMEFRAME_SECONDS.get(setup_tf, 60),
                             "slippage_allowance": max(0.0, spread_allowance*0.25)}, quote, now)
        result = {**wait, "direction": "BUY" if direction > 0 else "SELL",
                  "confidence": confidence, "setup_timeframe": setup_tf, "trigger_timeframe": trigger_tf,
                  "zone": {"low": zone_low, "high": zone_high, "width": width},
                  "order_plan": plan.to_dict(), "reason": rationale,
                  "status": "ENTRY_PROPOSAL" if plan.status == "PROPOSED" else "WAIT"}
        return result
