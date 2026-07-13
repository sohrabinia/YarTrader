from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class SourceQualityScore:
    provider_id: str
    availability: float  # ratio of successful fetches to total fetches
    error_rate: float    # ratio of failed fetches / invalid data occurrences
    consistency: float   # average consistency score from validations
    completeness: float  # average completeness score from validations
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def composite_score(self) -> float:
        """Computes composite reliability rating."""
        return (self.availability * 0.3) + ((1.0 - self.error_rate) * 0.3) + (self.consistency * 0.2) + (self.completeness * 0.2)


class DataSourceReliabilityTracker:
    """Tracks chronological records of external data provider performance and health."""
    def __init__(self) -> None:
        self._history: Dict[str, List[SourceQualityScore]] = {}  # provider_id -> scores history
        self._latency_history: Dict[str, List[float]] = {}       # provider_id -> response latencies (ms)
        self._failure_history: Dict[str, List[str]] = {}         # provider_id -> error logs
        self._connection_status: Dict[str, bool] = {}           # provider_id -> is_online

    def record_metrics(
        self,
        provider_id: str,
        availability: float,
        error_rate: float,
        consistency: float,
        completeness: float,
        latency_ms: Optional[float] = None,
        error_msg: Optional[str] = None
    ) -> SourceQualityScore:
        if not provider_id:
            raise ValidationException("Reliability Tracker Error: provider_id must not be empty.")

        for name, val in [
            ("availability", availability),
            ("error_rate", error_rate),
            ("consistency", consistency),
            ("completeness", completeness)
        ]:
            if not (0.0 <= val <= 1.0):
                raise ValidationException(f"Reliability Tracker Error: Metric '{name}' value {val} must be between 0.0 and 1.0.")

        score = SourceQualityScore(
            provider_id=provider_id,
            availability=availability,
            error_rate=error_rate,
            consistency=consistency,
            completeness=completeness,
            timestamp=datetime.now()
        )

        if provider_id not in self._history:
            self._history[provider_id] = []
        self._history[provider_id].append(score)

        # 1. Update Connection Status
        is_online = availability > 0.0
        self._connection_status[provider_id] = is_online

        # 2. Track Latency
        if latency_ms is not None:
            if provider_id not in self._latency_history:
                self._latency_history[provider_id] = []
            self._latency_history[provider_id].append(latency_ms)

        # 3. Track Failure History
        if error_msg:
            if provider_id not in self._failure_history:
                self._failure_history[provider_id] = []
            self._failure_history[provider_id].append(f"[{datetime.now().isoformat()}] {error_msg}")

        return score

    def get_average_scores(self, provider_id: str) -> Dict[str, float]:
        """Calculates average metric metrics for a provider."""
        if provider_id not in self._history or not self._history[provider_id]:
            return {
                "availability": 1.0,
                "error_rate": 0.0,
                "consistency": 1.0,
                "completeness": 1.0,
                "composite_score": 1.0
            }

        scores = self._history[provider_id]
        count = len(scores)

        avg_availability = sum(s.availability for s in scores) / count
        avg_error_rate = sum(s.error_rate for s in scores) / count
        avg_consistency = sum(s.consistency for s in scores) / count
        avg_completeness = sum(s.completeness for s in scores) / count
        avg_composite = sum(s.composite_score for s in scores) / count

        return {
            "availability": round(avg_availability, 4),
            "error_rate": round(avg_error_rate, 4),
            "consistency": round(avg_consistency, 4),
            "completeness": round(avg_completeness, 4),
            "composite_score": round(avg_composite, 4)
        }

    def generate_health_report(self, provider_id: str) -> Dict[str, Any]:
        """Compiles health metrics into a standardized Provider Health Report."""
        averages = self.get_average_scores(provider_id)

        latencies = self._latency_history.get(provider_id, [])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        return {
            "provider_id": provider_id,
            "is_connected": self._connection_status.get(provider_id, False),
            "provider_availability_score": averages["availability"],
            "error_rate": averages["error_rate"],
            "composite_reliability_score": averages["composite_score"],
            "average_latency_ms": round(avg_latency, 2),
            "failure_history_count": len(self._failure_history.get(provider_id, [])),
            "failure_logs": self._failure_history.get(provider_id, [])[-10:],  # last 10 failed logs
            "reported_at": datetime.now().isoformat()
        }

    def get_history(self, provider_id: str) -> List[SourceQualityScore]:
        return self._history.get(provider_id, [])

    def clear(self) -> None:
        self._history.clear()
        self._latency_history.clear()
        self._failure_history.clear()
        self._connection_status.clear()
