import logging
import math
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
        self._using_session_bridge = False
        if auto_initialize:
            self._try_import_and_init()

    def _try_import_and_init(self) -> bool:
        """Initialize the authenticated Session-2 bridge first in production.

        A native MT5 initialize() call from the LocalSystem service can appear
        successful while binding to the wrong Windows session. Production must
        therefore never accept native Session-0 IPC as authoritative.
        """
        import os
        is_production = any(
            os.environ.get(name, "").strip().lower() == "production"
            for name in ("YARTRADER_ENV", "TRADEYAR_ENV", "RG_ENV")
        )

        if is_production:
            try:
                from src.Infrastructure.mt5_session_bridge import (
                    MT5SessionBridgeClient,
                    MT5BridgeProxy,
                )
                bridge = MT5SessionBridgeClient()
                if not bridge.configured:
                    raise RuntimeError("YARTRADER_MT5_BRIDGE_TOKEN is not configured")
                health = bridge.call("health")
                if not health or not health.get("connected"):
                    raise RuntimeError("MT5 Session-2 bridge health check failed")
                if (str(health.get("login", "")) != self.TARGET_ACCOUNT
                        or str(health.get("server", "")) != self.TARGET_SERVER
                        or health.get("trade_mode") not in (None, 0)):
                    raise RuntimeError("MT5 Session-2 bridge account safety check failed")
                self._mt5 = MT5BridgeProxy(bridge)
                self._initialized = True
                self._using_session_bridge = True
                logger.info("[RealMT5BrokerAdapter] Production connected through authenticated Session-2 bridge.")
                return True
            except Exception as bridge_err:
                self._mt5 = None
                self._initialized = False
                self._using_session_bridge = False
                logger.error("[RealMT5BrokerAdapter] Production bridge unavailable; refusing native Session-0 fallback: %s", bridge_err)
                return False

        try:
            import MetaTrader5 as mt5
            self._using_session_bridge = False
            self._mt5 = mt5
            if self._mt5.initialize() and self._mt5.account_info() is not None:
                self._initialized = True
                logger.info("[RealMT5BrokerAdapter] MetaTrader5 initialized successfully.")
                return True

            import os
            default_path = r"C:\\Program Files\\MetaTrader 5\\terminal64.exe"
            if os.path.exists(default_path) and self._mt5.initialize(default_path):
                self._initialized = True
                logger.info("[RealMT5BrokerAdapter] MetaTrader5 initialized via path: %s", default_path)
                return True

            native_err = self._mt5.last_error()
            logger.warning("[RealMT5BrokerAdapter] MT5 initialize failed: %s", native_err)
            self._initialized = False
            return False
        except ImportError:
            logger.warning("[RealMT5BrokerAdapter] MetaTrader5 Python package not available.")
            return False
        except Exception as exc:
            logger.error("[RealMT5BrokerAdapter] Exception initializing MT5: %s", exc)
            self._mt5 = None
            self._initialized = False
            return False

    def _reconnect_and_read_account(self) -> Any:
        """Reset stale MT5 state and attempt one fresh connection."""
        self._mt5 = None
        self._initialized = False
        if not self._try_import_and_init():
            return None
        try:
            account = self._mt5.account_info()
        except Exception as exc:
            logger.error("MT5 account probe failed after reconnect: %s", exc)
            self._mt5 = None
            self._initialized = False
            return None
        if account is None:
            self._mt5 = None
            self._initialized = False
        return account

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

        # The Session-2 bridge can disappear while the service process stays alive.
        # A proxy that was initialized once must not remain marked healthy forever:
        # invalidate it and reconnect once on every failed account-health probe.
        try:
            acc_info = self._mt5.account_info()
        except Exception as exc:
            if not self._using_session_bridge:
                raise ValidationException(f"Failed to fetch MT5 account info: {exc}") from exc
            logger.warning("[RealMT5BrokerAdapter] MT5 bridge account probe raised; reconnecting once: %s", exc)
            acc_info = self._reconnect_and_read_account()
            if acc_info is None:
                raise ValidationException("MT5 bridge account probe failed after reconnect attempt; DEMO execution is paused.") from exc

        if acc_info is None:
            try:
                err = self._mt5.last_error()
            except Exception as exc:
                err = str(exc)
            if self._using_session_bridge:
                logger.warning("[RealMT5BrokerAdapter] MT5 bridge returned no account (%s); reconnecting once.", err)
                acc_info = self._reconnect_and_read_account()
                if acc_info is None:
                    raise ValidationException(f"Failed to fetch MT5 account info after bridge reconnect attempt: {err}")
            else:
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
            res = acc._asdict()
            if "margin_free" in res and res["margin_free"] is not None:
                res["free_margin"] = res["margin_free"]
            return res
        margin_free = getattr(acc, "margin_free", None)
        if hasattr(margin_free, "_mock_name"): # MagicMock check in unit test context
            margin_free = None
        raw_free_margin = getattr(acc, "free_margin", None)
        if hasattr(raw_free_margin, "_mock_name"):
            raw_free_margin = None
        free_margin = margin_free if margin_free is not None else raw_free_margin
        return {
            "login": getattr(acc, "login", None),
            "trade_mode": getattr(acc, "trade_mode", None),
            "balance": getattr(acc, "balance", None),
            "equity": getattr(acc, "equity", None),
            "profit": getattr(acc, "profit", None),
            "server": getattr(acc, "server", None),
            "currency": getattr(acc, "currency", None),
            "leverage": getattr(acc, "leverage", None),
            "margin_free": margin_free,
            "free_margin": free_margin,
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
        raw_digits = getattr(sym, "digits", None) if not isinstance(sym, dict) else sym.get("digits")
        if raw_digits is None or isinstance(raw_digits, bool) or not isinstance(raw_digits, int) or raw_digits < 0:
            digits = None
        else:
            digits = raw_digits
        return sym._asdict() if hasattr(sym, "_asdict") else {
            "name": getattr(sym, "name", symbol),
            "volume_min": getattr(sym, "volume_min", 0.0),
            "volume_step": getattr(sym, "volume_step", 0.0),
            "volume_max": getattr(sym, "volume_max", 100.0),
            "trade_mode": getattr(sym, "trade_mode", 0),
            "digits": digits,
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

    @staticmethod
    def _field_value(source: Any, name: str, default: Any = None) -> Any:
        if isinstance(source, dict):
            return source.get(name, default)
        return getattr(source, name, default)

    def _calculate_current_wallet_volume(
        self, symbol: str, order_type: str, entry_price: float, stop_loss: Any, sym_info: Any,
        risk_pct: Any = None,
    ) -> Dict[str, Any]:
        """Size every broker entry from a fresh wallet snapshot and broker PnL model.

        Caller-supplied lots are advisory only. If the account, protective stop,
        symbol contract, or broker PnL calculator is unavailable, reject the order.
        """
        import math
        from src.Risk.Services.professional_risk_engine import ProductionRiskPolicy

        mt5 = self._mt5
        account = mt5.account_info() if mt5 is not None else None
        if account is None:
            raise ValidationException("Risk sizing blocked: live MT5 account snapshot is unavailable.")

        def number(source: Any, key: str) -> float:
            value = self._field_value(source, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValidationException(f"Risk sizing blocked: current account/symbol field '{key}' is missing or invalid.")
            return float(value)

        balance = number(account, "balance")
        equity = number(account, "equity")
        free_margin = number(account, "margin_free") if self._field_value(account, "margin_free") is not None else number(account, "free_margin")
        configured_risk_pct = float(ProductionRiskPolicy.TARGET_RISK_PCT) if risk_pct is None else risk_pct
        if (isinstance(configured_risk_pct, bool) or not isinstance(configured_risk_pct, (int, float))
                or not math.isfinite(float(configured_risk_pct)) or not 0.0 < float(configured_risk_pct) <= float(ProductionRiskPolicy.TARGET_RISK_PCT)):
            raise ValidationException("Risk sizing blocked: requested strategy risk share must be positive and at or below the global 1% ceiling.")
        configured_risk_pct = float(configured_risk_pct)
        risk_basis = min(balance, equity)
        if risk_basis <= 0 or free_margin < 0:
            raise ValidationException("Risk sizing blocked: current balance, equity, or free margin is invalid.")
        sl = number({"stop_loss": stop_loss}, "stop_loss")
        entry = float(entry_price)
        if not math.isfinite(entry) or entry <= 0 or sl <= 0 or entry == sl:
            raise ValidationException("Risk sizing blocked: a valid entry price and protective stop-loss are mandatory.")

        order_type = str(order_type).upper()
        is_buy = order_type in ("BUY", "LONG", "BUY_LIMIT", "BUY_STOP")
        is_sell = order_type in ("SELL", "SHORT", "SELL_LIMIT", "SELL_STOP")
        if not (is_buy or is_sell):
            raise ValidationException(f"Risk sizing blocked: unsupported entry direction '{order_type}'.")
        if (is_buy and sl >= entry) or (is_sell and sl <= entry):
            raise ValidationException("Risk sizing blocked: stop-loss is on the wrong side of entry.")
        mt5_order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

        volume_min = number(sym_info, "volume_min")
        volume_max = number(sym_info, "volume_max")
        volume_step = number(sym_info, "volume_step")
        if volume_min <= 0 or volume_max < volume_min or volume_step <= 0:
            raise ValidationException("Risk sizing blocked: broker volume limits are invalid.")
        risk_budget = risk_basis * (configured_risk_pct / 100.0)
        min_profit = mt5.order_calc_profit(mt5_order_type, symbol, volume_min, entry, sl)
        if min_profit is None or isinstance(min_profit, bool) or not math.isfinite(float(min_profit)):
            raise ValidationException("Risk sizing blocked: broker cannot calculate minimum-lot stop-loss risk.")
        min_risk = abs(float(min_profit))
        if min_risk <= 0 or min_risk > risk_budget * 1.000001:
            raise ValidationException(
                f"Risk sizing blocked: broker minimum {volume_min:g} lot risks {min_risk:.4f}, "
                f"above current wallet budget {risk_budget:.4f} ({configured_risk_pct:.4f}%)."
            )

        risk_per_lot = min_risk / volume_min
        raw_volume = risk_budget / risk_per_lot
        volume = min(volume_max, math.floor((raw_volume + 1e-12) / volume_step) * volume_step)
        step_text = f"{volume_step:.8f}".rstrip("0").rstrip(".")
        volume_digits = len(step_text.split(".", 1)[1]) if "." in step_text else 0
        volume = round(volume, volume_digits)
        if volume < volume_min:
            raise ValidationException("Risk sizing blocked: risk-based lot is below broker minimum; no minimum-lot override is allowed.")
        selected_profit = mt5.order_calc_profit(mt5_order_type, symbol, volume, entry, sl)
        if selected_profit is None or isinstance(selected_profit, bool) or not math.isfinite(float(selected_profit)):
            raise ValidationException("Risk sizing blocked: broker cannot verify calculated position risk.")
        estimated_risk = abs(float(selected_profit))
        if estimated_risk > risk_budget * 1.000001:
            raise ValidationException("Risk sizing blocked: calculated lot exceeds the current wallet risk budget.")
        if hasattr(mt5, "order_calc_margin"):
            margin_required = mt5.order_calc_margin(mt5_order_type, symbol, volume, entry)
            if margin_required is not None and math.isfinite(float(margin_required)) and float(margin_required) > free_margin:
                raise ValidationException("Risk sizing blocked: calculated lot exceeds current free margin.")

        logger.info(
            "LIVE_WALLET_RISK_SIZING symbol=%s side=%s balance=%.2f equity=%.2f risk_basis=%.2f "
            "risk_budget=%.4f entry=%.8f sl=%.8f broker_min=%.8f selected_volume=%.8f estimated_risk=%.4f",
            symbol, order_type, balance, equity, risk_basis, risk_budget, entry, sl,
            volume_min, volume, estimated_risk,
        )
        return {"volume": volume, "balance": balance, "equity": equity,
                "risk_basis": risk_basis, "risk_budget": risk_budget,
                "estimated_risk": estimated_risk, "risk_pct": configured_risk_pct}

    @staticmethod
    def _classify_order_send_status(retcode: Any, mt5: Any) -> str:
        """Conservatively classify MT5 results; partial/ambiguous means reconcile, never retry."""
        done_code = getattr(mt5, "TRADE_RETCODE_DONE", 10009)
        placed_code = getattr(mt5, "TRADE_RETCODE_PLACED", 10008)
        partial_code = getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010)
        if retcode == partial_code:
            return "Partial"
        if retcode in [done_code, placed_code, 0, 10009, 10008]:
            return "Placed"
        if retcode is None or (isinstance(retcode, (int, float)) and retcode < 0):
            return "Uncertain"
        return "Failed"

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

        # 3. Map market, pending, and close actions. Pending orders are accepted
        # only with an explicit entry price and valid position relative to the quote.
        order_type_str = request.OrderType.upper()
        pending_types = {
            "BUY_LIMIT": "ORDER_TYPE_BUY_LIMIT", "SELL_LIMIT": "ORDER_TYPE_SELL_LIMIT",
            "BUY_STOP": "ORDER_TYPE_BUY_STOP", "SELL_STOP": "ORDER_TYPE_SELL_STOP",
        }
        is_pending = order_type_str in pending_types
        if order_type_str in ["BUY", "LONG"]:
            mt5_action_type = mt5.ORDER_TYPE_BUY
            price = request.Price or getattr(tick, "ask")
        elif order_type_str in ["SELL", "SHORT"]:
            mt5_action_type = mt5.ORDER_TYPE_SELL
            price = request.Price or getattr(tick, "bid")
        elif is_pending:
            mt5_action_type = getattr(mt5, pending_types[order_type_str], None)
            if mt5_action_type is None or request.Price is None:
                raise ValidationException("Pending order requires a supported MT5 order type and explicit entry price.")
            price = float(request.Price)
            bid, ask = float(getattr(tick, "bid")), float(getattr(tick, "ask"))
            valid_geometry = (
                (order_type_str == "BUY_LIMIT" and price < ask)
                or (order_type_str == "SELL_LIMIT" and price > bid)
                or (order_type_str == "BUY_STOP" and price > ask)
                or (order_type_str == "SELL_STOP" and price < bid)
            )
            if not valid_geometry:
                raise ValidationException(f"{order_type_str} entry price is on the wrong side of the current quote.")
            if request.Expiration is not None and int(request.Expiration) <= int(getattr(tick, "time", 0)):
                raise ValidationException("Pending order expiration must be later than the broker tick timestamp.")
        elif order_type_str == "CLOSE":
            # Position closing request
            if not request.PositionTicket:
                raise ValidationException("PositionTicket is required for CLOSE order type.")
            positions = mt5.positions_get(ticket=int(request.PositionTicket))
            if not positions or len(positions) == 0:
                raise ValidationException(f"No open MT5 position found for ticket {request.PositionTicket}")
            pos = positions[0]
            pos_type = getattr(pos, "type", 0)
            if pos_type == mt5.POSITION_TYPE_BUY:
                mt5_action_type = mt5.ORDER_TYPE_SELL
                price = getattr(tick, "bid")
            else:
                mt5_action_type = mt5.ORDER_TYPE_BUY
                price = getattr(tick, "ask")
        else:
            raise ValidationException(f"Unsupported OrderType: '{request.OrderType}'")

        # Validate symbol precision before doing sizing calculations.
        raw_digits = getattr(sym_info, "digits", None) if not isinstance(sym_info, dict) else sym_info.get("digits")
        if raw_digits is None or isinstance(raw_digits, bool) or not isinstance(raw_digits, int) or raw_digits < 0:
            raise ValidationException(f"Symbol '{request.Symbol}' authoritative digits precision is missing or invalid.")
        digits = raw_digits

        # Every broker entry is sized from the fresh account balance/equity and
        # the broker's own stop-loss PnL model. Never promote a requested lot to
        # broker minimum: if minimum risk exceeds budget, fail closed instead.
        if order_type_str == "CLOSE":
            volume = float(request.Volume)
            if not math.isfinite(volume) or volume <= 0:
                raise ValidationException("Close volume must be finite and positive.")
        else:
            sizing = self._calculate_current_wallet_volume(
                symbol=request.Symbol,
                order_type=order_type_str,
                entry_price=float(price),
                stop_loss=request.StopLoss,
                sym_info=sym_info,
                risk_pct=getattr(request, "RiskPct", None),
            )
            volume = float(sizing["volume"])
            logger.info(
                "ORDER_VOLUME_OVERRIDDEN symbol=%s requested_volume=%s risk_sized_volume=%s "
                "risk_budget=%s estimated_risk=%s",
                request.Symbol, request.Volume, volume, sizing["risk_budget"], sizing["estimated_risk"],
            )

        # Sanitize comment and resolve filling mode
        sanitized_comment = self._sanitize_comment(request.Comment)
        filling_mode = self._resolve_filling_mode(mt5, request.Symbol, sym_info)

        # Build MT5 order request structure with authoritative digits precision normalization
        price_norm = round(float(price), digits)
        trade_req = {
            "action": mt5.TRADE_ACTION_PENDING if is_pending else mt5.TRADE_ACTION_DEAL,
            "symbol": request.Symbol,
            "volume": float(volume),
            "type": mt5_action_type,
            "price": price_norm,
            "deviation": request.Deviation,
            "magic": request.Magic,
            "comment": sanitized_comment,
            "type_time": (getattr(mt5, "ORDER_TIME_SPECIFIED", getattr(mt5, "ORDER_TIME_GTC", 0))
                          if is_pending and request.Expiration is not None else mt5.ORDER_TIME_GTC),
            "type_filling": (getattr(mt5, "ORDER_FILLING_RETURN", filling_mode) if is_pending else filling_mode),
        }
        if is_pending and request.Expiration is not None:
            trade_req["expiration"] = int(request.Expiration)

        if request.OrderType.upper() == "CLOSE" and request.PositionTicket:
            trade_req["position"] = int(request.PositionTicket)
        else:
            if request.StopLoss is not None and not isinstance(request.StopLoss, bool) and float(request.StopLoss) > 0:
                trade_req["sl"] = round(float(request.StopLoss), digits)
            if request.TakeProfit is not None and not isinstance(request.TakeProfit, bool) and float(request.TakeProfit) > 0:
                trade_req["tp"] = round(float(request.TakeProfit), digits)

            # Validate broker stop level distance constraint if specified
            stops_level = getattr(sym_info, "trade_stops_level", 0) if not isinstance(sym_info, dict) else sym_info.get("trade_stops_level", 0)
            point = getattr(sym_info, "point", 0.01) if not isinstance(sym_info, dict) else sym_info.get("point", 0.01)
            if stops_level and isinstance(stops_level, int) and stops_level > 0 and point and isinstance(point, (int, float)) and point > 0:
                min_dist = stops_level * point
                if "sl" in trade_req and abs(price_norm - trade_req["sl"]) < min_dist - 1e-7:
                    raise ValidationException(
                        f"StopLoss distance ({abs(price_norm - trade_req['sl']):.{digits}f}) violates symbol '{request.Symbol}' trade_stops_level ({min_dist:.{digits}f})."
                    )
                if "tp" in trade_req and abs(trade_req["tp"] - price_norm) < min_dist - 1e-7:
                    raise ValidationException(
                        f"TakeProfit distance ({abs(trade_req['tp'] - price_norm):.{digits}f}) violates symbol '{request.Symbol}' trade_stops_level ({min_dist:.{digits}f})."
                    )

        # Build candidate filling modes (preferred resolved mode first, then remaining)
        fok_code = getattr(mt5, "ORDER_FILLING_FOK", 0)
        ioc_code = getattr(mt5, "ORDER_FILLING_IOC", 1)
        return_code = getattr(mt5, "ORDER_FILLING_RETURN", 2)
        # MT5 pending orders require RETURN filling; cycling through FOK/IOC
        # can make a valid pending request fail order_check on otherwise valid symbols.
        if is_pending:
            candidates = [return_code]
        else:
            candidates = [filling_mode]
            for mode_opt in [fok_code, ioc_code, return_code]:
                if mode_opt not in candidates:
                    candidates.append(mode_opt)

        pos_id = trade_req.get("position", None)
        import json
        last_err_before = mt5.last_error() if hasattr(mt5, "last_error") else "N/A"
        logger.info(f"[MT5 CLOSE FORENSIC] trade_req={json.dumps(trade_req, default=str)}")
        logger.info(f"[MT5 CLOSE FORENSIC] last_error_before_check={last_err_before}")

        # 4. Check Order with Fail-Closed Safety across filling candidates
        check_res = None
        check_retcode = -1
        check_comment = "order_check returned None"

        for cand_filling in candidates:
            trade_req["type_filling"] = cand_filling
            res_cand = mt5.order_check(trade_req)
            last_err_after = mt5.last_error() if hasattr(mt5, "last_error") else "N/A"
            logger.info(f"[MT5 CLOSE FORENSIC] filling_mode_candidate={cand_filling} order_check_result={res_cand} last_error_after_check={last_err_after}")

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
                    check_res = res_cand
                    check_retcode = cand_retcode
                    check_comment = getattr(res_cand, "comment", f"retcode {cand_retcode}")

        # Valid order_check success retcodes: 0, 10009 (TRADE_RETCODE_DONE).
        if check_res is None or check_retcode not in [0, 10009]:
            logger.warning(
                f"[RealMT5BrokerAdapter] order_check failed "
                f"(retcode={check_retcode}): {check_comment}. Halting order_send."
            )

            raw_check_response: Dict[str, Any] = {}
            if check_res is not None and hasattr(check_res, "_asdict"):
                try:
                    check_payload = check_res._asdict()
                    if isinstance(check_payload, dict):
                        raw_check_response.update(check_payload)
                except Exception:
                    pass
            # These fields are authoritative for the adapter's fail-closed decision.
            raw_check_response.update({
                "retcode": check_retcode,
                "comment": check_comment,
                "trade_req": dict(trade_req),
                "last_error": mt5.last_error() if hasattr(mt5, "last_error") else "N/A",
            })
            return OrderResponse(
                OrderId="0",
                Symbol=request.Symbol,
                Status="Failed",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=check_retcode,
                Comment=f"order_check failed: {check_comment}",
                RawResponse=raw_check_response,
            )

        # 5. Send Order
        res = mt5.order_send(trade_req)
        if res is None:
            err_code, err_msg = mt5.last_error()
            logger.error(f"[RealMT5BrokerAdapter] mt5.order_send failed: ({err_code}) {err_msg}")
            return OrderResponse(
                OrderId="0",
                Symbol=request.Symbol,
                Status="Uncertain",
                SubmittedAt=datetime.now(timezone.utc),
                Retcode=err_code,
                Comment=f"order_send returned None; broker execution status is uncertain and requires reconciliation: {err_msg}",
                RawResponse={"error_code": err_code, "error_msg": err_msg}
            )

        res_dict = res._asdict() if hasattr(res, "_asdict") else {}
        retcode = getattr(res, "retcode", -1)
        comment = getattr(res, "comment", "")
        order_ticket = str(getattr(res, "order", 0))
        deal_ticket = str(getattr(res, "deal", 0)) if getattr(res, "deal", 0) != 0 else None
        fill_price = float(getattr(res, "price", price))
        fill_volume = float(getattr(res, "volume", volume))

        # Partial/ambiguous responses are locked by the caller until manually reconciled.
        status = self._classify_order_send_status(retcode, mt5)

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

    def update_position_stop_loss(self, ticket: int, stop_loss: float) -> OrderResponse:
        """Tighten a bot-owned DEMO position stop without ever widening risk."""
        self.verify_safety_and_account(operation_type="DEMO")
        mt5 = self._mt5
        if mt5 is None or not self._initialized:
            raise ValidationException("MT5 is not initialized; cannot update position SL.")
        ticket = int(ticket)
        if not isinstance(stop_loss, (int, float)) or isinstance(stop_loss, bool) or not math.isfinite(float(stop_loss)) or float(stop_loss) <= 0:
            raise ValidationException("New structural stop must be a finite positive price.")
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return OrderResponse(OrderId=str(ticket), Symbol="", Status="Failed",
                                 SubmittedAt=datetime.now(timezone.utc), Retcode=-1,
                                 Comment=f"Position {ticket} was not found; SL was not modified.")
        position = positions[0]
        def _value(obj: Any, name: str, default: Any = None) -> Any:
            return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)
        symbol = str(_value(position, "symbol", ""))
        old_sl = float(_value(position, "sl", 0.0) or 0.0)
        current_tp = float(_value(position, "tp", 0.0) or 0.0)
        position_type = int(_value(position, "type", -1))
        buy_type = int(getattr(mt5, "POSITION_TYPE_BUY", 0))
        sell_type = int(getattr(mt5, "POSITION_TYPE_SELL", 1))
        if ((position_type == buy_type and old_sl > 0 and float(stop_loss) <= old_sl)
                or (position_type == sell_type and old_sl > 0 and float(stop_loss) >= old_sl)
                or position_type not in (buy_type, sell_type)):
            return OrderResponse(OrderId=str(ticket), Symbol=symbol, Status="NoChange",
                                 SubmittedAt=datetime.now(timezone.utc), Retcode=0,
                                 Comment="Structural stop update would not tighten existing risk.")
        action = getattr(mt5, "TRADE_ACTION_SLTP", None)
        if action is None:
            return OrderResponse(OrderId=str(ticket), Symbol=symbol, Status="Failed",
                                 SubmittedAt=datetime.now(timezone.utc), Retcode=-1,
                                 Comment="MT5 does not expose TRADE_ACTION_SLTP.")
        request = {"action": action, "symbol": symbol, "position": ticket,
                   "sl": float(stop_loss), "tp": current_tp}
        checked = mt5.order_check(request)
        code = int(_value(checked, "retcode", -1) if checked is not None else -1)
        if checked is None or code not in (0, 10009):
            return OrderResponse(OrderId=str(ticket), Symbol=symbol, Status="Failed",
                                 SubmittedAt=datetime.now(timezone.utc), Retcode=code,
                                 Comment=f"Structural SL order_check failed: {_value(checked, 'comment', 'no response')}")
        result = mt5.order_send(request)
        result_code = int(_value(result, "retcode", -1) if result is not None else -1)
        success_codes = {0, 10009, int(getattr(mt5, "TRADE_RETCODE_DONE", 10009))}
        return OrderResponse(OrderId=str(ticket), Symbol=symbol,
                             Status="Modified" if result is not None and result_code in success_codes else "Failed",
                             SubmittedAt=datetime.now(timezone.utc), Retcode=result_code,
                             Comment=str(_value(result, "comment", "no response") if result is not None else "SL update returned None"))

    def update_position_take_profit(self, ticket: int, take_profit: float) -> OrderResponse:
        """Extend a bot-owned DEMO position's TP without weakening its existing SL."""
        self.verify_safety_and_account(operation_type="DEMO")
        mt5 = self._mt5
        if mt5 is None or not self._initialized:
            raise ValidationException("MT5 is not initialized; cannot update position TP.")
        ticket = int(ticket)
        if (not isinstance(take_profit, (int, float)) or isinstance(take_profit, bool)
                or not math.isfinite(float(take_profit)) or float(take_profit) <= 0.0):
            raise ValidationException("New take-profit must be a finite positive price.")
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return OrderResponse(OrderId=str(ticket), Symbol="", Status="Failed",
                                 SubmittedAt=datetime.now(timezone.utc), Retcode=-1,
                                 Comment=f"Position {ticket} was not found; TP was not modified.")
        position = positions[0]
        def _field_value(obj: Any, name: str, default: Any = None) -> Any:
            return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)
        symbol = str(_field_value(position, "symbol", ""))
        stop_loss = float(_field_value(position, "sl", 0.0) or 0.0)
        current_tp = float(_field_value(position, "tp", 0.0) or 0.0)
        position_type = int(_field_value(position, "type", -1))
        buy_type = int(getattr(mt5, "POSITION_TYPE_BUY", 0))
        sell_type = int(getattr(mt5, "POSITION_TYPE_SELL", 1))
        new_tp = float(take_profit)
        if position_type == buy_type:
            improves = current_tp <= 0.0 or new_tp > current_tp
        elif position_type == sell_type:
            improves = current_tp <= 0.0 or new_tp < current_tp
        else:
            improves = False
        if not improves:
            return OrderResponse(OrderId=str(ticket), Symbol=symbol, Status="NoChange",
                                 SubmittedAt=datetime.now(timezone.utc), Retcode=0,
                                 Comment="TP update would not extend the existing target in the profitable direction.")
        if (position_type == buy_type and new_tp <= float(_field_value(position, "price_open", 0.0) or 0.0)) or \
                (position_type == sell_type and new_tp >= float(_field_value(position, "price_open", 0.0) or 0.0)):
            return OrderResponse(OrderId=str(ticket), Symbol=symbol, Status="Failed",
                                 SubmittedAt=datetime.now(timezone.utc), Retcode=-1,
                                 Comment="New TP is not on the profitable side of the position entry.")
        action = getattr(mt5, "TRADE_ACTION_SLTP", None)
        if action is None:
            return OrderResponse(OrderId=str(ticket), Symbol=symbol, Status="Failed",
                                 SubmittedAt=datetime.now(timezone.utc), Retcode=-1,
                                 Comment="MT5 does not expose TRADE_ACTION_SLTP.")
        request = {"action": action, "symbol": symbol, "position": ticket,
                   "sl": stop_loss, "tp": new_tp}
        checked = mt5.order_check(request)
        code = int(_field_value(checked, "retcode", -1) if checked is not None else -1)
        if checked is None or code not in (0, 10009):
            return OrderResponse(OrderId=str(ticket), Symbol=symbol, Status="Failed",
                                 SubmittedAt=datetime.now(timezone.utc), Retcode=code,
                                 Comment=f"TP-extension order_check failed: {_field_value(checked, 'comment', 'no response')}")
        result = mt5.order_send(request)
        result_code = int(_field_value(result, "retcode", -1) if result is not None else -1)
        success_codes = {0, 10009, int(getattr(mt5, "TRADE_RETCODE_DONE", 10009))}
        return OrderResponse(OrderId=str(ticket), Symbol=symbol,
                             Status="Modified" if result is not None and result_code in success_codes else "Failed",
                             SubmittedAt=datetime.now(timezone.utc), Retcode=result_code,
                             Comment=str(_field_value(result, "comment", "no response") if result is not None else "TP update returned None"))

    def clear_position_take_profit(self, ticket: int) -> OrderResponse:
        """Clear a preset TP on an existing position while preserving its protective SL.

        This operation is intentionally DEMO-only and fail-closed. The caller must
        verify the position belongs to YarTrader before invoking it.
        """
        self.verify_safety_and_account(operation_type="DEMO")
        mt5 = self._mt5
        if mt5 is None or not self._initialized:
            raise ValidationException("MT5 is not initialized; cannot clear position TP.")
        ticket = int(ticket)
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return OrderResponse(
                OrderId=str(ticket), Symbol="", Status="Failed",
                SubmittedAt=datetime.now(timezone.utc), Retcode=-1,
                Comment=f"Position {ticket} was not found; TP was not modified.",
            )
        position = positions[0]
        def _field_value(obj: Any, name: str, default: Any = None) -> Any:
            return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)
        symbol = str(_field_value(position, "symbol", ""))
        stop_loss = float(_field_value(position, "sl", 0.0) or 0.0)
        current_tp = float(_field_value(position, "tp", 0.0) or 0.0)
        if current_tp <= 0.0:
            return OrderResponse(
                OrderId=str(ticket), Symbol=symbol, Status="NoChange",
                SubmittedAt=datetime.now(timezone.utc), Retcode=0,
                Comment="Position already has no preset take-profit.",
            )
        action = getattr(mt5, "TRADE_ACTION_SLTP", None)
        if action is None:
            return OrderResponse(
                OrderId=str(ticket), Symbol=symbol, Status="Failed",
                SubmittedAt=datetime.now(timezone.utc), Retcode=-1,
                Comment="MT5 does not expose TRADE_ACTION_SLTP; TP was not modified.",
            )
        request = {
            "action": action, "symbol": symbol, "position": ticket,
            "sl": stop_loss, "tp": 0.0,
        }
        checked = mt5.order_check(request)
        check_code = int(_field_value(checked, "retcode", -1) if checked is not None else -1)
        if checked is None or check_code not in (0, 10009):
            raw_check = checked if isinstance(checked, dict) else (checked._asdict() if hasattr(checked, "_asdict") else {})
            return OrderResponse(
                OrderId=str(ticket), Symbol=symbol, Status="Failed",
                SubmittedAt=datetime.now(timezone.utc), Retcode=check_code,
                Comment=f"TP-clear order_check failed: {_field_value(checked, 'comment', 'no response')}",
                RawResponse=raw_check,
            )
        result = mt5.order_send(request)
        result_code = int(_field_value(result, "retcode", -1) if result is not None else -1)
        success_codes = {0, 10009, int(getattr(mt5, "TRADE_RETCODE_DONE", 10009))}
        raw_result = result if isinstance(result, dict) else (result._asdict() if hasattr(result, "_asdict") else {})
        return OrderResponse(
            OrderId=str(ticket), Symbol=symbol,
            Status="Modified" if result is not None and result_code in success_codes else "Failed",
            SubmittedAt=datetime.now(timezone.utc), Retcode=result_code,
            Comment=str(_field_value(result, "comment", "no response") if result is not None else "TP-clear order_send returned None"),
            RawResponse=raw_result,
        )

    def get_active_orders(self, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Return active broker orders; None means state unknown and must block new entries."""
        if not self._mt5 or not self._initialized:
            return None
        try:
            orders = self._mt5.orders_get(symbol=symbol) if symbol else self._mt5.orders_get()
        except Exception as exc:
            logger.error("[RealMT5BrokerAdapter] orders_get failed: %s", exc)
            return None
        if orders is None:
            return None
        return [o._asdict() if hasattr(o, "_asdict") else dict(o) for o in orders]

    def cancel_pending_order(self, ticket: int) -> OrderResponse:
        """Remove a pending order only after the DEMO account safety gate passes."""
        self.verify_safety_and_account(operation_type="DEMO")
        if not self._mt5 or not self._initialized:
            raise ValidationException("MT5 is not initialized; cannot cancel a pending order.")
        ticket = int(ticket)
        active = self._mt5.orders_get(ticket=ticket)
        if not active:
            raise ValidationException(f"Pending order {ticket} is not present in active broker orders.")
        order = active[0]
        symbol = str(getattr(order, "symbol", ""))
        request = {"action": self._mt5.TRADE_ACTION_REMOVE, "order": ticket, "symbol": symbol}
        checked = self._mt5.order_check(request)
        retcode = getattr(checked, "retcode", -1) if checked is not None else -1
        if checked is None or retcode not in (0, 10009):
            raise ValidationException(f"Pending-order cancel check failed for {ticket}: {getattr(checked, 'comment', 'no response')}")
        result = self._mt5.order_send(request)
        if result is None:
            raise ValidationException(f"Pending-order cancel returned no broker response for {ticket}.")
        code = getattr(result, "retcode", -1)
        success = code in (0, getattr(self._mt5, "TRADE_RETCODE_DONE", 10009), getattr(self._mt5, "TRADE_RETCODE_PLACED", 10008))
        return OrderResponse(
            OrderId=str(ticket), Symbol=symbol, Status="Cancelled" if success else "Failed",
            SubmittedAt=datetime.now(timezone.utc), Retcode=code,
            Comment=str(getattr(result, "comment", "")),
            RawResponse=result._asdict() if hasattr(result, "_asdict") else {},
        )

    def get_positions(self, symbol: Optional[str] = None, ticket: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """Queries active MT5 positions using mt5.positions_get(). Returns None (UNKNOWN) if MT5 is disconnected or query fails."""
        if not self._mt5 or not self._initialized:
            return None
        kwargs = {}
        if symbol:
            kwargs["symbol"] = symbol
        if ticket:
            kwargs["ticket"] = int(ticket)

        try:
            positions = self._mt5.positions_get(**kwargs)
            if positions is None:
                return None
        except Exception as e:
            logger.error(f"[RealMT5BrokerAdapter] positions_get exception: {e}")
            return None

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
            if type(self._mt5).__name__ == "MT5BridgeProxy":
                orders = self._mt5.history_orders_get(date_from=date_from, date_to=date_to, group=group or "")
            else:
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
            if type(self._mt5).__name__ == "MT5BridgeProxy":
                deals = self._mt5.history_deals_get(date_from=date_from, date_to=date_to)
            else:
                deals = self._mt5.history_deals_get(date_from, date_to)
        else:
            deals = self._mt5.history_deals_get()

        if deals is None:
            return []

        res = []
        for d in deals:
            res.append(d._asdict() if hasattr(d, "_asdict") else dict(d))
        return res
