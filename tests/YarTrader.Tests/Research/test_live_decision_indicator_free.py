import unittest
from unittest.mock import patch, MagicMock
from src.Intelligence.Execution.core import ExecutionIntelligenceCore

class TestLiveDecisionIndicatorFree(unittest.TestCase):
    """
    Regression test verifying that the live production decision path
    never invokes ATR, True Range indicator, or technical indicator engines.
    """

    def setUp(self):
        self.intel_core = ExecutionIntelligenceCore.get_instance()
        self.sample_candles = [
            {"time": f"2026-03-01T10:0{i}:00Z", "open": 2500.0 + i, "high": 2505.0 + i, "low": 2498.0 + i, "close": 2502.0 + i, "volume": 100}
            for i in range(10)
        ]

    def test_live_decision_path_no_indicator_invocations(self):
        """Proves ExecutionIntelligenceCore.evaluate_context() executes without invoking ATR or indicator engines."""
        res = self.intel_core.evaluate_context(
            symbol="XAUUSD",
            timeframe="H1",
            candles=self.sample_candles
        )

        self.assertEqual(res["symbol"], "XAUUSD")
        self.assertEqual(res["timeframe"], "H1")
        self.assertIn("narrative", res)
        self.assertIn("plan", res)

        # Confirm similarity contains no fabricated 88.5 score
        sim = res.get("similarity", {})
        self.assertEqual(sim.get("average_similarity_score"), 0.0)
        self.assertFalse(sim.get("similar_pattern_found"))
        self.assertIsNone(sim.get("best_match"))
        self.assertEqual(sim.get("evidence_state"), "INSUFFICIENT_EVIDENCE")

        # Confirm FRACTAL strategy is explicitly disabled in strategy evaluation
        strat_eval = res.get("strategy_evaluation", {})
        fractal_cand = next((c for c in strat_eval.get("candidates", []) if c.get("strategy_name") == "FRACTAL"), None)
        self.assertIsNotNone(fractal_cand)
        self.assertEqual(fractal_cand["direction"], "WAIT")
        self.assertEqual(fractal_cand["confidence"], 0.0)
        self.assertIn("FRACTAL strategy explicitly disabled: insufficient pattern memory evidence.", fractal_cand["reasoning"])

if __name__ == "__main__":
    unittest.main()
