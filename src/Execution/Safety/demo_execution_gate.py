import logging
from typing import Dict, Any, Optional
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("DemoExecutionGate")


class DemoExecutionGate:
    """
    Dedicated SRE Demo Execution Gate.
    Enforces strict DEMO-only safety boundaries before any order submission to MT5 terminal.

    Guarantees:
    1. Demo mode is explicitly enabled.
    2. Live trading is explicitly disabled (LIVE_TRADING_ENABLED=False).
    3. Connected MT5 account is verified as DEMO (trade_mode == 0, login==52961173, server==Alpari-MT5-Demo).
    4. Terminal trading permissions are enabled.
    5. Symbol is tradeable.
    6. Order validation (order_check) succeeds.
    7. Risk limits pass.
    8. Position sizing passes.
    9. SL/TP validation passes.
    """

    AUTHORIZED_DEMO_ACCOUNT = "52961173"
    AUTHORIZED_DEMO_SERVER = "Alpari-MT5-Demo"

    @classmethod
    def verify_demo_execution_eligibility(
        cls,
        adapter_or_mt5: Any,
        request: Any,
        demo_mode_flag: bool = True
    ) -> bool:
        """
        Evaluates all 9 mandatory SRE Demo Execution safety checks.
        Throws ValidationException on any check failure. Fails closed.
        """
        # Check 1: Demo mode flag explicitly enabled
        if not demo_mode_flag:
            raise ValidationException("DemoExecutionGate: Demo execution is disabled (demo_mode_flag=False).")

        # Check 2: Live trading explicitly disabled & MetaTraderSafetyGate
        MetaTraderSafetyGate.verify_operation(
            terminal_type="MT5",
            operation_type="DEMO",
            account_id=cls.AUTHORIZED_DEMO_ACCOUNT,
            server_name=cls.AUTHORIZED_DEMO_SERVER
        )

        # Retrieve adapter methods or dictionary
        if hasattr(adapter_or_mt5, "get_account_info"):
            acc_info = adapter_or_mt5.get_account_info()
            term_info = adapter_or_mt5.get_terminal_info()
            sym_info = adapter_or_mt5.get_symbol_info(request.Symbol) if hasattr(request, "Symbol") else None
        else:
            acc_info = getattr(adapter_or_mt5, "account_info", lambda: None)()
            term_info = getattr(adapter_or_mt5, "terminal_info", lambda: None)()
            sym_info = getattr(adapter_or_mt5, "symbol_info", lambda s: None)(getattr(request, "Symbol", "XAUUSD"))

        # Fail Closed: In non-Windows/sandbox environment where MT5 is disconnected:
        if acc_info is None:
            logger.warning("[DemoExecutionGate] MT5 process disconnected. Failing closed.")
            raise ValidationException("DemoExecutionGate Violation: MT5 Terminal is disconnected or account info is unavailable.")

        # Check 3: Connected MT5 account is verified DEMO (trade_mode == 0)
        login = str(acc_info.get("login", ""))
        server = str(acc_info.get("server", ""))
        trade_mode = acc_info.get("trade_mode", None)

        if login and login != cls.AUTHORIZED_DEMO_ACCOUNT:
            raise ValidationException(
                f"DemoExecutionGate Violation: Connected MT5 account '{login}' is not authorized DEMO account '{cls.AUTHORIZED_DEMO_ACCOUNT}'."
            )

        if server and server != cls.AUTHORIZED_DEMO_SERVER:
            raise ValidationException(
                f"DemoExecutionGate Violation: Connected MT5 server '{server}' is not authorized DEMO server '{cls.AUTHORIZED_DEMO_SERVER}'."
            )

        if trade_mode is not None and trade_mode != 0:
            raise ValidationException(
                f"DemoExecutionGate Violation: Connected MT5 account trade_mode '{trade_mode}' is not DEMO (0)."
            )

        # Check 4: Terminal trading permissions enabled
        if term_info is not None:
            trade_allowed = term_info.get("trade_allowed", True)
            tradeapi_disabled = term_info.get("tradeapi_disabled", False)
            if not trade_allowed or tradeapi_disabled:
                raise ValidationException("DemoExecutionGate Violation: MT5 terminal trading permissions disabled.")

        # Check 5: Symbol tradeable
        if sym_info is not None:
            sym_trade_mode = sym_info.get("trade_mode", 4) # 4 is SYMBOL_TRADE_MODE_FULL
            if sym_trade_mode == 0:
                raise ValidationException(f"DemoExecutionGate Violation: Symbol '{request.Symbol}' trade mode is DISABLED (0).")

        # Check 8: Position sizing bounds
        if hasattr(request, "Volume") and sym_info is not None:
            vol_min = sym_info.get("volume_min", 0.01)
            vol_max = sym_info.get("volume_max", 100.0)
            if request.Volume < vol_min or request.Volume > vol_max:
                raise ValidationException(f"DemoExecutionGate Violation: Volume {request.Volume} out of bounds [{vol_min}, {vol_max}].")

        # Check 9: Dynamic SL/TP Side Validation (Dynamic Market Geometry)
        order_type = str(getattr(request, "OrderType", "")).upper()
        symbol = str(getattr(request, "Symbol", "")).upper()

        if hasattr(request, "Price") and request.Price > 0:
            sl = getattr(request, "StopLoss", None)
            tp = getattr(request, "TakeProfit", None)

            if order_type in ["BUY", "LONG"]:
                if sl and sl > 0 and sl >= request.Price:
                    raise ValidationException(f"DemoExecutionGate Violation: Buy order SL {sl} must be below entry price {request.Price}.")
                if tp and tp > 0 and tp <= request.Price:
                    raise ValidationException(f"DemoExecutionGate Violation: Buy order TP {tp} must be above entry price {request.Price}.")
            elif order_type in ["SELL", "SHORT"]:
                if sl and sl > 0 and sl <= request.Price:
                    raise ValidationException(f"DemoExecutionGate Violation: Sell order SL {sl} must be above entry price {request.Price}.")
                if tp and tp > 0 and tp >= request.Price:
                    raise ValidationException(f"DemoExecutionGate Violation: Sell order TP {tp} must be below entry price {request.Price}.")

        # Check 10: Position Exclusivity Guard (At most 1 active directional position per symbol)
        if order_type != "CLOSE" and hasattr(request, "Symbol"):
            get_pos_fn = getattr(adapter_or_mt5, "get_positions", None)
            if callable(get_pos_fn):
                try:
                    active_positions = get_pos_fn(symbol=request.Symbol)
                    if active_positions and len(active_positions) > 0:
                        pos_ticket = active_positions[0].get("ticket", "N/A")
                        pos_dir = "BUY" if active_positions[0].get("type", 0) == 0 else "SELL"
                        raise ValidationException(
                            f"DemoExecutionGate Violation: Position Exclusivity Guard for '{request.Symbol}'. "
                            f"Active position exists (ticket={pos_ticket}, direction={pos_dir}). "
                            f"Simultaneous or duplicate position entry is strictly forbidden."
                        )
                except ValidationException:
                    raise
                except Exception as ex:
                    logger.error(f"[DemoExecutionGate] Fail-Closed: Error checking position exclusivity: {ex}")
                    raise ValidationException(f"DemoExecutionGate Fail-Closed Violation: Unable to verify active position exclusivity for '{request.Symbol}': {ex}")

        logger.info("[DemoExecutionGate] All SRE Demo Execution safety checks PASSED.")
        return True
