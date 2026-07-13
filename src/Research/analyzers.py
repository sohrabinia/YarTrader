import math
from typing import List, Optional
from src.Core.entities import MarketData

class TechnicalAnalyzer:
    """Provides pure mathematical and statistical calculators for financial market analysis."""

    @staticmethod
    def calculate_simple_moving_average(prices: List[float], period: int) -> Optional[float]:
        """Calculates Simple Moving Average (SMA) of a list of floats."""
        if not prices or len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_exponential_moving_average(prices: List[float], period: int) -> Optional[float]:
        """Calculates Exponential Moving Average (EMA) of a list of floats."""
        if not prices or len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        # Start seed with simple average
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    @staticmethod
    def calculate_historical_volatility(prices: List[float]) -> Optional[float]:
        """Calculates annualized volatility based on price returns."""
        if len(prices) < 2:
            return None

        # Calculate log returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                returns.append(math.log(prices[i] / prices[i - 1]))
            else:
                returns.append(0.0)

        if len(returns) < 2:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        standard_deviation = math.sqrt(variance)

        # Annualized volatility (assuming daily data, 252 trading days)
        return standard_deviation * math.sqrt(252)
