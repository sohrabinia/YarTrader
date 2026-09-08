import logging
from typing import Dict, Any, Optional

from src.Application.Services.intelligence_service import IntelligenceService
from src.Application.Services.learning_service import LearningService
from src.Application.Services.memory_service import MemoryService
from src.Application.Learning.learning_engine import LearningInsight, LearningConfig
from src.Application.Memory.memory_engine import MemoryRecord
from src.Application.Intelligence.intelligence_engine import IntelligenceSummary, IntelligenceContext, IntelligenceSignal
from src.Application.Decision.decision_context_engine import DecisionContextEngine, DecisionContextSummary
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)


class DecisionContextService:
    """
    Application service that coordinates retrieval from IntelligenceService,
    LearningService, and MemoryService to compile deterministic DecisionContextSummary objects.
    Does NOT calculate indicators, predict outcomes, or execute orders.
    """
    def __init__(
        self,
        intelligence_service: Optional[IntelligenceService] = None,
        learning_service: Optional[LearningService] = None,
        memory_service: Optional[MemoryService] = None,
        engine: Optional[DecisionContextEngine] = None
    ) -> None:
        self.intelligence_service = intelligence_service or IntelligenceService()
        self.learning_service = learning_service or LearningService()
        self.memory_service = memory_service or MemoryService()
        self.engine = engine or DecisionContextEngine()

    def get_decision_context_summary(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        strategy: str = "TREND",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Coordinates compilation of decision context summary across Phase 11-13 outputs.
        """
        if limit <= 0 or limit > 1000:
            raise ValidationException("limit must be between 1 and 1000 records.")

        strat_upper = strategy.strip().upper()

        # Retrieve Intelligence Summary via IntelligenceService
        intel_dict = self.intelligence_service.get_historical_intelligence_summary(
            symbol=symbol,
            interval=interval,
            strategy=strat_upper,
            limit=limit
        )

        ctx_dict = intel_dict.get("context", {})
        i_context = IntelligenceContext(
            symbol=symbol,
            interval=interval,
            strategy_type=strat_upper,
            total_observations=ctx_dict.get("total_observations", 0),
            active_signals_count=ctx_dict.get("active_signals_count", 0),
            signal_distribution=ctx_dict.get("signal_distribution", {}),
            signal_frequencies=ctx_dict.get("signal_frequencies", {})
        )

        i_signals = [
            IntelligenceSignal(
                signal_name=s.get("signal_name", "SIGNAL"),
                historical_count=s.get("historical_count", 0),
                frequency_ratio=s.get("frequency_ratio", 0.0),
                sample_confidence_state=s.get("sample_confidence_state", "LOW_SAMPLE")
            )
            for s in intel_dict.get("signal_summaries", [])
        ]

        intelligence_summary = IntelligenceSummary(
            symbol=symbol,
            interval=interval,
            strategy_type=strat_upper,
            historical_context_count=intel_dict.get("historical_context_count", 0),
            memory_records_count=intel_dict.get("memory_records_count", 0),
            context=i_context,
            signal_summaries=i_signals,
            sample_sufficiency_status=intel_dict.get("sample_sufficiency_status", "INSUFFICIENT_DATA"),
            statistical_confidence_score=float(intel_dict.get("statistical_confidence_score", 0.0))
        )

        # Retrieve Learning Insight via LearningService
        learning_dict = self.learning_service.analyze_historical_learning(
            symbol=symbol,
            interval=interval,
            strategy=strat_upper,
            limit=limit
        )

        l_config = LearningConfig(
            symbol=symbol,
            interval=interval,
            strategy_type=strat_upper,
            min_sample_threshold=learning_dict.get("config", {}).get("min_sample_threshold", 10)
        )

        learning_insight = LearningInsight(
            symbol=symbol,
            interval=interval,
            strategy_type=strat_upper,
            observation_count=learning_dict.get("observation_count", 0),
            signal_counts=learning_dict.get("signal_counts", {}),
            signal_frequencies=learning_dict.get("signal_frequencies", {}),
            sample_sufficiency=learning_dict.get("sample_sufficiency", False),
            reliability_summary=learning_dict.get("reliability_summary", {}),
            config=l_config
        )

        # Retrieve Memory Records via MemoryService
        memory_dict = self.memory_service.get_historical_memory(
            symbol=symbol,
            strategy_type=strat_upper
        )

        memory_records_raw = memory_dict.get("records", [])
        memory_records: list[MemoryRecord] = []
        from datetime import datetime, timezone

        for mr in memory_records_raw:
            ts_val = mr.get("timestamp")
            if isinstance(ts_val, str):
                try:
                    ts_obj = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                except Exception:
                    ts_obj = datetime.now(timezone.utc)
            else:
                ts_obj = ts_val or datetime.now(timezone.utc)

            if ts_obj.tzinfo is None:
                ts_obj = ts_obj.replace(tzinfo=timezone.utc)

            m_obj = MemoryRecord(
                id=mr.get("id", "mem-0"),
                timestamp=ts_obj,
                symbol=mr.get("symbol", symbol),
                interval=mr.get("interval", interval),
                strategy_type=mr.get("strategy_type", strat_upper),
                observation_type=mr.get("observation_type", "LEARNING_INSIGHT"),
                metrics=mr.get("metrics", {}),
                confidence=float(mr.get("confidence", 0.0)),
                source_phase=mr.get("source_phase", "PHASE_11_LEARNING")
            )
            memory_records.append(m_obj)

        summary: DecisionContextSummary = self.engine.compile_context_summary(
            intelligence_summary=intelligence_summary,
            learning_insight=learning_insight,
            memory_records=memory_records
        )

        return summary.to_dict()
