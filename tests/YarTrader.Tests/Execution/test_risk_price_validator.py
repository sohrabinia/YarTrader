import pytest
from src.Execution.Services.risk_price_validator import RiskPriceValidator


def test_risk_validator_buy_direction():
    sym_info = {"digits": 2, "point": 0.01, "trade_stops_level": 100}

    # Valid BUY (SL < Entry < TP)
    is_val, reason, p, sl, tp, vol, meta = RiskPriceValidator.validate_and_normalize(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2350.00,
        stop_loss=2340.00,
        take_profit=2370.00,
        volume=0.01,
        symbol_info=sym_info
    )

    assert is_val is True
    assert reason == "VALIDATED"
    assert sl < p < tp


def test_risk_validator_auto_adjusts_sl_above_entry_for_buy():
    sym_info = {"digits": 2, "point": 0.01, "trade_stops_level": 100}

    # BUY where SL was raw above Entry -> Normalizer auto-adjusts SL to below entry
    is_val, reason, p, sl, tp, vol, meta = RiskPriceValidator.validate_and_normalize(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2350.00,
        stop_loss=2360.00,  # Invalid raw SL above entry
        take_profit=2380.00,
        volume=0.01,
        symbol_info=sym_info
    )

    assert is_val is True
    assert sl < p  # Normalizer auto-adjusted SL to below entry
    assert sl <= p - 1.00  # Respects 100 pt ($1.00) min stop distance


def test_risk_validator_rejects_negative_entry():
    sym_info = {"digits": 2, "point": 0.01, "trade_stops_level": 100}

    is_val, reason, p, sl, tp, vol, meta = RiskPriceValidator.validate_and_normalize(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=-10.00,
        stop_loss=2340.00,
        take_profit=2370.00,
        volume=0.01,
        symbol_info=sym_info
    )

    assert is_val is False
    assert "Invalid entry price" in reason
