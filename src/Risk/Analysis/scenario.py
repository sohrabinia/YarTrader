from dataclasses import dataclass, field
from typing import Any, Dict, List
from src.Risk.Analysis.context import RiskAnalysisContext
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class RiskScenarioResult:
    """
    Represents the output findings of a single simulated hypothetical risk scenario.
    """
    ScenarioName: str
    ImpactRating: str  # e.g., "Elevated", "Severe", "Normal"
    AnalyticalRiskLevel: str  # e.g., "High", "Moderate", "Low"
    ShockDescription: str
    SimulationMetrics: Dict[str, Any] = field(default_factory=dict)


class RiskScenarioEngine:
    """
    Evaluates strategy and market suitability under hypothetical stressed risk states.
    Strictly simulated parameters; does not execute trades or active position sizing.
    """

    def evaluate_scenarios(self, context: RiskAnalysisContext) -> List[RiskScenarioResult]:
        """
        Runs hypothetical simulations across standard scenarios:
        - High Volatility
        - Market Instability
        - Sudden Regime Change
        - Data Uncertainty
        """
        if not context:
            raise ValidationException("RiskAnalysisContext cannot be None for scenario evaluation.")

        results = []

        # Extract features from context
        features = context.MarketFeatureSet or {}
        base_volatility = features.get("volatility", 0.15)
        base_confidence = features.get("confidence", 0.85)

        # 1. High Volatility Scenario
        high_vol_vol = base_volatility * 2.5
        results.append(
            RiskScenarioResult(
                ScenarioName="High Volatility Environment",
                ImpactRating="Severe" if high_vol_vol > 0.4 else "Elevated",
                AnalyticalRiskLevel="High" if high_vol_vol > 0.3 else "Moderate",
                ShockDescription=f"Simulates 250% increase in market volatility to {round(high_vol_vol, 4)}.",
                SimulationMetrics={
                    "shock_factor": 2.5,
                    "simulated_volatility": round(high_vol_vol, 4),
                    "var_multiplier": 2.0
                }
            )
        )

        # 2. Market Instability Scenario
        results.append(
            RiskScenarioResult(
                ScenarioName="Market Instability",
                ImpactRating="Elevated",
                AnalyticalRiskLevel="Moderate",
                ShockDescription="Simulates fragmented market conditions and spike in correlation factor deviations.",
                SimulationMetrics={
                    "correlation_instability_coef": 0.35,
                    "liquidity_dry_up_factor": 0.5
                }
            )
        )

        # 3. Sudden Regime Change Scenario
        results.append(
            RiskScenarioResult(
                ScenarioName="Sudden Regime Change",
                ImpactRating="Severe",
                AnalyticalRiskLevel="High",
                ShockDescription="Simulates a complete transition of macro market behavior states.",
                SimulationMetrics={
                    "state_transition_probability": 0.15,
                    "trend_reversal_magnitude": 0.8
                }
            )
        )

        # 4. Data Uncertainty Scenario
        uncertainty_confidence = base_confidence * 0.5
        results.append(
            RiskScenarioResult(
                ScenarioName="Data Uncertainty Scenario",
                ImpactRating="Elevated" if uncertainty_confidence < 0.5 else "Normal",
                AnalyticalRiskLevel="Moderate" if uncertainty_confidence < 0.5 else "Low",
                ShockDescription=f"Simulates a massive degradation in confidence to {round(uncertainty_confidence, 4)}.",
                SimulationMetrics={
                    "data_dropout_rate": 0.20,
                    "simulated_confidence": round(uncertainty_confidence, 4)
                }
            )
        )

        return results
