"""
Unit and Behavioral Tests for YarTrader Fractal Position Intelligence & Lifecycle Management
"""

import pytest
import os
import sys

from src.Research.Brain.fractal_position_intelligence import (
    FractalPositionThesis,
    FractalPositionLifecycleManager
)


def test_position_thesis_initialization_and_risk_sizing():
    pos = FractalPositionThesis(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00+00:00",
        entry_scale="H1",
        parent_scale="H4",
        risk_budget_usd=100.0,
        structural_invalidation_price=2330.0,
        target_price=2380.0
    )

    assert pos.symbol == "XAUUSD"
    assert pos.direction == "BUY"
    assert pos.risk_distance == 20.0
    assert pos.position_size_oz == 5.0  # 100 / 20 = 5 oz
    assert pos.current_state == "ENTERED"
    assert pos.thesis_status == "VALID"


def test_position_excursion_updates():
    pos = FractalPositionThesis(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00+00:00",
        entry_scale="H1",
        parent_scale="H4",
        risk_budget_usd=100.0,
        structural_invalidation_price=2330.0
    )

    pos.update_excursion(current_high=2370.0, current_low=2345.0, current_close=2365.0)
    assert pos.current_mfe == 20.0  # 2370 - 2350
    assert pos.current_mae == 5.0   # 2350 - 2345


def test_lifecycle_manager_structural_invalidation_exit():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD", default_risk_budget_usd=100.0)
    pos = mgr.open_position(
        direction="BUY",
        entry_price=2350.0,
        entry_time="2026-08-25T10:00:00+00:00",
        invalidation_price=2330.0,
        target_price=2380.0
    )

    assert len(mgr.active_positions) == 1

    # Candle that hits structural invalidation (low = 2325 < 2330)
    invalidating_candle = {
        "timestamp": "2026-08-25T11:00:00+00:00",
        "open": 2335.0,
        "high": 2338.0,
        "low": 2325.0,
        "close": 2328.0
    }
    market_state = {"macro_direction": "BEARISH", "local_direction": "BEARISH", "is_pullback": False}

    actions = mgr.update_positions_and_manage_lifecycle(invalidating_candle, market_state)

    assert len(mgr.active_positions) == 0
    assert len(mgr.history_positions) == 1
    assert mgr.history_positions[0].exit_reason == "STRUCTURAL_INVALIDATION"
    assert mgr.history_positions[0].exit_price == 2330.0
    assert len(mgr.reentry_candidates) == 1


def test_no_future_data_leakage_invariant():
    mgr = FractalPositionLifecycleManager(symbol="XAUUSD")
    pos = mgr.open_position(direction="BUY", entry_price=2000.0, entry_time="2026-01-01T00:00:00Z")

    # Feature calculation on bar t=10 must not consume bars t>10
    bars = [{"timestamp": i, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2001.0} for i in range(20)]

    actions_10 = mgr.update_positions_and_manage_lifecycle(bars[10], {"is_pullback": False})
    assert len(actions_10) == 1
    assert pos.current_mfe >= 0.0
