from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Decision.Intelligence.models import DecisionIntelligenceReport


@dataclass(frozen=True)
class BacktestScenario:
    scenario_id: str
    name: str
    start_time: datetime
    end_time: datetime
    symbol: str
    timeframe: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BacktestResult:
    backtest_id: str
    scenario_id: str
    start_time: datetime
    end_time: datetime
    total_intervals_processed: int
    reports_history: List[DecisionIntelligenceReport] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    compliance_audit_passed: bool = True
