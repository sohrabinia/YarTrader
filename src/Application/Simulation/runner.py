from datetime import datetime
from typing import List, Optional, Dict, Any

from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchEngine
from src.Research.MarketAnalysis.Services.services import ResearchProcessor
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
from src.Risk.Interfaces.interfaces import IRiskEngine
from src.Risk.Services.services import RiskAnalyzer
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Engine.engine import DecisionEngine
from src.Learning.Interfaces.interfaces import ILearningEngine
from src.Learning.Services.services import LearningProcessor
from src.Application.Pipeline.pipeline import IntelligencePipeline, PipelineContext, PipelineConfig

from src.Application.Simulation.models import (
    SimulationEnvironmentGuard,
    MarketScenario,
    ScenarioInput,
    ScenarioResult,
    SimulationReport,
    ExecutionBlockedError
)


class ScenarioMarketDataProvider(IMarketDataProvider):
    """Scenario-specific provider yielding pre-loaded price data for simulation validation."""
    def __init__(self, price_data: List[MarketDataPoint]):
        self._price_data = price_data

    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        # Filter points belonging to the asset request
        matched_points = [p for p in self._price_data if p.AssetId == request.Asset]
        if not matched_points:
            # Fallback: rewrite AssetId of points to request.Asset
            matched_points = [
                MarketDataPoint(
                    AssetId=request.Asset,
                    Timestamp=p.Timestamp,
                    Open=p.Open,
                    High=p.High,
                    Low=p.Low,
                    Close=p.Close,
                    Volume=p.Volume
                )
                for p in self._price_data
            ]
        return MarketDataResponse(
            Request=request,
            DataPoints=matched_points,
            RetrievedAt=datetime.now()
        )


class ScenarioRunner:
    """
    Orchestrates historical or synthetic simulation scenario execution over the IntelligencePipeline.
    Ensures safe offline verification without placing any broker trades.
    """
    def __init__(
        self,
        research_engine: Optional[IResearchEngine] = None,
        strategy_evaluator: Optional[IStrategyEvaluator] = None,
        risk_engine: Optional[IRiskEngine] = None,
        decision_engine: Optional[IDecisionEngine] = None,
        learning_engine: Optional[ILearningEngine] = None
    ) -> None:
        self._research_engine = research_engine or ResearchProcessor()
        self._strategy_evaluator = strategy_evaluator or StrategyEvaluator()
        self._risk_engine = risk_engine or RiskAnalyzer()
        self._decision_engine = decision_engine or DecisionEngine()
        self._learning_engine = learning_engine or LearningProcessor()

    def run_scenario(self, scenario_input: ScenarioInput) -> ScenarioResult:
        """
        Loads the scenario, checks safety, sets up custom providers,
        runs the unidirectional pipeline, and returns the result.
        """
        # Validate Scenario Input
        scenario = scenario_input.Scenario
        if not scenario.Asset or not scenario.PriceData:
            raise ValueError("Invalid Scenario: Asset and PriceData must not be empty.")

        # Ensure environment guard check passes
        SimulationEnvironmentGuard.verify_safety()

        # Build local mock provider that serving exactly the pre-loaded price series
        mock_data_provider = ScenarioMarketDataProvider(scenario.PriceData)

        # Build config & pipeline
        config = PipelineConfig(
            SimulationMode=True,
            LookbackDays=scenario_input.LookbackDays
        )
        pipeline = IntelligencePipeline(
            data_provider=mock_data_provider,
            research_engine=self._research_engine,
            strategy_evaluator=self._strategy_evaluator,
            risk_engine=self._risk_engine,
            decision_engine=self._decision_engine,
            learning_engine=self._learning_engine,
            config=config
        )

        # Form context
        # Use upper bound of time range as starting simulation reference
        start_time = scenario.TimeRange[1] if len(scenario.TimeRange) > 1 else datetime.now()
        context = PipelineContext(
            StartTime=start_time,
            Asset=scenario.Asset,
            Timeframe="H1",
            TargetRiskProfile=scenario_input.TargetRiskProfile,
            Metadata=scenario_input.Metadata
        )

        # Run pipeline
        pipeline_result = pipeline.execute(context)

        # Collect outcome
        outcome = pipeline_result.Feedback.ActualOutcomeMetric if pipeline_result.Feedback else 0.0

        return ScenarioResult(
            PipelineResult=pipeline_result,
            ExecutionPrevented=True,
            OutcomeMetric=outcome
        )

    def generate_report(self, result: ScenarioResult) -> SimulationReport:
        """Translates a ScenarioResult into a clean, audit-friendly SimulationReport."""
        pipeline_res = result.PipelineResult
        context = pipeline_res.Context
        scenario_info = {
            "Asset": context.Asset,
            "ExecutedAt": datetime.now().isoformat(),
            "DataPointsEvaluated": len(pipeline_res.MarketData.DataPoints)
        }

        research_sum = (
            f"Asset: {context.Asset}. "
            f"Research completed successfully. "
            f"Confidence Score: {pipeline_res.Research.ConfidenceScore:.2f}. "
            f"Findings status: {pipeline_res.Research.Findings.get('status', 'Unknown')}."
        )

        strat_sum = (
            f"Evaluated Strategy Candidate on {context.Asset}. "
            f"Overall Score: {pipeline_res.Strategy.Score.OverallScore:.2f}. "
            f"Notes: {pipeline_res.Strategy.EvaluationNotes}."
        )

        risk_sum = (
            f"Status: {'APPROVED' if pipeline_res.Risk.IsApproved else 'REJECTED'}. "
            f"Target Profile: {pipeline_res.Risk.RiskProfileName}. "
            f"Audit notes: {pipeline_res.Risk.AssessmentNotes}."
        )

        dec_sum = (
            f"Final Decision State: {pipeline_res.Decision.State}. "
            f"Reasoning summary: {pipeline_res.Decision.Reason.AnalysisSummary}."
        )

        learn_sum = "No feedback generated."
        if pipeline_res.Feedback:
            learn_sum = (
                f"Recorded outcome metric: {pipeline_res.Feedback.ActualOutcomeMetric:.2f}. "
                f"Feedback recorded at: {pipeline_res.Feedback.RecordedAt}."
            )

        return SimulationReport(
            ScenarioInfo=scenario_info,
            PipelineStatus="Success",
            ResearchSummary=research_sum,
            StrategySummary=strat_sum,
            RiskSummary=risk_sum,
            DecisionSummary=dec_sum,
            LearningFeedbackSummary=learn_sum,
            ExecutionPreventionStatus="GUARANTEED_SAFE_BY_SIMULATION_ENVIRONMENT_GUARD"
        )
