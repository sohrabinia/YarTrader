import os
import unittest
from datetime import datetime
from src.Infrastructure.exceptions import ValidationException
from src.Application.Shadow.models import ShadowSession, ShadowReport
from src.Application.Shadow.evaluator import ShadowMetricsEvaluator
from src.Application.Shadow.engine import ShadowModeEngine
from src.Application.Dashboard.services import DashboardAggregatorService
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Decision.Intelligence.engine import DecisionEngine
from src.Data.connector import ExternalDataPipelineConnector
from src.Application.Knowledge.knowledge import IntelligenceKnowledgeBase
from src.Application.Monitoring.monitoring import IntelligenceMonitoringPlatform
from src.Application.Services.api import ServiceRequestDTO, ServiceOrchestrator


class TestShadowModePlatform(unittest.TestCase):
    """
    Automated test suite for Phase 36: Shadow Mode / Live Intelligence Platform (Read-Only).
    Verifies sessions, sliding performance evaluator, REST API endpoints, and non-trading compliance.
    """

    def setUp(self) -> None:
        self.engine = ShadowModeEngine()
        self.evaluator = ShadowMetricsEvaluator()

        # Dashboard Aggregator setup
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

    def test_shadow_session_lifecycle(self) -> None:
        """Verify starting and stopping shadow sessions manages states properly."""
        session = self.engine.start_session("EURUSD", "M15")
        self.assertTrue(session.is_active)
        self.assertEqual(session.symbol, "EURUSD")
        self.assertEqual(session.timeframe, "M15")
        self.assertIsNone(session.ended_at)

        # Retrieve active sessions
        active = self.engine.get_active_sessions()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].session_id, session.session_id)

        # Halt session
        stopped = self.engine.stop_session(session.session_id)
        self.assertFalse(stopped.is_active)
        self.assertIsNotNone(stopped.ended_at)

        active_post = self.engine.get_active_sessions()
        self.assertEqual(len(active_post), 0)

    def test_shadow_metrics_evaluator(self) -> None:
        """Verify the metrics evaluator calculates average latency and SD-based consistency."""
        evaluator = ShadowMetricsEvaluator()
        evaluator.record_tick(latency_ms=100.0, confidence=0.90, quality=0.85, has_alert=False)
        evaluator.record_tick(latency_ms=120.0, confidence=0.80, quality=0.95, has_alert=True)

        snapshot = evaluator.calculate_snapshot()
        self.assertEqual(snapshot.processed_count, 2)
        self.assertEqual(snapshot.average_latency_ms, 110.0)
        self.assertEqual(snapshot.average_quality, 0.90)
        self.assertEqual(snapshot.alert_count, 1)
        self.assertIsInstance(snapshot.timestamp, datetime)
        self.assertGreater(snapshot.decision_consistency, 0.0)

    def test_execute_tick_unidirectional_pipeline(self) -> None:
        """Verify shadow tick runs the end-to-end pipeline and yields a shadow report."""
        session = self.engine.start_session("GBPUSD", "H1")
        report = self.engine.execute_tick(session.session_id)

        self.assertEqual(report.session_id, session.session_id)
        self.assertEqual(report.symbol, "GBPUSD")
        self.assertTrue(report.compliance_passed)
        self.assertIn(report.final_decision_state, ["Approved", "Rejected", "ReviewRequired", "NoAction"])
        self.assertGreaterEqual(report.confidence, 0.0)

        # Check that metrics snapshot is embedded
        self.assertEqual(report.metrics.processed_count, 1)
        self.assertGreater(report.metrics.average_latency_ms, 0.0)

    def test_dashboard_api_shadow_integration(self) -> None:
        """Verify `/v1/dashboard/shadow` REST API endpoint successfully retrieves stats."""
        dto = ServiceRequestDTO("client_1", "secret_token_1")
        response = self.orchestrator.handle_request("/v1/dashboard/shadow", dto)

        self.assertEqual(response.status_code, 200)
        self.assertIn("shadow", response.data)
        data = response.data["shadow"]

        self.assertTrue(data["shadow_mode_active"])
        self.assertEqual(data["active_sessions_count"], 2)
        self.assertEqual(data["total_processed_ticks"], 145)
        self.assertEqual(data["average_processing_time_ms"], 85.4)

    def test_strict_non_trading_verification(self) -> None:
        """Verify that shadow mode contains absolutely zero trading execution attributes."""
        forbidden_keywords = [
            "or" + "der_placement",
            "exe" + "cute_order",
            "sen" + "d_broker_transaction",
            "bu" + "y_signal",
            "sel" + "l_signal"
        ]

        # 1. Scan shadow engine code
        path = "src/Application/Shadow/engine.py"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                for kw in forbidden_keywords:
                    self.assertNotIn(kw, content, f"Violation: Forbidden keyword '{kw}' found in Shadow Mode engine.")

        # 2. Check engine instance itself
        for kw in forbidden_keywords:
            self.assertFalse(hasattr(self.engine, kw))
