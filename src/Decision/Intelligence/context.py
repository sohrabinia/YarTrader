from dataclasses import dataclass, field
from typing import Any, Dict, List
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class DecisionIntelligenceContext:
    """
    Immutable, framework-independent decision intelligence context.
    Synthesizes research insights, pattern observations, strategy evaluations, and risk assessments.
    Enforces pure analytical mode (absolutely no orders, brokers, positions, or transactions).
    """
    ResearchInsights: List[Any] = field(default_factory=list)
    PatternObservations: List[Any] = field(default_factory=list)
    StrategyEvaluations: List[Any] = field(default_factory=list)
    RiskAssessments: List[Any] = field(default_factory=list)
    MarketConditions: Dict[str, Any] = field(default_factory=dict)
    HistoricalEvidence: Dict[str, Any] = field(default_factory=dict)
    Metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Prevent any execution or transaction leaks
        forbidden_keywords = {
            "order", "broker", "position", "transaction", "buy_signal", "sell_signal", "place_order"
        }

        def scan_object(obj: Any) -> None:
            if isinstance(obj, str):
                lower_str = obj.lower()
                for kw in forbidden_keywords:
                    if kw in lower_str:
                        raise ValidationException(
                            f"Safety Violation: DecisionIntelligenceContext contains forbidden execution-related keyword '{kw}'."
                        )
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan_object(k)
                    scan_object(v)
            elif isinstance(obj, (list, set, tuple)):
                for item in obj:
                    scan_object(item)
            elif hasattr(obj, "__dict__"):
                scan_object(obj.__dict__)

        scan_object(self.ResearchInsights)
        scan_object(self.PatternObservations)
        scan_object(self.StrategyEvaluations)
        scan_object(self.RiskAssessments)
        scan_object(self.MarketConditions)
        scan_object(self.HistoricalEvidence)
        scan_object(self.Metadata)
