"""MT4 DEMO broker adapter backed by the YarTrader MQL4 bridge EA.

The EA owns broker calls and verifies IsDemo(), the exact account/server,
and XAUUSD-only execution. Python fails closed when the bridge is absent.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.Execution.Interfaces.interfaces import IBrokerAdapter
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Execution.Adapters.mt4_file_bridge import MT4FileBridge
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("RealMT4BrokerAdapter")


class RealMT4BrokerAdapter(IBrokerAdapter):
    TARGET_ACCOUNT = MetaTraderSafetyGate.MT4_DEMO_ACCOUNT
    TARGET_SERVER = MetaTraderSafetyGate.MT4_DEMO_SERVER
    PLATFORM_NAME = "MT4"

    def __init__(self, auto_initialize: bool = True, bridge: Optional[MT4FileBridge] = None) -> None:
        self.bridge = bridge or MT4FileBridge()
        self._initialized = False
        if auto_initialize:
            self._try_init()

    def _try_init(self) -> bool:
        try:
            info = self.get_account_info()
            self._initialized = bool(info and info.get("is_demo"))
        except Exception as exc:
            logger.warning("[RealMT4BrokerAdapter] bridge unavailable: %s", exc)
            self._initialized = False
        return self._initialized

    def verify_safety_and_account(self, operation_type: str = "DEMO") -> bool:
        MetaTraderSafetyGate.verify_operation(
            terminal_type="MT4", operation_type=operation_type,
            account_id=self.TARGET_ACCOUNT, server_name=self.TARGET_SERVER,
        )
        info = self.get_account_info()
        if not info:
            raise ValidationException("MT4 DEMO bridge is disconnected (fail-closed).")
        if not bool(info.get("is_demo")):
            raise ValidationException("SECURITY VIOLATION: connected MT4 account is not DEMO.")
        if str(info.get("login")) != self.TARGET_ACCOUNT:
            raise ValidationException(
                f"Unauthorized MT4 account '{info.get('login')}'; expected '{self.TARGET_ACCOUNT}'."
            )
        if str(info.get("server")) != self.TARGET_SERVER:
            raise ValidationException(
                f"Unauthorized MT4 server '{info.get('server')}'; expected '{self.TARGET_SERVER}'."
            )
        return True

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        try:
            parts = self.bridge.request("ACCOUNT")
            if not parts or parts[0] != "OK" or len(parts) < 5:
                return None
            return {
                "login": parts[1], "server": parts[2], "is_demo": parts[3] == "1",
                "balance": float(parts[4]), "trade_mode": 0 if parts[3] == "1" else 1,
            }
        except Exception:
            return None

    def get_terminal_info(self) -> Optional[Dict[str, Any]]:
        hb = self.bridge.heartbeat()
        if not hb:
            return None
        return {"connected": True, "server": hb["server"], "login": hb["login"], "is_demo": hb["is_demo"]}

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        tick = self.get_symbol_tick(symbol)
        return {"name": symbol.upper(), **tick} if tick else None

    def get_symbol_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            parts = self.bridge.request("TICK", symbol.upper())
            if not parts or parts[0] != "OK" or len(parts) < 5:
                return None
            return {"symbol": parts[1], "bid": float(parts[2]), "ask": float(parts[3]), "time": int(parts[4])}
        except Exception:
            return None

    def get_positions(self, symbol: Optional[str] = None, ticket: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        try:
            parts = self.bridge.request("POSITIONS", symbol.upper() if symbol else "")
            if not parts or parts[0] != "OK":
                return None
            raw = parts[1] if len(parts) > 1 else ""
            positions = []
            for item in filter(None, raw.split(";")):
                fields = item.split(",")
                if len(fields) < 5:
                    continue
                pos = {
                    "ticket": int(fields[0]), "type": int(fields[1]), "volume": float(fields[2]),
                    "price_open": float(fields[3]), "time": int(fields[4]),
                }
                if ticket is None or pos["ticket"] == int(ticket):
                    positions.append(pos)
            return positions
        except Exception:
            return None

    def send_order_to_broker(self, request: OrderRequest) -> OrderResponse:
        self.verify_safety_and_account("DEMO")
        if request.Symbol.upper() != "XAUUSD":
            raise ValidationException("MT4 DEMO execution is restricted to XAUUSD.")
        direction = request.OrderType.upper()
        if direction not in {"BUY", "SELL"}:
            raise ValidationException(f"Unsupported MT4 DEMO order type '{direction}'.")
        parts = self.bridge.request(
            "ORDER", request.Symbol.upper(), direction, request.Volume,
            request.Price or 0.0, request.StopLoss or 0.0,
            request.TakeProfit or 0.0, request.Magic or 0,
        )
        now = datetime.now(timezone.utc)
        if not parts or parts[0] != "OK":
            err = parts[1] if len(parts) > 1 else "UNKNOWN"
            return OrderResponse(
                OrderId="0", Symbol=request.Symbol.upper(), Status="Failed", SubmittedAt=now,
                Retcode=10021, Comment=f"MT4 bridge error {err}",
                RawResponse={"platform": "MT4", "error": err},
            )
        return OrderResponse(
            OrderId=parts[1], Symbol=request.Symbol.upper(), Status="Filled", SubmittedAt=now,
            Retcode=10009, Comment="MT4 DEMO order accepted", DealTicket=parts[1],
            Price=float(parts[2]), Volume=float(parts[3]),
            RawResponse={"platform": "MT4", "account": self.TARGET_ACCOUNT},
        )

    def close_order(self, ticket: int, volume: float) -> OrderResponse:
        self.verify_safety_and_account("DEMO")
        parts = self.bridge.request("CLOSE", int(ticket), float(volume))
        now = datetime.now(timezone.utc)
        if not parts or parts[0] != "OK":
            err = parts[1] if len(parts) > 1 else "UNKNOWN"
            return OrderResponse(
                OrderId=str(ticket), Symbol="XAUUSD", Status="Failed", SubmittedAt=now,
                Retcode=10021, Comment=f"MT4 bridge error {err}",
                RawResponse={"platform": "MT4", "error": err},
            )
        return OrderResponse(
            OrderId=str(ticket), Symbol="XAUUSD", Status="Filled", SubmittedAt=now,
            Retcode=10009, Comment="MT4 DEMO position closed", DealTicket=str(ticket),
            Price=float(parts[2]), Volume=float(parts[3]), RawResponse={"platform": "MT4"},
        )

    def send_order(self, request: OrderRequest) -> OrderResponse:
        return self.send_order_to_broker(request)
