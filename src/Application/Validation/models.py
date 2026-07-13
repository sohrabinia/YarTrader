from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class ScenarioConfiguration:
    """
    Configuration settings for running an intelligence validation scenario.
    """
    ScenarioType: str  # Normal, HighVolatility, LowInformation, Conflicting, DataFailure
    Asset: str
    Timeframe: str
    CustomParams: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioResult:
    """
    Structured outcome of a scenario execution run.
    """
    ScenarioName: str
    IsSuccess: bool
    Logs: List[str] = field(default_factory=list)
    Metrics: Dict[str, Any] = field(default_factory=dict)
    ExecutedAt: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ValidationScenario:
    """
    Represents a specific test case definition for intelligence layer integration.
    """
    Name: str
    Config: ScenarioConfiguration


@dataclass(frozen=True)
class PipelineHealthReport:
    """
    State report detailing internal system dependency structures and layer alignments.
    """
    Status: str  # Healthy, Degraded, Unhealthy
    LayerConnectivity: Dict[str, str] = field(default_factory=dict)
    Errors: List[str] = field(default_factory=list)
    AnalyzedAt: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class SystemBenchmarkMetrics:
    """
    Core performance benchmark parameters tracking speed, completion rates, and consistencies.
    """
    PipelineExecutionTime: float  # in seconds
    ScenarioCompletionRate: float  # percentage
    ErrorFrequency: float  # ratio of exceptions
    OutputConsistencyScore: float  # stability score (0.0 to 1.0)
    ComponentResponseTimes: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ComplianceAuditResult:
    """
    Auditing results proving platform adherence to clean architecture and execution safety.
    """
    IsCompliant: bool
    CheckedRules: Dict[str, bool] = field(default_factory=dict)
    Violations: List[str] = field(default_factory=list)
    AuditedAt: datetime = field(default_factory=datetime.now)
