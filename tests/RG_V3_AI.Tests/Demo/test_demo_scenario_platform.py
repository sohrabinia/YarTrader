import unittest
from datetime import datetime
from typing import Any
from src.Infrastructure.exceptions import ValidationException
from src.Decision.Models.models import DecisionState
from src.Application.Dashboard.services import DashboardAggregatorService
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Decision.Intelligence.engine import DecisionEngine
from src.Data.connector import ExternalDataPipelineConnector
from src.Application.Knowledge.knowledge import IntelligenceKnowledgeBase
from src.Application.Monitoring.monitoring import IntelligenceMonitoringPlatform
from src.Application.Services.api import ServiceRequestDTO, ServiceOrchestrator

from src.Application.Demo import (
    DemoScenario,
    DemoScenarioRunner,
    DemoReportGenerator,
    load_scenario_library,
    create_trend_continuation_scenario,
    create_trend_reversal_scenario,
    create_high_volatility_scenario,
    create_low_liquidity_scenario,
    create_conflicting_signals_scenario
)


class TestIntelligenceDemoScenarioPlatform(unittest.TestCase):
    """
    Comprehensive test suite validating Phase 34: Intelligence Demo Scenario Platform.
    Verifies 5 scenarios, trace completeness, report generation, dashboard metrics,
    and strict non-trading safety.
    """

    def setUp(self) -> None:
        self.runner = DemoScenarioRunner()
        self.generator = DemoReportGenerator()

        # Initialize dashboard aggregator components
        self.supervisor = IntelligenceSupervisor()
        self.decision_engine = DecisionEngine()
        self.connector = ExternalDataPipelineConnector()
        self.kb = IntelligenceKnowledgeBase()
        self.monitor = IntelligenceMonitoringPlatform()

        self.aggregator = DashboardAggregatorService(
            self.supervisor,
            self.decision_engine,
            self.connector,
            self.kb,
            self.monitor
        )
        self.orchestrator = ServiceOrchestrator()
        self.orchestrator.set_dashboard_aggregator(self.aggregator)

    def test_scenario_library_loading(self) -> None:
        """Verify scenario library loads exactly five scenarios with non-empty price streams."""
        scenarios = load_scenario_library(asset="EURUSD")
        self.assertEqual(len(scenarios), 5)

        ids = [sc.scenario_id for sc in scenarios]
        self.assertIn("demo-trend-continuation", ids)
        self.assertIn("demo-trend-reversal", ids)
        self.assertIn("demo-high-volatility", ids)
        self.assertIn("demo-low-liquidity", ids)
        self.assertIn("demo-conflicting-signals", ids)

        for sc in scenarios:
            self.assertEqual(sc.asset, "EURUSD")
            self.assertEqual(sc.timeframe, "H1")
            self.assertGreater(len(sc.price_data), 0)

    def test_trend_continuation_scenario_execution(self) -> None:
        """Verify trend continuation scenario resolves to APPROVED state."""
        sc = create_trend_continuation_scenario(asset="GBPUSD")
        result = self.runner.run_scenario(sc)

        self.assertTrue(result.success)
        self.assertEqual(result.final_decision_state, DecisionState.APPROVED)
        self.assertGreaterEqual(result.overall_confidence, 0.75)
        self.assertEqual(len(result.steps), 8)  # 8 stages captured

        # Verify step traces are present and marked SUCCESS
        step_names = [step.step_name for step in result.steps]
        self.assertEqual(
            step_names,
            [
                "Input",
                "Feature Extraction",
                "Research",
                "Strategy Evaluation",
                "Risk Analysis",
                "Decision",
                "Validation",
                "Final Explainable Report"
            ]
        )
        for step in result.steps:
            self.assertEqual(step.status, "SUCCESS")
            self.assertGreaterEqual(step.duration_ms, 0.0)

    def test_trend_reversal_scenario_execution(self) -> None:
        """Verify trend reversal scenario executes and handles changing momentum."""
        sc = create_trend_reversal_scenario(asset="GBPUSD")
        result = self.runner.run_scenario(sc)

        self.assertTrue(result.success)
        # Expect either rejected, or review required based on sudden negative return shift
        self.assertIn(result.final_decision_state, [DecisionState.REJECTED, DecisionState.REVIEW_REQUIRED])

    def test_high_volatility_scenario_execution(self) -> None:
        """Verify high volatility scenario fails risk limits and resolves to REJECTED."""
        sc = create_high_volatility_scenario(asset="GBPUSD")
        result = self.runner.run_scenario(sc)

        self.assertTrue(result.success)
        self.assertEqual(result.final_decision_state, DecisionState.REJECTED)

        # Verify risk step result details
        risk_step = result.steps[4]
        self.assertEqual(risk_step.step_name, "Risk Analysis")
        self.assertFalse(risk_step.payload["is_approved"])
        self.assertEqual(risk_step.payload["risk_profile"], "Low")

    def test_low_liquidity_scenario_execution(self) -> None:
        """Verify low liquidity scenario resolves to REVIEW_REQUIRED or INSUFFICIENT_DATA."""
        sc = create_low_liquidity_scenario(asset="GBPUSD")
        result = self.runner.run_scenario(sc)

        self.assertTrue(result.success)
        self.assertIn(result.final_decision_state, [DecisionState.REVIEW_REQUIRED, DecisionState.INSUFFICIENT_DATA])

    def test_conflicting_signals_scenario_execution(self) -> None:
        """Verify conflicting signals scenario triggers conflict detection and resolves to REVIEW_REQUIRED."""
        sc = create_conflicting_signals_scenario(asset="GBPUSD")
        result = self.runner.run_scenario(sc)

        self.assertTrue(result.success)
        self.assertEqual(result.final_decision_state, DecisionState.REVIEW_REQUIRED)

        # Verify conflict detected in decision report step
        dec_step = result.steps[5]
        self.assertEqual(dec_step.step_name, "Decision")
        self.assertTrue(dec_step.payload["conflict_detected"])
        self.assertEqual(dec_step.payload["conflict_type"], "Research_vs_Strategy")

    def test_demo_report_generation(self) -> None:
        """Verify report generator produces a beautifully formatted trace report."""
        sc = create_trend_continuation_scenario()
        exec_res = self.runner.run_scenario(sc)
        report = self.generator.generate_report(exec_res)

        self.assertIsNotNone(report.report_id)
        self.assertIsInstance(report.timestamp, datetime)
        self.assertIn("RG_V3_AI AUTONOMOUS FINANCIAL INTELLIGENCE PLATFORM DEMO", report.rendered_summary)
        self.assertIn("PIPELINE INTELLIGENCE TRACE TIMELINE", report.rendered_summary)
        self.assertIn("MULTI-AGENT PARTICIPATION & EXPLANATIONS", report.rendered_summary)
        self.assertIn("EVIDENCE VISUAL TRACE PATHWAY", report.rendered_summary)
        self.assertIn("APES-FIN COMPLIANCE AUDIT SUMMARY", report.rendered_summary)

    def test_dashboard_api_integration(self) -> None:
        """Verify demo dashboard API endpoints expose required metrics successfully."""
        dto = ServiceRequestDTO("client_1", "secret_token_1")
        resp = self.orchestrator.handle_request("/v1/dashboard/demo", dto)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("demo", resp.data)

        demo_data = resp.data["demo"]
        self.assertEqual(demo_data["demo_execution_status"], "Completed")
        self.assertIn("last_scenario_duration_ms", demo_data)
        self.assertIn("intelligence_quality_metrics", demo_data)
        self.assertIn("agent_performance_summary", demo_data)

        quality = demo_data["intelligence_quality_metrics"]
        self.assertIn("average_decision_confidence", quality)
        self.assertIn("decision_consistency_score", quality)

    def test_strict_non_trading_compliance(self) -> None:
        """Verify that demo pipeline contains absolutely zero active trading triggers."""
        sc = create_trend_continuation_scenario()
        exec_res = self.runner.run_scenario(sc)

        # Confirm there are no orders, buys, or sells anywhere in the payload
        forbidden_keywords = ["buy_signal", "sell_signal", "place_order", "execute_trade", "open_position", "send_transaction"]

        def check_val(val: Any) -> None:
            if isinstance(val, str):
                lower = val.lower()
                for kw in forbidden_keywords:
                    self.assertNotIn(kw, lower, f"Violation: Forbidden trading keyword '{kw}' found in execution payload.")
            elif isinstance(val, dict):
                for k, v in val.items():
                    check_val(k)
                    check_val(v)
            elif isinstance(val, (list, tuple, set)):
                for item in val:
                    check_val(item)

        for step in exec_res.steps:
            check_val(step.payload)
