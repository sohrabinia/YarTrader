"""
Comprehensive Unit & Behavioral Test Baseline for YarTrader Autonomous Position Intelligence
Tests 120-second normal exit lifetime floor, session lifecycle states, scale arbitration, movement states,
thesis weakening/invalidation, healthy vs dangerous pullbacks, structural exits, re-entry timing,
symmetric directional flips, position sizing math, and look-ahead invariants.
"""

import pytest
from src.Research.Brain.fractal_position_intelligence import (
    FractalPositionThesis,
    FractalPositionLifecycleManager,
    POSITION_MINIMUM_NORMAL_LIFETIME_SECONDS,
    VALID_LIFECYCLE_STATES,
    VALID_SESSION_STATES
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


def test_120_second_normal_exit_lifetime_floor():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD")
    pos = mgr.open_position(
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00Z",
        invalidation_price=2340.0,
        target_price=2380.0
    )

    # Candle at t+30s (age 30s < 120s floor): Normal target exit should be BLOCKED
    c_30s = {"timestamp": "2026-08-25T10:00:30Z", "high": 2385.0, "low": 2348.0, "close": 2382.0}
    actions_30s = mgr.update_positions_and_manage_lifecycle(c_30s, {"movement_state": "EXPANSION"})
    assert len(mgr.active_positions) == 1
    assert actions_30s[0]["action"] == "HOLD"
    assert actions_30s[0]["reason"] == "AGE_BELOW_120S_FLOOR"

    # Candle at t+125s (age 125s >= 120s floor): Target exit ALLOWED
    c_125s = {"timestamp": "2026-08-25T10:02:05Z", "high": 2385.0, "low": 2348.0, "close": 2382.0}
    actions_125s = mgr.update_positions_and_manage_lifecycle(c_125s, {"movement_state": "EXPANSION"})
    assert len(mgr.active_positions) == 0
    assert len(mgr.history_positions) == 1
    assert actions_125s[0]["action"] == "EXIT"
    assert actions_125s[0]["reason"] == "TARGET_COMPLETION"


def test_session_state_transitions_and_entry_rejection():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD", session_cutoff_hour=21, session_cutoff_minute=45)

    # 10:00 UTC -> NORMAL_SESSION
    assert mgr.evaluate_session_state("2026-08-25T10:00:00Z") == "NORMAL_SESSION"

    # 21:20 UTC -> ENTRY_RESTRICTED
    assert mgr.evaluate_session_state("2026-08-25T21:20:00Z") == "ENTRY_RESTRICTED"
    rejected_pos = mgr.open_position("BUY", 2350.0, "2026-08-25T21:20:00Z")
    assert rejected_pos is None

    # 21:35 UTC -> POSITION_UNWIND
    assert mgr.evaluate_session_state("2026-08-25T21:35:00Z") == "POSITION_UNWIND"

    # 21:45 UTC -> SESSION_FLAT
    assert mgr.evaluate_session_state("2026-08-25T21:45:00Z") == "SESSION_FLAT"


def test_session_unwind_to_zero_overnight_positions():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD", session_cutoff_hour=21, session_cutoff_minute=45)
    pos = mgr.open_position("BUY", 2350.0, "2026-08-25T10:00:00Z")
    assert len(mgr.active_positions) == 1

    # Candle at session unwind cutoff (21:35 UTC)
    c_unwind = {"timestamp": "2026-08-25T21:35:00Z", "high": 2355.0, "low": 2348.0, "close": 2352.0}
    actions = mgr.update_positions_and_manage_lifecycle(c_unwind, {"movement_state": "EXPANSION"})

    assert len(mgr.active_positions) == 0
    assert actions[0]["action"] == "SESSION_UNWIND_EXIT"
    assert mgr.history_positions[-1].exit_reason == "SESSION_UNWIND"


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


def test_structural_invalidation_exit_and_reentry_registration():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD", default_risk_budget_usd=100.0)
    pos = mgr.open_position(
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00Z",
        invalidation_price=2340.0,
        target_price=2380.0
    )

    # Bar at t+180s (>120s floor) triggers structural invalidation with parent scale divergence
    candle_invalid = {
        "timestamp": "2026-08-25T10:03:00Z",
        "open": 2345.0,
        "high": 2346.0,
        "low": 2338.0,
        "close": 2339.0
    }
    m_state = {"movement_state": "DANGEROUS_PULLBACK", "parent_direction": "BEARISH", "macro_direction": "BEARISH"}

    actions = mgr.update_positions_and_manage_lifecycle(candle_invalid, m_state)
    assert actions[0]["action"] == "EXIT"
    assert actions[0]["reason"] == "STRUCTURAL_INVALIDATION"
    assert actions[1]["action"] == "AUTO_DIRECTION_TRANSITION"
    assert len(mgr.history_positions) == 1


def test_reentry_and_direction_transition_execution():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD", default_risk_budget_usd=100.0)
    pos = mgr.open_position(
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00Z",
        invalidation_price=2340.0,
        target_price=2380.0
    )

    # Trigger exit without macro alignment so candidate stays in pool for manual execution
    candle_invalid = {
        "timestamp": "2026-08-25T10:03:00Z",
        "open": 2345.0,
        "high": 2346.0,
        "low": 2338.0,
        "close": 2339.0
    }
    m_state = {"movement_state": "DANGEROUS_PULLBACK", "parent_direction": "BEARISH", "macro_direction": "NEUTRAL"}
    mgr.update_positions_and_manage_lifecycle(candle_invalid, m_state)

    # Execute Direction Transition (BUY -> SELL)
    new_sell = mgr.execute_direction_transition(
        candidate_idx=0,
        entry_price=2338.0,
        entry_time="2026-08-25T10:05:00Z",
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

    # Candle 1: Normal progression at t+10s (age < 120s floor -> HOLD)
    c1 = {"timestamp": "2026-08-25T10:00:10Z", "high": 2355.0, "low": 2348.0, "close": 2354.0}
    actions1 = mgr.update_positions_and_manage_lifecycle(c1, {"movement_state": "EXPANSION"})
    assert len(actions1) == 1
    assert actions1[0]["action"] == "HOLD"
    assert pos.current_mfe == 5.0
    assert pos.current_mae == 2.0

    # Ensure future candles cannot affect past excursion
    c2 = {"timestamp": "2026-08-25T10:00:20Z", "high": 2370.0, "low": 2352.0, "close": 2368.0}
    actions2 = mgr.update_positions_and_manage_lifecycle(c2, {"movement_state": "EXPANSION"})
    assert pos.current_mfe == 20.0
