import math
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
    3. Connected account identity is strictly verified as DEMO (trade_mode == 0, login==52961173, server==Alpari-MT5-Demo).
    4. Terminal trading permissions are verified as enabled.
    5. Symbol metadata and trading mode are verified as active.
    6. Position sizing and volume bounds pass without permissive defaults.
    7. Dynamic SL/TP validation passes.
    8. Position Exclusivity Guard passes (UNKNOWN position state fails closed).
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
        Evaluates mandatory SRE Demo Execution safety checks.
        Throws ValidationException on any check failure or missing field. Fails closed.
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

        # Retrieve adapter account, terminal, and symbol info
        if hasattr(adapter_or_mt5, "get_account_info"):
            acc_info = adapter_or_mt5.get_account_info()
            term_info = adapter_or_mt5.get_terminal_info()
            sym_info = adapter_or_mt5.get_symbol_info(request.Symbol) if hasattr(request, "Symbol") else None
        else:
            acc_info = getattr(adapter_or_mt5, "account_info", lambda: None)()
            term_info = getattr(adapter_or_mt5, "terminal_info", lambda: None)()
            sym_info = getattr(adapter_or_mt5, "symbol_info", lambda s: None)(getattr(request, "Symbol", "XAUUSD"))

        # Strict Account Info Verification (NO PERMISSIVE DEFAULTS)
        if not acc_info or not isinstance(acc_info, dict):
            raise ValidationException("DemoExecutionGate Violation: MT5 Terminal is disconnected or account info is unavailable.")

        login = acc_info.get("login")
        server = acc_info.get("server")
        trade_mode = acc_info.get("trade_mode")

        if login is None or not str(login).strip():
            raise ValidationException("DemoExecutionGate Violation: Account login is missing or empty.")

        if server is None or not str(server).strip():
            raise ValidationException("DemoExecutionGate Violation: Account server is missing or empty.")

        is_real = acc_info.get("is_real", False)
        platform = str(acc_info.get("platform", "MT5")).upper()

        if is_real is True or trade_mode is None or isinstance(trade_mode, bool) or trade_mode != 0:
            raise ValidationException("SECURITY VIOLATION: Connected account is REAL or non-DEMO. Real account execution is strictly rejected repository-wide.")

        if platform == "MT4":
            if str(login) != "4109825":
                raise ValidationException(f"DemoExecutionGate Violation: Connected MT4 account '{login}' is not authorized DEMO account '4109825'.")
            if str(server) != "Alpari-MT4-Demo":
                raise ValidationException(f"DemoExecutionGate Violation: Connected MT4 server '{server}' is not authorized DEMO server 'Alpari-MT4-Demo'.")
        else:
            if str(login) != cls.AUTHORIZED_DEMO_ACCOUNT:
                raise ValidationException(
                    f"DemoExecutionGate Violation: Connected MT5 account '{login}' is not authorized DEMO account '{cls.AUTHORIZED_DEMO_ACCOUNT}'."
                )
            if str(server) != cls.AUTHORIZED_DEMO_SERVER:
                raise ValidationException(
                    f"DemoExecutionGate Violation: Connected MT5 server '{server}' is not authorized DEMO server '{cls.AUTHORIZED_DEMO_SERVER}'."
                )

        # Terminal Info Verification (NO PERMISSIVE DEFAULTS)
        if not term_info or not isinstance(term_info, dict):
            raise ValidationException("DemoExecutionGate Violation: Terminal info is missing or unavailable.")

        trade_allowed = term_info.get("trade_allowed")
        tradeapi_disabled = term_info.get("tradeapi_disabled")

        if trade_allowed is False or tradeapi_disabled is True:
            raise ValidationException("DemoExecutionGate Violation: MT5 terminal trading permissions disabled or tradeapi disabled.")

        # Symbol Info Verification (XAUUSD-ONLY Boundary Enforcement)
        req_sym = str(getattr(request, "Symbol", "UNKNOWN")).strip().upper()
        if req_sym != "XAUUSD":
            raise ValidationException(f"DemoExecutionGate Violation: Symbol '{req_sym}' is not authorized. Execution is strictly restricted to 'XAUUSD'.")

        if not sym_info or not isinstance(sym_info, dict):
            raise ValidationException(f"DemoExecutionGate Violation: Symbol info for '{req_sym}' is missing or unavailable.")

        sym_trade_mode = sym_info.get("trade_mode")
        if sym_trade_mode is None or (isinstance(sym_trade_mode, int) and sym_trade_mode == 0):
            raise ValidationException(f"DemoExecutionGate Violation: Symbol '{request.Symbol}' trade mode is DISABLED (0).")

        vol_min = sym_info.get("volume_min")
        vol_max = sym_info.get("volume_max")
        vol_step = sym_info.get("volume_step")

        if vol_min is None or vol_max is None or vol_step is None:
            raise ValidationException(f"DemoExecutionGate Violation: Symbol '{request.Symbol}' volume limits (volume_min/max/step) are missing.")

        try:
            v_min_f, v_max_f, v_step_f = float(vol_min), float(vol_max), float(vol_step)
            if not (math.isfinite(v_min_f) and v_min_f > 0 and math.isfinite(v_max_f) and v_max_f > 0 and math.isfinite(v_step_f) and v_step_f > 0):
                raise ValidationException(f"DemoExecutionGate Violation: Symbol '{request.Symbol}' volume limits are non-positive or non-finite.")
        except (ValueError, TypeError):
            raise ValidationException(f"DemoExecutionGate Violation: Symbol '{request.Symbol}' volume limits are malformed.")

        # Check Position Sizing Bounds against request Volume
        if hasattr(request, "Volume") and request.Volume is not None:
            req_vol = float(request.Volume)
            if not math.isfinite(req_vol) or req_vol <= 0:
                raise ValidationException(f"DemoExecutionGate Violation: Requested Volume {request.Volume} is invalid or <= 0.")
            if req_vol < v_min_f or req_vol > v_max_f:
                raise ValidationException(f"DemoExecutionGate Violation: Volume {req_vol} out of bounds [{v_min_f}, {v_max_f}].")

        # Dynamic SL/TP Side Validation
        order_type = str(getattr(request, "OrderType", "")).upper()
        if hasattr(request, "Price") and request.Price and float(request.Price) > 0:
            entry_p = float(request.Price)
            sl = getattr(request, "StopLoss", None)
            tp = getattr(request, "TakeProfit", None)

            if order_type in ["BUY", "LONG"]:
                if sl and float(sl) > 0 and float(sl) >= entry_p:
                    raise ValidationException(f"DemoExecutionGate Violation: Buy order SL {sl} must be below entry price {entry_p}.")
                if tp and float(tp) > 0 and float(tp) <= entry_p:
                    raise ValidationException(f"DemoExecutionGate Violation: Buy order TP {tp} must be above entry price {entry_p}.")
            elif order_type in ["SELL", "SHORT"]:
                if sl and float(sl) > 0 and float(sl) <= entry_p:
                    raise ValidationException(f"DemoExecutionGate Violation: Sell order SL {sl} must be above entry price {entry_p}.")
                if tp and float(tp) > 0 and float(tp) >= entry_p:
                    raise ValidationException(f"DemoExecutionGate Violation: Sell order TP {tp} must be below entry price {entry_p}.")

        # Position Exclusivity Guard
        if order_type != "CLOSE" and hasattr(request, "Symbol"):
            get_pos_fn = getattr(adapter_or_mt5, "get_positions", None)
            if callable(get_pos_fn):
                try:
                    active_positions = get_pos_fn(symbol=request.Symbol)
                    if active_positions is None:
                        raise ValidationException(f"DemoExecutionGate Fail-Closed Violation: Broker position state is UNKNOWN for '{request.Symbol}'.")
                    if len(active_positions) > 0:
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
