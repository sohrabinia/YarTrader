import math
from datetime import datetime
from typing import List, Dict, Any
from src.Application.Shadow.models import ShadowMetricsSnapshot


class ShadowMetricsEvaluator:
    """Calculates sliding indicators on shadow decision outputs over real-time intervals."""

    def __init__(self) -> None:
        self._latencies: List[float] = []
        self._confidences: List[float] = []
        self._qualities: List[float] = []
        self._alerts_count = 0

    def record_tick(self, latency_ms: float, confidence: float, quality: float, has_alert: bool) -> None:
        self._latencies.append(latency_ms)
        self._confidences.append(confidence)
        self._qualities.append(quality)
        if has_alert:
            self._alerts_count += 1

    def calculate_snapshot(self) -> ShadowMetricsSnapshot:
        count = len(self._latencies)
        if count == 0:
            return ShadowMetricsSnapshot(
                processed_count=0,
                average_latency_ms=0.0,
                decision_consistency=1.0,
                average_quality=1.0,
                alert_count=0,
                timestamp=datetime.now()
            )

        avg_lat = sum(self._latencies) / count
        avg_qual = sum(self._qualities) / count

        # Consistency: standard deviation/variance on confidence
        avg_conf = sum(self._confidences) / count
        variance = sum((c - avg_conf) ** 2 for c in self._confidences) / count
        consistency = max(0.0, min(1.0, 1.0 - math.sqrt(variance)))

        return ShadowMetricsSnapshot(
            processed_count=count,
            average_latency_ms=round(avg_lat, 2),
            decision_consistency=round(consistency, 4),
            average_quality=round(avg_qual, 4),
            alert_count=self._alerts_count,
            timestamp=datetime.now()
        )
