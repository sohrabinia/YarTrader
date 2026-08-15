import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.Application.Backtesting.engine import IntelligenceBacktestEngine
from src.Application.Backtesting.models import BacktestScenario
from src.Data.Market.models import CandleRecord


class TestForensicBacktestLeakage(unittest.TestCase):

    def setUp(self):
        self.mock_supervisor = MagicMock()
        self.mock_decision_engine = MagicMock()
        self.mock_connector = MagicMock()

        # Mock supervisor behaviors
        mock_ctx = MagicMock()
        self.mock_supervisor.orchestrate.return_value = mock_ctx
        self.mock_supervisor.compile_to_decision_context.return_value = MagicMock()

        # Mock decision engine report
        mock_report = MagicMock()
        from src.Decision.Models.models import DecisionState
        mock_report.State = DecisionState.APPROVED
        mock_report.Confidence = 0.90
        mock_report.Context.ResearchInsights = []
        self.mock_decision_engine.evaluate_intelligence_context.return_value = mock_report

    def test_no_future_bar_access(self):
        """Verifies that no record with timestamp > current_time enters the backtest engine context."""
        start_time = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)

        # Connector returns 1 valid past candle and 1 future leaked candle
        past_candle = CandleRecord(
            timestamp=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
            open=2300.0, high=2305.0, low=2295.0, close=2302.0, volume=100.0
        )
        future_candle = CandleRecord(
            timestamp=datetime(2026, 1, 10, 15, 0, tzinfo=timezone.utc), # Leaked future timestamp!
            open=2500.0, high=2510.0, low=2490.0, close=2505.0, volume=100.0
        )

        self.mock_connector.retrieve_and_process.return_value = ([past_candle, future_candle], {})

        engine = IntelligenceBacktestEngine(
            supervisor=self.mock_supervisor,
            decision_engine=self.mock_decision_engine,
            connector=self.mock_connector
        )

        scenario = BacktestScenario(
            scenario_id="scen-leakage-test",
            name="Leakage Test",
            start_time=start_time,
            end_time=start_time + timedelta(hours=1),
            symbol="XAUUSD",
            timeframe="M15",
            parameters={"interval_minutes": 15}
        )

        res = engine.run_backtest(scenario)
        self.assertTrue(res.compliance_audit_passed)

    def test_trade_accounting_reconciliation(self):
        """Verifies that individual trade P&L sums equal net backtest P&L."""
        start_time = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
        c1 = CandleRecord(timestamp=start_time, open=2300.0, high=2305.0, low=2295.0, close=2300.0, volume=100.0)
        c2 = CandleRecord(timestamp=start_time + timedelta(minutes=15), open=2300.0, high=2320.0, low=2290.0, close=2310.0, volume=100.0)

        self.mock_connector.retrieve_and_process.return_value = ([c1, c2], {})

        engine = IntelligenceBacktestEngine(
            supervisor=self.mock_supervisor,
            decision_engine=self.mock_decision_engine,
            connector=self.mock_connector
        )

        scenario = BacktestScenario(
            scenario_id="scen-accounting-test",
            name="Accounting Test",
            start_time=start_time,
            end_time=start_time + timedelta(minutes=45),
            symbol="XAUUSD",
            timeframe="M15",
            parameters={"initial_balance": 10000.0, "interval_minutes": 15}
        )

        res = engine.run_backtest(scenario)
        metrics = res.performance_metrics

        sum_trade_pnl = sum(t["p_and_l"] for t in metrics["trade_list"])
        net_pnl = metrics["net_p_and_l"]

        self.assertAlmostEqual(sum_trade_pnl, net_pnl, places=2)


if __name__ == "__main__":
    unittest.main()
