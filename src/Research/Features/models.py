from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Union

@dataclass(frozen=True)
class FeatureDefinition:
    """Defines feature parameters, category, and dependencies/requirements."""
    Name: str
    Description: str
    Category: str  # e.g., "Price", "Volatility", "Trend", "Statistical"
    CalculationRequirements: Dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.Name

    @property
    def description(self) -> str:
        return self.Description

    @property
    def category(self) -> str:
        return self.Category

    @property
    def calculation_requirements(self) -> Dict[str, Any]:
        return self.CalculationRequirements


@dataclass(frozen=True)
class FeatureValue:
    """Represents a calculated feature observation value at a point in time."""
    FeatureName: str
    Value: Union[float, str]
    Timestamp: datetime
    Metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def feature_name(self) -> str:
        return self.FeatureName

    @property
    def value(self) -> Union[float, str]:
        return self.Value

    @property
    def timestamp(self) -> datetime:
        return self.Timestamp

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.Metadata


@dataclass(frozen=True)
class MarketFeatureSet:
    """Packaged collection of extracted features for an asset over a time range."""
    AssetId: str
    StartTime: datetime
    EndTime: datetime
    Features: Dict[str, FeatureValue] = field(default_factory=dict)
    SourceDatasetInfo: Dict[str, Any] = field(default_factory=dict)

    @property
    def asset_id(self) -> str:
        return self.AssetId

    @property
    def start_time(self) -> datetime:
        return self.StartTime

    @property
    def end_time(self) -> datetime:
        return self.EndTime

    @property
    def features(self) -> Dict[str, FeatureValue]:
        return self.Features

    @property
    def source_dataset_info(self) -> Dict[str, Any]:
        return self.SourceDatasetInfo
