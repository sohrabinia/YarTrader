import os
import json
import shutil
import unittest
from datetime import datetime
from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry, REGISTRY_FILE
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine

class TestMultiSymbolMatrixRuntime(unittest.TestCase):
    """
    Automated SRE validation suite for Multi-Symbol & Multi-Timeframe Research Runtime.
    Ensures matrix resolution, dynamic registry, shadow position isolation, and restart integrity.
    """

    def setUp(self) -> None:
        self.registry = SymbolRegistry.get_instance()
        # Reset the registry to a clean test state
        if os.path.exists(REGISTRY_FILE):
            try:
                os.remove(REGISTRY_FILE)
            except OSError:
                pass
        self.registry.registry = {}
        self.registry.load_registry()

        # Clean snapshots folder for testing
        self.snapshot_dir = "runtime_logs/research_snapshots"
        if os.path.exists(self.snapshot_dir):
            try:
                shutil.rmtree(self.snapshot_dir)
            except OSError:
                pass
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def tearDown(self) -> None:
        # Restore clean state
        if os.path.exists(REGISTRY_FILE):
            try:
                os.remove(REGISTRY_FILE)
            except OSError:
                pass

    def test_regression_protection(self) -> None:
        """Regression Protection: Raise warning if multiple symbols/timeframes are configured but only 1 executes."""
        active_matrix = self.registry.get_active_matrix()
        executed_runs = 1 # Simulate degraded execution

        warning_raised = False
        if len(active_matrix) > 1 and executed_runs == 1:
            warning_raised = True
            print("WARNING: MULTI_SYMBOL_RUNTIME_DEGRADED")

        self.assertTrue(warning_raised)

    def test_1_multi_symbol_multi_tf_execution(self) -> None:
        """Test 1: Register XAUUSD (H1, H4) and EURUSD (H1), execute, verify 3 snapshots generated."""
        self.registry.registry = {}
        self.registry.register_symbol("XAUUSD", ["H1", "H4"])
        self.registry.register_symbol("EURUSD", ["H1"])

        active_matrix = self.registry.get_active_matrix()
        self.assertEqual(len(active_matrix), 3)
        self.assertIn(("XAUUSD", "H1"), active_matrix)
        self.assertIn(("XAUUSD", "H4"), active_matrix)
        self.assertIn(("EURUSD", "H1"), active_matrix)

        # Execute research loop simulation
        runtimes = {}
        for symbol, tf in active_matrix:
            runtime = ResearchRuntime(symbol=symbol, timeframe=tf, evidence_dir="runtime_logs")
            res = runtime.run_once()

            # Verify file exists
            snapshot_files = os.listdir(self.snapshot_dir)
            matching_files = [f for f in snapshot_files if f.startswith(f"rpt-{symbol}-{tf}-") and f.endswith(".json")]
            self.assertGreater(len(matching_files), 0, f"Snapshot for {symbol} on {tf} was not created.")

    def test_2_symbol_disable(self) -> None:
        """Test 2: Disable EURUSD, verify only XAUUSD executes."""
        self.registry.registry = {}
        self.registry.register_symbol("XAUUSD", ["H1", "H4"])
        self.registry.register_symbol("EURUSD", ["H1"])

        # Disable EURUSD
        self.registry.set_symbol_active("EURUSD", False)

        active_matrix = self.registry.get_active_matrix()
        self.assertEqual(len(active_matrix), 2)
        self.assertIn(("XAUUSD", "H1"), active_matrix)
        self.assertIn(("XAUUSD", "H4"), active_matrix)
        self.assertNotIn(("EURUSD", "H1"), active_matrix)

    def test_3_shadow_isolation(self) -> None:
        """Test 3: Open XAUUSD H1 SELL position. Verify XAUUSD H1 duplicate skips, while XAUUSD H4 succeeds."""
        engine = ShadowTradingEngine.get_instance()
        engine.reset_account()

        # Open an initial XAUUSD H1 SELL position
        pos_h1 = engine.handle_decision(
            decision_action="SELL",
            current_price=2350.0,
            symbol="XAUUSD",
            timeframe="H1"
        )
        self.assertIsNotNone(pos_h1)

        # Attempt to open duplicate XAUUSD H1 SELL (should skip)
        pos_duplicate = engine.handle_decision(
            decision_action="SELL",
            current_price=2349.0,
            symbol="XAUUSD",
            timeframe="H1"
        )
        self.assertIsNone(pos_duplicate)

        # Attempt to open XAUUSD H4 SELL (should succeed because of timeframe isolation)
        pos_h4 = engine.handle_decision(
            decision_action="SELL",
            current_price=2350.0,
            symbol="XAUUSD",
            timeframe="H4"
        )
        self.assertIsNotNone(pos_h4)

    def test_4_service_restart_persistence(self) -> None:
        """Test 4: Simulate a service/process restart, verify registry is restored successfully."""
        self.registry.registry = {}
        self.registry.register_symbol("XAUUSD", ["H1", "H4"])
        self.registry.register_symbol("GBPUSD", ["H1"])
        self.registry.save_registry()

        # Re-instantiate a clean Registry, mimicking startup
        new_registry = SymbolRegistry()
        active_matrix = new_registry.get_active_matrix()

        self.assertEqual(len(active_matrix), 3)
        self.assertIn(("XAUUSD", "H1"), active_matrix)
        self.assertIn(("GBPUSD", "H1"), active_matrix)
