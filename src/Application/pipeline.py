from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse
from src.Research.MarketAnalysis.Models.models import ResearchRequest, ResearchResult
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation
from src.Risk.Models.models import RiskProfile, RiskAssessment
from src.Decision.Models.models import DecisionContext, DecisionResult

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
    """Represents the end-to-end outcome logs and the final DecisionResult of the pipeline."""
    Context: PipelineContext
    MarketData: MarketDataResponse
    Research: ResearchResult
    Strategy: StrategyEvaluation
    Risk: RiskAssessment
    Decision: DecisionResult
    ExecutedAt: datetime


class IntelligencePipeline:
    """
    Orchestration controller coordinating the flow across Data, Research, Strategy, Risk, and Decision systems.
    Adheres strictly to the clean unidirectional APES-FIN pipeline rules.
    """
    def __init__(
        self,
        data_provider: Any,         # IMarketDataProvider
        research_engine: Any,       # IResearchEngine
        strategy_evaluator: Any,    # IStrategyEvaluator
        risk_engine: Any,           # IRiskEngine
        decision_engine: Any        # IDecisionEngine
    ) -> None:
        self._data_provider = data_provider
        self._research_engine = research_engine
        self._strategy_evaluator = strategy_evaluator
        self._risk_engine = risk_engine
        self._decision_engine = decision_engine

    def execute(self, context: PipelineContext) -> PipelineResult:
        # 1. Ingest/Data Layer Acquisition
        data_req = MarketDataRequest(
            Asset=context.Asset,
            StartTime=context.StartTime - timedelta_days_or_default(context),
            EndTime=context.StartTime,
            Timeframe=context.Timeframe
        )
        data_resp = self._data_provider.retrieve_market_data(data_req)

        # 2. Research Layer Interpretation
        res_req = ResearchRequest(
            Asset=context.Asset,
            StartTime=data_req.StartTime,
            EndTime=data_req.EndTime,
            Context={"bars_count": len(data_resp.DataPoints)}
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

        return PipelineResult(
            Context=context,
            MarketData=data_resp,
            Research=research_res,
            Strategy=strat_eval,
            Risk=risk_assess,
            Decision=decision_res,
            ExecutedAt=datetime.now()
        )

def timedelta_days_or_default(context: PipelineContext) -> datetime:
    """Helper to cleanly calculate standard historical timeframe boundaries."""
    from datetime import timedelta
    return timedelta(days=10)
