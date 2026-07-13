from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Application.Pipeline.pipeline import PipelineResult
from src.Risk.Models.models import RiskProfile


class ExecutionBlockedError(Exception):
    """Exception raised when an active order placement, live trading, or broker execution is blocked."""
    pass


class SimulationEnvironmentGuard:
    """
    Validation guard ensuring absolute safety during pipeline simulation.
    Strictly blocks any live execution, broker order submission, or real money transaction.
    """
    _simulation_active = True

    @classmethod
    def is_simulation_active(cls) -> bool:
        return cls._simulation_active

    @classmethod
    def set_simulation_active(cls, active: bool) -> None:
        cls._simulation_active = active

    @classmethod
    def verify_safety(cls) -> None:
        """Verifies that the current environment is running safely in simulation mode."""
        if not cls._simulation_active:
            raise ExecutionBlockedError(
                "Execution Blocked: Live broker connection, real-money execution, "
                "or active order creation are strictly prohibited outside simulation mode."
            )

    @classmethod
    def block_active_execution(cls, action_name: str) -> None:
        """Explicitly blocks any transaction or active broker order."""
        raise ExecutionBlockedError(
            f"Execution Blocked: Attempted active execution '{action_name}'. "
            f"Only passive simulation of historical scenarios is permitted."
        )


@dataclass(frozen=True)
class MarketScenario:
    """Represents a passive market scenario for testing or simulation."""
    Asset: str
    TimeRange: Tuple[datetime, datetime]
    PriceData: List[MarketDataPoint]
    Metadata: Dict[str, Any] = field(default_factory=dict)
    ScenarioType: str = "Trending"  # e.g., Trending, Ranging, High Volatility, Low Liquidity, Market Shock


@dataclass(frozen=True)
class ScenarioInput:
    """Represents input variables for running a specific simulation scenario."""
    Scenario: MarketScenario
    TargetRiskProfile: RiskProfile
    LookbackDays: int = 10
    Metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioResult:
    """Represents the output logs and performance metrics of a scenario execution."""
    PipelineResult: PipelineResult
    ExecutionPrevented: bool
    OutcomeMetric: float


@dataclass(frozen=True)
class SimulationReport:
    """Represents a summarized reporting structure for simulated scenarios."""
    ScenarioInfo: Dict[str, Any]
    PipelineStatus: str
    ResearchSummary: str
    StrategySummary: str
    RiskSummary: str
    DecisionSummary: str
    LearningFeedbackSummary: str
    ExecutionPreventionStatus: str
