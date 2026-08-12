from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionReason, DecisionState
from src.Research.MarketAnalysis.Models.models import ResearchResult
from src.Strategy.Models.models import StrategyEvaluation
from src.Risk.Models.models import RiskAssessment

# Consolidate: use the canonical advanced DecisionEngine as the sole decision engine
from src.Decision.Intelligence.engine import DecisionEngine


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
            CreatedAt=result.CreatedAt
        )
