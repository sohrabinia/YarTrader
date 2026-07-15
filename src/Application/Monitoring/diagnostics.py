import sys
from datetime import datetime
from typing import Any, Dict
from src.Application.Monitoring.health import SubsystemHealthCheck
from src.Infrastructure.Observability.metrics import PerformanceMetricsTracker


class PlatformDiagnosticsEngine:
    """Gathers and aggregates system-wide diagnostic parameters and logs telemetry data."""

    def __init__(self) -> None:
        self.started_at = datetime.now()

    def compile_diagnostics_report(self) -> Dict[str, Any]:
        uptime_sec = (datetime.now() - self.started_at).total_seconds()

        # Subsystem health status checks
        subsystems = {
            "runtime": SubsystemHealthCheck.check_runtime(),
            "pipeline": SubsystemHealthCheck.check_pipeline(),
            "research": SubsystemHealthCheck.check_research(),
            "strategy": SubsystemHealthCheck.check_strategy(),
            "risk": SubsystemHealthCheck.check_risk(),
            "decision": SubsystemHealthCheck.check_decision(),
            "learning": SubsystemHealthCheck.check_learning(),
            "storage": SubsystemHealthCheck.check_storage()
        }

        # If any subsystem failed, global status shifts
        has_failed = any(status == "FAILED" for status in subsystems.values())
        has_warning = any(status == "WARNING" for status in subsystems.values())

        global_status = "FAILED" if has_failed else ("WARNING" if has_warning else "READY")

        # Telemetry & metrics summary
        tracker = PerformanceMetricsTracker.get_tracker()
        metrics_summary = tracker.get_metrics_summary()

        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": round(uptime_sec, 2),
            "status": global_status,
            "subsystems": subsystems,
            "performance_metrics": metrics_summary,
            "environment_info": {
                "python_version": sys.version,
                "platform": sys.platform
            }
        }
