from dataclasses import dataclass, field
from typing import Any, Dict, List
from src.Risk.Analysis.context import RiskAnalysisContext
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class CorrelationReport:
    """
    Structured correlation report identifying relationships between market factors.
    Strictly passive and contains no execution or trading logic.
    """
    CorrelationMatrix: Dict[str, Dict[str, float]]
    CoreCorrelatedConditions: List[str]
    HighCorrelationFlags: Dict[str, bool]
    Metadata: Dict[str, Any] = field(default_factory=dict)


class CorrelationAnalyzer:
    """
    Analyzes mathematical relationships and dependencies between various market factors and features.
    """

    def analyze_correlation(self, context: RiskAnalysisContext) -> CorrelationReport:
        """
        Calculates mock/stable correlation indicators from market features.
        """
        if not context:
            raise ValidationException("RiskAnalysisContext cannot be None for correlation analysis.")

        # Establish deterministic relationship factors based on features or defaults
        features = context.MarketFeatureSet or {}
        volatility = features.get("volatility", 0.15)
        trend_strength = features.get("trend_strength", 0.5)

        # Build stable mock correlation matrix (values are determined by volatility and trend strength)
        correlation_matrix = {
            "Price": {
                "Price": 1.0,
                "Volatility": round(min(0.8, -0.3 + volatility), 2),
                "Trend": round(min(1.0, 0.4 + trend_strength), 2)
            },
            "Volatility": {
                "Price": round(min(0.8, -0.3 + volatility), 2),
                "Volatility": 1.0,
                "Trend": round(min(0.5, 0.1 - volatility), 2)
            },
            "Trend": {
                "Price": round(min(1.0, 0.4 + trend_strength), 2),
                "Volatility": round(min(0.5, 0.1 - volatility), 2),
                "Trend": 1.0
            }
        }

        # Identify correlated conditions
        correlated_conditions = []
        high_corr_flags = {}

        for factor_a, targets in correlation_matrix.items():
            for factor_b, val in targets.items():
                if factor_a != factor_b:
                    key = f"{factor_a}_{factor_b}"
                    if abs(val) > 0.7:
                        correlated_conditions.append(
                            f"Strong relationship detected between {factor_a} and {factor_b} (coef: {val})"
                        )
                        high_corr_flags[key] = True
                    else:
                        high_corr_flags[key] = False

        return CorrelationReport(
            CorrelationMatrix=correlation_matrix,
            CoreCorrelatedConditions=correlated_conditions,
            HighCorrelationFlags=high_corr_flags,
            Metadata={"asset": context.Metadata.get("asset", "unknown")}
        )
