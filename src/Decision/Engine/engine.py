import uuid
from datetime import datetime
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionReason, DecisionState
from src.Research.MarketAnalysis.Models.models import ResearchResult
from src.Strategy.Models.models import StrategyEvaluation
from src.Risk.Models.models import RiskAssessment

class DecisionEngine(IDecisionEngine):
    """
    Evaluates strategy outputs and risk assessments to produce formalized DecisionResults.
    Strictly contains zero BUY/SELL states.
    """
    def evaluate_decision(self, context: DecisionContext) -> DecisionResult:
        decision_id = str(uuid.uuid4())

        # Simple logical rules to evaluate decision state:
        total_weight = sum(context.AssetWeights.values())

        if total_weight <= 0:
            state = DecisionState.NO_ACTION
            summary = "No asset allocation recommended."
            audit_status = "Skipped"
            confidence = 1.0
        elif total_weight > 1.5:  # excess leverage
            state = DecisionState.REJECTED
            summary = "Total recommended allocation weight exceeds acceptable leverage constraints."
            audit_status = "Risk Check Failed"
            confidence = 0.90
        elif total_weight > 1.0:  # moderate leverage, requires manual review or additional checks
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


class DecisionReasoningFramework:
    """
    Advanced logical reasoner and integrator.
    Synthesizes Research outcomes, Strategy ratings, and Risk assessments to form a comprehensive DecisionResult.
    """
    def __init__(self) -> None:
        self._engine = DecisionEngine()

    def reason_and_decide(
        self,
        research_result: ResearchResult,
        strategy_evaluation: StrategyEvaluation,
        risk_assessment: RiskAssessment
    ) -> DecisionResult:
        """
        Integrates inputs from Research, Strategy, and Risk layers, evaluating their consistency
        and outputting a finalized DecisionResult detailing reasoning summaries and confidence.
        """
        asset = research_result.Request.Asset
        score = strategy_evaluation.Score.OverallScore

        # Create context
        context = DecisionContext(
            StrategyId=strategy_evaluation.StrategyId,
            AssetWeights={asset: score} if risk_assessment.IsApproved else {},
            TargetRiskProfile=risk_assessment.RiskProfileName
        )

        # Initial engine evaluation
        result = self._engine.evaluate_decision(context)

        # Synthesize advanced reasoning summary
        detailed_summary = (
            f"Decision reasoning completed for asset '{asset}'. "
            f"Research confidence: {research_result.ConfidenceScore:.2f}. "
            f"Strategy score: {score:.2f} ({strategy_evaluation.EvaluationNotes}). "
            f"Risk status: {risk_assessment.AssessmentNotes}."
        )

        # If risk is rejected, override state to REJECTED immediately
        final_state = result.State
        if not risk_assessment.IsApproved:
            final_state = DecisionState.REJECTED
            detailed_summary += " Decision OVERRIDDEN to REJECTED due to failed Risk audit."

        reason = DecisionReason(
            AnalysisSummary=detailed_summary,
            RiskAuditStatus="PASSED" if risk_assessment.IsApproved else "FAILED",
            ConfidenceScore=min(research_result.ConfidenceScore, result.Reason.ConfidenceScore)
        )

        return DecisionResult(
            DecisionId=result.DecisionId,
            Context=context,
            State=final_state,
            Reason=reason,
            CreatedAt=datetime.now()
        )
