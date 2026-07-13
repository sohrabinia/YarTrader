import unittest
from datetime import datetime, timedelta
from src.Core.entities import PerformanceMetric
from src.Learning.performance import ContinuousPerformanceTracker

class TestLearningPerformance(unittest.TestCase):
    def test_sharpe_and_sortino_ratios(self):
        tracker = ContinuousPerformanceTracker()

        # Simple returns list: some gains, some losses (daily returns)
        returns = [0.001, 0.002, -0.0015, 0.003, -0.0005, 0.0012]

        # Calculate Sharpe
        sharpe = tracker.calculate_sharpe_ratio(returns, risk_free_rate=0.01)
        self.assertIsInstance(sharpe, float)

        # Calculate Sortino
        sortino = tracker.calculate_sortino_ratio(returns, risk_free_rate=0.01)
        self.assertIsInstance(sortino, float)

    def test_performance_drift_detection(self):
        tracker = ContinuousPerformanceTracker()

        now = datetime.now()
        # Log 5 historical metrics that are very stable (around 1.5)
        for i in range(5):
            tracker.log_metric(PerformanceMetric(
                metric_id=f"m-{i}",
                metric_name="Sharpe",
                value=1.5,
                calculated_at=now - timedelta(days=5 - i)
            ))

        # Standard deviation is 0.0, so no drift is detected yet
        self.assertFalse(tracker.detect_performance_drift("Sharpe", threshold=2.0))

        # Log a few slightly different values to establish a variance
        tracker.log_metric(PerformanceMetric(
            metric_id="m-5",
            metric_name="Sharpe",
            value=1.6,
            calculated_at=now - timedelta(days=1)
        ))
        tracker.log_metric(PerformanceMetric(
            metric_id="m-6",
            metric_name="Sharpe",
            value=1.4,
            calculated_at=now - timedelta(days=2)
        ))

        # Now, log a highly drifted value (e.g., performance tanked to -2.0)
        tracker.log_metric(PerformanceMetric(
            metric_id="m-drift",
            metric_name="Sharpe",
            value=-2.0,
            calculated_at=now
        ))

        # Drift should be detected with a threshold of 2.0 standard deviations
        self.assertTrue(tracker.detect_performance_drift("Sharpe", threshold=2.0))
