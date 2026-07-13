import unittest
from datetime import datetime
from src.Core.entities import Asset, MarketData, RiskParameters, DecisionReport

class TestCoreEntities(unittest.TestCase):
    def test_asset_creation(self):
        asset = Asset(symbol="AAPL", name="Apple Inc.", asset_class="Equity")
        self.assertEqual(asset.symbol, "AAPL")
        self.assertEqual(asset.name, "Apple Inc.")
        self.assertEqual(asset.asset_class, "Equity")
        self.assertTrue(asset.is_active)

    def test_market_data_creation(self):
        now = datetime.now()
        data = MarketData(symbol="AAPL", price=150.0, volume=1000000.0, timestamp=now)
        self.assertEqual(data.symbol, "AAPL")
        self.assertEqual(data.price, 150.0)
        self.assertEqual(data.volume, 1000000.0)
        self.assertEqual(data.timestamp, now)

    def test_risk_parameters_creation(self):
        params = RiskParameters(
            max_single_asset_exposure=0.25,
            max_portfolio_drawdown=0.10,
            target_volatility_limit=0.15,
            leverage_allowed=False
        )
        self.assertEqual(params.max_single_asset_exposure, 0.25)
        self.assertEqual(params.max_portfolio_drawdown, 0.10)
        self.assertEqual(params.target_volatility_limit, 0.15)
        self.assertFalse(params.leverage_allowed)

    def test_decision_report_creation(self):
        now = datetime.now()
        report = DecisionReport(
            decision_id="dec-123",
            target_weights={"AAPL": 0.5, "MSFT": 0.5},
            reasoning="Neutral scoring",
            risk_evaluation="PASSED",
            timestamp=now
        )
        self.assertEqual(report.decision_id, "dec-123")
        self.assertEqual(report.target_weights["AAPL"], 0.5)
        self.assertEqual(report.reasoning, "Neutral scoring")
        self.assertEqual(report.risk_evaluation, "PASSED")
