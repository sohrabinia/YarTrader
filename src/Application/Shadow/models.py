from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ShadowSession:
    """Represents an active, read-only shadow simulation session."""
    session_id: str
    symbol: str
    timeframe: str
    is_active: bool
    started_at: datetime
    ended_at: Optional[datetime] = None


@dataclass(frozen=True)
class ShadowMetricsSnapshot:
    """Captured metrics of decision quality and latency in shadow mode."""
    processed_count: int
    average_latency_ms: float
    decision_consistency: float
    average_quality: float
    alert_count: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ShadowReport:
    """Aggregated output from a single live shadow execution iteration."""
    report_id: str
    session_id: str
    symbol: str
    timestamp: datetime
    final_decision_state: str
    confidence: float
    metrics: ShadowMetricsSnapshot
    compliance_passed: bool = True
