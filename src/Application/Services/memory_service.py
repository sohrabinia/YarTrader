import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.Application.Services.learning_service import LearningService
from src.Application.Memory.memory_engine import MemoryRecord, MemoryStore
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Application service that coordinates storage and retrieval of structured
    MemoryRecord instances derived from Phase 11 Learning Insights.
    Does NOT call MT5, strategies, or brokers directly.
    """
    def __init__(
        self,
        learning_service: Optional[LearningService] = None,
        store: Optional[MemoryStore] = None
    ) -> None:
        self.learning_service = learning_service or LearningService()
        self.store = store or MemoryStore()

    def record_learning_insight(
        self,
        symbol: str = "XAUUSD",
        interval: str = "M15",
        strategy: str = "TREND",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Retrieves LearningInsight from LearningService, converts it into a MemoryRecord,
        and persists it deterministically into MemoryStore.
        """
        insight_dict = self.learning_service.analyze_historical_learning(
            symbol=symbol,
            interval=interval,
            strategy=strategy,
            limit=limit
        )

        ts_raw = insight_dict.get("analyzed_at")
        if ts_raw:
            try:
                ts_obj = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except Exception:
                ts_obj = datetime.now(timezone.utc)
        else:
            ts_obj = datetime.now(timezone.utc)

        if ts_obj.tzinfo is None:
            ts_obj = ts_obj.replace(tzinfo=timezone.utc)

        active_ratio = insight_dict.get("reliability_summary", {}).get("active_signal_ratio", 0.0)
        conf_val = min(1.0, max(0.0, float(active_ratio)))

        rec_id = f"mem-{symbol.upper()}-{strategy.upper()}-{ts_obj.strftime('%Y%m%d%H%M%S')}"

        rec = MemoryRecord(
            id=rec_id,
            timestamp=ts_obj,
            symbol=symbol,
            interval=interval,
            strategy_type=strategy.upper(),
            observation_type="LEARNING_STATISTICAL_INSIGHT",
            metrics={
                "observation_count": insight_dict.get("observation_count", 0),
                "signal_counts": insight_dict.get("signal_counts", {}),
                "signal_frequencies": insight_dict.get("signal_frequencies", {}),
                "sample_sufficiency": insight_dict.get("sample_sufficiency", False)
            },
            confidence=conf_val,
            source_phase="PHASE_11_LEARNING"
        )
        rec.validate()

        self.store.add_record(rec)
        return rec.to_dict()

    def get_historical_memory(
        self,
        symbol: Optional[str] = None,
        strategy_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves historical MemoryRecord instances matching filters.
        """
        st_obj = None
        if start_time:
            try:
                st_obj = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except Exception:
                raise ValidationException(f"Invalid start_time format: '{start_time}'. Use ISO 8601.")

        et_obj = None
        if end_time:
            try:
                et_obj = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except Exception:
                raise ValidationException(f"Invalid end_time format: '{end_time}'. Use ISO 8601.")

        records = self.store.get_records(
            symbol=symbol,
            strategy_type=strategy_type,
            start_time=st_obj,
            end_time=et_obj
        )

        strategy_dist: Dict[str, int] = {}
        symbol_dist: Dict[str, int] = {}
        latest_ts: Optional[str] = None

        for r in records:
            s_type = r.strategy_type
            sym = r.symbol
            strategy_dist[s_type] = strategy_dist.get(s_type, 0) + 1
            symbol_dist[sym] = symbol_dist.get(sym, 0) + 1

        if records:
            latest_ts = records[-1].timestamp.isoformat()

        return {
            "total_records": len(records),
            "filters": {
                "symbol": symbol,
                "strategy_type": strategy_type,
                "start_time": start_time,
                "end_time": end_time
            },
            "summary": {
                "latest_timestamp": latest_ts,
                "strategy_distribution": strategy_dist,
                "symbol_distribution": symbol_dist
            },
            "records": [r.to_dict() for r in records]
        }
