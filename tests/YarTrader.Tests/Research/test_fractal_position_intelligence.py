"""
Comprehensive Unit & Behavioral Test Baseline for YarTrader Autonomous Position Intelligence
Tests state machine transitions, movement states, thesis weakening/invalidation, healthy vs dangerous pullbacks,
structural exits without fixed SL, re-entry timing, symmetric directional flips, position sizing math, and look-ahead invariants.
"""

import pytest
from src.Research.Brain.fractal_position_intelligence import (
    FractalPositionThesis,
    FractalPositionLifecycleManager,
    VALID_LIFECYCLE_STATES
)


def test_position_thesis_initialization_and_risk_sizing():
    thesis = FractalPositionThesis(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00Z",
        entry_scale="H1",
        parent_scale="H4",
        macro_scale="D1",
        risk_budget_usd=100.0,
        structural_invalidation_price=2330.0,
        target_price=2380.0
    )

    assert thesis.symbol == "XAUUSD"
    assert thesis.direction == "BUY"
    assert thesis.entry_price == 2350.0
    assert thesis.structural_invalidation_price == 2330.0
    assert thesis.target_price == 2380.0
    assert thesis.risk_distance == 20.0
    assert thesis.position_size_oz == 5.0  # $100 / $20 = 5.0 oz
    assert thesis.current_state == "ENTERED"
    assert thesis.thesis_status == "VALID"


def test_state_machine_valid_transitions():
    thesis = FractalPositionThesis(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00Z",
        risk_budget_usd=100.0,
        structural_invalidation_price=2330.0
    )

    thesis.record_state_change("HEALTHY_EXPANSION", "Expansion confirmed on M5")
    assert thesis.current_state == "HEALTHY_EXPANSION"

    thesis.record_state_change("HEALTHY_PULLBACK", "Pullback within H4 bounds")
    assert thesis.current_state == "HEALTHY_PULLBACK"

    thesis.record_state_change("EXITED", "Target reached")
    assert thesis.current_state == "EXITED"
    assert len(thesis.state_history) == 4


def test_multi_scale_movement_state_classification():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD")

    # Scenario 1: Healthy Expansion (D1 Bullish, H4 Bullish, M5 Bullish)
    candles_healthy = {
        "D1": [{"open": 2300.0, "high": 2360.0, "low": 2290.0, "close": 2355.0}],
        "H4": [{"open": 2340.0, "high": 2360.0, "low": 2335.0, "close": 2355.0}],
        "M5": [{"open": 2350.0, "high": 2356.0, "low": 2349.0, "close": 2355.0}]
    }
    state_healthy = mgr.evaluate_market_movement_state(candles_healthy)
    assert state_healthy["macro_direction"] == "BULLISH"
    assert state_healthy["movement_state"] == "EXPANSION"
    assert not state_healthy["is_pullback"]

    # Scenario 2: Healthy Pullback (D1 Bullish, H4 Bullish, M5 Bearish)
    candles_pullback = {
        "D1": [{"open": 2300.0, "high": 2360.0, "low": 2290.0, "close": 2355.0}],
        "H4": [{"open": 2340.0, "high": 2360.0, "low": 2335.0, "close": 2355.0}],
        "M5": [{"open": 2355.0, "high": 2356.0, "low": 2348.0, "close": 2350.0}]
    }
    state_pullback = mgr.evaluate_market_movement_state(candles_pullback)
    assert state_pullback["movement_state"] == "HEALTHY_PULLBACK"
    assert state_pullback["is_pullback"]

    # Scenario 3: Dangerous Pullback (D1 Bullish, H4 Bearish, M5 Bearish)
    candles_dangerous = {
        "D1": [{"open": 2300.0, "high": 2360.0, "low": 2290.0, "close": 2355.0}],
        "H4": [{"open": 2355.0, "high": 2356.0, "low": 2330.0, "close": 2335.0}],
        "M5": [{"open": 2350.0, "high": 2352.0, "low": 2330.0, "close": 2332.0}]
    }
    state_dangerous = mgr.evaluate_market_movement_state(candles_dangerous)
    assert state_dangerous["movement_state"] == "DANGEROUS_PULLBACK"


def test_structural_invalidation_exit_and_reentry_registration():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD", default_risk_budget_usd=100.0)
    pos = mgr.open_position(
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00Z",
        invalidation_price=2340.0,
        target_price=2380.0
    )

    # Bar triggers structural invalidation
    candle_invalid = {
        "timestamp": "2026-08-25T10:15:00Z",
        "open": 2345.0,
        "high": 2346.0,
        "low": 2338.0,
        "close": 2339.0
    }
    m_state = {"movement_state": "HEALTHY_PULLBACK"}

    actions = mgr.update_positions_and_manage_lifecycle(candle_invalid, m_state)
    assert len(actions) == 1
    assert actions[0]["action"] == "EXIT"
    assert actions[0]["reason"] == "STRUCTURAL_INVALIDATION"
    assert len(mgr.active_positions) == 0
    assert len(mgr.history_positions) == 1
    assert len(mgr.reentry_candidates) == 1
    assert len(mgr.direction_transition_candidates) == 1
    assert mgr.direction_transition_candidates[0]["to_direction"] == "SELL"


def test_structural_trailing_stop_update():
    thesis = FractalPositionThesis(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00Z",
        structural_invalidation_price=2330.0
    )

    thesis.update_structural_trailing_stop(2340.0)
    assert thesis.structural_invalidation_price == 2340.0

    # Should not move stop backwards
    thesis.update_structural_trailing_stop(2335.0)
    assert thesis.structural_invalidation_price == 2340.0


def test_reentry_and_direction_transition_execution():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD", default_risk_budget_usd=100.0)
    pos = mgr.open_position(
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00Z",
        invalidation_price=2340.0,
        target_price=2380.0
    )

    # Trigger exit to populate candidate pools
    mgr.update_positions_and_manage_lifecycle(
        {"timestamp": "2026-08-25T10:05:00Z", "high": 2342.0, "low": 2335.0, "close": 2338.0},
        {"movement_state": "DANGEROUS_PULLBACK"}
    )

    # Execute Direction Transition (BUY -> SELL)
    new_sell = mgr.execute_direction_transition(
        candidate_idx=0,
        entry_price=2338.0,
        entry_time="2026-08-25T10:10:00Z",
        invalidation_price=2350.0,
        target_price=2310.0
    )
    assert new_sell is not None
    assert new_sell.direction == "SELL"
    assert new_sell.entry_price == 2338.0
    assert len(mgr.active_positions) == 1


def test_no_lookahead_invariant():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD")
    pos = mgr.open_position(
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00Z",
        invalidation_price=2330.0,
        target_price=2380.0
    )

    # Candle 1: Normal progression
    c1 = {"timestamp": "2026-08-25T10:01:00Z", "high": 2355.0, "low": 2348.0, "close": 2354.0}
    actions1 = mgr.update_positions_and_manage_lifecycle(c1, {"movement_state": "EXPANSION"})
    assert len(actions1) == 1
    assert actions1[0]["action"] == "HOLD"
    assert pos.current_mfe == 5.0
    assert pos.current_mae == 2.0

    # Ensure future candles cannot affect past excursion
    c2 = {"timestamp": "2026-08-25T10:02:00Z", "high": 2370.0, "low": 2352.0, "close": 2368.0}
    actions2 = mgr.update_positions_and_manage_lifecycle(c2, {"movement_state": "EXPANSION"})
    assert pos.current_mfe == 20.0
