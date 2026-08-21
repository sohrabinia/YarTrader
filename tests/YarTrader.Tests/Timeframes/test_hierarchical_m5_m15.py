import os
import json
import uuid
import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Research.Brain.multi_timeframe import MultiTimeframePerception
from src.Research.Brain.models import MarketObservation
from src.Intelligence.Execution.alignment import MultiTimeframeAlignmentEngine
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine, ShadowTrade


class TestHierarchicalM5M15Trading(unittest.TestCase):
    """
    Automated integration and unit tests validating the 9-layer Hierarchical
    Multi-Timeframe Market Brain and M5/M15 Trading Intelligence Platform.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.symbol = "XAUUSD"
        self.perception = MultiTimeframePerception(symbol=self.symbol)
        self.alignment_engine = MultiTimeframeAlignmentEngine()
        self.shadow_engine = PredictiveShadowEngine.get_instance()

    def test_nine_timeframe_ingestion(self) -> None:
        """
        1. Validate multi-timeframe perception can handle ingestion of all 9 resolutions.
        Verify fractal relationships mapping can be mapped cleanly across these resolutions.
        """
        timeframes = ["Tick", "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]
        observations_by_tf = {}
        base_time = datetime(2026, 8, 4, 12, 0, 0)

        # Generate fake overlapping observations for each timeframe
        for tf in timeframes:
            observations_by_tf[tf] = [
                MarketObservation(
                    symbol=self.symbol,
                    timeframe=tf,
                    timestamp=base_time + timedelta(minutes=i),
                    high=2425.0,
                    low=2415.0,
                    open_price=2420.0,
                    close_price=2422.0 if i % 2 == 0 else 2418.0,
                    volume=100.0
                )
                for i in range(5)
            ]

        # Process fractal relationships
        relationships = self.perception.map_fractal_relationships(observations_by_tf)
        self.assertIsNotNone(relationships)

        # Verify the hierarchical context is generated perfectly
        hier_context = self.perception.generate_hierarchical_context(
            symbol=self.symbol,
            observations_by_tf=observations_by_tf,
            timestamp=base_time
        )
        self.assertEqual(hier_context["symbol"], "XAUUSD")
        self.assertIn("macro_bias", hier_context)
        self.assertIn("regime_and_structure", hier_context)
        self.assertIn("primary_decision", hier_context)
        self.assertIn("primary_execution", hier_context)
        self.assertIn("micro_confirmation", hier_context)

    def test_m15_setup_m5_trigger_alignment(self) -> None:
        """
        2. Validate M15 decision gate and M5 execution trigger logic.
        Ensure setups are NOT triggered without an active M15 setup,
        and verify confidence degradation under counter-trend HTFs.
        """
        # Scenario A: No M15 setup present (Trend is NEUTRAL)
        timeframe_narratives_no_setup = {
            "M15": {"trend": "NEUTRAL", "state": "RANGE"},
            "M5": {"trend": "BULLISH", "state": "TRENDING"},
            "H1": {"trend": "BULLISH", "state": "TRENDING"}
        }
        res_no_setup = self.alignment_engine.align_m15_m5_pipeline(
            symbol=self.symbol,
            timeframe_narratives=timeframe_narratives_no_setup,
            current_price=2420.0
        )
        self.assertEqual(res_no_setup["decision_action"], "WAIT")
        self.assertFalse(res_no_setup["setup_present"])
        self.assertIn("No M15 structure setup detected", res_no_setup["reason"])

        # Scenario B: M15 Setup is present, but M5 trigger confirmation does not match
        timeframe_narratives_no_m5_match = {
            "M15": {"trend": "BULLISH", "state": "TRENDING"},
            "M5": {"trend": "BEARISH", "state": "TRENDING"},
            "H1": {"trend": "BULLISH", "state": "TRENDING"}
        }
        res_no_m5_match = self.alignment_engine.align_m15_m5_pipeline(
            symbol=self.symbol,
            timeframe_narratives=timeframe_narratives_no_m5_match,
            current_price=2420.0
        )
        self.assertEqual(res_no_m5_match["decision_action"], "WAIT")
        self.assertTrue(res_no_m5_match["setup_present"])
        self.assertFalse(res_no_m5_match["trigger_confirmed"])

        # Scenario C: M15 Setup and M5 Trigger both confirm, but HTF runs counter-trend (re-multiplier check)
        timeframe_narratives_counter_trend = {
            "M15": {"trend": "BULLISH", "state": "TRENDING"},
            "M5": {"trend": "BULLISH", "state": "TRENDING"},
            "H1": {"trend": "BEARISH", "state": "TRENDING"},  # counter trend
            "H4": {"trend": "BEARISH", "state": "TRENDING"},  # counter trend
            "D1": {"trend": "BEARISH", "state": "TRENDING"}   # counter trend
        }
        res_counter_trend = self.alignment_engine.align_m15_m5_pipeline(
            symbol=self.symbol,
            timeframe_narratives=timeframe_narratives_counter_trend,
            current_price=2420.0
        )
        self.assertEqual(res_counter_trend["decision_action"], "BUY")
        self.assertTrue(res_counter_trend["setup_present"])
        self.assertTrue(res_counter_trend["trigger_confirmed"])
        # Base confidence is 75. Applying 3 counter-trend multipliers (0.70 each) degrades confidence to 75 * 0.7 * 0.7 * 0.7 = ~25.7%
        self.assertLess(res_counter_trend["confidence"], 30.0)
        self.assertIn("Counter-trend macro timeframes degraded overall confidence", res_counter_trend["reason"])

    def test_pattern_outcomes_logging(self) -> None:
        """
        3. Validate that completing trades records precise HierarchicalMarketContext details
        and updates pattern_outcomes.json.
        """
        # Create a predictive shadow order with mock hierarchical context inside evidence
        hier_ctx = {
            "macro_bias": {"D1": "Bullish", "H4": "Bullish"},
            "primary_decision": {"setup": "Long Reversal"},
            "primary_execution": {"trigger": "Breakout Confirmation"}
        }

        trade = self.shadow_engine.create_predictive_order(
            symbol=self.symbol,
            direction="LONG",
            entry=2420.0,
            stop=2410.0,
            target=2440.0,
            confidence=85.0,
            reason="M15 structure setup",
            custom_time_structure=5,
            evidence={"hierarchical_context": hier_ctx}
        )

        self.assertIsNotNone(trade.trade_id)
        self.assertEqual(trade.evidence["hierarchical_context"]["macro_bias"]["D1"], "Bullish")

        # Simulate price tick to trigger running and then hit take profit
        self.shadow_engine.update_market_ticks(self.symbol, 2420.5)
        self.assertEqual(trade.status, "RUNNING")

        # Hit Take Profit target
        self.shadow_engine.update_market_ticks(self.symbol, 2445.0)
        self.assertEqual(trade.status, "TARGET_HIT")

        # Check if the outcome was logged in pattern_outcomes.json
        self.assertTrue(os.path.exists(self.shadow_engine.patterns_file))
        with open(self.shadow_engine.patterns_file, "r") as f:
            patterns = json.load(f)

        matched = [p for p in patterns if p.get("trade_id") == trade.trade_id]
        self.assertEqual(len(matched), 1)
        logged_p = matched[0]
        self.assertEqual(logged_p["win_loss"], "Win")
        self.assertEqual(logged_p["macro_bias_d1"], "Bullish")
        self.assertEqual(logged_p["macro_bias_h4"], "Bullish")
        self.assertEqual(logged_p["m15_setup"], "Long Reversal")
        self.assertEqual(logged_p["m5_trigger"], "Breakout Confirmation")
        self.assertIn("historical_win_rate_pct", logged_p)

        # Check snapshot exists in TradeYarStorageRoot/Runtime/brain_memory/
        from src.Application.Deployment.storage import YarTraderStorageManager
        brain_memory_dir = os.path.join(YarTraderStorageManager.get_manager().get_runtime_dir(), "brain_memory")
        snapshot_filepath = os.path.join(brain_memory_dir, f"pattern_{trade.trade_id}.json")
        self.assertTrue(os.path.exists(snapshot_filepath))
        with open(snapshot_filepath, "r") as sf:
            sf_data = json.load(sf)
        self.assertEqual(sf_data["trade_id"], trade.trade_id)

    def test_api_multi_timeframe_endpoint(self) -> None:
        """
        4. Validate that GET /api/intelligence/multi-timeframe returns 200 and a valid matrix.
        """
        response = self.client.get("/api/intelligence/multi-timeframe")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("XAUUSD", data)
        xau_ctx = data["XAUUSD"]
        self.assertEqual(xau_ctx["symbol"], "XAUUSD")
        self.assertIn("macro_bias", xau_ctx)
        self.assertIn("primary_decision", xau_ctx)
        self.assertIn("primary_execution", xau_ctx)
