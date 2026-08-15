import unittest
from src.Core.timeframes import TimeframeNormalizer
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from scripts.run_phase_2_1_experiment import generate_deterministic_hash


class TestTimeframeNormalizerRegression(unittest.TestCase):
    """
    Regression tests for TimeframeNormalizer and PredictiveShadowEngine context creation
    as required by the Timeframe Contract Regression Fix Directive.
    """

    def setUp(self) -> None:
        self.engine = PredictiveShadowEngine.get_instance()
        # Reset local data structures to start clean
        self.engine.runtime_manager.symbol_brains = {}
        self.engine.runtime_manager.processing_queues = {}

    def test_tick_input_normalization(self) -> None:
        # Case 1: "Tick" input is normalized to "Tick" (string)
        self.assertEqual(TimeframeNormalizer.normalize("Tick"), "Tick")
        self.assertEqual(TimeframeNormalizer.normalize("tick"), "Tick")
        self.assertEqual(TimeframeNormalizer.normalize("TICK"), "Tick")

    def test_m1_input_normalization(self) -> None:
        # Case 2: "M1" input is normalized to "M1" (string)
        self.assertEqual(TimeframeNormalizer.normalize("M1"), "M1")
        self.assertEqual(TimeframeNormalizer.normalize("m1"), "M1")

    def test_integer_timeframe_input_normalization(self) -> None:
        # Case 3: Integer timeframe input normalization
        self.assertEqual(TimeframeNormalizer.normalize(1), 1)
        self.assertEqual(TimeframeNormalizer.normalize(4), 4)
        self.assertEqual(TimeframeNormalizer.normalize(16), 16)
        self.assertEqual(TimeframeNormalizer.normalize(64), 64)
        self.assertEqual(TimeframeNormalizer.normalize(256), 256)
        self.assertEqual(TimeframeNormalizer.normalize(1024), 1024)

        # String representations of valid integers
        self.assertEqual(TimeframeNormalizer.normalize("64"), 64)
        self.assertEqual(TimeframeNormalizer.normalize("256"), 256)
        self.assertEqual(TimeframeNormalizer.normalize("1024"), 1024)

    def test_invalid_timeframe_input_handling(self) -> None:
        # Case 4: Invalid timeframe inputs must raise ValueError
        with self.assertRaises(ValueError):
            TimeframeNormalizer.normalize("M2")

        with self.assertRaises(ValueError):
            TimeframeNormalizer.normalize(0)

        with self.assertRaises(ValueError):
            TimeframeNormalizer.normalize(-5)

        with self.assertRaises(ValueError):
            TimeframeNormalizer.normalize(None)

        with self.assertRaises(ValueError):
            TimeframeNormalizer.normalize([])

        with self.assertRaises(ValueError):
            TimeframeNormalizer.normalize(True)

        with self.assertRaises(ValueError):
            TimeframeNormalizer.normalize(False)

    def test_predictive_shadow_engine_context_creation(self) -> None:
        # Case 5: PredictiveShadowEngine context creation
        # Using string timeframe
        ctx_tick = self.engine.get_or_create_context("XAUUSD", "Tick")
        self.assertEqual(ctx_tick.timeframe, "Tick")

        # Using integer timeframe
        ctx_64 = self.engine.get_or_create_context("XAUUSD", 64)
        self.assertEqual(ctx_64.timeframe, 64)

        # Using string representing integer
        ctx_256 = self.engine.get_or_create_context("XAUUSD", "256")
        self.assertEqual(ctx_256.timeframe, 256)

        # Ensure all contexts exist in flat contexts view
        self.assertIn("XAUUSD_Tick", self.engine.contexts)
        self.assertIn("XAUUSD_64", self.engine.contexts)
        self.assertIn("XAUUSD_256", self.engine.contexts)

    def test_deterministic_hash_regression(self) -> None:
        # Critical Finding 3: Test deterministic hashes
        params1 = {"minimum_events_threshold": 10000, "execution_timeframe": "M5"}
        params2 = {"execution_timeframe": "M5", "minimum_events_threshold": 10000}
        params3 = {"execution_timeframe": "M15", "minimum_events_threshold": 10000}

        hash1 = generate_deterministic_hash(params1)
        hash2 = generate_deterministic_hash(params2)
        hash3 = generate_deterministic_hash(params3)

        # Equal inputs (even with different key orders) produce equal hashes (because sort_keys=True)
        self.assertEqual(hash1, hash2)
        # Different inputs produce different hashes
        self.assertNotEqual(hash1, hash3)
        self.assertIsNotNone(hash1)
        self.assertEqual(len(hash1), 64) # sha256 length

    def test_reports_api_never_returns_numeric_timeframe_values(self) -> None:
        """
        Regression test: Reports API must never return numeric timeframe values.
        Verify that statistics and dictionaries serialized for API clients always have
        strictly string-typed 'timeframe' fields.
        """
        # Create numeric-timeframe context
        ctx_numeric = self.engine.get_or_create_context("XAUUSD", 1024)
        stats = ctx_numeric.get_statistics()

        # Must be string-typed
        self.assertIsInstance(stats["timeframe"], str)
        self.assertEqual(stats["timeframe"], "1024")

        # Also verify with standard string-based timeframes
        ctx_str = self.engine.get_or_create_context("XAUUSD", "M5")
        stats_str = ctx_str.get_statistics()
        self.assertIsInstance(stats_str["timeframe"], str)
        self.assertEqual(stats_str["timeframe"], "M5")
