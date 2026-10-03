import time
import tempfile
from pathlib import Path
from unittest import TestCase

from src.Execution.Adapters.mt4_file_bridge import MT4FileBridge
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.exceptions import ValidationException


class TestMT4RoleIsolation(TestCase):
    def write_hb(self, directory: Path, login: str, server: str, demo: str, timestamp=None):
        ts = int(time.time() if timestamp is None else timestamp)
        (directory / MT4FileBridge.HEARTBEAT).write_text(
            f"{login}|{server}|{demo}|XAUUSD|2000.0|2000.2|{ts}|C:\\\\MT4Demo", encoding="utf-8"
        )

    def test_malformed_heartbeat_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / MT4FileBridge.HEARTBEAT
            p.write_text("252031952|Alpari-Pro.ECN-Demo|1|XAUUSD|2000.0", encoding="utf-8")
            self.assertIsNone(MT4FileBridge(td).heartbeat())

    def test_missing_terminal_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / MT4FileBridge.HEARTBEAT
            p.write_text(f"252031952|Alpari-Pro.ECN-Demo|1|XAUUSD|2000|2000.2|{int(time.time())}", encoding="utf-8")
            self.assertIsNone(MT4FileBridge(td).heartbeat())

    def test_invalid_demo_flag_never_becomes_demo(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / MT4FileBridge.HEARTBEAT
            p.write_text("252031952|Alpari-Pro.ECN-Demo|TRUE|XAUUSD|2000|2000.2|9999999999", encoding="utf-8")
            self.assertIsNone(MT4FileBridge(td).heartbeat())

    def test_stale_heartbeat_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            self.write_hb(Path(td), "252031952", "Alpari-Pro.ECN-Demo", "1", int(time.time()) - 60)
            self.assertIsNone(MT4FileBridge(td).heartbeat(max_age_seconds=10))

    def test_real_signal_heartbeat_is_not_accepted_as_demo(self):
        with tempfile.TemporaryDirectory() as td:
            self.write_hb(Path(td), "143056202", "Alpari-Pro.ECN", "0")
            hb = MT4FileBridge(td).heartbeat()
            self.assertIsNotNone(hb)
            self.assertEqual(hb["terminal_path"], r"C:\\MT4Demo")
            self.assertFalse(hb["is_demo"])
            self.assertNotEqual(hb["login"], MetaTraderSafetyGate.MT4_DEMO_ACCOUNT)

    def test_mt4_demo_role_requires_exact_demo_account_and_server(self):
        self.assertTrue(
            MetaTraderSafetyGate.verify_operation(
                "MT4", "DEMO",
                MetaTraderSafetyGate.MT4_DEMO_ACCOUNT,
                MetaTraderSafetyGate.MT4_DEMO_SERVER,
            )
        )
        with self.assertRaises(ValidationException):
            MetaTraderSafetyGate.verify_operation(
                "MT4", "DEMO",
                MetaTraderSafetyGate.MT4_LIVE_ACCOUNT,
                MetaTraderSafetyGate.MT4_LIVE_SERVER,
            )

    def test_live_roles_remain_hard_blocked(self):
        for role in ("REAL_LIVE", "LIVE_MT4", "LIVE_MT5"):
            with self.assertRaises(ValidationException):
                MetaTraderSafetyGate.verify_operation("MT4", role)
