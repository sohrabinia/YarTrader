import unittest
from datetime import datetime
from src.Decision.Models.models import DecisionState
from src.Decision.Intelligence import (
    DecisionEngine,
    DecisionContextBuilder,
    DecisionAnalyzer,
    DecisionQualityEvaluator,
    DecisionConflictResolver,
    DecisionReportBuilder,
    DecisionValidator,
    DecisionIntelligenceContext as OldIntelligenceContext
)
from src.Decision.Intelligence.Agents.models import AgentContext, AgentMessage
from src.Decision.Intelligence.Agents.agents import ResearchAgent, StrategyAnalystAgent, RiskAgent, ValidationAgent

class TestAgentValidationIntegration(unittest.TestCase):
    """
    Validates agent integration with existing Decision Intelligence Layer models
    and advanced conflict resolution scenarios.
    """

    def setUp(self) -> None:
        self.research = ResearchAgent()
        self.strategy = StrategyAnalystAgent()
        self.risk = RiskAgent()
        self.validation = ValidationAgent()
        self.now = datetime.now()

    def test_decision_layer_integration(self) -> None:
        """Test integration output correctly constructs a DecisionIntelligenceContext."""
        # Assemble message outputs from agents
        msg_init = AgentMessage("msg-1", "Orchestrator", "ResearchAgent", {"asset": "AAPL"})
        res_msg = self.research.process_message(msg_init, AgentContext("ctx-1"))

        msg_strat = AgentMessage("msg-2", "Orchestrator", "StrategyAnalystAgent", {
            "asset": "AAPL",
            "research_sentiment": res_msg.Payload["research_sentiment"]
        })
        strat_msg = self.strategy.process_message(msg_strat, AgentContext("ctx-2"))

        msg_risk = AgentMessage("msg-3", "Orchestrator", "RiskAgent", {
            "asset": "AAPL",
            "strategy_score": strat_msg.Payload["strategy_score"]
        })
        risk_msg = self.risk.process_message(msg_risk, AgentContext("ctx-3"))

        # Map to DecisionIntelligenceContext (Phase 18 model)
        builder = DecisionContextBuilder()
        dec_context = builder.build_context(
            research_output=[res_msg.Payload],
            strategy_evaluation=[strat_msg.Payload],
            risk_assessment=[risk_msg.Payload],
            metadata={"asset": "AAPL"}
        )

        self.assertEqual(len(dec_context.ResearchInsights), 1)
        self.assertEqual(dec_context.ResearchInsights[0]["research_sentiment"], "bullish")
        self.assertEqual(dec_context.StrategyEvaluations[0]["strategy_score"], 0.85)
        self.assertTrue(dec_context.RiskAssessments[0]["risk_approved"])

    def test_conflict_scenario_1_research_vs_risk(self) -> None:
        """Test Conflict Scenario 1: Positive research vs high uncertainty/failed risk."""
        # 1. Research gives bullish
        res_payload = {"research_sentiment": "bullish", "insights_count": 2}

        # 2. Strategy Analyst gives high score
        strat_payload = {"strategy_score": 0.85, "confidence": 0.90}

        # 3. Risk is rejected
        risk_payload = {"risk_approved": False, "assessment_notes": "Exceeds extreme drawdowns limit"}

        engine = DecisionEngine()
        dec_context = engine.builder.build_context(
            research_output=[res_payload],
            strategy_evaluation=[strat_payload],
            risk_assessment=[risk_payload],
            metadata={"asset": "AAPL"}
        )

        report = engine.evaluate_intelligence_context(dec_context)

        # Conflict must be detected, and state must be Rejected
        self.assertEqual(report.State, DecisionState.REJECTED)
        self.assertTrue(report.ConflictAnalysis.ConflictDetected)
        self.assertEqual(report.ConflictAnalysis.ConflictType, "Strategy_vs_Risk")

    def test_conflict_scenario_2_strategy_vs_validation(self) -> None:
        """Test Conflict Scenario 2: High score strategy vs low validation reliability."""
        res_payload = {"research_sentiment": "bearish", "insights_count": 2}
        strat_payload = {"strategy_score": 0.85, "confidence": 0.90} # Strategy conflicts with research sentiment!
        risk_payload = {"risk_approved": True, "assessment_notes": "Limits safe"}

        engine = DecisionEngine()
        dec_context = engine.builder.build_context(
            research_output=[res_payload],
            strategy_evaluation=[strat_payload],
            risk_assessment=[risk_payload],
            metadata={"asset": "AAPL"}
        )

        report = engine.evaluate_intelligence_context(dec_context)

        # Conflict resolver must detect the Research vs Strategy contradiction and reduce confidence!
        self.assertTrue(report.ConflictAnalysis.ConflictDetected)
        self.assertEqual(report.ConflictAnalysis.ConflictType, "Research_vs_Strategy")
        self.assertTrue(report.ConflictAnalysis.ConfidenceImpact < 0.0)

    def test_conflict_scenario_3_missing_agent_output(self) -> None:
        """Test Conflict Scenario 3: Missing agent output yields safe degradation."""
        # Missing strategy evaluation -> yields safe ReviewRequired state
        engine = DecisionEngine()
        dec_context = engine.builder.build_context(
            research_output=[{"research_sentiment": "bullish"}],
            strategy_evaluation=[], # Missing
            risk_assessment=[{"risk_approved": True}],
            metadata={"asset": "AAPL"}
        )

        report = engine.evaluate_intelligence_context(dec_context)
        self.assertEqual(report.State, DecisionState.REVIEW_REQUIRED)
