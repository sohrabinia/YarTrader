import math
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from unittest.mock import MagicMock

from src.Execution.Interfaces.interfaces import IBrokerAdapter
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("RealMT5BrokerAdapter")

def _as_dict_safe(obj: Any) -> Optional[Dict[str, Any]]:
    """Safely extracts dictionary representation from object or mock."""
    if hasattr(obj, "_asdict") and callable(obj._asdict):
        try:
            res = obj._asdict()
            if isinstance(res, dict):
                return res
        except Exception:
            pass
    return None


class RealMT5BrokerAdapter(IBrokerAdapter):
    """
    Concrete Real MetaTrader 5 Broker Adapter.
    Uses native MetaTrader5 Python API calls (initialize, account_info, terminal_info,
    symbol_info, symbol_info_tick, order_check, order_send, positions_get,
    orders_get, history_orders_get, history_deals_get).

    Enforces MetaTraderSafetyGate before any trade operation.
    Real Live trading is strictly blocked repository-wide.
    Authorized DEMO account is strictly 52961173 on Alpari-MT5-Demo.
    """

    TARGET_ACCOUNT = "52961173"
    TARGET_SERVER = "Alpari-MT5-Demo"

    def __init__(self, auto_initialize: bool = True):
        logger.info("[MT5 ADAPTER VERSION] CLOSE FORENSIC REMEDIATION ACTIVE")
        self._mt5 = None
        self._initialized = False
        if auto_initialize:
            self._try_import_and_init()

    def _try_import_and_init(self) -> bool:
        """Attempts to import MetaTrader5 and initialize terminal connection."""
        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5
            if self._mt5.initialize() and self._mt5.account_info() is not None:
                self._initialized = True
                logger.info("[RealMT5BrokerAdapter] MetaTrader5 initialized successfully.")
                return True

            # Fallback to explicit terminal path if standard initialize has no IPC connection
            import os
            default_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
            if os.path.exists(default_path) and self._mt5.initialize(default_path):
                self._initialized = True
                logger.info(f"[RealMT5BrokerAdapter] MetaTrader5 initialized via path: {default_path}")
                return True

            err = self._mt5.last_error()
            logger.warning(f"[RealMT5BrokerAdapter] MT5 initialize failed: {err}")
            return False
        except ImportError:
            logger.warning("[RealMT5BrokerAdapter] MetaTrader5 Python package not available.")
            return False
        except Exception as e:
            logger.error(f"[RealMT5BrokerAdapter] Exception initializing MT5: {e}")
            return False

    def verify_safety_and_account(self, operation_type: str = "DEMO") -> bool:
        """
        Enforces MetaTraderSafetyGate and verifies active account and server match target DEMO credentials.
        """
        # 1. Call MetaTraderSafetyGate
        MetaTraderSafetyGate.verify_operation(
            terminal_type="MT5",
            operation_type=operation_type,
            account_id=self.TARGET_ACCOUNT,
            server_name=self.TARGET_SERVER
        )

        # 2. Check MT5 connection and active account if MT5 is available
        if not self._mt5 or not self._initialized:
            if not self._try_import_and_init():
                raise ValidationException("MT5 Terminal is not initialized or MetaTrader5 package is unavailable.")

        acc_info = self._mt5.account_info()
        if acc_info is None:
            err = self._mt5.last_error()
            raise ValidationException(f"Failed to fetch MT5 account info: {err}")

        actual_login = str(getattr(acc_info, "login", ""))
        actual_server = str(getattr(acc_info, "server", ""))
        trade_mode = getattr(acc_info, "trade_mode", None)

        if actual_login != self.TARGET_ACCOUNT:
            raise ValidationException(
                f"SRE Security Gate Violation: Active MT5 account '{actual_login}' does not match authorized DEMO account '{self.TARGET_ACCOUNT}'."
            )

        if actual_server != self.TARGET_SERVER:
            raise ValidationException(
                f"SRE Security Gate Violation: Active MT5 server '{actual_server}' does not match authorized DEMO server '{self.TARGET_SERVER}'."
            )

        # Explicit trade_mode check: 0 is ACCOUNT_TRADE_MODE_DEMO in MT5 C-API
        if trade_mode is not None and trade_mode != 0:
            raise ValidationException(
                f"SRE Security Gate Violation: Active MT5 account trade_mode '{trade_mode}' is not DEMO (0)."
            )

        return True

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Returns active MT5 account information."""
        if not self._mt5:
            return None
        acc = self._mt5.account_info()
        if acc is None:
            return None
        d = _as_dict_safe(acc)
        if d is not None:
            d["is_real"] = False if d.get("trade_mode") == 0 else True
            d["platform"] = "MT5"
            return d
        return {
            "login": getattr(acc, "login", None),
            "trade_mode": getattr(acc, "trade_mode", None),
            "is_real": False if getattr(acc, "trade_mode", None) == 0 else True,
            "balance": getattr(acc, "balance", None),
            "equity": getattr(acc, "equity", None),
            "profit": getattr(acc, "profit", None),
            "server": getattr(acc, "server", None),
            "currency": getattr(acc, "currency", None),
            "leverage": getattr(acc, "leverage", None),
            "free_margin": getattr(acc, "margin_free", None),
            "platform": "MT5",
        }

    def get_terminal_info(self) -> Optional[Dict[str, Any]]:
        """Returns active MT5 terminal info."""
        if not self._mt5:
            return None
        term = self._mt5.terminal_info()
        if term is None:
            return None
        d = _as_dict_safe(term)
        if d is not None:
            if "trade_allowed" not in d:
                d["trade_allowed"] = getattr(term, "trade_allowed", False)
            if "tradeapi_disabled" not in d:
                d["tradeapi_disabled"] = getattr(term, "tradeapi_disabled", True)
            return d
        return {
            "connected": getattr(term, "connected", False),
            "name": getattr(term, "name", ""),
            "path": getattr(term, "path", ""),
            "trade_allowed": getattr(term, "trade_allowed", False),
            "tradeapi_disabled": getattr(term, "tradeapi_disabled", True),
        }

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches symbol information from MT5. Fails closed with None if metadata is missing or invalid."""
        if not self._mt5:
            return None
        sym = self._mt5.symbol_info(symbol)
        if sym is None:
            return None
        # Select symbol in Market Watch if not selected
        if not getattr(sym, "select", False):
            self._mt5.symbol_select(symbol, True)

        d = _as_dict_safe(sym)
        if d is not None:
            info = d
        else:
            info = {
                "name": getattr(sym, "name", symbol),
                "volume_min": getattr(sym, "volume_min", None),
                "volume_step": getattr(sym, "volume_step", None),
                "volume_max": getattr(sym, "volume_max", None),
                "trade_mode": getattr(sym, "trade_mode", None),
                "digits": getattr(sym, "digits", None),
                "point": getattr(sym, "point", None),
            }

        # Reject unittest MagicMock objects in production adapter metadata
        for k in ["volume_min", "volume_step", "volume_max", "trade_mode", "digits", "point"]:
            if isinstance(info.get(k), MagicMock):
                logger.warning(f"[RealMT5BrokerAdapter] Symbol metadata '{k}' is MagicMock for '{symbol}'. Failing closed.")
                return None

        # Strict Validation: ZERO FINANCIAL FALLBACKS
        if info.get("volume_min") is None or info.get("volume_step") is None or info.get("volume_max") is None:
            logger.warning(f"[RealMT5BrokerAdapter] Symbol metadata for '{symbol}' missing required volume limits.")
            return None

        try:
            v_min_f = float(info["volume_min"])
            v_step_f = float(info["volume_step"])
            v_max_f = float(info["volume_max"])
            if not (math.isfinite(v_min_f) and v_min_f > 0 and math.isfinite(v_step_f) and v_step_f > 0 and math.isfinite(v_max_f) and v_max_f > 0):
                logger.warning(f"[RealMT5BrokerAdapter] Symbol metadata for '{symbol}' contains non-positive or non-finite volume limits.")
                return None
        except (ValueError, TypeError):
            return None

        return info

    def get_symbol_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches latest real tick for symbol. Fails closed with None if tick data is missing or invalid."""
        if not self._mt5:
            return None
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        d = _as_dict_safe(tick)
        tick_info = d if d is not None else {
            "time": getattr(tick, "time", None),
            "bid": getattr(tick, "bid", None),
            "ask": getattr(tick, "ask", None),
            "last": getattr(tick, "last", None),
            "volume": getattr(tick, "volume", None),
        }

        # Reject MagicMock tick objects
        for k in ["bid", "ask", "time"]:
            if isinstance(tick_info.get(k), MagicMock):
                logger.warning(f"[RealMT5BrokerAdapter] Tick field '{k}' is MagicMock for '{symbol}'. Failing closed.")
                return None

        # Strict Fail-Closed Validation for Real Ticks
        bid = tick_info.get("bid")
        ask = tick_info.get("ask")
        time_val = tick_info.get("time")

        if bid is None or ask is None or time_val is None:
            logger.warning(f"[RealMT5BrokerAdapter] Symbol tick for '{symbol}' is missing mandatory fields (bid/ask/time).")
            return None

        try:
            bid_f = float(bid)
            ask_f = float(ask)
            time_f = float(time_val)
            if not (math.isfinite(bid_f) and bid_f > 0 and math.isfinite(ask_f) and ask_f > 0 and math.isfinite(time_f) and time_f > 0):
                logger.warning(f"[RealMT5BrokerAdapter] Symbol tick for '{symbol}' contains non-positive or non-finite bid/ask/time.")
                return None
        except (ValueError, TypeError):
            return None

        return tick_info

    def _sanitize_comment(self, comment: Optional[str]) -> str:
        """Sanitizes comment to safe short ASCII string (max 15 chars, alphanumeric/underscore)."""
        if not comment:
            return "YarClose"
        ascii_str = "".join(c for c in str(comment) if ord(c) < 128)
        clean_str = "".join(c for c in ascii_str if c.isalnum() or c in "_-")
        sanitized = clean_str[:15].strip()
        return sanitized or "YarClose"

    def _resolve_filling_mode(self, mt5: Any, symbol: str, sym_info: Any) -> int:
        """Deterministically resolves supported MT5 filling mode for symbol."""
        fok_code = getattr(mt5, "ORDER_FILLING_FOK", 0)
        ioc_code = getattr(mt5, "ORDER_FILLING_IOC", 1)
        return_code = getattr(mt5, "ORDER_FILLING_RETURN", 2)

        f_mode = getattr(sym_info, "filling_mode", None) if sym_info else None
        if f_mode is not None and isinstance(f_mode, int):
            if f_mode & 1:  # SYMBOL_FILLING_FOK bit 0 set (1) -> ORDER_FILLING_FOK (0)
                return fok_code
            if f_mode & 2:  # SYMBOL_FILLING_IOC bit 1 set (2) -> ORDER_FILLING_IOC (1)
                return ioc_code
            if f_mode & 4:  # SYMBOL_FILLING_RETURN bit 2 set (4) -> ORDER_FILLING_RETURN (2)
                return return_code

        # Default fallback preference: FOK -> IOC
        return fok_code

    def send_order_to_broker(self, request: OrderRequest) -> OrderResponse:
        """
        Sends order to real MT5 terminal via mt5.order_send().
        Strictly enforces MetaTraderSafetyGate and exact risk volume preservation before submission.
        """
        # 1. Enforce SRE Safety Gate & Account Alignment
        self.verify_safety_and_account(operation_type="DEMO")

        mt5 = self._mt5
        # 2. Validate Symbol & Metadata
        sym_info = self.get_symbol_info(request.Symbol)
        if sym_info is None:
            raise ValidationException(f"Symbol '{request.Symbol}' metadata is missing or invalid in MT5 terminal.")

        mt5_sym_obj = mt5.symbol_info(request.Symbol)
        if mt5_sym_obj and not getattr(mt5_sym_obj, "visible", True):
            mt5.symbol_select(request.Symbol, True)

        tick = self.get_symbol_tick(request.Symbol)
        if tick is None or float(tick.get("bid", 0)) <= 0 or float(tick.get("ask", 0)) <= 0:
            raise ValidationException(f"Real tick for symbol '{request.Symbol}' is unavailable or invalid.")

        # 3. Map Order Action and Price
        order_type_str = request.OrderType.upper()
        if order_type_str in ["BUY", "LONG"]:
            mt5_action_type = mt5.ORDER_TYPE_BUY
            price = request.Price or float(tick["ask"])
        elif order_type_str in ["SELL", "SHORT"]:
            mt5_action_type = mt5.ORDER_TYPE_SELL
            price = request.Price or float(tick["bid"])
        elif order_type_str == "CLOSE":
            if not request.PositionTicket:
                raise ValidationException("PositionTicket is required for CLOSE order type.")
            positions = mt5.positions_get(ticket=int(request.PositionTicket))
            if not positions or len(positions) == 0:
                raise ValidationException(f"No open MT5 position found for ticket {request.PositionTicket}")
            pos = positions[0]
            pos_type = getattr(pos, "type", 0)
            if pos_type == mt5.POSITION_TYPE_BUY:
                mt5_action_type = mt5.ORDER_TYPE_SELL
                price = float(tick["bid"])
            else:
                mt5_action_type = mt5.ORDER_TYPE_BUY
                price = float(tick["ask"])
        else:
            raise ValidationException(f"Unsupported OrderType: '{request.OrderType}'")

        # 4. PRESERVE EXACT RISK VOLUME (NO SILENT MUTATION OR ROUNDING)
        vol_min = float(sym_info["volume_min"])
        vol_step = float(sym_info["volume_step"])
        vol_max = float(sym_info["volume_max"])

        req_vol = float(request.Volume) if (request.Volume is not None and not isinstance(request.Volume, bool)) else 0.0
        if not math.isfinite(req_vol) or req_vol <= 0:
            raise ValidationException(f"Requested order volume {request.Volume} is non-finite or <= 0.")

        if req_vol < vol_min or req_vol > vol_max:
            raise ValidationException(f"Requested volume {req_vol} violates broker volume limits [{vol_min}, {vol_max}].")

        step_rem = abs(req_vol - round(req_vol / vol_step) * vol_step)
        if step_rem > 1e-5:
            raise ValidationException(f"Requested volume {req_vol} does not align with broker volume step {vol_step}.")

        volume = req_vol

        # Sanitize comment and resolve filling mode
        sanitized_comment = self._sanitize_comment(request.Comment)
        filling_mode = self._resolve_filling_mode(mt5, request.Symbol, mt5_sym_obj)

        # Build MT5 order request structure
        trade_req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": request.Symbol,
            "volume": float(volume),
            "type": mt5_action_type,
            "price": float(price),
            "deviation": request.Deviation,
            "magic": request.Magic,
            "comment": sanitized_comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        if request.OrderType.upper() == "CLOSE" and request.PositionTicket:
            trade_req["position"] = int(request.PositionTicket)

        if request.StopLoss and request.StopLoss > 0:
            trade_req["sl"] = float(request.StopLoss)
        if request.TakeProfit and request.TakeProfit > 0:
            trade_req["tp"] = float(request.TakeProfit)

        # Build candidate filling modes
        fok_code = getattr(mt5, "ORDER_FILLING_FOK", 0)
        ioc_code = getattr(mt5, "ORDER_FILLING_IOC", 1)
        return_code = getattr(mt5, "ORDER_FILLING_RETURN", 2)
        candidates = [filling_mode]
        for mode_opt in [fok_code, ioc_code, return_code]:
            if mode_opt not in candidates:
                candidates.append(mode_opt)

        check_res = None
        check_retcode = -1
        check_comment = "order_check returned None"

        for cand_filling in candidates:
            trade_req["type_filling"] = cand_filling
            res_cand = mt5.order_check(trade_req)
            cand_retcode = getattr(res_cand, "retcode", -1) if res_cand is not None else -1
            if res_cand is not None and cand_retcode in [0, 10009]:
                check_res = res_cand
                check_retcode = cand_retcode
                check_comment = getattr(res_cand, "comment", "OK")
                filling_mode = cand_filling
                break
            else:
                if res_cand is not None:
                    check_res = res_cand
                    check_retcode = cand_retcode
                    check_comment = getattr(res_cand, "comment", f"retcode {cand_retcode}")

        if check_res is None or check_retcode not in [0, 10009]:
            logger.warning(
                f"[RealMT5BrokerAdapter] order_check failed "
                f"(retcode={check_retcode}): {check_comment}. Halting order_send."
            )

            return OrderResponse(
                OrderId="0",
                Symbol=request.Symbol,
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=check_retcode,
                Comment=f"order_check failed: {check_comment}",
                RawResponse=(
                    _as_dict_safe(check_res)
                    if check_res is not None
                    else {
                        "retcode": check_retcode,
                        "comment": check_comment,
                        "trade_req": trade_req,
                        "last_error": mt5.last_error() if hasattr(mt5, "last_error") else "N/A"
                    }
                )
            )

        # 5. Send Order
        res = mt5.order_send(trade_req)
        if res is None:
            err_code, err_msg = mt5.last_error() if hasattr(mt5, "last_error") else (-1, "order_send returned None")
            logger.error(f"[RealMT5BrokerAdapter] mt5.order_send failed: ({err_code}) {err_msg}")
            return OrderResponse(
                OrderId="0",
                Symbol=request.Symbol,
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=err_code,
                Comment=f"order_send returned None: {err_msg}",
                RawResponse={"error_code": err_code, "error_msg": err_msg}
            )

        res_dict = _as_dict_safe(res) or {}
        retcode = getattr(res, "retcode", -1) if not isinstance(getattr(res, "retcode", -1), MagicMock) else -1
        comment = getattr(res, "comment", "") if not isinstance(getattr(res, "comment", ""), MagicMock) else ""
        order_ticket = str(getattr(res, "order", 0)) if not isinstance(getattr(res, "order", 0), MagicMock) else "0"
        deal_ticket = str(getattr(res, "deal", 0)) if (hasattr(res, "deal") and getattr(res, "deal", 0) != 0 and not isinstance(getattr(res, "deal", 0), MagicMock)) else None

        # Authoritative broker response price & volume validation (NO SUBSTITUTION / NO FABRICATION)
        res_price = getattr(res, "price", None)
        res_volume = getattr(res, "volume", None)

        if res_price is None or isinstance(res_price, bool) or isinstance(res_price, MagicMock):
            fill_price = 0.0
        else:
            try:
                fill_price = float(res_price)
            except (ValueError, TypeError):
                fill_price = 0.0

        if res_volume is None or isinstance(res_volume, bool) or isinstance(res_volume, MagicMock):
            fill_volume = 0.0
        else:
            try:
                fill_volume = float(res_volume)
            except (ValueError, TypeError):
                fill_volume = 0.0

        done_code = getattr(mt5, "TRADE_RETCODE_DONE", 10009)
        placed_code = getattr(mt5, "TRADE_RETCODE_PLACED", 10008)

        # Successful order fill strictly requires retcode in done/placed AND positive fill price/volume from broker
        is_retcode_ok = (retcode in [done_code, placed_code, 0, 10009, 10008])
        is_fill_valid = (math.isfinite(fill_price) and fill_price > 0 and math.isfinite(fill_volume) and fill_volume > 0)

        if is_retcode_ok and is_fill_valid:
            status = "Placed"
        else:
            status = "Failed"
            if not is_fill_valid and is_retcode_ok:
                comment = f"Order send failed: Broker response missing valid fill price (${fill_price}) or volume ({fill_volume})."

        return OrderResponse(
            OrderId=order_ticket,
            Symbol=request.Symbol,
            Status=status,
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=retcode,
            Comment=comment,
            DealTicket=deal_ticket,
            Price=fill_price,
            Volume=fill_volume,
            RawResponse=res_dict
        )

    def get_positions(self, symbol: Optional[str] = None, ticket: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """Queries active MT5 positions using mt5.positions_get(). Returns None when query fails (UNKNOWN state)."""
        if not self._mt5 or not self._initialized:
            return None
        kwargs = {}
        if symbol:
            kwargs["symbol"] = symbol
        if ticket:
            kwargs["ticket"] = int(ticket)

        try:
            positions = self._mt5.positions_get(**kwargs)
        except Exception as e:
            logger.error(f"[RealMT5BrokerAdapter] positions_get exception: {e}")
            return None

        if positions is None:
            return None

        res = []
        for pos in positions:
            pos_dict = _as_dict_safe(pos)
            if pos_dict is None:
                ticket_val = getattr(pos, "ticket", None)
                symbol_val = getattr(pos, "symbol", None)
                type_val = getattr(pos, "type", None)
                vol_val = getattr(pos, "volume", None)
                open_p = getattr(pos, "price_open", None)
                curr_p = getattr(pos, "price_current", None)
                time_val = getattr(pos, "time", None)

                if any(v is None or isinstance(v, MagicMock) for v in [ticket_val, symbol_val, type_val, vol_val, open_p, curr_p, time_val]):
                    logger.warning(f"[RealMT5BrokerAdapter] Position object is missing required fields or contains MagicMock. Failing closed.")
                    return None

                pos_dict = {
                    "ticket": ticket_val,
                    "symbol": symbol_val,
                    "type": type_val,
                    "volume": vol_val,
                    "price_open": open_p,
                    "price_current": curr_p,
                    "sl": getattr(pos, "sl", 0.0),
                    "tp": getattr(pos, "tp", 0.0),
                    "time": time_val,
                    "magic": getattr(pos, "magic", 0),
                    "comment": getattr(pos, "comment", ""),
                    "profit": getattr(pos, "profit", 0.0),
                    "swap": getattr(pos, "swap", 0.0),
                }

            # Strict field validation for required position fields (NO TICKET=0, VOLUME=0.0 FABRICATION)
            try:
                t_id = int(pos_dict.get("ticket", 0))
                p_sym = str(pos_dict.get("symbol", "")).strip()
                p_vol = float(pos_dict.get("volume", 0.0))

                if t_id <= 0 or not p_sym or not math.isfinite(p_vol) or p_vol <= 0:
                    logger.warning(f"[RealMT5BrokerAdapter] Position field validation failed (ticket={t_id}, symbol={p_sym}, vol={p_vol}). Returning UNKNOWN position state.")
                    return None
            except (ValueError, TypeError) as e:
                logger.warning(f"[RealMT5BrokerAdapter] Position field type conversion exception: {e}. Returning UNKNOWN position state.")
                return None

            res.append(pos_dict)
        return res

    def get_history_orders(self, ticket: Optional[int] = None, group: Optional[str] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Queries MT5 historical orders using mt5.history_orders_get()."""
        if not self._mt5 or not self._initialized:
            return []

        if ticket:
            orders = self._mt5.history_orders_get(ticket=int(ticket))
        elif date_from and date_to:
            orders = self._mt5.history_orders_get(date_from, date_to, group=group or "")
        else:
            orders = self._mt5.history_orders_get(group=group or "")

        if orders is None:
            return []

        res = []
        for ord_item in orders:
            res.append(_as_dict_safe(ord_item) or dict(ord_item))
        return res

    def get_history_deals(self, ticket: Optional[int] = None, position: Optional[int] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Queries MT5 historical deals using mt5.history_deals_get()."""
        if not self._mt5 or not self._initialized:
            return []

        if ticket:
            deals = self._mt5.history_deals_get(ticket=int(ticket))
        elif position:
            deals = self._mt5.history_deals_get(position=int(position))
        elif date_from and date_to:
            deals = self._mt5.history_deals_get(date_from, date_to)
        else:
            deals = self._mt5.history_deals_get()

        if deals is None:
            return []

        res = []
        for d in deals:
            res.append(_as_dict_safe(d) or dict(d))
        return res
