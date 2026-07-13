from dataclasses import dataclass, field
from typing import Any, Dict, List
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class RiskAnalysisContext:
    """
    Immutable risk analysis context representing market feature sets, research insights,
    strategy evaluations, historical scenarios, and metadata.
    Guarantees no database, broker, or execution dependencies.
    """
    MarketFeatureSet: Dict[str, Any] = field(default_factory=dict)
    ResearchInsights: List[Any] = field(default_factory=list)
    StrategyEvaluation: Dict[str, Any] = field(default_factory=dict)
    HistoricalScenarioInfo: Dict[str, Any] = field(default_factory=dict)
    RiskContext: Dict[str, Any] = field(default_factory=dict)
    Metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Enforce zero execution and transaction dependencies
        forbidden_keywords = {
            "order", "position", "broker", "transfer_money", "withdrawal", "deposit", "buy_order", "sell_order"
        }

        def scan_object(obj: Any) -> None:
            if isinstance(obj, str):
                lower_str = obj.lower()
                for kw in forbidden_keywords:
                    if kw in lower_str:
                        raise ValidationException(
                            f"Safety Violation: RiskAnalysisContext contains forbidden execution-related keyword '{kw}'."
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

        scan_object(self.MarketFeatureSet)
        scan_object(self.ResearchInsights)
        scan_object(self.StrategyEvaluation)
        scan_object(self.HistoricalScenarioInfo)
        scan_object(self.RiskContext)
        scan_object(self.Metadata)
