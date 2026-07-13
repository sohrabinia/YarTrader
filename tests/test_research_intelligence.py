import unittest
from datetime import datetime, timedelta
from src.Research.MarketAnalysis.Models.models import MarketObservation, ResearchRequest, ResearchResult, MarketInsight
from src.Research.Indicators.Models.models import IndicatorDefinition, IndicatorResult
from src.Research.MarketAnalysis.Services.services import MarketAnalysisEngine, ResearchProcessor
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchEngine, IMarketAnalyzer, IResearchRepository
from src.Research.Indicators.Interfaces.interfaces import IIndicatorProvider

class TestResearchIntelligence(unittest.TestCase):
    def test_research_modules_imports(self):
        """Verify that all Phase 3 Research Intelligence classes are successfully imported."""
        self.assertIsNotNone(MarketObservation)
        self.assertIsNotNone(ResearchRequest)
        self.assertIsNotNone(ResearchResult)
        self.assertIsNotNone(MarketInsight)
        self.assertIsNotNone(IndicatorDefinition)
        self.assertIsNotNone(IndicatorResult)
        self.assertIsNotNone(MarketAnalysisEngine)
        self.assertIsNotNone(ResearchProcessor)
        self.assertIsNotNone(IResearchEngine)
        self.assertIsNotNone(IMarketAnalyzer)
        self.assertIsNotNone(IResearchRepository)
        self.assertIsNotNone(IIndicatorProvider)

    def test_research_models_properties(self):
        """Verify research request, result, observation, and insight models."""
        now = datetime.now()
        req = ResearchRequest(
            Asset="EURUSD",
            StartTime=now - timedelta(days=5),
            EndTime=now,
            Context={"timeframe_multiplier": 2}
        )
        self.assertEqual(req.asset, "EURUSD")
        self.assertEqual(req.context["timeframe_multiplier"], 2)

        res = ResearchResult(
            Request=req,
            Findings={"volatility": 0.12},
            ConfidenceScore=0.92,
            CreatedAt=now
        )
        self.assertEqual(res.request.asset, "EURUSD")
        self.assertEqual(res.confidence_score, 0.92)

        obs = MarketObservation(
            Asset="EURUSD",
            Timestamp=now,
            Observations={"rsi": 58.2},
            Source="MT5"
        )
        self.assertEqual(obs.asset, "EURUSD")
        self.assertEqual(obs.observations["rsi"], 58.2)

        insight = MarketInsight(
            Category="Trend",
            Description="Moderately bullish",
            Confidence=0.75,
            CreatedAt=now
        )
        self.assertEqual(insight.category, "Trend")
        self.assertEqual(insight.confidence, 0.75)

    def test_indicator_models(self):
        """Verify indicator definition and result models."""
        now = datetime.now()
        definition = IndicatorDefinition(
            Name="Simple Moving Average",
            Type="SMA",
            Parameters={"period": 20}
        )
        self.assertEqual(definition.name, "Simple Moving Average")
        self.assertEqual(definition.parameters["period"], 20)

        res = IndicatorResult(
            Definition=definition,
            Value=1.0950,
            CalculatedAt=now
        )
        self.assertEqual(res.definition.name, "Simple Moving Average")
        self.assertEqual(res.value, 1.0950)

    def test_research_services(self):
        """Verify placeholder research processor and market analysis engines execute cleanly."""
        now = datetime.now()

        # 1. Test MarketAnalysisEngine
        analysis_engine = MarketAnalysisEngine()
        obs_list = [
            MarketObservation("AAPL", now, {"price_trend": "bullish", "confidence": 0.8}, "MT5")
        ]
        insights = analysis_engine.analyze_observations(obs_list)
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].Category, "TrendAnalysis")
        self.assertIn("bullish", insights[0].Description)
        self.assertEqual(insights[0].Confidence, 0.8)

        # 2. Test ResearchProcessor
        processor = ResearchProcessor()
        req = ResearchRequest("AAPL", now - timedelta(days=1), now, {"theme": "volatility_breakout"})
        result = processor.analyze_market(req)
        self.assertEqual(result.Request.Asset, "AAPL")
        self.assertEqual(result.Findings["status"], "completed")
        self.assertEqual(result.ConfidenceScore, 0.85)
