import os
import unittest
from datetime import datetime, timedelta

from src.Data.MarketData.Models.models import MarketDataPoint
from src.Decision.Intelligence.models import DecisionIntelligenceReport, ConflictResolutionResult, DecisionEvidenceTrail, DecisionQualityScore
from src.Strategy.Models.models import StrategyCandidate, StrategyScore, StrategyEvaluation, StrategyDefinition
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
from src.Strategy.Registry.registry import StrategyRegistry
from src.Risk.Models.models import RiskProfile, RiskAssessment
from src.Execution.Models.models import OrderRequest

# Newly added modules
from src.Application.Backtesting.backtest_engine import (
    BacktestEngine,
    HistoricalDataProvider,
    PerformanceAnalyzer
)
from src.Strategy.strategy_intelligence import StrategyEngine, StrategyLifecycleManager
from src.Risk.Analysis.risk_management import RiskEngine, RiskPolicy
from src.Application.Shadow.paper_execution import PaperExecutionEngine, VirtualPortfolio, VirtualOrder, TradeJournal
from src.Execution.Adapters.live_trading import LiveTradingFoundation, ExecutionGuard, ExecutionBlockedError
from src.Learning.Optimization.learning_intelligence import LearningEngine, PerformanceMemory
from src.Runtime.autonomous_orchestrator import AutonomousOrchestrator


class TestVersion1CompleteIntelligence(unittest.TestCase):
    """
    Comprehensive test suite validating Phases 41 - 50 Autonomous Trading Intelligence completion.
    """

    def setUp(self) -> None:
        ExecutionGuard.set_live_trading_enabled(False) # DEFAULT MODE = DISABLED

    def tearDown(self) -> None:
        ExecutionGuard.set_live_trading_enabled(False)

    def test_backtesting_historical_provider_and_analyzer(self) -> None:
        """Verify historical providers store rates and PerformanceAnalyzer computes complete standard metrics."""
        provider = HistoricalDataProvider()

        pts = [
            MarketDataPoint("XAUUSD", datetime.now() - timedelta(hours=1), 2000.0, 2005.0, 1995.0, 2002.0, 1000.0)
        ]
        provider.load_dataset("XAUUSD", pts)

        req = MarketDataRequest("XAUUSD", datetime.now() - timedelta(hours=2), datetime.now(), "H1")
        response = provider.retrieve_market_data(req)
        self.assertEqual(len(response.DataPoints), 1)

        # Performance Analyzer Metrics
        dummy_reports = [
            DecisionIntelligenceReport(
                ReportId="r1", State="Approved", Confidence=0.85,
                QualityScore=DecisionQualityScore(0.90, 0.90, 0.90, 0.90), ConflictAnalysis=ConflictResolutionResult(False, "None", []),
                EvidenceTrail=DecisionEvidenceTrail("r1", [], datetime.now()), Context=None, IntelligenceSummary="Approved",
                GeneratedAt=datetime.now()
            ),
            DecisionIntelligenceReport(
                ReportId="r2", State="Rejected", Confidence=0.15,
                QualityScore=DecisionQualityScore(0.90, 0.90, 0.90, 0.90), ConflictAnalysis=ConflictResolutionResult(False, "None", []),
                EvidenceTrail=DecisionEvidenceTrail("r2", [], datetime.now()), Context=None, IntelligenceSummary="Rejected",
                GeneratedAt=datetime.now()
            )
        ]
        metrics = PerformanceAnalyzer.calculate_metrics(dummy_reports)
        self.assertGreater(metrics["total_return"], 0.0)
        self.assertEqual(metrics["win_rate"], 1.0)
        self.assertEqual(metrics["total_trades"], 2)

    def test_strategy_lifecycle_and_engine(self) -> None:
        """Verify strategy lifecycle manager transitions candidates to active pools and registers concepts."""
        registry = StrategyRegistry()
        manager = StrategyLifecycleManager(registry)

        definition = StrategyDefinition("concept-1", "Technical Trend", "Momentum", datetime.now(), "1.0.0", "Approved")
        registry.register_strategy(definition)

        manager.activate_strategy("concept-1")
        self.assertIn("concept-1", manager.get_active_strategy_ids())

        # Strategy Engine confirmation
        evaluator = StrategyEvaluator()
        engine = StrategyEngine(evaluator, manager)

        candidate = StrategyCandidate(
            Id="concept-1", Name="Technical Trend", Description="", ResearchContext={},
            CreatedAt=datetime.now(), EvaluationStatus="Pending"
        )
        eval_res = engine.process_candidate(candidate)
        self.assertIn("Active Strategy Processed", eval_res.EvaluationNotes)

    def test_risk_policies_and_sizing_limits(self) -> None:
        """Verify risk policy limits prevent high concentrations and sizer allocates precise positions."""
        profile = RiskProfile("Low", 1.0, 0.40) # max weight 40%
        policy = RiskPolicy(profile)
        engine = RiskEngine(policy)

        # 1. Compliant allocation
        weights_ok = {"XAUUSD": 0.35}
        self.assertTrue(policy.validate_allocation(weights_ok))

        assess_ok = engine.assess_allocation(weights_ok)
        self.assertTrue(assess_ok.IsApproved)
        self.assertEqual(assess_ok.PortfolioRiskMetrics.ExpectedVolatility, 0.08)

        # 2. Violating allocation
        weights_bad = {"XAUUSD": 0.55}
        self.assertFalse(policy.validate_allocation(weights_bad))

        assess_bad = engine.assess_allocation(weights_bad)
        self.assertFalse(assess_bad.IsApproved)

        # Position Sizing
        sizes = engine.calculate_position_sizing(weights_ok, portfolio_value=50000.0)
        self.assertEqual(sizes["XAUUSD"], 17500.0)

    def test_paper_trading_virtual_journal_and_p_n_l(self) -> None:
        """Verify VirtualPortfolio records BUY/SELL orders and TradeJournal captures complete trade trees."""
        portfolio = VirtualPortfolio(initial_balance=100000.0)
        journal = TradeJournal()
        engine = PaperExecutionEngine(portfolio, journal)

        # Buy 10 units of gold at 2000
        engine.process_decision_allocation("XAUUSD", target_weight=0.20, current_price=2000.0) # 20000 allocation -> 10 volume
        self.assertEqual(portfolio.holdings["XAUUSD"], 10.0)
        self.assertEqual(portfolio.balance, 80000.0)

        # Portfolio sell to 10% weight -> sell 5 units at 2100 (simulating profit)
        engine.process_decision_allocation("XAUUSD", target_weight=0.10, current_price=2100.0) # 10000 allocation -> 4.76 volume, so sell 5.23 volume
        self.assertLess(portfolio.holdings["XAUUSD"], 10.0)
        self.assertEqual(len(journal.get_journal()), 2)

    def test_disabled_by_default_trading_guards(self) -> None:
        """Verify that live execution adapter blocks execution immediately under DEFAULT DISABLED state."""
        self.assertFalse(ExecutionGuard.is_live_trading_enabled())

        # Verify ExecutionGuard raises ExecutionBlockedError
        with self.assertRaises(ExecutionBlockedError) as context:
            ExecutionGuard.verify_safety()
        self.assertIn("Live broker execution, real-money trading, or active order creation are strictly prohibited", str(context.exception))

        # Verify LiveTradingFoundation adapter blocks execution
        live_adapter = LiveTradingFoundation()
        req = OrderRequest("XAUUSD", "Buy", 1.0, 0.10)

        with self.assertRaises(ExecutionBlockedError) as context_live:
            live_adapter.execute_live_order(req)
        self.assertIn("Live Trading Security Block", str(context_live.exception))

    def test_learning_loop_performance_optimization(self) -> None:
        """Verify PerformanceMemory logs historical decisions and LearningEngine proposes optimization suggestions."""
        memory = PerformanceMemory()
        engine = LearningEngine(memory)

        # Initially empty
        self.assertEqual(engine.generate_feedback_report()["analyzed_count"], 0)

        # Record Approved Decisions
        dummy_report = DecisionIntelligenceReport(
            ReportId="r1", State="Approved", Confidence=0.85,
            QualityScore=DecisionQualityScore(0.90, 0.90, 0.90, 0.90), ConflictAnalysis=ConflictResolutionResult(False, "None", []),
            EvidenceTrail=DecisionEvidenceTrail("r1", [], datetime.now()), Context=None, IntelligenceSummary="Approved",
            GeneratedAt=datetime.now()
        )
        memory.record_decision(dummy_report)

        report = engine.generate_feedback_report()
        self.assertEqual(report["analyzed_count"], 1)
        self.assertEqual(report["overall_success_ratio"], 1.0)
        self.assertEqual(report["suggested_optimization_multiplier"], 1.10) # positive multiplier suggestion

    def test_autonomous_orchestrator_complete_flow_pass(self) -> None:
        """Verify the high-level orchestrator executes the complete 8-stage flow successfully."""
        orchestrator = AutonomousOrchestrator()
        result = orchestrator.execute_complete_flow("XAUUSD", "H1")

        self.assertIsNotNone(result["timestamp"])
        self.assertEqual(result["symbol"], "XAUUSD")
        self.assertEqual(result["timeframe"], "H1")
        self.assertGreater(result["research_confidence"], 0.0)
        self.assertTrue(result["risk_approved"])
        self.assertIn("XAUUSD", result["position_sizing"])
        self.assertGreater(result["virtual_balance"], 0.0)


# Import helper
from src.Data.MarketData.Models.models import MarketDataRequest
