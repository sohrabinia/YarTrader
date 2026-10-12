import math

from scripts.research.train_hierarchical_base_behavior import (
    attach_causal_atr_scale,
    historical_spread_cost_price,
    simulate_pending_retest,
)


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


def test_historical_spread_cost_uses_entry_for_buy_and_exit_for_sell():
    bars = [{"spread_points": 10}, {"spread_points": 40}]

    assert historical_spread_cost_price(bars, 0, 1, 1, 0.01) == 0.1
    assert historical_spread_cost_price(bars, 0, 1, -1, 0.01) == 0.4


def test_historical_spread_cost_rejects_missing_or_invalid_data():
    assert historical_spread_cost_price([{}], 0, 0, 1, 0.01) is None
    assert historical_spread_cost_price([{"spread_points": 10}], 0, 0, 1, 0.0) is None


def test_simulation_refuses_candidate_without_confirmed_destination_base():
    event = {
        "timeframe": "M15",
        "exit_direction": 1,
        "base_low": 100.0,
        "base_high": 101.0,
        "base_atr": 1.0,
    }
    assert simulate_pending_retest(event, {"parent_aligned": True}, None, [], [], 1000, "m1-trigger", 0.05) is None
