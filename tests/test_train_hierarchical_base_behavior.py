import math

from scripts.research.train_hierarchical_base_behavior import attach_causal_atr_scale


def test_attach_causal_atr_uses_only_closed_bars_at_confirmation():
    bars = [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0}
        for _ in range(18)
    ]
    bars[13].update(high=103.0, low=99.0)
    bars[14].update(high=102.0, low=98.0)
    event = {"confirmation_index": 14}

    attach_causal_atr_scale([event], bars, period=3)

    assert math.isclose(event["base_atr"], 10.0 / 3.0)

    future_changed = [dict(row) for row in bars]
    future_changed[15].update(high=10000.0, low=1.0, close=9999.0)
    future_event = {"confirmation_index": 14}
    attach_causal_atr_scale([future_event], future_changed, period=3)
    assert future_event["base_atr"] == event["base_atr"]


def test_attach_causal_atr_skips_insufficient_or_invalid_event_index():
    bars = [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0}
        for _ in range(10)
    ]
    events = [{"confirmation_index": 2}, {"confirmation_index": 20}]

    attach_causal_atr_scale(events, bars, period=3)

    assert all("base_atr" not in event for event in events)
