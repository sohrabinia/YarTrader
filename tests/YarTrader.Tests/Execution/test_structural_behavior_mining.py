from datetime import datetime, timezone

from src.Intelligence.Execution.structural_behavior_mining import mine_structural_behaviors


def _fixture():
    start = int(datetime(2026, 1, 5, 8, tzinfo=timezone.utc).timestamp())
    closes = [105, 106, 107, 109, 108, 111, 112, 109, 108, 107, 106, 105]
    bars = []
    for i, close in enumerate(closes):
        op = close - 0.2
        bars.append({"time": start + i * 60, "open": op,
                     "high": max(op, close) + (1.2 if i in (3, 4) else 0.4),
                     "low": min(op, close) - 0.4, "close": close})
    events = {
        "H4": [{"event_id": "parent-h4", "timeframe": "H4", "base_type": "DEMAND",
                "confirmation_time": start + 60, "base_low": 100.0, "base_high": 110.0,
                "exit_direction": 1}],
        "M1": [{"event_id": "child-m1", "timeframe": "M1", "base_type": "DEMAND",
                "confirmation_time": start + 240, "base_low": 105.0, "base_high": 109.0,
                "exit_direction": 1}],
    }
    return start, bars, events


def test_mines_parent_child_reaction_motifs_and_time_context():
    start, bars, events = _fixture()
    result = mine_structural_behaviors(events, {"M1": bars}, now=bars[-1]["time"],
                                       horizon_bars=2, min_pattern_samples=1)
    assert result["status"] == "OK"
    assert result["completed_touch_samples"] > 0
    sample = next(s for s in result["samples"] if s["parent_base_id"] == "parent-h4")
    assert sample["parent_timeframe"] == "H4"
    assert sample["child_timeframe"] == "M1"
    assert sample["session_utc"] == "LONDON"
    assert sample["outcome_end_time"] <= bars[-1]["time"]
    assert "reaction" in sample and "zone_segment" in sample
    # A child Base confirmed after this touch must not be included as a feature.
    assert sample["touch_time"] < events["M1"][0]["confirmation_time"]
    assert sample["child_base_count"] == 0
    assert result["motifs"]
    assert all(m["trade_edge_validated"] is False for m in result["motifs"])


def test_does_not_label_incomplete_forward_horizon():
    _, bars, events = _fixture()
    cutoff = bars[4]["time"]
    result = mine_structural_behaviors(events, {"M1": bars}, now=cutoff,
                                       horizon_bars=3, min_pattern_samples=1)
    assert result["completed_touch_samples"] == 0
    assert all(s["outcome_end_time"] <= cutoff for s in result["samples"])


def test_missing_or_invalid_streams_fail_closed_with_empty_research():
    result = mine_structural_behaviors({}, {}, now=1_800_000_000)
    assert result["status"] == "OK"
    assert result["event_count"] == 0
    assert result["completed_touch_samples"] == 0
    assert result["motifs"] == []


def test_persisted_behavior_memory_deduplicates_repeated_analysis(tmp_path):
    from src.Intelligence.Execution.structural_behavior_mining import persist_and_aggregate_structural_behaviors

    _, bars, events = _fixture()
    research = mine_structural_behaviors(events, {"M1": bars}, now=bars[-1]["time"],
                                         horizon_bars=2, min_pattern_samples=1)
    database = tmp_path / "behavior.sqlite3"
    first = persist_and_aggregate_structural_behaviors(research, str(database), min_pattern_samples=1)
    second = persist_and_aggregate_structural_behaviors(research, str(database), min_pattern_samples=1)
    assert first["durable_observation_count"] == research["completed_touch_samples"]
    assert second["durable_observation_count"] == first["durable_observation_count"]
    assert second["memory_store"] == "SQLITE_VERSIONED_DEDUPLICATED_HISTORICAL_OBSERVATIONS"
    assert second["motifs"]
    assert all(m["trade_edge_validated"] is False for m in second["motifs"])



def test_chronological_holdout_validation_uses_training_motifs_only():
    from src.Intelligence.Execution.structural_behavior_mining import validate_structural_behavior_samples

    rows = []
    start = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())
    for i in range(100):
        rows.append({
            "parent_base_id": f"parent-{i // 10}",
            "touch_time": start + i * 100,
            "outcome_end_time": start + i * 100 + 200,
            "parent_timeframe": "H4",
            "parent_base_type": "RBR",
            "parent_direction": 1,
            "child_timeframe": "M5",
            "zone_segment": "LOWER",
            "visit_ordinal": 1,
            "reaction": "REJECT_UP",
            "session_utc": "LONDON",
            "continuation_in_parent_widths": 1.5 if i % 3 else 0.2,
            "reversal_excursion_in_parent_widths": 0.4,
        })
    result = validate_structural_behavior_samples(
        rows, train_fraction=0.7, min_training_samples=5, min_oos_samples=5
    )
    assert result["status"] == "OOS_DIAGNOSTIC_ONLY"
    assert result["training_samples_after_embargo"] < 70
    assert result["matched_oos_samples"] > 0
    assert result["parent_only_selected_training_motifs"] >= 1
    assert result["oos_parent_only_baseline"]["samples"] > 0
    assert result["mean_continuation_delta_vs_parent_only"] is not None
    assert result["trade_edge_validated"] is False
    assert result["oos_training_motif_subset"]["samples"] == result["matched_oos_samples"]


def test_chronological_holdout_validation_fails_closed_on_small_data():
    from src.Intelligence.Execution.structural_behavior_mining import validate_structural_behavior_samples

    result = validate_structural_behavior_samples([])
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["trade_edge_validated"] is False


def test_nested_child_stack_includes_only_bases_confirmed_by_touch_time():
    start, bars, events = _fixture()
    events["M15"] = [{
        "event_id": "child-m15-known", "timeframe": "M15", "base_type": "RBR",
        "confirmation_time": start + 100, "base_low": 104.0, "base_high": 109.0,
        "exit_direction": 1,
    }]
    result = mine_structural_behaviors(events, {"M1": bars}, now=bars[-1]["time"],
                                       horizon_bars=2, min_pattern_samples=1)
    first = next(s for s in result["samples"] if s["touch_time"] < events["M1"][0]["confirmation_time"])
    assert first["nested_child_timeframes"] == ["M15"]
    assert first["child_timeframes_signature"] == "M15"
    assert first["child_base_count"] == 1


def test_parent_zone_invalidation_stops_new_visits_but_keeps_started_outcome_horizon():
    start, bars, events = _fixture()
    invalidation_time = start + 240
    parent_bars = [{
        "time": invalidation_time, "open": 101.0, "high": 103.0,
        "low": 98.0, "close": 99.0,
    }]
    result = mine_structural_behaviors(
        events, {"M1": bars, "H4": parent_bars},
        now=bars[-1]["time"], horizon_bars=2, min_pattern_samples=1,
    )
    samples = [s for s in result["samples"] if s["parent_base_id"] == "parent-h4"]
    assert samples
    assert all(s["touch_time"] < invalidation_time for s in samples)
    assert any(s["outcome_end_time"] >= invalidation_time for s in samples)
    assert all(s["parent_zone_eventually_invalidated"] for s in samples)


def test_persistence_migrates_existing_sqlite_schema(tmp_path):
    import sqlite3
    from src.Intelligence.Execution.structural_behavior_mining import persist_and_aggregate_structural_behaviors

    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("""CREATE TABLE structural_observations (
            observation_id TEXT PRIMARY KEY, parent_base_id TEXT, parent_timeframe TEXT NOT NULL,
            parent_base_type TEXT NOT NULL, parent_direction INTEGER NOT NULL,
            child_timeframe TEXT NOT NULL, zone_segment TEXT NOT NULL, visit_class TEXT NOT NULL,
            reaction TEXT NOT NULL, session_utc TEXT NOT NULL, continuation REAL NOT NULL,
            reversal REAL NOT NULL, child_base_count INTEGER NOT NULL, touch_time INTEGER NOT NULL,
            payload_json TEXT NOT NULL)""")
    _, bars, events = _fixture()
    research = mine_structural_behaviors(events, {"M1": bars}, now=bars[-1]["time"],
                                         horizon_bars=2, min_pattern_samples=1)
    result = persist_and_aggregate_structural_behaviors(research, str(database), min_pattern_samples=1)
    with sqlite3.connect(database) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(structural_observations)")}
    assert "child_timeframes_signature" in columns
    assert result["durable_observation_count"] == research["completed_touch_samples"]



def test_persistence_keeps_different_outcome_horizons_separate(tmp_path):
    from src.Intelligence.Execution.structural_behavior_mining import persist_and_aggregate_structural_behaviors

    _, bars, events = _fixture()
    short = mine_structural_behaviors(events, {"M1": bars}, now=bars[-1]["time"],
                                     horizon_bars=2, min_pattern_samples=1)
    long = mine_structural_behaviors(events, {"M1": bars}, now=bars[-1]["time"],
                                    horizon_bars=3, min_pattern_samples=1)
    database = tmp_path / "multi-horizon.sqlite3"
    first = persist_and_aggregate_structural_behaviors(short, str(database), min_pattern_samples=1)
    second = persist_and_aggregate_structural_behaviors(long, str(database), min_pattern_samples=1)
    assert second["durable_observation_count"] == (
        first["durable_observation_count"] + long["completed_touch_samples"]
    )
    assert {motif["outcome_horizon_bars"] for motif in second["motifs"]} == {2, 3}
    assert second["algorithm_version"] == "structural_v2"
    assert second["walk_forward_validation"]["trade_edge_validated"] is False
