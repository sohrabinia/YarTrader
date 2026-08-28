"""
YarTrader MT5 User-Session Local Bridge Server
Runs inside the interactive user desktop session (Session 2/Session 1) where MT5 terminal is active.
Binds strictly to 127.0.0.1:8001 and provides local IPC bridge for YarTrader Windows Service (Session 0).

SECURITY MANDATE:
- Binds ONLY to 127.0.0.1 (localhost).
- Never exposes passwords, raw credentials, balance, equity, or account holder names.
- Read-only data/health bridge. Live trading is strictly disabled.
"""

import os
import sys
import json
import time
import socket
import logging
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [MT5-BRIDGE] %(message)s")
logger = logging.getLogger("MT5UserSessionBridge")

HOST = "127.0.0.1"
PORT = 8001

MT5_INITIALIZED = False
mt5 = None

def init_mt5() -> bool:
    global mt5, MT5_INITIALIZED
    try:
        import MetaTrader5 as mt5_module
        mt5 = mt5_module
        term_path = os.getenv("YARTRADER_MT5_TERMINAL_PATH") or os.getenv("TRADEYAR_MT5_TERMINAL_PATH") or r"C:\Program Files\MetaTrader 5\terminal64.exe"
        if os.path.exists(term_path) and mt5.initialize(path=term_path):
            MT5_INITIALIZED = True
            logger.info(f"MT5 initialized successfully via explicit path: {term_path}")
            return True
        elif mt5.initialize():
            MT5_INITIALIZED = True
            logger.info("MT5 initialized successfully via default IPC.")
            return True
        else:
            err = mt5.last_error()
            logger.warning(f"MT5 initialize failed: {err}")
            MT5_INITIALIZED = False
            return False
    except ImportError:
        logger.error("MetaTrader5 package not installed in Python environment.")
        MT5_INITIALIZED = False
        return False
    except Exception as e:
        logger.error(f"Exception initializing MT5 in bridge: {e}")
        MT5_INITIALIZED = False
        return False

class MT5BridgeRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy HTTP request logging unless error
        pass

    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            global MT5_INITIALIZED, mt5
            connected = False
            if not MT5_INITIALIZED:
                init_mt5()

            if MT5_INITIALIZED and mt5 is not None:
                try:
                    term_info = mt5.terminal_info()
                    if term_info is not None and getattr(term_info, "connected", False):
                        connected = True
                except Exception:
                    connected = False

            self._send_json({
                "status": "healthy" if connected else "degraded",
                "connected": connected,
                "terminal_running": connected,
                "provider_health": "HEALTHY" if connected else "UNHEALTHY",
                "bridge": "active",
                "session": "user_desktop",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            self._send_json({"error": "Endpoint not found"}, 404)

    def do_POST(self):
        if self.path == "/fetch_rates":
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self._send_json({"is_success": False, "error_message": "Invalid JSON body"}, 400)
                return

            symbol = payload.get("symbol", "XAUUSD")
            timeframe = payload.get("timeframe", "H1")
            start_str = payload.get("start_time")
            end_str = payload.get("end_time")

            global MT5_INITIALIZED, mt5
            if not MT5_INITIALIZED:
                if not init_mt5():
                    self._send_json({"is_success": False, "error_message": "MT5 terminal offline on user session bridge"}, 503)
                    return

            try:
                tf_map = {
                    "M1": getattr(mt5, "TIMEFRAME_M1", 1),
                    "M5": getattr(mt5, "TIMEFRAME_M5", 5),
                    "M15": getattr(mt5, "TIMEFRAME_M15", 15),
                    "M30": getattr(mt5, "TIMEFRAME_M30", 30),
                    "H1": getattr(mt5, "TIMEFRAME_H1", 16385),
                    "H4": getattr(mt5, "TIMEFRAME_H4", 16388),
                    "D1": getattr(mt5, "TIMEFRAME_D1", 16408),
                }
                mt5_tf = tf_map.get(timeframe.upper(), getattr(mt5, "TIMEFRAME_H1", 16385))

                start_dt = datetime.fromisoformat(start_str) if start_str else datetime.now(timezone.utc) - timedelta(hours=24)
                end_dt = datetime.fromisoformat(end_str) if end_str else datetime.now(timezone.utc)

                if start_dt.tzinfo is not None:
                    start_dt = start_dt.astimezone(timezone.utc).replace(tzinfo=None)
                if end_dt.tzinfo is not None:
                    end_dt = end_dt.astimezone(timezone.utc).replace(tzinfo=None)

                if not mt5.symbol_select(symbol, True):
                    logger.warning(f"Could not select symbol {symbol} in Market Watch")

                rates = mt5.copy_rates_range(symbol, mt5_tf, start_dt, end_dt)
                if rates is None or len(rates) == 0:
                    # Fallback pos
                    rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, 100)

                if rates is None:
                    err_code, err_msg = mt5.last_error()
                    self._send_json({"is_success": False, "error_message": f"MT5 copy_rates failed: ({err_code}) {err_msg}"}, 500)
                    return

                raw_rates = []
                for rate in rates:
                    raw_rates.append({
                        "time": int(rate["time"]),
                        "open": float(rate["open"]),
                        "high": float(rate["high"]),
                        "low": float(rate["low"]),
                        "close": float(rate["close"]),
                        "tick_volume": float(rate.get("tick_volume", rate.get("volume", 0)))
                    })

                self._send_json({"is_success": True, "raw_data": raw_rates})
            except Exception as e:
                self._send_json({"is_success": False, "error_message": f"Bridge exception: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Endpoint not found"}, 404)

def run_bridge_server():
    # Single instance check
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((HOST, PORT))
    except socket.error:
        logger.warning(f"Port {PORT} is already bound. Another MT5 User-Session Bridge instance is already running.")
        sys.exit(0)

    sock.close()

    init_mt5()

    server = HTTPServer((HOST, PORT), MT5BridgeRequestHandler)
    logger.info(f"YarTrader MT5 User-Session Bridge listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Bridge server shutting down...")
    finally:
        if mt5 is not None and MT5_INITIALIZED:
            try:
                mt5.shutdown()
            except Exception:
                pass
        server.server_close()

if __name__ == "__main__":
    run_bridge_server()
