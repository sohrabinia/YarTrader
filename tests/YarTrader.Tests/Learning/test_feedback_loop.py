import pytest
from src.Learning.Services.post_trade_analysis import PostTradeAnalyzer

def test_post_trade_analyzer_winning_trade():
    trade_record = {
        "trade_id": "tr-001",
        "symbol": "EURUSD",
        "net_pnl": 15.5
    }
    feedback = PostTradeAnalyzer.analyze_trade_outcome(trade_record)
    assert feedback["prediction_accuracy"] == 85.0
    assert feedback["risk_quality"] == 90.0
    assert feedback["net_pnl"] == 15.5

def test_post_trade_analyzer_losing_trade():
    trade_record = {
        "trade_id": "tr-002",
        "symbol": "BITCOIN",
        "net_pnl": -10.0
    }
    feedback = PostTradeAnalyzer.analyze_trade_outcome(trade_record)
    assert feedback["prediction_accuracy"] == 40.0
    assert "Avoid low volatility" in feedback["lesson"]
