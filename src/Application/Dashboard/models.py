from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PipelineStageStatus:
    stage_name: str
    status: str  # Healthy, Degraded, Inactive
    last_processed_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OverviewMetrics:
    system_health: str  # Healthy, Degraded, Unhealthy
    pipeline_status: str
    service_status: str
    last_processing_time_ms: float
    stage_statuses: List[PipelineStageStatus] = field(default_factory=list)


@dataclass(frozen=True)
class AgentDashboardMetrics:
    agent_id: str
    name: str
    status: str
    capability: List[str]
    workload_count: int
    reliability_score: float
    performance_history: List[float] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class DecisionDashboardMetrics:
    decision_id: str
    timestamp: datetime
    state: str
    evidence_sources: List[str]
    confidence_quality: float
    consistency_score: float
    reliability_score: float
    conflicts_detected: bool
    resolution_explanation: str


@dataclass(frozen=True)
class ProviderDashboardMetrics:
    provider_id: str
    status: str
    latency_ms: float
    failure_rate: float
    data_quality_score: float
    reliability_history_count: int


@dataclass(frozen=True)
class DashboardReportPayload:
    report_id: str
    generated_at: datetime
    overview: OverviewMetrics
    agents: List[AgentDashboardMetrics] = field(default_factory=list)
    decisions: List[DecisionDashboardMetrics] = field(default_factory=list)
    providers: List[ProviderDashboardMetrics] = field(default_factory=list)
    additional_analytics: Dict[str, Any] = field(default_factory=dict)
