import os
import unittest
import queue
from datetime import datetime
from fastapi.testclient import TestClient

from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.Application.Services.web_dashboard import app, global_auth_service

class TestCognitiveTopologySaaS(unittest.TestCase):
    """
    Standard SRE test suite for the Multi-Asset & Multi-Timeframe Cognitive Engine (v8.0).
    Ensures absolute isolated brain environments and safe decision fusions.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.engine = PredictiveShadowEngine.get_instance()
        self.engine.contexts = {}
        self.engine.trades = []
        self.engine.signals = []

        # Clear mock sessions
        global_auth_service.active_sessions = {}

    def test_one_hundred_fifty_isolated_engines(self) -> None:
        # Register 30 active symbols
        # For every symbol, 5 timeframe contexts are automatically instantiated
        # 30 x 5 = 150 independent SCM contexts
        for i in range(1, 31):
            symbol = f"ASSET{i}"
            self.engine.runtime_manager.get_or_create_symbol_hierarchy(symbol)

        # Confirm 30 active symbols registered
        self.assertEqual(len(self.engine.runtime_manager.symbol_brains), 30)

        # Confirm 150 contexts exist
        total_contexts = sum(len(frames) for frames in self.engine.runtime_manager.symbol_brains.values())
        self.assertEqual(total_contexts, 150)

    def test_decision_fusion_logic_alignment(self) -> None:
        # Setup multi-timeframe trades on Gold (XAUUSD)
        # Frame 4 (Short): LONG trade
        self.engine.create_predictive_order(
            symbol="XAUUSD", direction="LONG", entry=2000.0, stop=1990.0, target=2020.0, confidence=80.0, custom_time_structure=4
        )
        self.engine.update_market_ticks("XAUUSD", 2001.0) # trigger

        # Frame 256 (Macro): LONG trade
        self.engine.create_predictive_order(
            symbol="XAUUSD", direction="LONG", entry=2000.0, stop=1990.0, target=2020.0, confidence=90.0, custom_time_structure=256
        )
        self.engine.update_market_ticks("XAUUSD", 2001.0) # trigger

        # Fetch Decision Fusion Signal
        resp = self.client.get("/api/user/fusion/XAUUSD")
        self.assertEqual(resp.status_code, 200)
        fusion = resp.json()

        self.assertEqual(fusion["symbol"], "XAUUSD")
        self.assertEqual(fusion["action"], "LONG")
        self.assertGreater(fusion["confidence"], 50.0)
        self.assertIn("Frame 4 Bullish", fusion["reason"])
        self.assertIn("Frame 256 Bullish", fusion["reason"])

    def test_absolute_memory_and_stats_isolation(self) -> None:
        # Create context shadow trades
        t1 = self.engine.create_predictive_order("EURUSD", "LONG", 1.1000, 1.0900, 1.1100, 80.0, custom_time_structure=16)
        t2 = self.engine.create_predictive_order("EURUSD", "SHORT", 1.0500, 1.0600, 1.0400, 75.0, custom_time_structure=64)

        # EURUSD Frame 16 gets WIN
        self.engine.update_market_ticks("EURUSD", 1.1010)
        self.engine.update_market_ticks("EURUSD", 1.1150) # target hit

        # Check separate context statistics
        ctx_16 = self.engine.contexts["EURUSD_16"]
        ctx_64 = self.engine.contexts["EURUSD_64"]

        stats_16 = ctx_16.get_statistics()
        stats_64 = ctx_64.get_statistics()

        # Frame 16 statistics
        self.assertEqual(stats_16["completed_trades"], 1)
        self.assertEqual(stats_16["wins"], 1)
        self.assertEqual(stats_16["win_rate_pct"], 100.0)

        # Frame 64 statistics must remain completely untouched (isolated)
        self.assertEqual(stats_64["completed_trades"], 0)
        self.assertEqual(stats_64["wins"], 0)
        self.assertEqual(stats_64["win_rate_pct"], 0.0)

    def test_backpressure_and_queue_safety(self) -> None:
        # Register a symbol and push tick updates
        self.engine.runtime_manager.get_or_create_symbol_hierarchy("XAUUSD")

        # Test direct SRE backpressure and sliding window queue dropping
        q = self.engine.runtime_manager.processing_queues["XAUUSD"]
        # Fill queue to maximum capacity
        for i in range(1000):
            q.put({"price": 2000.0, "timestamp": datetime.now()})

        self.assertTrue(q.full())

        # Queueing another tick must slide successfully without throwing full error (handled by non-blocking fallback)
        self.engine.runtime_manager.queue_tick_update("XAUUSD", 2005.0)
        self.assertTrue(q.full())
