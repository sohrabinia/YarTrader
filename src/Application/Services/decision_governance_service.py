import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from src.Application.Services.decision_intelligence_service import DecisionIntelligenceService
from src.Application.Decision.decision_context_engine import (
    DecisionContextSummary,
    DecisionContext,
    DecisionFactor
)
from src.Application.Decision.decision_intelligence_engine import (
    DecisionIntelligenceSummary,
    DecisionIntelligenceMetric
)
from src.Application.Governance.decision_governance_engine import (
    DecisionGovernanceEngine,
    GovernanceResult
)
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)


class DecisionGovernanceService:
    """
    Application service coordinating retrieval from DecisionIntelligenceService
    and evaluate_governance via DecisionGovernanceEngine.
    Does NOT generate buy/sell signals, calculate indicators, predict outcomes, or execute orders.
    """
    def __init__(
        self,
        decision_intelligence_service: Optional[DecisionIntelligenceService] = None,
        engine: Optional[DecisionGovernanceEngine] = None
    ) -> None:
        self.decision_intelligence_service = decision_intelligence_service or DecisionIntelligenceService()
        self.engine = engine or DecisionGovernanceEngine()

    def evaluate_decision_governance(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        strategy: str = "TREND",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Coordinates evaluation of decision governance rules across Phase 15 intelligence output.
        """
        if limit <= 0 or limit > 1000:
            raise ValidationException("limit must be between 1 and 1000 records.")

        strat_upper = strategy.strip().upper()

        # Retrieve Decision Intelligence Summary via DecisionIntelligenceService
        intel_dict = self.decision_intelligence_service.get_decision_intelligence_summary(
            symbol=symbol,
            interval=interval,
            strategy=strat_upper,
            limit=limit
        )

        d_ctx_summary_raw = intel_dict.get("decision_context_summary", {})
        raw_ctx = d_ctx_summary_raw.get("decision_context", {})
        ts_val = raw_ctx.get("timestamp")
        if isinstance(ts_val, str):
            try:
                ts_obj = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            except Exception:
                ts_obj = datetime.now(timezone.utc)
        else:
            ts_obj = ts_val or datetime.now(timezone.utc)

        if ts_obj.tzinfo is None:
            ts_obj = ts_obj.replace(tzinfo=timezone.utc)

        d_context = DecisionContext(
            timestamp=ts_obj,
            symbol=symbol,
            interval=interval,
            historical_context_count=raw_ctx.get("historical_context_count", 0),
            learning_summary=raw_ctx.get("learning_summary", {}),
            memory_summary=raw_ctx.get("memory_summary", {}),
            intelligence_summary=raw_ctx.get("intelligence_summary", {})
        )

        factors = [
            DecisionFactor(
                factor_name=f.get("factor_name", "Factor"),
                factor_value=f.get("factor_value", None),
                source=f.get("source", "Phase 14 Context"),
                explanation=f.get("explanation", "")
            )
            for f in d_ctx_summary_raw.get("factors", [])
        ]

        context_summary = DecisionContextSummary(
            context_id=d_ctx_summary_raw.get("context_id", "ctx-0"),
            symbol=symbol,
            interval=interval,
            strategy_type=strat_upper,
            decision_context=d_context,
            factors=factors,
            reliability_state=d_ctx_summary_raw.get("reliability_state", "INSUFFICIENT_CONTEXT"),
            data_quality_state=d_ctx_summary_raw.get("data_quality_state", "LOW_QUALITY")
        )

        metrics = [
            DecisionIntelligenceMetric(
                metric_name=m.get("metric_name", "Metric"),
                metric_value=m.get("metric_value", None),
                category=m.get("category", "GENERAL"),
                explanation=m.get("explanation", "")
            )
            for m in intel_dict.get("metrics", [])
        ]

        intelligence_summary = DecisionIntelligenceSummary(
            intelligence_id=intel_dict.get("intelligence_id", "intel-0"),
            symbol=symbol,
            interval=interval,
            strategy_type=strat_upper,
            decision_readiness_state=intel_dict.get("decision_readiness_state", "INSUFFICIENT_CONTEXT"),
            context_sufficiency_score=float(intel_dict.get("context_sufficiency_score", 0.0)),
            evidence_factor_quality=intel_dict.get("evidence_factor_quality", "LOW_QUALITY"),
            metrics=metrics,
            decision_context_summary=context_summary
        )

        result: GovernanceResult = self.engine.evaluate_governance(
            intelligence_summary=intelligence_summary
        )

        return result.to_dict()
