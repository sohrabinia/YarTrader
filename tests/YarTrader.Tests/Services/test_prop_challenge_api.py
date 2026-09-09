import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import global_auth_service
from src.Risk.Services.prop_challenge_engine import PropChallengeEngine, DISCLAIMER_TEXT

class TestPropChallengeAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.engine = PropChallengeEngine(config_filepath="test_runtime_logs/test_prop_config.json")

    def _create_session(self, email: str, role: str = "USER") -> str:
        user_obj = {"email": email.lower(), "role": role, "name": email.split("@")[0]}
        return global_auth_service.create_session(user_obj)

    def test_unconfigured_prop_challenge_status(self):
        """Verifies that unconfigured prop challenge returns NOT_CONFIGURED status."""
        response = self.client.get("/api/prop/challenge")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("disclaimer", data)
        self.assertEqual(data["disclaimer"], DISCLAIMER_TEXT)

    def test_update_and_get_configured_prop_challenge(self):
        """Verifies updating prop challenge configuration and retrieving active status."""
        config_payload = {
            "prop_firm_name": "FTMO Challenge",
            "account_number": "FTMO-99214",
            "account_size": 100000.0,
            "target_profit_pct": 10.0,
            "daily_loss_limit_pct": 5.0,
            "max_drawdown_pct": 10.0,
            "risk_per_trade_pct": 1.0,
            "max_exposure_pct": 3.0,
            "max_concurrent_positions": 3,
            "session_rules": "ALLOW_ALL_SESSIONS",
            "overnight_rule": "FLAT_BEFORE_CLOSE",
            "news_rule": "NO_NEW_ENTRIES_AROUND_HIGH_IMPACT"
        }

        post_res = self.client.post("/api/prop/config", json=config_payload)
        self.assertEqual(post_res.status_code, 200)
        post_data = post_res.json()
        self.assertEqual(post_data["status"], "Success")
        self.assertTrue(post_data["config"]["is_configured"])

        get_res = self.client.get("/api/prop/challenge?equity=98000&daily_pl=-1000")
        self.assertEqual(get_res.status_code, 200)
        status_data = get_res.json()
        self.assertTrue(status_data["is_configured"])
        self.assertIn(status_data["status"], ["CHALLENGE_READY", "NORMAL", "CAUTION", "DAILY_LIMIT_NEAR", "DRAWDOWN_NEAR", "TRADING_HALTED"])
        self.assertIsNotNone(status_data["metrics"])
        self.assertEqual(status_data["metrics"]["account_size"], 100000.0)
        self.assertEqual(status_data["metrics"]["remaining_daily_loss"], 4000.0)
        self.assertEqual(status_data["metrics"]["remaining_drawdown"], 8000.0)

    # --- CATALOG TESTS ---

    def test_catalog_loads(self):
        """Verifies catalog loads and returns presets."""
        presets = self.engine.get_presets_catalog()
        self.assertIsInstance(presets, list)
        self.assertGreater(len(presets), 0)

    def test_preset_ids_unique(self):
        """Verifies all preset IDs in the catalog are unique."""
        presets = self.engine.get_presets_catalog()
        preset_ids = [p["preset_id"] for p in presets]
        self.assertEqual(len(preset_ids), len(set(preset_ids)))

    def test_required_fields_and_provenance_exist(self):
        """Verifies required rule and provenance fields exist in all catalog presets."""
        presets = self.engine.get_presets_catalog()
        for p in presets:
            self.assertIn("preset_id", p)
            self.assertIn("display_name", p)
            self.assertIn("account_size", p)
            self.assertIn("target_profit_pct", p)
            self.assertIn("daily_loss_limit_pct", p)
            self.assertIn("max_drawdown_pct", p)
            self.assertIn("status", p)
            self.assertIn("source", p)
            self.assertIn("phases", p)
            self.assertTrue("retrieved_at" in p or "effective_at" in p)

    def test_preset_status_valid(self):
        """Verifies preset provenance status is valid."""
        presets = self.engine.get_presets_catalog()
        for p in presets:
            self.assertIn(p["status"], ["verified", "illustrative", "deprecated"])

    # --- VALIDATION TESTS ---

    def _sample_valid_preset(self):
        return {
            "preset_id": "test-valid-preset",
            "display_name": "Test Valid Preset",
            "account_size": 100000.0,
            "target_profit_pct": 10.0,
            "daily_loss_limit_pct": 5.0,
            "max_drawdown_pct": 10.0,
            "risk_per_trade_pct": 1.0,
            "max_exposure_pct": 3.0,
            "max_concurrent_positions": 3,
            "status": "illustrative",
            "source": "Test Suite Validation Reference",
            "retrieved_at": "2026-09-01T00:00:00Z"
        }

    def test_valid_preset_accepted(self):
        """Verifies a structurally valid preset definition is accepted."""
        preset = self._sample_valid_preset()
        validated = self.engine.validate_preset_definition(preset)
        self.assertEqual(validated["preset_id"], "test-valid-preset")

    def test_invalid_account_size_rejected(self):
        """Verifies non-positive account size is rejected."""
        preset = self._sample_valid_preset()
        preset["account_size"] = 0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        preset["account_size"] = -50000.0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        preset["account_size"] = True
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_invalid_percentages_rejected(self):
        """Verifies impossible percentages are rejected."""
        preset = self._sample_valid_preset()

        preset["target_profit_pct"] = 0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        preset["target_profit_pct"] = 150.0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        preset = self._sample_valid_preset()
        preset["daily_loss_limit_pct"] = -5.0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_invalid_drawdown_rejected(self):
        """Verifies invalid drawdown value is rejected."""
        preset = self._sample_valid_preset()
        preset["max_drawdown_pct"] = 0.0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        preset["max_drawdown_pct"] = 120.0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_invalid_exposure_rejected(self):
        """Verifies invalid exposure value is rejected."""
        preset = self._sample_valid_preset()
        preset["max_exposure_pct"] = -1.0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_malformed_preset_id_rejected(self):
        """Verifies malformed preset IDs are rejected."""
        preset = self._sample_valid_preset()

        preset["preset_id"] = ""
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        preset["preset_id"] = "invalid preset with spaces"
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        preset["preset_id"] = "invalid!id@specials"
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_missing_provenance_rejected(self):
        """Verifies missing mandatory provenance fields are rejected."""
        preset = self._sample_valid_preset()

        # Missing source
        preset["source"] = ""
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        # Invalid status
        preset = self._sample_valid_preset()
        preset["status"] = "unverified_status"
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        # Missing timestamp
        preset = self._sample_valid_preset()
        del preset["retrieved_at"]
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_contradictory_constraints_rejected(self):
        """Verifies contradictory risk constraints are rejected."""
        # Daily loss exceeds max drawdown limit
        preset = self._sample_valid_preset()
        preset["daily_loss_limit_pct"] = 12.0
        preset["max_drawdown_pct"] = 10.0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        # Risk per trade exceeds daily loss limit
        preset = self._sample_valid_preset()
        preset["risk_per_trade_pct"] = 6.0
        preset["daily_loss_limit_pct"] = 5.0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

        # Max exposure less than risk per trade
        preset = self._sample_valid_preset()
        preset["risk_per_trade_pct"] = 2.0
        preset["max_exposure_pct"] = 1.0
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    # --- MULTI-PHASE SPECIFIC TESTS ---

    def test_multi_phase_model_validation(self):
        """Verifies multi-phase preset validation with 2 phases."""
        preset = self._sample_valid_preset()
        preset["phases"] = [
            {
                "phase_id": "phase-1",
                "display_name": "Phase 1 - Evaluation",
                "phase_order": 1,
                "phase_type": "evaluation",
                "target_profit_pct": 10.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0,
                "min_trading_days": 4,
                "max_trading_days": 30
            },
            {
                "phase_id": "phase-2",
                "display_name": "Phase 2 - Verification",
                "phase_order": 2,
                "phase_type": "verification",
                "target_profit_pct": 5.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0,
                "min_trading_days": 4,
                "max_trading_days": 60
            }
        ]
        validated = self.engine.validate_preset_definition(preset)
        self.assertEqual(len(validated["phases"]), 2)
        self.assertEqual(validated["phases"][0]["phase_id"], "phase-1")
        self.assertEqual(validated["phases"][1]["phase_id"], "phase-2")

    def test_duplicate_phase_ids_rejected(self):
        """Verifies duplicate phase IDs within a preset are rejected."""
        preset = self._sample_valid_preset()
        preset["phases"] = [
            {
                "phase_id": "phase-1",
                "display_name": "Phase 1",
                "phase_order": 1,
                "target_profit_pct": 10.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0
            },
            {
                "phase_id": "phase-1",
                "display_name": "Duplicate Phase 1",
                "phase_order": 2,
                "target_profit_pct": 5.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0
            }
        ]
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_invalid_phase_ordering_rejected(self):
        """Verifies non-sequential or duplicate phase ordering is rejected."""
        preset = self._sample_valid_preset()
        preset["phases"] = [
            {
                "phase_id": "phase-1",
                "display_name": "Phase 1",
                "phase_order": 1,
                "target_profit_pct": 10.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0
            },
            {
                "phase_id": "phase-2",
                "display_name": "Phase 2",
                "phase_order": 3,
                "target_profit_pct": 5.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0
            }
        ]
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_invalid_trading_day_range_rejected(self):
        """Verifies max_trading_days < min_trading_days is rejected."""
        preset = self._sample_valid_preset()
        preset["phases"] = [
            {
                "phase_id": "phase-1",
                "display_name": "Phase 1",
                "phase_order": 1,
                "target_profit_pct": 10.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0,
                "min_trading_days": 10,
                "max_trading_days": 5
            }
        ]
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_contradictory_phase_rules_rejected(self):
        """Verifies contradictory risk rules inside a phase are rejected."""
        preset = self._sample_valid_preset()
        preset["phases"] = [
            {
                "phase_id": "phase-1",
                "display_name": "Phase 1",
                "phase_order": 1,
                "target_profit_pct": 10.0,
                "daily_loss_limit_pct": 15.0,
                "max_drawdown_pct": 10.0
            }
        ]
        with self.assertRaises(ValueError):
            self.engine.validate_preset_definition(preset)

    def test_single_phase_backward_compatibility(self):
        """Verifies single-phase preset without explicit 'phases' field gets converted to 1-phase list."""
        preset = self._sample_valid_preset()
        self.assertNotIn("phases", preset)
        validated = self.engine.validate_preset_definition(preset)
        self.assertIn("phases", validated)
        self.assertEqual(len(validated["phases"]), 1)
        self.assertEqual(validated["phases"][0]["phase_id"], "phase-1")
        self.assertEqual(validated["phases"][0]["target_profit_pct"], 10.0)

    def test_deterministic_phase_transitions(self):
        """Verifies deterministic phase evaluation status transitions."""
        phase = {
            "phase_id": "phase-1",
            "display_name": "Phase 1 - Evaluation",
            "phase_order": 1,
            "target_profit_pct": 10.0,
            "daily_loss_limit_pct": 5.0,
            "max_drawdown_pct": 10.0,
            "min_trading_days": 4
        }

        # Active state (profit 0%)
        res = self.engine.evaluate_phase_status(phase, equity=100000.0, account_size=100000.0, daily_pl=0.0, trading_days=0)
        self.assertEqual(res["status"], "ACTIVE")
        self.assertEqual(res["progress_pct"], 0.0)

        # Active state (target reached but min_trading_days not met)
        res_pending_days = self.engine.evaluate_phase_status(phase, equity=110000.0, account_size=100000.0, daily_pl=0.0, trading_days=2)
        self.assertEqual(res_pending_days["status"], "ACTIVE")
        self.assertEqual(res_pending_days["progress_pct"], 100.0)

        # Passed state (target reached and min_trading_days met)
        res_passed = self.engine.evaluate_phase_status(phase, equity=110000.0, account_size=100000.0, daily_pl=0.0, trading_days=4)
        self.assertEqual(res_passed["status"], "PASSED")
        self.assertEqual(res_passed["progress_pct"], 100.0)

        # Failed state (max drawdown exceeded)
        res_failed = self.engine.evaluate_phase_status(phase, equity=89000.0, account_size=100000.0, daily_pl=0.0, trading_days=1)
        self.assertEqual(res_failed["status"], "FAILED")

    # --- MULTI-ACCOUNT ISOLATION TESTS ---

    def test_multi_account_configuration_isolation(self):
        """Verifies configurations are strictly isolated per account ID."""
        self.engine.save_config({"prop_firm_name": "FTMO Challenge", "account_size": 100000.0}, account_id="user_alpha")
        self.engine.save_config({"prop_firm_name": "Funding Pips Challenge", "account_size": 50000.0}, account_id="user_beta")

        cfg_a = self.engine.load_config("user_alpha")
        cfg_b = self.engine.load_config("user_beta")

        self.assertEqual(cfg_a["prop_firm_name"], "FTMO Challenge")
        self.assertEqual(cfg_a["account_size"], 100000.0)

        self.assertEqual(cfg_b["prop_firm_name"], "Funding Pips Challenge")
        self.assertEqual(cfg_b["account_size"], 50000.0)

    def test_multi_account_trading_halt_isolation(self):
        """Verifies TRADING_HALTED state on one account does not halt another account."""
        self.engine.save_config({"account_size": 100000.0, "daily_loss_limit_pct": 5.0, "max_drawdown_pct": 10.0}, account_id="user_halted")
        self.engine.save_config({"account_size": 100000.0, "daily_loss_limit_pct": 5.0, "max_drawdown_pct": 10.0}, account_id="user_active")

        # Account A hits daily loss limit (-$6000 >= $5000 limit) -> TRADING_HALTED
        status_a = self.engine.get_status(live_equity=94000.0, live_daily_pl=-6000.0, account_id="user_halted")
        self.assertEqual(status_a["status"], "TRADING_HALTED")

        # Account B is within limits -> CHALLENGE_READY / NORMAL
        status_b = self.engine.get_status(live_equity=99500.0, live_daily_pl=-500.0, account_id="user_active")
        self.assertNotEqual(status_b["status"], "TRADING_HALTED")
        self.assertIn(status_b["status"], ["CHALLENGE_READY", "NORMAL"])

    def test_multi_account_phase_state_isolation(self):
        """Verifies active phase state is isolated between accounts."""
        self.engine.save_config({"active_phase_id": "phase-2", "trading_days": 5}, account_id="user_phase2")
        self.engine.save_config({"active_phase_id": "phase-1", "trading_days": 0}, account_id="user_phase1")

        cfg_a = self.engine.load_config("user_phase2")
        cfg_b = self.engine.load_config("user_phase1")

        self.assertEqual(cfg_a["active_phase_id"], "phase-2")
        self.assertEqual(cfg_a["trading_days"], 5)

        self.assertEqual(cfg_b["active_phase_id"], "phase-1")
        self.assertEqual(cfg_b["trading_days"], 0)

    # --- CTO MANDATED SECURITY TESTS (TEST A THROUGH TEST E) ---

    def test_security_a_own_account_access(self):
        """Test A: Authenticated User A accesses their own account state (200 OK)."""
        token_a = self._create_session("user_a@yartrader.app")
        headers = {"Authorization": f"Bearer {token_a}"}

        res = self.client.get("/api/prop/challenge", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["account_id"], "user_a@yartrader.app")

    def test_security_b_cross_account_read_forbidden(self):
        """Test B: Authenticated User A attempting to read User B's state gets HTTP 403."""
        token_a = self._create_session("user_a@yartrader.app")
        self._create_session("user_b@yartrader.app")
        headers = {"Authorization": f"Bearer {token_a}"}

        res = self.client.get("/api/prop/challenge?account_id=user_b@yartrader.app", headers=headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden", res.json()["detail"])

    def test_security_c_cross_account_write_forbidden(self):
        """Test C: Authenticated User A attempting to write User B's config gets HTTP 403 and User B remains unchanged."""
        token_a = self._create_session("user_a@yartrader.app")
        token_b = self._create_session("user_b@yartrader.app")

        # Save initial config for User B
        self.client.post("/api/prop/config", json={"account_size": 100000.0, "prop_firm_name": "Original User B Firm"}, headers={"Authorization": f"Bearer {token_b}"})

        # User A attempts to overwrite User B's config
        malicious_payload = {
            "account_id": "user_b@yartrader.app",
            "account_size": 50000.0,
            "prop_firm_name": "Hacked Firm Name"
        }
        res = self.client.post("/api/prop/config", json=malicious_payload, headers={"Authorization": f"Bearer {token_a}"})
        self.assertEqual(res.status_code, 403)

        # Verify User B's state remains strictly unchanged
        res_b = self.client.get("/api/prop/challenge", headers={"Authorization": f"Bearer {token_b}"})
        self.assertEqual(res_b.status_code, 200)
        self.assertEqual(res_b.json()["config"]["prop_firm_name"], "Original User B Firm")
        self.assertEqual(res_b.json()["config"]["account_size"], 100000.0)

    def test_security_d_unauthenticated_arbitrary_account_access_denied(self):
        """Test D: Request without valid authentication passing arbitrary account_id gets HTTP 401."""
        res_get = self.client.get("/api/prop/challenge?account_id=user_b@yartrader.app")
        self.assertEqual(res_get.status_code, 401)

        res_post = self.client.post("/api/prop/config", json={"account_id": "user_b@yartrader.app", "account_size": 50000.0})
        self.assertEqual(res_post.status_code, 401)

    def test_security_e_admin_cross_account_access_allowed(self):
        """Test E: Authenticated Admin accessing another account is permitted."""
        token_admin = self._create_session("admin@yartrader.app", role="ADMIN")
        token_b = self._create_session("user_b@yartrader.app")

        # Set User B config
        self.client.post("/api/prop/config", json={"account_size": 100000.0, "prop_firm_name": "User B Firm"}, headers={"Authorization": f"Bearer {token_b}"})

        # Admin reads User B state
        res_admin_get = self.client.get("/api/prop/challenge?account_id=user_b@yartrader.app", headers={"Authorization": f"Bearer {token_admin}"})
        self.assertEqual(res_admin_get.status_code, 200)
        self.assertEqual(res_admin_get.json()["account_id"], "user_b@yartrader.app")
        self.assertEqual(res_admin_get.json()["config"]["prop_firm_name"], "User B Firm")

    # --- API TESTS ---

    def test_get_presets_endpoint(self):
        """Verifies GET /api/prop/presets returns HTTP 200, valid schema, stable IDs, and multi-phase structure."""
        res = self.client.get("/api/prop/presets")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("presets", data)
        self.assertIn("total", data)
        self.assertGreater(data["total"], 0)
        self.assertEqual(len(data["presets"]), data["total"])

        for preset in data["presets"]:
            self.assertIn("preset_id", preset)
            self.assertIn("display_name", preset)
            self.assertIn("status", preset)
            self.assertIn("source", preset)
            self.assertIn("phases", preset)
            self.assertGreater(len(preset["phases"]), 0)
            self.assertIn(preset["status"], ["verified", "illustrative", "deprecated"])

    def test_get_presets_endpoint_is_read_only(self):
        """Verifies GET /api/prop/presets does not mutate configuration state."""
        status_before = self.client.get("/api/prop/challenge").json()
        self.client.get("/api/prop/presets")
        status_after = self.client.get("/api/prop/challenge").json()
        self.assertEqual(status_before, status_after)

if __name__ == "__main__":
    unittest.main()
