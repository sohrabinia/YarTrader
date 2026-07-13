import uuid
from datetime import datetime
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionResult, DecisionReason, DecisionState

class DecisionEngine(IDecisionEngine):
    """
    Evaluates strategy outputs and risk assessments to produce formalized DecisionResults.
    Strictly contains zero BUY/SELL states.
    """
    def evaluate_decision(self, context: DecisionContext) -> DecisionResult:
        decision_id = str(uuid.uuid4())

        # Simple logical rules to evaluate decision state:
        # If expected volatility exceeds threshold or leverage fits constraints
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
