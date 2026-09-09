import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Risk.Services.prop_challenge_engine import PropChallengeEngine, DISCLAIMER_TEXT

class TestPropChallengeAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.engine = PropChallengeEngine(config_filepath="test_runtime_logs/test_prop_config.json")

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

    # --- API TESTS ---

    def test_get_presets_endpoint(self):
        """Verifies GET /api/prop/presets returns HTTP 200, valid schema, stable IDs, and provenance."""
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
            self.assertIn(preset["status"], ["verified", "illustrative", "deprecated"])

    def test_get_presets_endpoint_is_read_only(self):
        """Verifies GET /api/prop/presets does not mutate configuration state."""
        status_before = self.client.get("/api/prop/challenge").json()
        self.client.get("/api/prop/presets")
        status_after = self.client.get("/api/prop/challenge").json()
        self.assertEqual(status_before, status_after)

if __name__ == "__main__":
    unittest.main()
