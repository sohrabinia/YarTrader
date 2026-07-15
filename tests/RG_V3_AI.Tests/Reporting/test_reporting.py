import os
import unittest
import json
from src.Infrastructure.exceptions import ValidationException
from src.Application.Deployment.storage import TradeYarStorageManager
from src.Application.Reporting.engine import ReportEngine


class TestReportingIntelligenceSystem(unittest.TestCase):
    """
    Unit and integration tests for the Reporting Intelligence System (Phase 8).
    Verifies creation, structure, validation boundaries, and formats (JSON, MD, HTML).
    """

    def setUp(self) -> None:
        self.engine = ReportEngine()
        self.storage_manager = TradeYarStorageManager.get_manager()

    def test_research_report_generation(self) -> None:
        """Verify compiling a research report structure."""
        data = {
            "asset": "EURUSD",
            "timeframe": "M15",
            "findings": ["Trend Continuation bullish signal detected."],
            "confidence": 0.95,
            "metadata": {"volatility": "low"}
        }
        rep = self.engine.generate_research_report(data)
        self.assertEqual(rep["report_type"], "Research Report")
        self.assertEqual(rep["asset"], "EURUSD")
        self.assertEqual(rep["confidence"], 0.95)
        self.assertIn("findings", rep)

    def test_research_report_validation_failure(self) -> None:
        """Verify research report raises exception without asset key."""
        with self.assertRaises(ValidationException):
            self.engine.generate_research_report({})

    def test_risk_report_generation(self) -> None:
        """Verify compiling a risk report structure."""
        data = {
            "is_approved": True,
            "risk_profile": "Conservative",
            "portfolio_metrics": {"expected_volatility": 0.05}
        }
        rep = self.engine.generate_risk_report(data)
        self.assertEqual(rep["report_type"], "Risk Report")
        self.assertTrue(rep["is_approved"])
        self.assertEqual(rep["risk_profile"], "Conservative")

    def test_decision_explanation_report_generation(self) -> None:
        """Verify compiling a decision explanation report structure."""
        data = {
            "final_decision_state": "Approved",
            "overall_confidence": 0.92,
            "explanations": ["Approved: Safe momentum with low volatility."],
            "trace_map": {"path": ["Research", "Strategy", "Risk", "Decision"]}
        }
        rep = self.engine.generate_decision_explanation_report(data)
        self.assertEqual(rep["report_type"], "Decision Explanation Report")
        self.assertEqual(rep["final_decision_state"], "Approved")
        self.assertEqual(rep["overall_confidence"], 0.92)

    def test_simulation_report_generation(self) -> None:
        """Verify compiling a simulation report structure."""
        data = {
            "scenario_name": "Trend Reversal Stress Test",
            "total_intervals": 144,
            "performance_metrics": {"decision_consistency": 0.98},
            "compliance_passed": True
        }
        rep = self.engine.generate_simulation_report(data)
        self.assertEqual(rep["report_type"], "Simulation Report")
        self.assertEqual(rep["scenario_name"], "Trend Reversal Stress Test")
        self.assertEqual(rep["compliance_status"], "PASSED")

    def test_system_health_report_generation(self) -> None:
        """Verify compiling a system health report structure and status validation."""
        # 1. Ready state
        data = {
            "status": "READY",
            "uptime_seconds": 12000.0,
            "subsystems": {"database": "OK"}
        }
        rep = self.engine.generate_system_health_report(data)
        self.assertEqual(rep["report_type"], "System Health Report")
        self.assertEqual(rep["status"], "READY")

        # 2. Invalid state defaults to READY
        data["status"] = "INVALID_STATE"
        rep2 = self.engine.generate_system_health_report(data)
        self.assertEqual(rep2["status"], "READY")

    def test_report_export_json(self) -> None:
        """Verify exporting a report to JSON format file."""
        data = {"asset": "GBPUSD", "findings": ["Trend Reversal bearish."]}
        rep = self.engine.generate_research_report(data)
        filepath = self.engine.export_report(rep, fmt="json")

        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            self.assertEqual(loaded["report_id"], rep["report_id"])
            self.assertEqual(loaded["asset"], "GBPUSD")

    def test_report_export_markdown(self) -> None:
        """Verify exporting a report to Markdown format file."""
        data = {"asset": "USDJPY", "findings": ["Low liquidity warning."]}
        rep = self.engine.generate_research_report(data)
        filepath = self.engine.export_report(rep, fmt="markdown")

        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("# Research Report", content)
            self.assertIn("**Asset:** USDJPY", content)

    def test_report_export_html(self) -> None:
        """Verify exporting a report to HTML format file."""
        data = {"asset": "AUDUSD", "findings": ["Normal conditions."]}
        rep = self.engine.generate_research_report(data)
        filepath = self.engine.export_report(rep, fmt="html")

        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("<h1>Research Report</h1>", content)

    def test_report_export_invalid_format(self) -> None:
        """Verify invalid format choice raises ValidationException."""
        rep = {"report_type": "Dummy", "report_id": "1"}
        with self.assertRaises(ValidationException):
            self.engine.export_report(rep, fmt="pdf")
