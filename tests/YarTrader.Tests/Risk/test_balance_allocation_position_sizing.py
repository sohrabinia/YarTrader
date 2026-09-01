"""
YarTrader 0.5% Account Balance Allocation & Discovered Market Intelligence Sizing Tests
========================================================================================

Verifies that capital allocation equals 0.5% of current account balance per trade
(Allocation USD = Balance * 0.005), calculated using instrument price specifications,
and rejects sub-broker-minimum volumes without forcing artificial 0.01 lot defaults.
"""

import pytest
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine, PositionSizingResult


def test_a_point_five_percent_account_balance_capital_allocation():
    engine = ProfessionalRiskEngine()

    # Balance $10,000 -> 0.5% Risk Budget = $50.00
    # SL distance = $10 -> $1000 risk per lot (+ $7 commission = $1007)
    # Volume = 50 / 1007 = 0.0496 -> rounded to 0.05 lots
    res10k = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2490.0,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=0.5,
        leverage=100.0,
        contract_size=100.0,
        volume_min=0.01,
        volume_step=0.01
    )
    assert res10k.is_valid is True
    assert res10k.risk_budget_usd == 50.0
    assert res10k.volume_lots == 0.05

    # Balance $20,000 -> 0.5% Risk Budget = $100.00 -> 100 / 1007 = 0.099 -> 0.10 lots
    res20k = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2490.0,
        account_equity=20000.0,
        free_margin=20000.0,
        risk_pct=0.5,
        leverage=100.0,
        contract_size=100.0,
        volume_min=0.01,
        volume_step=0.01
    )
    assert res20k.is_valid is True
    assert res20k.risk_budget_usd == 100.0
    assert res20k.volume_lots == 0.10


def test_b_instrument_aware_volume_calculation():
    engine = ProfessionalRiskEngine()

    # Forex EURUSD @ 1.0850 ($100,000 contract size)
    # Balance $10,000 -> 0.5% Risk Budget = $50.00
    # SL distance = 50 pips (0.0050) -> $500 risk per lot (+ $7 comm) = $507
    # Volume = 50 / 507 = 0.0986 -> 0.10 lots
    res_eur = engine.evaluate_equity_risk_and_position_size(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        account_equity=10000.0,
        free_margin=10000.0,
        risk_pct=0.5,
        leverage=100.0,
        contract_size=100000.0,
        volume_min=0.01,
        volume_step=0.01
    )
    assert res_eur.is_valid is True
    assert res_eur.volume_lots == 0.10


def test_c_sub_broker_minimum_rejects_without_forcing_0_01():
    engine = ProfessionalRiskEngine()

    # Small balance ($100) -> 0.5% Margin Allocation = $0.50
    # On XAUUSD @ $2,500 with 1:100 leverage, volume = ($0.50 * 100) / $250,000 = 0.0002 lots
    # With broker minimum = 0.01 lots, system MUST REJECT, NOT force 0.01
    res = engine.evaluate_equity_risk_and_position_size(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2490.0,
        account_equity=100.0,
        free_margin=100.0,
        risk_pct=0.5,
        leverage=100.0,
        contract_size=100.0,
        volume_min=0.01,
        volume_step=0.01
    )
    assert res.is_valid is False
    assert "below broker minimum" in res.rejection_reason


def test_d_discovered_intelligence_path_and_signal_integration():
    from src.Decision.Intelligence.professional_signal_engine import ProfessionalSignalEngine
    engine = ProfessionalSignalEngine()
    sig = engine.generate_signal(
        symbol="XAUUSD",
        timeframe="M5",
        candles_by_tf={},
        spread_pip=1.0,
        platform_provenance="MT4"
    )
    assert sig.symbol == "XAUUSD"
    assert sig.direction in ["BUY", "SELL", "WAIT"]


def test_e_safety_gates_and_real_account_rejection():
    from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
    from src.Infrastructure.exceptions import ValidationException

    with pytest.raises(ValidationException, match="Real Live Trading is hard-disabled"):
        MetaTraderSafetyGate.verify_operation("MT4", "REAL_LIVE", "12345", "Real-Server")
