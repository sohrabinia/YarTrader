from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
from src.Core.entities import Asset, MarketData, RiskParameters, DecisionReport, PerformanceMetric

class IRepository(ABC):
    """Core gateway interface for generic entity storage and retrieval."""
    @abstractmethod
    def save_asset(self, asset: Asset) -> None:
        pass

    @abstractmethod
    def get_asset(self, symbol: str) -> Optional[Asset]:
        pass

    @abstractmethod
    def list_assets(self) -> List[Asset]:
        pass

    @abstractmethod
    def save_market_data(self, data: MarketData) -> None:
        pass

    @abstractmethod
    def get_latest_market_data(self, symbol: str) -> Optional[MarketData]:
        pass

    @abstractmethod
    def get_historical_market_data(self, symbol: str, start_time: datetime, end_time: datetime) -> List[MarketData]:
        pass


class IRiskEvaluator(ABC):
    """Core gateway interface for assessing portfolio allocations against risk bounds."""
    @abstractmethod
    def check_allocation_safety(self, weights: Dict[str, float], params: RiskParameters) -> bool:
        """Returns True if the proposed weights conform to risk parameters."""
        pass

    @abstractmethod
    def calculate_portfolio_volatility(self, weights: Dict[str, float]) -> float:
        """Calculates expected annualized volatility for a proposed allocation."""
        pass


class IDecisionService(ABC):
    """Core service interface for financial intelligence and portfolio analysis decisions."""
    @abstractmethod
    def analyze_market_and_recommend(self, risk_params: RiskParameters) -> DecisionReport:
        """Performs analytical research and recommendation report generation."""
        pass


class IPerformanceTracker(ABC):
    """Core interface for continuous performance tracking, feedback loops, and learning metadata."""
    @abstractmethod
    def log_metric(self, metric: PerformanceMetric) -> None:
        pass

    @abstractmethod
    def get_metric_history(self, metric_name: str) -> List[PerformanceMetric]:
        pass

    @abstractmethod
    def detect_performance_drift(self, metric_name: str, threshold: float) -> bool:
        pass
