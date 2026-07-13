from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

@dataclass(frozen=True)
class IndicatorDefinition:
    """Represents a passive, parameter-driven indicator definition (e.g. SMA, Volatility index)."""
    Name: str
    Type: str
    Parameters: Dict[str, Any]

    @property
    def name(self) -> str:
        return self.Name

    @property
    def type(self) -> str:
        return self.Type

    @property
    def parameters(self) -> Dict[str, Any]:
        return self.Parameters


@dataclass(frozen=True)
class IndicatorResult:
    """Represents the calculated indicator numeric output."""
    Definition: IndicatorDefinition
    Value: float
    CalculatedAt: datetime

    @property
    def definition(self) -> IndicatorDefinition:
        return self.Definition

    @property
    def value(self) -> float:
        return self.Value

    @property
    def calculated_at(self) -> datetime:
        return self.CalculatedAt
