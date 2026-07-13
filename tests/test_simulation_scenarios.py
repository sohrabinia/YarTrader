import unittest
from datetime import datetime, timedelta
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Risk.Models.models import RiskProfile
from src.Decision.Models.models import DecisionState

from src.Application.Simulation.models import (
    SimulationEnvironmentGuard,
    MarketScenario,
    ScenarioInput,
    ScenarioResult,
    SimulationReport,
    ExecutionBlockedError
)
from src.Application.Simulation.runner import ScenarioRunner


class TestSimulationScenarios(unittest.TestCase):
    def setUp(self) -> None:
        # Reset guard state before each test
        SimulationEnvironmentGuard.set_simulation_active(True)
        self.runner = ScenarioRunner()

        # Build dummy synthetic price data points
        now = datetime.now()
        self.synthetic_points = [
            MarketDataPoint(
                AssetId="AAPL",
                Timestamp=now - timedelta(days=2),
                Open=150.0,
                High=155.0,
                Low=149.0,
                Close=152.0,
                Volume=10000.0
            ),
            MarketDataPoint(
                AssetId="AAPL",
                Timestamp=now - timedelta(days=1),
                Open=152.0,
                High=158.0,
                Low=151.0,
                Close=157.0,
                Volume=12000.0
            ),
        ]

        self.valid_scenario = MarketScenario(
            Asset="AAPL",
            TimeRange=(now - timedelta(days=2), now),
            PriceData=self.synthetic_points,
            ScenarioType="Trending"
        )

    def test_scenario_execution_basic(self) -> None:
        """Test 1: Verify basic simulation scenario execution completes successfully."""
        profile = RiskProfile("Low", 1.5, 0.90)  # Safe thresholds
        scenario_input = ScenarioInput(
            Scenario=self.valid_scenario,
            TargetRiskProfile=profile,
            LookbackDays=5,
            Metadata={"ActualOutcomeMetric": 0.08}
        )

        result = self.runner.run_scenario(scenario_input)

        # Assert successful pipeline execution and matching inputs
        self.assertIsNotNone(result)
        self.assertTrue(result.ExecutionPrevented)
        self.assertEqual(result.OutcomeMetric, 0.08)
        self.assertEqual(result.PipelineResult.Context.Asset, "AAPL")
        self.assertEqual(result.PipelineResult.Decision.State, DecisionState.APPROVED)

        # Verify generation of report
        report = self.runner.generate_report(result)
        self.assertIsNotNone(report)
        self.assertEqual(report.PipelineStatus, "Success")
        self.assertIn("APPROVED", report.RiskSummary)
        self.assertIn("AAPL", report.ResearchSummary)
        self.assertEqual(report.ExecutionPreventionStatus, "GUARANTEED_SAFE_BY_SIMULATION_ENVIRONMENT_GUARD")

    def test_scenario_execution_high_volatility(self) -> None:
        """Test 2: Verify risk engine responds appropriately under strict risk limits (e.g. high volatility/tight profiles)."""
        # Set extremely restrictive risk limits where single asset weight cannot exceed 0.20
        # This will trigger a risk rejection because the strategy evaluator returns score 0.85 (higher than 0.20)
        profile = RiskProfile("High Volatility Restrictive", 1.0, 0.20)
        scenario_input = ScenarioInput(
            Scenario=self.valid_scenario,
            TargetRiskProfile=profile,
            LookbackDays=5,
            Metadata={"ActualOutcomeMetric": -0.15}
        )

        result = self.runner.run_scenario(scenario_input)

        # Verify risk analyzer successfully rejected the allocation
        self.assertIsNotNone(result)
        self.assertFalse(result.PipelineResult.Risk.IsApproved)
        self.assertEqual(result.PipelineResult.Decision.State, DecisionState.NO_ACTION)

        # Verify report includes the rejection detail
        report = self.runner.generate_report(result)
        self.assertEqual(report.PipelineStatus, "Success")
        self.assertIn("REJECTED", report.RiskSummary)
        self.assertIn("No asset allocation recommended", report.DecisionSummary)

    def test_scenario_simulation_safety(self) -> None:
        """Test 3: Verify SimulationEnvironmentGuard successfully blocks live execution attempts."""
        # Active order / live trading attempt must trigger SimulationEnvironmentGuard
        profile = RiskProfile("Low", 1.5, 0.90)
        scenario_input = ScenarioInput(
            Scenario=self.valid_scenario,
            TargetRiskProfile=profile
        )

        # Disable simulation mode to mimic an active trading state attempt
        SimulationEnvironmentGuard.set_simulation_active(False)

        # Running a scenario must be blocked immediately
        with self.assertRaises(ExecutionBlockedError) as context:
            self.runner.run_scenario(scenario_input)
        self.assertIn("Live broker connection, real-money execution, or active order creation are strictly prohibited", str(context.exception))

        # Explicitly blocking an action also triggers the guard
        with self.assertRaises(ExecutionBlockedError) as context_action:
            SimulationEnvironmentGuard.block_active_execution("MT5 Broker Submit Order")
        self.assertIn("Attempted active execution 'MT5 Broker Submit Order'", str(context_action.exception))

    def test_scenario_invalid(self) -> None:
        """Test 4: Verify providing an invalid scenario results in safe, graceful failure with meaningful errors."""
        invalid_scenario = MarketScenario(
            Asset="",  # Missing symbol
            TimeRange=(datetime.now(), datetime.now()),
            PriceData=[]  # Empty data
        )

        profile = RiskProfile("Low", 1.5, 0.90)
        scenario_input = ScenarioInput(
            Scenario=invalid_scenario,
            TargetRiskProfile=profile
        )

        # Must raise a ValueError with descriptive explanation
        with self.assertRaises(ValueError) as context:
            self.runner.run_scenario(scenario_input)
        self.assertIn("Asset and PriceData must not be empty", str(context.exception))
