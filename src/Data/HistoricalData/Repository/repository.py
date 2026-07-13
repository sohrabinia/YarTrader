from typing import Dict, List
from src.Data.HistoricalData.Interfaces.interfaces import IHistoricalDataRepository
from src.Data.MarketData.Models.models import MarketDataPoint, MarketDataRequest

class HistoricalDataRepository(IHistoricalDataRepository):
    """
    Standard implementation of IHistoricalDataRepository to store and retrieve historical data points.
    Integrates seamlessly with clean repository lookup patterns.
    """
    def __init__(self) -> None:
        self._store: Dict[str, List[MarketDataPoint]] = {}

    def store_historical_data(self, points: List[MarketDataPoint]) -> None:
        """Stores a collection of data points in local historical memory database."""
        for pt in points:
            if pt.AssetId not in self._store:
                self._store[pt.AssetId] = []
            self._store[pt.AssetId].append(pt)

        # Ensure they remain ordered by timestamp
        for asset_id in self._store:
            self._store[asset_id].sort(key=lambda x: x.Timestamp)

    def retrieve_historical_data(self, request: MarketDataRequest) -> List[MarketDataPoint]:
        """Retrieves and filters historical market data records based on request boundaries."""
        points = self._store.get(request.Asset, [])
        return [
            pt for pt in points
            if request.StartTime <= pt.Timestamp <= request.EndTime
        ]
