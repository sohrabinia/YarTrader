"""Live, causal multi-timeframe Base watcher for YarTrader.

Consumes caller-supplied CLOSED OHLC candles. It detects recent bases, links
nested parent/child zones, counts each completed revisit, measures penetration
and post-touch excursions, and emits an analysis snapshot. It never executes orders.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import os

from src.Research.Brain.multitimeframe_base_transition_engine import (
    TIMEFRAME_ORDER, TIMEFRAME_SECONDS, _bar_end_time, detect_base_departures,
)

# Bounded recent windows keep per-update work predictable. Feed sufficient closed
# candles; the monitor is a live observer, not a substitute for offline training.
WINDOWS = {"MN1": 120, "W1": 180, "D1": 260, "H4": 420, "H1": 600,
           "M15": 900, "M5": 1200, "M1": 1800}
SCAN_STEPS = {"MN1": 1, "W1": 1, "D1": 1, "H4": 2, "H1": 2,
              "M15": 3, "M5": 5, "M1": 5}


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(obj, Mapping) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _epoch(value: Any) -> int:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    if hasattr(value, "timestamp") and callable(value.timestamp):
        return int(value.timestamp())
    return int(float(value))


def _normalize_candles(candles: Sequence[Any], tf: str, now: int) -> list[dict[str, Any]]:
    rows = []
    # Market feeds may hand over deep history on every tick; inspect only a bounded tail.
    try:
        candles = candles[-(WINDOWS.get(tf, 500) * 3):]
    except (TypeError, IndexError):
        pass
    for candle in candles:
        try:
            ts = _epoch(_get(candle, "time", "timestamp", "Timestamp", "Time"))
            row = {"time": ts,
                   "open": float(_get(candle, "open", "Open")),
                   "high": float(_get(candle, "high", "High")),
                   "low": float(_get(candle, "low", "Low")),
                   "close": float(_get(candle, "close", "Close"))}
            if not all(math.isfinite(row[k]) for k in ("open", "high", "low", "close")):
                continue
            if row["high"] < max(row["open"], row["close"], row["low"]):
                continue
            if row["low"] > min(row["open"], row["close"], row["high"]):
                continue
            # Never consume a candle that cannot have closed as of the snapshot.
            if ts + TIMEFRAME_SECONDS.get(tf, 60) > now:
                continue
            rows.append(row)
        except (TypeError, ValueError, OverflowError):
            continue
    rows.sort(key=lambda x: x["time"])
    dedup = {}
    for row in rows:
        dedup[row["time"]] = row
    return list(dedup.values())[-WINDOWS.get(tf, 500):]


class MultitimeframeBaseBehaviorMonitor:
    """Stateful snapshot builder. All returned trade actions are proposal-only."""

    def __init__(self, state_path: str | Path | None = None) -> None:
        # Keep durable observation memory separate from source control and credentials.
        # Pass state_path=None to opt out (useful for isolated tests/research runs).
        self.state_path = Path(state_path) if state_path is not None else Path("runtime_logs") / "base_behavior_monitor_state.json"
        self._reaction_state: dict[str, dict[str, Any]] = {"schema_version": 1, "bases": {}}
        self._persistence_status = "DISABLED" if state_path is None else "NOT_LOADED"
        if state_path is not None:
            self._load_state()

    def _load_state(self) -> None:
        try:
            if self.state_path.exists():
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and raw.get("schema_version") == 1 and isinstance(raw.get("bases"), dict):
                    self._reaction_state = raw
                    self._persistence_status = "LOADED"
                else:
                    self._persistence_status = "INVALID_STATE_IGNORED"
            else:
                self._persistence_status = "NEW_STATE"
        except (OSError, ValueError, TypeError):
            self._persistence_status = "LOAD_ERROR"

    def _save_state(self) -> None:
        if self.state_path is None:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
            tmp.write_text(json.dumps(self._reaction_state, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            os.replace(tmp, self.state_path)
            self._persistence_status = "SAVED"
        except OSError:
            self._persistence_status = "SAVE_ERROR"

    def _merge_reaction_history(self, event_id: str, tf: str, observed: Sequence[Mapping[str, Any]], base_timeframe: str | None = None) -> list[dict[str, Any]]:
        bases = self._reaction_state.setdefault("bases", {})
        base = bases.setdefault(event_id, {"timeframe": base_timeframe or tf, "reactions": {}})
        reactions = base.setdefault("reactions", {})
        changed = False
        for item in observed:
            row = dict(item)
            # A revisit's start time is stable across rolling snapshots. Upsert it so
            # an in-progress episode can receive improved metrics without duplicates.
            key = f"{tf}:{int(row.get('start_time', 0))}"
            if reactions.get(key) != row:
                reactions[key] = row
                changed = True
        ordered = sorted(reactions.values(), key=lambda r: (int(r.get("start_time", 0)), str(r.get("timeframe", ""))))
        for number, row in enumerate(ordered, start=1):
            row["reaction_number"] = number
        if changed:
            self._save_state()
        return ordered

    @staticmethod
    def _parent_for(child: Mapping[str, Any],
                    events_by_tf: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any] | None:
        try:
            child_rank = TIMEFRAME_ORDER.index(str(child["timeframe"]))
        except ValueError:
            return None
        candidates = []
        for tf in TIMEFRAME_ORDER[:child_rank]:
            for parent in events_by_tf.get(tf, []):
                if int(parent["confirmation_time"]) > int(child["confirmation_time"]):
                    continue
                if int(parent["base_start_time"]) > int(child["base_start_time"]):
                    continue
                if int(parent["base_end_time"]) < int(child["base_end_time"]):
                    continue
                if float(parent["base_low"]) > float(child["base_low"]):
                    continue
                if float(parent["base_high"]) < float(child["base_high"]):
                    continue
                candidates.append(parent)
        return min(candidates, key=lambda e: TIMEFRAME_ORDER.index(str(e["timeframe"]))) if candidates else None

    @staticmethod
    def _reaction_rows(event: Mapping[str, Any], bars: Sequence[Mapping[str, Any]],
                       tf: str, now: int) -> list[dict[str, Any]]:
        low, high = float(event["base_low"]), float(event["base_high"])
        width = high - low
        direction = int(event.get("exit_direction", 0))
        if width <= 0 or direction not in (-1, 1):
            return []
        start = int(event["confirmation_time"])
        rows = [b for idx, b in enumerate(bars) if int(b["time"]) >= start and
                _bar_end_time(bars, idx, tf) <= now]
        episodes = []
        inside = False
        current = None
        for bar in rows:
            overlap = float(bar["low"]) <= high and float(bar["high"]) >= low
            if overlap and not inside:
                current = {"base_id": event["event_id"], "timeframe": event["timeframe"],
                           "visit": len(episodes) + 1, "start_time": int(bar["time"]),
                           "first_touch_price": min(high, max(low, float(bar["close"]))),
                           "penetration_fraction": 0.0, "mfe_atr": 0.0, "mae_atr": 0.0,
                           "bars": 0, "end_time": int(bar["time"])}
                episodes.append(current)
            if overlap and current is not None:
                if direction > 0:
                    depth = (high - max(low, float(bar["low"]))) / width
                    fav = (float(bar["high"]) - high) / max(float(event.get("base_atr", width)), 1e-12)
                    adv = (high - float(bar["low"])) / max(float(event.get("base_atr", width)), 1e-12)
                else:
                    depth = (min(high, float(bar["high"])) - low) / width
                    fav = (low - float(bar["low"])) / max(float(event.get("base_atr", width)), 1e-12)
                    adv = (float(bar["high"]) - low) / max(float(event.get("base_atr", width)), 1e-12)
                current["penetration_fraction"] = round(max(current["penetration_fraction"], min(1.0, max(0.0, depth))), 4)
                current["mfe_atr"] = round(max(current["mfe_atr"], fav), 4)
                current["mae_atr"] = round(max(current["mae_atr"], adv), 4)
                current["bars"] += 1
                current["end_time"] = int(bar["time"])
            inside = overlap
            if not overlap:
                current = None
        for episode in episodes:
            episode["duration_seconds"] = max(0, episode["end_time"] - episode["start_time"] + TIMEFRAME_SECONDS.get(tf, 60))
            episode["complete"] = episode["end_time"] < (int(rows[-1]["time"]) if rows else start)
        return episodes

    def analyze(self, candles_by_tf: Mapping[str, Sequence[Any]], now: int | float | datetime) -> dict[str, Any]:
        now_i = _epoch(now)
        bars_by_tf: dict[str, list[dict[str, Any]]] = {}
        events_by_tf: dict[str, list[dict[str, Any]]] = {}
        for tf in TIMEFRAME_ORDER:
            source = candles_by_tf.get(tf, ())
            bars = _normalize_candles(source, tf, now_i) if source else []
            if len(bars) < 50:
                bars_by_tf[tf] = bars
                events_by_tf[tf] = []
                continue
            bars_by_tf[tf] = bars
            events_by_tf[tf] = detect_base_departures(
                bars, tf, scan_step=SCAN_STEPS.get(tf, 1), horizon=min(24, max(5, len(bars)//20))
            )
        all_events = sorted((dict(e) for vals in events_by_tf.values() for e in vals
                             if int(e["confirmation_time"]) <= now_i),
                            key=lambda e: int(e["confirmation_time"]))
        for event in all_events:
            event["parent"] = None
            event["reaction_history"] = []
            parent = self._parent_for(event, events_by_tf)
            if parent:
                event["parent"] = {"event_id": parent["event_id"], "timeframe": parent["timeframe"],
                                   "direction": parent["exit_direction"],
                                   "alignment": "ALIGNED" if int(parent["exit_direction"]) == int(event["exit_direction"]) else "OPPOSED",
                                   "relation": "NESTED"}
            child_tfs = [candidate for candidate in TIMEFRAME_ORDER
                         if TIMEFRAME_ORDER.index(candidate) > TIMEFRAME_ORDER.index(event["timeframe"])
                         and bars_by_tf.get(candidate)]
            if not child_tfs and bars_by_tf.get(str(event["timeframe"])):
                child_tfs = [str(event["timeframe"])]
            history_by_tf = {}
            counts_by_tf = {}
            for child_tf in child_tfs:
                observed = self._reaction_rows(event, bars_by_tf[child_tf], child_tf, now_i)
                history = self._merge_reaction_history(str(event["event_id"]), child_tf, observed, base_timeframe=str(event["timeframe"]))
                history_by_tf[child_tf] = history
                counts_by_tf[child_tf] = len(history)
            # Keep per-timeframe counts separate: one market swing can touch the
            # same zone on M1 and M5 and must not be double-counted as one ordinal.
            event["reaction_history_by_timeframe"] = history_by_tf
            event["reaction_counts_by_timeframe"] = counts_by_tf
            event["reaction_count"] = sum(counts_by_tf.values())
            event["reaction_timeframe"] = child_tfs[-1] if child_tfs else None
            event["reaction_history"] = history_by_tf.get(event["reaction_timeframe"], []) if child_tfs else []
            event["last_reaction"] = event["reaction_history"][-1] if event["reaction_history"] else None
            micro_tf = next((candidate for candidate in reversed(TIMEFRAME_ORDER)
                             if bars_by_tf.get(candidate)), None)
            latest_bar = bars_by_tf[micro_tf][-1] if micro_tf else None
            close = float(latest_bar["close"]) if latest_bar else None
            low, high = float(event["base_low"]), float(event["base_high"])
            direction = int(event["exit_direction"])
            if close is None:
                wave_state = "NO_CLOSED_PRICE"
                favorable_atr = None
            elif low <= close <= high:
                wave_state = "RETESTING_BASE"
                favorable_atr = 0.0
            elif (direction > 0 and close < low) or (direction < 0 and close > high):
                wave_state = "STRUCTURE_INVALIDATED"
                favorable_atr = 0.0
            else:
                atr = max(float(event.get("base_atr", high-low)), 1e-12)
                favorable_atr = ((close-high) if direction > 0 else (low-close)) / atr
                wave_state = "RIDING_WAVE" if favorable_atr >= 1.0 else "POST_DEPARTURE"
            event["wave_state"] = wave_state
            event["favorable_excursion_atr_at_snapshot"] = round(favorable_atr, 4) if favorable_atr is not None else None
            event["wave_state_price_timeframe"] = micro_tf
        recent = [e for e in all_events if now_i - int(e["confirmation_time"]) <=
                  8 * TIMEFRAME_SECONDS.get(str(e["timeframe"]), 60)]
        parents = [e for e in recent if TIMEFRAME_ORDER.index(str(e["timeframe"])) < TIMEFRAME_ORDER.index("M15")]
        children = [e for e in recent if e["timeframe"] in ("M15", "M5")]
        latest_child = children[-1] if children else None
        parent = self._parent_for(latest_child, events_by_tf) if latest_child else None
        alignment = None
        if parent and latest_child:
            alignment = "ALIGNED" if int(parent["exit_direction"]) == int(latest_child["exit_direction"]) else "OPPOSED"
        return {
            "status": "BASE_BEHAVIOR_OBSERVATION_ONLY",
            "as_of": now_i,
            "persistence": {"status": self._persistence_status,
                            "state_path": str(self.state_path) if self.state_path is not None else None,
                            "stored_bases": len(self._reaction_state.get("bases", {})),
                            "stored_reactions": sum(len(b.get("reactions", {})) for b in self._reaction_state.get("bases", {}).values())},
            "execution_enabled": False,
            "timeframes": {tf: {"closed_bars": len(bars_by_tf.get(tf, [])),
                                "detected_bases": len(events_by_tf.get(tf, [])),
                                "recent_bases": sum(1 for e in events_by_tf.get(tf, [])
                                    if now_i - int(e["confirmation_time"]) <= 8*TIMEFRAME_SECONDS.get(tf, 60))}
                           for tf in TIMEFRAME_ORDER},
            "active_bases": recent,
            "parent_child": {"latest_child_id": latest_child.get("event_id") if latest_child else None,
                             "parent_id": parent.get("event_id") if parent else None,
                             "alignment": alignment,
                             "status": "LINKED" if parent else "NO_CONFIRMED_PARENT"},
            "reaction_ledger": [{"base_id": e["event_id"], "timeframe": e["timeframe"],
                                 "reaction_counts_by_timeframe": e.get("reaction_counts_by_timeframe", {}),
                                 "reaction_history_by_timeframe": e.get("reaction_history_by_timeframe", {}),
                                 "total_observed_visits_across_timeframes": e.get("reaction_count", 0),
                                 "last_reaction": e.get("last_reaction")} for e in all_events],
            "decision": {"status": "WAIT", "reason": "Observation is not a validated, costed strategy; proposal/entry/reversal gates remain closed.",
                         "entry_proposal": None, "exit_proposal": None, "reverse_proposal": None},
            "data_contract": "Input candles must be closed, chronological OHLC bars; only data known by as_of is used.",
        }
