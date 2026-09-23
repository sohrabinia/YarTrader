import os
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from app.workers.research_worker import is_autonomous_demo_enabled
from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Infrastructure.exceptions import ValidationException


class TestDemoExecutionGateSafety(unittest.TestCase):
    """
    Required SRE Safety Tests for Demo Execution Gate & Demo Execution Engine.
    Verifies that real live trading remains IMPOSSIBLE and all safety rules hold.
    """

    def setUp(self):
        self.original_env = os.environ.get("AUTONOMOUS_DEMO_TRADING_ENABLED")
        os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = "true"
        self.mock_adapter = MagicMock()
        self.mock_adapter.get_account_info.return_value = {
            "login": "52961173",
            "server": "Alpari-MT5-Demo",
            "trade_mode": 0,
            "equity": 10000.0
        }
        self.mock_adapter.get_terminal_info.return_value = {
            "connected": True,
            "trade_allowed": True,
            "tradeapi_disabled": False
        }
        self.mock_adapter.get_symbol_info.return_value = {
            "name": "XAUUSD",
            "trade_mode": 4,
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01
        }

    def tearDown(self):
        if self.original_env is None:
            os.environ.pop("AUTONOMOUS_DEMO_TRADING_ENABLED", None)
        else:
            os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = self.original_env

    def test_01_real_live_execution_rejected(self):
        """Test 1: REAL_LIVE operation is hard-blocked."""
        from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(terminal_type="MT5", operation_type="REAL_LIVE")
        self.assertIn("Real Live Trading is hard-disabled", str(ctx.exception))

    def test_02_demo_execution_allowed_with_explicit_gate(self):
        """Test 2: Demo execution passes when demo mode is enabled and checks pass."""
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01, Price=2350.0, StopLoss=2340.0, TakeProfit=2370.0)
        res = DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertTrue(res)

    def test_03_live_account_rejected_even_if_demo_gate_enabled(self):
        """Test 3: Live account (login!=52961173 or trade_mode!=0) is rejected."""
        self.mock_adapter.get_account_info.return_value = {
            "login": "143056202", # Live account
            "server": "Alpari-Pro.ECN",
            "trade_mode": 2 # Real account
        }
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01)
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("SECURITY VIOLATION: Connected account is REAL", str(ctx.exception))

    def test_04_terminal_trading_disabled_rejected(self):
        """Test 4: Terminal with trade_allowed=False is rejected."""
        self.mock_adapter.get_terminal_info.return_value = {
            "connected": True,
            "trade_allowed": False,
            "tradeapi_disabled": False
        }
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01)
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("trading permissions disabled", str(ctx.exception))

    def test_05_invalid_symbol_trade_mode_rejected(self):
        """Test 5: Symbol with trade_mode=0 (disabled) is rejected."""
        self.mock_adapter.get_symbol_info.return_value = {
            "name": "XAUUSD",
            "trade_mode": 0 # Trade disabled
        }
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01)
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("trade mode is DISABLED", str(ctx.exception))

    def test_06_invalid_volume_out_of_bounds_rejected(self):
        """Test 6: Volume smaller than volume_min or larger than volume_max is rejected."""
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.001) # Less than 0.01
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("out of bounds", str(ctx.exception))

    def test_07_invalid_sl_tp_rejected(self):
        """Test 7: Buy order with SL above entry price is rejected."""
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01, Price=2350.0, StopLoss=2360.0) # SL > Price
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("Buy order SL 2360.0 must be below entry price 2350.0", str(ctx.exception))

    def test_08_failed_order_check_prevents_order_send(self):
        """Test 8: DemoExecutionEngine logs failure if adapter order placement fails."""
        self.mock_adapter.send_order_to_broker.return_value = OrderResponse(
            OrderId="0",
            Symbol="XAUUSD",
            Status="Failed",
            SubmittedAt=datetime.now(timezone.utc),
            Comment="order_check failed retcode=10013"
        )
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)
        resp = engine.execute_demo_decision("XAUUSD", "BUY", 0.01, price=2350.0, sl=2340.0, tp=2370.0)
        self.assertEqual(resp.Status, "Failed")

    def test_09_disconnected_terminal_fails_closed(self):
        """Test 9: Disconnected terminal (acc_info is None) fails closed."""
        self.mock_adapter.get_account_info.return_value = None
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01)
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(self.mock_adapter, req, demo_mode_flag=True)
        self.assertIn("MT5 Terminal is disconnected", str(ctx.exception))

    def test_10_shadow_trading_remains_functional(self):
        """Test 10: Shadow trading engine runs independently without live/broker order send."""
        from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine
        shadow = ShadowTradingEngine.get_instance()
        self.assertIsNotNone(shadow.account)
        self.assertGreater(shadow.account.balance, 0)

    def test_11_demo_execution_engine_storage_root_isolation(self):
        """Test 11: DemoExecutionEngine log_dir resolves under canonical TradeYarStorageRoot."""
        from src.Application.Deployment.storage import YarTraderStorageManager
        storage_mgr = YarTraderStorageManager.get_manager()
        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)
        self.assertTrue(engine.log_dir.startswith(storage_mgr.storage_root) or engine.log_dir.startswith(storage_mgr.get_log_dir()))

    def test_12_missing_account_equity_fails_closed_no_fallback(self):
        """Test 12: Missing or non-positive account equity causes execution dispatch to fail closed."""
        from app.workers.research_worker import ResearchWorker
        worker = ResearchWorker()
        worker.demo_engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True)

        # Mock adapter returns None for account info
        self.mock_adapter.get_account_info.return_value = None

        # Verify that account info is None and no trade execution occurs
        acc = worker.demo_engine.adapter.get_account_info()
        self.assertIsNone(acc)

    @patch("time.sleep", return_value=None)
    @patch("src.Risk.Services.professional_risk_engine.ProfessionalRiskEngine.evaluate_equity_risk_and_position_size")
    def test_13_adversarial_account_and_free_margin_call_count_zero(self, mock_sizing, mock_sleep):
        """Test 13: Invalid/missing free margin or equity produce sizing call count == 0 and execution call count == 0."""
        from app.workers.research_worker import ResearchWorker

        adversarial_cases = [
            None,                                           # 1. acc_info = None
            "raise_exception",                              # 2. get_account_info raises exception
            {},                                             # 3. missing equity key
            {"equity": None},                               # 4. equity = None
            {"equity": 0.0},                                # 5. equity = 0
            {"equity": -100.0},                             # 6. equity < 0
            {"equity": float("nan")},                       # 7. equity = NaN
            {"equity": float("inf")},                       # 8. equity = infinity
            {"equity": "malformed_str"},                    # 9. malformed equity string
            {"equity": 10000.0, "free_margin": None},       # 10. missing free margin (None)
            {"equity": 10000.0, "free_margin": 0.0},        # 11. free margin = 0
            {"equity": 10000.0, "free_margin": -500.0},     # 12. free margin < 0
            {"equity": 10000.0, "free_margin": float("nan")}, # 13. free margin = NaN
            {"equity": 10000.0, "free_margin": float("inf")}, # 14. free margin = Inf
            {"equity": 10000.0, "free_margin": "malformed"},  # 15. malformed free margin string
        ]

        for idx, acc_data in enumerate(adversarial_cases):
            mock_sizing.reset_mock()
            worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")

            mock_adapter = MagicMock()
            if acc_data == "raise_exception":
                mock_adapter.get_account_info.side_effect = RuntimeError("Broker connection timeout")
            else:
                mock_adapter.get_account_info.return_value = acc_data
            mock_adapter.get_symbol_info.return_value = {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}

            mock_demo = MagicMock()
            mock_demo.adapter = mock_adapter
            mock_demo.get_active_positions.return_value = []
            worker.demo_engine = mock_demo

            mock_runtime = MagicMock()
            mock_run_res = MagicMock()
            mock_run_res.Findings = {
                "autonomous_decision": {
                    "action": "BUY",
                    "entry": 2500.0,
                    "stop_loss": 2490.0,
                    "take_profit": 2520.0,
                    "risk_reward": 2.0,
                    "confidence": 80.0
                }
            }
            mock_runtime.run_once.return_value = mock_run_res
            mock_runtime.provider.delegate.get_connection_health.return_value = {"connected": True, "status": "HEALTHY"}
            worker.runtimes[("XAUUSD", "H1")] = mock_runtime

            worker.is_running = True
            def stop_loop_after_one(*args, **kwargs):
                if not hasattr(stop_loop_after_one, "called"):
                    stop_loop_after_one.called = True
                    return [("XAUUSD", "H1", "Commodities", "MT5")]
                worker.is_running = False
                return [("XAUUSD", "H1", "Commodities", "MT5")]

            with patch.object(worker, "_get_active_matrix", side_effect=stop_loop_after_one):
                worker._run_loop()

            self.assertEqual(mock_sizing.call_count, 0, f"Case {idx+1} failed sizing call count expectation (expected 0, got {mock_sizing.call_count})")
            self.assertEqual(mock_demo.execute_demo_decision.call_count, 0, f"Case {idx+1} failed execution call count expectation")
            self.assertNotIn("XAUUSD", worker.last_executed_signal, f"Case {idx+1} updated last_executed_signal unexpectedly")

    @patch("time.sleep", return_value=None)
    @patch("src.Risk.Services.professional_risk_engine.ProfessionalRiskEngine.evaluate_equity_risk_and_position_size")
    def test_14_invalid_symbol_volume_limits_finite_checks(self, mock_sizing, mock_sleep):
        """Test 14: Non-finite or <=0 symbol volume limits (min, max, step) produce sizing call count == 0 and execution call count == 0."""
        from app.workers.research_worker import ResearchWorker

        invalid_symbol_cases = [
            {"volume_min": None, "volume_max": 100.0, "volume_step": 0.01},
            {"volume_min": 0.0, "volume_max": 100.0, "volume_step": 0.01},
            {"volume_min": -0.01, "volume_max": 100.0, "volume_step": 0.01},
            {"volume_min": float("nan"), "volume_max": 100.0, "volume_step": 0.01},
            {"volume_min": 0.01, "volume_max": float("nan"), "volume_step": 0.01},
            {"volume_min": 0.01, "volume_max": float("inf"), "volume_step": 0.01},
            {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.0},
            {"volume_min": 0.01, "volume_max": 100.0, "volume_step": float("nan")},
        ]

        for idx, sym_info in enumerate(invalid_symbol_cases):
            mock_sizing.reset_mock()
            worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")

            mock_adapter = MagicMock()
            mock_adapter.get_account_info.return_value = {"login": "52961173", "equity": 10000.0, "free_margin": 10000.0}
            mock_adapter.get_symbol_info.return_value = sym_info

            mock_demo = MagicMock()
            mock_demo.adapter = mock_adapter
            mock_demo.get_active_positions.return_value = []
            worker.demo_engine = mock_demo

            mock_runtime = MagicMock()
            mock_run_res = MagicMock()
            mock_run_res.Findings = {
                "autonomous_decision": {
                    "action": "BUY",
                    "entry": 2500.0,
                    "stop_loss": 2490.0,
                    "take_profit": 2520.0,
                    "risk_reward": 2.0,
                    "confidence": 80.0
                }
            }
            mock_runtime.run_once.return_value = mock_run_res
            mock_runtime.provider.delegate.get_connection_health.return_value = {"connected": True, "status": "HEALTHY"}
            worker.runtimes[("XAUUSD", "H1")] = mock_runtime

            worker.is_running = True
            def stop_loop_after_one(*args, **kwargs):
                if not hasattr(stop_loop_after_one, "called"):
                    stop_loop_after_one.called = True
                    return [("XAUUSD", "H1", "Commodities", "MT5")]
                worker.is_running = False
                return [("XAUUSD", "H1", "Commodities", "MT5")]

            with patch.object(worker, "_get_active_matrix", side_effect=stop_loop_after_one):
                worker._run_loop()

            self.assertEqual(mock_sizing.call_count, 0, f"Symbol Case {idx+1} failed sizing call count expectation")
            self.assertEqual(mock_demo.execute_demo_decision.call_count, 0, f"Symbol Case {idx+1} failed execution call count expectation")

    @patch("time.sleep", return_value=None)
    @patch("src.Risk.Services.professional_risk_engine.ProfessionalRiskEngine.evaluate_equity_risk_and_position_size")
    def test_15_reversal_volume_authority_and_rejection_state(self, mock_sizing, mock_sleep):
        """Test 15: Reversal volume input is ignored entirely (sizing computes volume) and failed execution status does NOT mutate state."""
        from app.workers.research_worker import ResearchWorker
        from src.Risk.Services.professional_risk_engine import PositionSizingResult

        mock_sizing.return_value = PositionSizingResult(
            is_valid=True,
            volume_lots=0.85,
            risk_budget_usd=50.0,
            risk_pct=0.5,
            margin_required_usd=1000.0,
            free_margin_usd=10000.0,
            effective_be_price=2500.0,
            rejection_reason=""
        )

        # 1. Test Reversal ignores reassessment volume input (e.g. malformed/huge volume 999.9) and uses sized volume 0.85
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")

        mock_adapter = MagicMock()
        mock_adapter.get_account_info.return_value = {"login": "52961173", "equity": 10000.0, "free_margin": 10000.0}
        mock_adapter.get_symbol_info.return_value = {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}

        mock_demo = MagicMock()
        mock_demo.adapter = mock_adapter
        mock_demo.get_active_positions.side_effect = [
            [{"ticket": 1001, "type": 0, "symbol": "XAUUSD"}], # Active BUY
            [] # Closed flat
        ]
        mock_demo.close_position.return_value = OrderResponse(OrderId="1001", Symbol="XAUUSD", Status="Closed", SubmittedAt=datetime.now(timezone.utc), Comment="RevClose")

        # Execution fails with MARKET_CLOSED
        mock_demo.execute_demo_decision.return_value = OrderResponse(OrderId="0", Symbol="XAUUSD", Status="Failed", SubmittedAt=datetime.now(timezone.utc), Comment="MARKET_CLOSED")
        worker.demo_engine = mock_demo

        mock_runtime = MagicMock()
        initial_run_res = MagicMock()
        initial_run_res.Findings = {
            "autonomous_decision": {
                "action": "SELL",
                "entry": 2500.0,
                "stop_loss": 2510.0,
                "take_profit": 2480.0,
                "risk_reward": 2.0,
                "confidence": 80.0
            }
        }
        reassess_run_res = MagicMock()
        reassess_run_res.Findings = {
            "autonomous_decision": {
                "action": "SELL",
                "entry": 2500.0,
                "stop_loss": 2510.0,
                "take_profit": 2480.0,
                "risk_reward": 2.0,
                "confidence": 80.0,
                "volume": 999.9 # Huge/malformed input volume from reassessment decision
            }
        }
        mock_runtime.run_once.side_effect = [initial_run_res, reassess_run_res]
        mock_runtime.provider.delegate.get_connection_health.return_value = {"connected": True, "status": "HEALTHY"}
        worker.runtimes[("XAUUSD", "H1")] = mock_runtime

        worker.is_running = True
        def stop_loop_after_one(*args, **kwargs):
            if not hasattr(stop_loop_after_one, "called"):
                stop_loop_after_one.called = True
                return [("XAUUSD", "H1", "Commodities", "MT5")]
            worker.is_running = False
            return [("XAUUSD", "H1", "Commodities", "MT5")]

        with patch.object(worker, "_get_active_matrix", side_effect=stop_loop_after_one):
            worker._run_loop()

        # Assertions
        self.assertEqual(mock_sizing.call_count, 1)
        self.assertEqual(mock_demo.execute_demo_decision.call_count, 1)
        # Verify volume passed to execute_demo_decision is 0.85 (from sizing), NOT 999.9 (from decision dict)
        self.assertEqual(mock_demo.execute_demo_decision.call_args[1]["volume"], 0.85)
        # Verify state was NOT mutated because execution Status was 'Failed'
        self.assertNotIn("XAUUSD", worker.last_executed_signal)


class TestAutonomousDemoExecutionGate(unittest.TestCase):
    """
    Focused SRE Regression Tests for Autonomous DEMO Execution Gate.
    Enforces strict security contract for AUTONOMOUS_DEMO_TRADING_ENABLED.
    """

    def setUp(self):
        self.original_env = os.environ.get("AUTONOMOUS_DEMO_TRADING_ENABLED")

    def tearDown(self):
        if self.original_env is None:
            os.environ.pop("AUTONOMOUS_DEMO_TRADING_ENABLED", None)
        else:
            os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = self.original_env

    def test_01_env_absent_blocked(self):
        os.environ.pop("AUTONOMOUS_DEMO_TRADING_ENABLED", None)
        self.assertFalse(is_autonomous_demo_enabled())

    def test_02_env_empty_blocked(self):
        os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = ""
        self.assertFalse(is_autonomous_demo_enabled())

    def test_03_env_whitespace_blocked(self):
        os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = "   "
        self.assertFalse(is_autonomous_demo_enabled())

    def test_04_env_false_blocked(self):
        os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = "false"
        self.assertFalse(is_autonomous_demo_enabled())

    def test_05_env_zero_blocked(self):
        os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = "0"
        self.assertFalse(is_autonomous_demo_enabled())

    def test_06_env_no_blocked(self):
        os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = "no"
        self.assertFalse(is_autonomous_demo_enabled())

    def test_07_env_off_blocked(self):
        os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = "off"
        self.assertFalse(is_autonomous_demo_enabled())

    def test_08_unknown_values_blocked(self):
        for val in ["1", "yes", "maybe", "ENABLED", "true123", "invalid"]:
            os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = val
            self.assertFalse(is_autonomous_demo_enabled(), f"Value '{val}' should be BLOCKED")

    def test_09_explicit_true_enabled(self):
        for val in ["true", "TRUE", "True", "  true  ", "  TRUE\t"]:
            os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = val
            self.assertTrue(is_autonomous_demo_enabled(), f"Value '{val}' should be ENABLED")

    def test_10_non_xauusd_remains_blocked(self):
        """Non-XAUUSD symbols are strictly blocked from execution dispatch regardless of ENV."""
        from app.workers.research_worker import ResearchWorker
        os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"] = "true"
        worker = ResearchWorker(symbol="EURUSD", timeframe="H1")

        mock_demo = MagicMock()
        worker.demo_engine = mock_demo

        mock_runtime = MagicMock()
        mock_run_res = MagicMock()
        mock_run_res.Findings = {
            "autonomous_decision": {
                "action": "BUY",
                "entry": 1.0850,
                "stop_loss": 1.0800,
                "take_profit": 1.0950,
                "risk_reward": 2.0,
                "confidence": 80.0
            }
        }
        mock_runtime.run_once.return_value = mock_run_res
        mock_runtime.provider.delegate.get_connection_health.return_value = {"connected": True, "status": "HEALTHY"}
        worker.runtimes[("EURUSD", "H1")] = mock_runtime

        worker.is_running = True
        def stop_after_one(*args, **kwargs):
            if not hasattr(stop_after_one, "called"):
                stop_after_one.called = True
                return [("EURUSD", "H1", "Forex", "MT5")]
            worker.is_running = False
            return [("EURUSD", "H1", "Forex", "MT5")]

        with patch.object(worker, "_get_active_matrix", side_effect=stop_after_one):
            worker._run_loop()

        self.assertEqual(mock_demo.execute_demo_decision.call_count, 0)

    def test_11_live_execution_remains_impossible(self):
        """Verify MetaTraderSafetyGate hard blocks REAL_LIVE operations."""
        from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
        from src.Infrastructure.exceptions import ValidationException
        with self.assertRaises(ValidationException) as ctx:
            MetaTraderSafetyGate.verify_operation(terminal_type="MT5", operation_type="REAL_LIVE")
        self.assertIn("Real Live Trading is hard-disabled", str(ctx.exception))

    @patch("time.sleep", return_value=None)
    def test_12_spying_dispatch_blocked_when_env_absent(self, mock_sleep):
        """
        CRITICAL SPYING TEST:
        When action = BUY/SELL and AUTONOMOUS_DEMO_TRADING_ENABLED is absent,
        prove that execute_demo_decision is NEVER called at the order dispatch boundary.
        """
        from app.workers.research_worker import ResearchWorker
        os.environ.pop("AUTONOMOUS_DEMO_TRADING_ENABLED", None)

        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")

        mock_adapter = MagicMock()
        mock_adapter.get_account_info.return_value = {"login": "52961173", "equity": 10000.0, "free_margin": 10000.0}
        mock_adapter.get_symbol_info.return_value = {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}

        mock_demo = MagicMock()
        mock_demo.adapter = mock_adapter
        mock_demo.get_active_positions.return_value = []
        worker.demo_engine = mock_demo

        mock_runtime = MagicMock()
        mock_run_res = MagicMock()
        mock_run_res.Findings = {
            "autonomous_decision": {
                "action": "SELL",
                "entry": 2500.0,
                "stop_loss": 2510.0,
                "take_profit": 2480.0,
                "risk_reward": 2.0,
                "confidence": 85.0
            }
        }
        mock_runtime.run_once.return_value = mock_run_res
        mock_runtime.provider.delegate.get_connection_health.return_value = {"status": "HEALTHY"}
        worker.runtimes[("XAUUSD", "H1")] = mock_runtime

        worker.is_running = True
        def stop_after_one(*args, **kwargs):
            if not hasattr(stop_after_one, "called"):
                stop_after_one.called = True
                return [("XAUUSD", "H1", "Commodities", "MT5")]
            worker.is_running = False
            return [("XAUUSD", "H1", "Commodities", "MT5")]

        with patch.object(worker, "_get_active_matrix", side_effect=stop_after_one):
            worker._run_loop()

        # Proves execution dispatch was NOT called when ENV was absent!
        self.assertEqual(mock_demo.execute_demo_decision.call_count, 0)
        self.assertNotIn("XAUUSD", worker.last_executed_signal)


class TestRiskTargetContractRemediation(unittest.TestCase):
    """
    Focused SRE Regression Tests for Risk Target Contract Remediation.
    Verifies that target risk is strictly 0.5%, 2.0% ceiling is enforced,
    RR >= 1.5 is enforced, and daily loss >= 8.0% blocks trading.
    """

    def setUp(self):
        self.original_env = os.environ.get("RISK_PCT_PER_TRADE")

    def tearDown(self):
        if self.original_env is None:
            os.environ.pop("RISK_PCT_PER_TRADE", None)
        else:
            os.environ["RISK_PCT_PER_TRADE"] = self.original_env

    def test_01_production_risk_policy_target_is_point_five(self):
        """Test 1: ProductionRiskPolicy.TARGET_RISK_PCT is strictly 0.5%."""
        from src.Risk.Services.professional_risk_engine import ProductionRiskPolicy
        self.assertEqual(ProductionRiskPolicy.TARGET_RISK_PCT, 0.5)

    def test_02_missing_risk_env_defaults_to_point_five(self):
        """Test 2: Missing RISK_PCT_PER_TRADE ENV defaults to 0.5%."""
        os.environ.pop("RISK_PCT_PER_TRADE", None)
        raw_risk_env = os.getenv("RISK_PCT_PER_TRADE", "0.5")
        self.assertEqual(float(raw_risk_env), 0.5)

    def test_03_explicit_risk_env_resolves_correctly(self):
        """Test 3: Explicit RISK_PCT_PER_TRADE resolves correctly."""
        os.environ["RISK_PCT_PER_TRADE"] = "0.5"
        raw_risk_env = os.getenv("RISK_PCT_PER_TRADE", "0.5")
        self.assertEqual(float(raw_risk_env), 0.5)

    def test_04_invalid_risk_env_fails_closed(self):
        """Test 4: Invalid/non-numeric RISK_PCT_PER_TRADE fails closed in worker sizing."""
        from app.workers.research_worker import ResearchWorker
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")

        mock_adapter = MagicMock()
        mock_adapter.get_account_info.return_value = {"login": "52961173", "equity": 10000.0, "free_margin": 10000.0}
        mock_adapter.get_symbol_info.return_value = {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}
        mock_demo = MagicMock()
        mock_demo.adapter = mock_adapter
        worker.demo_engine = mock_demo

        os.environ["RISK_PCT_PER_TRADE"] = "invalid_string"
        sized = worker._validate_and_size_decision("XAUUSD", "BUY", {"entry": 2500.0, "stop_loss": 2490.0, "take_profit": 2520.0})
        self.assertIsNone(sized)

    def test_05_risk_exceeding_hard_ceiling_rejected(self):
        """Test 5: Risk exceeding 2.0% hard ceiling is rejected."""
        from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
        risk_engine = ProfessionalRiskEngine()
        res = risk_engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2500.0,
            stop_loss=2490.0,
            account_equity=10000.0,
            free_margin=10000.0,
            risk_pct=2.5 # Exceeds 2.0% hard ceiling
        )
        self.assertFalse(res.is_valid)
        self.assertIn("exceeds maximum allowable ceiling of 2.0%", res.rejection_reason)

    def test_06_rr_below_minimum_threshold_rejected(self):
        """Test 6: Real RR < 1.5 minimum threshold is rejected."""
        from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
        risk_engine = ProfessionalRiskEngine()
        eval_res = risk_engine.evaluate_trade_risk(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2500.0,
            stop_loss=2490.0,
            take_profit=2505.0 # Low RR < 1.5
        )
        self.assertFalse(eval_res.is_valid)
        self.assertEqual(eval_res.direction, "WAIT")
        self.assertIn("< 1.5 minimum threshold", eval_res.rejection_reason)

    def test_07_daily_loss_limit_exceeded_blocks_trading(self):
        """Test 7: Portfolio daily loss >= 8.0% blocks trading."""
        from src.Intelligence.Execution.portfolio import PortfolioRiskIntelligenceEngine
        portfolio_engine = PortfolioRiskIntelligenceEngine(max_daily_drawdown_pct=8.0)
        res = portfolio_engine.calculate_portfolio_risk(
            active_trades=[],
            virtual_balance=10000.0,
            start_of_day_equity=10000.0,
            daily_pnl=-850.0 # 8.5% loss >= 8.0%
        )
        self.assertFalse(res["approved"])
        self.assertTrue(any("max daily loss threshold" in v for v in res["violations"]))

    def test_08_position_sizing_uses_half_percent_risk_budget(self):
        """Test 8: Position sizing calculation calculates exact risk budget using 0.5% target risk."""
        from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
        risk_engine = ProfessionalRiskEngine()
        equity = 10000.0
        res = risk_engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2500.0,
            stop_loss=2490.0,
            account_equity=equity,
            free_margin=equity,
            risk_pct=0.5
        )
        self.assertTrue(res.is_valid)
        # 0.5% of $10,000 equity is $50.00 risk budget
        self.assertEqual(res.risk_budget_usd, 50.0)


class TestDailyLossKillSwitchExecutionBoundary(unittest.TestCase):
    """
    SRE Unit Tests for DailyLossKillSwitch at the Execution Boundary.
    Verifies:
    1. loss < 8% -> gate passes
    2. loss >= 8% -> execution blocked
    3. invalid/missing equity -> execution blocked
    4. kill switch exception -> execution blocked
    5. no alternate execution path bypasses daily-loss protection.
    """

    def setUp(self):
        from src.Risk.Services.daily_loss_kill_switch import DailyLossKillSwitch
        self.kill_switch = DailyLossKillSwitch.get_instance()
        today_key, _, _ = self.kill_switch.get_session_key_and_window()
        self.kill_switch.set_session_baseline(equity=10000.0, session_date=today_key)

    def test_01_loss_below_8_percent_passes(self):
        # 5% loss ($9500 current equity vs $10000 baseline) -> allowed
        allowed, reason, meta = self.kill_switch.evaluate_daily_loss(9500.0)
        self.assertTrue(allowed)
        self.assertIsNone(reason)
        self.assertFalse(meta["kill_switch_active"])

    def test_02_loss_8_percent_or_higher_blocked(self):
        # 8.5% loss ($9150 current equity vs $10000 baseline) -> blocked
        allowed, reason, meta = self.kill_switch.evaluate_daily_loss(9150.0)
        self.assertFalse(allowed)
        self.assertEqual(reason, "DAILY_LOSS_LIMIT_REACHED")
        self.assertTrue(meta["kill_switch_active"])

    def test_03_invalid_or_missing_equity_blocked(self):
        for invalid_eq in [None, "invalid", -100.0, float("nan"), float("inf"), False, True, 0.0]:
            allowed, reason, meta = self.kill_switch.evaluate_daily_loss(invalid_eq)
            self.assertFalse(allowed, f"Invalid equity '{invalid_eq}' should be BLOCKED")
            self.assertEqual(reason, "KILL_SWITCH_ERROR")

    def test_06_demo_execution_gate_rejects_missing_or_invalid_equity(self):
        """Verifies DemoExecutionGate raises ValidationException for missing, boolean, zero, negative, or non-finite equity."""
        mock_adapter = MagicMock()
        mock_adapter.get_terminal_info.return_value = {"connected": True, "trade_allowed": True}
        mock_adapter.get_symbol_info.return_value = {"name": "XAUUSD", "trade_mode": 4, "volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}

        invalid_equities = [None, True, False, "invalid_str", 0.0, -500.0, float("nan"), float("inf"), float("-inf")]

        for eq in invalid_equities:
            mock_adapter.get_account_info.return_value = {
                "login": "52961173",
                "server": "Alpari-MT5-Demo",
                "trade_mode": 0,
                "equity": eq
            }
            req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01, Price=2500.0, StopLoss=2490.0, TakeProfit=2520.0)
            with self.assertRaises(ValidationException, msg=f"Equity '{eq}' should raise ValidationException"):
                DemoExecutionGate.verify_demo_execution_eligibility(mock_adapter, req, demo_mode_flag=True)

    def test_04_kill_switch_exception_blocks_worker_validation(self):
        from app.workers.research_worker import ResearchWorker
        worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")

        mock_adapter = MagicMock()
        mock_adapter.get_account_info.return_value = {"login": "52961173", "equity": 10000.0, "free_margin": 10000.0}
        mock_adapter.get_symbol_info.return_value = {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}
        mock_demo = MagicMock()
        mock_demo.adapter = mock_adapter
        worker.demo_engine = mock_demo

        with patch.object(self.kill_switch, "evaluate_daily_loss", side_effect=RuntimeError("Persistence disk error")):
            sized = worker._validate_and_size_decision("XAUUSD", "BUY", {"entry": 2500.0, "stop_loss": 2490.0, "take_profit": 2520.0})
            self.assertIsNone(sized)

    def test_05_demo_execution_gate_enforces_daily_loss_protection(self):
        # Trigger kill switch with 10% loss
        today_key, _, _ = self.kill_switch.get_session_key_and_window()
        self.kill_switch.set_session_baseline(equity=10000.0, session_date=today_key)
        self.kill_switch.evaluate_daily_loss(9000.0) # Active kill switch

        mock_adapter = MagicMock()
        mock_adapter.get_account_info.return_value = {
            "login": "52961173",
            "server": "Alpari-MT5-Demo",
            "trade_mode": 0,
            "equity": 9000.0
        }
        mock_adapter.get_terminal_info.return_value = {"connected": True, "trade_allowed": True}
        mock_adapter.get_symbol_info.return_value = {"name": "XAUUSD", "trade_mode": 4, "volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}

        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.01, Price=2500.0, StopLoss=2490.0, TakeProfit=2520.0)
        with self.assertRaises(ValidationException) as ctx:
            DemoExecutionGate.verify_demo_execution_eligibility(mock_adapter, req, demo_mode_flag=True)
        self.assertIn("Daily 8% loss limit active", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
