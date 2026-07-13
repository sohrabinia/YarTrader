from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

@dataclass(frozen=True)
class ResearchMetrics:
    """Represents a passive, parameter-driven summary of researched statistical coefficients."""
    MeanReturn: float
    Variance: float
    ConfidenceRating: float
    CalculatedAt: datetime
    Attributes: Dict[str, Any] = field(default_factory=dict)
