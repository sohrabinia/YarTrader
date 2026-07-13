import unittest
from datetime import datetime
from src.Infrastructure.exceptions import ValidationException
from src.Decision.Intelligence.Agents.models import IIntelligenceAgent, AgentMessage, AgentContext
from src.Decision.Intelligence.Agents.agents import (
    ResearchAgent,
    StrategyAnalystAgent,
    RiskAgent,
    ValidationAgent,
    LearningAgent
)

class TestAgentContracts(unittest.TestCase):
    """
    Validates that all platform agents conform strictly to standard identity,
    responsibility, and safety isolation contracts.
    """

    def setUp(self) -> None:
        self.research = ResearchAgent()
        self.strategy = StrategyAnalystAgent()
        self.risk = RiskAgent()
        self.validation = ValidationAgent()
        self.learning = LearningAgent()
        self.now = datetime.now()

    def test_agent_identities_and_responsibilities(self) -> None:
        """Test Agent identities and responsibilities match specifications."""
        agents = [self.research, self.strategy, self.risk, self.validation, self.learning]

        for agent in agents:
            # Identity and responsibilities must exist and be defined
            self.assertIsNotNone(agent.Name)
            self.assertTrue(len(agent.Name.strip()) > 0)
            self.assertIsNotNone(agent.Responsibility)
            self.assertTrue(len(agent.Responsibility.strip()) > 0)
            self.assertTrue(isinstance(agent, IIntelligenceAgent))

    def test_research_agent_isolation_limits(self) -> None:
        """Test ResearchAgent capabilities and forbidden boundaries."""
        context = AgentContext("ctx-1")
        msg = AgentMessage("msg-1", "Orchestrator", "ResearchAgent", {"asset": "AAPL"})

        response = self.research.process_message(msg, context)

        # Allowed observations
        self.assertEqual(response.Payload["research_sentiment"], "bullish")
        self.assertEqual(response.Payload["insights_count"], 2)
        self.assertIn("Double Bottom", response.Payload["patterns"])

        # Verify no execution details exist in payload
        forbidden_keywords = ["order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"]
        for kw in forbidden_keywords:
            self.assertNotIn(kw, str(response.Payload).lower())

    def test_strategy_agent_isolation_limits(self) -> None:
        """Test StrategyAnalystAgent capabilities and forbidden boundaries."""
        context = AgentContext("ctx-2")
        msg = AgentMessage("msg-2", "Orchestrator", "StrategyAnalystAgent", {"asset": "AAPL", "research_sentiment": "bullish"})

        response = self.strategy.process_message(msg, context)

        # Allowed scoring
        self.assertEqual(response.Payload["strategy_score"], 0.85)
        self.assertEqual(response.Payload["confidence"], 0.90)

        # Verify no execution signals or signals exist in payload
        forbidden_keywords = ["order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"]
        for kw in forbidden_keywords:
            self.assertNotIn(kw, str(response.Payload).lower())

    def test_risk_agent_isolation_limits(self) -> None:
        """Test RiskAgent capabilities and forbidden boundaries."""
        context = AgentContext("ctx-3")

        # Test low volatility is approved
        msg_low = AgentMessage("msg-3a", "Orchestrator", "RiskAgent", {"asset": "AAPL", "strategy_score": 0.85, "volatility_level": "low"})
        res_low = self.risk.process_message(msg_low, context)
        self.assertTrue(res_low.Payload["risk_approved"])

        # Test high volatility triggers safety check and restricts score
        msg_high = AgentMessage("msg-3b", "Orchestrator", "RiskAgent", {"asset": "AAPL", "strategy_score": 0.85, "volatility_level": "high"})
        res_high = self.risk.process_message(msg_high, context)
        self.assertFalse(res_high.Payload["risk_approved"])
        self.assertIn("Fails volatility stress check", res_high.Payload["assessment_notes"])

        # Verify no position opening commands are generated
        forbidden_keywords = ["order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"]
        for kw in forbidden_keywords:
            self.assertNotIn(kw, str(res_high.Payload).lower())

    def test_validation_agent_isolation_limits(self) -> None:
        """Test ValidationAgent capabilities and forbidden boundaries."""
        context = AgentContext("ctx-4")

        # Test risk approved yields compliance
        msg_ok = AgentMessage("msg-4a", "Orchestrator", "ValidationAgent", {"asset": "AAPL", "risk_approved": True})
        res_ok = self.validation.process_message(msg_ok, context)
        self.assertTrue(res_ok.Payload["validation_passed"])

        # Test risk failed yields validation failure
        msg_fail = AgentMessage("msg-4b", "Orchestrator", "ValidationAgent", {"asset": "AAPL", "risk_approved": False})
        res_fail = self.validation.process_message(msg_fail, context)
        self.assertFalse(res_fail.Payload["validation_passed"])
        self.assertIn("Fails risk assessment verification", res_fail.Payload["reasons"])

        # Validation agent cannot modify decisions on its own
        forbidden_keywords = ["order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"]
        for kw in forbidden_keywords:
            self.assertNotIn(kw, str(res_fail.Payload).lower())

    def test_learning_agent_isolation_limits(self) -> None:
        """Test LearningAgent capabilities and forbidden boundaries."""
        context = AgentContext("ctx-5")

        # Test stable returns
        msg_ok = AgentMessage("msg-5a", "Orchestrator", "LearningAgent", {"asset": "AAPL", "observed_result": 0.12})
        res_ok = self.learning.process_message(msg_ok, context)
        self.assertEqual(res_ok.Payload["suggestion"], "Maintain existing parameters")

        # Test high downside return triggers suggest parameter adjustment
        msg_fail = AgentMessage("msg-5b", "Orchestrator", "LearningAgent", {"asset": "AAPL", "observed_result": -0.15})
        res_fail = self.learning.process_message(msg_fail, context)
        self.assertEqual(res_fail.Payload["suggestion"], "Reduce max single-asset exposure limit parameter")

        # Learning agent has zero order or live broker control
        forbidden_keywords = ["order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"]
        for kw in forbidden_keywords:
            self.assertNotIn(kw, str(res_fail.Payload).lower())
