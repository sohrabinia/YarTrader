import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionReason, DecisionState
from src.Decision.Intelligence.models import (
    DecisionIntelligenceContext,
    DecisionIntelligenceReport,
    DecisionHistoryRecord
)
from src.Decision.Intelligence.services import (
    DecisionContextBuilder,
    DecisionAnalyzer,
    DecisionQualityEvaluator,
    DecisionConflictResolver,
    DecisionEvidenceCollector,
    DecisionReportBuilder,
    DecisionValidator,
    DecisionHistoryStore
)
from src.Infrastructure.exceptions import ValidationException


class DecisionEngine(IDecisionEngine):
    """
    Advanced context-aware Decision Intelligence Engine.
    Synthesizes multi-factor inputs (Research, Strategy, Risk) to produce explainable analytical decisions.
    Strictly contains zero BUY/SELL states or trading execution mechanics.
    """
    def __init__(self) -> None:
        self.builder = DecisionContextBuilder()
        self.analyzer = DecisionAnalyzer()
        self.evaluator = DecisionQualityEvaluator()
        self.conflict_resolver = DecisionConflictResolver()
        self.collector = DecisionEvidenceCollector()
        self.report_builder = DecisionReportBuilder()
        self.validator = DecisionValidator()
        self.history_store = DecisionHistoryStore()

    def evaluate_decision(self, context: DecisionContext) -> DecisionResult:
        """
        Implements the traditional IDecisionEngine interface for backward compatibility.
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
            summary = "Total recommended allocation weight exceeds acceptable leverage constraints."
            audit_status = "Risk Check Failed"
            confidence = 0.90
        elif total_weight > 1.0:
            state = DecisionState.REVIEW_REQUIRED
            summary = "Allocation contains active leverage; review is required."
            audit_status = "Awaiting Verification"
            confidence = 0.85
        else:
            state = DecisionState.APPROVED
            summary = f"Allocation of {len(context.AssetWeights)} assets meets all standard constraints."
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

    def evaluate_intelligence_context(
        self,
        context: DecisionIntelligenceContext
    ) -> DecisionIntelligenceReport:
        """
        Executes the advanced multi-dimensional decision evaluation workflow.
        """
        decision_id = str(uuid.uuid4())

        # 1. Structural Validation
        self.validator.validate_context(context)

        # 2. Analyze context
        analysis = self.analyzer.analyze_context(context)

        # 3. Evaluate decision quality
        quality_score = self.evaluator.evaluate_quality(context, analysis)

        # 4. Resolve layer conflicts
        conflict_result = self.conflict_resolver.resolve_conflicts(context, analysis)

        # 5. Collect evidence trail
        evidence_trail = self.collector.collect_evidence(decision_id, context)

        # 6. Determine analytical Decision State
        # - Default to NoAction if weights are empty
        # - ReviewRequired if evidence is insufficient
        # - Rejected if risk rejected
        # - ReviewRequired if severe conflict
        # - Approved otherwise
        state = DecisionState.APPROVED

        # Check Insufficient Evidence -> ReviewRequired
        # (e.g. no strategy evaluations or no research insights)
        if not context.StrategyEvaluations or not context.ResearchInsights:
            state = DecisionState.REVIEW_REQUIRED

        # Check risk approval
        risk_approved = analysis.SupportingEvidence.get("risk_approved", True)
        if not risk_approved:
            state = DecisionState.REJECTED

        # If empty allocation, default to NoAction
        has_weights = False
        if context.StrategyEvaluations:
            for s in context.StrategyEvaluations:
                if hasattr(s, "Score") and getattr(s, "Score").OverallScore > 0:
                    has_weights = True
                elif isinstance(s, dict) and s.get("score", 0.0) > 0:
                    has_weights = True
        if not has_weights and state == DecisionState.APPROVED:
            state = DecisionState.NO_ACTION

        # 7. Compile report
        report = self.report_builder.build_report(
            context=context,
            analysis=analysis,
            quality_score=quality_score,
            conflict_analysis=conflict_result,
            evidence_trail=evidence_trail,
            state=state
        )

        # 8. Validate final confidence level
        self.validator.validate_confidence(report.Confidence)

        # 9. Store in History
        self.history_store.record_decision(report)

        return report
