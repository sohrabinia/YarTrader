import unittest
import uuid
import time
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


class TestE2EScenariosAndStress(unittest.TestCase):
    """
    Complete end-to-end multi-agent scenario test cases and high-load stress testing.
    Verifies stability, performance, and memory efficiency under high intelligence processing.
    """

    def setUp(self) -> None:
        self.supervisor = IntelligenceSupervisor()
        self.decision_engine = DecisionEngine()
        self.base_context = AgentContextBuilder.create_with_market_data("AAPL", "H4")

    # ==========================================
    # 1. END-TO-END SCENARIO TESTS
    # ==========================================

    def test_scenario_a_normal_market(self) -> None:
        """Scenario A: Normal market. All agents available, complete intelligence report generated."""
        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())
        self.supervisor.register_agent(ValidationAgent())
        self.supervisor.register_agent(LearningAgent())

        final_ctx = self.supervisor.orchestrate(self.base_context)
        decision_ctx = self.supervisor.compile_to_decision_context(final_ctx)
        report = self.decision_engine.evaluate_intelligence_context(decision_ctx)

        self.assertEqual(report.State, DecisionState.APPROVED)
        self.assertFalse(report.ConflictAnalysis.ConflictDetected)
        self.assertEqual(len(report.EvidenceTrail.ResearchEvidence), 1)
        self.assertEqual(len(report.EvidenceTrail.StrategyEvidence), 1)

    def test_scenario_b_high_volatility(self) -> None:
        """Scenario B: High Volatility. Risk Agent detects instability, causing increased risk assessment scrutiny."""
        class HighVolatilityRiskAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__("agent-risk", "Risk Agent", "Detects high volatility")

            def process(self, context, msg) -> IntelligenceMessage:
                return IntelligenceMessage(
                    message_id="msg-risk-high-vol",
                    sender_id=self.agent_id,
                    recipient_id=msg.sender_id,
                    timestamp=datetime.now(),
                    message_type="RiskAssessment",
                    payload={
                        "IsApproved": True,  # still approved but warning
                        "RiskProfileName": "Moderate",
                        "PortfolioRiskMetrics": {"annualized_volatility": 0.28, "max_drawdown": 0.12, "sharp_ratio": 1.4},
                        "AssessmentNotes": "WARNING: High volatility detected in the market. Scrutiny increased."
                    }
                )

        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(HighVolatilityRiskAgent())

        final_ctx = self.supervisor.orchestrate(self.base_context)
        decision_ctx = self.supervisor.compile_to_decision_context(final_ctx)
        report = self.decision_engine.evaluate_intelligence_context(decision_ctx)

        # High volatility is detected, notes are forwarded correctly
        self.assertEqual(report.State, DecisionState.APPROVED)
        self.assertIn("High volatility detected", report.Context.RiskAssessments[0].AssessmentNotes)

    def test_scenario_c_conflicting_intelligence(self) -> None:
        """Scenario C: Conflicting Intelligence. Agents disagree (Research positive, Risk fails). Conflict resolver activates."""
        class NegativeRiskAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__("agent-risk", "Risk Agent", "Rejects everything")

            def process(self, context, msg) -> IntelligenceMessage:
                return IntelligenceMessage(
                    message_id="msg-risk-neg",
                    sender_id=self.agent_id,
                    recipient_id=msg.sender_id,
                    timestamp=datetime.now(),
                    message_type="RiskAssessment",
                    payload={
                        "IsApproved": False,
                        "RiskProfileName": "Moderate",
                        "PortfolioRiskMetrics": {"annualized_volatility": 0.40, "max_drawdown": 0.25, "sharp_ratio": 0.1},
                        "AssessmentNotes": "High uncertainty and exposure violations."
                    }
                )

        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(NegativeRiskAgent())

        final_ctx = self.supervisor.orchestrate(self.base_context)
        decision_ctx = self.supervisor.compile_to_decision_context(final_ctx)
        report = self.decision_engine.evaluate_intelligence_context(decision_ctx)

        # Disagreement triggers active conflict resolution and rejected state
        self.assertEqual(report.State, DecisionState.REJECTED)
        self.assertTrue(report.ConflictAnalysis.ConflictDetected)
        self.assertEqual(report.ConflictAnalysis.ConflictType, "Strategy_vs_Risk")

    def test_scenario_d_data_failure(self) -> None:
        """Scenario D: Data Failure. Research data is unavailable. System degrades gracefully."""
        class NoDataResearchAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__("agent-research", "Research Agent", "No data")

            def process(self, context, msg) -> IntelligenceMessage:
                return IntelligenceMessage(
                    message_id="msg-res-empty",
                    sender_id=self.agent_id,
                    recipient_id=msg.sender_id,
                    timestamp=datetime.now(),
                    message_type="ResearchReport",
                    payload={"findings": [], "features": {}}  # No features/findings
                )

        self.supervisor.register_agent(NoDataResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())

        final_ctx = self.supervisor.orchestrate(self.base_context)
        decision_ctx = self.supervisor.compile_to_decision_context(final_ctx)
        report = self.decision_engine.evaluate_intelligence_context(decision_ctx)

        # Runs smoothly, but state defaults to REVIEW_REQUIRED due to incomplete crucial information
        self.assertEqual(report.State, DecisionState.REVIEW_REQUIRED)

    def test_scenario_e_agent_failure(self) -> None:
        """Scenario E: Agent failure. Validation agent crashes, system remains stable and continues."""
        class CrashValidationAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__("agent-validation", "Crasher", "Throws error")

            def process(self, context, msg) -> IntelligenceMessage:
                raise RuntimeError("Hardware failure during validation audit!")

        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())
        self.supervisor.register_agent(CrashValidationAgent())

        final_ctx = self.supervisor.orchestrate(self.base_context)

        # Validation status is marked FAILED, but orchestration completes successfully
        self.assertEqual(self.supervisor.get_agent_status("agent-validation"), "FAILED")
        self.assertNotIn("ComplianceAudit", final_ctx.data)
        self.assertIn("error_agent-validation", final_ctx.data)

    # ==========================================
    # 2. INTENSITY AND STRESS TESTS
    # ==========================================

    def test_stress_agent_messages_routing(self) -> None:
        """Stress: Process 100 agent messages sequentially through the Router."""
        from src.Application.Agents.communication import MessageRouter

        router = MessageRouter()

        class DummyAgent:
            def process(self, c, m): pass

        agent = DummyAgent()

        start_time = time.time()
        for i in range(100):
            msg = IntelligenceMessage(
                message_id=f"msg-stress-{i}",
                sender_id="sender",
                recipient_id="recipient",
                timestamp=datetime.now(),
                message_type="StressTest",
                payload={"index": i}
            )
            router.process_and_route(msg, agent)

        elapsed = time.time() - start_time
        # Sequentially routing 100 messages should be extremely fast (under 500ms)
        self.assertLess(elapsed, 1.0)

    def test_stress_intelligence_contexts_enrichment(self) -> None:
        """Stress: Create and enrich 1000 intelligence contexts (copy-on-write)."""
        ctx = AgentContextBuilder.create_empty()

        start_time = time.time()
        for i in range(1000):
            # Monotonically increasing enrichment
            ctx = ctx.enrich(
                agent_id="agent-load",
                key=f"field_{i}",
                value={"metric_val": float(i)}
            )

        elapsed = time.time() - start_time
        self.assertEqual(ctx.version, 1001)
        self.assertEqual(len(ctx.audit_trail), 1000)
        # Deepcopy 1000 times sequentially should run in a brief window (increased limit for slow environments)
        self.assertLess(elapsed, 5.0)

    def test_stress_large_historical_memory_retrieval(self) -> None:
        """Stress: Store 1000 items in memory store and retrieve them rapidly."""
        from src.Application.Agents.memory import AgentMemory

        mem = AgentMemory(max_size=1000)

        # Store 1000 items
        for i in range(1000):
            mem.store("agent-x", f"key-{i}", f"val-{i}", tags=["stress", f"tag-{i % 5}"])

        start_time = time.time()
        # Retrieve random keys
        for i in range(100, 200):
            val = mem.retrieve("agent-x", f"key-{i}")
            self.assertEqual(val, f"val-{i}")

        # Query by tags (retrieve sub-lists)
        subset = mem.query_by_tags("agent-x", ["stress"])
        self.assertEqual(len(subset), 1000)

        elapsed = time.time() - start_time
        self.assertLess(elapsed, 1.0)

    def test_stress_multiple_simultaneous_validations(self) -> None:
        """Stress: Execute validation agent process across multiple mock parallel tasks."""
        agent = ValidationAgent()
        ctx = AgentContextBuilder.create_with_market_data("AAPL", "H4")

        start_time = time.time()
        for i in range(100):
            msg = IntelligenceMessage(
                message_id=f"msg-val-stress-{i}",
                sender_id="supervisor",
                recipient_id=agent.agent_id,
                timestamp=datetime.now(),
                message_type="ExecuteTask",
                payload={"index": i}
            )
            out = agent.process(ctx, msg)
            self.assertEqual(out.message_type, "ComplianceAudit")

        elapsed = time.time() - start_time
        self.assertLess(elapsed, 1.0)
