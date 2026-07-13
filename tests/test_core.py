from datetime import datetime
from src.Core.entities import Asset, MarketData, RiskParameters, DecisionReport

def test_asset_creation():
    asset = Asset(symbol="AAPL", name="Apple Inc.", asset_class="Equity")
    assert asset.symbol == "AAPL"
    assert asset.name == "Apple Inc."
    assert asset.asset_class == "Equity"
    assert asset.is_active is True

def test_market_data_creation():
    now = datetime.now()
    data = MarketData(symbol="AAPL", price=150.0, volume=1000000.0, timestamp=now)
    assert data.symbol == "AAPL"
    assert data.price == 150.0
    assert data.volume == 1000000.0
    assert data.timestamp == now

def test_risk_parameters_creation():
    params = RiskParameters(
        max_single_asset_exposure=0.25,
        max_portfolio_drawdown=0.10,
        target_volatility_limit=0.15,
        leverage_allowed=False
    )
    assert params.max_single_asset_exposure == 0.25
    assert params.max_portfolio_drawdown == 0.10
    assert params.target_volatility_limit == 0.15
    assert params.leverage_allowed is False

def test_decision_report_creation():
    now = datetime.now()
    report = DecisionReport(
        decision_id="dec-123",
        target_weights={"AAPL": 0.5, "MSFT": 0.5},
        reasoning="Neutral scoring",
        risk_evaluation="PASSED",
        timestamp=now
    )
    assert report.decision_id == "dec-123"
    assert report.target_weights["AAPL"] == 0.5
    assert report.reasoning == "Neutral scoring"
    assert report.risk_evaluation == "PASSED"
