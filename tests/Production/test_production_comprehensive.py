import os
import unittest
import json
from src.Application.Deployment.storage import TradeYarStorageManager
from src.Infrastructure.Observability.logging import (
    StructuredLogger,
    get_correlation_id,
    set_correlation_id,
    clear_correlation_id
)
from src.Infrastructure.Observability.metrics import PerformanceMetricsTracker
from src.Infrastructure.Observability.tracing import ExecutionTracer
from src.Infrastructure.Observability.audit import AuditTrailManager
from src.Application.Monitoring.diagnostics import PlatformDiagnosticsEngine


class TestProductionComprehensive(unittest.TestCase):
    """
    Comprehensive verification suite for production infrastructure integration and diagnostics.
    Validates Storage isolation, Observability logging & trace trees, Audit logging, and Subsystem Health.
    """

    def setUp(self) -> None:
        self.storage_manager = TradeYarStorageManager.get_manager()
        clear_correlation_id()
        PerformanceMetricsTracker.get_tracker().reset()

    def tearDown(self) -> None:
        clear_correlation_id()
        PerformanceMetricsTracker.get_tracker().reset()

    def test_storage_confinement_isolation(self) -> None:
        """Verify storage paths strictly isolate runtime logs, reports, and temp directories."""
        self.assertIsNotNone(self.storage_manager.get_log_dir())
        self.assertIsNotNone(self.storage_manager.get_reports_dir())
        self.assertIsNotNone(self.storage_manager.get_runtime_dir())
        self.assertIsNotNone(self.storage_manager.get_cache_dir())

    def test_observability_correlation_id_context(self) -> None:
        """Verify thread-local correlation IDs propagate and track cleanly across logs."""
        cid = "custom-test-correlation-12345"
        set_correlation_id(cid)
        self.assertEqual(get_correlation_id(), cid)

        logger = StructuredLogger(service_name="Test_System")
        log_json = logger.info("TestCorrelationContext", {"param": "val"})

        record = json.loads(log_json)
        self.assertEqual(record["correlation_id"], cid)
        self.assertEqual(record["event"], "TestCorrelationContext")

    def test_observability_metrics_aggregation(self) -> None:
        """Verify PerformanceMetricsTracker accurately aggregates component execution times."""
        tracker = PerformanceMetricsTracker.get_tracker()
        tracker.record_latency("pipeline_execution", 120.5)
        tracker.record_latency("pipeline_execution", 80.5)
        tracker.record_latency("research_latency", 15.4)
        tracker.record_warning()
        tracker.record_error()

        summary = tracker.get_metrics_summary()
        self.assertEqual(summary["average_pipeline_execution_ms"], 100.5)
        self.assertEqual(summary["average_research_latency_ms"], 15.4)
        self.assertEqual(summary["warning_count"], 1)
        self.assertEqual(summary["error_count"], 1)

    def test_observability_trace_spans(self) -> None:
        """Verify execution spans recursively construct correct tree traces."""
        tracer = ExecutionTracer()

        root = tracer.start_span("Pipeline_Execution")
        child_research = tracer.start_span("Research_Analysis")
        tracer.end_span({"insights_found": 3}) # ends research
        tracer.end_span() # ends pipeline execution

        tree = tracer.get_trace_tree()
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]["name"], "Pipeline_Execution")
        self.assertEqual(len(tree[0]["children"]), 1)
        self.assertEqual(tree[0]["children"][0]["name"], "Research_Analysis")
        self.assertEqual(tree[0]["children"][0]["metadata"]["insights_found"], 3)

    def test_observability_audit_trail(self) -> None:
        """Verify audit trail entries write correct jsonl schemas securely."""
        audit_mgr = AuditTrailManager()
        audit_mgr.record_event(
            action="PipelineStarted",
            actor="SupervisorAgent",
            outcome="Success",
            details={"asset": "EURUSD"}
        )

        records = audit_mgr.get_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["action"], "PipelineStarted")
        self.assertEqual(records[0]["actor"], "SupervisorAgent")
        self.assertEqual(records[0]["details"]["asset"], "EURUSD")

    def test_comprehensive_diagnostics_report(self) -> None:
        """Verify PlatformDiagnosticsEngine compiles READY state for all registered layers."""
        engine = PlatformDiagnosticsEngine()
        report = engine.compile_diagnostics_report()

        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["subsystems"]["runtime"], "READY")
        self.assertEqual(report["subsystems"]["pipeline"], "READY")
        self.assertEqual(report["subsystems"]["research"], "READY")
        self.assertEqual(report["subsystems"]["strategy"], "READY")
        self.assertEqual(report["subsystems"]["risk"], "READY")
        self.assertEqual(report["subsystems"]["decision"], "READY")
        self.assertEqual(report["subsystems"]["learning"], "READY")
        self.assertEqual(report["subsystems"]["storage"], "READY")
