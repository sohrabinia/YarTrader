"""Mine recurring causal parent/child Base interactions, not candle-shape templates.

Research output only: observations are grouped by structural relation, touch location,
visit number, direction, child timeframe, UTC session and reaction outcome. Future bars
are used only to label completed historical outcomes, never to establish level availability.
"""
from __future__ import annotations

from collections import defaultdict
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
import math

TIMEFRAME_ORDER = ("MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1")


def _session(epoch: int) -> str:
    hour = datetime.fromtimestamp(epoch, timezone.utc).hour
    if hour < 7: return "ASIA"
    if hour < 12: return "LONDON"
    if hour < 16: return "NEW_YORK"
    if hour < 21: return "NEW_YORK_LATE"
    return "ROLLOVER"


def _stamp(bar: Mapping[str, Any]) -> int:
    try: return int(bar.get("time", bar.get("timestamp", 0)))
    except (TypeError, ValueError, OverflowError): return 0


def _valid_bars(rows: Sequence[Mapping[str, Any]], cutoff: int) -> list[dict[str, float]]:
    result = []
    for row in rows or []:
        try:
            t = _stamp(row)
            o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
            if t <= 0 or t > cutoff or not all(math.isfinite(v) for v in (o, h, l, c)):
                continue
            if l <= 0 or h < max(o, c) or l > min(o, c) or h <= l:
                continue
            result.append({"time": t, "open": o, "high": h, "low": l, "close": c})
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return sorted({b["time"]: b for b in result}.values(), key=lambda b: b["time"])


def mine_structural_behaviors(
    events_by_tf: Mapping[str, Sequence[Mapping[str, Any]]],
    candles_by_tf: Mapping[str, Sequence[Mapping[str, Any]]],
    now: int,
    horizon_bars: int = 20,
    min_pattern_samples: int = 3,
) -> dict[str, Any]:
    """Summarize post-confirmation visits to Base zones and their child-base context.

    A motif is relational, not a symmetric drawing: parent TF/type/direction, child TF,
    parent-zone segment, visit ordinal, UTC session/hour and observed reaction. A sample
    is included only when its entire forward outcome horizon is available by ``now``.
    """
    cutoff = int(now)
    bars = {str(tf).upper(): _valid_bars(rows, cutoff) for tf, rows in candles_by_tf.items()}
    bar_times = {tf: [bar["time"] for bar in stream] for tf, stream in bars.items()}
    events = []
    for tf, group in events_by_tf.items():
        for raw in group or []:
            try:
                e = dict(raw)
                e["timeframe"] = str(e.get("timeframe") or tf).upper()
                e["confirmation_time"] = int(e.get("confirmation_time", 0))
                e["base_low"] = float(e["base_low"])
                e["base_high"] = float(e["base_high"])
                e["exit_direction"] = int(e.get("exit_direction", 0))
                if (e["confirmation_time"] > 0 and e["confirmation_time"] <= cutoff
                        and 0 < e["base_low"] < e["base_high"]
                        and e["timeframe"] in TIMEFRAME_ORDER):
                    events.append(e)
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
    events.sort(key=lambda e: (e["confirmation_time"], e["timeframe"]))
    samples: list[dict[str, Any]] = []
    touch_counts: dict[str, int] = defaultdict(int)
    for parent in events:
        parent_tf = parent["timeframe"]
        parent_rank = TIMEFRAME_ORDER.index(parent_tf)
        lo, hi = parent["base_low"], parent["base_high"]
        width = hi - lo
        if width <= 0: continue
        # A confirmed Base is not treated as valid forever. Stop counting new
        # interactions at the first parent-timeframe close through its far edge.
        # The invalidation candle itself is excluded because OHLC cannot order
        # intrabar touches relative to the closing break.
        parent_stream = bars.get(parent_tf, [])
        invalidated_at = None
        if parent_stream and parent["exit_direction"] != 0:
            start_parent = bisect_right(bar_times[parent_tf], parent["confirmation_time"])
            for parent_bar in parent_stream[start_parent:]:
                if ((parent["exit_direction"] > 0 and parent_bar["close"] < lo)
                        or (parent["exit_direction"] < 0 and parent_bar["close"] > hi)):
                    invalidated_at = int(parent_bar["time"])
                    break
        # Pre-filter nested events once per parent. Doing this inside every touch
        # would repeatedly scan the entire event history and scale poorly on M1 data.
        parent_nested_events = [
            e for e in events
            if TIMEFRAME_ORDER.index(e["timeframe"]) > parent_rank
            and e["base_low"] <= hi and e["base_high"] >= lo
            and e.get("event_id") != parent.get("event_id")
        ]
        # Use each supplied lower-timeframe candle stream independently.
        for child_tf, stream in bars.items():
            if child_tf not in TIMEFRAME_ORDER or TIMEFRAME_ORDER.index(child_tf) <= parent_rank:
                continue
            # Binary search avoids rescanning all candles before the parent confirmation.
            start_child = bisect_right(bar_times[child_tf], parent["confirmation_time"])
            end_child = bisect_left(bar_times[child_tf], invalidated_at) if invalidated_at else len(stream)
            post = stream[start_child:end_child]
            if not post: continue
            in_episode = False
            ordinal = 0
            for i, bar in enumerate(post):
                touched = bar["low"] <= hi and bar["high"] >= lo
                if not touched:
                    in_episode = False
                    continue
                if in_episode: continue
                in_episode = True
                # Outcome labels continue across a later parent-zone invalidation;
                # invalidation ends future *visits*, not the already-started outcome.
                future_start = bisect_right(bar_times[child_tf], bar["time"])
                future = stream[future_start:future_start + horizon_bars]
                if len(future) < horizon_bars: continue
                ordinal += 1
                prev = post[i - 1]["close"] if i else None
                close = bar["close"]
                if close > hi:
                    reaction = "BREAK_UP"
                elif close < lo:
                    reaction = "BREAK_DOWN"
                elif prev is not None and prev > hi and close < hi:
                    reaction = "REJECT_DOWN"
                elif prev is not None and prev < lo and close > lo:
                    reaction = "REJECT_UP"
                else:
                    reaction = "INSIDE_OR_AMBIGUOUS"
                # Locate the candle's overlap with the zone, rather than clamping
                # its whole-candle midpoint to an edge when the candle spans outside.
                overlap_low = max(lo, bar["low"])
                overlap_high = min(hi, bar["high"])
                touch_price = (overlap_low + overlap_high) / 2.0
                fraction = (touch_price - lo) / width
                segment = "LOWER" if fraction < 1/3 else "UPPER" if fraction > 2/3 else "MIDDLE"
                # Only child Bases already confirmed at the touch timestamp are
                # features. Child Bases confirmed later in the outcome horizon would
                # leak future information into the structural relationship.
                # Capture the full nested Base stack already known at touch time,
                # not only Bases on the candle stream used to observe the interaction.
                child_events = [e for e in parent_nested_events
                                if e["confirmation_time"] <= bar["time"]]
                child_tfs = sorted({e["timeframe"] for e in child_events},
                                   key=TIMEFRAME_ORDER.index)
                if parent["exit_direction"] > 0:
                    continuation = max(0.0, max(b["high"] for b in future) - hi) / width
                    reversal = max(0.0, hi - min(b["low"] for b in future)) / width
                elif parent["exit_direction"] < 0:
                    continuation = max(0.0, lo - min(b["low"] for b in future)) / width
                    reversal = max(0.0, max(b["high"] for b in future) - lo) / width
                else:
                    continuation = max((max(b["high"] for b in future) - hi),
                                       (lo - min(b["low"] for b in future)), 0.0) / width
                    reversal = max(0.0, max(b["high"] for b in future) - min(b["low"] for b in future)) / width
                ts = int(bar["time"])
                sample = {
                    "parent_base_id": parent.get("event_id"), "parent_timeframe": parent_tf,
                    "parent_confirmation_time": int(parent["confirmation_time"]),
                    "parent_zone_eventually_invalidated": invalidated_at is not None,
                    "parent_invalidated_at": invalidated_at,
                    "parent_base_type": str(parent.get("base_type", "UNKNOWN")),
                    "parent_direction": parent["exit_direction"], "parent_low": lo, "parent_high": hi,
                    "child_timeframe": child_tf, "child_base_ids": [e.get("event_id") for e in child_events if e.get("event_id")],
                    "child_base_count": len(child_events), "child_base_timeframes": child_tfs,
                    "nested_child_timeframes": child_tfs,
                    "child_timeframes_signature": ">".join(child_tfs) if child_tfs else "NONE",
                    "zone_segment": segment, "visit_ordinal": ordinal,
                    "reaction": reaction, "continuation_in_parent_widths": round(continuation, 4),
                    "reversal_excursion_in_parent_widths": round(reversal, 4),
                    "touch_time": ts, "utc_hour": datetime.fromtimestamp(ts, timezone.utc).hour,
                    "weekday_utc": datetime.fromtimestamp(ts, timezone.utc).weekday(),
                    "session_utc": _session(ts), "outcome_horizon_bars": horizon_bars,
                    "outcome_end_time": int(future[-1]["time"]),
                }
                samples.append(sample)
                touch_counts[child_tf] += 1
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for s in samples:
        key = (s["parent_timeframe"], s["parent_base_type"], s["parent_direction"],
               s["child_timeframe"], s.get("child_timeframes_signature", "NONE"),
               s["zone_segment"], "FIRST_VISIT" if s["visit_ordinal"] == 1 else "REVISIT",
               s["reaction"], s["session_utc"])
        grouped[key].append(s)
    motifs = []
    for key, group in grouped.items():
        n = len(group)
        motifs.append({
            "motif_id": "|".join(map(str, key)), "parent_timeframe": key[0],
            "parent_base_type": key[1], "parent_direction": key[2],
            "child_timeframe": key[3],
            "child_timeframes_signature": key[4],
            "nested_child_timeframes": [] if key[4] == "NONE" else key[4].split(">"),
            "zone_segment": key[5], "visit_class": key[6],
            "reaction": key[7], "session_utc": key[8], "samples": n,
            "mean_continuation_in_parent_widths": round(sum(x["continuation_in_parent_widths"] for x in group)/n, 4),
            "median_continuation_in_parent_widths": round(sorted(x["continuation_in_parent_widths"] for x in group)[n//2], 4),
            "mean_reversal_excursion_in_parent_widths": round(sum(x["reversal_excursion_in_parent_widths"] for x in group)/n, 4),
            "mean_child_bases_per_visit": round(sum(x["child_base_count"] for x in group)/n, 3),
            "sample_sufficient_for_exploration": n >= int(min_pattern_samples),
            "trade_edge_validated": False,
        })
    motifs.sort(key=lambda x: (x["samples"], x["mean_continuation_in_parent_widths"]), reverse=True)
    return {
        "status": "OK", "as_of": cutoff, "timezone": "UTC", "horizon_bars": horizon_bars,
        "event_count": len(events), "completed_touch_samples": len(samples),
        "motif_count": len(motifs), "motifs": motifs,
        "walk_forward_validation": validate_structural_behavior_samples(samples),
        # Keep every completed observation available to the durable store. The
        # persistence layer trims only the API/report sample preview to 2,000 rows.
        "samples": samples,
        "limitations": [
            "Descriptive historical evidence only; not a trade win rate or profitability claim.",
            "Session buckets use UTC and should be configured to broker/server time before operational use.",
            "Parent-zone interactions are observed on available lower-timeframe OHLC; intrabar order is unknowable.",
            "Only fully completed forward horizons are included; current incomplete visits are not labeled.",
            "Parent zones stop receiving new visits after a parent-timeframe close through the far edge; the break candle is excluded due unknown intrabar ordering.",
        ],
    }


def persist_and_aggregate_structural_behaviors(
    research: Mapping[str, Any], database_path: str, min_pattern_samples: int = 3,
) -> dict[str, Any]:
    """Persist observations idempotently and return motif statistics across prior runs.

    SQLite is the durable observation ledger. Observation IDs prevent duplicate samples
    when the same candle window is evaluated repeatedly. Persisted motifs remain
    descriptive; this function never marks a pattern as trade-validated.
    """
    import json
    import sqlite3
    from contextlib import closing
    from pathlib import Path

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(path), timeout=10.0)) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS structural_observations (
            observation_id TEXT PRIMARY KEY, parent_base_id TEXT, parent_timeframe TEXT NOT NULL,
            parent_base_type TEXT NOT NULL, parent_direction INTEGER NOT NULL,
            child_timeframe TEXT NOT NULL, child_timeframes_signature TEXT NOT NULL DEFAULT '',
            zone_segment TEXT NOT NULL, visit_class TEXT NOT NULL,
            reaction TEXT NOT NULL, session_utc TEXT NOT NULL, continuation REAL NOT NULL,
            reversal REAL NOT NULL, child_base_count INTEGER NOT NULL, touch_time INTEGER NOT NULL,
            outcome_horizon_bars INTEGER NOT NULL DEFAULT 20,
            algorithm_version TEXT NOT NULL DEFAULT 'structural_v2', payload_json TEXT NOT NULL)""")
        columns = {row[1] for row in db.execute("PRAGMA table_info(structural_observations)")}
        if "child_timeframes_signature" not in columns:
            db.execute("ALTER TABLE structural_observations ADD COLUMN child_timeframes_signature TEXT NOT NULL DEFAULT ''")
        if "outcome_horizon_bars" not in columns:
            db.execute("ALTER TABLE structural_observations ADD COLUMN outcome_horizon_bars INTEGER NOT NULL DEFAULT 20")
            # Preserve the horizon recorded in each legacy payload where available.
            for legacy_id, payload in db.execute("SELECT observation_id, payload_json FROM structural_observations").fetchall():
                try:
                    horizon = max(1, int(json.loads(payload).get("outcome_horizon_bars", 20)))
                    # Old keys omitted the horizon; upgrade them without duplicating
                    # observations when this same historical window is rerun.
                    upgraded_id = legacy_id if legacy_id.endswith(f"|H{horizon}") else f"{legacy_id}|H{horizon}"
                    if upgraded_id != legacy_id:
                        db.execute("UPDATE structural_observations SET observation_id=?, outcome_horizon_bars=? WHERE observation_id=?", (upgraded_id, horizon, legacy_id))
                    else:
                        db.execute("UPDATE structural_observations SET outcome_horizon_bars=? WHERE observation_id=?", (horizon, legacy_id))
                except (TypeError, ValueError, json.JSONDecodeError, sqlite3.IntegrityError):
                    continue
        if "algorithm_version" not in columns:
            # Existing rows were generated before the overlap-segment and horizon fixes.
            # Preserve them for audit, but do not mix them into current-version statistics.
            db.execute("ALTER TABLE structural_observations ADD COLUMN algorithm_version TEXT NOT NULL DEFAULT 'legacy_v1'")
        db.execute("CREATE INDEX IF NOT EXISTS idx_structural_touch_time ON structural_observations(touch_time)")
        for sample in research.get("samples", []):
            # Stable fallback identity prevents unrelated Bases without event IDs
            # from collapsing into one observation. Include geometry and confirmation.
            parent_id = str(sample.get("parent_base_id") or "|".join((
                str(sample.get("parent_timeframe", "UNKNOWN")),
                str(sample.get("parent_confirmation_time", 0)),
                str(sample.get("parent_base_type", "UNKNOWN")),
                format(float(sample.get("parent_low", 0.0)), ".10g"),
                format(float(sample.get("parent_high", 0.0)), ".10g"),
            )))
            child_tf = str(sample.get("child_timeframe") or "UNKNOWN_TF")
            touch_time = int(sample.get("touch_time", 0))
            horizon_bars = max(1, int(sample.get("outcome_horizon_bars", research.get("horizon_bars", 20))))
            algorithm_version = "structural_v2"
            observation_id = f"{parent_id}|{child_tf}|{touch_time}|{sample.get('zone_segment', 'UNKNOWN')}|SV2|H{horizon_bars}"
            visit_class = "FIRST_VISIT" if int(sample.get("visit_ordinal", 0)) == 1 else "REVISIT"
            signature = str(sample.get("child_timeframes_signature")
                            or ">".join(sample.get("nested_child_timeframes", [])) or "NONE")
            db.execute("""INSERT OR IGNORE INTO structural_observations
                (observation_id, parent_base_id, parent_timeframe, parent_base_type,
                 parent_direction, child_timeframe, child_timeframes_signature,
                 zone_segment, visit_class, reaction, session_utc, continuation,
                 reversal, child_base_count, touch_time, outcome_horizon_bars, algorithm_version, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (observation_id, parent_id, str(sample.get("parent_timeframe", "UNKNOWN")),
                 str(sample.get("parent_base_type", "UNKNOWN")), int(sample.get("parent_direction", 0)),
                 child_tf, signature, str(sample.get("zone_segment", "UNKNOWN")), visit_class,
                 str(sample.get("reaction", "UNKNOWN")), str(sample.get("session_utc", "UNKNOWN")),
                 float(sample.get("continuation_in_parent_widths", 0.0)),
                 float(sample.get("reversal_excursion_in_parent_widths", 0.0)),
                 int(sample.get("child_base_count", 0)), touch_time, horizon_bars, algorithm_version,
                 json.dumps(sample, ensure_ascii=False, allow_nan=False)))
        db.commit()
        rows = db.execute("""SELECT parent_timeframe, parent_base_type, parent_direction,
            child_timeframe, child_timeframes_signature, zone_segment, visit_class, reaction,
            session_utc, continuation, reversal, child_base_count, outcome_horizon_bars FROM structural_observations
            WHERE algorithm_version='structural_v2' ORDER BY touch_time ASC""").fetchall()
        all_current_payloads = db.execute("SELECT payload_json FROM structural_observations WHERE algorithm_version='structural_v2' ORDER BY touch_time ASC").fetchall()
        recent_rows = db.execute("SELECT payload_json FROM structural_observations WHERE algorithm_version='structural_v2' ORDER BY touch_time DESC LIMIT 2000").fetchall()
        total = db.execute("SELECT COUNT(*) FROM structural_observations WHERE algorithm_version='structural_v2'").fetchone()[0]

    grouped: dict[tuple[Any, ...], list[tuple[float, float, int]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[:9]) + (int(row[12]),)].append((float(row[9]), float(row[10]), int(row[11])))
    motifs = []
    for key, values in grouped.items():
        n = len(values)
        continuations = sorted(x[0] for x in values)
        reversals = [x[1] for x in values]
        motifs.append({
            "motif_id": "|".join(map(str, key)), "parent_timeframe": key[0],
            "parent_base_type": key[1], "parent_direction": key[2], "child_timeframe": key[3],
            "child_timeframes_signature": key[4],
            "nested_child_timeframes": [] if key[4] in ("", "NONE") else key[4].split(">"),
            "zone_segment": key[5], "visit_class": key[6], "reaction": key[7],
            "session_utc": key[8], "outcome_horizon_bars": key[9], "samples": n,
            "mean_continuation_in_parent_widths": round(sum(continuations) / n, 4),
            "median_continuation_in_parent_widths": round(continuations[n // 2], 4),
            "mean_reversal_excursion_in_parent_widths": round(sum(reversals) / n, 4),
            "mean_child_bases_per_visit": round(sum(x[2] for x in values) / n, 3),
            "sample_sufficient_for_exploration": n >= int(min_pattern_samples),
            "trade_edge_validated": False,
        })
    motifs.sort(key=lambda x: (x["samples"], x["mean_continuation_in_parent_widths"]), reverse=True)
    result = dict(research)
    result["motifs"] = motifs
    result["motif_count"] = len(motifs)
    result["durable_observation_count"] = int(total)
    result["samples"] = [json.loads(row[0]) for row in reversed(recent_rows)]
    # Validate all observations from the current algorithm version, not only the
    # 2,000-row API preview. Legacy algorithm versions remain stored but are excluded.
    result["walk_forward_validation"] = validate_structural_behavior_samples(
        [json.loads(row[0]) for row in all_current_payloads]
    )
    result["algorithm_version"] = "structural_v2"
    result["legacy_observations_preserved"] = True
    result["memory_store"] = "SQLITE_VERSIONED_DEDUPLICATED_HISTORICAL_OBSERVATIONS"
    return result


def validate_structural_behavior_samples(
    samples: Sequence[Mapping[str, Any]],
    train_fraction: float = 0.70,
    min_training_samples: int = 5,
    min_oos_samples: int = 5,
) -> dict[str, Any]:
    """Chronological holdout diagnostic for structural motifs; never a trade gate.

    The split is chronological and training labels whose outcome horizon crosses the
    split are embargoed. Motifs are learned from training rows only, then evaluated on
    later rows. This is a research diagnostic, not a broker-costed strategy backtest.
    """
    import math

    valid = []
    for raw in samples or []:
        try:
            row = dict(raw)
            row["touch_time"] = int(row["touch_time"])
            row["outcome_end_time"] = int(row["outcome_end_time"])
            row["continuation_in_parent_widths"] = float(row["continuation_in_parent_widths"])
            row["reversal_excursion_in_parent_widths"] = float(row["reversal_excursion_in_parent_widths"])
            if (row["touch_time"] > 0 and row["outcome_end_time"] >= row["touch_time"]
                    and math.isfinite(row["continuation_in_parent_widths"])
                    and math.isfinite(row["reversal_excursion_in_parent_widths"])):
                valid.append(row)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    valid.sort(key=lambda x: (x["touch_time"], x["outcome_end_time"]))
    if len(valid) < max(2 * int(min_training_samples), int(min_oos_samples) + 1):
        return {
            "status": "INSUFFICIENT_DATA", "sample_count": len(valid),
            "trade_edge_validated": False,
            "reason": "Not enough chronological observations for a separated train/test evaluation.",
        }
    split_index = int(len(valid) * float(train_fraction))
    split_index = min(max(1, split_index), len(valid) - 1)
    split_time = valid[split_index]["touch_time"]
    # Embargo any training observation whose future-label horizon overlaps the OOS era.
    train = [x for x in valid[:split_index] if x["outcome_end_time"] < split_time]
    test = [x for x in valid[split_index:] if x["touch_time"] >= split_time]
    if len(train) < int(min_training_samples) or len(test) < int(min_oos_samples):
        return {
            "status": "INSUFFICIENT_DATA", "sample_count": len(valid),
            "training_samples_after_embargo": len(train), "oos_samples": len(test),
            "split_time": split_time, "trade_edge_validated": False,
            "reason": "Chronological split or outcome-horizon embargo left too few samples.",
        }

    def parent_identity(row):
        explicit = row.get("parent_base_id")
        if explicit:
            return str(explicit)
        fields = ("parent_timeframe", "parent_confirmation_time", "parent_base_type",
                  "parent_low", "parent_high")
        fallback = "|".join(str(row.get(field, "")) for field in fields)
        return fallback if fallback.strip("|") else f"UNKNOWN_PARENT_AT_{row.get('touch_time', 0)}"

    # Keep test observations from parent Bases never used in training. The same
    # long-lived zone appearing on both sides can otherwise make OOS look stronger
    # than generalization to genuinely new structural zones.
    train_parent_ids = {parent_identity(row) for row in train}
    oos_before_parent_embargo = len(test)
    test = [row for row in test if parent_identity(row) not in train_parent_ids]
    if len(test) < int(min_oos_samples):
        return {
            "status": "INSUFFICIENT_UNSEEN_PARENT_BASES",
            "split_time": split_time,
            "training_samples_after_embargo": len(train),
            "oos_samples_before_parent_embargo": oos_before_parent_embargo,
            "oos_samples": len(test),
            "oos_parent_embargo_excluded": oos_before_parent_embargo - len(test),
            "trade_edge_validated": False,
            "reason": "Too few out-of-sample observations remain after excluding parent Bases seen in training.",
        }

    def key(row):
        return (
            row.get("parent_timeframe"), row.get("parent_base_type"),
            int(row.get("parent_direction", 0)), row.get("child_timeframe"),
            row.get("child_timeframes_signature")
                or ">".join(row.get("nested_child_timeframes", [])) or "NONE",
            row.get("zone_segment"),
            "FIRST_VISIT" if int(row.get("visit_ordinal", 0)) == 1 else "REVISIT",
            row.get("reaction"), row.get("session_utc"),
            int(row.get("outcome_horizon_bars", 20)),
        )

    training_groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in train:
        training_groups[key(row)].append(row)
    # Select motifs using training outcomes only. A motif is a candidate only if
    # it has enough samples and its mean continuation excursion exceeds reversal.
    # This direction is then frozen before the out-of-sample period is inspected.
    selected_training_motifs = {}
    for motif_key, group in training_groups.items():
        if len(group) < int(min_training_samples):
            continue
        mean_cont = sum(float(x["continuation_in_parent_widths"]) for x in group) / len(group)
        mean_rev = sum(float(x["reversal_excursion_in_parent_widths"]) for x in group) / len(group)
        if mean_cont > mean_rev:
            selected_training_motifs[motif_key] = {
                "training_samples": len(group),
                "training_mean_continuation": round(mean_cont, 4),
                "training_mean_reversal": round(mean_rev, 4),
                "training_excursion_edge": round(mean_cont - mean_rev, 4),
            }
    matched = [row for row in test if key(row) in selected_training_motifs]

    # Ablation baseline: select only on parent timeframe/type/direction, without
    # the nested child stack, zone segment, visit class, reaction, or session.
    def parent_only_key(row):
        return (row.get("parent_timeframe"), row.get("parent_base_type"),
                int(row.get("parent_direction", 0)), int(row.get("outcome_horizon_bars", 20)))

    parent_only_groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in train:
        parent_only_groups[parent_only_key(row)].append(row)
    selected_parent_only = {}
    for coarse_key, group in parent_only_groups.items():
        if len(group) < int(min_training_samples):
            continue
        mean_cont = sum(float(x["continuation_in_parent_widths"]) for x in group) / len(group)
        mean_rev = sum(float(x["reversal_excursion_in_parent_widths"]) for x in group) / len(group)
        if mean_cont > mean_rev:
            selected_parent_only[coarse_key] = {
                "training_samples": len(group),
                "training_excursion_edge": round(mean_cont - mean_rev, 4),
            }
    parent_only_matched = [row for row in test if parent_only_key(row) in selected_parent_only]

    def summarize(rows):
        if not rows:
            return {"samples": 0}
        continuation = [x["continuation_in_parent_widths"] for x in rows]
        reversal = [x["reversal_excursion_in_parent_widths"] for x in rows]
        dominant = sum(c > r for c, r in zip(continuation, reversal))
        n = len(rows)
        # Wilson interval for the descriptive continuation-dominance ratio.
        z = 1.959963984540054
        p = dominant / n
        den = 1 + z*z/n
        center = (p + z*z/(2*n)) / den
        radius = z * math.sqrt((p*(1-p)/n) + z*z/(4*n*n)) / den
        return {
            "samples": n,
            "mean_continuation_in_parent_widths": round(sum(continuation)/n, 4),
            "mean_reversal_excursion_in_parent_widths": round(sum(reversal)/n, 4),
            "continuation_dominance_ratio": round(p, 4),
            "continuation_dominance_wilson_95_ci": [round(max(0.0, center-radius), 4),
                                                       round(min(1.0, center+radius), 4)],
        }

    baseline = summarize(test)
    conditional = summarize(matched)
    parent_only_baseline = summarize(parent_only_matched)
    enough_matched = len(matched) >= int(min_oos_samples)
    delta = None
    if enough_matched:
        delta = round(
            conditional["mean_continuation_in_parent_widths"]
            - baseline["mean_continuation_in_parent_widths"], 4
        )
    delta_vs_parent_only = None
    reversal_delta_vs_parent_only = None
    if enough_matched and len(parent_only_matched) >= int(min_oos_samples):
        delta_vs_parent_only = round(
            conditional["mean_continuation_in_parent_widths"]
            - parent_only_baseline["mean_continuation_in_parent_widths"], 4
        )
        reversal_delta_vs_parent_only = round(
            conditional["mean_reversal_excursion_in_parent_widths"]
            - parent_only_baseline["mean_reversal_excursion_in_parent_widths"], 4
        )
    return {
        "status": "OOS_DIAGNOSTIC_ONLY" if enough_matched else "NO_MATCHED_OOS_MOTIFS",
        "split_time": split_time,
        "train_fraction_requested": float(train_fraction),
        "training_samples_after_embargo": len(train),
        "oos_samples_before_parent_embargo": oos_before_parent_embargo,
        "oos_samples": len(test),
        "oos_parent_embargo_excluded": oos_before_parent_embargo - len(test),
        "eligible_training_motifs": len(selected_training_motifs),
        "selected_training_motif_examples": [
            {"motif_key": list(k), **v}
            for k, v in list(selected_training_motifs.items())[:20]
        ],
        "matched_oos_samples": len(matched),
        "oos_unconditional_baseline": baseline,
        "oos_training_motif_subset": conditional,
        "parent_only_selected_training_motifs": len(selected_parent_only),
        "matched_oos_parent_only_samples": len(parent_only_matched),
        "oos_parent_only_baseline": parent_only_baseline,
        "mean_continuation_delta_vs_unconditional": delta,
        "mean_continuation_delta_vs_parent_only": delta_vs_parent_only,
        "mean_reversal_delta_vs_parent_only": reversal_delta_vs_parent_only,
        "trade_edge_validated": False,
        "limitations": [
            "This compares descriptive price excursions, not executed trades or net PnL.",
            "OHLC cannot resolve intrabar order, spread, slippage, commissions, or fills.",
            "Repeated touches from the same parent Base may be dependent; confidence intervals are descriptive.",
            "No classic-pattern baseline was found in the inspected detector path; equivalence comparison remains unimplemented.",
        ],
    }
