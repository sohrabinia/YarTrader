import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from src.Risk.Analysis.exposure import ExposureAssessment
from src.Risk.Analysis.correlation import CorrelationReport
from src.Risk.Analysis.scenario import RiskScenarioResult
from src.Risk.Analysis.scorer import RiskScore
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class RiskAnalysisReport:
    """
    Structured analytical risk report integrating exposure, correlation, scenario, and scoring breakdowns.
    """
    ReportId: str
    MarketConditions: Dict[str, Any]
    ExposureAnalysis: ExposureAssessment
    CorrelationAnalysis: CorrelationReport
    ScenarioAnalysis: List[RiskScenarioResult]
    RiskScoring: RiskScore
    EvidenceTrail: Dict[str, Any]
    GeneratedAt: datetime = field(default_factory=datetime.now)


class RiskReportBuilder:
    """
    Compiles detailed RiskAnalysisReport instances from individual analytical component results.
    """

    def build_report(
        self,
        market_conditions: Dict[str, Any],
        exposure_analysis: ExposureAssessment,
        correlation_analysis: CorrelationReport,
        scenario_analysis: List[RiskScenarioResult],
        risk_scoring: RiskScore,
        evidence_trail: Dict[str, Any]
    ) -> RiskAnalysisReport:
        """
        Builds a comprehensive RiskAnalysisReport with full validation.
        """
        if exposure_analysis is None:
            raise ValidationException("Exposure analysis cannot be None.")
        if correlation_analysis is None:
            raise ValidationException("Correlation report cannot be None.")
        if scenario_analysis is None:
            raise ValidationException("Scenario analysis results cannot be None.")
        if risk_scoring is None:
            raise ValidationException("Risk scoring details cannot be None.")

        report_id = f"rrpt-{uuid.uuid4()}"

        return RiskAnalysisReport(
            ReportId=report_id,
            MarketConditions=market_conditions or {},
            ExposureAnalysis=exposure_analysis,
            CorrelationAnalysis=correlation_analysis,
            ScenarioAnalysis=list(scenario_analysis),
            RiskScoring=risk_scoring,
            EvidenceTrail=evidence_trail or {},
            GeneratedAt=datetime.now()
        )
