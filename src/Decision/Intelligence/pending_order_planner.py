"""Research-first planner for conditional/pending entries; never submits broker orders."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Mapping, Optional
import math


@dataclass(frozen=True)
class PendingOrderPlan:
    status: str
    order_type: str
    direction: str
    entry: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    gross_reward_risk: Optional[float]
    net_reward_risk: Optional[float]
    expires_at: Optional[float]
    cancel_if: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PendingOrderPlanner:
    """Turn an already-confirmed market scenario into a conditional order proposal.

    This class deliberately has no broker/MT5 dependency. A separate execution
    service must revalidate quote, spread, risk, account, and broker state before
    placing, modifying, or cancelling any order.
    """

    def __init__(self, min_confidence: float = 70.0, min_net_rr: float = 1.5,
                 max_spread_atr: float = 0.12, entry_buffer_atr: float = 0.05):
        self.min_confidence = float(min_confidence)
        self.min_net_rr = float(min_net_rr)
        self.max_spread_atr = float(max_spread_atr)
        self.entry_buffer_atr = float(entry_buffer_atr)

    @staticmethod
    def _wait(direction: str, reason: str, expires_at: Optional[float] = None) -> PendingOrderPlan:
        return PendingOrderPlan("WAIT", "NONE", direction, None, None, None, None, None,
                                expires_at, "No order exists to cancel.", reason)

    def plan(self, scenario: Mapping[str, Any], quote: Mapping[str, Any],
             now: float) -> PendingOrderPlan:
        direction = str(scenario.get("direction", "WAIT")).upper()
        setup = str(scenario.get("setup_type", "")).upper()
        expires_at = scenario.get("expires_at")
        if direction not in {"BUY", "SELL"}:
            return self._wait(direction, "Direction is not actionable.")
        required = ("zone_low", "zone_high", "invalidation", "target", "atr", "confidence")
        if any(scenario.get(k) is None for k in required):
            return self._wait(direction, "Scenario lacks a zone, invalidation, target, ATR, or confidence.", expires_at)
        try:
            low, high = float(scenario["zone_low"]), float(scenario["zone_high"])
            invalidation, target = float(scenario["invalidation"]), float(scenario["target"])
            atr, confidence = float(scenario["atr"]), float(scenario["confidence"])
            bid, ask = float(quote["bid"]), float(quote["ask"])
            now = float(now)
            expiry = float(expires_at) if expires_at is not None else None
            slip = max(0.0, float(scenario.get("slippage_allowance", 0.0)))
            commission = max(0.0, float(scenario.get("commission_price_allowance", 0.0)))
        except (TypeError, ValueError, KeyError):
            return self._wait(direction, "Scenario or quote contains invalid numeric values.", expires_at)
        nums = (low, high, invalidation, target, atr, confidence, bid, ask, now, slip, commission)
        if not all(math.isfinite(v) for v in nums) or low >= high or atr <= 0 or bid <= 0 or ask < bid:
            return self._wait(direction, "Invalid zone/ATR/quote geometry.", expires_at)
        if expiry is not None and (not math.isfinite(expiry) or expiry <= now):
            return self._wait(direction, "Scenario expired; recalculate from fresh closed candles.", expires_at)
        if confidence < self.min_confidence:
            return self._wait(direction, "Confidence is below the pending-order threshold.", expires_at)
        spread = ask - bid
        if spread / atr > self.max_spread_atr:
            return self._wait(direction, "Spread is too large relative to current ATR.", expires_at)
        if setup not in {"RETEST", "BREAKOUT"}:
            return self._wait(direction, "Only confirmed RETEST or BREAKOUT scenarios can propose pending orders.", expires_at)

        buffer = self.entry_buffer_atr * atr
        if setup == "RETEST":
            order_type = "BUY_LIMIT" if direction == "BUY" else "SELL_LIMIT"
            try:
                entry = float(scenario.get("entry_price", (low + high) / 2.0))
            except (TypeError, ValueError):
                return self._wait(direction, "Retest entry price is invalid.", expires_at)
            if not math.isfinite(entry) or not low <= entry <= high:
                return self._wait(direction, "Retest entry price must be inside the selected Base zone.", expires_at)
            if direction == "BUY" and entry >= ask - buffer:
                return self._wait(direction, "Buy retest zone is not safely below the ask; wait for price structure.", expires_at)
            if direction == "SELL" and entry <= bid + buffer:
                return self._wait(direction, "Sell retest zone is not safely above the bid; wait for price structure.", expires_at)
        else:
            order_type = "BUY_STOP" if direction == "BUY" else "SELL_STOP"
            entry = high + buffer if direction == "BUY" else low - buffer
            if direction == "BUY" and entry <= ask + buffer:
                return self._wait(direction, "Breakout level is already crossed or too close; do not chase.", expires_at)
            if direction == "SELL" and entry >= bid - buffer:
                return self._wait(direction, "Breakdown level is already crossed or too close; do not chase.", expires_at)

        if direction == "BUY" and not (invalidation < entry < target):
            return self._wait(direction, "Buy invalidation/entry/target geometry is invalid.", expires_at)
        if direction == "SELL" and not (target < entry < invalidation):
            return self._wait(direction, "Sell target/entry/invalidation geometry is invalid.", expires_at)
        risk = abs(entry - invalidation)
        reward = abs(target - entry)
        cost = spread + slip + commission
        net_reward = reward - cost
        net_risk = risk + cost
        gross_rr = reward / risk if risk > 0 else 0.0
        net_rr = net_reward / net_risk if net_reward > 0 and net_risk > 0 else 0.0
        if net_rr < self.min_net_rr:
            return self._wait(direction, "Expected reward after estimated costs does not meet minimum net R/R.", expires_at)

        return PendingOrderPlan(
            status="PROPOSED", order_type=order_type, direction=direction,
            entry=round(entry, 5), stop_loss=round(invalidation, 5), take_profit=round(target, 5),
            gross_reward_risk=round(gross_rr, 4), net_reward_risk=round(net_rr, 4),
            expires_at=expiry,
            cancel_if=("zone invalidated, opposite structure confirmed, spread exceeds threshold, "
                       "scenario expires, or target/stop geometry no longer passes revalidation"),
            reason="Conditional order proposal only; broker placement requires a separate risk and execution gate.",
        )

    @staticmethod
    def should_cancel(plan: Mapping[str, Any], *, now: float, zone_invalidated: bool,
                      opposite_structure_confirmed: bool, spread_atr: float,
                      max_spread_atr: float = 0.12) -> bool:
        """Pure cancellation policy for a pending order; caller must verify broker state."""
        expiry = plan.get("expires_at")
        try:
            if expiry is not None and float(now) >= float(expiry):
                return True
            if not math.isfinite(float(spread_atr)) or float(spread_atr) > max_spread_atr:
                return True
        except (TypeError, ValueError):
            return True
        return bool(zone_invalidated or opposite_structure_confirmed)