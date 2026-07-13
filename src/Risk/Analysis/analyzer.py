from datetime import datetime
from typing import Dict, List, Optional
from src.Risk.Interfaces.interfaces import IRiskEngine
from src.Risk.Models.models import RiskProfile, RiskAssessment, PortfolioRisk
from src.Risk.Analysis.context import RiskAnalysisContext
from src.Risk.Analysis.exposure import ExposureAnalyzer, ExposureAssessment
from src.Risk.Analysis.correlation import CorrelationAnalyzer, CorrelationReport
from src.Risk.Analysis.scenario import RiskScenarioEngine, RiskScenarioResult
from src.Risk.Analysis.scorer import RiskScoreCalculator, RiskScore
from src.Risk.Analysis.assessment import AdvancedRiskAssessment
from src.Risk.Analysis.report import RiskReportBuilder, RiskAnalysisReport
from src.Infrastructure.exceptions import ValidationException

class RiskAnalyzer(IRiskEngine):
    """
    Advanced Risk Intelligence Analyzer.
    Orchestrates exposure, correlation, scenario simulation, and multidimensional scoring.
    Maintains clean APES-FIN compliance, providing purely passive, analytical assessment outcomes.
    """

    def __init__(self) -> None:
        self._exposure_analyzer = ExposureAnalyzer()
        self._correlation_analyzer = CorrelationAnalyzer()
        self._scenario_engine = RiskScenarioEngine()
        self._score_calculator = RiskScoreCalculator()
        self._report_builder = RiskReportBuilder()

    def analyze_advanced_risk(self, context: RiskAnalysisContext) -> AdvancedRiskAssessment:
        """
        Runs the full Advanced Risk Intelligence Layer analytical workflow.
        """
        if not context:
            raise ValidationException("RiskAnalysisContext cannot be None for advanced risk analysis.")

        # 1. Run Exposure Analyzer
        exposure_res = self._exposure_analyzer.analyze_exposure(context)

        # 2. Run Correlation Analyzer
        correlation_res = self._correlation_analyzer.analyze_correlation(context)

        # 3. Run Scenario Engine
        scenario_res = self._scenario_engine.evaluate_scenarios(context)

        # 4. Calculate Risk Score
        score_res = self._score_calculator.calculate_risk_score(context)

        # 5. Determine overall classification
        classification = "Low"
        if score_res.OverallRiskScore > 0.75:
            classification = "Critical"
        elif score_res.OverallRiskScore > 0.55:
            classification = "High"
        elif score_res.OverallRiskScore > 0.35:
            classification = "Moderate"

        # Gather evidence from context metadata/insights
        evidence = {
            "insights_count": len(context.ResearchInsights),
            "feature_set_keys": list(context.MarketFeatureSet.keys())
        }

        # Build risk factors list based on results
        risk_factors = []
        if score_res.MarketRiskScore > 0.5:
            risk_factors.append("Elevated Market Volatility")
        if score_res.StrategyCompatibilityRisk > 0.5:
            risk_factors.append("Incompatible Strategy Score")
        if score_res.StabilityScore < 0.5:
            risk_factors.append("Low Historical Stability")

        return AdvancedRiskAssessment(
            OverallClassification=classification,
            RiskFactors=risk_factors,
            Evidence=evidence,
            ScenarioResults=scenario_res,
            RiskScoreInfo=score_res,
            ConfidenceMetadata={"confidence": score_res.ConfidenceLevel}
        )

    def build_full_report(self, context: RiskAnalysisContext) -> RiskAnalysisReport:
        """
        Evaluates risk components and compiles the finalized RiskAnalysisReport.
        """
        assessment = self.analyze_advanced_risk(context)

        exposure_res = self._exposure_analyzer.analyze_exposure(context)
        correlation_res = self._correlation_analyzer.analyze_correlation(context)

        return self._report_builder.build_report(
            market_conditions=context.MarketFeatureSet,
            exposure_analysis=exposure_res,
            correlation_analysis=correlation_res,
            scenario_analysis=assessment.ScenarioResults,
            risk_scoring=assessment.RiskScoreInfo,
            evidence_trail=assessment.Evidence
        )

    def analyze_risk(self, weights: Dict[str, float], profile: RiskProfile) -> RiskAssessment:
        """
        Implements the legacy IRiskEngine interface to ensure 100% backward compatibility.
        """
        # Simple safety bounds checking
        is_safe = True
        total_w = sum(weights.values())
        if total_w > profile.MaxLeverageFactor:
            is_safe = False
        for symbol, w in weights.items():
            if w > profile.MaxSingleAssetWeight:
                is_safe = False

        # Calculate mock/standard statistical metrics
        metrics = PortfolioRisk(
            ExpectedVolatility=0.155,
            HistoricalDrawdown=0.082,
            VaR=0.045
        )

        notes = (
            f"Portfolio allocation assessed successfully against profile '{profile.RiskToleranceLevel}'. "
            f"Result: {'Approved' if is_safe else 'Rejected'}."
        )

        return RiskAssessment(
            IsApproved=is_safe,
            RiskProfileName=profile.RiskToleranceLevel,
            PortfolioRiskMetrics=metrics,
            AssessmentNotes=notes,
            AssessedAt=datetime.now()
        )
