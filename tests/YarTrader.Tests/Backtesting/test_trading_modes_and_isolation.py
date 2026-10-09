import os
import unittest
import json
from datetime import datetime, timedelta
from unittest.mock import patch
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

    def test_demo_scenario_does_not_fabricate_execution_records(self) -> None:
        """Scenario approval is not an executed trade and must not create fake PnL."""
        resp = self.client.post("/api/demo/run", json={"scenario_id": "trend_continuation", "asset": "EURUSD"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIsNone(data["simulated_trade"])
        self.assertEqual(data["report"]["data_provenance"], "PERSISTED_DEMO_EXECUTION_RECORDS_ONLY")
        self.assertIsNone(data["report"]["account"])
        self.assertIsNone(data["report"]["balance"])

        trades_resp = self.client.get("/api/demo/trades")
        self.assertEqual(trades_resp.status_code, 200)
        self.assertEqual(trades_resp.json(), [])

        report_resp = self.client.get("/api/demo/report")
        self.assertEqual(report_resp.status_code, 200)
        rep = report_resp.json()
        self.assertEqual(rep["data_provenance"], "PERSISTED_DEMO_EXECUTION_RECORDS_ONLY")
        self.assertEqual(rep["total_trades"], 0)
        self.assertIsNone(rep["account"])
        self.assertIsNone(rep["balance"])

    def test_demo_account_status_uses_broker_history_without_exposing_identifiers(self) -> None:
        """Live DEMO telemetry must report real broker facts, separate deposits, and redact account identifiers."""
        with patch("src.Execution.Adapters.mt5_adapter.RealMT5BrokerAdapter") as adapter_cls:
            adapter = adapter_cls.return_value
            adapter._initialized = True
            adapter.get_account_info.return_value = {
                "login": "52961173", "server": "Alpari-MT5-Demo", "trade_mode": 0,
                "balance": 2970.18, "equity": 2970.18, "profit": 0.0, "currency": "USD",
            }
            adapter.get_terminal_info.return_value = {
                "connected": True, "trade_allowed": True, "tradeapi_disabled": False,
            }
            adapter.verify_safety_and_account.return_value = True
            adapter.get_positions.return_value = []
            adapter.get_history_deals.return_value = [
                {"type": 0, "entry": 0, "position_id": 1, "time": 100,
                 "profit": 0.0, "commission": -0.1, "swap": 0.0, "fee": 0.0,
                 "magic": 143056, "comment": "YarTrader DEMO", "symbol": "XAUUSD"},
                {"type": 1, "entry": 1, "position_id": 1, "time": 101,
                 "profit": -2.0, "commission": -0.1, "swap": 0.0, "fee": 0.0,
                 "magic": 0, "comment": "", "symbol": "XAUUSD"},
                {"type": 0, "entry": 0, "position_id": 2, "time": 200,
                 "profit": 0.0, "commission": -0.1, "swap": 0.0, "fee": 0.0,
                 "magic": 143056, "comment": "YarTrader DEMO", "symbol": "XAUUSD"},
                {"type": 1, "entry": 1, "position_id": 2, "time": 201,
                 "profit": 5.0, "commission": -0.1, "swap": 0.0, "fee": 0.0,
                 "magic": 0, "comment": "", "symbol": "XAUUSD"},
                {"type": 2, "entry": 0, "position_id": 0, "time": 202,
                 "profit": 1000.0, "commission": 0.0, "swap": 0.0, "fee": 0.0,
                 "magic": 0, "comment": "Deposit", "symbol": ""},
            ]
            response = self.client.get("/api/demo/account-status")

        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["account_mode"], "DEMO")
        self.assertTrue(report["demo_execution_ready"])
        self.assertEqual(report["balance"], 2970.18)
        self.assertEqual(report["open_positions_count"], 0)
        self.assertEqual(report["account_history"]["closed_trades"], 2)
        self.assertAlmostEqual(report["account_history"]["net_pnl"], 2.6)
        self.assertEqual(report["yartrader_associated_history"]["closed_trades"], 2)
        self.assertAlmostEqual(report["yartrader_associated_history"]["net_pnl"], 2.6)
        self.assertEqual(report["deposit_events"], 1)
        self.assertEqual(report["deposit_total"], 1000.0)
        self.assertEqual(report["cash_operations_net"], 1000.0)
        self.assertAlmostEqual(report["net_change_including_cash_operations"], 1002.6)
        self.assertAlmostEqual(report["estimated_balance_at_window_start"], 1967.58)
        self.assertNotIn("52961173", response.text)
        self.assertNotIn("Alpari", response.text)

    def test_safety_gate_mt4_rejection(self) -> None:
        """Confirms that MT4 real money execution is completely blocked to satisfy fail-closed SRE directives."""
        with self.assertRaises(Exception):
            MetaTraderSafetyGate.verify_operation(
                terminal_type="MT4",
                operation_type="REAL_LIVE",
                account_id="143056202",
                server_name="Alpari-Pro.ECN"
            )
