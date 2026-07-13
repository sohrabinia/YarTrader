from datetime import datetime
from typing import Dict, List
from src.Core.entities import PerformanceMetric
from src.Core.interfaces import IPerformanceTracker

class ContinuousPerformanceTracker(IPerformanceTracker):
    """
    Implements learning feedback tracking and classical risk/return metric analysis.
    Monitors model performance characteristics over time to trigger retuning flags (strictly no ML models are run here).
    """
    def __init__(self) -> None:
        self._metrics: Dict[str, List[PerformanceMetric]] = {}

    def log_metric(self, metric: PerformanceMetric) -> None:
        """Stores a calculated metric trace in memory."""
        if metric.metric_name not in self._metrics:
            self._metrics[metric.metric_name] = []
        self._metrics[metric.metric_name].append(metric)

    def get_metric_history(self, metric_name: str) -> List[PerformanceMetric]:
        """Queries metric logs over time."""
        return self._metrics.get(metric_name, [])

    def detect_performance_drift(self, metric_name: str, threshold: float) -> bool:
        """
        Calculates drift based on standard deviation of recent metric values.
        Returns True if the absolute deviation of the latest point exceeds threshold.
        """
        history = self.get_metric_history(metric_name)
        if len(history) < 5:
            return False  # insufficient history to establish a reliable mean

        values = [m.value for m in history]
        latest_val = values[-1]
        past_vals = values[:-1]

        mean = sum(past_vals) / len(past_vals)
        variance = sum((x - mean) ** 2 for x in past_vals) / len(past_vals)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return False

        z_score = abs(latest_val - mean) / std_dev
        return z_score > threshold

    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Calculates annualized Sharpe Ratio for a stream of return rates.
        Formula: (Average Return - Risk Free Rate) / Standard Deviation of Return
        """
        if not returns:
            return 0.0

        mean_return = sum(returns) / len(returns)
        if len(returns) < 2:
            return 0.0

        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        # Annualized Sharpe ratio (assuming daily returns, 252 trading days)
        annualized_return = mean_return * 252
        annualized_vol = std_dev * (252 ** 0.5)

        return (annualized_return - risk_free_rate) / annualized_vol

    @staticmethod
    def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Calculates Sortino Ratio, considering only downside standard deviation.
        """
        if not returns or len(returns) < 2:
            return 0.0

        mean_return = sum(returns) / len(returns)
        downside_returns = [r for r in returns if r < 0.0]

        if not downside_returns:
            return 0.0

        # Downside variance
        downside_variance = sum(r ** 2 for r in downside_returns) / len(returns)
        downside_deviation = downside_variance ** 0.5

        if downside_deviation == 0:
            return 0.0

        annualized_return = mean_return * 252
        annualized_downside_vol = downside_deviation * (252 ** 0.5)

        return (annualized_return - risk_free_rate) / annualized_downside_vol
