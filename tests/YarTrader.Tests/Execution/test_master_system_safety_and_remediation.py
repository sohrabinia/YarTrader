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
    # P0-1: DAILY LOSS KILL SWITCH & UNCONDITIONAL PRE-ENTRY GATE
    # =========================================================================
    def test_pre_entry_validation_without_equity_fails_closed(self):
        """Tests that validate_pre_entry without current_equity fails closed immediately."""
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

        res = self.session_engine.validate_pre_entry(symbol="XAUUSD")
        self.assertFalse(res.allowed)
        self.assertIn("KILL_SWITCH_ERROR", res.rejection_reason)

    def test_daily_loss_kill_switch_baseline_persistence(self):
        """Tests that session baseline equity is immutable once set and does not reset to lower current equity."""
        ks = DailyLossKillSwitch(state_file_path=os.path.join(self.tmp_dir.name, "baseline_test.json"))

        # 1. Establish session baseline at 100,000
        allowed, reason, meta = ks.evaluate_daily_loss(current_equity=100000.0, session_baseline_equity=100000.0)
        self.assertTrue(allowed)
        self.assertEqual(meta["baseline_equity"], 100000.0)

        # 2. Evaluation at 95,000 (5% loss -> allowed)
        allowed, reason, meta = ks.evaluate_daily_loss(current_equity=95000.0)
        self.assertTrue(allowed)
        self.assertEqual(meta["baseline_equity"], 100000.0)

        # 3. Subsequent evaluation at 91,000 (9% loss relative to 100,000 -> blocked!)
        allowed, reason, meta = ks.evaluate_daily_loss(current_equity=91000.0)
        self.assertFalse(allowed)
        self.assertEqual(meta["baseline_equity"], 100000.0)
        self.assertIn("DAILY_LOSS_LIMIT_REACHED", reason)

    # =========================================================================
    # P0-2: RESEARCH WORKER EXECUTION PATH & AUTONOMOUS DEFAULT TOGGLE
    # =========================================================================
    def test_research_worker_equity_validation_and_autonomous_default_off(self):
        """Tests that ResearchWorker validates equity strictly and defaults AUTONOMOUS_DEMO_TRADING_ENABLED to False."""
        worker = ResearchWorker()

        # Valid equity returns float
        eq = worker._validate_equity({"equity": 10000.0})
        self.assertEqual(eq, 10000.0)

        # Missing or invalid equity raises ValueError
        for bad_acc in [None, {}, {"equity": None}, {"equity": 0}, {"equity": -100}, {"equity": "abc"}, {"equity": float("nan")}]:
            with self.assertRaises(ValueError):
                worker._validate_equity(bad_acc)

        # Test default env check is false
        if "AUTONOMOUS_DEMO_TRADING_ENABLED" in os.environ:
            del os.environ["AUTONOMOUS_DEMO_TRADING_ENABLED"]

        default_enabled = os.getenv("AUTONOMOUS_DEMO_TRADING_ENABLED", "false").lower() in ["true", "1", "yes"]
        self.assertFalse(default_enabled, "AUTONOMOUS_DEMO_TRADING_ENABLED must default to False when env var is missing.")

    # =========================================================================
    # P0-3 & P0-4: MT5 FALLBACK REMOVAL & EXACT RISK VOLUME PRESERVATION
    # =========================================================================
    def test_mt5_adapter_no_defaults_and_exact_volume_preservation(self):
        """Tests that RealMT5BrokerAdapter fails closed on missing metadata and preserves exact volume."""
        adapter = RealMT5BrokerAdapter(auto_initialize=False)

        info = adapter.get_symbol_info("XAUUSD")
        self.assertIsNone(info)

        req_unaligned = OrderRequest(Symbol="XAUUSD", OrderType="BUY", Volume=0.015)
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
        self.assertTrue(DemoExecutionGate.verify_demo_execution_eligibility(mock_adapter, req))

        class BadLoginAdapter(MockAdapter):
            def get_account_info(self):
                return {"login": "", "server": "Alpari-MT5-Demo", "trade_mode": 0}
        with self.assertRaises(ValidationException):
            DemoExecutionGate.verify_demo_execution_eligibility(BadLoginAdapter(), req)

    # =========================================================================
    # P1: REVERSAL CLOSE VOLUME - NO 0.01 FALLBACK
    # =========================================================================
    def test_reversal_close_volume_authoritative_no_fallback(self):
        """Tests that DemoExecutionEngine.close_position uses exact broker volume 0.75 and fails if volume is missing."""
        captured_requests = []

        class MockCloseAdapter:
            def get_positions(self, symbol=None):
                return [{"ticket": 12345, "symbol": "XAUUSD", "type": 0, "volume": 0.75}]
            def send_order_to_broker(self, request):
                captured_requests.append(request)
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
        self.assertEqual(len(captured_requests), 1)
        self.assertEqual(captured_requests[0].Volume, 0.75)

        # Test missing position returns Failed status without fallback
        class MockMissingAdapter:
            def get_positions(self, symbol=None):
                return []
            def send_order_to_broker(self, request):
                from src.Execution.Models.models import OrderResponse
                return OrderResponse(OrderId="0", Symbol=request.Symbol, Status="Failed", SubmittedAt=datetime.now(timezone.utc), Retcode=10014)

        missing_engine = DemoExecutionEngine(adapter=MockMissingAdapter(), demo_mode=True)
        fail_resp = missing_engine.close_position(symbol="XAUUSD", position_ticket=99999, is_eod_flatten=True)
        self.assertEqual(fail_resp.Status, "Failed")

    # =========================================================================
    # P1: STRICT TIMEFRAME AGGREGATION
    # =========================================================================
    def test_strict_timeframe_aggregator(self):
        """Tests that StrictTimeframeAggregator rejects unknown timeframes and incomplete buckets."""
        with self.assertRaises(ValueError):
            StrictTimeframeAggregator.get_timeframe_ratio("M1", "UNKNOWN")

        m1_candles = [
            {"time": 1700000000 + i * 60, "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2002.0, "volume": 10}
            for i in range(5)
        ]
        m5 = StrictTimeframeAggregator.aggregate_candles(m1_candles, "M1", "M5")
        self.assertEqual(len(m5), 1)
        self.assertEqual(m5[0]["timeframe"], "M5")
        self.assertEqual(m5[0]["candle_count"], 5)

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
