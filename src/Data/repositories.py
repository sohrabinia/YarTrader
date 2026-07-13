from datetime import datetime
from typing import Dict, List, Optional
from src.Core.entities import Asset, MarketData
from src.Core.interfaces import IRepository

class InMemoryRepository(IRepository):
    """
    High-performance in-memory repository implementing the core IRepository gateway interface.
    This manages data state cleanly without external database dependencies.
    """
    def __init__(self) -> None:
        self._assets: Dict[str, Asset] = {}
        self._market_data: Dict[str, List[MarketData]] = {}

    def save_asset(self, asset: Asset) -> None:
        """Stores or updates asset metadata."""
        self._assets[asset.symbol] = asset

    def get_asset(self, symbol: str) -> Optional[Asset]:
        """Retrieves asset by symbol."""
        return self._assets.get(symbol)

    def list_assets(self) -> List[Asset]:
        """Lists all active assets in database."""
        return list(self._assets.values())

    def save_market_data(self, data: MarketData) -> None:
        """Appends market pricing data points."""
        if data.symbol not in self._market_data:
            self._market_data[data.symbol] = []
        self._market_data[data.symbol].append(data)
        # Keep them sorted by timestamp
        self._market_data[data.symbol].sort(key=lambda x: x.timestamp)

    def get_latest_market_data(self, symbol: str) -> Optional[MarketData]:
        """Retrieves most recent price snapshot."""
        data_list = self._market_data.get(symbol)
        if data_list:
            return data_list[-1]
        return None

    def get_historical_market_data(self, symbol: str, start_time: datetime, end_time: datetime) -> List[MarketData]:
        """Queries historical price points within specified time boundaries."""
        data_list = self._market_data.get(symbol, [])
        return [
            d for d in data_list
            if start_time <= d.timestamp <= end_time
        ]
