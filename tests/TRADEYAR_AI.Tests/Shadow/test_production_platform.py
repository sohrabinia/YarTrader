import os
import unittest
from fastapi.testclient import TestClient

from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.Application.Services.web_dashboard import app, global_auth_service

class TestProductionPlatformSaaS(unittest.TestCase):
    """
    Final SRE SaaS platform validation test suite for TradeYar AI v7.0.
    Ensures absolute three-tier route isolation, limits, and pricing compliance.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.engine = PredictiveShadowEngine.get_instance()
        self.engine.contexts = {}
        self.engine.trades = []
        self.engine.signals = []

        # Reset auth session store
        global_auth_service.active_sessions = {}

    def test_public_saas_metrics_and_pricing(self) -> None:
        # Check pricing and conversion statistics are active
        resp = self.client.get("/api/public/pricing")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 4)
        self.assertEqual(data[3]["tier_id"], "institutional")
        self.assertIn("50 Active Symbols", data[3]["features"])

        # Check compliance disclaimers
        resp2 = self.client.get("/api/public/metrics")
        self.assertEqual(resp2.status_code, 200)
        metrics = resp2.json()
        self.assertEqual(metrics["active_markets_count"], 30)
        self.assertIn("Simulated performance results", metrics["compliance_disclaimer"])

    def test_user_terminal_horizon_signals(self) -> None:
        # Add predictive order on Macro horizon (frame 256)
        self.engine.create_predictive_order(
            symbol="BTCUSD",
            direction="LONG",
            entry=60000.0,
            stop=59000.0,
            target=65000.0,
            confidence=80.0,
            custom_time_structure=256
        )

        # Retrieve user signals filtered by Macro horizon
        resp = self.client.get("/api/user/signals?horizon=macro")
        self.assertEqual(resp.status_code, 200)
        signals = resp.json()
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["horizon"], "Macro")
        self.assertEqual(signals[0]["symbol"], "BTCUSD")

        # Test equity growth simulator
        resp2 = self.client.get("/api/user/equity-simulation?initial_balance=10000&monthly_growth_pct=10&months=3")
        self.assertEqual(resp2.status_code, 200)
        growth_data = resp2.json()
        self.assertEqual(len(growth_data["projection"]), 4) # month 0 to 3
        self.assertEqual(growth_data["final_balance"], 13310.0)

    def test_admin_symbols_registration_limit(self) -> None:
        # Admin SRE token
        admin_token = global_auth_service.create_session({"email": "admin@tradeyar.ai", "role": "ADMIN"})

        # Create contexts for 30 symbols
        for i in range(1, 31):
            symbol = f"SYM{i}"
            self.engine.create_predictive_order(symbol, "LONG", 10.0, 9.0, 11.0, 80.0, custom_time_structure=64)

        # Attempting the 31st symbol context registration MUST trigger ValueError via REST POST endpoint
        payload = {"symbol": "SYM31", "timeframe": 64}
        resp = self.client.post(f"/api/admin/symbols?token={admin_token}", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Hard SRE limit reached", resp.json()["detail"])

    def test_strict_role_based_security_guards(self) -> None:
        # Register a standard User session token
        user_token = global_auth_service.create_session({"email": "trader@tradeyar.ai", "role": "USER"})

        # Normal users attempting SRE admin actions MUST be blocked with 403 Forbidden
        resp1 = self.client.get(f"/api/admin/symbols?token={user_token}")
        self.assertEqual(resp1.status_code, 403)
        self.assertIn("Forbidden", resp1.json()["detail"])

        payload = {"symbol": "XAUUSD", "timeframe": 64}
        resp2 = self.client.post(f"/api/admin/symbols?token={user_token}", json=payload)
        self.assertEqual(resp2.status_code, 403)

    def test_independent_per_timeframe_analytics(self) -> None:
        admin_token = global_auth_service.create_session({"email": "admin@tradeyar.ai", "role": "ADMIN"})

        # Gold Frame 1 (Micro) with target hit (wins)
        t1 = self.engine.create_predictive_order("XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0, custom_time_structure=1)
        self.engine.update_market_ticks("XAUUSD", 2001.0)
        self.engine.update_market_ticks("XAUUSD", 2025.0)

        # Gold Frame 1024 (Macro) with stop hit (losses)
        t2 = self.engine.create_predictive_order("XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0, custom_time_structure=1024)
        self.engine.update_market_ticks("XAUUSD", 2001.0)
        self.engine.update_market_ticks("XAUUSD", 1985.0)

        # Retrieve distinct, unmerged timeframe reports
        resp = self.client.get(f"/api/admin/reports?symbol=XAUUSD&token={admin_token}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Since v8.0 instantiates 5 default contexts + 1 custom 1024 context = 6 contexts
        self.assertEqual(data["count"], 6)

        reports = data["reports"]
        rep_micro = next((r for r in reports if r["timeframe"] == 1), None)
        rep_macro = next((r for r in reports if r["timeframe"] == 1024), None)

        self.assertIsNotNone(rep_micro)
        self.assertIsNotNone(rep_macro)

        self.assertEqual(rep_micro["win_rate_pct"], 100.0)
        self.assertEqual(rep_macro["win_rate_pct"], 0.0)
