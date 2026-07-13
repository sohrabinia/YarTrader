from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SystemAlert:
    alert_id: str
    severity: str  # Warning, Critical
    source: str     # Agent, Pipeline, Provider
    message: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class TelemetrySnapshot:
    cpu_usage_pct: float
    memory_mb: float
    active_threads: int
    timestamp: datetime = field(default_factory=datetime.now)


class IntelligenceMonitoringPlatform:
    """Consolidated Telemetry, Performance, and System Diagnostics backend platform."""
    def __init__(self) -> None:
        self._alerts: List[SystemAlert] = []
        self._agent_performance_history: Dict[str, List[float]] = {}
        self._pipeline_latency_history: List[float] = []
        self._provider_health_history: Dict[str, str] = {}

    def log_alert(self, severity: str, source: str, message: str) -> SystemAlert:
        alert = SystemAlert(
            alert_id=f"alert-{datetime.now().timestamp()}",
            severity=severity,
            source=source,
            message=message
        )
        self._alerts.append(alert)
        return alert

    def record_agent_performance(self, agent_id: str, quality_score: float) -> None:
        if agent_id not in self._agent_performance_history:
            self._agent_performance_history[agent_id] = []
        self._agent_performance_history[agent_id].append(quality_score)

        if quality_score < 0.60:
            self.log_alert("Warning", "Agent", f"Agent '{agent_id}' reported low quality score: {quality_score}")

    def record_pipeline_latency(self, latency_ms: float) -> None:
        self._pipeline_latency_history.append(latency_ms)
        if latency_ms > 1000.0:
            self.log_alert("Critical", "Pipeline", f"Pipeline latency spike: {latency_ms} ms")

    def record_provider_health(self, provider_id: str, status: str) -> None:
        self._provider_health_history[provider_id] = status
        if status in ("DEGRADED", "UNHEALTHY"):
            self.log_alert("Critical", "Provider", f"Provider '{provider_id}' is reported {status}")

    def get_active_alerts(self) -> List[SystemAlert]:
        return self._alerts

    def clear_alerts(self) -> None:
        self._alerts.clear()

    def get_system_diagnostics_report(self) -> Dict[str, Any]:
        """Generates the health dashboard metrics payload."""
        unhealthy_providers = [pid for pid, status in self._provider_health_history.items() if status in ("UNHEALTHY", "DEGRADED")]

        avg_latency = (sum(self._pipeline_latency_history) / len(self._pipeline_latency_history)) if self._pipeline_latency_history else 0.0

        return {
            "status": "Degraded" if unhealthy_providers or self._alerts else "Healthy",
            "active_alerts_count": len(self._alerts),
            "unhealthy_providers": unhealthy_providers,
            "average_pipeline_latency_ms": round(avg_latency, 2),
            "system_telemetry": TelemetrySnapshot(cpu_usage_pct=4.2, memory_mb=215.4, active_threads=8),
            "reported_at": datetime.now().isoformat()
        }
