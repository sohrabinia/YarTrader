import os
import unittest
import threading
from fastapi.testclient import TestClient

from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.Application.Services.web_dashboard import app, global_auth_service

class TestMultiAssetMultiResolutionCognitive(unittest.TestCase):
    """
    Enterprise-grade test cases for TradeYar AI v3.3.
    Enforces strict Multi-Asset & Multi-Resolution isolated cognitive context rules.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.engine = PredictiveShadowEngine.get_instance()
        # Reset engine contexts, active trades and signals
        self.engine.contexts = {}
        self.engine.trades = []
        self.engine.signals = []
        self.engine.bases = []
        self.engine.nodes = []
        self.engine.patterns = []
        self.engine.learning = []

        # Clear mock sessions
        global_auth_service.active_sessions = {}

    # Test 1: Multi-symbol concurrent execution
    def test_multi_symbol_concurrent_execution(self) -> None:
        # Create trades concurrently on XAUUSD, BTCUSD, and EURUSD
        t1 = self.engine.create_predictive_order("XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0, custom_time_structure=64)
        t2 = self.engine.create_predictive_order("BTCUSD", "SHORT", 60000.0, 61000.0, 58000.0, 85.0, custom_time_structure=64)
        t3 = self.engine.create_predictive_order("EURUSD", "LONG", 1.1000, 1.0900, 1.1200, 75.0, custom_time_structure=64)

        self.assertEqual(len(self.engine.trades), 3)
        self.assertEqual(t1.symbol, "XAUUSD")
        self.assertEqual(t2.symbol, "BTCUSD")
        self.assertEqual(t3.symbol, "EURUSD")

        # Verify contexts are created independently
        self.assertIn("XAUUSD_64", self.engine.contexts)
        self.assertIn("BTCUSD_64", self.engine.contexts)
        self.assertIn("EURUSD_64", self.engine.contexts)

    # Test 2: Multi-timeframe execution per symbol
    def test_multi_timeframe_execution_per_symbol(self) -> None:
        # Gold on Frames 4, 16, 64, 256
        self.engine.create_predictive_order("XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0, custom_time_structure=4)
        self.engine.create_predictive_order("XAUUSD", "SHORT", 2010.0, 2020.0, 1990.0, 75.0, custom_time_structure=16)
        self.engine.create_predictive_order("XAUUSD", "LONG", 2005.0, 1995.0, 2025.0, 82.0, custom_time_structure=64)
        self.engine.create_predictive_order("XAUUSD", "SHORT", 2015.0, 2025.0, 1995.0, 78.0, custom_time_structure=256)

        self.assertIn("XAUUSD_4", self.engine.contexts)
        self.assertIn("XAUUSD_16", self.engine.contexts)
        self.assertIn("XAUUSD_64", self.engine.contexts)
        self.assertIn("XAUUSD_256", self.engine.contexts)

        self.assertEqual(len(self.engine.contexts["XAUUSD_4"].trades), 1)
        self.assertEqual(len(self.engine.contexts["XAUUSD_256"].trades), 1)

    # Test 3: Memory isolation (no cross-contamination)
    def test_memory_isolation_btc_gold(self) -> None:
        # Create Gold trade and close it as STOP_HIT (losses/failure)
        gold_trade = self.engine.create_predictive_order("XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0, custom_time_structure=64)
        self.engine.update_market_ticks("XAUUSD", 2001.0) # trigger
        self.engine.update_market_ticks("XAUUSD", 1985.0) # stop hit

        # Create BTC trade and close it as TARGET_HIT (success)
        btc_trade = self.engine.create_predictive_order("BTCUSD", "SHORT", 60000.0, 61000.0, 58000.0, 85.0, custom_time_structure=256)
        self.engine.update_market_ticks("BTCUSD", 59990.0) # trigger
        self.engine.update_market_ticks("BTCUSD", 57500.0) # target hit

        # Check isolated context lists
        gold_ctx = self.engine.contexts["XAUUSD_64"]
        btc_ctx = self.engine.contexts["BTCUSD_256"]

        # Gold should only have its learning history
        self.assertEqual(len(gold_ctx.learning), 1)
        self.assertFalse(gold_ctx.learning[0]["success"])

        # BTC should only have its learning history
        self.assertEqual(len(btc_ctx.learning), 1)
        self.assertTrue(btc_ctx.learning[0]["success"])

    # Test 4: Separate reporting per timeframe
    def test_separate_reporting_per_timeframe(self) -> None:
        # Gold Frame 4 has win
        t1 = self.engine.create_predictive_order("XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0, custom_time_structure=4)
        self.engine.update_market_ticks("XAUUSD", 2001.0)
        self.engine.update_market_ticks("XAUUSD", 2025.0)

        # Gold Frame 64 has loss
        t2 = self.engine.create_predictive_order("XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0, custom_time_structure=64)
        self.engine.update_market_ticks("XAUUSD", 2001.0)
        self.engine.update_market_ticks("XAUUSD", 1985.0)

        # Query Admin Reports API
        resp = self.client.get("/api/admin/reports?symbol=XAUUSD")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Since v8.0 instantiates the 5 default timeframe contexts (1, 4, 16, 64, 256) per active symbol
        self.assertEqual(data["count"], 5)

        reports = data["reports"]
        # Find frame 4 report
        rep_4 = next((r for r in reports if r["timeframe"] == "4"), None)
        # Find frame 64 report
        rep_64 = next((r for r in reports if r["timeframe"] == "64"), None)

        self.assertIsNotNone(rep_4)
        self.assertIsNotNone(rep_64)

        self.assertEqual(rep_4["wins"], 1)
        self.assertEqual(rep_4["losses"], 0)
        self.assertEqual(rep_4["win_rate_pct"], 100.0)

        self.assertEqual(rep_64["wins"], 0)
        self.assertEqual(rep_64["losses"], 1)
        self.assertEqual(rep_64["win_rate_pct"], 0.0)

    # Test 5: Route separation
    def test_route_separation_rules(self) -> None:
        # Query User Markets
        user_resp = self.client.get("/api/user/markets")
        self.assertEqual(user_resp.status_code, 200)
        self.assertEqual(len(user_resp.json()), 4)

        # Query Admin Symbols without token (fails in real settings, but check check_admin_guard block)
        # Create regular user token
        user_token = global_auth_service.create_session({"email": "trader@tradeyar.ai", "role": "USER"})
        admin_resp = self.client.get(f"/api/admin/symbols?token={user_token}")
        self.assertEqual(admin_resp.status_code, 403)

    # Test 6: Enforcement of the 30 active symbols limit
    def test_thirty_active_symbols_limit_enforced(self) -> None:
        # Attempt to create contexts for 31 unique symbols
        # Default limit is 30
        for i in range(1, 31):
            symbol_name = f"SYM{i}"
            self.engine.create_predictive_order(symbol_name, "LONG", 10.0, 9.0, 12.0, 80.0, custom_time_structure=64)

        # The 31st unique symbol creation MUST raise ValueError
        with self.assertRaises(ValueError):
            self.engine.create_predictive_order("SYM31", "LONG", 10.0, 9.0, 12.0, 80.0, custom_time_structure=64)

    # Test 7: Concurrent requests handling
    def test_concurrent_multi_user_requests(self) -> None:
        # Spawn multiple threads sending queries concurrently
        results = []

        def worker(sym, tf):
            try:
                t = self.engine.create_predictive_order(sym, "LONG", 100.0, 90.0, 110.0, 75.0, custom_time_structure=tf)
                results.append(t)
            except Exception as e:
                results.append(e)

        threads = []
        # Create 10 threads working concurrently on different contexts
        for i in range(10):
            sym = f"CONC{i}"
            t = threading.Thread(target=worker, args=(sym, 64))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(results), 10)
        for res in results:
            self.assertNotIsInstance(res, Exception)
            self.assertEqual(res.status, "CREATED")
