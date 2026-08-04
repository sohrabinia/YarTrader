import os
import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.ShadowTrading.Engine.TimeEngine import CustomTimeEngine
from src.ShadowTrading.Engine.BehaviorEngine import MarketBehaviorEngine
from src.ShadowTrading.Engine.BaseNodeDetector import BaseNodeDetector, BaseStructure, NodeStructure
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine, ShadowTrade
from src.Application.Services.web_dashboard import app

class TestAutonomousShadowTradingEngine(unittest.TestCase):
    """
    Standard Engineering test cases for the Autonomous Shadow Trading Engine (v3.2).
    Verifies pure mathematical/tick structures, predictive orders, and admin/user separation rules.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.engine = PredictiveShadowEngine.get_instance()
        # Reset local data structures to start clean
        self.engine.trades = []
        self.engine.signals = []
        self.engine.bases = []
        self.engine.nodes = []
        self.engine.patterns = []
        self.engine.learning = []
        self.engine.runtime_manager.symbol_brains = {}
        self.engine.runtime_manager.processing_queues = {}

    # Test 1: Tick data creates custom timeframes
    def test_tick_data_creates_custom_timeframes(self) -> None:
        ticks = [
            {"price": 2000.0 + i * 0.1, "timestamp": (datetime.now() + timedelta(seconds=i)).isoformat()}
            for i in range(10)
        ]
        engine = CustomTimeEngine(target_sizes=[1, 4])
        structures = engine.build_structures(ticks)

        self.assertIn(1, structures)
        self.assertIn(4, structures)
        self.assertEqual(len(structures[4]), 3)  # 10 / 4 = 2 full structures of size 4 + 1 partial structure of size 2

        first_bar = structures[4][0]
        self.assertEqual(first_bar.tick_count, 4)
        self.assertGreater(first_bar.duration, 0.0)
        self.assertGreater(first_bar.price_range, 0.0)
        self.assertEqual(first_bar.movement_behavior, "EXPANSION_UP")

    # Test 2: Virtual order created before price arrival
    def test_virtual_order_created_before_price_arrival(self) -> None:
        # Create order with entry at 2354 while "current" tick price is 2350
        trade = self.engine.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=2354.0,
            stop=2342.0,
            target=2368.0,
            confidence=78.0,
            reason="Market Structure Expansion"
        )

        self.assertEqual(trade.status, "CREATED")
        self.assertEqual(trade.entry, 2354.0)

        # Simulating tick updates below entry price (should not trigger)
        self.engine.update_market_ticks("XAUUSD", 2351.0)
        self.assertEqual(trade.status, "CREATED")

        # Simulating tick reaching or exceeding entry (should trigger)
        self.engine.update_market_ticks("XAUUSD", 2354.5)
        self.assertEqual(trade.status, "RUNNING")

    # Test 3: Shadow lifecycle works
    def test_shadow_lifecycle_works(self) -> None:
        trade = self.engine.create_predictive_order(
            symbol="XAUUSD",
            direction="SHORT",
            entry=2000.0,
            stop=2010.0,
            target=1980.0,
            confidence=70.0
        )
        self.assertEqual(trade.status, "CREATED")

        # Trigger Order -> RUNNING
        self.engine.update_market_ticks("XAUUSD", 1999.0)
        self.assertEqual(trade.status, "RUNNING")

        # Hit target
        self.engine.update_market_ticks("XAUUSD", 1978.0)
        self.assertEqual(trade.status, "TARGET_HIT")
        self.assertEqual(trade.result, "TARGET_HIT")

    # Test 4: Judge updates memory
    def test_judge_updates_memory(self) -> None:
        trade = self.engine.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=2000.0,
            stop=1990.0,
            target=2020.0,
            confidence=80.0
        )

        # Trigger
        self.engine.update_market_ticks("XAUUSD", 2001.0)

        # Close via stop hit
        self.engine.update_market_ticks("XAUUSD", 1985.0)
        self.assertEqual(trade.status, "STOP_HIT")

        # Check if patterns and learning memories were added to PredictiveShadowEngine lists
        self.assertGreater(len(self.engine.patterns), 0)
        self.assertGreater(len(self.engine.learning), 0)

        # Check learning record contents
        learn_rec = self.engine.learning[-1]
        self.assertEqual(learn_rec["trade_id"], trade.trade_id)
        self.assertFalse(learn_rec["success"])
        self.assertEqual(learn_rec["confidence_shift"], -0.05)

    # Test 5: User signal matches Shadow Trade ID
    def test_user_signal_matches_shadow_trade_id(self) -> None:
        trade = self.engine.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=2000.0,
            stop=1990.0,
            target=2010.0,
            confidence=85.0
        )

        self.assertEqual(len(self.engine.signals), 1)
        sig = self.engine.signals[0]
        self.assertEqual(sig["shadow_trade_id"], trade.trade_id)
        self.assertEqual(sig["entry_zone"], 2000.0)
        self.assertEqual(sig["invalidation_level"], 1990.0)

    # Test 6: Admin API exposes full data
    def test_admin_api_exposes_full_data(self) -> None:
        self.engine.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=2000.0,
            stop=1990.0,
            target=2010.0,
            confidence=85.0,
            reason="Compression Breakout",
            custom_time_structure=256,
            pattern="Base Compression Shift"
        )

        response = self.client.get("/api/admin/shadow-trades")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data), 1)
        trade = data[0]
        # Admin fields MUST be present
        self.assertIn("trade_id", trade)
        self.assertIn("custom_time_structure", trade)
        self.assertIn("mae", trade)
        self.assertIn("mfe", trade)
        self.assertIn("base_id", trade)
        self.assertIn("node_id", trade)
        self.assertIn("pattern", trade)
        self.assertEqual(trade["custom_time_structure"], 256)

    # Test 7: User API hides internal data
    def test_user_api_hides_internal_data(self) -> None:
        self.engine.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=2000.0,
            stop=1990.0,
            target=2010.0,
            confidence=85.0,
            reason="Compression Breakout",
            custom_time_structure=256,
            pattern="Base Compression Shift"
        )

        response = self.client.get("/api/user/signals")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data), 1)
        signal = data[0]

        # User exposed clean fields
        self.assertIn("signal_id", signal)
        self.assertIn("symbol", signal)
        self.assertIn("direction", signal)
        self.assertIn("entry_zone", signal)
        self.assertIn("invalidation_level", signal)
        self.assertIn("target_zone", signal)
        self.assertIn("confidence", signal)
        self.assertIn("reason", signal)
        self.assertIn("status", signal)

        # Forbidden fields for User (MUST NOT be exposed)
        self.assertNotIn("mae", signal)
        self.assertNotIn("mfe", signal)
        self.assertNotIn("custom_time_structure", signal)
        self.assertNotIn("base_id", signal)
        self.assertNotIn("node_id", signal)
        self.assertNotIn("pattern", signal)
        self.assertNotIn("raw_ticks", signal)
        self.assertNotIn("learning_weights", signal)

    # Test 8: No indicators exist
    def test_no_indicators_exist(self) -> None:
        # Scan BehaviorEngine to verify no classical indicators exist
        behavior = MarketBehaviorEngine()

        # Ensure no standard functions or variables exist
        for prop in dir(behavior):
            self.assertNotIn("rsi", prop.lower())
            self.assertNotIn("macd", prop.lower())
            self.assertNotIn("ema", prop.lower())
            self.assertNotIn("sma", prop.lower())
            self.assertNotIn("moving_average", prop.lower())
            self.assertNotIn("bollinger", prop.lower())
            self.assertNotIn("stochastic", prop.lower())
            self.assertNotIn("atr", prop.lower())

    # Test 9: No MT5 timeframe dependency
    def test_no_mt5_timeframe_dependency(self) -> None:
        # Custom timeframes must be integer-based tick bundles
        engine = CustomTimeEngine()
        # Verify sizes are entirely custom integer ticks rather than MT5 constants (like MT5_TIMEFRAME_M1)
        for ts in engine.target_sizes:
            self.assertIsInstance(ts, int)
            self.assertNotIn(ts, [16385, 16386, 16387, 16388]) # Standard MT5 timeframe constant values

    # Test 10: Regression test for trade.evidence = None guard check
    def test_regression_trade_evidence_none(self) -> None:
        # Create a trade with evidence explicitly set to None
        trade = self.engine.create_predictive_order(
            symbol="XAUUSD",
            direction="LONG",
            entry=2000.0,
            stop=1990.0,
            target=2010.0,
            confidence=85.0,
            reason="Regression Test None Evidence"
        )
        trade.evidence = None

        # Trigger RUNNING state
        self.engine.update_market_ticks("XAUUSD", 2001.0)

        # Trigger STOP_HIT closing state, which invokes _record_pattern_outcome_context
        try:
            self.engine.update_market_ticks("XAUUSD", 1985.0)
        except AttributeError as e:
            self.fail(f"PredictiveShadowEngine regression occurred: trade.evidence=None raised AttributeError: {e}")

        # Assert status transitioned correctly and is not crashed
        self.assertEqual(trade.status, "STOP_HIT")
        self.assertGreater(len(self.engine.patterns), 0)
