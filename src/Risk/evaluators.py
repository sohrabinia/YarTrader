import math
from typing import Dict, List
from src.Core.entities import RiskParameters
from src.Core.interfaces import IRiskEvaluator

class PortfolioRiskEvaluator(IRiskEvaluator):
    """
    Evaluates proposed portfolio weight structures against strict safety rules and calculates risk metrics.
    """
    def __init__(self, historical_covariances: Dict[str, Dict[str, float]] = None) -> None:
        # Simple covariance matrix representation: {"AAPL": {"AAPL": 0.04, "MSFT": 0.02}, ...}
        self._covariances = historical_covariances or {}

    def check_allocation_safety(self, weights: Dict[str, float], params: RiskParameters) -> bool:
        """
        Validates whether the proposed weights are completely safe under risk parameters.
        Checks single asset limits, total weight limit (leverage), and expected volatility bounds.
        """
        # Rule 1: Sum of weights must not exceed 1.0 if leverage is not allowed
        total_weight = sum(weights.values())
        if total_weight > 1.0001 and not params.leverage_allowed:
            return False

        # Rule 2: Ensure weights are non-negative (no short selling)
        if any(w < -0.0001 for w in weights.values()):
            return False

        # Rule 3: Single asset exposure limit
        for symbol, weight in weights.items():
            if weight > params.max_single_asset_exposure:
                return False

        # Rule 4: Volatility limits check
        expected_vol = self.calculate_portfolio_volatility(weights)
        if expected_vol > params.target_volatility_limit:
            return False

        return True

    def calculate_portfolio_volatility(self, weights: Dict[str, float]) -> float:
        """
        Calculates expected annualized portfolio volatility using weights and historical covariances.
        Formula: sqrt(W^T * Cov * W)
        """
        if not weights:
            return 0.0

        variance = 0.0
        for asset_i, w_i in weights.items():
            for asset_j, w_j in weights.items():
                cov_ij = self._covariances.get(asset_i, {}).get(asset_j, 0.0)
                # If self-covariance (variance) is missing, assign a safe default standard deviation
                if asset_i == asset_j and cov_ij == 0.0:
                    cov_ij = 0.0625  # defaults to 25% individual asset standard deviation (0.25^2)
                variance += w_i * w_j * cov_ij

        return math.sqrt(max(0.0, variance))
