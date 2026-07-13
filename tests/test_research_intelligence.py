from datetime import datetime, timedelta
from src.Research.MarketAnalysis.Models.models import MarketObservation, ResearchRequest, ResearchResult, MarketInsight
from src.Research.Indicators.Models.models import IndicatorDefinition, IndicatorResult
from src.Research.MarketAnalysis.Services.services import MarketAnalysisEngine, ResearchProcessor
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchEngine, IMarketAnalyzer, IResearchRepository
from src.Research.Indicators.Interfaces.interfaces import IIndicatorProvider

def test_research_modules_imports():
    """Verify that all Phase 3 Research Intelligence classes are successfully imported."""
    assert MarketObservation is not None
    assert ResearchRequest is not None
    assert ResearchResult is not None
    assert MarketInsight is not None
    assert IndicatorDefinition is not None
    assert IndicatorResult is not None
    assert MarketAnalysisEngine is not None
    assert ResearchProcessor is not None
    assert IResearchEngine is not None
    assert IMarketAnalyzer is not None
    assert IResearchRepository is not None
    assert IIndicatorProvider is not None

def test_research_models_properties():
    """Verify research request, result, observation, and insight models."""
    now = datetime.now()
    req = ResearchRequest(
        Asset="EURUSD",
        StartTime=now - timedelta(days=5),
        EndTime=now,
        Context={"timeframe_multiplier": 2}
    )
    assert req.asset == "EURUSD"
    assert req.context["timeframe_multiplier"] == 2

    res = ResearchResult(
        Request=req,
        Findings={"volatility": 0.12},
        ConfidenceScore=0.92,
        CreatedAt=now
    )
    assert res.request.asset == "EURUSD"
    assert res.confidence_score == 0.92

    obs = MarketObservation(
        Asset="EURUSD",
        Timestamp=now,
        Observations={"rsi": 58.2},
        Source="MT5"
    )
    assert obs.asset == "EURUSD"
    assert obs.observations["rsi"] == 58.2

    insight = MarketInsight(
        Category="Trend",
        Description="Moderately bullish",
        Confidence=0.75,
        CreatedAt=now
    )
    assert insight.category == "Trend"
    assert insight.confidence == 0.75

def test_indicator_models():
    """Verify indicator definition and result models."""
    now = datetime.now()
    definition = IndicatorDefinition(
        Name="Simple Moving Average",
        Type="SMA",
        Parameters={"period": 20}
    )
    assert definition.name == "Simple Moving Average"
    assert definition.parameters["period"] == 20

    res = IndicatorResult(
        Definition=definition,
        Value=1.0950,
        CalculatedAt=now
    )
    assert res.definition.name == "Simple Moving Average"
    assert res.value == 1.0950

def test_research_services():
    """Verify placeholder research processor and market analysis engines execute cleanly."""
    now = datetime.now()

    # 1. Test MarketAnalysisEngine
    analysis_engine = MarketAnalysisEngine()
    obs_list = [
        MarketObservation("AAPL", now, {"price_trend": "bullish", "confidence": 0.8}, "MT5")
    ]
    insights = analysis_engine.analyze_observations(obs_list)
    assert len(insights) == 1
    assert insights[0].Category == "TrendAnalysis"
    assert "bullish" in insights[0].Description
    assert insights[0].Confidence == 0.8

    # 2. Test ResearchProcessor
    processor = ResearchProcessor()
    req = ResearchRequest("AAPL", now - timedelta(days=1), now, {"theme": "volatility_breakout"})
    result = processor.analyze_market(req)
    assert result.Request.Asset == "AAPL"
    assert result.Findings["status"] == "completed"
    assert result.ConfidenceScore == 0.85
