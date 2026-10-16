"""Evidence-aware DEMO-only strategy exploration and style discovery selector."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable, Any


def choose_demo_strategy(candidates: Iterable[str], symbol: str, storage_root: str | Path) -> dict[str, Any]:
    """Prefer under-sampled candidate styles; rotate ties to avoid fixed first-item bias.

    This is a DEMO exploration policy, not evidence that a style is profitable.
    Live activation is deliberately outside this module and remains disabled.
    """
    names = list(dict.fromkeys(str(x).strip().upper() for x in candidates if str(x).strip()))
    if not names:
        raise ValueError("At least one qualified strategy candidate is required.")
    root = Path(storage_root) / str(symbol).strip().upper()
    report_path = root / "autonomous_strategy_discovery.json"
    state_path = root / "strategy_selection_state.json"
    report = {}
    state = {}
    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        pass
    try:
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        pass
    samples: dict[str, int] = {}
    research_scores: dict[str, tuple[float, float]] = {}
    for cohort in report.get("cohorts", []) if isinstance(report, dict) else []:
        try:
            cohort_name = str(cohort.get("cohort", ""))
            prefix = str(symbol).strip().upper() + "|"
            if not cohort_name.upper().startswith(prefix):
                continue
            strategy = cohort_name[len(prefix):].strip().upper()
            samples[strategy] = max(0, int(cohort.get("closed_position_count", 0) or 0))
            pf = float(cohort.get("profit_factor") or 0.0)
            expectancy = float(cohort.get("net_expectancy_per_position") or 0.0)
            if (cohort.get("status") == "PROMISING_HYPOTHESIS_REQUIRES_WALK_FORWARD"
                    and samples[strategy] >= 30 and expectancy > 0 and pf >= 1.15):
                research_scores[strategy] = (expectancy, pf)
        except (TypeError, ValueError, OverflowError):
            continue
    # DEMO-only paper exploration may prioritize promising research hypotheses,
    # but this does not mark them validated or authorize live trading.
    promising = [name for name in names if name in research_scores]
    if promising:
        selected = max(promising, key=lambda name: (research_scores[name][0], research_scores[name][1]))
        reason = "PROMISING_DEMO_HYPOTHESIS_REQUIRES_WALK_FORWARD"
    else:
        minimum = min(samples.get(name, 0) for name in names)
        under_sampled = [name for name in names if samples.get(name, 0) == minimum]
        cursor = max(0, int(state.get("rotation_cursor", 0) or 0))
        selected = under_sampled[cursor % len(under_sampled)]
        reason = "LOWEST_OBSERVED_SAMPLE_COUNT_ROUND_ROBIN"
        cursor += 1
        state["rotation_cursor"] = cursor
    state.update({"symbol": str(symbol).strip().upper(), "last_selected_strategy": selected,
                  "last_selection_reason": reason, "last_candidates": names,
                  "observed_closed_positions_by_strategy": samples,
                  "research_only_scores": {k: {"expectancy": v[0], "profit_factor": v[1]} for k, v in research_scores.items()}})
    root.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(state_path)
    return {"selected_strategy": selected, "reason": reason,
            "observed_closed_positions": samples.get(selected, 0),
            "candidate_count": len(names), "validated_for_live": False,
            "activation_allowed": False, "observed_closed_positions_by_strategy": samples}
