from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

@dataclass(frozen=True)
class RiskProfile:
    """Represents a set of risk profiles/tolerances for an asset or portfolio."""
    RiskToleranceLevel: str  # e.g., "Low", "Moderate", "High"
    MaxLeverageFactor: float
    MaxSingleAssetWeight: float


@dataclass(frozen=True)
class ExposureModel:
    """Represents calculated mathematical exposures for assets."""
    AssetExposures: Dict[str, float]  # symbol -> exposure weight


@dataclass(frozen=True)
class PortfolioRisk:
    """Represents the calculated expected risk characteristics of a portfolio."""
    ExpectedVolatility: float
    HistoricalDrawdown: float
    VaR: float  # Value at Risk percentage


@dataclass(frozen=True)
class RiskAssessment:
    """Represents the outcome of a risk assessment audit on a target portfolio allocation."""
    IsApproved: bool
    RiskProfileName: str
    PortfolioRiskMetrics: PortfolioRisk
    AssessmentNotes: str
    AssessedAt: datetime
