import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.Research.MarketAnalysis.Models.models import ResearchRequest
from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine


class FeatureExtractionBrainStateTests(unittest.TestCase):
    def test_compatibility_engine_does_not_instantiate_live_brains_or_indicators(self):
        """The legacy class name is only an alias; Base-only research must not instantiate Brain or indicators."""
        provider = MagicMock()
        engine = FeatureExtractionResearchEngine(data_provider=provider)
        now = datetime(2026, 10, 1, 12, 0, 0)
        points = [
            SimpleNamespace(
                Timestamp=now + timedelta(hours=i), Open=2000.0 + i,
                High=2001.0 + i, Low=1999.0 + i, Close=2000.5 + i, Volume=100.0,
            )
            for i in range(60)
        ]
        request = ResearchRequest(
            Asset="XAUUSD", StartTime=now, EndTime=now + timedelta(hours=59),
            Context={"timeframe": "H1"},
        )
        response = SimpleNamespace(DataPoints=points)
        no_candidate = {
            "best_candidate": None,
            "base_plan": {"status": "WAIT", "reason": "No validated Base candidate"},
            "hierarchy": {}, "reaction_analysis": {}, "model_status": "WAIT",
            "summary": "No validated Base hierarchy/reaction candidate exists.",
        }
        with patch("src.Research.Brain.live_brain.LiveAnalysisBrain", side_effect=AssertionError("legacy Brain must not run")), \
             patch("src.Intelligence.Execution.strategy_orchestrator.StrategyOrchestrator.evaluate_all_strategies", return_value=no_candidate):
            result = engine.analyze_market(request, market_data_response=response)

        self.assertIsNone(engine.feature_pipeline)
        self.assertEqual(engine._live_brains, {})
        self.assertFalse(result.Findings["newborn_brain_report"]["brain_available"])
        self.assertEqual(result.Findings["autonomous_decision"]["action"], "WAIT")
        self.assertEqual(result.Findings["autonomous_decision"]["evidence"]["decision_authority"], "BASE_HIERARCHY")


if __name__ == "__main__":
    unittest.main()
