import pytest

from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.Configuration.config import ConfigurationManager
from src.Infrastructure.exceptions import ValidationException


@pytest.mark.parametrize("operation", ["DATA", "ANALYSIS", "RESEARCH", "BACKTEST", "SIGNAL"])
def test_configuration_failure_blocks_non_live_operation(monkeypatch, operation):
    def fail_config():
        raise RuntimeError("configuration backend unavailable")

    monkeypatch.setattr(ConfigurationManager, "get_config", fail_config)

    with pytest.raises(ValidationException, match="configuration is unavailable"):
        MetaTraderSafetyGate.verify_operation("MT5", operation)


def test_missing_live_trading_flag_blocks(monkeypatch):
    monkeypatch.setattr(ConfigurationManager, "get_config", lambda: object())

    with pytest.raises(ValidationException, match="missing live_trading_enabled"):
        MetaTraderSafetyGate.verify_operation("MT5", "DATA")


def test_malformed_live_trading_flag_blocks(monkeypatch):
    class BadConfig:
        live_trading_enabled = "false"

    monkeypatch.setattr(ConfigurationManager, "get_config", lambda: BadConfig())

    with pytest.raises(ValidationException, match="must be boolean"):
        MetaTraderSafetyGate.verify_operation("MT5", "DATA")


def test_live_trading_enabled_true_blocks(monkeypatch):
    class LiveConfig:
        live_trading_enabled = True

    monkeypatch.setattr(ConfigurationManager, "get_config", lambda: LiveConfig())

    with pytest.raises(ValidationException, match="live_trading_enabled is true"):
        MetaTraderSafetyGate.verify_operation("MT5", "DATA")
