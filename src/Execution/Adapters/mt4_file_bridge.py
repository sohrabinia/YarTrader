"""Fail-closed file IPC bridge for authorized local MT4 EAs.

The EA owns all broker calls. Python never talks to a broker account directly.
Every heartbeat is parsed strictly and is considered usable only when its
account/server/demo-role fields are explicit and its timestamp is fresh.
"""
import glob
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class MT4FileBridge:
    REQUEST = "yartrader_mt4_request.txt"
    HEARTBEAT = "yartrader_mt4_heartbeat.txt"

    def __init__(self, common_dir: Optional[str] = None, timeout: float = 4.0):
        self.common_dir = Path(common_dir or os.getenv("YARTRADER_MT4_COMMON_FILES", "")).expanduser()
        if not str(self.common_dir):
            self.common_dir = Path()
        if not self.common_dir.exists():
            candidates = glob.glob(r"C:\Users\*\AppData\Roaming\MetaQuotes\Terminal\Common\Files")
            existing = [Path(p) for p in candidates if Path(p).exists()]
            if existing:
                self.common_dir = existing[0]
        self.timeout = float(timeout)

    def _path(self, name: str) -> Path:
        return self.common_dir / name

    def heartbeat(self, max_age_seconds: float = 10.0) -> Optional[Dict[str, Any]]:
        """Return only a complete, fresh heartbeat; malformed/stale data fails closed."""
        p = self._path(self.HEARTBEAT)
        if not p.exists():
            return None
        try:
            parts = p.read_text(encoding="utf-8").strip().split("|")
            if len(parts) < 7:
                return None
            login, server, demo_raw, symbol = (x.strip() for x in parts[:4])
            if not login or not server or demo_raw not in {"0", "1"} or not symbol:
                return None
            bid, ask, timestamp = float(parts[4]), float(parts[5]), int(parts[6])
            terminal_path = parts[7].strip() if len(parts) >= 8 else ""
            terminal_path = parts[7].strip() if len(parts) >= 8 else ""
            if bid <= 0 or ask <= 0 or timestamp <= 0 or not terminal_path:
                return None
            now = int(time.time())
            if timestamp > now + 5 or now - timestamp > max_age_seconds:
                return None
            return {
                "login": login,
                "server": server,
                "is_demo": demo_raw == "1",
                "symbol": symbol.upper(),
                "bid": bid,
                "ask": ask,
                "time": timestamp,
                "fresh": True,
                "terminal_path": terminal_path,
                "terminal_path": terminal_path,
            }
        except (OSError, ValueError, TypeError):
            return None

    def request(self, operation: str, *args: object) -> List[str]:
        if not self.common_dir.exists():
            raise RuntimeError("MT4 common FILE_COMMON directory is unavailable.")
        request_id = uuid.uuid4().hex
        response = self._path(f"yartrader_mt4_response_{request_id}.txt")
        request = self._path(self.REQUEST)
        if request.exists():
            age = time.time() - request.stat().st_mtime
            if age < self.timeout:
                raise RuntimeError("MT4 bridge is busy with another request.")
            request.unlink(missing_ok=True)
        payload = "|".join([request_id, operation, *[str(x) for x in args]]) + "\n"
        tmp = self._path(self.REQUEST + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, request)
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if response.exists():
                try:
                    parts = response.read_text(encoding="utf-8").strip().split("|")
                finally:
                    try:
                        response.unlink(missing_ok=True)
                    except PermissionError:
                        pass
                if not parts or parts[0] != request_id:
                    raise RuntimeError("MT4 bridge returned an invalid response id.")
                return parts[1:]
            time.sleep(0.05)
        raise RuntimeError("MT4 bridge request timed out; execution is fail-closed.")
