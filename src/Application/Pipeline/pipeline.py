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

        return AdvancedPipelineResult(
            Context=context,
            MarketData=data_resp,
            Research=research_res,
            Strategy=strat_eval,
            Risk=risk_assess,
            DecisionReport=decision_report,
            Feedback=feedback,
            ExecutedAt=datetime.now()
        )
