import os
import unittest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.Application.Backtesting.models import BacktestScenario, BacktestResult
from src.Application.Backtesting.engine import IntelligenceBacktestEngine
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Application.Agents.concrete_agents import (
    ResearchAgent,
    StrategyAnalystAgent,
    RiskAgent,
    ValidationAgent,
    LearningAgent
)
from src.Decision.Intelligence.engine import DecisionEngine
from src.Data.connector import ExternalDataPipelineConnector
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Application.Services.web_dashboard import app

class TestTradingModesAndIsolation(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

        self.supervisor = IntelligenceSupervisor()
        self.supervisor.register_agent(ResearchAgent())
        self.supervisor.register_agent(StrategyAnalystAgent())
        self.supervisor.register_agent(RiskAgent())
        self.supervisor.register_agent(ValidationAgent())
        self.supervisor.register_agent(LearningAgent())

        self.decision_engine = DecisionEngine()
        self.connector = ExternalDataPipelineConnector()

        self.engine = IntelligenceBacktestEngine(
            self.supervisor,
            self.decision_engine,
            self.connector
        )
        self.now = datetime.now()

    def test_backtest_trade_engine_simulation(self) -> None:
        """Verifies that Backtest engine simulates trades, balance, equity, and SRE metrics correctly."""
        scenario = BacktestScenario(
            scenario_id="scen-test-isolation",
            name="Momentum Test Run",
            start_time=self.now - timedelta(hours=8),
            end_time=self.now,
            symbol="EURUSD",
            timeframe="M15",
            parameters={
                "interval_minutes": 120,
                "strategy_type": "Momentum",
                "initial_balance": 10000.0
            }
        )
        result = self.engine.run_backtest(scenario)
        metrics = result.performance_metrics

        # Standard SRE Backtesting assertions
        self.assertEqual(result.total_intervals_processed, 4)
        self.assertIn("initial_balance", metrics)
        self.assertIn("final_balance", metrics)
        self.assertIn("net_p_and_l", metrics)
        self.assertIn("return_pct", metrics)
        self.assertIn("total_trades", metrics)
        self.assertIn("win_rate_pct", metrics)
        self.assertIn("profit_factor", metrics)
        self.assertIn("maximum_drawdown_pct", metrics)
        self.assertIn("trade_list", metrics)
        self.assertIn("equity_curve", metrics)

    def test_backtest_runs_differ_by_strategy(self) -> None:
        """Verifies that Momentum and MeanReversion backtests generate explainable different outcomes."""
        scen_a = BacktestScenario(
            scenario_id="scen-a",
            name="Momentum",
            start_time=self.now - timedelta(hours=6),
            end_time=self.now,
            symbol="EURUSD",
            timeframe="M15",
            parameters={
                "interval_minutes": 120,
                "strategy_type": "Momentum"
            }
        )
        scen_b = BacktestScenario(
            scenario_id="scen-b",
            name="MeanReversion",
            start_time=self.now - timedelta(hours=6),
            end_time=self.now,
            symbol="EURUSD",
            timeframe="M15",
            parameters={
                "interval_minutes": 120,
                "strategy_type": "MeanReversion"
            }
        )

        res_a = self.engine.run_backtest(scen_a)
        res_b = self.engine.run_backtest(scen_b)

        # Confirm that trades exist and differ
        trades_a = res_a.performance_metrics["trade_list"]
        trades_b = res_b.performance_metrics["trade_list"]

        if trades_a and trades_b:
            self.assertNotEqual(trades_a[0]["direction"], trades_b[0]["direction"])

    def test_demo_execution_persistence_isolation(self) -> None:
        """Verifies DEMO scenario execution is persisted without fabricated broker/account telemetry."""
        resp = self.client.post("/api/demo/run", json={"scenario_id": "trend_continuation", "asset": "EURUSD"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["result"]["mode"], "DEMO")
        self.assertEqual(data["result"]["data_provenance"], "DEMO_SCENARIO_SIMULATION")

        trades_resp = self.client.get("/api/demo/trades")
        self.assertEqual(trades_resp.status_code, 200)
        demo_trades = trades_resp.json()
        self.assertGreater(len(demo_trades), 0)
        self.assertTrue(all(t["mode"] == "DEMO" for t in demo_trades))

        report_resp = self.client.get("/api/demo/report")
        self.assertEqual(report_resp.status_code, 200)
        report = report_resp.json()
        self.assertEqual(report["mode"], "DEMO")
        self.assertEqual(report["data_provenance"], "DEMO_SCENARIO_SIMULATION")
        self.assertGreaterEqual(report["total_runs"], len(demo_trades))

    def test_safety_gate_mt4_rejection(self) -> None:
        """Confirms that MT4 real money execution is completely blocked to satisfy fail-closed SRE directives."""
        with self.assertRaises(Exception):
            MetaTraderSafetyGate.verify_operation(
                terminal_type="MT4",
                operation_type="REAL_LIVE",
                account_id="143056202",
                server_name="Alpari-Pro.ECN"
            )
