import unittest
from datetime import datetime
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Application.Agents.concrete_agents import (
    ResearchAgent,
    StrategyAnalystAgent,
    RiskAgent,
    ValidationAgent,
    LearningAgent
)
from src.Application.Agents.context import AgentContextBuilder


class TestAPESFINCompliance(unittest.TestCase):
    """
    Compliance test suite validating APES-FIN standards and confirming zero Trading Bot behavior.
    """

    def setUp(self) -> None:
        self.supervisor = IntelligenceSupervisor()
        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())
        self.supervisor.register_agent(ValidationAgent())
        self.supervisor.register_agent(LearningAgent())
        self.context = AgentContextBuilder.create_with_market_data("AAPL", "H4")

    def test_strict_non_trading_bot_behavior(self) -> None:
        """Test: Verify no agent or supervisor can generate BUY/SELL signals or place trades."""
        final_context = self.supervisor.orchestrate(self.context)

        # 1. Verify that no action keywords are in context payload
        for key, value in final_context.data.items():
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    # None of the values should be active trade commands
                    self.assertNotIn("buy", str(sub_key).lower())
                    self.assertNotIn("sell", str(sub_key).lower())
                    self.assertNotIn("execute", str(sub_key).lower())
                    self.assertNotIn("place_order", str(sub_val).lower())

        # 2. Check compiled decision context has zero active trading action states
        decision_ctx = self.supervisor.compile_to_decision_context(final_context)
        self.assertEqual(decision_ctx.Metadata["asset"], "AAPL")
        self.assertNotIn("trade_action", decision_ctx.Metadata)

    def test_apes_fin_structural_boundaries(self) -> None:
        """Test: Agents only perform passive analysis and parameter recommendations without auto-execution."""
        final_context = self.supervisor.orchestrate(self.context)

        # Learning Agent should only make parameter optimization recommendations
        learning_report = final_context.data.get("LearningFeedback")
        self.assertIsNotNone(learning_report)
        self.assertTrue(learning_report["feedback_analyzed"])

        # Recommendations are passive lists of rules or mathematical suggestions
        suggestions = learning_report["improvement_suggestions"]
        self.assertIsInstance(suggestions, list)
        for sug in suggestions:
            # Suggestions are passive and informational only
            self.assertIn("volatility", sug.lower())
