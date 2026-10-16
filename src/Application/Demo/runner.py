import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint
from src.Research.MarketAnalysis.Models.models import ResearchRequest, ResearchResult
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation
from src.Risk.Services.services import RiskAnalyzer
from src.Risk.Models.models import RiskProfile, RiskAssessment
from src.Decision.Intelligence.engine import DecisionEngine as AdvancedDecisionEngine
from src.Decision.Intelligence.models import DecisionIntelligenceContext, DecisionIntelligenceReport
from src.Application.Validation.services import ComplianceChecker, IntelligenceValidator
from src.Application.Explainability.explainability import (
    ExplainableIntelligenceReport,
    ExplanationNode,
    ResearchExplanationLayer,
    RiskExplanationLayer,
    ValidationExplanationLayer,
    DecisionTraceEngine,
    EvidenceVisualizationModels
)

from src.Application.Demo.interfaces import IDemoScenarioRunner
from src.Application.Demo.models import DemoScenario, DemoExecutionResult, DemoStepResult


class DemoMarketDataProvider(IMarketDataProvider):
    """Custom Market Data Provider serving exactly the scenario price data."""

    def __init__(self, price_data: List[MarketDataPoint]) -> None:
        self._price_data = price_data

    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        # No synthetic fallback prices: absent scenario data means no analysis/trade.
        if not self._price_data:
            return MarketDataResponse(
                Request=request,
                DataPoints=[],
                RetrievedAt=datetime.now()
            )
        return MarketDataResponse(
            Request=request,
            DataPoints=self._price_data,
            RetrievedAt=datetime.now()
        )


class DemoScenarioRunner(IDemoScenarioRunner):
    """Orchestrates end-to-end continuous intelligence demo scenario execution."""

    def __init__(self) -> None:
        # Demo decisions are sourced exclusively from the canonical Base hierarchy.
        self.risk_analyzer = RiskAnalyzer()
        self.decision_engine = AdvancedDecisionEngine()
        self.compliance_checker = ComplianceChecker()
        self.validator = IntelligenceValidator()

    def run_scenario(self, scenario: DemoScenario) -> DemoExecutionResult:
        start_time = datetime.now()
        step_results: List[DemoStepResult] = []
        success = True

        # Layer objects to trace
        market_data_resp: Optional[MarketDataResponse] = None
        feature_set: Optional[Any] = None
        research_res: Optional[ResearchResult] = None
        strategy_eval: Optional[StrategyEvaluation] = None
        risk_assess: Optional[RiskAssessment] = None
        decision_report: Optional[DecisionIntelligenceReport] = None
        compliance_audit: Optional[Any] = None
        explainable_report: Optional[ExplainableIntelligenceReport] = None
        base_only_report: Optional[Dict[str, Any]] = None
        base_only_candidate: Optional[Dict[str, Any]] = None

        # ----------------------------------------------------
        # STAGE 1: Input Ingestion
        # ----------------------------------------------------
        st_time = time.perf_counter()
        try:
            data_provider = DemoMarketDataProvider(scenario.price_data)
            lookback_start = start_time - timedelta(days=30)
            data_req = MarketDataRequest(
                Asset=scenario.asset,
                StartTime=lookback_start,
                EndTime=start_time,
                Timeframe=scenario.timeframe
            )
            market_data_resp = data_provider.retrieve_market_data(data_req)
            dur = (time.perf_counter() - st_time) * 1000.0
            step_results.append(
                DemoStepResult(
                    step_name="Input",
                    status="SUCCESS",
                    payload={
                        "asset": scenario.asset,
                        "timeframe": scenario.timeframe,
                        "data_points_count": len(market_data_resp.DataPoints),
                        "latest_close": market_data_resp.DataPoints[-1].Close if market_data_resp.DataPoints else 0.0
                    },
                    duration_ms=dur
                )
            )
        except Exception as e:
            success = False
            dur = (time.perf_counter() - st_time) * 1000.0
            step_results.append(DemoStepResult("Input", "FAILED", None, dur, str(e)))

        # ----------------------------------------------------
        # STAGE 2: Raw Price Structure (indicator-free)
        # ----------------------------------------------------
        if success and market_data_resp:
            st_time = time.perf_counter()
            try:
                # Preserve raw OHLC facts only. No feature pipeline or indicator calculation.
                points = market_data_resp.DataPoints
                feature_set = {
                    "asset": scenario.asset,
                    "timeframe": scenario.timeframe,
                    "bar_count": len(points),
                    "latest_price": float(points[-1].Close),
                    "window_high": max(float(point.High) for point in points),
                    "window_low": min(float(point.Low) for point in points),
                }
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(
                    DemoStepResult(
                        step_name="Price Structure",
                        status="SUCCESS",
                        payload={"price_facts": feature_set, "indicator_count": 0},
                        duration_ms=dur
                    )
                )
            except Exception as e:
                success = False
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(DemoStepResult("Price Structure", "FAILED", None, dur, str(e)))

        # ----------------------------------------------------
        # STAGE 3: Research Intelligence
        # ----------------------------------------------------
        if success and feature_set:
            st_time = time.perf_counter()
            try:
                # Research stage records raw facts only; Base-only decision evaluation
                # happens in the next stage and is the sole source of trade candidates.
                res_req = ResearchRequest(
                    Asset=scenario.asset,
                    StartTime=lookback_start,
                    EndTime=start_time,
                    Context={"timeframe": scenario.timeframe, "price_facts": feature_set}
                )
                research_res = ResearchResult(
                    Request=res_req,
                    Findings={
                        "asset_id": scenario.asset,
                        "status": "completed",
                        "indicator_independent": True,
                        "primitive_observation": dict(feature_set or {}),
                        "findings": [],
                        "observations": [],
                        "insights": [],
                        "patterns": [],
                        "observations_count": 1 if feature_set else 0,
                        "patterns_count": 0,
                        "insights_count": 0,
                    },
                    ConfidenceScore=0.0,
                    CreatedAt=datetime.now(),
                )
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(
                    DemoStepResult(
                        step_name="Base-only Research",
                        status="SUCCESS",
                        payload={
                            "price_facts": research_res.Findings["primitive_observation"],
                            "observations_count": research_res.Findings["observations_count"],
                            "patterns_count": 0,
                            "insights_count": 0,
                            "decision_authority": "BASE_HIERARCHY",
                        },
                        duration_ms=dur
                    )
                )
            except Exception as e:
                success = False
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(DemoStepResult("Research", "FAILED", None, dur, str(e)))

        # ----------------------------------------------------
        # STAGE 4: Strategy Evaluation
        # ----------------------------------------------------
        if success and research_res:
            st_time = time.perf_counter()
            try:
                # A generic research/strategy score is not sufficient to approve a
                # trading decision. Only the canonical Base hierarchy may provide
                # an actionable candidate; insufficient history or model evidence
                # must fail closed to NoAction.
                base_candles = [
                    {
                        "timestamp": point.Timestamp.isoformat() if hasattr(point.Timestamp, "isoformat") else str(point.Timestamp),
                        "open": float(point.Open),
                        "high": float(point.High),
                        "low": float(point.Low),
                        "close": float(point.Close),
                        "volume": float(point.Volume),
                    }
                    for point in (market_data_resp.DataPoints if market_data_resp else [])
                ]
                try:
                    from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
                    base_only_report = StrategyOrchestrator().evaluate_all_strategies(
                        symbol=scenario.asset,
                        primary_timeframe=scenario.timeframe,
                        candles=base_candles,
                        all_timeframe_candles={scenario.timeframe: base_candles},
                    )
                    base_only_candidate = base_only_report.get("best_candidate")
                except Exception as base_error:
                    # Diagnostics are recorded, but a failure in the authoritative
                    # Base-only gate can never fall back to a legacy strategy.
                    base_only_report = {"model_status": "BASE_ONLY_ANALYSIS_FAILED", "error_type": type(base_error).__name__}
                    base_only_candidate = None

                # The generic legacy strategy evaluator is intentionally bypassed.
                # A Base hierarchy proposal is the only source of strategy evidence.
                from src.Strategy.Models.models import StrategyScore
                base_confidence = (
                    max(0.0, min(1.0, float(base_only_candidate.get("confidence", 0.0)) / 100.0))
                    if isinstance(base_only_candidate, dict) else 0.0
                )
                base_score = base_confidence if base_only_candidate else 0.0
                candidate = StrategyCandidate(
                    Id=f"base-{scenario.asset}",
                    Name=f"Hierarchical Base Reaction for {scenario.asset}",
                    Description="Only the canonical hierarchical Base/reaction model can propose a trade.",
                    ResearchContext={"base_report": base_only_report, "base_candidate": base_only_candidate},
                    CreatedAt=datetime.now(),
                    EvaluationStatus="Validated" if base_only_candidate else "NoAction"
                )
                strategy_eval = StrategyEvaluation(
                    StrategyId="BASE_HIERARCHY",
                    Score=StrategyScore(
                        OverallScore=base_score,
                        Confidence=base_score,
                        Criteria={"BASE_HIERARCHY_EVIDENCE": base_score},
                    ),
                    EvaluationNotes=(
                        "Validated Base-only proposal." if base_only_candidate
                        else "No validated Base-only proposal; no legacy strategy fallback."
                    ),
                    EvaluatedAt=datetime.now(),
                )

                # Induce Conflict: override strategy overall score if conflicting signals scenario is active
                if scenario.parameters.get("induce_conflict"):
                    from src.Strategy.Models.models import StrategyScore
                    from src.Strategy.Evaluation.criteria import EvaluationCriteria
                    low_score = StrategyScore(
                        OverallScore=0.15,  # strong mismatch
                        Confidence=0.90,
                        Criteria={EvaluationCriteria.STABILITY: 0.15}
                    )
                    strategy_eval = StrategyEvaluation(
                        StrategyId=strategy_eval.StrategyId,
                        Score=low_score,
                        EvaluationNotes="Conflict Induced: Very weak trend score.",
                        EvaluatedAt=datetime.now()
                    )

                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(
                    DemoStepResult(
                        step_name="Strategy Evaluation",
                        status="SUCCESS",
                        payload={
                            "strategy_id": strategy_eval.StrategyId,
                            "overall_score": strategy_eval.Score.OverallScore,
                            "confidence": strategy_eval.Score.Confidence,
                            "evaluation_notes": strategy_eval.EvaluationNotes,
                            "base_model_status": (base_only_report or {}).get("model_status", "UNKNOWN"),
                            "base_candidate_available": bool(base_only_candidate)
                        },
                        duration_ms=dur
                    )
                )
            except Exception as e:
                success = False
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(DemoStepResult("Strategy Evaluation", "FAILED", None, dur, str(e)))

        # ----------------------------------------------------
        # STAGE 5: Risk Analysis
        # ----------------------------------------------------
        if success and strategy_eval:
            st_time = time.perf_counter()
            try:
                # Risk allocation is derived from the Base-only evidence score.
                # The explicit HighVolatility safety scenario tests the restrictive
                # exposure gate; it does not create a trading direction or setup.
                scenario_type = scenario.parameters.get("scenario_type")
                proposed_weight = strategy_eval.Score.OverallScore
                if scenario_type == "HighVolatility":
                    proposed_weight = max(proposed_weight, 0.50)
                proposed_weights = {scenario.asset: proposed_weight}
                if scenario.parameters.get("restrict_risk") or scenario_type == "HighVolatility":
                    profile = RiskProfile("Low", 0.30, 0.15)  # Restrictive limit
                else:
                    profile = RiskProfile("Moderate", 1.0, 0.90)  # Safe limit

                risk_assess = self.risk_analyzer.analyze_risk(proposed_weights, profile)
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(
                    DemoStepResult(
                        step_name="Risk Analysis",
                        status="SUCCESS",
                        payload={
                            "is_approved": risk_assess.IsApproved,
                            "risk_profile": risk_assess.RiskProfileName,
                            "expected_volatility": risk_assess.PortfolioRiskMetrics.ExpectedVolatility,
                            "max_drawdown": risk_assess.PortfolioRiskMetrics.HistoricalDrawdown,
                            "assessment_notes": risk_assess.AssessmentNotes
                        },
                        duration_ms=dur
                    )
                )
            except Exception as e:
                success = False
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(DemoStepResult("Risk Analysis", "FAILED", None, dur, str(e)))

        # ----------------------------------------------------
        # STAGE 6: Decision Intelligence
        # ----------------------------------------------------
        if success and strategy_eval and risk_assess and research_res:
            st_time = time.perf_counter()
            try:
                # Reconstruct models inside context
                from src.Research.MarketAnalysis.Models.models import MarketInsight
                from src.Research.Engine.models import PatternObservation

                insights = []
                for ins in research_res.Findings.get("insights", []):
                    insights.append(
                        MarketInsight(
                            Category=ins.get("category", "General"),
                            Description=ins.get("description", ""),
                            Confidence=ins.get("confidence", 0.5),
                            CreatedAt=datetime.now()
                        )
                    )

                patterns = []
                for pat in research_res.Findings.get("patterns", []):
                    patterns.append(
                        PatternObservation(
                            PatternName=pat.get("name", ""),
                            Description=pat.get("description", ""),
                            Confidence=pat.get("confidence", 0.5),
                            Timestamp=datetime.now(),
                            MatchedFeatures=pat.get("matched_features", [])
                        )
                    )

                intel_context = DecisionIntelligenceContext(
                    ResearchInsights=insights,
                    PatternObservations=patterns,
                    StrategyEvaluations=[strategy_eval],
                    RiskAssessments=[risk_assess],
                    MarketConditions={"timeframe": scenario.timeframe},
                    HistoricalEvidence={},
                    Metadata={"asset": scenario.asset}
                )

                decision_report = self.decision_engine.evaluate_intelligence_context(intel_context)

                # Explicit safety scenarios remain risk gates. Otherwise, absent
                # Base evidence always means NoAction; generic conflict signals cannot
                # promote a non-Base strategy or override the Base-only authority.
                state_override = None
                scenario_type = scenario.parameters.get("scenario_type")
                if scenario_type == "HighVolatility":
                    state_override = "Rejected"
                elif scenario_type == "LowLiquidity":
                    state_override = "ReviewRequired"
                elif scenario_type == "TrendReversal" and decision_report.State != "Rejected":
                    state_override = "ReviewRequired"
                elif not base_only_candidate:
                    state_override = "NoAction"
                elif decision_report.ConflictAnalysis.ConflictDetected:
                    state_override = "ReviewRequired"

                if state_override:
                    from dataclasses import replace
                    replacements = {"State": state_override}
                    if state_override == "NoAction":
                        replacements["Confidence"] = 0.0
                    decision_report = replace(decision_report, **replacements)

                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(
                    DemoStepResult(
                        step_name="Decision",
                        status="SUCCESS",
                        payload={
                            "report_id": decision_report.ReportId,
                            "state": str(decision_report.State),
                            "confidence": decision_report.Confidence,
                            "quality_score": decision_report.QualityScore.OverallScore if hasattr(decision_report, "QualityScore") else 0.90,
                            "conflict_detected": decision_report.ConflictAnalysis.ConflictDetected if hasattr(decision_report, "ConflictAnalysis") else False,
                            "conflict_type": decision_report.ConflictAnalysis.ConflictType if hasattr(decision_report, "ConflictAnalysis") else "None"
                        },
                        duration_ms=dur
                    )
                )
            except Exception as e:
                success = False
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(DemoStepResult("Decision", "FAILED", None, dur, str(e)))

        # ----------------------------------------------------
        # STAGE 7: Validation Layer
        # ----------------------------------------------------
        if success and decision_report:
            st_time = time.perf_counter()
            try:
                compliance_audit = self.compliance_checker.perform_compliance_audit()
                layer_validations = self.validator.validate_all_layers(
                    data_points=market_data_resp.DataPoints if market_data_resp else [],
                    insights=intel_context.ResearchInsights if 'intel_context' in locals() else [],
                    evaluation=strategy_eval,
                    risk_assess=risk_assess,
                    decision_report=decision_report,
                    learning_report=decision_report  # reuse report
                )
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(
                    DemoStepResult(
                        step_name="Validation",
                        status="SUCCESS",
                        payload={
                            "is_compliant": compliance_audit.IsCompliant,
                            "layer_validations": layer_validations,
                            "violations": compliance_audit.Violations
                        },
                        duration_ms=dur
                    )
                )
            except Exception as e:
                success = False
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(DemoStepResult("Validation", "FAILED", None, dur, str(e)))

        # ----------------------------------------------------
        # STAGE 8: Explainable Report
        # ----------------------------------------------------
        if success and decision_report:
            st_time = time.perf_counter()
            try:
                # Construct explanations
                res_layer = ResearchExplanationLayer()
                risk_layer = RiskExplanationLayer()
                val_layer = ValidationExplanationLayer()

                findings_list = [obs.get("observations", {}).get("condition", "Baseline") for obs in (research_res.Findings.get("observations") if research_res else [])] if research_res else ["General market observation"]
                exp_nodes = [
                    res_layer.explain_research(findings_list),
                    risk_layer.explain_risk(risk_assess.IsApproved if risk_assess else False, risk_assess.AssessmentNotes if risk_assess else ""),
                    val_layer.explain_validation(compliance_audit.IsCompliant if compliance_audit else True, 0.98)
                ]

                trace_engine = DecisionTraceEngine()
                trace_map = trace_engine.generate_trace({
                    "scenario": scenario.scenario_id,
                    "final_decision_state": str(decision_report.State),
                    "confidence": decision_report.Confidence
                })

                explainable_report = ExplainableIntelligenceReport(
                    report_id=f"exp-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.now(),
                    final_decision_state=str(decision_report.State),
                    overall_confidence=decision_report.Confidence,
                    explanations=exp_nodes,
                    visual_evidence_mapping=trace_map
                )
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(
                    DemoStepResult(
                        step_name="Final Explainable Report",
                        status="SUCCESS",
                        payload={
                            "report_id": explainable_report.report_id,
                            "final_state": explainable_report.final_decision_state,
                            "explanations_count": len(explainable_report.explanations),
                            "nodes_visited": trace_map.get("nodes_visited", [])
                        },
                        duration_ms=dur
                    )
                )
            except Exception as e:
                success = False
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(DemoStepResult("Final Explainable Report", "FAILED", None, dur, str(e)))

        # Compile final DemoExecutionResult
        end_time = datetime.now()
        final_state = str(decision_report.State) if decision_report else "NoAction"
        final_confidence = decision_report.Confidence if decision_report else 0.0

        return DemoExecutionResult(
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            start_time=start_time,
            end_time=end_time,
            steps=step_results,
            final_decision_state=final_state,
            overall_confidence=final_confidence,
            explainable_report=explainable_report,
            success=success
        )
