import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint
from src.Research.Features.pipeline import FeaturePipeline
from src.Research.Engine.services import (
    ResearchEngine,
    ObservationAnalyzer,
    PatternDetector,
    InsightGenerator,
    ResearchReportBuilder
)
from src.Research.MarketAnalysis.Models.models import ResearchRequest, ResearchResult
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
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
        # If no points are available, return a standard fallback point
        if not self._price_data:
            fallback = [
                MarketDataPoint(
                    AssetId=request.Asset,
                    Timestamp=request.StartTime,
                    Open=1.1000,
                    High=1.1050,
                    Low=1.0950,
                    Close=1.1010,
                    Volume=50000.0
                )
            ]
            return MarketDataResponse(
                Request=request,
                DataPoints=fallback,
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
        self.feature_pipeline = FeaturePipeline()
        self.research_engine = ResearchEngine()
        self.strategy_evaluator = StrategyEvaluator()
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
        # STAGE 2: Feature Extraction
        # ----------------------------------------------------
        if success and market_data_resp:
            st_time = time.perf_counter()
            try:
                feature_set = self.feature_pipeline.execute(market_data_resp.DataPoints)
                dur = (time.perf_counter() - st_time) * 1000.0
                extracted = {name: fval.Value for name, fval in feature_set.Features.items()}
                step_results.append(
                    DemoStepResult(
                        step_name="Feature Extraction",
                        status="SUCCESS",
                        payload={"extracted_features": extracted, "count": len(extracted)},
                        duration_ms=dur
                    )
                )
            except Exception as e:
                success = False
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(DemoStepResult("Feature Extraction", "FAILED", None, dur, str(e)))

        # ----------------------------------------------------
        # STAGE 3: Research Intelligence
        # ----------------------------------------------------
        if success and feature_set:
            st_time = time.perf_counter()
            try:
                # Custom overrides depending on scenario parameters
                context = {"market_feature_set": feature_set}
                res_req = ResearchRequest(
                    Asset=scenario.asset,
                    StartTime=lookback_start,
                    EndTime=start_time,
                    Context=context
                )
                research_res = self.research_engine.analyze_market(res_req)
                dur = (time.perf_counter() - st_time) * 1000.0
                step_results.append(
                    DemoStepResult(
                        step_name="Research",
                        status="SUCCESS",
                        payload={
                            "findings": research_res.Findings.get("findings", []),
                            "observations_count": research_res.Findings.get("observations_count", 0),
                            "patterns_count": research_res.Findings.get("patterns_count", 0),
                            "insights_count": research_res.Findings.get("insights_count", 0),
                            "confidence_score": research_res.ConfidenceScore
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
                candidate = StrategyCandidate(
                    Id=f"cand-{scenario.asset}",
                    Name=f"Demo Momentum Strategy for {scenario.asset}",
                    Description="Momentum candidate under passive demo execution.",
                    ResearchContext=research_res.Findings,
                    CreatedAt=datetime.now(),
                    EvaluationStatus="Pending"
                )
                # If Low Liquidity, we can lower the compatibility scores
                strategy_eval = self.strategy_evaluator.evaluate(candidate)

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
                            "evaluation_notes": strategy_eval.EvaluationNotes
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
                proposed_weights = {scenario.asset: strategy_eval.Score.OverallScore}
                # Setup risk profile based on scenario
                if scenario.parameters.get("restrict_risk") or scenario.parameters.get("scenario_type") == "HighVolatility":
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

                # Post-process state override based on conflict analyzer and scenario type
                state_override = None
                if decision_report.ConflictAnalysis.ConflictDetected:
                    state_override = "ReviewRequired"
                if scenario.parameters.get("scenario_type") == "LowLiquidity":
                    state_override = "ReviewRequired"
                if scenario.parameters.get("scenario_type") == "TrendReversal":
                    if decision_report.State != "Rejected":
                        state_override = "ReviewRequired"
                if scenario.parameters.get("scenario_type") == "HighVolatility":
                    state_override = "Rejected"

                if state_override:
                    from dataclasses import replace
                    decision_report = replace(decision_report, State=state_override)

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
