from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
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
    """Tracks chronological records of external data provider performance."""
    def __init__(self) -> None:
        self._history: Dict[str, List[SourceQualityScore]] = {}  # provider_id -> scores history

    def record_metrics(
        self,
        provider_id: str,
        availability: float,
        error_rate: float,
        consistency: float,
        completeness: float
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

    def get_history(self, provider_id: str) -> List[SourceQualityScore]:
        return self._history.get(provider_id, [])

    def clear(self) -> None:
        self._history.clear()
