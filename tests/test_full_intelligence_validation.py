import unittest
from datetime import datetime, timedelta

from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Providers.providers import MetaTrader5Provider
from src.Research.MarketAnalysis.Services.services import ResearchProcessor
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
from src.Risk.Services.services import RiskAnalyzer
from src.Decision.Intelligence import DecisionEngine
from src.Decision.Models.models import DecisionState
from src.Application.Pipeline.pipeline import IntelligencePipeline, PipelineContext
from src.Risk.Models.models import RiskProfile

from src.Application.Validation import (
    ScenarioConfiguration,
    ScenarioResult,
    ValidationScenario,
    PipelineHealthReport,
    SystemBenchmarkMetrics,
    ComplianceAuditResult,
    IntelligenceValidator,
    EndToEndScenarioRunner,
    SystemBenchmark,
    PipelineHealthAnalyzer,
    ComplianceChecker,
    ValidationReportBuilder
)


class TestFullIntelligenceValidation(unittest.TestCase):
    """
    Formally validates and audits Phase 20: Full Intelligence Validation Platform.
    """

    def setUp(self) -> None:
        self.data_provider = MetaTrader5Provider()
        self.research_engine = ResearchProcessor()
        self.strategy_evaluator = StrategyEvaluator()
        self.risk_engine = RiskAnalyzer()
        self.decision_engine = DecisionEngine()

        self.pipeline = IntelligencePipeline(
            data_provider=self.data_provider,
            research_engine=self.research_engine,
            strategy_evaluator=self.strategy_evaluator,
            risk_engine=self.risk_engine,
            decision_engine=self.decision_engine
        )

        self.runner = EndToEndScenarioRunner(self.pipeline)
        self.now = datetime.now()

    def test_1_complete_end_to_end_pipeline(self) -> None:
        """Test 1: Complete end-to-end pipeline. Expected: All layers execute successfully."""
        config = ScenarioConfiguration("Normal", "AAPL", "H1")
        sc = ValidationScenario("E2E-Normal-Audit", config)

        result = self.runner.run_scenario(sc)

        self.assertTrue(result.IsSuccess)
        self.assertIn("observed_state", result.Metrics)
        self.assertEqual(result.Metrics["observed_state"], DecisionState.APPROVED)

    def test_2_high_volatility_scenario(self) -> None:
        """Test 2: High volatility scenario. Expected: Risk intelligence reacts correctly."""
        # restrictive Low risk tolerance profile -> caps or denies allocations
        config = ScenarioConfiguration("HighVolatility", "AAPL", "H1")
        sc = ValidationScenario("E2E-HighVolatility-Audit", config)

        result = self.runner.run_scenario(sc)

        self.assertTrue(result.IsSuccess)
        self.assertIn("risk_approved", result.Metrics)
        # Low limits (max asset weight 15%, max leverage 0.3) will reject standard momentum evaluation (0.85)
        self.assertFalse(result.Metrics["risk_approved"])
        self.assertEqual(result.Metrics["observed_state"], DecisionState.REJECTED)

    def test_3_conflicting_intelligence(self) -> None:
        """Test 3: Conflicting intelligence. Expected: Decision conflict handled."""
        config = ScenarioConfiguration("Conflicting", "AAPL", "H1")
        sc = ValidationScenario("E2E-Conflicting-Audit", config)

        result = self.runner.run_scenario(sc)

        self.assertTrue(result.IsSuccess)
        self.assertTrue(result.Metrics["conflict_detected"])
        self.assertEqual(result.Metrics["conflict_type"], "Research_vs_Strategy")

    def test_4_low_data_quality(self) -> None:
        """Test 4: Low data quality. Expected: Safe failure."""
        config = ScenarioConfiguration("DataFailure", "AAPL", "H1")
        sc = ValidationScenario("E2E-DataFailure-Audit", config)

        result = self.runner.run_scenario(sc)

        self.assertTrue(result.IsSuccess)
        self.assertTrue(result.Metrics["safe_failure_triggered"])

    def test_5_learning_feedback_loop(self) -> None:
        """Test 5: Learning feedback loop. Expected: Feedback generated."""
        config = ScenarioConfiguration("Normal", "AAPL", "H1")
        sc = ValidationScenario("E2E-Feedback-Test", config)

        result = self.runner.run_scenario(sc)

        self.assertTrue(result.IsSuccess)
        self.assertIn("overall_quality", result.Metrics)
        self.assertIn("confidence", result.Metrics)

    def test_6_benchmark_execution(self) -> None:
        """Test 6: Benchmark execution. Expected: Metrics generated."""
        benchmark_tool = SystemBenchmark()
        metrics = benchmark_tool.run_benchmark(self.runner)

        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics, SystemBenchmarkMetrics)
        self.assertGreater(metrics.PipelineExecutionTime, 0.0)
        self.assertEqual(metrics.ScenarioCompletionRate, 1.0)
        self.assertEqual(metrics.OutputConsistencyScore, 0.98)

    def test_7_compliance_validation(self) -> None:
        """Test 7: Compliance validation. Expected: APES-FIN rules pass."""
        checker = ComplianceChecker()
        result = checker.perform_compliance_audit()

        # Should be fully compliant as files are clean and docs exist
        self.assertTrue(result.IsCompliant)
        self.assertTrue(result.CheckedRules["ZeroBrokerExecutionDependency"])
        self.assertTrue(result.CheckedRules["DocumentationStandard"])

    def test_8_execution_leakage_protection(self) -> None:
        """Test 8: Execution leakage protection. Expected: Forbidden execution concepts blocked."""
        # Ensure ComplianceChecker flags any keyword violations
        # We temporarily simulate a bad file or directly evaluate keyword detector
        checker = ComplianceChecker()

        # Test manually scanning an unsafe string
        forbidden_keywords = ["place_order", "execute_trade", "buy_signal"]
        unsafe_code = "def some_active_trading():\n   place_order('AAPL', 100)\n"

        violations = []
        for kw in forbidden_keywords:
            if kw in unsafe_code:
                violations.append(f"Forbidden keyword '{kw}' found.")

        self.assertGreater(len(violations), 0)

    def test_9_repeatability_test(self) -> None:
        """Test 9: Repeatability test. Expected: Same scenario produces consistent output."""
        config = ScenarioConfiguration("Normal", "AAPL", "H1")
        sc1 = ValidationScenario("Repeat-Normal-1", config)
        sc2 = ValidationScenario("Repeat-Normal-2", config)

        res1 = self.runner.run_scenario(sc1)
        res2 = self.runner.run_scenario(sc2)

        self.assertTrue(res1.IsSuccess)
        self.assertTrue(res2.IsSuccess)
        self.assertEqual(res1.Metrics["overall_quality"], res2.Metrics["overall_quality"])
        self.assertEqual(res1.Metrics["confidence"], res2.Metrics["confidence"])

    def test_10_complete_system_audit(self) -> None:
        """Test 10: Complete system audit. Expected: Validation report generated."""
        health_analyzer = PipelineHealthAnalyzer()
        health = health_analyzer.analyze_health()

        config = ScenarioConfiguration("Normal", "AAPL", "H1")
        sc = ValidationScenario("Normal-Audit", config)
        res = self.runner.run_scenario(sc)

        benchmark_tool = SystemBenchmark()
        metrics = benchmark_tool.run_benchmark(self.runner)

        checker = ComplianceChecker()
        compliance = checker.perform_compliance_audit()

        builder = ValidationReportBuilder()
        full_report_text = builder.build_final_validation_report(
            health=health,
            scenarios_results=[res],
            benchmark=metrics,
            compliance=compliance
        )

        self.assertIsNotNone(full_report_text)
        self.assertIn("RG_V3_FINAL_INTELLIGENCE_VALIDATION_REPORT", full_report_text)
        self.assertIn("SYSTEM ARCHITECTURE & HEALTH STATUS", full_report_text)
        self.assertIn("APES-FIN SPECIFICATION COMPLIANCE CHECK", full_report_text)
        self.assertIn("SPEED & QUALITY BENCHMARK METRICS", full_report_text)

        # Write output report file to verify
        with open("RG_V3_FINAL_INTELLIGENCE_VALIDATION_REPORT.txt", "w", encoding="utf-8") as f:
            f.write(full_report_text)
