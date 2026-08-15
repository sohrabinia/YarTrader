import unittest
from datetime import datetime

from src.Decision.Intelligence.engine import DecisionEngine
from src.Decision.Intelligence.models import DecisionIntelligenceContext
from src.Decision.Models.models import DecisionState
from src.Research.MarketAnalysis.Models.models import MarketInsight
from src.Research.Engine.models import PatternObservation
from src.Strategy.Models.models import StrategyEvaluation, StrategyScore
from src.Risk.Models.models import RiskAssessment, PortfolioRisk
from src.Infrastructure.exceptions import ValidationException


class TestGateForensics(unittest.TestCase):

    def setUp(self):
        self.engine = DecisionEngine()

    def test_decision_gate_validation_exception_on_empty_context(self):
        """Verifies that a completely empty context raises ValidationException."""
        empty_ctx = DecisionIntelligenceContext(
            ResearchInsights=[],
            PatternObservations=[],
            StrategyEvaluations=[],
            RiskAssessments=[],
            MarketConditions={},
            HistoricalEvidence={},
            Metadata={}
        )

        with self.assertRaises(ValidationException):
            self.engine.evaluate_intelligence_context(empty_ctx)

    def test_decision_gate_rejected_on_risk_rejection(self):
        """Verifies that an unapproved risk assessment yields DecisionState.REJECTED."""
        ctx = DecisionIntelligenceContext(
            ResearchInsights=[MarketInsight(Category="Trend", Description="Bullish", Confidence=0.8, CreatedAt=datetime.now())],
            PatternObservations=[PatternObservation("Double Bottom", "Pattern", 0.8, datetime.now(), ["price"])],
            StrategyEvaluations=[StrategyEvaluation(StrategyId="s1", Score=StrategyScore(OverallScore=0.8, Confidence=0.85, Criteria={}), EvaluationNotes="Ok", EvaluatedAt=datetime.now())],
            RiskAssessments=[RiskAssessment(IsApproved=False, RiskProfileName="Moderate", PortfolioRiskMetrics=PortfolioRisk(0.15, 0.10, 0.0), AssessmentNotes="Risk High", AssessedAt=datetime.now())],
            MarketConditions={"timeframe": "M15"},
            HistoricalEvidence={"agent_context_id": "ctx-1"},
            Metadata={"asset": "XAUUSD"}
        )

        report = self.engine.evaluate_intelligence_context(ctx)
        self.assertEqual(report.State, DecisionState.REJECTED)

    def test_decision_gate_approved_on_valid_inputs(self):
        """Verifies positive path yields DecisionState.APPROVED when research, strategy, and risk are valid."""
        ctx = DecisionIntelligenceContext(
            ResearchInsights=[MarketInsight(Category="Trend", Description="Bullish", Confidence=0.85, CreatedAt=datetime.now())],
            PatternObservations=[PatternObservation("Double Bottom", "Pattern", 0.85, datetime.now(), ["price"])],
            StrategyEvaluations=[StrategyEvaluation(StrategyId="s1", Score=StrategyScore(OverallScore=0.85, Confidence=0.90, Criteria={}), EvaluationNotes="Ok", EvaluatedAt=datetime.now())],
            RiskAssessments=[RiskAssessment(IsApproved=True, RiskProfileName="Moderate", PortfolioRiskMetrics=PortfolioRisk(0.12, 0.05, 0.0), AssessmentNotes="Approved", AssessedAt=datetime.now())],
            MarketConditions={"timeframe": "M15"},
            HistoricalEvidence={"agent_context_id": "ctx-1"},
            Metadata={"asset": "XAUUSD"}
        )

        report = self.engine.evaluate_intelligence_context(ctx)
        self.assertEqual(report.State, DecisionState.APPROVED)


if __name__ == "__main__":
    unittest.main()
