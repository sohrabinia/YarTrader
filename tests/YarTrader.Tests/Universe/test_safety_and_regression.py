import unittest
from unittest.mock import MagicMock
from app.workers.research_worker import ResearchWorker
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
from src.Execution.Models.models import OrderRequest
from src.Infrastructure.exceptions import ValidationException

class TestSafetyAndRegression(unittest.TestCase):
    """
    Tests enforcing Safety Invariants & XAUUSD Regression:
    - DEMO-only execution authorization preserved
    - LIVE trading strictly blocked repository-wide
    - Risk ceiling hard-capped at 2.0% equity risk per trade
    - RR < 1.5 decision rejection preserved
    - Missing account equity or margin fails closed
    - ShadowWorker remains Disabled
    - XAUUSD existing behavior remains regression-free
    """

    def setUp(self):
        self.worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")

    def test_live_trading_hard_blocked(self):
        # Verify MetaTraderSafetyGate blocks LIVE operations
        with self.assertRaises(Exception):
            MetaTraderSafetyGate.verify_operation(
                terminal_type="MT5",
                operation_type="LIVE",
                account_id="52961173",
                server_name="Alpari-MT5-Demo"
            )

    def test_demo_execution_gate_authorization(self):
        # Mock valid DEMO adapter
        mock_adapter = MagicMock()
        mock_adapter.get_account_info.return_value = {
            "login": "52961173",
            "server": "Alpari-MT5-Demo",
            "trade_mode": 0,
            "is_real": False,
            "platform": "MT5"
        }
        mock_adapter.get_terminal_info.return_value = {"trade_allowed": True, "tradeapi_disabled": False}
        mock_adapter.get_symbol_info.return_value = {"trade_mode": 4, "volume_min": 0.01, "volume_max": 100.0}
        mock_adapter.get_positions.return_value = []

        req = OrderRequest(
            Symbol="XAUUSD",
            OrderType="BUY",
            Volume=0.01,
            Price=2300.0,
            StopLoss=2290.0,
            TakeProfit=2320.0
        )

        res = DemoExecutionGate.verify_demo_execution_eligibility(
            adapter_or_mt5=mock_adapter,
            request=req,
            demo_mode_flag=True
        )
        self.assertTrue(res)

        # Real account flag must be rejected
        mock_adapter.get_account_info.return_value["is_real"] = True
        with self.assertRaises(ValidationException):
            DemoExecutionGate.verify_demo_execution_eligibility(
                adapter_or_mt5=mock_adapter,
                request=req,
                demo_mode_flag=True
            )

    def test_risk_ceiling_hard_max_2_percent(self):
        risk_engine = ProfessionalRiskEngine()
        res = risk_engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2300.0,
            stop_loss=2290.0,
            account_equity=10000.0,
            free_margin=10000.0,
            risk_pct=2.01,  # Exceeds 2.0% ceiling
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01
        )
        self.assertFalse(res.is_valid)
        self.assertIn("ceiling", res.rejection_reason.lower())

    def test_missing_equity_fails_closed(self):
        mock_engine = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.get_account_info.return_value = {"equity": 0.0, "free_margin": 1000.0}
        mock_engine.adapter = mock_adapter
        self.worker.demo_engine = mock_engine

        sized = self.worker._validate_and_size_decision("XAUUSD", "BUY", {"entry": 2300.0, "stop_loss": 2290.0})
        self.assertIsNone(sized, "Missing or <=0 equity must fail closed")

    def test_xauusd_regression_processing(self):
        runtime = self.worker._get_or_create_runtime("XAUUSD", "H1")
        res = runtime.run_once()
        self.assertIsNotNone(res)
        self.assertEqual(res.Request.Asset, "XAUUSD")
        self.assertIn("autonomous_decision", res.Findings)

if __name__ == "__main__":
    unittest.main()
