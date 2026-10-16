from datetime import datetime, timezone

from src.Intelligence.Execution.historical_structure_research import analyze_historical_structure_levels


def _bars():
    rows = []
    prices = [100, 102, 105, 109, 110, 106, 103, 100, 97, 99, 102, 105, 108, 107, 104,
              101, 98, 96, 99, 103, 106, 109, 108, 104, 100, 97, 99, 102, 105, 103]
    start = int(datetime(2026, 1, 1, 6, tzinfo=timezone.utc).timestamp())
    for i, close in enumerate(prices):
        op = close - 0.3
        hi = max(op, close) + (1.0 if i in (4, 21) else 0.5)
        lo = min(op, close) - 0.5
        rows.append({"time": start + i * 60, "open": op, "high": hi, "low": lo, "close": close})
    return rows


def test_structure_research_tracks_confirmed_swings_and_touch_outcomes():
    bars = _bars()
    result = analyze_historical_structure_levels({"M1": bars}, now=bars[-1]["time"] + 60,
                                                  current_prices={"M1": bars[-1]["close"]})
    assert result["status"] == "OK"
    data = result["timeframes"]["M1"]
    assert data["status"] == "OK"
    assert data["latest_swing_high"] is not None
    assert data["latest_swing_low"] is not None
    assert data["latest_swing_high"]["confirmed_at"] > data["latest_swing_high"]["pivot_time"]
    level = data["latest_swing_high"]
    assert "touch_count_after_confirmation" in level
    assert "max_continuation_distance_20_bars" in level
    assert "max_rejection_distance_20_bars" in level
    assert "touches_by_session_utc" in level
    assert result["current_price_context"]["M1"]["nearest_swing_levels"]


def test_structure_research_does_not_use_future_bars():
    bars = _bars()
    cutoff = bars[10]["time"] + 60
    result = analyze_historical_structure_levels({"M1": bars}, now=cutoff)
    assert result["timeframes"]["M1"]["last_candle_time"] <= cutoff
    assert all(level["confirmed_at"] <= cutoff for level in result["timeframes"]["M1"]["levels"])


def test_missing_timeframes_are_explicitly_reported():
    result = analyze_historical_structure_levels({"M1": _bars()})
    assert result["timeframes"]["MN1"]["status"] == "NO_DATA"
    assert result["timezone_for_sessions"] == "UTC"
