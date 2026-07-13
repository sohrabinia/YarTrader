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

class MomentumScoringStrategy(BaseAssetScoringStrategy):
    """
    A concrete asset evaluation model scoring assets on mathematical trend momentum.
    Strictly calculates score ratings; does not output buy/sell trade execution rules.
    """
    def score_assets(self, asset_market_data: Dict[str, List[MarketData]]) -> Dict[str, float]:
        scores = {}
        for symbol, data_points in asset_market_data.items():
            if not data_points or len(data_points) < 5:
                scores[symbol] = 0.5  # Neutral default score
                continue

            latest_price = data_points[-1].price
            older_price = data_points[-5].price

            if older_price > 0:
                raw_momentum = (latest_price - older_price) / older_price
                # Map to a score around 0.5
                score = 0.5 + (raw_momentum * 10)
                scores[symbol] = max(0.0, min(1.0, score))
            else:
                scores[symbol] = 0.5
        return scores
