import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionReason, DecisionState
from src.Decision.Intelligence.context import DecisionIntelligenceContext
from src.Decision.Intelligence.builder import DecisionContextBuilder
from src.Decision.Intelligence.analyzer import DecisionAnalyzer, DecisionAnalysis
from src.Decision.Intelligence.evaluator import DecisionQualityEvaluator, DecisionQualityScore
from src.Decision.Intelligence.resolver import DecisionConflictResolver, ConflictResolutionResult
from src.Decision.Intelligence.evidence import DecisionEvidenceCollector, DecisionEvidenceTrail
from src.Decision.Intelligence.report import DecisionReportBuilder, DecisionIntelligenceReport
from src.Decision.Intelligence.history import DecisionHistoryRecord, DecisionValidator
from src.Infrastructure.exceptions import ValidationException

class DecisionEngine(IDecisionEngine):
    """
    Advanced Decision Intelligence Engine.
    Synthesizes research insights, strategy evaluations, and risk assessments to produce formalized DecisionResults.
    Strictly simulated parameters; contains zero BUY/SELL states.
    """

    def __init__(self) -> None:
        self._analyzer = DecisionAnalyzer()
        self._quality_evaluator = DecisionQualityEvaluator()
        self._conflict_resolver = DecisionConflictResolver()
        self._evidence_collector = DecisionEvidenceCollector()
        self._report_builder = DecisionReportBuilder()
        self._validator = DecisionValidator()
        self._history: List[DecisionHistoryRecord] = []

    def evaluate_advanced_decision(self, context: DecisionIntelligenceContext) -> DecisionResult:
        """
        Processes a DecisionIntelligenceContext to return a finalized DecisionResult detailing reasoning and states.
        """
        # 1. Validate Context
        self._validator.validate_context(context)

        # 2. Analyze Alignment
        analysis = self._analyzer.analyze_context(context)

        # 3. Quality scoring
        quality = self._quality_evaluator.evaluate_quality(context)

        # 4. Conflict resolution
        conflicts = self._conflict_resolver.resolve_conflicts(context)

        # 5. Determine decision state
        # Analytical states: Approved, Rejected, ReviewRequired, NoAction, InsufficientData
        insights_count = len(context.ResearchInsights)
        strategy_count = len(context.StrategyEvaluations)
        risk_count = len(context.RiskAssessments)

        if insights_count == 0 or strategy_count == 0:
            state = "InsufficientData"
            explanation = "Failed to make a decision due to insufficient data."
        elif risk_count == 0:
            state = DecisionState.REVIEW_REQUIRED
            explanation = "Manual review required: risk assessment missing."
        else:
            # Check risk status
            first_risk = context.RiskAssessments[0]
            risk_approved = True
            if hasattr(first_risk, "IsApproved"):
                risk_approved = first_risk.IsApproved
            elif isinstance(first_risk, dict):
                risk_approved = first_risk.get("is_approved", True)

            if not risk_approved:
                state = DecisionState.REJECTED
                explanation = "Rejected due to failed Risk checks."
            elif analysis.Confidence < 0.6:
                state = DecisionState.REVIEW_REQUIRED
                explanation = "Review required due to low alignment or confidence levels."
            else:
                state = DecisionState.APPROVED
                explanation = "Decision approved under all parameters."

        # Apply conflict resolution impact
        final_confidence = round(max(0.0, min(1.0, analysis.Confidence + conflicts.ConfidenceImpact)), 4)

        # Build legacy reasoning structure
        reason = DecisionReason(
            AnalysisSummary=f"{explanation} {analysis.Summary}. Resolution: {conflicts.ResolutionExplanation}",
            RiskAuditStatus="PASSED" if state == DecisionState.APPROVED else "FAILED/AWAITING",
            ConfidenceScore=final_confidence
        )

        # Legacy context bridge
        legacy_context = DecisionContext(
            StrategyId=context.Metadata.get("strategy_id", "cand-unknown"),
            AssetWeights=context.Metadata.get("asset_weights", {}),
            TargetRiskProfile=context.Metadata.get("target_risk_profile", "unknown")
        )

        result = DecisionResult(
            DecisionId=str(uuid.uuid4()),
            Context=legacy_context,
            State=state,
            Reason=reason,
            CreatedAt=datetime.now()
        )

        # Record History Record
        history_record = DecisionHistoryRecord(
            Timestamp=datetime.now(),
            ContextSummary=analysis.Summary,
            Result=result,
            Confidence=final_confidence,
            EvidenceReferences={"trace_id": f"rec-{result.DecisionId}"}
        )
        self._history.append(history_record)

        return result

    def generate_intelligence_report(self, context: DecisionIntelligenceContext) -> DecisionIntelligenceReport:
        """
        Builds and compiles a full DecisionIntelligenceReport.
        """
        result = self.evaluate_advanced_decision(context)
        analysis = self._analyzer.analyze_context(context)
        quality = self._quality_evaluator.evaluate_quality(context)
        conflicts = self._conflict_resolver.resolve_conflicts(context)
        evidence = self._evidence_collector.collect_evidence(context)

        return self._report_builder.build_report(
            context=context,
            summary=result.Reason.AnalysisSummary,
            evidence_trail=evidence,
            quality_score=quality,
            conflict_analysis=conflicts,
            confidence_info={"final_confidence": result.Reason.ConfidenceScore}
        )

    def evaluate_decision(self, context: DecisionContext) -> DecisionResult:
        """
        Legacy IDecisionEngine fallback logic to ensure full backward compatibility.
        """
        decision_id = str(uuid.uuid4())
        total_weight = sum(context.AssetWeights.values()) if context.AssetWeights else 0.0

        if total_weight <= 0:
            state = DecisionState.NO_ACTION
            summary = "No asset allocation recommended."
            audit_status = "Skipped"
            confidence = 1.0
        elif total_weight > 1.5:
            state = DecisionState.REJECTED
            summary = "Total recommended allocation weight exceeds leverage limits."
            audit_status = "Risk Check Failed"
            confidence = 0.90
        elif total_weight > 1.0:
            state = DecisionState.REVIEW_REQUIRED
            summary = "Allocation contains active leverage; review is required."
            audit_status = "Awaiting Verification"
            confidence = 0.85
        else:
            state = DecisionState.APPROVED
            summary = f"Allocation of {len(context.AssetWeights)} assets meets standard rules."
            audit_status = "Approved"
            confidence = 0.95

        reason = DecisionReason(
            AnalysisSummary=summary,
            RiskAuditStatus=audit_status,
            ConfidenceScore=confidence
        )

        return DecisionResult(
            DecisionId=decision_id,
            Context=context,
            State=state,
            Reason=reason,
            CreatedAt=datetime.now()
        )

    def get_history(self) -> List[DecisionHistoryRecord]:
        """Queries in-memory list of historical decision records."""
        return list(self._history)
