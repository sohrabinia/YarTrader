import logging
from typing import Dict, Any, Optional

from src.Application.Services.learning_service import LearningService
from src.Application.Services.memory_service import MemoryService
from src.Application.Learning.learning_engine import LearningInsight, LearningConfig, LearningDataset
from src.Application.Memory.memory_engine import MemoryRecord
from src.Application.Intelligence.intelligence_engine import IntelligenceEngine, IntelligenceSummary
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)


class IntelligenceService:
    """
    Application service that coordinates retrieval of LearningInsight (Phase 11)
    and MemoryRecords (Phase 12) to compile deterministic IntelligenceSummary objects.
    Does NOT modify Learning, Memory, Strategies, or MT5 execution boundaries.
    """
    def __init__(
        self,
        learning_service: Optional[LearningService] = None,
        memory_service: Optional[MemoryService] = None,
        engine: Optional[IntelligenceEngine] = None
    ) -> None:
        self.learning_service = learning_service or LearningService()
        self.memory_service = memory_service or MemoryService()
        self.engine = engine or IntelligenceEngine()

    def get_historical_intelligence_summary(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        strategy: str = "TREND",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Coordinates historical context compilation from LearningService and MemoryService outputs.
        """
        if limit <= 0 or limit > 1000:
            raise ValidationException("limit must be between 1 and 1000 records.")

        strat_upper = strategy.strip().upper()

        # Retrieve Learning Insight
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

        # Retrieve Memory Records
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

        summary: IntelligenceSummary = self.engine.compile_summary(
            learning_insight=learning_insight,
            memory_records=memory_records
        )

        return summary.to_dict()
