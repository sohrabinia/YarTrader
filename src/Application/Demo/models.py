from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Application.Explainability.explainability import ExplainableIntelligenceReport


@dataclass(frozen=True)
class DemoScenario:
    """Represents a demonstration and validation scenario setup."""
    scenario_id: str
    name: str
    description: str
    asset: str
    timeframe: str
    price_data: List[Any] = field(default_factory=list)  # list of MarketDataPoint or similar
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DemoStepResult:
    """Represents the execution result of a single pipeline step."""
    step_name: str  # e.g., "Ingestion", "Feature Extraction", "Research", "Strategy Evaluation", "Risk Analysis", "Decision", "Validation"
    status: str     # e.g., "SUCCESS", "FAILED"
    payload: Any    # raw output or description from this stage
    duration_ms: float
    error_message: Optional[str] = None


@dataclass(frozen=True)
class DemoExecutionResult:
    """Groups full-trace outcomes from executing a DemoScenario."""
    scenario_id: str
    name: str
    start_time: datetime
    end_time: datetime
    steps: List[DemoStepResult] = field(default_factory=list)
    final_decision_state: str = "NoAction"  # e.g. Approved, Rejected, ReviewRequired, etc.
    overall_confidence: float = 0.0
    explainable_report: Optional[ExplainableIntelligenceReport] = None
    success: bool = True


@dataclass(frozen=True)
class DemoReport:
    """Represents a trace-complete, printable, and audit-ready report object."""
    report_id: str
    timestamp: datetime
    execution_result: DemoExecutionResult
    rendered_summary: str
