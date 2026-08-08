import os
import unittest
from unittest.mock import patch
from src.Infrastructure.Configuration.config import ConfigurationManager
from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry, REGISTRY_FILE
from src.ShadowTrading.Engine.SymbolRuntimeManager import SymbolRuntimeManager
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine

class TestTickDisablement(unittest.TestCase):
    def setUp(self) -> None:
        ConfigurationManager.reset()
        if os.path.exists(REGISTRY_FILE):
            os.remove(REGISTRY_FILE)
        SymbolRegistry._instance = None
        self.registry = SymbolRegistry.get_instance()

    def tearDown(self) -> None:
        ConfigurationManager.reset()
        if os.path.exists(REGISTRY_FILE):
            os.remove(REGISTRY_FILE)
        SymbolRegistry._instance = None

    @patch.dict(os.environ, {"TICK_CHART_ANALYSIS_ENABLED": "False"})
    def test_tick_disabled_default(self) -> None:
        """Verify that when TICK_CHART_ANALYSIS_ENABLED is False (or absent), Tick path is completely disabled."""
        config = ConfigurationManager.get_config()
        self.assertFalse(config.tick_chart_analysis_enabled)

        # Timeframe policy should not return "Tick"
        tfs = self.registry.get_timeframe_policy("Forex")
        self.assertNotIn("Tick", tfs)

        # Active matrix should not contain "Tick"
        self.registry.registry = {}
        self.registry.register_symbol("TESTSYM", ["Tick", "M15"])
        matrix = self.registry.get_active_matrix()
        for symbol, tf, asset_class, provider in matrix:
            self.assertNotEqual(tf, "Tick")

        # SymbolRuntimeManager should filter out "Tick"
        manager = SymbolRuntimeManager()
        # Mock sys.modules check or environment testing check to simulate production setup
        with patch("sys.modules", {}), patch.dict(os.environ, {"TESTING": "False"}):
            brains = manager.get_or_create_symbol_hierarchy("EURUSD")
            self.assertNotIn("Tick", brains)

    @patch.dict(os.environ, {"TICK_CHART_ANALYSIS_ENABLED": "True"})
    def test_tick_enabled_explicit(self) -> None:
        """Verify that when TICK_CHART_ANALYSIS_ENABLED is True, Tick path becomes fully operational again."""
        config = ConfigurationManager.get_config()
        self.assertTrue(config.tick_chart_analysis_enabled)

        # Timeframe policy should return "Tick"
        tfs = self.registry.get_timeframe_policy("Forex")
        self.assertIn("Tick", tfs)

        # Active matrix should contain "Tick"
        self.registry.registry = {}
        self.registry.register_symbol("TESTSYM", ["Tick", "M15"])
        matrix = self.registry.get_active_matrix()
        has_tick = any(tf == "Tick" for symbol, tf, asset_class, provider in matrix)
        self.assertTrue(has_tick)

        # SymbolRuntimeManager should keep "Tick"
        manager = SymbolRuntimeManager()
        with patch("sys.modules", {}), patch.dict(os.environ, {"TESTING": "False"}):
            brains = manager.get_or_create_symbol_hierarchy("EURUSD")
            self.assertIn("Tick", brains)
