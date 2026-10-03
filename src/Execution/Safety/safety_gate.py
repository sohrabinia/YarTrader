import logging
from typing import Optional
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("MetaTraderSafetyGate")

class MetaTraderSafetyGate:
    """Fail-closed platform/account isolation for YarTrader market data and DEMO execution."""
    MT5_DEMO_ACCOUNT="52961173"; MT5_DEMO_SERVER="Alpari-MT5-Demo"
    MT4_DEMO_ACCOUNT="252031952"; MT4_DEMO_SERVER="Alpari-Pro.ECN-Demo"
    MT4_LIVE_ACCOUNT="143056202"; MT4_LIVE_SERVER="Alpari-Pro.ECN"
    LIVE_EXECUTION_TERMINAL="MT4"; LIVE_EXECUTION_LOCKED=True

    @classmethod
    def verify_operation(cls, terminal_type: str, operation_type: str, account_id: Optional[str]=None, server_name: Optional[str]=None) -> bool:
        terminal_type=str(terminal_type).upper(); operation_type=str(operation_type).upper()
        if operation_type in {"REAL_LIVE","LIVE_MT4","LIVE_MT5"}:
            raise ValidationException("LIVE trading is hard-disabled.")
        from src.Infrastructure.Configuration.config import ConfigurationManager
        try:
            config=ConfigurationManager.get_config()
            if getattr(config,"live_trading_enabled",False):
                raise ValidationException("live_trading_enabled is true; execution is fail-closed.")
        except ValidationException: raise
        except Exception: pass

        if terminal_type=="MT5":
            allowed_ops={"DATA","ANALYSIS","RESEARCH","BACKTEST","DEMO"}
            expected_account=cls.MT5_DEMO_ACCOUNT if operation_type=="DEMO" else None
            expected_server=cls.MT5_DEMO_SERVER if operation_type=="DEMO" else None
        elif terminal_type=="MT4":
            allowed_ops={"DATA","ANALYSIS","RESEARCH","BACKTEST","SIGNAL","DEMO"}
            expected_account=cls.MT4_DEMO_ACCOUNT if operation_type=="DEMO" else (cls.MT4_LIVE_ACCOUNT if operation_type=="SIGNAL" else None)
            expected_server=cls.MT4_DEMO_SERVER if operation_type=="DEMO" else (cls.MT4_LIVE_SERVER if operation_type=="SIGNAL" else None)
        else:
            raise ValidationException(f"Unknown or unsupported MetaTrader terminal type '{terminal_type}'.")

        if operation_type not in allowed_ops:
            raise ValidationException(f"{terminal_type} terminal assigned unsupported role '{operation_type}'.")
        if expected_account is not None:
            if account_id is None or str(account_id)!=expected_account:
                raise ValidationException(f"Unauthorized {terminal_type} account for role '{operation_type}'.")
            if server_name is None or str(server_name)!=expected_server:
                raise ValidationException(f"Unauthorized {terminal_type} server for role '{operation_type}'.")

        if operation_type in {"DATA","ANALYSIS","RESEARCH","BACKTEST","SIGNAL"}:
            return True
        if operation_type=="DEMO":
            if account_id is None or server_name is None:
                raise ValidationException(f"Unauthorized {terminal_type} DEMO account/server.")
            if terminal_type=="MT5" and (str(account_id)!=cls.MT5_DEMO_ACCOUNT or str(server_name)!=cls.MT5_DEMO_SERVER):
                raise ValidationException("Unauthorized MT5 DEMO account/server.")
            if terminal_type=="MT4" and (str(account_id)!=cls.MT4_DEMO_ACCOUNT or str(server_name)!=cls.MT4_DEMO_SERVER):
                raise ValidationException("Unauthorized MT4 DEMO account/server.")
            logger.info("[SAFETY_GATE] Audit PASSED: Terminal=%s, Operation=DEMO", terminal_type)
            return True
        raise ValidationException(f"Execution role '{operation_type}' is not permitted on {terminal_type}.")
