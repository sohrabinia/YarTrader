import unittest
from datetime import datetime, timedelta
from src.Core.entities import Asset, MarketData, RiskParameters
from src.Data.repositories import InMemoryRepository
from src.Decision.engine import AutonomousDecisionEngine
from src.Strategy.base import MomentumScoringStrategy
from src.Risk.evaluators import PortfolioRiskEvaluator

class TestDecisionEngine(unittest.TestCase):
    def test_decision_engine_recommendations(self):
        # Setup data
        repo = InMemoryRepository()

        asset1 = Asset("AAPL", "Apple Inc.", "Equity")
        asset2 = Asset("MSFT", "Microsoft Corp.", "Equity")
        repo.save_asset(asset1)
        repo.save_asset(asset2)

        now = datetime.now()
        # Feed 10 days of prices. Apple is trending up, Microsoft is neutral
        for i in range(10):
            ts = now - timedelta(days=10 - i)
            repo.save_market_data(MarketData("AAPL", 100.0 + i * 2, 1000000.0, ts))
            repo.save_market_data(MarketData("MSFT", 150.0, 1000000.0, ts))

        strategy = MomentumScoringStrategy("Momentum")
        risk_eval = PortfolioRiskEvaluator()
        engine = AutonomousDecisionEngine(repo, strategy, risk_eval)

        params = RiskParameters(
            max_single_asset_exposure=0.60,
            max_portfolio_drawdown=0.15,
            target_volatility_limit=0.30,
            leverage_allowed=False
        )

        report = engine.analyze_market_and_recommend(params)
        self.assertIsNotNone(report.decision_id)
        self.assertIn("AAPL", report.target_weights)
        self.assertIn("MSFT", report.target_weights)

        # Apple has high momentum, so it should have a higher score/weight than MSFT
        self.assertTrue(report.target_weights["AAPL"] > report.target_weights["MSFT"])

        # Ensure exposure limit is respected (max single asset exposure is 60%)
        self.assertTrue(report.target_weights["AAPL"] <= 0.6001)
