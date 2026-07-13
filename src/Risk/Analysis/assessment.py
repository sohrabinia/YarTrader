from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from src.Risk.Analysis.scorer import RiskScore
from src.Risk.Analysis.scenario import RiskScenarioResult

@dataclass(frozen=True)
class AdvancedRiskAssessment:
    """
    Structured outcome of an advanced risk assessment.
    Contains overall classification, factors, evidence, scenarios, and confidence metadata.
    """
    OverallClassification: str  # e.g., "Low", "Moderate", "High", "Critical"
    RiskFactors: List[str]
    Evidence: Dict[str, Any]
    ScenarioResults: List[RiskScenarioResult]
    RiskScoreInfo: RiskScore
    ConfidenceMetadata: Dict[str, Any]
    AssessedAt: datetime = field(default_factory=datetime.now)
