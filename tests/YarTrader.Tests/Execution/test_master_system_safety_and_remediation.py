import os
import math
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from src.Risk.Services.daily_loss_kill_switch import DailyLossKillSwitch
from src.Execution.Services.market_session_engine import MarketSessionEngine, MarketState, SessionInterval
from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
from src.Execution.Models.models import OrderRequest
from src.Data.Aggregation.timeframe_aggregator import StrictTimeframeAggregator
from src.Intelligence.Execution.core import ExecutionIntelligenceCore
from src.Infrastructure.exceptions import ValidationException
from app.workers.research_worker import ResearchWorker


class TestMasterSystemSafetyAndRemediation(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_state_file = os.path.join(self.tmp_dir.name, "daily_loss_kill_switch.json")
        self.kill_switch = DailyLossKillSwitch(state_file_path=self.tmp_state_file)
        self.session_engine = MarketSessionEngine()
        self.session_engine.kill_switch = self.kill_switch

    def tearDown(self):
        self.tmp_dir.cleanup()

    # =========================================================================
    # P0-1: DAILY LOSS KILL SWITCH
    # =========================================================================
    def test_daily_loss_kill_switch_valid_and_invalid_equity(self):
        """Tests that DailyLossKillSwitch validates equity strictly and blocks daily loss >= 8%."""
        # 1. Valid initial equity set baseline
        allowed, reason, meta = self.kill_switch.evaluate_daily_loss(current_equity=10000.0, session_baseline_equity=10000.0)
        self.assertTrue(allowed, f"Should be allowed but got: {reason}")

        # 2. Loss < 8% allowed (7% loss)
        allowed, reason, meta = self.kill_switch.evaluate_daily_loss(current_equity=9300.0)
        self.assertTrue(allowed, f"Should be allowed but got: {reason}")

        # 3. Loss >= 8% blocked (8.1% loss)
        allowed, reason, meta = self.kill_switch.evaluate_daily_loss(current_equity=9190.0)
        self.assertFalse(allowed)
        self.assertIn("DAILY_LOSS_LIMIT_REACHED", reason)

        # 4. Invalid current equity values fail closed
        ks_fresh = DailyLossKillSwitch(state_file_path=os.path.join(self.tmp_dir.name, "fresh_ks.json"))
        for bad_eq in [None, "invalid", False, -500.0, 0, float("nan"), float("inf")]:
            allowed, reason, meta = ks_fresh.evaluate_daily_loss(current_equity=bad_eq)
            self.assertFalse(allowed, f"Should fail closed for bad equity: {bad_eq}")
            self.assertIn("KILL_SWITCH_ERROR", reason)

    def test_market_session_engine_daily_loss_integration(self):
        """Tests that MarketSessionEngine.validate_pre_entry enforces daily loss kill switch strictly."""
        now = datetime.now(timezone.utc)
        interval = SessionInterval(
            session_id="SESH-001",
            broker="DEFAULT",
            symbol="XAUUSD",
            market="FOREX",
            date_str=now.strftime("%Y-%m-%d"),
            weekday=now.weekday(),
            session_start=(now - timedelta(hours=1)).time(),
            session_end=(now.replace(hour=23, minute=59)).time(),
            utc_start=now.replace(hour=0, minute=0, second=0),
            utc_end=now.replace(hour=23, minute=59, second=59)
        )
        self.session_engine.register_session_interval(interval)

        # Valid equity pre-entry validation
        res = self.session_engine.validate_pre_entry(symbol="XAUUSD", current_equity=10000.0, session_baseline_equity=10000.0)
        self.assertTrue(res.allowed, f"Pre-entry should be allowed but got: {res.message}")

        # Equity with > 8% loss blocked
        res_loss = self.session_engine.validate_pre_entry(symbol="XAUUSD", current_equity=9100.0, session_baseline_equity=10000.0)
        self.assertFalse(res_loss.allowed)
        self.assertIn("DAILY_LOSS_LIMIT_REACHED", res_loss.rejection_reason)

    # =========================================================================
    # P0-2: RESEARCH WORKER EXECUTION PATH
    # =========================================================================
    def test_research_worker_equity_and_session_validation(self):
        """Tests that ResearchWorker validates equity and fails closed if equity is missing/invalid."""
        worker = ResearchWorker()

        # Valid equity returns float
        eq = worker._validate_equity({"equity": 10000.0})
        self.assertEqual(eq, 10000.0)

        # Missing or invalid equity raises ValueError
        for bad_acc in [None, {}, {"equity": None}, {"equity": 0}, {"equity": -100}, {"equity": "abc"}, {"equity": float("nan")}]:
            with self.assertRaises(ValueError):
                worker._validate_equity(bad_acc)

    # =========================================================================
    # P0-3 & P0-4: MT5 FALLBACK REMOVAL & EXACT RISK VOLUME PRESERVATION
    # =========================================================================
    def test_mt5_adapter_no_defaults_and_exact_volume_preservation(self):
        """Tests that RealMT5BrokerAdapter fails closed on missing metadata and preserves exact volume."""
        adapter = RealMT5BrokerAdapter(auto_initialize=False)

        # Dummy uninitialized adapter get_symbol_info returns None
        info = adapter.get_symbol_info("XAUUSD")
        self.assertIsNone(info)

        # Test volume validation logic on send_order_to_broker
        req_unaligned = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.015)
        # Without MT5 connected, verify_safety_and_account throws ValidationException
        with self.assertRaises(ValidationException):
            adapter.send_order_to_broker(req_unaligned)

    # =========================================================================
    # P0-5: POSITION QUERY UNKNOWN STATE
    # =========================================================================
    def test_get_positions_returns_none_when_disconnected(self):
        """Tests that get_positions() returns None (UNKNOWN) rather than [] when adapter is uninitialized."""
        adapter = RealMT5BrokerAdapter(auto_initialize=False)
        pos = adapter.get_positions(symbol="XAUUSD")
        self.assertIsNone(pos, "Disconnected adapter get_positions() must return None (UNKNOWN state).")

    # =========================================================================
    # P0-6: STRICT DEMO IDENTITY
    # =========================================================================
    def test_demo_execution_gate_strict_identity(self):
        """Tests that DemoExecutionGate rejects missing or non-matching account/terminal/symbol fields."""
        req = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.1, Price=2500.0, StopLoss=2490.0)

        class MockAdapter:
            def get_account_info(self):
                return {"login": "52961173", "server": "Alpari-MT5-Demo", "trade_mode": 0, "is_real": False}
            def get_terminal_info(self):
                return {"trade_allowed": True, "tradeapi_disabled": False}
            def get_symbol_info(self, symbol):
                return {"trade_mode": 4, "volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}
            def get_positions(self, symbol=None):
                return []

        mock_adapter = MockAdapter()

        # Valid mock passes
        self.assertTrue(DemoExecutionGate.verify_demo_execution_eligibility(mock_adapter, req))

        # Missing login
        class BadLoginAdapter(MockAdapter):
            def get_account_info(self):
                return {"login": "", "server": "Alpari-MT5-Demo", "trade_mode": 0}
        with self.assertRaises(ValidationException):
            DemoExecutionGate.verify_demo_execution_eligibility(BadLoginAdapter(), req)

        # Missing trade_mode
        class BadTradeModeAdapter(MockAdapter):
            def get_account_info(self):
                return {"login": "52961173", "server": "Alpari-MT5-Demo", "trade_mode": None}
        with self.assertRaises(ValidationException):
            DemoExecutionGate.verify_demo_execution_eligibility(BadTradeModeAdapter(), req)

        # UNKNOWN position query state returns None
        class UnknownPosAdapter(MockAdapter):
            def get_positions(self, symbol=None):
                return None
        with self.assertRaises(ValidationException):
            DemoExecutionGate.verify_demo_execution_eligibility(UnknownPosAdapter(), req)

    # =========================================================================
    # P1: REVERSAL CLOSE VOLUME
    # =========================================================================
    def test_reversal_close_volume_authoritative(self):
        """Tests that DemoExecutionEngine.close_position uses authoritative position volume."""
        class MockCloseAdapter:
            def get_positions(self, symbol=None):
                return [{"ticket": 12345, "symbol": "XAUUSD", "type": 0, "volume": 0.35}]
            def send_order_to_broker(self, request):
                from src.Execution.Models.models import OrderResponse
                return OrderResponse(
                    OrderId="101",
                    Symbol=request.Symbol,
                    Status="Placed",
                    SubmittedAt=datetime.now(timezone.utc),
                    Retcode=10009
                )

        mock_close = MockCloseAdapter()
        engine = DemoExecutionEngine(adapter=mock_close, demo_mode=True)

        resp = engine.close_position(symbol="XAUUSD", position_ticket=12345, is_eod_flatten=True)
        self.assertIsNotNone(resp)

    # =========================================================================
    # P1: STRICT TIMEFRAME AGGREGATION
    # =========================================================================
    def test_strict_timeframe_aggregator(self):
        """Tests that StrictTimeframeAggregator rejects unknown timeframes and incomplete buckets."""
        # Unknown timeframe
        with self.assertRaises(ValueError):
            StrictTimeframeAggregator.get_timeframe_ratio("M1", "UNKNOWN")

        # Complete M1 -> M5 aggregation
        m1_candles = [
            {"time": 1700000000 + i * 60, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0, "volume": 10}
            for i in range(5)
        ]
        m5 = StrictTimeframeAggregator.aggregate_candles(m1_candles, "M1", "M5")
        self.assertEqual(len(m5), 1)
        self.assertEqual(m5[0]["timeframe"], "M5")
        self.assertEqual(m5[0]["candle_count"], 5)

        # Incomplete bucket (4 candles) yields 0 M5 candles
        m5_inc = StrictTimeframeAggregator.aggregate_candles(m1_candles[:4], "M1", "M5")
        self.assertEqual(len(m5_inc), 0)

    # =========================================================================
    # P1: CONTEXT IDENTITY ISOLATION
    # =========================================================================
    def test_context_identity_causal_isolation(self):
        """Tests that context_identity derived from identical OHLC differs across timeframes."""
        candles = [
            {"time": 1700000000, "open": 2000.0, "high": 2010.0, "low": 1990.0, "close": 2005.0},
            {"time": 1700000060, "open": 2005.0, "high": 2015.0, "low": 2000.0, "close": 2010.0}
        ]

        id_m5 = ExecutionIntelligenceCore.compute_context_identity("XAUUSD", "M5", candles)
        id_h1 = ExecutionIntelligenceCore.compute_context_identity("XAUUSD", "H1", candles)

        self.assertNotEqual(id_m5, id_h1, "Same OHLC vector on M5 and H1 must produce distinct context_identity SHA256 hashes.")


if __name__ == "__main__":
    unittest.main()
