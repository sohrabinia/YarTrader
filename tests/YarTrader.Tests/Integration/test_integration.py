import unittest
from datetime import datetime
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Application.Agents.concrete_agents import (
    ResearchAgent,
    StrategyAnalystAgent,
    RiskAgent,
    ValidationAgent,
    LearningAgent,
    BaseAgent
)
from src.Application.Agents.context import AgentContextBuilder
from src.Application.Agents.communication import IntelligenceMessage
from src.Decision.Intelligence.engine import DecisionEngine
from src.Decision.Models.models import DecisionState


class TestDecisionAndConflictIntegration(unittest.TestCase):
    """
    Integration tests verifying coordination between the Multi-Agent Layer and
    the Decision Intelligence Core, including Conflict Resolution scenarios.
    """

    def setUp(self) -> None:
        self.supervisor = IntelligenceSupervisor()
        self.decision_engine = DecisionEngine()
        self.base_context = AgentContextBuilder.create_with_market_data("AAPL", "H4")

    def test_complete_successful_integration(self) -> None:
        """Test: Seamless multi-agent orchestration compiling to high-confidence decision."""
        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())
        self.supervisor.register_agent(ValidationAgent())
        self.supervisor.register_agent(LearningAgent())

        # Orchestrate all agents
        enriched_agent_ctx = self.supervisor.orchestrate(self.base_context)

        # Compile to Phase 18 Decision Context
        decision_ctx = self.supervisor.compile_to_decision_context(enriched_agent_ctx)

        # Run Phase 18 Decision Engine evaluation
        report = self.decision_engine.evaluate_intelligence_context(decision_ctx)

        # Verify evidence trace and core parameters
        self.assertIsNotNone(report)
        self.assertEqual(report.State, DecisionState.APPROVED)
        self.assertFalse(report.ConflictAnalysis.ConflictDetected)
        self.assertEqual(report.Context.Metadata["asset"], "AAPL")
        self.assertGreater(report.Confidence, 0.70)

        # Verify that source evidence from agents is preserved
        self.assertEqual(len(report.EvidenceTrail.ResearchEvidence), 1)
        self.assertEqual(len(report.EvidenceTrail.StrategyEvidence), 1)
        self.assertEqual(len(report.EvidenceTrail.RiskEvidence), 1)

    def test_conflict_scenario_1_research_vs_risk(self) -> None:
        """
        Conflict Scenario 1:
        Research Agent produces bullish observations, but Risk Agent rejects proposal due to instability.
        Expected: Conflict is detected, state is REJECTED.
        """
        class RejectionRiskAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__("agent-risk", "Risk Agent", "Fails audit")

            def process(self, context, msg) -> IntelligenceMessage:
                return IntelligenceMessage(
                    message_id="msg-risk-reject",
                    sender_id=self.agent_id,
                    recipient_id=msg.sender_id,
                    timestamp=datetime.now(),
                    message_type="RiskAssessment",
                    payload={
                        "IsApproved": False,
                        "RiskProfileName": "Moderate",
                        "PortfolioRiskMetrics": {"annualized_volatility": 0.35, "max_drawdown": 0.18, "sharp_ratio": 0.4},
                        "AssessmentNotes": "Severe risk exposure detected! Action rejected."
                    }
                )

        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RejectionRiskAgent())

        enriched_agent_ctx = self.supervisor.orchestrate(self.base_context)
        decision_ctx = self.supervisor.compile_to_decision_context(enriched_agent_ctx)
        report = self.decision_engine.evaluate_intelligence_context(decision_ctx)

        # Rejection should trigger, conflict detected
        self.assertEqual(report.State, DecisionState.REJECTED)
        self.assertTrue(report.ConflictAnalysis.ConflictDetected)
        self.assertEqual(report.ConflictAnalysis.ConflictType, "Strategy_vs_Risk")

    def test_conflict_scenario_2_strategy_vs_validation(self) -> None:
        """
        Conflict Scenario 2:
        Strategy Analyst assigns a high score, but Validation Agent flags low reliability / data quality.
        Expected: Decision quality overall score is reduced.
        """
        class LowQualityValidationAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__("agent-validation", "Validation Agent", "Flags low quality")

            def process(self, context, msg) -> IntelligenceMessage:
                return IntelligenceMessage(
                    message_id="msg-val-fail",
                    sender_id=self.agent_id,
                    recipient_id=msg.sender_id,
                    timestamp=datetime.now(),
                    message_type="ComplianceAudit",
                    payload={
                        "compliance_checked": False,
                        "data_quality_score": 0.15,
                        "system_health_status": "Degraded",
                        "notes": "Low reliability data stream detected."
                    }
                )

        # 1. Orchestrate with normal Validation Agent
        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())
        self.supervisor.register_agent(ValidationAgent())

        normal_agent_ctx = self.supervisor.orchestrate(self.base_context)
        normal_ctx = self.supervisor.compile_to_decision_context(normal_agent_ctx)
        normal_report = self.decision_engine.evaluate_intelligence_context(normal_ctx)

        # 2. Reset supervisor and register low quality Validation Agent
        degraded_supervisor = IntelligenceSupervisor()
        degraded_supervisor.register_agent(ResearchAgent())
        degraded_supervisor.register_agent(StrategyAnalystAgent())
        degraded_supervisor.register_agent(RiskAgent())
        degraded_supervisor.register_agent(LowQualityValidationAgent())

        degraded_agent_ctx = degraded_supervisor.orchestrate(self.base_context)
        degraded_ctx = degraded_supervisor.compile_to_decision_context(degraded_agent_ctx)
        degraded_report = self.decision_engine.evaluate_intelligence_context(degraded_ctx)

        # QualityScore and confidence should be significantly lower for low quality
        self.assertLess(degraded_report.Confidence, normal_report.Confidence)
        self.assertLess(degraded_report.QualityScore.OverallScore, normal_report.QualityScore.OverallScore)

    def test_conflict_scenario_3_missing_agent_output(self) -> None:
        """
        Conflict Scenario 3:
        Missing agent output (e.g. Research Agent is not registered).
        Expected: Safe degradation, pipeline completes, report switches state to REVIEW_REQUIRED.
        """
        # Clear default auto-registered ResearchAgent to simulate missing Research agent
        self.supervisor._agents.pop("agent-research", None)
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())

        enriched_agent_ctx = self.supervisor.orchestrate(self.base_context)
        decision_ctx = self.supervisor.compile_to_decision_context(enriched_agent_ctx)
        report = self.decision_engine.evaluate_intelligence_context(decision_ctx)

        # Report should degrade to REVIEW_REQUIRED due to incomplete crucial details (missing Research)
        self.assertEqual(report.State, DecisionState.REVIEW_REQUIRED)
        self.assertIn("warning_missing_agent-research", enriched_agent_ctx.data)
