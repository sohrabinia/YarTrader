from src.Decision.Intelligence.hierarchical_base_behavior_engine import HierarchicalBaseBehaviorEngine


def _base(event_id, timeframe, start, end, confirmation, low, high, direction):
    return {
        "event_id": event_id,
        "timeframe": timeframe,
        "base_type": "RBD",
        "base_start_time": start,
        "base_end_time": end,
        "confirmation_time": confirmation,
        "base_low": low,
        "base_high": high,
        "base_mid": (low + high) / 2,
        "base_width": high - low,
        "exit_direction": direction,
    }


def test_newest_orphan_child_does_not_hide_older_valid_multitimeframe_setup():
    parent = _base("H1-parent", "H1", 700, 980, 900, 90, 110, 1)
    older_child = _base("M5-child-with-parent", "M5", 950, 970, 1000, 99, 101, 1)
    newest_orphan = _base("M5-orphan", "M5", 1020, 1040, 1050, 120, 122, -1)
    micro_trigger = _base("M1-trigger", "M1", 1055, 1059, 1060, 100, 101, 1)

    result = HierarchicalBaseBehaviorEngine().analyze(
        {"H1": [parent], "M5": [older_child, newest_orphan], "M1": [micro_trigger]},
        quote={"bid": 100.2, "ask": 100.3},
        now=1100,
        exploration_mode=True,
    )

    structure = result["structure"]
    assert structure["parent_base_id"] == "H1-parent"
    assert structure["child_base_id"] == "M5-child-with-parent"
    assert structure["micro_base_id"] == "M1-trigger"
    assert structure["hierarchy_complete_to_m1"] is True
