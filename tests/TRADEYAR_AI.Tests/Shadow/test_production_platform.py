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

    def test_timeframe_normalization_regression(self) -> None:
        """
        Regression tests for Phase 2:
        Verifies:
        - Duplicate prevention: 'M5', 'm5', 5, '5' map to the same canonical key ('M5').
        - Custom timeframe coexistence: e.g. 1024 and 'M5' both coexist beautifully.
        - Runtime reload/hydration consistency.
        """
        self.engine.contexts = {} # Reset

        # 1. Duplicate prevention
        ctx1 = self.engine.get_or_create_context("XAUUSD", "M5")
        ctx2 = self.engine.get_or_create_context("XAUUSD", "m5")
        ctx3 = self.engine.get_or_create_context("XAUUSD", 5)
        ctx4 = self.engine.get_or_create_context("XAUUSD", "5")

        # Verify that all 4 retrieve the exact same SymbolTimeContext object
        self.assertEqual(id(ctx1), id(ctx2))
        self.assertEqual(id(ctx1), id(ctx3))
        self.assertEqual(id(ctx1), id(ctx4))
        self.assertEqual(ctx1.timeframe, "M5")

        # 2. Custom timeframe coexistence
        ctx_custom = self.engine.get_or_create_context("XAUUSD", 1024)
        self.assertEqual(ctx_custom.timeframe, 1024)

        # 3. Reload/hydration consistency simulation
        # Simulate saving a trade on "5" (normalized to "M5")
        t = self.engine.create_predictive_order("XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0, custom_time_structure=5)
        self.assertEqual(t.custom_time_structure, "M5")

        # Reset contexts in-memory to trigger hydration
        self.engine.contexts = {}
        # Ensure we have only the saved trade in memory and load it back
        self.engine.trades = [t]
        self.engine._hydrate_contexts()

        # Verify that it is loaded into the canonical 'M5' context correctly
        flat_contexts = self.engine.contexts
        self.assertIn("XAUUSD_M5", flat_contexts)
        self.assertEqual(len(flat_contexts["XAUUSD_M5"].trades), 1)

    def test_trade_evidence_safety(self) -> None:
        """
        Regression tests for Phase 4:
        Verifies:
        - No crash when evidence=None, evidence={}, evidence=invalid type (e.g. string).
        - Correct lifecycle completion (hitting target) without interruption.
        - Persistence is fully functional and saved.
        """
        self.engine.contexts = {} # Reset
        self.engine.trades = [] # Reset trades in memory

        # 1. Create predictive orders with different evidence payloads (None, dict, invalid string)
        t_none = self.engine.create_predictive_order(
            "XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0,
            custom_time_structure=5, evidence=None
        )
        t_empty = self.engine.create_predictive_order(
            "XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0,
            custom_time_structure=5, evidence={}
        )
        t_invalid = self.engine.create_predictive_order(
            "XAUUSD", "LONG", 2000.0, 1990.0, 2020.0, 80.0,
            custom_time_structure=5, evidence="not_a_dict"
        )

        # Confirm evidence has been normalized to dictionary
        self.assertIsInstance(t_none.evidence, dict)
        self.assertIsInstance(t_empty.evidence, dict)
        self.assertIsInstance(t_invalid.evidence, dict)

        # 2. Trigger them
        self.engine.update_market_ticks("XAUUSD", 2001.0)
        self.assertEqual(t_none.status, "RUNNING")
        self.assertEqual(t_empty.status, "RUNNING")
        self.assertEqual(t_invalid.status, "RUNNING")

        # 3. Hit target to complete the lifecycle
        self.engine.update_market_ticks("XAUUSD", 2025.0)
        self.assertEqual(t_none.status, "TARGET_HIT")
        self.assertEqual(t_empty.status, "TARGET_HIT")
        self.assertEqual(t_invalid.status, "TARGET_HIT")

        # 4. Verify persistence works and does not get interrupted
        self.assertEqual(len(self.engine.trades), 3)
        # Verify that our trades list on disk can be loaded and read cleanly
        saved_trades = self.engine._load_trades()
        # Find saved records corresponding to these three trade IDs
        saved_ids = [st.trade_id for st in saved_trades]
        self.assertIn(t_none.trade_id, saved_ids)
        self.assertIn(t_empty.trade_id, saved_ids)
        self.assertIn(t_invalid.trade_id, saved_ids)

    def test_empty_runtime_telemetry(self) -> None:
        """
        Regression tests for Phase 6:
        Verifies that empty runtime state/memory system returns exactly zeros (no fake additives).
        """
        from src.Application.Services.web_dashboard import global_memory_system

        # Backup memory events & tables
        old_events = list(global_memory_system.events)
        old_patterns = dict(global_memory_system.patterns)
        old_concepts = dict(global_memory_system.concepts)

        try:
            # Clear memory system
            global_memory_system.events = []
            global_memory_system.patterns = {}
            global_memory_system.concepts = {}

            # Fetch intelligence status telemetry
            resp = self.client.get("/api/intelligence/status")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            # Verify they are strictly zero
            self.assertEqual(data["memory"], 0)
            self.assertEqual(data["patterns"], 0)
            self.assertEqual(data["concepts"], 0)

        finally:
            # Restore
            global_memory_system.events = old_events
            global_memory_system.patterns = old_patterns
            global_memory_system.concepts = old_concepts
