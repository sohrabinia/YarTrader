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
