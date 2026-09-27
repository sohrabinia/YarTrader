import os
import time
import requests
from typing import Optional, Dict, Any, List

from src.Data.Providers.MT5.mt5 import MT5ConnectionHealth


class MT5BridgeClient:
    """Client for communicating with the local MT5 Interactive Bridge agent from Session 0 service context."""

    def __init__(self, bridge_url: Optional[str] = None, token: Optional[str] = None, timeout_sec: float = 5.0) -> None:
        self.bridge_url = bridge_url or os.getenv("MT5_BRIDGE_URL", "http://127.0.0.1:5001").rstrip("/")
        self.timeout_sec = timeout_sec
        self.token = token or self._resolve_token()

    def _resolve_token(self) -> str:
        """
        Resolves the Bearer secret token from ENV or secret file.
        Canonical Precedence:
          1. MT5_BRIDGE_SECRET_TOKEN environment variable
          2. <YarTraderStorageRoot>\\Secrets\\mt5_bridge_token.secret
          3. C:\\YarTraderAI\\Secrets\\mt5_bridge_token.secret
          No relative or legacy path fallback
        Fail-closed: Raises RuntimeError if token cannot be safely resolved.
        """
        env_token = os.getenv("MT5_BRIDGE_SECRET_TOKEN")
        if env_token and env_token.strip():
            return env_token.strip()

        try:
            from src.Application.Deployment.storage import YarTraderStorageManager
            storage_mgr = YarTraderStorageManager.get_manager()
            secret_file = os.path.join(storage_mgr.get_secrets_dir(), "mt5_bridge_token.secret")
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
        except Exception as e:
            raise RuntimeError(f"MT5 Bridge Client Security Failure: Could not read secret file: {e}")

        raise RuntimeError("MT5 Bridge Client Security Failure: MT5_BRIDGE_SECRET_TOKEN environment variable or secret file missing.")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_health(self) -> Dict[str, Any]:
        """Checks unauthenticated health endpoint on local bridge."""
        try:
            url = f"{self.bridge_url}/health"
            resp = requests.get(url, timeout=self.timeout_sec)
            if resp.status_code == 200:
                return resp.json()
            return {"status": "UNHEALTHY", "http_code": resp.status_code}
        except Exception as e:
            return {"status": "UNREACHABLE", "error": str(e)}

    def get_mt5_status(self) -> MT5ConnectionHealth:
        """Retrieves authoritative MT5 connection status from local bridge."""
        try:
            url = f"{self.bridge_url}/mt5/status"
            resp = requests.get(url, headers=self._get_headers(), timeout=self.timeout_sec)
            if resp.status_code == 200:
                data = resp.json()
                return MT5ConnectionHealth(
                    connected=data.get("connected", False),
                    server=data.get("server"),
                    ping_ms=data.get("ping_ms", 0.0),
                    last_error=data.get("last_error")
                )
            elif resp.status_code == 401:
                return MT5ConnectionHealth(
                    connected=False,
                    server=None,
                    ping_ms=0.0,
                    last_error="Bridge Authentication Failed: 401 Unauthorized"
                )
            elif resp.status_code == 403:
                return MT5ConnectionHealth(
                    connected=False,
                    server=None,
                    ping_ms=0.0,
                    last_error="Bridge Security Violation: Non-loopback request rejected (403 Forbidden)"
                )
            else:
                return MT5ConnectionHealth(
                    connected=False,
                    server=None,
                    ping_ms=0.0,
                    last_error=f"Bridge HTTP Error: {resp.status_code}"
                )
        except requests.exceptions.Timeout:
            return MT5ConnectionHealth(
                connected=False,
                server=None,
                ping_ms=0.0,
                last_error="Bridge Connection Timeout"
            )
        except Exception as e:
            return MT5ConnectionHealth(
                connected=False,
                server=None,
                ping_ms=0.0,
                last_error=f"Bridge Client Exception: {str(e)}"
            )

    def fetch_market_data(
        self,
        symbol: str,
        timeframe: str = "H1",
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetches raw market candles from local bridge supporting time ranges."""
        url = f"{self.bridge_url}/market-data"
        payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": count,
            "start_time": start_time,
            "end_time": end_time
        }
        try:
            resp = requests.post(url, json=payload, headers=self._get_headers(), timeout=self.timeout_sec)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("candles", [])
            else:
                return []
        except Exception:
            return []
