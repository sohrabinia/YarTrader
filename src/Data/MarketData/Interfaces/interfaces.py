from abc import ABC, abstractmethod
from typing import Any, List
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint
from src.Data.Common.models import DataQualityReport

class IMarketDataProvider(ABC):
    """Interface defining contracts for obtaining market data from upstream providers."""
    @abstractmethod
    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        """Retrieves market data based on specified request parameters."""
        pass


class IMarketDataNormalizer(ABC):
    """Interface defining contracts to translate third-party data payloads into TRADEYAR models."""
    @abstractmethod
    def normalize_external_data(self, external_data: Any, asset_id: str) -> List[MarketDataPoint]:
        """Translates dynamic external inputs into standardized TRADEYAR MarketDataPoint objects."""
        pass


class IMarketDataValidator(ABC):
    """Interface defining contracts for strict schema and validation rules on market data points."""
    @abstractmethod
    def validate_market_data(self, points: List[MarketDataPoint]) -> bool:
        """Validates list of data points to ensure they fit minimum structural rules."""
        pass


class IDataQualityChecker(ABC):
    """Interface defining contracts to perform thorough quality audits and return detailed reports."""
    @abstractmethod
    def check_quality(self, points: List[MarketDataPoint]) -> DataQualityReport:
        """Audits data quality and returns a detailed report on record validity and potential anomalies."""
        pass
