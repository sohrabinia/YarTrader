"""Deterministic equal-risk allocation across simultaneously eligible strategy slots."""
from __future__ import annotations
import math
from typing import Iterable


def allocate_strategy_risk_pct(
    strategy_names: Iterable[str],
    selected_strategy: str,
    total_risk_pct: float = 1.0,
) -> dict[str, float | str | int]:
    """Return an equal share of total_risk_pct for the selected strategy.

    Only unique, non-empty strategy names count. If no strategy list is supplied,
    use the selected strategy as a one-slot portfolio. The result never exceeds
    the total budget; the execution adapter remains the final risk authority.
    """
    total = float(total_risk_pct)
    if not math.isfinite(total) or total <= 0.0 or total > 1.0:
        raise ValueError("Total strategy risk budget must be finite and in (0, 1.0]%.")
    selected = str(selected_strategy or "").strip().upper()
    names = list(dict.fromkeys(str(name).strip().upper() for name in strategy_names if str(name).strip()))
    if selected and selected not in names:
        names.append(selected)
    if not names:
        raise ValueError("At least one named strategy is required for risk allocation.")
    if not selected:
        raise ValueError("A selected strategy is required for risk allocation.")
    share = total / len(names)
    return {"selected_strategy": selected, "strategy_count": len(names),
            "total_risk_pct": total, "risk_pct": share,
            "allocation_method": "EQUAL_STRATEGY_RISK_SHARE"}


def allocate_demo_slot_risk_pct(
    occupied_strategy_names: Iterable[str],
    selected_strategy: str,
    max_slots: int,
    total_risk_pct: float = 1.0,
) -> dict[str, float | str | int]:
    """Allocate risk by actual/configured concurrent slots, not unselected candidates.

    The percentage is a per-trade sizing ceiling (normally 1%), not an aggregate
    portfolio budget to divide by candidate count or concurrency. Unused slots reserve
    only concurrency capacity. Before a new order is submitted, the execution service
    separately caps the combined stop-loss risk of all open positions and pending orders
    at the authoritative portfolio ceiling; the daily-loss kill switch remains a
    separate realized/floating-loss control.
    """
    try:
        slot_count = int(max_slots)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Maximum concurrent DEMO slots must be a positive integer.") from exc
    if slot_count < 1 or slot_count > 10:
        raise ValueError("Maximum concurrent DEMO slots must be between 1 and 10.")
    selected = str(selected_strategy or "").strip().upper()
    if not selected:
        raise ValueError("A selected strategy is required for DEMO slot risk allocation.")
    names = list(dict.fromkeys(
        str(name).strip().upper() for name in occupied_strategy_names if str(name).strip()
    ))
    if selected not in names:
        names.append(selected)
    if len(names) > slot_count:
        raise ValueError("Occupied strategy slots exceed the configured maximum; new entry must be blocked.")
    # The configured percentage is a per-trade budget, not a portfolio budget
    # to be divided by concurrent slots. Daily loss is guarded separately; dividing
    # 1% across three slots incorrectly reduced each trade to 0.333%.
    occupied_count = len(names)
    result = allocate_strategy_risk_pct([selected], selected, total_risk_pct)
    result["allocation_method"] = "PER_TRADE_TARGET_WITH_SEPARATE_AGGREGATE_AND_DAILY_CAPS"
    result["max_concurrent_slots"] = slot_count
    result["occupied_slot_count"] = occupied_count
    result["reserved_slot_count"] = slot_count - occupied_count
    return result
