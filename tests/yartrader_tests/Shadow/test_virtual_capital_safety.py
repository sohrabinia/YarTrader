import os
import pytest
from unittest.mock import patch, MagicMock
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine, ShadowTrade

@pytest.fixture(autouse=True)
def clean_env():
    """Backup and restore env vars after each test to prevent pollution."""
    old_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(old_env)

def test_shadow_mode_zero_broker_balance():
    """
    Test 1: Checks that virtual balance allows simulation trades to proceed
    even if the broker balance is $0 under SHADOW mode.
    """
    os.environ["YARTRADER_TRADING_MODE"] = "SHADOW"
    os.environ["VIRTUAL_CAPITAL_INITIAL_BALANCE"] = "1000.0"

    # Instantiate PredictiveShadowEngine (or get singleton instance and reset config)
    engine = PredictiveShadowEngine.get_instance()
    engine.virtual_capital_balance = engine.get_virtual_capital_initial_balance()

    # Mock get_broker_balance to return 0.0
    with patch.object(engine, 'get_broker_balance', return_value=0.0):
        # Place simulation trade
        trade = engine.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=1800.0,
            stop=1780.0,
            target=1840.0,
            confidence=85.0,
            reason="M5 compression breakout",
            custom_time_structure=64
        )
        assert isinstance(trade, ShadowTrade)
        assert trade.symbol == "XAUUSD"
        assert trade.status == "CREATED"
        assert engine.virtual_capital_balance == 1000.0

def test_live_mode_zero_balance_blocked():
    """
    Test 2: Checks that LIVE execution is blocked if Broker Balance is <= 0.
    """
    os.environ["YARTRADER_TRADING_MODE"] = "LIVE"

    engine = PredictiveShadowEngine.get_instance()

    with patch.object(engine, 'get_broker_balance', return_value=0.0):
        # Placing a live trade with $0 broker balance must raise ValueError
        with pytest.raises(ValueError, match="Real order BLOCKED: Insufficient Capital in LIVE mode"):
            engine.create_predictive_order(
                symbol="XAUUSD",
                direction="LONG",
                entry=1800.0,
                stop=1780.0,
                target=1840.0,
                confidence=85.0,
                reason="M5 compression breakout",
                custom_time_structure=64
            )

def test_shadow_mode_blocks_mt5_order_send():
    """
    Test 3: Confirms that SHADOW mode does not call any live order send or broker mutations.
    """
    os.environ["YARTRADER_TRADING_MODE"] = "SHADOW"

    engine = PredictiveShadowEngine.get_instance()

    # Mock mt5 order_send to verify it is never called
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}):
        trade = engine.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=1800.0,
            stop=1780.0,
            target=1840.0,
            confidence=85.0,
            reason="M5 compression breakout",
            custom_time_structure=64
        )
        assert isinstance(trade, ShadowTrade)
        # Verify order_send was never called
        assert mock_mt5.order_send.call_count == 0

def test_unknown_mode_fails_closed():
    """
    Test 4: If trading context is unknown, fail closed.
    """
    os.environ["YARTRADER_TRADING_MODE"] = "UNKNOWN_MODE"

    engine = PredictiveShadowEngine.get_instance()

    with pytest.raises(ValueError, match="Execution BLOCKED: Unknown trading mode"):
        engine.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=1800.0,
            stop=1780.0,
            target=1840.0,
            confidence=85.0,
            reason="M5 compression breakout",
            custom_time_structure=64
        )
