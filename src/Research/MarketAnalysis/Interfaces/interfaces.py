from abc import ABC, abstractmethod
from typing import List
from src.Research.MarketAnalysis.Models.models import ResearchRequest, ResearchResult, MarketObservation, MarketInsight

class IResearchEngine(ABC):
    """Interface defining operations for executing robust market research on historical and structural data."""
    @abstractmethod
    def analyze_market(self, request: ResearchRequest) -> ResearchResult:
        """Processes a ResearchRequest and outputs a high-level ResearchResult package."""
        pass


class IMarketAnalyzer(ABC):
    """Interface defining operations for analyzing streaming or batch MarketObservations to extract Insights."""
    @abstractmethod
    def analyze_observations(self, observations: List[MarketObservation]) -> List[MarketInsight]:
        """Analyzes observed market events and extracts structured market insights."""
        pass


class IResearchRepository(ABC):
    """Interface defining database storage and retrieval operations for persistent research outputs."""
    @abstractmethod
    def store_research_result(self, result: ResearchResult) -> None:
        """Saves a research output result cleanly to the database."""
        pass

    @abstractmethod
    def get_research_results(self, asset: str) -> List[ResearchResult]:
        """Retrieves historical research outputs corresponding to the specified asset."""
        pass


class IFractalEngine(ABC):
    """Standardized Interface for YarTrader Fractal Behavior Analysis Subsystem."""

    @abstractmethod
    def analyze_fractals(
        self,
        symbol: str,
        primary_timeframe: str,
        candles_by_tf: dict,
        historical_patterns: list = None
    ) -> dict:
        """
        Executes multi-timeframe fractal containment, pattern similarity matching,
        and multi-scale self-similarity base detection.
        """
        pass
