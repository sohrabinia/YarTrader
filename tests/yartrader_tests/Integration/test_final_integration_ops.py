import unittest
from datetime import datetime, timedelta
from src.Infrastructure.exceptions import ValidationException
from src.Application.Backtesting.models import BacktestScenario
from src.Application.Backtesting.engine import IntelligenceBacktestEngine
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Decision.Intelligence.engine import DecisionEngine
from src.Data.connector import ExternalDataPipelineConnector

from src.Application.Demo import (
    DemoScenarioRunner,
    DemoReportGenerator,
    create_trend_continuation_scenario
)
from src.Application.Deployment.config import ProductionConfig
from src.Application.Deployment.health import ProductionHealthChecker
from src.Application.Shadow.engine import ShadowModeEngine


class TestFinalIntegrationAndIntelligenceOperations(unittest.TestCase):
    """
    Final Integration & Operations Test Suite for YARTRADER.
    Aggregates Backtesting, Demo Scenarios, Production configs, health diagnostics,
    and Shadow Mode execution into a single, unified Operational Run.
    """

    def setUp(self) -> None:
        self.supervisor = IntelligenceSupervisor()
        self.decision_engine = DecisionEngine()
        self.connector = ExternalDataPipelineConnector()

        # 1. Backtesting setup
        self.backtest_engine = IntelligenceBacktestEngine(
            supervisor=self.supervisor,
            decision_engine=self.decision_engine,
            connector=self.connector
        )

        # 2. Demo setup
        self.demo_runner = DemoScenarioRunner()
        self.demo_generator = DemoReportGenerator()

        # 3. Health setup
        self.health_checker = ProductionHealthChecker()

        # 4. Shadow mode setup
        self.shadow_engine = ShadowModeEngine()

    def test_complete_platform_operational_run(self) -> None:
        """Verify that all major platform components operate harmoniously as a single, cohesive engine."""

        # --- Stage A: Production Configuration & Health Diagnostics ---
        config = ProductionConfig({
            "ENVIRONMENT": "production",
            "LOOKBACK_DAYS": 15,
            "API_TIMEOUT": 5.0,
            "LOG_LEVEL": "INFO"
        })
        self.assertTrue(config.runtime_check())

        diagnostics = self.health_checker.run_comprehensive_diagnostics()
        self.assertEqual(diagnostics["status"], "HEALTHY")
        self.assertEqual(diagnostics["subsystems"]["intelligence_pipeline"]["status"], "HEALTHY")

        # --- Stage B: Demo Scenario Processing & Reporting ---
        demo_sc = create_trend_continuation_scenario(asset="EURUSD")
        demo_res = self.demo_runner.run_scenario(demo_sc)
        self.assertTrue(demo_res.success)
        self.assertEqual(demo_res.final_decision_state, "Approved")

        demo_report = self.demo_generator.generate_report(demo_res)
        self.assertTrue("YARTRADER" in demo_report.rendered_summary or "YARTRADER" in demo_report.rendered_summary or "YarTrader" in demo_report.rendered_summary)

        # --- Stage C: Live Shadow Mode Session Ingestion ---
        shadow_session = self.shadow_engine.start_session("GBPUSD", "H1")
        self.assertTrue(shadow_session.is_active)

        shadow_report = self.shadow_engine.execute_tick(shadow_session.session_id)
        self.assertEqual(shadow_report.session_id, shadow_session.session_id)
        self.assertTrue(shadow_report.compliance_passed)
        self.assertGreater(shadow_report.metrics.processed_count, 0)

        stopped_shadow = self.shadow_engine.stop_session(shadow_session.session_id)
        self.assertFalse(stopped_shadow.is_active)

        # --- Stage D: Intelligence Backtesting Loop ---
        now = datetime.now()
        backtest_sc = BacktestScenario(
            scenario_id="final-bt-1",
            name="Final Integration Backtest",
            start_time=now - timedelta(hours=3),
            end_time=now,
            symbol="EURUSD",
            timeframe="H1",
            parameters={"interval_minutes": 60}
        )
        backtest_result = self.backtest_engine.run_backtest(backtest_sc)
        self.assertTrue(backtest_result.compliance_audit_passed)
        self.assertGreaterEqual(backtest_result.total_intervals_processed, 1)

        # Confirm all systems resolved without execution leakage
        self.assertTrue(demo_res.success)
        self.assertTrue(shadow_report.compliance_passed)
        self.assertTrue(backtest_result.compliance_audit_passed)

    def test_strict_platform_non_trading_seal(self) -> None:
        """Verify that the final integration tests contain absolutely zero execution leaks."""
        forbidden_keywords = [
            "or" + "der_placement",
            "exe" + "cute_order",
            "sen" + "d_broker_transaction",
            "bu" + "y_signal",
            "sel" + "l_signal",
            "pl" + "ace_order"
        ]

        # Scan our E2E test file itself for contiguous forbidden strings to be absolutely safe
        with open(__file__, "r", encoding="utf-8") as f:
            content = f.read()
            for kw in forbidden_keywords:
                self.assertNotIn(kw, content, f"E2E Safety Breach: E2E code contains trading keyword '{kw}'.")
