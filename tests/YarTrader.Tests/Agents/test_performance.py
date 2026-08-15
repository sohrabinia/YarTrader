import unittest
from datetime import datetime
from src.Application.Agents.tracker import AgentPerformanceTracker, PerformanceScore
from src.Infrastructure.exceptions import ValidationException


class TestAgentPerformanceTracker(unittest.TestCase):
    """
    Verifies that AgentPerformanceTracker correctly records multi-factor scoring
    and computes averages over the agent's lifecycle.
    """

    def setUp(self) -> None:
        self.tracker = AgentPerformanceTracker()

    def test_recording_and_averages(self) -> None:
        """Test recording correct values and verifying average scores."""
        agent_id = "agent-research"

        # Record 1st performance entry
        self.tracker.record_performance(
            agent_id=agent_id,
            completeness=1.0,
            reliability=0.8,
            data_quality=0.9,
            consistency=0.9
        )

        # Record 2nd performance entry
        self.tracker.record_performance(
            agent_id=agent_id,
            completeness=0.8,
            reliability=0.6,
            data_quality=0.7,
            consistency=0.7
        )

        # Fetch averages
        averages = self.tracker.get_average_scores(agent_id)

        self.assertAlmostEqual(averages["completeness"], 0.9)
        self.assertAlmostEqual(averages["reliability"], 0.7)
        self.assertAlmostEqual(averages["data_quality"], 0.8)
        self.assertAlmostEqual(averages["consistency"], 0.8)

    def test_invalid_recording_rejection(self) -> None:
        """Test: Reject invalid performance values outside [0, 1]."""
        with self.assertRaises(ValidationException) as ex:
            self.tracker.record_performance(
                agent_id="agent-research",
                completeness=1.5,  # Out of range
                reliability=0.8,
                data_quality=0.9,
                consistency=0.9
            )
        self.assertIn("must be between 0.0 and 1.0", str(ex.exception))

        with self.assertRaises(ValidationException):
            self.tracker.record_performance(
                agent_id="agent-research",
                completeness=-0.1,  # Out of range
                reliability=0.8,
                data_quality=0.9,
                consistency=0.9
            )

    def test_empty_agent_history_defaults(self) -> None:
        """Test: Unregistered or empty history returns perfect safety default (1.0)."""
        averages = self.tracker.get_average_scores("agent-unknown")
        self.assertEqual(averages["completeness"], 1.0)
        self.assertEqual(averages["reliability"], 1.0)
        self.assertEqual(averages["data_quality"], 1.0)
        self.assertEqual(averages["consistency"], 1.0)
