import threading
from typing import Any, Dict, List, Optional


class PerformanceMetricsTracker:
    """Tracks latency metrics, call frequencies, and warning/error anomaly rates."""

    _instance: Optional["PerformanceMetricsTracker"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "PerformanceMetricsTracker":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self) -> None:
        self._latencies: Dict[str, List[float]] = {
            "pipeline_execution": [],
            "research_latency": [],
            "strategy_latency": [],
            "risk_latency": [],
            "decision_latency": [],
            "learning_latency": []
        }
        self._warning_count = 0
        self._error_count = 0
        self._custom_metrics: Dict[str, float] = {}

    @classmethod
    def get_tracker(cls) -> "PerformanceMetricsTracker":
        return cls()

    def record_latency(self, metric_key: str, duration_ms: float) -> None:
        if metric_key in self._latencies:
            self._latencies[metric_key].append(duration_ms)

    def record_warning(self) -> None:
        self._warning_count += 1

    def record_error(self) -> None:
        self._error_count += 1

    def set_custom_metric(self, name: str, val: float) -> None:
        self._custom_metrics[name] = val

    def get_average_latency(self, metric_key: str) -> float:
        values = self._latencies.get(metric_key, [])
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def get_metrics_summary(self) -> Dict[str, Any]:
        return {
            "average_pipeline_execution_ms": self.get_average_latency("pipeline_execution"),
            "average_research_latency_ms": self.get_average_latency("research_latency"),
            "average_strategy_latency_ms": self.get_average_latency("strategy_latency"),
            "average_risk_latency_ms": self.get_average_latency("risk_latency"),
            "average_decision_latency_ms": self.get_average_latency("decision_latency"),
            "average_learning_latency_ms": self.get_average_latency("learning_latency"),
            "warning_count": self._warning_count,
            "error_count": self._error_count,
            "custom_metrics": self._custom_metrics.copy()
        }

    def reset(self) -> None:
        self._latencies = {k: [] for k in self._latencies}
        self._warning_count = 0
        self._error_count = 0
        self._custom_metrics.clear()
