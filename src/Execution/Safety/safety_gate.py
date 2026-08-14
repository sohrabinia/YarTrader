import os
import logging
from typing import Any, Dict, Optional
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("MetaTraderSafetyGate")

class MetaTraderSafetyGate:
    """
    Production-hardened, fail-closed SRE Safety Gate for MetaTrader terminals.
    Separates concerns between MT5 (Demo/Research) and MT4 (Live Simulation),
    and strictly blocks any live execution paths in production.
    """

    # Authoritative Accounts & Servers
    MT5_DEMO_ACCOUNT = "52961173"
    MT5_DEMO_SERVER = "Alpari-MT5-Demo"

    MT4_LIVE_ACCOUNT = "143056202"
    MT4_LIVE_SERVER = "Alpari-Pro.ECN"

    @classmethod
    def verify_operation(
        cls,
        terminal_type: str,  # "MT5" or "MT4"
        operation_type: str, # "DATA", "ANALYSIS", "RESEARCH", "BACKTEST", "DEMO", "LIVE_SIMULATION", "REAL_LIVE"
        account_id: Optional[str] = None,
        server_name: Optional[str] = None
    ) -> bool:
        """
        Validates operations against terminal boundaries, accounts, and safety gates.
        Throws ValidationException on any violation to fail closed.
        """
        terminal_type = str(terminal_type).upper()
        operation_type = str(operation_type).upper()

        logger.info(
            f"[SAFETY_GATE] Audit request: Terminal={terminal_type}, "
            f"Operation={operation_type}, Account={account_id}, Server={server_name}"
        )

        # 1. Real Live Trading is HARD-DISABLED repository-wide
        if operation_type == "REAL_LIVE":
            logger.error("[SAFETY_GATE] SECURITY ALERT: Real Live Trading execution attempted! Execution BLOCKED.")
            raise ValidationException(
                "SRE Security Gate Violation: Real Live Trading is hard-disabled repository-wide."
            )

        # 2. Global Safety Switch Validation
        # Explicit check for LIVE_TRADING_ENABLED configuration
        from src.Infrastructure.Configuration.config import ConfigurationManager
        try:
            config = ConfigurationManager.get_config()
            live_trading_enabled = getattr(config, "live_trading_enabled", False)
        except Exception:
            live_trading_enabled = False

        if live_trading_enabled:
            # Dual guard: Even if config flag is enabled, we fail-closed if anyone attempts real live execution
            logger.error("[SAFETY_GATE] SECURITY ALERT: live_trading_enabled flag is True but real execution is blocked.")
            raise ValidationException(
                "SRE Security Gate Violation: Live trading flag manipulation detected! Real execution is hard-disabled."
            )

        # 3. Terminal Assignment Separation & Account Isolation
        if terminal_type == "MT5":
            # MT5 is strictly for analysis, research, backtest, and demo data/trading
            allowed_ops = ["DATA", "ANALYSIS", "RESEARCH", "BACKTEST", "DEMO"]
            if operation_type not in allowed_ops:
                raise ValidationException(
                    f"SRE Safety Gate Violation: MT5 terminal assigned incorrect role '{operation_type}'."
                )

            # Account & Server Verification if provided
            if account_id is not None and str(account_id) != cls.MT5_DEMO_ACCOUNT:
                raise ValidationException(
                    f"SRE Safety Gate Violation: MT5 terminal connected to unauthorized account '{account_id}'. "
                    f"Authorized account is strictly '{cls.MT5_DEMO_ACCOUNT}'."
                )
            if server_name is not None and str(server_name) != cls.MT5_DEMO_SERVER:
                raise ValidationException(
                    f"SRE Safety Gate Violation: MT5 terminal connected to unauthorized server '{server_name}'. "
                    f"Authorized server is strictly '{cls.MT5_DEMO_SERVER}'."
                )

        elif terminal_type == "MT4":
            # MT4 is strictly for Live Trading Simulation / فرضی
            allowed_ops = ["LIVE_SIMULATION"]
            if operation_type not in allowed_ops:
                raise ValidationException(
                    f"SRE Safety Gate Violation: MT4 terminal assigned incorrect role '{operation_type}'."
                )

            # Account & Server Verification if provided
            if account_id is not None and str(account_id) != cls.MT4_LIVE_ACCOUNT:
                raise ValidationException(
                    f"SRE Safety Gate Violation: MT4 terminal connected to unauthorized account '{account_id}'. "
                    f"Authorized simulation account is strictly '{cls.MT4_LIVE_ACCOUNT}'."
                )
            if server_name is not None and str(server_name) != cls.MT4_LIVE_SERVER:
                raise ValidationException(
                    f"SRE Safety Gate Violation: MT4 terminal connected to unauthorized server '{server_name}'. "
                    f"Authorized simulation server is strictly '{cls.MT4_LIVE_SERVER}'."
                )

        else:
            raise ValidationException(
                f"SRE Safety Gate Violation: Unknown or unsupported MetaTrader terminal type '{terminal_type}'."
            )

        logger.info(f"[SAFETY_GATE] Audit PASSED: Terminal={terminal_type}, Operation={operation_type}")
        return True
