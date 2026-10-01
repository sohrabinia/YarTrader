"""Fail-closed file IPC bridge for a locally attached MT4 DEMO EA.

The EA owns all broker calls. Python never imports a fictitious MetaTrader4
package and never talks to a live account. The shared FILE_COMMON directory
is the only transport.
"""
import glob
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional


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

    def heartbeat(self) -> Optional[Dict[str, str]]:
        p = self._path(self.HEARTBEAT)
        if not p.exists():
            return None
        try:
            parts = p.read_text(encoding="utf-8").strip().split("|")
            if len(parts) < 7:
                return None
            return {"login": parts[0], "server": parts[1], "is_demo": parts[2] == "1",
                    "symbol": parts[3], "bid": float(parts[4]), "ask": float(parts[5]), "time": int(parts[6])}
        except (OSError, ValueError):
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
                    response.unlink(missing_ok=True)
                if not parts or parts[0] != request_id:
                    raise RuntimeError("MT4 bridge returned an invalid response id.")
                return parts[1:]
            time.sleep(0.05)
        raise RuntimeError("MT4 bridge request timed out; execution is fail-closed.")
