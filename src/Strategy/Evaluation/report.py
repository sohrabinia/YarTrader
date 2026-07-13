import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Strategy.Models.models import StrategyCandidate, StrategyEvaluation
from src.Strategy.Evaluation.comparator import StrategyComparisonResult
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class StrategyEvaluationReport:
    """
    Structured research report compiling results of candidate strategy evaluations.
    This report contains analysis and evidence, and is completely decoupled from active execution.
    """
    ReportId: str
    EvaluatedStrategies: List[StrategyCandidate]
    ScoringBreakdown: Dict[str, Dict[str, float]]
    ResearchEvidence: Dict[str, Any]
    ComparisonInfo: Optional[StrategyComparisonResult]
    ConfidenceInfo: Dict[str, float]
    GeneratedAt: datetime
    SummaryNotes: str


class EvaluationReportBuilder:
    """
    Builds compiled StrategyEvaluationReport instances from raw candidate, evaluation, and comparison data.
    """

    def build_report(
        self,
        candidates: List[StrategyCandidate],
        evaluations: List[StrategyEvaluation],
        comparison: Optional[StrategyComparisonResult] = None,
        research_evidence: Optional[Dict[str, Any]] = None,
        summary_notes: str = ""
    ) -> StrategyEvaluationReport:
        """
        Synthesizes evaluated strategies, scoring breakdowns, evidence, and comparisons into a cohesive report.
        """
        if not candidates:
            raise ValidationException("Candidates list cannot be empty for report building.")
        if not evaluations:
            raise ValidationException("Evaluations list cannot be empty for report building.")

        report_id = f"rpt-{uuid.uuid4()}"

        # Build maps for lookup
        eval_map = {ev.StrategyId: ev for ev in evaluations}
        scoring_breakdown = {}
        confidence_info = {}

        for cand in candidates:
            if cand.Id not in eval_map:
                raise ValidationException(
                    f"Validation Error: Candidate '{cand.Id}' does not have a corresponding evaluation."
                )
            ev = eval_map[cand.Id]
            scoring_breakdown[cand.Id] = dict(ev.Score.Criteria)
            confidence_info[cand.Id] = ev.Score.Confidence

        evidence = research_evidence or {}
        if not evidence:
            # Gather evidence from candidates' research context
            evidence = {cand.Id: cand.ResearchContext for cand in candidates}

        notes = summary_notes or f"Evaluation report successfully generated for {len(candidates)} candidate(s)."

        return StrategyEvaluationReport(
            ReportId=report_id,
            EvaluatedStrategies=list(candidates),
            ScoringBreakdown=scoring_breakdown,
            ResearchEvidence=evidence,
            ComparisonInfo=comparison,
            ConfidenceInfo=confidence_info,
            GeneratedAt=datetime.now(),
            SummaryNotes=notes
        )
