from abc import ABC, abstractmethod
from typing import Any
from src.Research.Indicators.Models.models import IndicatorDefinition, IndicatorResult

class IIndicatorProvider(ABC):
    """
    Interface defining indicator calculation contracts.
    Note: Indicators are completely passive mathematical structures.
    They must NOT generate trades, signals, or make decisions.
    """
    @abstractmethod
    def calculate_indicator(self, definition: IndicatorDefinition, market_data: Any) -> IndicatorResult:
        """Calculates a mathematical indicator (e.g. SMA, volatility) from input data."""
        pass
