import os
import sys
import time
import secrets
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Header, HTTPException, Security, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from src.Application.Deployment.storage import YarTraderStorageManager


def _get_mt5_pid(t_info: Any) -> Optional[int]:
    """Resolves the OS process ID (PID) for the active MT5 terminal process."""
    if t_info is None:
        return None
    if hasattr(t_info, "pid") and getattr(t_info, "pid", None):
        return int(getattr(t_info, "pid"))

    term_path = getattr(t_info, "path", None)
    if not term_path:
        return None

    try:
        import psutil
        norm_target = os.path.normpath(term_path).lower()
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                exe = proc.info.get('exe')
                if exe and os.path.normpath(exe).lower() == norm_target:
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import subprocess
            out = subprocess.check_output('wmic process where "name=\'terminal64.exe\'" get ExecutablePath,ProcessId /format:csv', shell=True, text=True)
            norm_target = os.path.normpath(term_path).lower()
            for line in out.splitlines():
                parts = [p.strip() for p in line.split(",") if p.strip()]
                if len(parts) >= 3:
                    exe_path = parts[1]
                    pid_str = parts[2]
                    if os.path.normpath(exe_path).lower() == norm_target and pid_str.isdigit():
                        return int(pid_str)
        except Exception:
            pass

    return None


def get_or_create_bridge_secret_token() -> str:
    """
    Retrieves or auto-generates the secure ACL-restricted token for the MT5 Interactive Bridge.
    Canonical Precedence:
      1. MT5_BRIDGE_SECRET_TOKEN environment variable
      2. <YarTraderStorageRoot>\\Secrets\\mt5_bridge_token.secret
      3. C:\\YarTraderAI\\Secrets\\mt5_bridge_token.secret
    Only canonical absolute storage paths are accepted; no relative or legacy fallbacks.
    Fail-closed: Raises RuntimeError if token cannot be safely resolved or generated.
    """
    env_token = os.getenv("MT5_BRIDGE_SECRET_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    try:
        storage_mgr = YarTraderStorageManager.get_manager()
        secret_dir = storage_mgr.get_secrets_dir()
        os.makedirs(secret_dir, exist_ok=True)
        secret_file = os.path.join(secret_dir, "mt5_bridge_token.secret")

        candidate_files = [
            secret_file,
            os.path.join(r"C:\YarTraderAI\Secrets", "mt5_bridge_token.secret"),
        ]
        for cf in candidate_files:
            if os.path.exists(cf):
                with open(cf, "r", encoding="utf-8-sig") as f:
                    tok = f.read().strip()
                    if tok:
                        return tok

        raise RuntimeError(
            "MT5 Bridge Security Failure: canonical secret token is missing; "
            "set MT5_BRIDGE_SECRET_TOKEN or provision the canonical secret file."
        )
    except Exception as e:
        raise RuntimeError(f"MT5 Bridge Security Failure: Could not resolve or generate secret token: {e}")


security_scheme = HTTPBearer(auto_error=False)

app = FastAPI(
    title="YarTrader MT5 Interactive Bridge",
    description="Read-Only Local Loopback Bridge Agent connecting Session 0 Windows Service to Session 2 MT5 Terminal",
    version="1.0.0"
)


def verify_bearer_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> str:
    """Enforces Bearer authentication on protected Bridge endpoints."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AUTHENTICATION_REQUIRED", "message": "Missing or invalid Authorization Bearer header"}
        )
    token = credentials.credentials.strip()
    expected_token = get_or_create_bridge_secret_token()
    if not secrets.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_TOKEN", "message": "Unauthorized MT5 Bridge token"}
        )
    return token


from fastapi.responses import JSONResponse

@app.middleware("http")
async def enforce_loopback_only(request: Request, call_next):
    """Rejects any non-loopback network request fail-closed."""
    client_host = request.client.host if request.client else "unknown"
    allowed_hosts = ["127.0.0.1", "localhost", "::1", "testclient"]
    if client_host not in allowed_hosts:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "LOOPBACK_ONLY", "message": "Access restricted strictly to local loopback"}
        )
    return await call_next(request)


class MarketDataRequest(BaseModel):
    symbol: str
    timeframe: str = "H1"
    count: int = 100
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@app.get("/health")
def get_health():
    """Unauthenticated public health probe."""
    now_utc = datetime.now(timezone.utc).isoformat()
    return {
        "status": "HEALTHY",
        "service": "YarTrader.MT5Bridge",
        "version": "1.0.0",
        "mt5_installed": MT5_AVAILABLE,
        "bridge_pid": os.getpid(),
        "timestamp": time.time(),
        "timestamp_utc": now_utc
    }


@app.get("/mt5/status")
def get_mt5_status(token: str = Security(verify_bearer_token)):
    """Authenticated endpoint returning authoritative MT5 terminal connection health."""
    now_utc = datetime.now(timezone.utc).isoformat()
    bridge_pid = os.getpid()

    if not MT5_AVAILABLE or mt5 is None:
        return {
            "connected": False,
            "initialized": False,
            "server": None,
            "login": None,
            "last_error": "MetaTrader5 Python library unavailable in Bridge environment",
            "ping_ms": 0.0,
            "bridge_pid": bridge_pid,
            "mt5_terminal_path": None,
            "source": "MT5_BRIDGE_AGENT",
            "retrieval_timestamp": now_utc
        }

    try:
        t_info = mt5.terminal_info()
        if t_info is None or not getattr(t_info, "connected", False):
            init_ok = mt5.initialize()
            if not init_ok:
                err = mt5.last_error()
                return {
                    "connected": False,
                    "initialized": False,
                    "server": None,
                    "login": None,
                    "last_error": f"MT5 initialize failed: {err}",
                    "ping_ms": 0.0,
                    "bridge_pid": bridge_pid,
                    "mt5_terminal_path": None,
                    "source": "MT5_BRIDGE_AGENT",
                    "retrieval_timestamp": now_utc
                }
            t_info = mt5.terminal_info()

        a_info = mt5.account_info()
        ping_ms = getattr(t_info, "ping_last", 0.0) / 1000.0 if t_info else 0.0
        term_path = getattr(t_info, "path", None) if t_info else None
        mt5_pid = _get_mt5_pid(t_info)

        return {
            "connected": bool(t_info and getattr(t_info, "connected", False)),
            "initialized": True,
            "server": getattr(a_info, "server", None) if a_info else None,
            "login": getattr(a_info, "login", None) if a_info else None,
            "last_error": None,
            "ping_ms": float(ping_ms),
            "bridge_pid": bridge_pid,
            "mt5_pid": mt5_pid,
            "mt5_terminal_path": term_path,
            "source": "LIVE_MT5_TERMINAL",
            "retrieval_timestamp": now_utc
        }
    except Exception as e:
        return {
            "connected": False,
            "initialized": False,
            "server": None,
            "login": None,
            "last_error": f"Bridge MT5 exception: {str(e)}",
            "ping_ms": 0.0,
            "bridge_pid": bridge_pid,
            "mt5_terminal_path": None,
            "source": "MT5_BRIDGE_AGENT",
            "retrieval_timestamp": now_utc
        }


def _convert_tf(tf_str: str) -> int:
    """Converts timeframe string to MT5 timeframe constant."""
    if not MT5_AVAILABLE or mt5 is None:
        return 16385  # Default H1
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    return tf_map.get(tf_str.upper(), mt5.TIMEFRAME_H1)


def _parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


@app.post("/market-data")
def fetch_market_data(req: MarketDataRequest, token: str = Security(verify_bearer_token)):
    """Authenticated endpoint returning raw MT5 rates/candles for a symbol supporting time ranges."""
    now_utc = datetime.now(timezone.utc).isoformat()
    bridge_pid = os.getpid()

    if not MT5_AVAILABLE or mt5 is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "MT5_UNAVAILABLE", "message": "MetaTrader5 library unavailable on Bridge agent"}
        )

    tf_const = _convert_tf(req.timeframe)
    symbol = req.symbol.upper()

    try:
        t_info = mt5.terminal_info()
        if t_info is None or not getattr(t_info, "connected", False):
            if not mt5.initialize():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"error": "MT5_DISCONNECTED", "message": f"MT5 initialize failed on Bridge: {mt5.last_error()}"}
                )
            t_info = mt5.terminal_info()

        a_info = mt5.account_info()
        mt5.symbol_select(symbol, True)

        start_dt = _parse_dt(req.start_time)
        end_dt = _parse_dt(req.end_time)

        rates = None
        if start_dt and end_dt and start_dt < end_dt:
            rates = mt5.copy_rates_range(symbol, tf_const, start_dt, end_dt)

        if rates is None or len(rates) == 0:
            rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, req.count)

        if rates is None or len(rates) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NO_DATA", "message": f"MT5 returned no data for symbol {symbol}"}
            )

        candle_list = []
        for r in rates:
            candle_list.append({
                "time": int(r["time"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "tick_volume": int(r["tick_volume"]),
                "spread": int(r["spread"]),
                "real_volume": int(r["real_volume"])
            })

        term_path = getattr(t_info, "path", None) if t_info else None
        mt5_pid = _get_mt5_pid(t_info)
        server_name = getattr(a_info, "server", None) if a_info else None
        login_id = getattr(a_info, "login", None) if a_info else None

        return {
            "symbol": symbol,
            "timeframe": req.timeframe,
            "requested_count": req.count,
            "returned_count": len(candle_list),
            "bridge_pid": bridge_pid,
            "mt5_pid": mt5_pid,
            "mt5_terminal_path": term_path,
            "server": server_name,
            "login": login_id,
            "retrieval_timestamp": now_utc,
            "data_source": "LIVE_MT5_TERMINAL",
            "data_provenance": "PROVEN_AUTHORITATIVE_MT5_RATES",
            "candles": candle_list
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "BRIDGE_FETCH_EXCEPTION", "message": f"Exception fetching market data: {str(e)}"}
        )


def run_bridge_server(host: str = "127.0.0.1", port: int = 5001):
    """Entrypoint to run the uvicorn server for the MT5 Interactive Bridge."""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    port_env = int(os.getenv("MT5_BRIDGE_PORT", "5001"))
    run_bridge_server(host="127.0.0.1", port=port_env)
