import os
import time
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Application.Deployment.storage import TradeYarStorageManager


class StructuredLogger:
    """Production-grade structured logger emitting key-value JSON records."""

    def __init__(self, service_name: str = "YarTrader") -> None:
        self.service_name = service_name
        self._logs: List[str] = []
        self._storage_manager = TradeYarStorageManager.get_manager()
        self._log_file_path = os.path.join(self._storage_manager.get_log_dir(), "yartrader.log")

    def log(self, level: str, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        record = {
            "timestamp": datetime.now().isoformat(),
            "service": self.service_name,
            "level": level.upper(),
            "event": event,
            "metadata": metadata or {}
        }
        json_str = json.dumps(record)
        self._logs.append(json_str)

        # Strictly isolate writes inside the TradeYarStorageRoot/Logs directory
        try:
            os.makedirs(os.path.dirname(self._log_file_path), exist_ok=True)
            with open(self._log_file_path, "a", encoding="utf-8") as f:
                f.write(json_str + "\n")
        except Exception:
            pass

        return json_str

    def debug(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.log("DEBUG", event, metadata)

    def info(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.log("INFO", event, metadata)

    def warning(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.log("WARNING", event, metadata)

    def error(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return self.log("ERROR", event, metadata)

    def get_logs(self) -> List[str]:
        return self._logs

    def clear(self) -> None:
        self._logs.clear()


class PerformanceMetricsTracker:
    """Tracks latency metrics and operational anomaly/warning counts."""

    def __init__(self) -> None:
        self._metrics: Dict[str, List[float]] = {
            "pipeline_execution_time": [],
            "agent_latency": [],
            "scenario_execution_time": [],
            "decision_processing_time": []
        }
        self._warning_count = 0
        self._error_count = 0
        self._recent_errors: List[str] = []

    def record_pipeline_execution(self, duration_ms: float) -> None:
        self._metrics["pipeline_execution_time"].append(duration_ms)

    def record_agent_latency(self, duration_ms: float) -> None:
        self._metrics["agent_latency"].append(duration_ms)

    def record_scenario_execution(self, duration_ms: float) -> None:
        self._metrics["scenario_execution_time"].append(duration_ms)

    def record_decision_processing(self, duration_ms: float) -> None:
        self._metrics["decision_processing_time"].append(duration_ms)

    def record_warning(self, msg: str) -> None:
        self._warning_count += 1

    def record_error(self, error_msg: str) -> None:
        self._error_count += 1
        self._recent_errors.append(error_msg)

    def get_average_latency(self, metric_key: str) -> float:
        values = self._metrics.get(metric_key, [])
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def get_performance_summary(self) -> Dict[str, Any]:
        return {
            "average_pipeline_execution_ms": self.get_average_latency("pipeline_execution_time"),
            "average_agent_latency_ms": self.get_average_latency("agent_latency"),
            "average_scenario_execution_ms": self.get_average_latency("scenario_execution_time"),
            "average_decision_processing_ms": self.get_average_latency("decision_processing_time"),
            "warning_count": self._warning_count,
            "error_count": self._error_count,
            "recent_errors": self._recent_errors[-5:]
        }
