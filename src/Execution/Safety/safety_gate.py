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

    LIVE_EXECUTION_TERMINAL = "MT4"
    LIVE_EXECUTION_LOCKED = True

    @classmethod
    def verify_operation(cls, terminal_type: str, operation_type: str,
                         account_id: Optional[str] = None,
                         server_name: Optional[str] = None) -> bool:
        """Fail-closed role matrix.

        MT5 DEMO is the only executable DEMO path. MT4 is data/signal-only on
        the configured signal account. MT4 LIVE is the only reserved future live role and remains hard-disabled; MT5 LIVE is unsupported.
        """
        terminal_type = str(terminal_type).upper()
        operation_type = str(operation_type).upper()

        # Canonical future live role is MT4 only, but it remains hard-locked until
        # an active real MT4 account is explicitly configured and authorized.
        if operation_type in {"REAL_LIVE", "LIVE_MT4"}:
            raise ValidationException("MT4 Live Trading is hard-disabled until an active real MT4 account is configured. Real Live Trading is hard-disabled.")
        if operation_type == "LIVE_MT5":
            raise ValidationException("MT5 Live Trading is not a supported execution role.")

        from src.Infrastructure.Configuration.config import ConfigurationManager
        try:
            config = ConfigurationManager.get_config()
        except Exception as exc:
            logger.critical("[SAFETY_GATE] Configuration unavailable; blocking operation.")
            raise ValidationException("Runtime configuration is unavailable; operation blocked fail-closed.") from exc

        if not hasattr(config, "live_trading_enabled"):
            logger.critical("[SAFETY_GATE] live_trading_enabled is missing; blocking operation.")
            raise ValidationException("Runtime configuration is missing live_trading_enabled; operation blocked fail-closed.")

        live_enabled = getattr(config, "live_trading_enabled")
        if not isinstance(live_enabled, bool):
            logger.critical("[SAFETY_GATE] live_trading_enabled is malformed; blocking operation.")
            raise ValidationException("live_trading_enabled must be boolean; operation blocked fail-closed.")

        if live_enabled:
            raise ValidationException("live_trading_enabled is true; Real Live Trading is hard-disabled; execution is fail-closed.")

        if terminal_type == "MT5":
            allowed_ops = {"DATA", "ANALYSIS", "RESEARCH", "BACKTEST", "DEMO"}
            expected_account = cls.MT5_DEMO_ACCOUNT if operation_type == "DEMO" else None
            expected_server = cls.MT5_DEMO_SERVER if operation_type == "DEMO" else None
        elif terminal_type == "MT4":
            # MT4 is the Signal/data terminal. Its future LIVE role is reserved but hard-locked; it must never be used for DEMO orders.
            allowed_ops = {"DATA", "ANALYSIS", "RESEARCH", "BACKTEST", "SIGNAL"}
            expected_account = cls.MT4_LIVE_ACCOUNT if operation_type == "SIGNAL" else None
            expected_server = cls.MT4_LIVE_SERVER if operation_type == "SIGNAL" else None
        else:
            raise ValidationException(f"Unknown or unsupported MetaTrader terminal type '{terminal_type}'.")

        if operation_type not in allowed_ops:
            raise ValidationException(f"{terminal_type} terminal assigned unsupported role '{operation_type}'.")

        if expected_account is not None:
            if account_id is None or str(account_id) != expected_account:
                raise ValidationException(f"Unauthorized {terminal_type} account for role '{operation_type}'.")
            if server_name is None or str(server_name) != expected_server:
                raise ValidationException(f"Unauthorized {terminal_type} server for role '{operation_type}'.")

        # Any order-capable caller must explicitly be MT5 DEMO. MT4 SIGNAL is read-only.
        if operation_type in {"DATA", "ANALYSIS", "RESEARCH", "BACKTEST", "SIGNAL"}:
            return True
        if terminal_type == "MT5" and operation_type == "DEMO":
            if account_id is not None and str(account_id) != cls.MT5_DEMO_ACCOUNT:
                raise ValidationException("Unauthorized MT5 DEMO account.")
            if server_name is not None and str(server_name) != cls.MT5_DEMO_SERVER:
                raise ValidationException("Unauthorized MT5 DEMO server.")
            logger.info("[SAFETY_GATE] Audit PASSED: Terminal=MT5, Operation=DEMO")
            return True
        raise ValidationException(f"Execution role '{operation_type}' is not permitted on {terminal_type}.")
