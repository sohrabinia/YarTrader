import unittest
from src.Decision.Intelligence.Agents.services import AgentPerformanceTracker

class TestAgentPerformanceTracker(unittest.TestCase):
    """
    Validates completeness, quality, reliability, and consistency logging and scoring.
    """

    def setUp(self) -> None:
        self.tracker = AgentPerformanceTracker()

    def test_performance_tracking_and_scoring(self) -> None:
        """Test performance metric logs and averaged evaluations."""
        self.tracker.log_agent_performance("ResearchAgent", 1.0, 0.90, 0.85, 0.95)
        self.tracker.log_agent_performance("ResearchAgent", 0.90, 0.95, 0.95, 0.85)

        comp = self.tracker.get_agent_score("ResearchAgent", "Completeness")
        qual = self.tracker.get_agent_score("ResearchAgent", "Quality")
        rel = self.tracker.get_agent_score("ResearchAgent", "Reliability")
        cons = self.tracker.get_agent_score("ResearchAgent", "Consistency")

        self.assertAlmostEqual(comp, 0.95)
        self.assertAlmostEqual(qual, 0.925)
        self.assertAlmostEqual(rel, 0.90)
        self.assertAlmostEqual(cons, 0.90)

    def test_missing_agent_performance_score(self) -> None:
        """Test scoring of non-logged agents returns default 0.0."""
        score = self.tracker.get_agent_score("NonExistent", "Quality")
        self.assertEqual(score, 0.0)
