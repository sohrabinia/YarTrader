"""Session-2 MT5 bridge for the LocalSystem YarTrader runtime.

The native MetaTrader5 Python package uses Windows-session-scoped IPC.  YarTrader's
production service intentionally runs as LocalSystem in Session 0, while the
interactive MT5 terminal runs in the logged-in operator session.  This module
provides a loopback-only, token-authenticated JSON bridge so the service can
consume the same terminal without moving the service account or weakening the
execution gates.

The agent is deliberately a separate process.  It must run in the same Windows
user session as terminal64.exe.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional


DEFAULT_URL = "http://127.0.0.1:8765"
TOKEN_ENV = "YARTRADER_MT5_BRIDGE_TOKEN"
ALLOW_DEMO_ENV = "YARTRADER_MT5_BRIDGE_ALLOW_DEMO_EXECUTION"


def _jsonable(value: Any) -> Any:
    """Convert MT5/native values to JSON-safe primitives without losing row fields."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()

    # MetaTrader5 copy_rates_* returns a NumPy structured ndarray in the
    # interactive Session-2 process.  Serializing that ndarray with str()
    # turns the entire candle series into one string, which later makes the
    # production provider fail with "'str' object has no attribute 'time'".
    dtype = getattr(value, "dtype", None)
    field_names = getattr(dtype, "names", None) if dtype is not None else None
    if field_names:
        return [
            {str(name): _jsonable(row[name]) for name in field_names}
            for row in value
        ]

    if hasattr(value, "_asdict"):
        return {str(k): _jsonable(v) for k, v in value._asdict().items()}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]

    # NumPy scalar values expose item(), which converts them to native Python
    # ints/floats before json.dumps sees them.
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _jsonable(item())
        except (TypeError, ValueError):
            pass

    # Generic array-like values (without named structured fields).
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            return _jsonable(tolist())
        except (TypeError, ValueError):
            pass

    return str(value)


@dataclass
class BridgeResponse:
    ok: bool
    result: Any = None
    error: Optional[str] = None
    error_code: Optional[int] = None


class MT5SessionBridgeClient:
    """Small synchronous JSON client used by the Session-0 service."""

    def __init__(self, url: Optional[str] = None, token: Optional[str] = None, timeout: float = 3.0):
        self.url = (url or os.getenv("YARTRADER_MT5_BRIDGE_URL") or DEFAULT_URL).rstrip("/")
        self.token = token or os.getenv(TOKEN_ENV)
        self.timeout = timeout
        self._constant_cache: Dict[str, Any] = {}

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def call(self, method: str, **params: Any) -> Any:
        if not self.token:
            raise RuntimeError(f"{TOKEN_ENV} is not configured")
        body = json.dumps({"method": method, "params": params}, default=_jsonable).encode("utf-8")
        req = urllib.request.Request(
            self.url + "/rpc",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-YarTrader-Bridge-Token": self.token,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"MT5 session bridge unavailable: {exc}") from exc
        if not payload.get("ok"):
            raise RuntimeError(payload.get("error") or "MT5 session bridge request failed")
        return payload.get("result")

    def constant(self, name: str) -> Any:
        if name not in self._constant_cache:
            self._constant_cache[name] = self.call("constant", name=name)
        return self._constant_cache[name]


class MT5BridgeProxy:
    """Drop-in subset of the MetaTrader5 module consumed by YarTrader."""

    def __init__(self, client: MT5SessionBridgeClient):
        self.client = client

    def initialize(self, *args: Any, **kwargs: Any) -> bool:
        result = self.client.call("health")
        return bool(result and result.get("connected"))

    def shutdown(self) -> None:
        return None

    def last_error(self) -> Any:
        return self.client.call("last_error")

    def terminal_info(self) -> Any:
        return _DictObject(self.client.call("terminal_info"))

    def account_info(self) -> Any:
        result = self.client.call("account_info")
        return _DictObject(result) if result else None

    def symbols_get(self) -> Any:
        return [_DictObject(x) for x in (self.client.call("symbols_get") or [])]

    def symbol_info(self, symbol: str) -> Any:
        result = self.client.call("symbol_info", symbol=symbol)
        return _DictObject(result) if result else None

    def symbol_info_tick(self, symbol: str) -> Any:
        result = self.client.call("symbol_info_tick", symbol=symbol)
        return _DictObject(result) if result else None

    def copy_rates_range(self, symbol: str, timeframe: int, date_from: Any, date_to: Any) -> Any:
        return self.client.call("copy_rates_range", symbol=symbol, timeframe=timeframe,
                                date_from=_jsonable(date_from), date_to=_jsonable(date_to))

    def copy_rates_from(self, symbol: str, timeframe: int, date_to: Any, count: int) -> Any:
        return self.client.call("copy_rates_from", symbol=symbol, timeframe=timeframe,
                                date_to=_jsonable(date_to), count=count)

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start: int, count: int) -> Any:
        return self.client.call("copy_rates_from_pos", symbol=symbol, timeframe=timeframe,
                                start=start, count=count)

    def positions_get(self, **kwargs: Any) -> Any:
        return [_DictObject(x) for x in (self.client.call("positions_get", **kwargs) or [])]

    def history_orders_get(self, **kwargs: Any) -> Any:
        return [_DictObject(x) for x in (self.client.call("history_orders_get", **kwargs) or [])]

    def history_deals_get(self, **kwargs: Any) -> Any:
        return [_DictObject(x) for x in (self.client.call("history_deals_get", **kwargs) or [])]

    def order_check(self, request: Dict[str, Any]) -> Any:
        result = self.client.call("order_check", request=request)
        return _DictObject(result) if result else None

    def order_send(self, request: Dict[str, Any]) -> Any:
        result = self.client.call("order_send", request=request)
        return _DictObject(result) if result else None

    def symbol_select(self, symbol: str, select: bool) -> bool:
        return bool(self.client.call("symbol_select", symbol=symbol, select=select))

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        return self.client.constant(name)


class _DictObject:
    def __init__(self, values: Optional[Dict[str, Any]]):
        self._values = values or {}

    def __getattr__(self, name: str) -> Any:
        try:
            return self._values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def _asdict(self) -> Dict[str, Any]:
        return dict(self._values)


class _AgentHandler(BaseHTTPRequestHandler):
    server_version = "YarTrader-MT5-Session-Agent/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[MT5SessionAgent] " + (fmt % args))

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write(200, {"ok": True, "service": "yartrader-mt5-session-agent"})
        else:
            self._write(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/rpc":
            self._write(404, {"ok": False, "error": "not found"})
            return
        expected = self.server.token
        supplied = self.headers.get("X-YarTrader-Bridge-Token", "")
        if not expected or not secrets.compare_digest(supplied, expected):
            self._write(401, {"ok": False, "error": "unauthorized"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            result = self.server.dispatch(request.get("method"), request.get("params") or {})
            self._write(200, {"ok": True, "result": _jsonable(result)})
        except Exception as exc:
            self._write(200, {"ok": False, "error": str(exc)})

    def _write(self, code: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload, default=_jsonable).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class MT5SessionAgent(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, host: str, port: int, token: str, mt5_module: Any):
        super().__init__((host, port), _AgentHandler)
        self.token = token
        self.mt5 = mt5_module

    def _account_guard(self) -> Any:
        acc = self.mt5.account_info()
        if acc is None:
            raise RuntimeError(f"MT5 account_info unavailable: {self.mt5.last_error()}")
        login = str(getattr(acc, "login", ""))
        server = str(getattr(acc, "server", ""))
        trade_mode = getattr(acc, "trade_mode", None)
        if login != "52961173" or server != "Alpari-MT5-Demo" or trade_mode not in (None, 0):
            raise RuntimeError("MT5 DEMO account safety guard rejected active terminal")
        return acc

    def dispatch(self, method: str, params: Dict[str, Any]) -> Any:
        if method == "health":
            acc = self._account_guard()
            term = self.mt5.terminal_info()
            return {
                "connected": bool(term is not None and getattr(term, "connected", False)),
                "login": str(getattr(acc, "login", "")),
                "server": str(getattr(acc, "server", "")),
                "trade_mode": getattr(acc, "trade_mode", None),
            }

        if method == "constant":
            name = str(params["name"])
            return getattr(self.mt5, name)

        if method == "last_error":
            return self.mt5.last_error()

        if method in {"terminal_info", "account_info", "symbols_get", "symbol_info", "symbol_info_tick",
                      "copy_rates_range", "copy_rates_from", "copy_rates_from_pos", "positions_get",
                      "history_orders_get", "history_deals_get"}:
            self._account_guard()
            fn = getattr(self.mt5, method)
            if method == "symbol_info":
                return fn(params["symbol"])
            if method == "symbol_info_tick":
                return fn(params["symbol"])
            if method == "symbols_get":
                return fn()
            if method == "terminal_info":
                return fn()
            if method == "account_info":
                return fn()
            if method == "copy_rates_range":
                date_from = params.get("date_from")
                date_to = params.get("date_to")
                if isinstance(date_from, str):
                    date_from = datetime.fromisoformat(date_from)
                if isinstance(date_to, str):
                    date_to = datetime.fromisoformat(date_to)
                return fn(params["symbol"], params["timeframe"], date_from, date_to)
            if method == "copy_rates_from":
                date_to = params.get("date_to")
                if isinstance(date_to, str):
                    date_to = datetime.fromisoformat(date_to)
                return fn(params["symbol"], params["timeframe"], date_to, params["count"])
            if method == "copy_rates_from_pos":
                return fn(params["symbol"], params["timeframe"], params["start"], params["count"])
            if method == "history_orders_get":
                converted = dict(params)
                for key in ("date_from", "date_to"):
                    if isinstance(converted.get(key), str):
                        converted[key] = datetime.fromisoformat(converted[key])
                if converted.get("ticket") is not None:
                    return fn(ticket=converted["ticket"])
                if converted.get("date_from") is not None and converted.get("date_to") is not None:
                    if converted.get("group") is not None:
                        return fn(converted["date_from"], converted["date_to"], group=converted["group"])
                    return fn(converted["date_from"], converted["date_to"])
                if converted.get("group") is not None:
                    return fn(group=converted["group"])
                return fn()
            if method == "history_deals_get":
                converted = dict(params)
                for key in ("date_from", "date_to"):
                    if isinstance(converted.get(key), str):
                        converted[key] = datetime.fromisoformat(converted[key])
                if converted.get("ticket") is not None:
                    return fn(ticket=converted["ticket"])
                if converted.get("position") is not None:
                    return fn(position=converted["position"])
                if converted.get("date_from") is not None and converted.get("date_to") is not None:
                    return fn(converted["date_from"], converted["date_to"])
                return fn()
            return fn(**params)
            return fn(**params)

        if method == "symbol_select":
            self._account_guard()
            return bool(self.mt5.symbol_select(params["symbol"], bool(params["select"])))

        if method in {"order_check", "order_send"}:
            if os.getenv(ALLOW_DEMO_ENV, "").strip().lower() != "true":
                raise RuntimeError(f"{ALLOW_DEMO_ENV} is not enabled")
            self._account_guard()
            request = dict(params.get("request") or {})
            if method == "order_check":
                return self.mt5.order_check(request)
            return self.mt5.order_send(request)

        raise RuntimeError(f"Unsupported MT5 bridge method: {method}")


def run_agent(host: str = "127.0.0.1", port: int = 8765) -> None:
    token = os.getenv(TOKEN_ENV)
    if not token:
        raise RuntimeError(f"{TOKEN_ENV} must be configured before starting MT5 session agent")

    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    agent = MT5SessionAgent(host, port, token, mt5)
    health = agent.dispatch("health", {})
    if not health["connected"]:
        raise RuntimeError("MT5 terminal is not connected")
    print(f"[MT5SessionAgent] listening on http://{host}:{port} account={health['login']} server={health['server']}")
    try:
        agent.serve_forever()
    finally:
        agent.server_close()
        mt5.shutdown()
