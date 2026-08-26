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

if __name__ == "__main__":
    unittest.main()
