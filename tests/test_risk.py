import unittest
from src.Core.entities import RiskParameters
from src.Risk.evaluators import PortfolioRiskEvaluator

class TestRiskEvaluator(unittest.TestCase):
    def test_portfolio_risk_evaluator_safety(self):
        # Simple covariance mapping: Apple is 20% vol (0.04 variance), MSFT is 15% vol (0.0225 variance)
        covs = {
            "AAPL": {"AAPL": 0.04, "MSFT": 0.01},
            "MSFT": {"AAPL": 0.01, "MSFT": 0.0225}
        }
        evaluator = PortfolioRiskEvaluator(historical_covariances=covs)

        # Let's check a safe allocation
        weights = {"AAPL": 0.15, "MSFT": 0.15}
        params = RiskParameters(
            max_single_asset_exposure=0.20,
            max_portfolio_drawdown=0.15,
            target_volatility_limit=0.25,
            leverage_allowed=False
        )
        self.assertTrue(evaluator.check_allocation_safety(weights, params))

        # Check exposure violation (exceeds single asset exposure max of 20%)
        unsafe_exposure_weights = {"AAPL": 0.25, "MSFT": 0.05}
        self.assertFalse(evaluator.check_allocation_safety(unsafe_exposure_weights, params))

        # Check leverage violation (total weight = 1.2 > 1.0)
        unsafe_leverage_weights = {"AAPL": 0.20, "MSFT": 1.0}
        self.assertFalse(evaluator.check_allocation_safety(unsafe_leverage_weights, params))

    def test_portfolio_volatility_calculation(self):
        # Apple individual variance is 0.04 (standard dev = 20%)
        covs = {
            "AAPL": {"AAPL": 0.04}
        }
        evaluator = PortfolioRiskEvaluator(historical_covariances=covs)

        # If portfolio is 100% AAPL, vol should be exactly sqrt(1.0 * 1.0 * 0.04) = 20%
        vol = evaluator.calculate_portfolio_volatility({"AAPL": 1.0})
        self.assertAlmostEqual(vol, 0.20, places=6)
