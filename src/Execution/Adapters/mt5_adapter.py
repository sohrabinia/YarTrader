import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.Execution.Interfaces.interfaces import IBrokerAdapter
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("RealMT5BrokerAdapter")


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
        if hasattr(acc, "_asdict"):
            return acc._asdict()
        return {
            "login": getattr(acc, "login", None),
            "trade_mode": getattr(acc, "trade_mode", None),
            "balance": getattr(acc, "balance", None),
            "equity": getattr(acc, "equity", None),
            "profit": getattr(acc, "profit", None),
            "server": getattr(acc, "server", None),
            "currency": getattr(acc, "currency", None),
            "leverage": getattr(acc, "leverage", None),
        }

    def get_terminal_info(self) -> Optional[Dict[str, Any]]:
        """Returns active MT5 terminal info."""
        if not self._mt5:
            return None
        term = self._mt5.terminal_info()
        if term is None:
            return None
        return term._asdict() if hasattr(term, "_asdict") else {
            "connected": getattr(term, "connected", False),
            "name": getattr(term, "name", ""),
            "path": getattr(term, "path", ""),
        }

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches symbol information from MT5."""
        if not self._mt5:
            return None
        sym = self._mt5.symbol_info(symbol)
        if sym is None:
            return None
        # Select symbol in Market Watch if not selected
        if not getattr(sym, "select", False):
            self._mt5.symbol_select(symbol, True)
        return sym._asdict() if hasattr(sym, "_asdict") else {
            "name": getattr(sym, "name", symbol),
            "volume_min": getattr(sym, "volume_min", 0.01),
            "volume_step": getattr(sym, "volume_step", 0.01),
            "volume_max": getattr(sym, "volume_max", 100.0),
            "trade_mode": getattr(sym, "trade_mode", 0),
            "digits": getattr(sym, "digits", 2),
            "point": getattr(sym, "point", 0.01),
        }

    def get_symbol_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches latest real tick for symbol."""
        if not self._mt5:
            return None
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return tick._asdict() if hasattr(tick, "_asdict") else {
            "time": getattr(tick, "time", int(datetime.now(timezone.utc).timestamp())),
            "bid": getattr(tick, "bid", 0.0),
            "ask": getattr(tick, "ask", 0.0),
            "last": getattr(tick, "last", 0.0),
            "volume": getattr(tick, "volume", 0),
        }

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
        Strictly enforces MetaTraderSafetyGate before submission.
        """
        # 1. Enforce SRE Safety Gate & Account Alignment
        self.verify_safety_and_account(operation_type="DEMO")

        mt5 = self._mt5
        # 2. Validate Symbol
        sym_info = mt5.symbol_info(request.Symbol)
        if sym_info is None:
            raise ValidationException(f"Symbol '{request.Symbol}' is not available in MT5 terminal.")

        if not getattr(sym_info, "visible", True):
            mt5.symbol_select(request.Symbol, True)

        tick = mt5.symbol_info_tick(request.Symbol)
        if tick is None or getattr(tick, "bid", 0) <= 0 or getattr(tick, "ask", 0) <= 0:
            raise ValidationException(f"Real tick for symbol '{request.Symbol}' is unavailable or invalid.")

        digits = int(getattr(sym_info, "digits", 2))
        point = float(getattr(sym_info, "point", 0.01))
        trade_stops_level = float(getattr(sym_info, "trade_stops_level", 0))
        trade_freeze_level = float(getattr(sym_info, "trade_freeze_level", 0))

        # Dynamic stop distance calculation (respecting trade_stops_level and trade_freeze_level)
        stop_level_pts = max(trade_stops_level, trade_freeze_level)
        min_stop_distance = max(stop_level_pts * point, 10.0 * point if point > 0 else 0.1)

        # 3. Map Order Action and Price
        order_type_str = request.OrderType.upper()
        if order_type_str in ["BUY", "LONG"]:
            mt5_action_type = mt5.ORDER_TYPE_BUY
            price = round(request.Price or getattr(tick, "ask"), digits)
        elif order_type_str in ["SELL", "SHORT"]:
            mt5_action_type = mt5.ORDER_TYPE_SELL
            price = round(request.Price or getattr(tick, "bid"), digits)
        elif order_type_str == "CLOSE":
            # Position closing request contract invariant enforcement
            pos_ticket = int(request.PositionTicket) if request.PositionTicket else 0
            if pos_ticket <= 0:
                raise ValidationException(f"Valid non-zero PositionTicket is required for CLOSE order type, got {pos_ticket}.")
            positions = mt5.positions_get(ticket=pos_ticket)
            if not positions or len(positions) == 0:
                raise ValidationException(f"No open MT5 position found for ticket {pos_ticket}")
            pos = positions[0]
            pos_type = getattr(pos, "type", 0)
            if pos_type == mt5.POSITION_TYPE_BUY:
                mt5_action_type = mt5.ORDER_TYPE_SELL
                price = round(getattr(tick, "bid"), digits)
            else:
                mt5_action_type = mt5.ORDER_TYPE_BUY
                price = round(getattr(tick, "ask"), digits)
        else:
            raise ValidationException(f"Unsupported OrderType: '{request.OrderType}'")

        # Validate minimum volume safe bounds
        vol_min = getattr(sym_info, "volume_min", 0.01) if hasattr(sym_info, "volume_min") else (sym_info.get("volume_min", 0.01) if isinstance(sym_info, dict) else 0.01)
        vol_step = getattr(sym_info, "volume_step", 0.01) if hasattr(sym_info, "volume_step") else (sym_info.get("volume_step", 0.01) if isinstance(sym_info, dict) else 0.01)
        vol_max = getattr(sym_info, "volume_max", 100.0) if hasattr(sym_info, "volume_max") else (sym_info.get("volume_max", 100.0) if isinstance(sym_info, dict) else 100.0)
        volume = max(vol_min, min(request.Volume, vol_max))
        # Align to step
        if vol_step > 0:
            volume = round(round(volume / vol_step) * vol_step, 4)

        # Sanitize comment and resolve filling mode
        sanitized_comment = self._sanitize_comment(request.Comment)
        filling_mode = self._resolve_filling_mode(mt5, request.Symbol, sym_info)

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

        if order_type_str == "CLOSE":
            trade_req["position"] = int(request.PositionTicket)
            # Strictly pop SL and TP from CLOSE request payload
            trade_req.pop("sl", None)
            trade_req.pop("tp", None)
        else:
            # Dynamic SL/TP Normalization & Distance Enforcement for OPEN orders only
            if request.StopLoss and request.StopLoss > 0:
                sl = round(request.StopLoss, digits)
                if mt5_action_type == mt5.ORDER_TYPE_BUY:
                    if price - sl < min_stop_distance:
                        sl = round(price - min_stop_distance, digits)
                elif mt5_action_type == mt5.ORDER_TYPE_SELL:
                    if sl - price < min_stop_distance:
                        sl = round(price + min_stop_distance, digits)
                trade_req["sl"] = float(sl)

            if request.TakeProfit and request.TakeProfit > 0:
                tp = round(request.TakeProfit, digits)
                if mt5_action_type == mt5.ORDER_TYPE_BUY:
                    if tp - price < min_stop_distance:
                        tp = round(price + min_stop_distance, digits)
                elif mt5_action_type == mt5.ORDER_TYPE_SELL:
                    if price - tp < min_stop_distance:
                        tp = round(price - min_stop_distance, digits)
                trade_req["tp"] = float(tp)

        # Build candidate filling modes (preferred resolved mode first, then remaining)
        fok_code = getattr(mt5, "ORDER_FILLING_FOK", 0)
        ioc_code = getattr(mt5, "ORDER_FILLING_IOC", 1)
        return_code = getattr(mt5, "ORDER_FILLING_RETURN", 2)
        candidates = [filling_mode]
        for mode_opt in [fok_code, ioc_code, return_code]:
            if mode_opt not in candidates:
                candidates.append(mode_opt)

        pos_id = trade_req.get("position", None)
        sl_present = "sl" in trade_req
        tp_present = "tp" in trade_req
        if order_type_str == "CLOSE":
            pos_type_str = "BUY" if mt5_action_type == mt5.ORDER_TYPE_SELL else "SELL"
            close_type_str = "SELL" if mt5_action_type == mt5.ORDER_TYPE_SELL else "BUY"
            price_src_str = "BID" if mt5_action_type == mt5.ORDER_TYPE_SELL else "ASK"
            logger.info(
                f"[MT5 CLOSE FORENSIC] position_ticket={pos_id} position_type={pos_type_str} "
                f"close_type={close_type_str} close_price_source={price_src_str} "
                f"close_price={price} volume={volume} position={pos_id} "
                f"sl_present={sl_present} tp_present={tp_present} filling_mode={filling_mode}"
            )
            # Mandatory Invariant Assertions before order_check/order_send
            assert pos_id is not None and int(pos_id) > 0, "CLOSE request MUST contain valid position_ticket > 0"
            assert not sl_present, "CLOSE trade_req MUST NOT contain 'sl'"
            assert not tp_present, "CLOSE trade_req MUST NOT contain 'tp'"
        else:
            logger.info(
                f"[MT5 OPEN FORENSIC] symbol={request.Symbol} order_type={order_type_str} "
                f"price={price} sl={trade_req.get('sl')} tp={trade_req.get('tp')} "
                f"volume={volume} filling_mode={filling_mode}"
            )

        # 4. Check Order with Fail-Closed Safety across filling candidates
        check_res = None
        check_retcode = -1
        check_comment = "order_check returned None"
        first_non_filling_error = None
        check_tag = "[MT5 CLOSE CHECK]" if order_type_str == "CLOSE" else "[MT5 OPEN CHECK]"

        for cand_filling in candidates:
            trade_req["type_filling"] = cand_filling
            res_cand = mt5.order_check(trade_req)
            last_err_after = mt5.last_error() if hasattr(mt5, "last_error") else "N/A"
            logger.info(f"{check_tag} filling_mode_candidate={cand_filling} order_check_result={res_cand} last_error_after_check={last_err_after}")

            cand_retcode = getattr(res_cand, "retcode", -1) if res_cand is not None else -1
            if res_cand is not None and cand_retcode in [0, 10009]:
                check_res = res_cand
                check_retcode = cand_retcode
                check_comment = getattr(res_cand, "comment", "OK")
                filling_mode = cand_filling
                logger.info(f"[RealMT5BrokerAdapter] order_check PASSED with candidate filling_mode={cand_filling}")
                break
            else:
                if res_cand is not None:
                    # Record non-filling error (e.g. 10016 Invalid Stops) as primary if encountered
                    if cand_retcode != 10030 and first_non_filling_error is None:
                        first_non_filling_error = (res_cand, cand_retcode, getattr(res_cand, "comment", f"retcode {cand_retcode}"))
                    if check_res is None or check_retcode == -1 or check_retcode == 10030:
                        check_res = res_cand
                        check_retcode = cand_retcode
                        check_comment = getattr(res_cand, "comment", f"retcode {cand_retcode}")

        # If any candidate failed with a specific parameter error (e.g., 10016), prioritize that error message over generic 10030
        if check_retcode != 10009 and check_retcode != 0 and first_non_filling_error is not None:
            check_res, check_retcode, check_comment = first_non_filling_error

        # Valid order_check success retcodes: 0, 10009 (TRADE_RETCODE_DONE).
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
                    check_res._asdict()
                    if check_res is not None and hasattr(check_res, "_asdict")
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
            err_code, err_msg = mt5.last_error()
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

        res_dict = res._asdict() if hasattr(res, "_asdict") else {}
        retcode = getattr(res, "retcode", -1)
        comment = getattr(res, "comment", "")
        order_ticket = str(getattr(res, "order", 0))
        deal_ticket = str(getattr(res, "deal", 0)) if getattr(res, "deal", 0) != 0 else None
        fill_price = float(getattr(res, "price", price))
        fill_volume = float(getattr(res, "volume", volume))

        done_code = getattr(mt5, "TRADE_RETCODE_DONE", 10009)
        placed_code = getattr(mt5, "TRADE_RETCODE_PLACED", 10008)
        status = "Placed" if retcode in [done_code, placed_code, 0, 10009, 10008] else "Failed"

        logger.info(
            f"[RealMT5BrokerAdapter] Real mt5.order_send response: "
            f"retcode={retcode}, order={order_ticket}, deal={deal_ticket}, status={status}, price={fill_price}, volume={fill_volume}"
        )

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

    def get_positions(self, symbol: Optional[str] = None, ticket: Optional[int] = None) -> List[Dict[str, Any]]:
        """Queries active MT5 positions using mt5.positions_get()."""
        if not self._mt5 or not self._initialized:
            return []
        kwargs = {}
        if symbol:
            kwargs["symbol"] = symbol
        if ticket:
            kwargs["ticket"] = int(ticket)

        positions = self._mt5.positions_get(**kwargs)
        if positions is None:
            return []

        res = []
        for pos in positions:
            pos_dict = pos._asdict() if hasattr(pos, "_asdict") else {
                "ticket": getattr(pos, "ticket", 0),
                "symbol": getattr(pos, "symbol", ""),
                "type": getattr(pos, "type", 0),
                "volume": getattr(pos, "volume", 0.0),
                "price_open": getattr(pos, "price_open", 0.0),
                "price_current": getattr(pos, "price_current", 0.0),
                "sl": getattr(pos, "sl", 0.0),
                "tp": getattr(pos, "tp", 0.0),
                "time": getattr(pos, "time", 0),
                "magic": getattr(pos, "magic", 0),
                "comment": getattr(pos, "comment", ""),
                "profit": getattr(pos, "profit", 0.0),
                "swap": getattr(pos, "swap", 0.0),
            }
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
            res.append(ord_item._asdict() if hasattr(ord_item, "_asdict") else dict(ord_item))
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
            res.append(d._asdict() if hasattr(d, "_asdict") else dict(d))
        return res
