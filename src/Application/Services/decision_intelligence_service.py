import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from src.Application.Services.decision_context_service import DecisionContextService
from src.Application.Decision.decision_context_engine import (
    DecisionContextSummary,
    DecisionContext,
    DecisionFactor
)
from src.Application.Decision.decision_intelligence_engine import (
    DecisionIntelligenceEngine,
    DecisionIntelligenceSummary
)
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)


class DecisionIntelligenceService:
    """
    Application service coordinating retrieval from DecisionContextService
    and compile_intelligence_summary via DecisionIntelligenceEngine.
    Does NOT calculate indicators, predict outcomes, or execute orders.
    """
    def __init__(
        self,
        decision_context_service: Optional[DecisionContextService] = None,
        engine: Optional[DecisionIntelligenceEngine] = None
    ) -> None:
        self.decision_context_service = decision_context_service or DecisionContextService()
        self.engine = engine or DecisionIntelligenceEngine()

    def get_decision_intelligence_summary(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        strategy: str = "TREND",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Coordinates compilation of decision intelligence summary from Phase 14 context output.
        """
        if limit <= 0 or limit > 1000:
            raise ValidationException("limit must be between 1 and 1000 records.")

        strat_upper = strategy.strip().upper()

        # Retrieve Decision Context Summary via DecisionContextService
        context_dict = self.decision_context_service.get_decision_context_summary(
            symbol=symbol,
            interval=interval,
            strategy=strat_upper,
            limit=limit
        )

        raw_ctx = context_dict.get("decision_context", {})
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
            for f in context_dict.get("factors", [])
        ]

        context_summary = DecisionContextSummary(
            context_id=context_dict.get("context_id", "ctx-0"),
            symbol=symbol,
            interval=interval,
            strategy_type=strat_upper,
            decision_context=d_context,
            factors=factors,
            reliability_state=context_dict.get("reliability_state", "INSUFFICIENT_CONTEXT"),
            data_quality_state=context_dict.get("data_quality_state", "LOW_QUALITY")
        )

        summary: DecisionIntelligenceSummary = self.engine.compile_intelligence_summary(
            context_summary=context_summary
        )

        return summary.to_dict()
