from dataclasses import dataclass, field
from typing import Any, Dict, List
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class StrategyEvaluationContext:
    """
    Immutable, framework-independent evaluation context for assessing Strategy Candidates.
    Strictly contains passive research context, market observations, and historical scenario info.
    Guarantees zero execution leakages (no orders, positions, broker references, or trade commands).
    """
    ResearchInsights: List[Any] = field(default_factory=list)
    MarketObservations: List[Any] = field(default_factory=list)
    HistoricalScenarioInfo: Dict[str, Any] = field(default_factory=dict)
    RiskContext: Dict[str, Any] = field(default_factory=dict)
    Metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Strict safety check for execution leaking parameters
        forbidden_keywords = {"order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"}

        def scan_object(obj: Any) -> None:
            if isinstance(obj, str):
                lower_str = obj.lower()
                for keyword in forbidden_keywords:
                    if keyword in lower_str:
                        raise ValidationException(
                            f"Safety Violation: StrategyEvaluationContext contains forbidden execution-related keyword '{keyword}' in data: '{obj}'."
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

        scan_object(self.HistoricalScenarioInfo)
        scan_object(self.RiskContext)
        scan_object(self.Metadata)
        scan_object(self.ResearchInsights)
        scan_object(self.MarketObservations)
