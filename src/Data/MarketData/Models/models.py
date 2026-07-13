from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass(frozen=True)
class MarketDataPoint:
    """Represents a standardized point-in-time OHLCV bar for an asset."""
    AssetId: str
    Timestamp: datetime
    Open: float
    High: float
    Low: float
    Close: float
    Volume: float

    @property
    def asset_id(self) -> str:
        return self.AssetId

    @property
    def timestamp(self) -> datetime:
        return self.Timestamp

    @property
    def open(self) -> float:
        return self.Open

    @property
    def high(self) -> float:
        return self.High

    @property
    def low(self) -> float:
        return self.Low

    @property
    def close(self) -> float:
        return self.Close

    @property
    def volume(self) -> float:
        return self.Volume


@dataclass(frozen=True)
class MarketDataRequest:
    """Represents a request parameters block to acquire historical or live market data."""
    Asset: str
    StartTime: datetime
    EndTime: datetime
    Timeframe: str  # e.g., "M1", "H1", "D1"

    @property
    def asset(self) -> str:
        return self.Asset

    @property
    def start_time(self) -> datetime:
        return self.StartTime

    @property
    def end_time(self) -> datetime:
        return self.EndTime

    @property
    def timeframe(self) -> str:
        return self.Timeframe


@dataclass(frozen=True)
class MarketDataResponse:
    """Represents the response containing the retrieved market data points and retrieval metadata."""
    Request: MarketDataRequest
    DataPoints: List[MarketDataPoint]
    RetrievedAt: datetime

    @property
    def request(self) -> MarketDataRequest:
        return self.Request

    @property
    def data_points(self) -> List[MarketDataPoint]:
        return self.DataPoints

    @property
    def retrieved_at(self) -> datetime:
        return self.RetrievedAt


@dataclass(frozen=True)
class MarketDataSourceInfo:
    """Represents identification and versioning metadata of an upstream market data provider."""
    ProviderName: str
    Version: str
    DataType: str  # e.g., "OHLCV", "Tick", "OrderBook"

    @property
    def provider_name(self) -> str:
        return self.ProviderName

    @property
    def version(self) -> str:
        return self.Version

    @property
    def data_type(self) -> str:
        return self.DataType
