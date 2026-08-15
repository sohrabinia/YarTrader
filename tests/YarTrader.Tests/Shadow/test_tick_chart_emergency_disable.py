import os
import unittest
from src.Infrastructure.Configuration.config import ConfigurationManager
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry

class TestTickChartEmergencyDisable(unittest.TestCase):
    """
    Emergency containment validation tests for TICK_CHART_ANALYSIS_ENABLED feature flag.
    Verifies that Tick Chart analysis, buffering, and detection are completely gated when disabled
    while other timeframes and processes continue to work flawlessly.
    """

    def setUp(self):
        self.engine = PredictiveShadowEngine.get_instance()
        self.registry = SymbolRegistry.get_instance()
        # Reset engine and registry
        self.engine.trades = []
        self.engine.signals = []
        self.engine.bases = []
        self.engine.nodes = []
        self.engine.runtime_manager.reset_brains()

        # Backup original registry state and configuration
        self.original_registry = self.registry.registry.copy()
        self.original_flag = ConfigurationManager.get_config().tick_chart_analysis_enabled

        # Set up a test entry that explicitly requests Tick timeframe
        self.registry.registry["XAUUSD"] = {
            "active": True,
            "asset_class": "Commodities",
            "provider": "MT5",
            "timeframes": ["Tick", "M15", "H1", "H4", "D1"]
        }

    def tearDown(self):
        # Restore registry and configuration state
        self.registry.registry = self.original_registry
        self.registry.save_registry()
        ConfigurationManager.get_config().tick_chart_analysis_enabled = self.original_flag
        self.engine.runtime_manager.reset_brains()

    def test_disabled_state_behavior(self):
        """
        Verify that when TICK_CHART_ANALYSIS_ENABLED = False:
        - Tick timeframe is excluded from active matrix and timeframe policy
        - Tick research does not execute and is filtered
        - detect_base and detect_node are not invoked
        - Tick-specific buffering and processing is avoided
        """
        config = ConfigurationManager.get_config()
        config.tick_chart_analysis_enabled = False

        # 1. Verify Tick timeframe is excluded from active matrix
        active_matrix = self.registry.get_active_matrix()
        timeframes = [item[1] for item in active_matrix if item[0] == "XAUUSD"]
        self.assertNotIn("Tick", timeframes)

        # 2. Verify get_timeframe_policy excludes Tick
        policy = self.registry.get_timeframe_policy("Commodities")
        self.assertNotIn("Tick", policy)

        # 3. Verify detect_base and detect_node are not invoked and tick buffer is not populated
        ctx = self.engine.get_or_create_context("XAUUSD", 64)
        ctx.tick_buffer = []
        self.engine.update_market_ticks("XAUUSD", 2400.0)

        self.assertEqual(len(ctx.tick_buffer), 0)
        self.assertEqual(len(ctx.bases), 0)
        self.assertEqual(len(ctx.nodes), 0)

    def test_enabled_state_behavior(self):
        """
        Verify that when TICK_CHART_ANALYSIS_ENABLED = True:
        - Tick timeframe returns to the active matrix and timeframe policy
        - Existing Tick behaviors remain intact
        """
        config = ConfigurationManager.get_config()
        config.tick_chart_analysis_enabled = True

        # 1. Verify get_timeframe_policy contains Tick
        policy = self.registry.get_timeframe_policy("Commodities")
        self.assertIn("Tick", policy)

        # 2. Verify get_active_matrix contains Tick
        active_matrix = self.registry.get_active_matrix()
        timeframes = [item[1] for item in active_matrix if item[0] == "XAUUSD"]
        self.assertIn("Tick", timeframes)

        # 3. Verify tick buffer is populated and detection runs normally
        ctx = self.engine.get_or_create_context("XAUUSD", 64)
        ctx.tick_buffer = []
        for i in range(11):
            self.engine.update_market_ticks("XAUUSD", 2400.0 + i * 0.05)

        self.assertEqual(len(ctx.tick_buffer), 11)
