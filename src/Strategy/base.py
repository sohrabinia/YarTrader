from abc import ABC, abstractmethod
from typing import Dict, List
from src.Core.entities import MarketData

class BaseAssetScoringStrategy(ABC):
    """
    Abstract base strategy defining interface for scoring and ranking assets.
    Provides passive financial evaluation models without producing BUY/SELL signals or trading rules.
    """
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def score_assets(self, asset_market_data: Dict[str, List[MarketData]]) -> Dict[str, float]:
        """
        Calculates normalized suitability scores for each asset based on research indicators.
        Returns a dictionary mapping asset symbol to score (e.g., between 0.0 and 1.0).
        """
        pass
