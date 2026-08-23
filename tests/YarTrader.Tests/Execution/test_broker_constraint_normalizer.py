import pytest
from src.Execution.Services.broker_constraint_normalizer import BrokerConstraintNormalizer


def test_normalizer_eurusd_5_digits():
    sym_info = {
        "digits": 5,
        "point": 0.00001,
        "trade_stops_level": 20,
        "volume_min": 0.01,
        "volume_step": 0.01,
        "volume_max": 100.0,
    }

    norm_price, norm_sl, norm_tp, norm_vol, meta = BrokerConstraintNormalizer.normalize_trade_parameters(
        symbol="EURUSD",
        direction="BUY",
        raw_price=1.085234,
        raw_sl=1.08518,  # Too close (0.000054 < min_stop 0.00020)
        raw_tp=1.086501,
        raw_volume=0.013,
        symbol_info=sym_info
    )

    assert norm_price == 1.08523
    assert norm_vol == 0.01
    assert norm_sl <= 1.08503  # Adjusted for 20 pt (0.00020) min distance
    assert norm_tp == 1.08650


def test_normalizer_bitcoin_2_digits_and_stops():
    sym_info = {
        "digits": 2,
        "point": 0.01,
        "trade_stops_level": 500,  # $5.00
        "volume_min": 0.01,
        "volume_step": 0.01,
        "volume_max": 50.0,
    }

    norm_price, norm_sl, norm_tp, norm_vol, meta = BrokerConstraintNormalizer.normalize_trade_parameters(
        symbol="BITCOIN",
        direction="SELL",
        raw_price=65000.00,
        raw_sl=65002.50,  # $2 < $5 min stop
        raw_tp=64900.00,
        raw_volume=0.05,
        symbol_info=sym_info
    )

    assert norm_price == 65000.00
    assert norm_sl >= 65005.00  # Adjusted for $5.00 min stop
    assert norm_tp == 64900.00
