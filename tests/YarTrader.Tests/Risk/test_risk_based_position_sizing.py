"""
YarTrader Risk-Based Position Sizing Tests
==========================================

Verifies that position sizing is calculated strictly against 0.5% account equity risk budget,
eliminates artificial universal 0.01 lot entry floors, respects broker minimums/steps,
and rejects sub-broker-minimum volumes instead of forcing 0.01.
"""

import pytest
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine, PositionSizingResult


def test_a_point_five_percent_risk_budget_calculation():
    engine = ProfessionalRiskEngine()

    # Account Equity = $10,000 -> 0.5% Risk Budget = $50.00
    res10k = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2490.0,  # $10 SL distance -> $1000 risk per lot (+ $7 commission) = $1007
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=0.5
    )
    assert res10k.is_valid is True
    assert res10k.risk_budget_usd == 50.0

    # Account Equity = $20,000 -> 0.5% Risk Budget = $100.00
    res20k = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2490.0,
        account_equity=20000.0,
        free_margin=20000.0,
        risk_pct=0.5
    )
    assert res20k.is_valid is True
    assert res20k.risk_budget_usd == 100.0


def test_b_stop_distance_volume_scaling():
    engine = ProfessionalRiskEngine()

    # Wider SL ($20 distance) -> smaller lot volume
    res_wide = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2480.0,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=0.5,
        volume_min=0.001
    )

    # Tighter SL ($5 distance) -> larger lot volume
    res_tight = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2495.0,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=0.5,
        volume_min=0.001
    )

    assert res_tight.volume_lots > res_wide.volume_lots


def test_c_volume_below_broker_minimum_rejects_without_forcing_0_01():
    engine = ProfessionalRiskEngine()

    # Tiny balance ($100) -> 0.5% Risk = $0.50
    # On $20 SL distance ($2007 risk per lot), calculated volume = 0.0002 lots
    # With broker minimum = 0.01 lots, system MUST REJECT, NOT force 0.01
    res = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2480.0,
        account_equity=100.0,
        free_margin=100.0,
        risk_pct=0.5,
        volume_min=0.01
    )

    assert res.is_valid is False
    assert "below broker minimum" in res.rejection_reason


def test_d_volume_step_normalization():
    engine = ProfessionalRiskEngine()

    res = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2490.0,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=0.5,
        volume_step=0.01
    )

    # Verify calculated lots rounded to volume_step 0.01
    assert round(res.volume_lots * 100) == int(res.volume_lots * 100)


def test_e_safety_gates_and_real_account_rejection():
    from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
    from src.Infrastructure.exceptions import ValidationException

    with pytest.raises(ValidationException, match="Real Live Trading is hard-disabled"):
        MetaTraderSafetyGate.verify_operation("MT4", "REAL_LIVE", "12345", "Real-Server")
