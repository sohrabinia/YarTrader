from dataclasses import dataclass, field
from typing import Any, Dict, List
from src.Risk.Analysis.context import RiskAnalysisContext
from src.Infrastructure.exceptions import ValidationException

@dataclass(frozen=True)
class ExposureAssessment:
    """
    Represents the output findings of an exposure analysis.
    This contains purely analytical results and is decoupled from trading operations.
    """
    ConcentrationRating: str  # e.g., "High", "Medium", "Low"
    ConcentrationNotes: str
    DependencyAnalysis: Dict[str, Any]
    SensitivityMetrics: Dict[str, float]
    MarketConditionExposure: Dict[str, Any]
    SummaryFindings: List[str] = field(default_factory=list)


class ExposureAnalyzer:
    """
    Analyzes exposure characteristics of a strategy candidate or market state.
    Provides purely passive, analytical assessment findings.
    """

    def analyze_exposure(self, context: RiskAnalysisContext) -> ExposureAssessment:
        """
        Runs concentration, dependency, and sensitivity analyses.
        """
        if not context:
            raise ValidationException("RiskAnalysisContext cannot be None for exposure analysis.")

        # 1. Concentration Analysis
        features = context.MarketFeatureSet or {}
        strategy_eval = context.StrategyEvaluation or {}

        # Calculate some analytical properties from features
        volatility_val = features.get("volatility", 0.15)
        trend_val = features.get("trend_strength", 0.5)

        # Build concentration details
        concentration_rating = "Low"
        concentration_notes = "Diverse conditions observed; low style concentration."
        if trend_val > 0.8:
            concentration_rating = "High"
            concentration_notes = "High concentration condition: heavy dependency on single trend state."

        # 2. Dependency Analysis
        dependency = {
            "volatility_state_dependency": "Strong dependency on volatility state" if volatility_val > 0.25 else "Moderate dependency",
            "timeframe_dependency": context.Metadata.get("timeframe", "unknown")
        }

        # 3. Sensitivity Evaluation
        sensitivity = {
            "beta": round(float(strategy_eval.get("beta", 1.0)), 2),
            "volatility_sensitivity": round(volatility_val * 1.5, 4),
            "regime_shift_sensitivity": 0.85 if volatility_val > 0.2 else 0.4
        }

        # 4. Market Condition Exposure
        market_condition = {
            "bullish_exposure": "Favorable" if trend_val > 0.6 else "Neutral",
            "bearish_exposure": "Unfavorable" if trend_val > 0.6 else "Neutral",
            "choppy_exposure": "High risk" if volatility_val > 0.25 else "Acceptable"
        }

        # Assemble summary findings
        summary = []
        if concentration_rating == "High":
            summary.append("High concentration condition")
        if volatility_val > 0.25:
            summary.append("Strong dependency on volatility state")
        else:
            summary.append("Low diversification condition")

        return ExposureAssessment(
            ConcentrationRating=concentration_rating,
            ConcentrationNotes=concentration_notes,
            DependencyAnalysis=dependency,
            SensitivityMetrics=sensitivity,
            MarketConditionExposure=market_condition,
            SummaryFindings=summary
        )
