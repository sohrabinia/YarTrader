from abc import ABC, abstractmethod
from typing import List
from src.Data.MarketData.Models.models import MarketDataPoint, MarketDataRequest

class IHistoricalDataRepository(ABC):
    """Interface defining storage and lookup operations on historical market data points."""
    @abstractmethod
    def store_historical_data(self, points: List[MarketDataPoint]) -> None:
        """Saves a collection of data points to the historical database."""
        pass

    @abstractmethod
    def retrieve_historical_data(self, request: MarketDataRequest) -> List[MarketDataPoint]:
        """Queries historical records fitting the request parameters."""
        pass
