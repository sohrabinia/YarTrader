"""Causal, proposal-only multi-timeframe Base reaction decision engine.

Learns only broker-costed net-R labels. Reaction statistics are keyed by the
Base's own timeframe, type, parent relation/alignment, revisit number and depth
bin. Outputs entry/exit/reversal proposals; it never sends broker orders.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Mapping, Sequence
import math

from src.Decision.Intelligence.pending_order_planner import PendingOrderPlanner
from src.Research.Brain.multitimeframe_base_transition_engine import TIMEFRAME_ORDER, TIMEFRAME_SECONDS

DEPTH_BINS = ("EDGE", "OUTER", "INNER", "FAR_EDGE")


def _rank(tf: str) -> int:
    try:
        return TIMEFRAME_ORDER.index(tf)
    except ValueError:
        return len(TIMEFRAME_ORDER)


def _depth_bin(value: Any) -> str:
    try:
        depth = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if not math.isfinite(depth) or depth < 0 or depth > 1:
        return "UNKNOWN"
    if depth < 0.25:
        return "EDGE"
    if depth < 0.50:
        return "OUTER"
    if depth < 0.75:
        return "INNER"
    return "FAR_EDGE"


class BaseReactionDecisionEngine:
    """Learn reaction quality and gate entry/exit/reversal proposals on economics."""

    def __init__(self, planner: PendingOrderPlanner | None = None,
                 min_samples: int = 40, min_win_rate: float = 0.52,
                 min_mean_net_r: float = 0.05, min_reverse_net_rr: float = 1.2):
        self.planner = planner or PendingOrderPlanner()
        self.min_samples = int(min_samples)
        self.min_win_rate = float(min_win_rate)
        self.min_mean_net_r = float(min_mean_net_r)
        self.min_reverse_net_rr = float(min_reverse_net_rr)
        self._stats: Dict[str, Dict[str, float]] = {}

    @staticmethod
    def profile_key(timeframe: str, base_type: str, parent_timeframe: str,
                    parent_relation: str, parent_aligned: bool,
                    reaction_number: int, penetration_fraction: float) -> str:
        return "|".join((str(timeframe), str(base_type), str(parent_timeframe),
                         str(parent_relation), "ALIGNED" if parent_aligned else "OPPOSED",
                         str(max(1, int(reaction_number))), _depth_bin(penetration_fraction)))

    def learn(self, labels: Sequence[Mapping[str, Any]], as_of: int) -> Dict[str, Any]:
        """Aggregate completed, costed net_R outcomes; reject future/ambiguous labels."""
        grouped: Dict[str, list[float]] = defaultdict(list)
        rejected = 0
        for row in labels:
            try:
                if int(row["label_end_time"]) >= int(as_of):
                    rejected += 1
                    continue
                if int(row.get("label_horizon_bars", 0)) <= 0:
                    rejected += 1
                    continue
                if row.get("first_transition") in (None, "ambiguous_same_bar", "horizon_expired"):
                    rejected += 1
                    continue
                # Never train this model on descriptive MFE/MAE proxies.
                if row.get("net_R") is None or row.get("outcome_source") not in ("broker_costed", "historical_execution_simulation"):
                    rejected += 1
                    continue
                net_r = float(row["net_R"])
                if not math.isfinite(net_r):
                    rejected += 1
                    continue
                key = self.profile_key(
                    str(row["timeframe"]), str(row["base_type"]),
                    str(row.get("parent_timeframe") or "NONE"),
                    str(row.get("parent_relation") or "NONE"),
                    row.get("parent_aligned") is True,
                    int(row.get("reaction_number", 1)), float(row.get("penetration_fraction", -1)),
                )
                grouped[key].append(net_r)
            except (KeyError, TypeError, ValueError, OverflowError):
                rejected += 1
        self._stats = {}
        for key, values in grouped.items():
            n = len(values)
            wins = sum(v > 0 for v in values)
            rate = wins / n
            mean_net = sum(values) / n
            variance_net = (sum((value - mean_net) ** 2 for value in values) / (n - 1)) if n > 1 else 1e18
            self._stats[key] = {
                "samples": n, "win_rate": rate,
                "standard_error": math.sqrt(max(0.0, rate * (1-rate)) / n),
                "mean_net_r": mean_net,
                "mean_net_r_standard_error": math.sqrt(variance_net / n) if math.isfinite(variance_net) else math.inf,
            }
        return {"status": "REACTION_NET_R_MODEL_AGGREGATED", "groups": len(self._stats),
                "eligible_labels": sum(len(v) for v in grouped.values()), "rejected_labels": rejected,
                "as_of": int(as_of), "execution_enabled": False}

    def export_stats(self) -> Dict[str, Any]:
        return {"version": 1, "status": "RESEARCH_ONLY_NOT_ACTIVATED",
                "min_samples": self.min_samples, "min_win_rate": self.min_win_rate,
                "min_mean_net_r": self.min_mean_net_r,
                "min_reverse_net_rr": self.min_reverse_net_rr,
                "groups": {k: dict(v) for k, v in self._stats.items()}}

    def load_stats(self, model: Mapping[str, Any]) -> None:
        if int(model.get("version", 0)) != 1 or not isinstance(model.get("groups"), Mapping):
            raise ValueError("Unsupported Base reaction model")
        clean: Dict[str, Dict[str, float]] = {}
        for key, value in model["groups"].items():
            n, win, mean = int(value["samples"]), float(value["win_rate"]), float(value["mean_net_r"])
            se = float(value.get("standard_error", 0.0))
            if "mean_net_r_standard_error" not in value:
                raise ValueError(f"Reaction model group lacks mean-net-R uncertainty: {key}")
            mean_se = float(value["mean_net_r_standard_error"])
            if n < 0 or not all(math.isfinite(x) for x in (win, mean, se, mean_se)) or not 0 <= win <= 1 or mean_se < 0:
                raise ValueError(f"Invalid reaction statistics: {key}")
            clean[str(key)] = {"samples": n, "win_rate": win, "mean_net_r": mean,
                               "standard_error": se, "mean_net_r_standard_error": mean_se}
        self._stats = clean

    def _qualifying_stat(self, key: str) -> tuple[bool, str, Mapping[str, Any] | None]:
        stat = self._stats.get(key)
        if not stat or int(stat["samples"]) < self.min_samples:
            return False, "Insufficient prior net-R examples for this exact timeframe/parent/depth/revisit profile.", stat
        mean_net = float(stat["mean_net_r"])
        mean_se = float(stat.get("mean_net_r_standard_error", 1e9))
        if float(stat["win_rate"]) < self.min_win_rate or mean_net < self.min_mean_net_r:
            return False, "Reaction profile fails historical win-rate or mean net-R gate.", stat
        # Bonferroni-style conservative threshold for the four depth bins compared
        # within a fixed timeframe/parent/revisit context.
        if mean_net - 2.5 * mean_se < self.min_mean_net_r:
            return False, "Reaction profile's depth-familywise lower confidence bound for mean net-R is below the minimum edge gate.", stat
        return True, "Reaction profile passes research gates including a conservative mean net-R confidence bound.", stat

    def evaluate(self, *, setup: Mapping[str, Any], quote: Mapping[str, Any], now: float,
                 parent: Mapping[str, Any] | None, child: Mapping[str, Any] | None,
                 micro: Mapping[str, Any] | None, reaction: Mapping[str, Any] | None,
                 active_position: Mapping[str, Any] | None = None,
                 current_trade: Mapping[str, Any] | None = None,
                 opposite_setup: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        """Evaluate one known-at-now Base reaction. All output is proposal-only.

        setup: direction, timeframe, base_type, zone_low/high, invalidation,
        target, atr, confidence, expires_at. reaction carries reaction_number and
        penetration_fraction measured in that same Base's own timeframe.
        """
        wait = lambda reason, **extra: {"status": "WAIT", "reason": reason,
                                       "execution_enabled": False, **extra}
        if not child or not parent or not micro or not reaction:
            return wait("A confirmed parent, child, fresh M1 trigger and measured same-Base reaction are all required.")
        tf = str(child.get("timeframe", ""))
        ptf = str(parent.get("timeframe", ""))
        if _rank(ptf) >= _rank(tf) or tf not in ("M15", "M5"):
            return wait("Parent/child timeframe hierarchy is invalid.")
        if int(parent.get("confirmation_time", 0)) > int(child.get("confirmation_time", 0)):
            return wait("Parent was not confirmed before the child setup; causal ordering failed.")
        child_direction = int(child.get("exit_direction", 0))
        if child_direction not in (-1, 1) or int(parent.get("exit_direction", 0)) != child_direction:
            return wait("Parent and child departure directions are not aligned.")
        now_i = int(now)
        for event, name in ((parent, "parent"), (child, "child"), (micro, "M1 trigger")):
            if int(event.get("confirmation_time", 0)) > now_i:
                return wait(f"{name} contains future information.")
        if str(micro.get("timeframe")) != "M1" or int(micro.get("exit_direction", 0)) != child_direction:
            return wait("M1 timing Base is not direction-aligned.")
        if now_i - int(micro.get("confirmation_time", 0)) > 8 * TIMEFRAME_SECONDS["M1"]:
            return wait("M1 trigger is stale.")
        if str(reaction.get("base_id")) != str(child.get("event_id")):
            return wait("Reaction measurement does not belong to the selected child Base.")
        try:
            reaction_number = int(reaction["reaction_number"])
            depth = float(reaction["penetration_fraction"])
            if reaction_number < 1 or not 0 <= depth <= 1 or not math.isfinite(depth):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            return wait("Reaction count/depth is missing or invalid.")
        aligned = int(parent.get("exit_direction", 0)) == child_direction
        relation = str(setup.get("parent_relation", "NESTED"))
        # Compare representative entry points from each depth bin using only the
        # exact timeframe/parent/revisit profile. Do not pick a depth without prior
        # net-R evidence for that cell.
        candidate_profiles = []
        for candidate_depth in (0.125, 0.375, 0.625, 0.875):
            candidate_key = self.profile_key(tf, str(child.get("base_type", "UNKNOWN")), ptf,
                                             relation, aligned, reaction_number, candidate_depth)
            ok, reason, candidate_stat = self._qualifying_stat(candidate_key)
            if ok and candidate_stat:
                candidate_profiles.append((float(candidate_stat["mean_net_r"]),
                                           int(candidate_stat["samples"]), candidate_depth,
                                           candidate_key, candidate_stat))
        if candidate_profiles:
            _, _, depth, key, stat = max(candidate_profiles, key=lambda item: (item[0], item[1]))
            passes, profile_reason = True, "Best qualifying depth-bin profile by historical mean net-R; still proposal-only."
        else:
            depth = float(reaction.get("penetration_fraction", 0.5))
            key = self.profile_key(tf, str(child.get("base_type", "UNKNOWN")), ptf,
                                   relation, aligned, reaction_number, depth)
            passes, profile_reason, stat = self._qualifying_stat(key)
        context = {"parent_id": parent.get("event_id"), "parent_timeframe": ptf,
                   "parent_relation": relation,
                   "child_id": child.get("event_id"), "child_timeframe": tf,
                   "micro_id": micro.get("event_id"), "reaction_number": reaction_number,
                   "penetration_fraction": depth, "penetration_bin": _depth_bin(depth),
                   "profile_key": key, "profile_stats": stat,
                   "depth_selection": "best_passing_profile_by_mean_net_R" if candidate_profiles else "no_candidate_depth_passed"}
        hold_ev = None
        wave_valid = True
        if current_trade:
            try:
                hold_ev = float(current_trade.get("hold_net_expected_value_r"))
                wave_valid = current_trade.get("wave_structure_valid") is True
                if not math.isfinite(hold_ev):
                    hold_ev = None
            except (TypeError, ValueError):
                hold_ev = None
                wave_valid = False
        opp = dict(opposite_setup or {})
        try:
            net_ev = float(opp["net_expected_value_r"])
            net_rr = float(opp["net_reward_risk"])
            opposite_confirmed = opp.get("reversal_confirmed") is True
        except (KeyError, TypeError, ValueError):
            net_ev, net_rr, opposite_confirmed = -math.inf, 0.0, False
        reverse_economics = opposite_confirmed and net_ev > 0 and net_rr >= self.min_reverse_net_rr
        held_wave_lost_edge = active_position and current_trade and (not wave_valid or hold_ev is None or hold_ev <= 0)
        if held_wave_lost_edge and not (reverse_economics and passes):
            return {"status": "EXIT_PROPOSAL", "reason": "Held wave no longer passes structural/economic continuation gate.",
                    "close_current_first": True, "structure": context, "hold_net_expected_value_r": hold_ev,
                    "wave_structure_valid": wave_valid, "execution_enabled": False,
                    "note": "Close proposal only; an opposite entry still needs a qualified reaction profile."}
        if not passes:
            if active_position:
                return wait(profile_reason, structure=context, exit_decision="HOLD_OR_PROTECT",
                            note="No reaction-profile edge: do not reverse on this evidence alone.")
            return wait(profile_reason, structure=context)

        direction = "BUY" if child_direction > 0 else "SELL"
        scenario = dict(setup)
        # Keep model win rate as a separate empirical statistic; do not disguise
        # it as calibrated signal confidence for the generic pending-order planner.
        scenario.update({"direction": direction, "setup_type": str(setup.get("setup_type", "RETEST")),
                         "confidence": float(setup.get("confidence", 0)),
                         "penetration_fraction": depth})
        if scenario["setup_type"].upper() == "RETEST":
            low, high = float(setup["zone_low"]), float(setup["zone_high"])
            scenario["entry_price"] = (high - depth * (high-low)) if direction == "BUY" else (low + depth * (high-low))
        plan = self.planner.plan(scenario, quote, now).to_dict()
        if active_position:
            held = str(active_position.get("direction", "")).upper()
            if held == direction:
                return {"status": "HOLDING", "reason": "Position direction agrees with qualified Base reaction; manage via stop/target and wave rules.",
                        "structure": context, "order_plan": plan, "execution_enabled": False}
            if held_wave_lost_edge and reverse_economics and plan["status"] == "PROPOSED":
                return {"status": "REVERSE_PROPOSAL", "reason": "Opposite Base structure and reaction profile pass; net economics remain positive after supplied costs.",
                        "close_current_first": True, "structure": context, "net_expected_value_r": net_ev,
                        "net_reward_risk": net_rr, "order_plan": plan, "execution_enabled": False}
            return {"status": "EXIT_OR_HOLD_REVIEW", "reason": "Current position may be reviewed against structural invalidation, but opposite entry fails confirmation/economic gates.",
                    "close_current_first": False, "structure": context, "net_expected_value_r": net_ev,
                    "net_reward_risk": net_rr, "execution_enabled": False}
        return {"status": "ENTRY_PROPOSAL" if plan["status"] == "PROPOSED" else "WAIT",
                "reason": profile_reason if plan["status"] == "PROPOSED" else plan["reason"],
                "structure": context, "scenario": scenario, "order_plan": plan,
                "execution_enabled": False}
