from typing import Dict, Any, Optional
from src.Strategy.Models.models import StrategyCandidate, StrategyScore
from src.Strategy.Evaluation.context import StrategyEvaluationContext
from src.Strategy.Evaluation.criteria import EvaluationCriteria
from src.Infrastructure.exceptions import ValidationException

class StrategyScorer:
    """
    Computes passive, parameter-driven evaluation scores across multiple dimensions
    for a given StrategyCandidate under a specific StrategyEvaluationContext.
    Guarantees no trading decisions or signal generations are made.
    """

    def calculate_score(
        self,
        candidate: StrategyCandidate,
        context: StrategyEvaluationContext
    ) -> StrategyScore:
        """
        Calculates score breakdown across dimensions:
        - ResearchAlignment
        - HistoricalCompatibility
        - RiskCompatibility
        - Stability
        - Complexity (Optional/Supported)
        - DataRequirements (Optional/Supported)
        """
        # 1. Validation
        if not candidate:
            raise ValidationException("StrategyCandidate cannot be None for scoring.")
        if not context:
            raise ValidationException("StrategyEvaluationContext cannot be None for scoring.")

        # 2. Base scores
        research_alignment = 0.80
        historical_compatibility = 0.75
        risk_compatibility = 0.85
        stability = 0.80
        complexity = 0.90
        data_requirements = 0.70

        # 3. Dynamic adjustment based on Research Insights
        if context.ResearchInsights:
            # Average confidence of insights
            confidences = []
            for insight in context.ResearchInsights:
                # Support both object attributes and dict get
                if hasattr(insight, "Confidence"):
                    confidences.append(insight.Confidence)
                elif hasattr(insight, "confidence"):
                    confidences.append(insight.confidence)
                elif isinstance(insight, dict):
                    confidences.append(insight.get("confidence", 0.5))
                else:
                    confidences.append(0.5)

            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                # Boost alignment and stability if confidence is high, otherwise reduce
                research_alignment = min(1.0, max(0.0, research_alignment * (0.5 + avg_confidence)))
                stability = min(1.0, max(0.0, stability * (0.6 + 0.5 * avg_confidence)))

        # 4. Dynamic adjustment based on Risk Context
        risk_limit = context.RiskContext.get("risk_limit", 1.0)
        if risk_limit < 0.5:
            # Stricter risk limits lower compatibility if candidate research context shows higher risk
            risk_compatibility = min(1.0, max(0.0, risk_compatibility * 0.9))
        elif risk_limit > 0.8:
            risk_compatibility = min(1.0, max(0.0, risk_compatibility * 1.05))

        # 5. Dynamic adjustment based on Historical Scenario info
        scenario_success_rate = context.HistoricalScenarioInfo.get("success_rate", 0.5)
        if scenario_success_rate > 0.7:
            historical_compatibility = min(1.0, max(0.0, historical_compatibility * 1.1))
            stability = min(1.0, max(0.0, stability * 1.05))
        elif scenario_success_rate < 0.4:
            historical_compatibility = min(1.0, max(0.0, historical_compatibility * 0.8))
            stability = min(1.0, max(0.0, stability * 0.9))

        # 6. Gather all criteria
        criteria_scores = {
            "ResearchAlignment": round(research_alignment, 4),
            "HistoricalCompatibility": round(historical_compatibility, 4),
            "RiskCompatibility": round(risk_compatibility, 4),
            "Stability": round(stability, 4),
            EvaluationCriteria.STABILITY: round(stability, 4),
            EvaluationCriteria.COMPLEXITY: round(complexity, 4),
            EvaluationCriteria.DATA_REQUIREMENTS: round(data_requirements, 4),
            EvaluationCriteria.RISK_COMPATIBILITY: round(risk_compatibility, 4)
        }

        # Calculate overall score as weighted or simple average of core four
        core_scores = [research_alignment, historical_compatibility, risk_compatibility, stability]
        overall_score = round(sum(core_scores) / len(core_scores), 4)

        # Confidence is derived from average confidence of research insights or default
        confidence_val = 0.85
        if context.ResearchInsights and confidences:
            confidence_val = round(sum(confidences) / len(confidences), 4)

        return StrategyScore(
            OverallScore=overall_score,
            Confidence=confidence_val,
            Criteria=criteria_scores
        )
