from datetime import datetime, timedelta, timezone

from src.Research.Brain.brain_context import build_brain_context, discover_cross_symbol_relations
from src.Research.Brain.discovery import PatternDiscoveryEngine
from src.Research.Brain.models import MarketObservation


def candle(symbol, tf, ts, close):
    return MarketObservation(
        symbol=symbol,
        timeframe=tf,
        timestamp=ts,
        high=close + 0.5,
        low=close - 0.5,
        open_price=close - 0.1,
        close_price=close,
        volume=1.0,
    )


def test_context_is_point_in_time_and_remembers_last_confirmed_swings():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    obs = [
        candle("XAUUSD", "M1", t0 + timedelta(minutes=i), v)
        for i, v in enumerate([100, 105, 101, 104, 99, 103, 102, 200])
    ]
    decision = t0 + timedelta(minutes=6)
    ctx = build_brain_context("XAUUSD", "M1", decision, {"M1": obs})
    snap = ctx["history"]["M1"]
    assert snap["last_close"] == 102
    assert snap["last_timestamp"] == (t0 + timedelta(minutes=6)).isoformat()
    assert snap["structure"]["latest_swing_high"] is not None
    assert snap["structure"]["latest_swing_low"] is not None
    assert ctx["future_excluded"] is True


def test_context_changes_when_closed_higher_timeframe_context_changes():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    m1 = [candle("XAUUSD", "M1", t0 + timedelta(minutes=i), 100 + i) for i in range(10)]
    m15a = [candle("XAUUSD", "M15", t0 + timedelta(minutes=15*i), 200 + i) for i in range(3)]
    m15b = m15a + [candle("XAUUSD", "M15", t0 + timedelta(minutes=45), 180)]
    a = build_brain_context("XAUUSD", "M1", t0 + timedelta(minutes=30), {"M1": m1, "M15": m15a})
    b = build_brain_context("XAUUSD", "M1", t0 + timedelta(minutes=60), {"M1": m1, "M15": m15b})
    assert a["context_id"] != b["context_id"]
    assert a["history"]["M15"]["last_close"] == 202
    assert b["history"]["M15"]["last_close"] == 180


def test_cross_symbol_relation_is_discovered_not_hard_coded():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    increments = [1, 3, 2, 4, 1, 5, 2, 3, 4, 2, 5, 1]
    source_prices = []
    target_prices = []
    a = b = 100.0
    for i, inc in enumerate(increments):
        a += inc
        source_prices.append(a)
        if i >= 2:
            b += increments[i - 2]
        target_prices.append(b)
    source = [candle("AAA", "M1", t0 + timedelta(minutes=i), v) for i, v in enumerate(source_prices)]
    target = [candle("BBB", "M1", t0 + timedelta(minutes=i), v) for i, v in enumerate(target_prices)]
    relations = discover_cross_symbol_relations(
        {"AAA": source, "BBB": target},
        t0 + timedelta(minutes=11),
        "M1",
        max_lag=4,
        min_samples=6,
        min_abs_correlation=0.75,
    )
    assert any(r["source_symbol"] == "AAA" and r["target_symbol"] == "BBB" and r["lag_bars"] == 2 for r in relations)


def test_pattern_matching_requires_same_context_when_context_is_known():
    engine = PatternDiscoveryEngine(similarity_threshold=0.8)
    p = engine.create_new_pattern([1.0, -0.5, 0.25, 0.1], symbol="XAUUSD", timeframe="M1",
                                  timeframe_signature=["M1", "M15"], context_id="ctx-a",
                                  context_signature={"history": {"M15": {"last_close": 1}}})
    assert engine.find_matches([1.0, -0.5, 0.25, 0.1], [p], "XAUUSD", "M1", ["M1", "M15"], "ctx-a")
    assert engine.find_matches([1.0, -0.5, 0.25, 0.1], [p], "XAUUSD", "M1", ["M1", "M15"], "ctx-b") == []
