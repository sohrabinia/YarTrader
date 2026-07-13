import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchEngine
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator
from src.Risk.Interfaces.interfaces import IRiskEngine
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Learning.Interfaces.interfaces import ILearningEngine
from src.Learning.Models.models import LearningFeedback

from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse
from src.Research.MarketAnalysis.Models.models import ResearchRequest, ResearchResult
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation
from src.Risk.Models.models import RiskProfile, RiskAssessment
from src.Decision.Models.models import DecisionContext, DecisionResult


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration settings for pipeline execution."""
    SimulationMode: bool = True
    LookbackDays: int = 10
    DefaultOutcomeMetric: float = 0.05
    CustomSettings: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineContext:
    """Represents the multi-layer execution variables of an active pipeline run."""
    StartTime: datetime
    Asset: str
    Timeframe: str
    TargetRiskProfile: RiskProfile
    Metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineResult:
    """Represents the end-to-end outcome logs, final DecisionResult, and LearningFeedback of the pipeline."""
    Context: PipelineContext
    MarketData: MarketDataResponse
    Research: ResearchResult
    Strategy: StrategyEvaluation
    Risk: RiskAssessment
    Decision: DecisionResult
    Feedback: Optional[LearningFeedback] = None
    ExecutedAt: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class AdvancedPipelineResult:
    """Represents the end-to-end outcome logs, final DecisionIntelligenceReport, and LearningFeedback of the pipeline."""
    Context: PipelineContext
    MarketData: MarketDataResponse
    Research: ResearchResult
    Strategy: StrategyEvaluation
    Risk: RiskAssessment
    DecisionReport: Any  # DecisionIntelligenceReport
    Feedback: Optional[LearningFeedback] = None
    OptimizationReport: Optional[Any] = None  # Phase 19 OptimizationReport
    ExecutedAt: datetime = field(default_factory=datetime.now)


class IntelligencePipeline:
    """
    Orchestration controller coordinating the flow across Data, Research, Strategy, Risk, Decision, and Learning systems.
    Adheres strictly to the clean unidirectional APES-FIN pipeline rules.
    """
    def __init__(
        self,
        data_provider: IMarketDataProvider,
        research_engine: IResearchEngine,
        strategy_evaluator: IStrategyEvaluator,
        risk_engine: IRiskEngine,
        decision_engine: IDecisionEngine,
        learning_engine: Optional[ILearningEngine] = None,
        config: Optional[PipelineConfig] = None
    ) -> None:
        self._data_provider = data_provider
        self._research_engine = research_engine
        self._strategy_evaluator = strategy_evaluator
        self._risk_engine = risk_engine
        self._decision_engine = decision_engine

        if learning_engine is None:
            from src.Learning.Services.services import LearningProcessor
            self._learning_engine = LearningProcessor()
        else:
            self._learning_engine = learning_engine

        self._config = config or PipelineConfig()

    def execute(self, context: PipelineContext) -> PipelineResult:
        # Enforce that only execution simulation mode is supported for safety
        if not self._config.SimulationMode:
            raise ValueError(
                "Execution is strictly restricted to simulation mode only. "
                "Real trading, broker connection, and real money operations are prohibited."
            )

        # 1. Ingest/Data Layer Acquisition
        lookback = self._config.LookbackDays
        data_req = MarketDataRequest(
            Asset=context.Asset,
            StartTime=context.StartTime - timedelta(days=lookback),
            EndTime=context.StartTime,
            Timeframe=context.Timeframe
        )
        data_resp = self._data_provider.retrieve_market_data(data_req)

        # 2. Research Layer Interpretation
        res_req = ResearchRequest(
            Asset=context.Asset,
            StartTime=data_req.StartTime,
            EndTime=data_req.EndTime,
            Context={"bars_count": len(data_resp.DataPoints), "simulation": self._config.SimulationMode}
        )
        research_res = self._research_engine.analyze_market(res_req)

        # 3. Strategy Layer Assessment
        candidate = StrategyCandidate(
            Id=f"cand-{context.Asset}",
            Name="Pipeline Momentum Concept",
            Description=f"Momentum concept for {context.Asset}",
            ResearchContext=research_res.Findings,
            CreatedAt=datetime.now(),
            EvaluationStatus="Pending"
        )
        strat_eval = self._strategy_evaluator.evaluate(candidate)

        # 4. Risk Layer Verification
        proposed_weights = {context.Asset: strat_eval.Score.OverallScore}
        risk_assess = self._risk_engine.analyze_risk(proposed_weights, context.TargetRiskProfile)

        # 5. Decision Layer Integration
        dec_context = DecisionContext(
            StrategyId=candidate.Id,
            AssetWeights=proposed_weights if risk_assess.IsApproved else {},
            TargetRiskProfile=context.TargetRiskProfile.RiskToleranceLevel
        )
        decision_res = self._decision_engine.evaluate_decision(dec_context)

        # 6. Learning Feedback Integration
        outcome_metric = context.Metadata.get("ActualOutcomeMetric", self._config.DefaultOutcomeMetric)
        feedback = LearningFeedback(
            DecisionId=decision_res.DecisionId,
            ActualOutcomeMetric=outcome_metric,
            RecordedAt=datetime.now()
        )
        self._learning_engine.process_feedback(feedback)

        return PipelineResult(
            Context=context,
            MarketData=data_resp,
            Research=research_res,
            Strategy=strat_eval,
            Risk=risk_assess,
            Decision=decision_res,
            Feedback=feedback,
            ExecutedAt=datetime.now()
        )

    def execute_advanced(self, context: PipelineContext) -> AdvancedPipelineResult:
        """
        Executes the advanced multi-factor intelligence pipeline incorporating
        the Advanced Decision Intelligence Layer.
        """
        if not self._config.SimulationMode:
            raise ValueError(
                "Execution is strictly restricted to simulation mode only. "
                "Real trading, broker connection, and real money operations are prohibited."
            )

        # 1. Ingest/Data Layer Acquisition
        lookback = self._config.LookbackDays
        data_req = MarketDataRequest(
            Asset=context.Asset,
            StartTime=context.StartTime - timedelta(days=lookback),
            EndTime=context.StartTime,
            Timeframe=context.Timeframe
        )
        data_resp = self._data_provider.retrieve_market_data(data_req)

        # 2. Research Layer Interpretation
        res_req = ResearchRequest(
            Asset=context.Asset,
            StartTime=data_req.StartTime,
            EndTime=data_req.EndTime,
            Context={"bars_count": len(data_resp.DataPoints), "simulation": self._config.SimulationMode}
        )
        research_res = self._research_engine.analyze_market(res_req)

        # 3. Strategy Layer Assessment
        candidate = StrategyCandidate(
            Id=f"cand-{context.Asset}",
            Name="Pipeline Momentum Concept",
            Description=f"Momentum concept for {context.Asset}",
            ResearchContext=research_res.Findings,
            CreatedAt=datetime.now(),
            EvaluationStatus="Pending"
        )
        strat_eval = self._strategy_evaluator.evaluate(candidate)

        # 4. Risk Layer Verification
        proposed_weights = {context.Asset: strat_eval.Score.OverallScore}
        risk_assess = self._risk_engine.analyze_risk(proposed_weights, context.TargetRiskProfile)

        # 5. Advanced Decision Layer Integration
        from src.Decision.Intelligence.services import DecisionContextBuilder
        from src.Decision.Intelligence.engine import DecisionEngine as AdvancedDecisionEngine

        builder = DecisionContextBuilder()
        dec_intel_context = builder.build_context(
            research_output=research_res,
            strategy_evaluation=strat_eval,
            risk_assessment=risk_assess,
            market_context={"timeframe": context.Timeframe},
            metadata={"asset": context.Asset}
        )

        if hasattr(self._decision_engine, "evaluate_intelligence_context"):
            decision_report = self._decision_engine.evaluate_intelligence_context(dec_intel_context)
        else:
            adv_engine = AdvancedDecisionEngine()
            decision_report = adv_engine.evaluate_intelligence_context(dec_intel_context)

        # 6. Learning Feedback Integration
        outcome_metric = context.Metadata.get("ActualOutcomeMetric", self._config.DefaultOutcomeMetric)
        feedback = LearningFeedback(
            DecisionId=decision_report.ReportId,
            ActualOutcomeMetric=outcome_metric,
            RecordedAt=datetime.now()
        )
        self._learning_engine.process_feedback(feedback)

        # 6b. Advanced Learning & Optimization Integration
        from src.Learning.Optimization.models import LearningFeedbackRecord
        from src.Learning.Optimization.services import LearningProcessor as AdvancedLearningProcessor

        adv_learning_record = LearningFeedbackRecord(
            DecisionReference=decision_report.ReportId,
            AnalysisContext={
                "risk_approved": risk_assess.IsApproved,
                "insights_count": len(dec_intel_context.ResearchInsights)
            },
            ExpectedQuality=decision_report.QualityScore.OverallScore if hasattr(decision_report, "QualityScore") else 0.85,
            ObservedResult=outcome_metric,
            ConfidenceInformation=decision_report.Confidence,
            Timestamp=datetime.now()
        )

        adv_learning_processor = AdvancedLearningProcessor()
        adv_learning_processor.process_feedback_record(adv_learning_record)
        opt_report = adv_learning_processor.generate_optimization_report()

        return AdvancedPipelineResult(
            Context=context,
            MarketData=data_resp,
            Research=research_res,
            Strategy=strat_eval,
            Risk=risk_assess,
            DecisionReport=decision_report,
            Feedback=feedback,
            OptimizationReport=opt_report,
            ExecutedAt=datetime.now()
        )

    def execute_multi_agent(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Executes the Phase 21 Multi-Agent Intelligence Layer workflow.
        Coordinates Research, Strategy, Risk, Validation, and Learning agents
        using the IntelligenceSupervisor orchestrator.
        """
        if not self._config.SimulationMode:
            raise ValueError(
                "Execution is strictly restricted to simulation mode only. "
                "Real trading, broker connection, and real money operations are prohibited."
            )

        from src.Decision.Intelligence.Agents.models import AgentContext, AgentMessage
        from src.Decision.Intelligence.Agents.agents import (
            ResearchAgent,
            StrategyAnalystAgent,
            RiskAgent,
            ValidationAgent,
            LearningAgent
        )
        from src.Decision.Intelligence.Agents.services import IntelligenceSupervisor, AgentPerformanceTracker

        # Initialize Supervisor and register agents
        supervisor = IntelligenceSupervisor()
        research_agent = ResearchAgent()
        strategy_agent = StrategyAnalystAgent()
        risk_agent = RiskAgent()
        validation_agent = ValidationAgent()
        learning_agent = LearningAgent()

        supervisor.register_agent(research_agent)
        supervisor.register_agent(strategy_agent)
        supervisor.register_agent(risk_agent)
        supervisor.register_agent(validation_agent)
        supervisor.register_agent(learning_agent)

        # Create shared agent context
        agent_context = AgentContext(
            ContextId=f"ctx-agent-{context.Asset}",
            Variables={"asset": context.Asset, "timeframe": context.Timeframe},
            Metadata={"target_risk_profile": context.TargetRiskProfile.RiskToleranceLevel}
        )

        # 1. Execute Research Agent
        msg_init = AgentMessage("msg-1", "PipelineOrchestrator", "ResearchAgent", {"asset": context.Asset})
        res_msg = supervisor.execute_agent_safely("ResearchAgent", msg_init, agent_context)
        if res_msg:
            agent_context = agent_context.enrich("ResearchAgent", "research_sentiment", res_msg.Payload["research_sentiment"])
            agent_context = agent_context.enrich("ResearchAgent", "insights_count", res_msg.Payload["insights_count"])

        # 2. Execute Strategy Agent
        msg_strat_init = AgentMessage(
            "msg-2",
            "PipelineOrchestrator",
            "StrategyAnalystAgent",
            {"asset": context.Asset, "research_sentiment": agent_context.Variables.get("research_sentiment", "neutral")}
        )
        strat_msg = supervisor.execute_agent_safely("StrategyAnalystAgent", msg_strat_init, agent_context)
        if strat_msg:
            agent_context = agent_context.enrich("StrategyAnalystAgent", "strategy_score", strat_msg.Payload["strategy_score"])

        # 3. Execute Risk Agent
        msg_risk_init = AgentMessage(
            "msg-3",
            "PipelineOrchestrator",
            "RiskAgent",
            {
                "asset": context.Asset,
                "strategy_score": agent_context.Variables.get("strategy_score", 0.50),
                "volatility_level": context.Metadata.get("volatility_level", "low")
            }
        )
        risk_msg = supervisor.execute_agent_safely("RiskAgent", msg_risk_init, agent_context)
        if risk_msg:
            agent_context = agent_context.enrich("RiskAgent", "risk_approved", risk_msg.Payload["risk_approved"])

        # 4. Execute Validation Agent
        msg_val_init = AgentMessage(
            "msg-4",
            "PipelineOrchestrator",
            "ValidationAgent",
            {
                "asset": context.Asset,
                "risk_approved": agent_context.Variables.get("risk_approved", True)
            }
        )
        val_msg = supervisor.execute_agent_safely("ValidationAgent", msg_val_init, agent_context)
        if val_msg:
            agent_context = agent_context.enrich("ValidationAgent", "validation_passed", val_msg.Payload["validation_passed"])

        # 5. Execute Learning Agent
        msg_learn_init = AgentMessage(
            "msg-5",
            "PipelineOrchestrator",
            "LearningAgent",
            {
                "asset": context.Asset,
                "observed_result": context.Metadata.get("ActualOutcomeMetric", 0.05)
            }
        )
        learn_msg = supervisor.execute_agent_safely("LearningAgent", msg_learn_init, agent_context)
        if learn_msg:
            agent_context = agent_context.enrich("LearningAgent", "suggestion", learn_msg.Payload["suggestion"])

        # Score agent performances
        performance_tracker = AgentPerformanceTracker()
        for agent_name in supervisor.list_registered_agents():
            performance_tracker.log_agent_performance(agent_name, 1.0, 0.95, 0.90, 0.95)

        return {
            "supervisor": supervisor,
            "agent_context": agent_context,
            "performance_tracker": performance_tracker,
            "is_success": True,
            "executed_at": datetime.now()
        }
