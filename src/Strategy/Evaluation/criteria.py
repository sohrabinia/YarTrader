from dataclasses import dataclass

@dataclass(frozen=True)
class EvaluationCriteria:
    """
    Represents standardized evaluation dimensions used to score strategy concepts.
    Note: These are qualitative / quantitative descriptive markers only; they do NOT generate trade choices.
    """
    STABILITY: str = "Stability"                   # Measure of expected return-rate variance
    COMPLEXITY: str = "Complexity"                 # Measure of architectural simplicity
    DATA_REQUIREMENTS: str = "DataRequirements"     # Ingest intensity metrics
    RISK_COMPATIBILITY: str = "RiskCompatibility" # Conformity check with active risk mandates
