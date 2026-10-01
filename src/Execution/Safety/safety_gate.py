import logging
from typing import Optional
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("MetaTraderSafetyGate")


class MetaTraderSafetyGate:
    """Fail-closed platform/account isolation for YarTrader market data and DEMO execution."""

    MT5_DEMO_ACCOUNT = "52961173"
    MT5_DEMO_SERVER = "Alpari-MT5-Demo"

    MT4_DEMO_ACCOUNT = "252031952"
    MT4_DEMO_SERVER = "Alpari-Pro.ECN-Demo"

    MT4_LIVE_ACCOUNT = "143056202"
    MT4_LIVE_SERVER = "Alpari-Pro.ECN"

    @classmethod
    def verify_operation(cls, terminal_type: str, operation_type: str,
                         account_id: Optional[str] = None,
                         server_name: Optional[str] = None) -> bool:
        terminal_type = str(terminal_type).upper()
        operation_type = str(operation_type).upper()
        if operation_type == "REAL_LIVE":
            raise ValidationException("SRE Safety Gate Violation: Real Live Trading is hard-disabled repository-wide.")
        from src.Infrastructure.Configuration.config import ConfigurationManager
        try:
            config = ConfigurationManager.get_config()
            if getattr(config, "live_trading_enabled", False):
                raise ValidationException("SRE Safety Gate Violation: live_trading_enabled is true; execution is fail-closed.")
        except ValidationException:
            raise
        except Exception:
            pass
        if operation_type == "MT5_DEMO":
            operation_type = "DEMO"
        elif operation_type in {"MT5_BACKTEST", "BACKTEST"}:
            operation_type = "BACKTEST"
        elif operation_type in {"MT4_LIVE", "LIVE_SIMULATION"}:
            operation_type = "LIVE_SIMULATION"

        if terminal_type == "MT5":
            allowed_ops = {"DATA", "ANALYSIS", "RESEARCH", "BACKTEST", "DEMO"}
            expected_account, expected_server = cls.MT5_DEMO_ACCOUNT, cls.MT5_DEMO_SERVER
        elif terminal_type == "MT4":
            allowed_ops = {"DATA", "ANALYSIS", "RESEARCH", "BACKTEST", "DEMO", "LIVE_SIMULATION"}
            expected_account, expected_server = cls.MT4_DEMO_ACCOUNT, cls.MT4_DEMO_SERVER
        else:
            raise ValidationException(f"Unknown or unsupported MetaTrader terminal type '{terminal_type}'.")
        if operation_type not in allowed_ops:
            raise ValidationException(f"{terminal_type} terminal assigned unsupported role '{operation_type}'.")
        if account_id is not None and str(account_id) != expected_account:
            raise ValidationException(f"Unauthorized {terminal_type} account '{account_id}'; expected '{expected_account}'.")
        if server_name is not None and str(server_name) != expected_server:
            raise ValidationException(f"Unauthorized {terminal_type} server '{server_name}'; expected '{expected_server}'.")
        logger.info("[SAFETY_GATE] Audit PASSED: Terminal=%s, Operation=%s", terminal_type, operation_type)
        return True
