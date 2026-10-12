import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field, replace
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
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation, StrategyScore
from src.Risk.Models.models import RiskProfile, RiskAssessment
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionReason, DecisionState


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
        # Keep the constructor argument for compatibility, but never use the legacy evaluator.
        self._strategy_evaluator = None
        self._risk_engine = risk_engine
        self._decision_engine = decision_engine

        if learning_engine is None:
            from src.Learning.Services.services import LearningProcessor
            self._learning_engine = LearningProcessor()
        else:
            self._learning_engine = learning_engine

        self._config = config or PipelineConfig()

    def _execute_common_steps(self, context: PipelineContext):
        """
        Internal helper sharing the exact steps 1 to 4 to prevent pipeline logic duplication.
        """
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

        # 2. Research telemetry only; no generic strategy/indicator output can authorize trades.
        res_req = ResearchRequest(
            Asset=context.Asset,
            StartTime=data_req.StartTime,
            EndTime=data_req.EndTime,
            Context={"bars_count": len(data_resp.DataPoints), "simulation": self._config.SimulationMode,
                     "timeframe": context.Timeframe, "indicator_independent": True}
        )
        raw_points = list(data_resp.DataPoints or [])
        primitive_observation = {
            "symbol": context.Asset,
            "timeframe": context.Timeframe,
            "bar_count": len(raw_points),
            "latest_price": float(raw_points[-1].Close) if raw_points else None,
            "window_high": max((float(point.High) for point in raw_points), default=None),
            "window_low": min((float(point.Low) for point in raw_points), default=None),
        }
        research_res = ResearchResult(
            Request=res_req,
            Findings={
                "asset_id": context.Asset,
                "status": "completed" if raw_points else "no_data",
                "indicator_independent": True,
                "feature_set": {"features_count": 0, "mode": "primitive_indicator_free"},
                "primitive_observation": primitive_observation,
                "newborn_brain_report": {"status": "DISABLED_NON_BASE", "execution_enabled": False},
                "findings": [], "observations": [], "insights": [], "patterns": [],
            },
            ConfidenceScore=0.0,
            CreatedAt=datetime.now(),
        )

        base_candles = [
            {
                "timestamp": point.Timestamp.isoformat() if hasattr(point.Timestamp, "isoformat") else str(point.Timestamp),
                "open": float(point.Open), "high": float(point.High),
                "low": float(point.Low), "close": float(point.Close),
                "volume": float(point.Volume),
            }
            for point in data_resp.DataPoints
        ]
        from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
        base_report = StrategyOrchestrator().evaluate_all_strategies(
            symbol=context.Asset,
            primary_timeframe=context.Timeframe,
            candles=base_candles,
            all_timeframe_candles={context.Timeframe: base_candles},
        )
        base_candidate = base_report.get("best_candidate")
        base_confidence = (
            max(0.0, min(1.0, float(base_candidate.get("confidence", 0.0)) / 100.0))
            if isinstance(base_candidate, dict) else 0.0
        )
        score = base_confidence if base_candidate else 0.0
        # Evaluate risk before constructing the unified decision payload; a qualified
        # Base candidate must never bypass the risk layer due to ordering of locals.
        proposed_weights = {context.Asset: score}
        risk_assess = self._risk_engine.analyze_risk(proposed_weights, context.TargetRiskProfile)
        findings = dict(research_res.Findings or {})
        findings["indicator_independent"] = True
        findings["decision_authority"] = "BASE_HIERARCHY"
        findings["base_only_report"] = base_report
        findings["base_candidate_available"] = bool(base_candidate)
        base_plan = base_report.get("base_plan") or {}
        direction = str((base_candidate or {}).get("direction", "WAIT")).upper()
        actionable = bool(
            base_candidate
            and direction in ("BUY", "SELL")
            and str(base_plan.get("status", "")).upper() == "PROPOSED"
            and bool(getattr(risk_assess, "IsApproved", False))
        )
        findings["intel_summary"] = {
            "decision_authority": "BASE_HIERARCHY",
            "candidate_available": bool(base_candidate),
            "plan": base_plan,
            "summary": base_report.get("summary") or "No validated Base-only proposal.",
            "execution_enabled": False,
        }
        findings["autonomous_decision"] = {
            "action": direction if actionable else "WAIT",
            "entry": float((base_candidate or {}).get("entry") or 0.0) if actionable else 0.0,
            "stop_loss": float((base_candidate or {}).get("stop_loss") or 0.0) if actionable else 0.0,
            "take_profit": float((base_candidate or {}).get("take_profit") or 0.0) if actionable else 0.0,
            "risk_reward": float((base_candidate or {}).get("risk_reward") or 0.0) if actionable else 0.0,
            "confidence": float((base_candidate or {}).get("confidence") or 0.0) if actionable else 0.0,
            "reasoning": list((base_candidate or {}).get("reasoning") or []) if actionable else [
                str(base_plan.get("reason") or base_report.get("summary") or "No validated Base-only proposal; wait.")
            ],
            "evidence": {"decision_authority": "BASE_HIERARCHY"},
            "execution_enabled": False,
        }
        findings["pipeline_outputs"] = {
            "technical_analysis": {
                "bar_count": len(raw_points),
                "latest_price": primitive_observation.get("latest_price"),
                "indicator_independent": True,
                "features_count": 0,
            },
            "smart_interpretation": {
                "action": findings["autonomous_decision"]["action"],
                "decision_authority": "BASE_HIERARCHY",
                "summary": findings["intel_summary"]["summary"],
            },
        }
        research_res = replace(research_res, Findings=findings)

        # 3. The sole strategy candidate is the canonical hierarchical Base model.
        candidate = StrategyCandidate(
            Id="BASE_HIERARCHY",
            Name="Hierarchical Base Reaction",
            Description=f"Hierarchical Base and costed re-entry reaction for {context.Asset}",
            ResearchContext={"base_report": base_report, "base_candidate": base_candidate},
            CreatedAt=datetime.now(),
            EvaluationStatus="Validated" if base_candidate else "NoAction"
        )
        strat_eval = StrategyEvaluation(
            StrategyId="BASE_HIERARCHY",
            Score=StrategyScore(
                OverallScore=score,
                Confidence=score,
                Criteria={"BASE_HIERARCHY_EVIDENCE": score},
            ),
            EvaluationNotes=(
                "Validated Base-only proposal." if base_candidate
                else "No validated Base-only proposal; no legacy strategy fallback."
            ),
            EvaluatedAt=datetime.now(),
        )

        # 4. Risk Layer Verification was evaluated before the signal payload was built.
        return data_resp, research_res, candidate, strat_eval, risk_assess, proposed_weights

    def execute(self, context: PipelineContext) -> PipelineResult:
        data_resp, research_res, candidate, strat_eval, risk_assess, proposed_weights = self._execute_common_steps(context)

        # 5. Decision Layer Integration
        dec_context = DecisionContext(
            StrategyId=candidate.Id,
            AssetWeights=proposed_weights if risk_assess.IsApproved else {},
            TargetRiskProfile=context.TargetRiskProfile.RiskToleranceLevel
        )
        decision_res = self._decision_engine.evaluate_decision(dec_context)
        if not research_res.Findings.get("base_candidate_available"):
            decision_res = replace(
                decision_res,
                State=DecisionState.NO_ACTION,
                Reason=DecisionReason(
                    AnalysisSummary="No validated hierarchical Base proposal; legacy strategies are disabled.",
                    RiskAuditStatus="BASE_ONLY_WAIT",
                    ConfidenceScore=0.0,
                ),
            )

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
        data_resp, research_res, candidate, strat_eval, risk_assess, proposed_weights = self._execute_common_steps(context)

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
        if not research_res.Findings.get("base_candidate_available"):
            decision_report = replace(decision_report, State=DecisionState.NO_ACTION, Confidence=0.0)

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
