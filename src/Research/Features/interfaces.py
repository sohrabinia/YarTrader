from abc import ABC, abstractmethod
from typing import List
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.Features.models import FeatureValue, MarketFeatureSet

class IFeatureCalculator(ABC):
    """Interface defining the contract for executing analytical feature calculations."""

    @abstractmethod
    def calculate(self, data_points: List[MarketDataPoint]) -> List[FeatureValue]:
        """Calculates features from a series of market data points and returns feature values."""
        pass


class IFeaturePipeline(ABC):
    """Interface defining the orchestration contract for executing a feature extraction pipeline."""

    @abstractmethod
    def execute(self, data_points: List[MarketDataPoint]) -> MarketFeatureSet:
        """Executes registered calculators to produce a unified MarketFeatureSet from data points."""
        pass
