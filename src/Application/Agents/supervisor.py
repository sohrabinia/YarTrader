import uuid
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Application.Agents.interfaces import IIntelligenceAgent
from src.Application.Agents.context import AgentContext, AgentContextBuilder
from src.Application.Agents.communication import IntelligenceMessage, MessageRouter
from src.Application.Agents.memory import AgentMemory
from src.Application.Agents.tracker import AgentPerformanceTracker
from src.Decision.Intelligence.models import DecisionIntelligenceContext
from src.Research.MarketAnalysis.Models.models import MarketInsight
from src.Research.Engine.models import PatternObservation
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore
from src.Risk.Models.models import RiskProfile, RiskAssessment, PortfolioRisk
from src.Infrastructure.exceptions import ValidationException


class IntelligenceSupervisor:
    """
    Supervisor coordinating Multi-Agent lifecycle, registration, execution ordering,
    failure recovery, timeout simulations, and compilation into DecisionIntelligenceContext.
    """
    def __init__(self) -> None:
        self._agents: Dict[str, IIntelligenceAgent] = {}
        self._agent_status: Dict[str, str] = {}  # agent_id -> ACTIVE, FAILED, TIMED_OUT, etc.
        self._router = MessageRouter()
        self._memory = AgentMemory()
        self._tracker = AgentPerformanceTracker()
        self._timeouts: Dict[str, float] = {}  # agent_id -> timeout_seconds limit

    def register_agent(self, agent: IIntelligenceAgent, timeout_seconds: float = 2.0) -> None:
        """Registers an intelligence agent and sets its initial active state."""
        if not agent or not hasattr(agent, "agent_id"):
            raise ValidationException("Supervisor Error: Invalid agent instance.")
        self._agents[agent.agent_id] = agent
        self._agent_status[agent.agent_id] = "ACTIVE"
        self._timeouts[agent.agent_id] = timeout_seconds

    def get_agent(self, agent_id: str) -> Optional[IIntelligenceAgent]:
        """Discovers a registered agent by ID."""
        return self._agents.get(agent_id)

    def get_agent_status(self, agent_id: str) -> str:
        """Returns the current status of an agent."""
        return self._agent_status.get(agent_id, "UNKNOWN")

    def set_agent_status(self, agent_id: str, status: str) -> None:
        """Manually overrides or updates the status of an agent."""
        if agent_id in self._agents:
            self._agent_status[agent_id] = status

    def list_agents(self) -> List[IIntelligenceAgent]:
        """Lists all registered agents."""
        return list(self._agents.values())

    def process(self, context: Any, message: Any) -> Any:
        """Required to act as a valid recipient/sender in the message router."""
        return message

    def orchestrate(self, context: AgentContext) -> AgentContext:
        """
        Runs registered agents in correct execution ordering:
        Research -> Strategy -> Risk -> Validation -> Learning.
        Gracefully handles individual agent failures and timeouts.
        """
        # Define strict execution ordering by agent_id or type
        execution_order = [
            "agent-research",
            "agent-strategy",
            "agent-risk",
            "agent-validation",
            "agent-learning"
        ]

        current_ctx = context

        for agent_id in execution_order:
            agent = self._agents.get(agent_id)
            if not agent:
                # If a required agent is missing, system degrades gracefully.
                # Record missing agent in context audit.
                current_ctx = current_ctx.enrich(
                    agent_id="supervisor",
                    key=f"warning_missing_{agent_id}",
                    value=f"Agent '{agent_id}' is not registered. Graceful degradation applied.",
                    action="degrade"
                )
                continue

            status = self._agent_status.get(agent_id, "INACTIVE")
            if status != "ACTIVE":
                current_ctx = current_ctx.enrich(
                    agent_id="supervisor",
                    key=f"warning_inactive_{agent_id}",
                    value=f"Agent '{agent_id}' is in '{status}' status and was bypassed.",
                    action="skip"
                )
                continue

            # Build input message
            msg_id = f"msg-sup-{uuid.uuid4()}"
            input_msg = IntelligenceMessage(
                message_id=msg_id,
                sender_id="supervisor",
                recipient_id=agent_id,
                timestamp=datetime.now(),
                message_type="ExecuteTask",
                payload={"asset": current_ctx.data.get("asset", "UNKNOWN")},
                trace_trail=[]
            )

            try:
                # Simulate timeout check
                timeout_limit = self._timeouts.get(agent_id, 2.0)
                start_time = time.time()

                # Execute Agent process
                output_msg = agent.process(current_ctx, input_msg)

                elapsed = time.time() - start_time
                if elapsed > timeout_limit:
                    raise TimeoutError(f"Agent '{agent_id}' processing exceeded timeout threshold of {timeout_limit}s.")

                # Record successful execution and store in memory
                self._router.process_and_route(output_msg, self)
                self._memory.store(
                    namespace=agent_id,
                    key=output_msg.message_type,
                    value=output_msg.payload,
                    tags=[output_msg.message_type, "orchestrated"]
                )

                # Record metrics in tracker
                self._tracker.record_performance(
                    agent_id=agent_id,
                    completeness=1.0,
                    reliability=1.0,
                    data_quality=1.0,
                    consistency=1.0
                )

                # Enrich global context copy-on-write
                current_ctx = current_ctx.enrich(
                    agent_id=agent_id,
                    key=output_msg.message_type,
                    value=output_msg.payload,
                    action="process_complete"
                )

            except TimeoutError as te:
                # Handle timeout safely
                self._agent_status[agent_id] = "TIMED_OUT"
                self._tracker.record_performance(
                    agent_id=agent_id,
                    completeness=0.0,
                    reliability=0.0,
                    data_quality=0.5,
                    consistency=0.5
                )
                current_ctx = current_ctx.enrich(
                    agent_id="supervisor",
                    key=f"error_{agent_id}",
                    value={"error_type": "Timeout", "details": str(te)},
                    action="handle_timeout"
                )

            except Exception as e:
                # Handle any other failure/exception safely
                self._agent_status[agent_id] = "FAILED"
                self._tracker.record_performance(
                    agent_id=agent_id,
                    completeness=0.0,
                    reliability=0.0,
                    data_quality=0.0,
                    consistency=0.0
                )
                current_ctx = current_ctx.enrich(
                    agent_id="supervisor",
                    key=f"error_{agent_id}",
                    value={"error_type": "Failure", "details": str(e)},
                    action="handle_failure"
                )

        return current_ctx

    def compile_to_decision_context(self, context: AgentContext) -> DecisionIntelligenceContext:
        """
        Maps enriched AgentContext data into a validated DecisionIntelligenceContext
        to be consumed directly by the existing Decision Intelligence Layer.
        """
        # Determine any data quality penalties from validation agent
        compliance_report = context.data.get("ComplianceAudit")
        quality_multiplier = 1.0
        if compliance_report:
            quality_score = compliance_report.get("data_quality_score", 1.0)
            if quality_score < 0.5:
                quality_multiplier = 0.3  # Scale down confidence on low quality validation

        # 1. Extract Research insights & Pattern observations
        research_report = context.data.get("ResearchReport")
        insights = []
        patterns = []
        if research_report and research_report.get("findings"):
            # Reconstruct model instances for robust integration
            raw_confidence = research_report.get("features", {}).get("trend_strength", 0.8)
            insights.append(
                MarketInsight(
                    Category="Trend",
                    Description=", ".join(research_report.get("findings", [])),
                    Confidence=raw_confidence * quality_multiplier,
                    CreatedAt=datetime.now()
                )
            )
            patterns.append(
                PatternObservation(
                    PatternName="Double Bottom",
                    Description="Double Bottom pattern found by research agent",
                    Confidence=0.85 * quality_multiplier,
                    Timestamp=datetime.now(),
                    MatchedFeatures=["price"]
                )
            )

        # 2. Extract Strategy evaluations
        strat_report = context.data.get("StrategyEvaluation")
        evals = []
        if strat_report:
            score_dict = strat_report.get("score", {})
            evals.append(
                StrategyEvaluation(
                    StrategyId=strat_report.get("strategy_id", "strat-unknown"),
                    Score=StrategyScore(
                        OverallScore=score_dict.get("OverallScore", 0.0),
                        Confidence=score_dict.get("Confidence", 0.0) * quality_multiplier,
                        Criteria=score_dict.get("Criteria", {})
                    ),
                    EvaluationNotes=strat_report.get("evaluation_notes", ""),
                    EvaluatedAt=datetime.now()
                )
            )

        # 3. Extract Risk assessments
        risk_report = context.data.get("RiskAssessment")
        risks = []
        if risk_report:
            metrics_dict = risk_report.get("PortfolioRiskMetrics", {})
            risks.append(
                RiskAssessment(
                    IsApproved=risk_report.get("IsApproved", False),
                    RiskProfileName=risk_report.get("RiskProfileName", "Moderate"),
                    PortfolioRiskMetrics=PortfolioRisk(
                        ExpectedVolatility=metrics_dict.get("annualized_volatility", 0.0),
                        HistoricalDrawdown=metrics_dict.get("max_drawdown", 0.0),
                        VaR=metrics_dict.get("sharp_ratio", 0.0)
                    ),
                    AssessmentNotes=risk_report.get("AssessmentNotes", ""),
                    AssessedAt=datetime.now()
                )
            )

        # 4. Construct DecisionIntelligenceContext
        asset = context.data.get("asset", "UNKNOWN")
        return DecisionIntelligenceContext(
            ResearchInsights=insights,
            PatternObservations=patterns,
            StrategyEvaluations=evals,
            RiskAssessments=risks,
            MarketConditions={"timeframe": context.data.get("timeframe", "H4")},
            HistoricalEvidence={"agent_context_id": context.context_id},
            Metadata={"asset": asset}
        )
