from dataclasses import dataclass
from typing import Any, Dict
from src.Risk.Analysis.context import RiskAnalysisContext
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class RiskScore:
    """
    Represents calculated multi-factor risk scores.
    Strictly descriptive metrics; contains no decision commands.
    """
    MarketRiskScore: float  # 0.0 to 1.0
    StrategyCompatibilityRisk: float  # 0.0 to 1.0
    StabilityScore: float  # 0.0 to 1.0 (higher = more stable/less risky)
    ConfidenceLevel: float  # 0.0 to 1.0
    OverallRiskScore: float  # 0.0 to 1.0


class RiskScoreCalculator:
    """
    Computes mathematical risk score indicators from market and strategy factors.
    Guarantees that the same input produces identical, stable scores.
    """

    def calculate_risk_score(self, context: RiskAnalysisContext) -> RiskScore:
        """
        Derives scores deterministically.
        """
        if not context:
            raise ValidationException("RiskAnalysisContext cannot be None for risk score calculation.")

        # Extract features and evaluation
        features = context.MarketFeatureSet or {}
        strategy_eval = context.StrategyEvaluation or {}
        risk_profile = context.RiskContext or {}

        # 1. Market Risk Score
        volatility = float(features.get("volatility", 0.15))
        # Map volatility (typically 0.0 to 0.5+) to a score between 0.0 and 1.0
        market_risk = min(1.0, max(0.0, volatility * 2.0))

        # 2. Strategy Compatibility Risk
        # Lower compatibility risk if Strategy overall score is high
        strategy_score_val = strategy_eval.get("overall_score", 0.75)
        strategy_risk = min(1.0, max(0.0, 1.0 - strategy_score_val))

        # 3. Stability Score
        # Based on historical success rate and confidence
        success_rate = float(context.HistoricalScenarioInfo.get("success_rate", 0.5))
        stability = min(1.0, max(0.0, success_rate * 0.8 + (1.0 - market_risk) * 0.2))

        # 4. Confidence Level
        # Directly derived from features confidence and strategy confidence
        features_confidence = float(features.get("confidence", 0.85))
        strategy_confidence = float(strategy_eval.get("confidence", 0.85))
        confidence = round((features_confidence + strategy_confidence) / 2.0, 4)

        # Calculate Overall Risk Score
        # Overall risk increases with market risk and strategy risk, decreases with stability
        overall_risk = round(min(1.0, max(0.0, (market_risk * 0.5 + strategy_risk * 0.3 + (1.0 - stability) * 0.2))), 4)

        return RiskScore(
            MarketRiskScore=round(market_risk, 4),
            StrategyCompatibilityRisk=round(strategy_risk, 4),
            StabilityScore=round(stability, 4),
            ConfidenceLevel=confidence,
            OverallRiskScore=overall_risk
        )
