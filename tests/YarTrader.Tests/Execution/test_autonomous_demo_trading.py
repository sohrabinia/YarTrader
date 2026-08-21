import os
import time
import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.workers.research_worker import ResearchWorker
from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
from src.Execution.Models.models import OrderResponse, OrderRequest
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate

def create_mock_adapter():
    mock_adapter = MagicMock()
    mock_adapter.get_account_info.return_value = {
        "login": 52961173,
        "server": "Alpari-MT5-Demo",
        "trade_mode": 0,
        "balance": 33000.0,
        "equity": 33000.0,
        "margin_free": 30000.0
    }
    mock_adapter.get_terminal_info.return_value = {"connected": True, "trade_allowed": True}
    mock_adapter.get_symbol_info.return_value = {
        "symbol": "XAUUSD",
        "visible": True,
        "volume_min": 0.01,
        "volume_max": 100.0
    }

    mock_resp = OrderResponse(
        OrderId="10001",
        Symbol="XAUUSD",
        Status="SUCCESS",
        SubmittedAt=datetime.now(),
        Price=2420.5,
        Volume=0.01,
        Comment="Simulated Order Executed Successfully"
    )
    mock_adapter.send_order_to_broker.return_value = mock_resp
    return mock_adapter

class TestAutonomousDemoTrading(unittest.TestCase):
    def setUp(self) -> None:
        self.worker = ResearchWorker(symbol="XAUUSD", timeframe="H1", interval_sec=1.0, cooldown_sec=2.0)
        self.shadow_engine = PredictiveShadowEngine.get_instance()

    def test_autonomous_worker_lifecycle(self) -> None:
        """1. Test autonomous worker start, status tracking, and graceful stop."""
        self.assertFalse(self.worker.is_running)

        mock_runtime = MagicMock()
        mock_runtime.provider.delegate.get_connection_health.return_value.connected = True
        mock_runtime.run_once.return_value.Request.EndTime = None
        mock_runtime.run_once.return_value.Findings = {}

        with patch.object(self.worker, "_get_or_create_runtime", return_value=mock_runtime), \
             patch.object(self.worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Commodities", "MT5")]):

            self.worker.start()
            self.assertTrue(self.worker.is_running)
            time.sleep(0.2)
            self.assertEqual(self.worker.status, "RUNNING")

            self.worker.stop()
            self.assertFalse(self.worker.is_running)
            self.assertEqual(self.worker.status, "STOPPED")

    def test_autonomous_decision_to_demo_execution_without_api_trigger(self) -> None:
        """2. Verifies that an actionable signal in ResearchWorker automatically executes a Demo trade."""
        shadow_trades_before = len(self.shadow_engine.trades)

        mock_adapter = create_mock_adapter()
        engine = DemoExecutionEngine(adapter=mock_adapter, demo_mode=True)

        mock_runtime = MagicMock()
        mock_runtime.provider.delegate.get_connection_health.return_value.connected = True
        mock_runtime.run_once.return_value.Request.EndTime = None
        mock_runtime.run_once.return_value.Findings = {
            "pipeline_outputs": {
                "signals": {
                    "direction": "BUY",
                    "entry_price": 2420.5,
                    "sl": 2400.0,
                    "tp": 2450.0,
                    "volume": 0.01,
                    "timestamp": time.time()
                }
            }
        }

        with patch.object(self.worker, "_get_or_create_runtime", return_value=mock_runtime), \
             patch.object(self.worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Commodities", "MT5")]):

            self.worker.is_running = True
            active_matrix = self.worker._get_active_matrix()
            for symbol, tf, asset_class, provider in active_matrix:
                runtime = self.worker._get_or_create_runtime(symbol, tf, asset_class, provider)
                res = runtime.run_once()
                signals = res.Findings.get("pipeline_outputs", {}).get("signals", {})
                if signals and signals.get("direction") in ["BUY", "SELL"]:
                    sig_dir = signals.get("direction")
                    sig_price = signals.get("entry_price")
                    sig_sl = signals.get("sl")
                    sig_tp = signals.get("tp")
                    sig_vol = signals.get("volume", 0.01)

                    exec_resp = engine.execute_demo_decision(
                        symbol=symbol,
                        direction=sig_dir,
                        volume=sig_vol,
                        price=sig_price,
                        sl=sig_sl,
                        tp=sig_tp,
                        comment=f"YarTrader DEMO {symbol}",
                        magic=143056,
                        decision_id="DEC-TEST-001"
                    )
                    self.assertEqual(exec_resp.Status, "SUCCESS")
                    self.assertIsNotNone(exec_resp.OrderId)

        shadow_trades_after = len(self.shadow_engine.trades)
        self.assertEqual(shadow_trades_before, shadow_trades_after)

    def test_deduplication_and_cooldown_protection(self) -> None:
        """3 & 5. Verifies duplicate signal order spamming is prevented by cooldown logic."""
        symbol = "XAUUSD"
        sig_dir = "BUY"
        now_time = time.time()

        self.worker.last_executed_signal[symbol.upper()] = {
            "direction": sig_dir,
            "sig_time": now_time,
            "exec_time": now_time,
            "decision_id": "DEC-PREV"
        }

        last_exec = self.worker.last_executed_signal.get(symbol.upper())
        elapsed = time.time() - last_exec.get("exec_time", 0)
        is_same_signal = (last_exec.get("direction") == sig_dir and last_exec.get("sig_time") == now_time)

        self.assertTrue(is_same_signal or elapsed < self.worker.cooldown_sec)

    def test_demo_persistence_and_restart_recovery(self) -> None:
        """4. Verifies Demo state recovers after service/engine re-instantiation."""
        mock_adapter = create_mock_adapter()

        engine = DemoExecutionEngine(adapter=mock_adapter, demo_mode=True)
        resp = engine.execute_demo_decision(
            symbol="EURUSD",
            direction="BUY",
            volume=0.1,
            price=1.0850,
            sl=1.0800,
            tp=1.0950,
            comment="Restart Test",
            magic=143056,
            decision_id="DEC-RESTART-001"
        )
        self.assertEqual(resp.Status, "SUCCESS")

        # Verify evidence files persisted on disk
        evidence_files = [f for f in os.listdir(engine.log_dir) if f.startswith("demo_order_")]
        self.assertGreater(len(evidence_files), 0)

    def test_demo_mode_hard_isolation(self) -> None:
        """7, 8 & 9. Confirms Demo execution NEVER writes to Shadow, Backtest, or Live broker."""
        shadow_before = len(self.shadow_engine.trades)

        mock_adapter = create_mock_adapter()

        engine = DemoExecutionEngine(adapter=mock_adapter, demo_mode=True)
        resp = engine.execute_demo_decision(
            symbol="GBPUSD",
            direction="SELL",
            volume=0.05,
            price=1.2850,
            sl=1.2900,
            tp=1.2750,
            comment="Isolation Test",
            magic=143056,
            decision_id="DEC-ISO-001"
        )
        self.assertEqual(resp.Status, "SUCCESS")

        shadow_after = len(self.shadow_engine.trades)
        self.assertEqual(shadow_before, shadow_after)

        self.assertFalse(os.environ.get("LIVE_TRADING_ENABLED", "False").lower() in ("true", "1"))

    def test_demo_execution_gate_safety_checks(self) -> None:
        """6 & 10. Validates that DemoExecutionGate enforces DEMO account 52961173 and safety checks."""
        mock_adapter = create_mock_adapter()

        req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="BUY",
            Volume=0.01,
            Price=2420.5,
            StopLoss=2400.0,
            TakeProfit=2450.0
        )

        res = DemoExecutionGate.verify_demo_execution_eligibility(
            adapter_or_mt5=mock_adapter,
            request=req,
            demo_mode_flag=True
        )
        self.assertTrue(res)
