from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass(frozen=True)
class HistoricalRecord:
    """Represents a standardized point-in-time historical OHLCV record for an asset."""
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
class DatasetMetadata:
    """Represents the identification and versioning metadata of a historical market dataset."""
    DatasetId: str
    Name: str
    AssetId: str
    Timeframe: str
    Format: str  # "CSV" or "JSON"
    RecordCount: int = 0
    FilePath: Optional[str] = None
    CreatedAt: datetime = field(default_factory=datetime.now)

    @property
    def dataset_id(self) -> str:
        return self.DatasetId

    @property
    def name(self) -> str:
        return self.Name

    @property
    def asset_id(self) -> str:
        return self.AssetId

    @property
    def timeframe(self) -> str:
        return self.Timeframe

    @property
    def format(self) -> str:
        return self.Format

    @property
    def record_count(self) -> int:
        return self.RecordCount

    @property
    def file_path(self) -> Optional[str]:
        return self.FilePath

    @property
    def created_at(self) -> datetime:
        return self.CreatedAt


@dataclass(frozen=True)
class HistoricalDataset:
    """Represents a full historical dataset containing metadata and records."""
    Metadata: DatasetMetadata
    Records: List[HistoricalRecord]

    @property
    def metadata(self) -> DatasetMetadata:
        return self.Metadata

    @property
    def records(self) -> List[HistoricalRecord]:
        return self.Records


@dataclass(frozen=True)
class MarketDataBatch:
    """Represents a packaged batch of historical market records for an asset."""
    AssetId: str
    Records: List[HistoricalRecord]

    @property
    def asset_id(self) -> str:
        return self.AssetId

    @property
    def records(self) -> List[HistoricalRecord]:
        return self.Records
