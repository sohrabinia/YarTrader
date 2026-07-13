import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from src.Decision.Intelligence.context import DecisionIntelligenceContext
from src.Decision.Intelligence.evidence import DecisionEvidenceTrail
from src.Decision.Intelligence.evaluator import DecisionQualityScore
from src.Decision.Intelligence.resolver import ConflictResolutionResult
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class DecisionIntelligenceReport:
    """
    Structured analytical report containing a full audit of decision intelligence.
    """
    ReportId: str
    Context: DecisionIntelligenceContext
    IntelligenceSummary: str
    EvidenceTrail: DecisionEvidenceTrail
    QualityScore: DecisionQualityScore
    ConflictAnalysis: ConflictResolutionResult
    ConfidenceInfo: Dict[str, Any]
    GeneratedAt: datetime = field(default_factory=datetime.now)


class DecisionReportBuilder:
    """
    Compiles detailed DecisionIntelligenceReport instances from analytical components.
    """

    def build_report(
        self,
        context: DecisionIntelligenceContext,
        summary: str,
        evidence_trail: DecisionEvidenceTrail,
        quality_score: DecisionQualityScore,
        conflict_analysis: ConflictResolutionResult,
        confidence_info: Dict[str, Any]
    ) -> DecisionIntelligenceReport:
        """
        Synthesizes decision intelligence parameters into a formal analytical report.
        """
        if context is None:
            raise ValidationException("DecisionIntelligenceContext cannot be None.")
        if evidence_trail is None:
            raise ValidationException("DecisionEvidenceTrail cannot be None.")
        if quality_score is None:
            raise ValidationException("DecisionQualityScore cannot be None.")
        if conflict_analysis is None:
            raise ValidationException("ConflictResolutionResult cannot be None.")

        report_id = f"drpt-{uuid.uuid4()}"

        return DecisionIntelligenceReport(
            ReportId=report_id,
            Context=context,
            IntelligenceSummary=summary or "Decision report finalized successfully.",
            EvidenceTrail=evidence_trail,
            QualityScore=quality_score,
            ConflictAnalysis=conflict_analysis,
            ConfidenceInfo=confidence_info or {},
            GeneratedAt=datetime.now()
        )
