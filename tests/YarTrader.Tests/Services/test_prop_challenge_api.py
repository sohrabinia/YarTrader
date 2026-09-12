import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import global_auth_service
from src.Risk.Services.prop_challenge_engine import PropChallengeEngine, DISCLAIMER_TEXT

class TestPropChallengeAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.engine = PropChallengeEngine(config_filepath="test_runtime_logs/test_prop_config.json")

        # Create two distinct test users in auth repo
        self.user1 = {
            "email": "user1_prop@yartrader.app",
            "name": "Prop User One",
            "password_hash": global_auth_service.hash_password("Pass123!"),
            "role": "USER",
            "email_verified": True
        }
        self.user2 = {
            "email": "user2_prop@yartrader.app",
            "name": "Prop User Two",
            "password_hash": global_auth_service.hash_password("Pass123!"),
            "role": "USER",
            "email_verified": True
        }

        global_auth_service.repo.users[self.user1["email"]] = self.user1
        global_auth_service.repo.users[self.user2["email"]] = self.user2

        self.token_user1 = global_auth_service.create_session(self.user1)
        self.token_user2 = global_auth_service.create_session(self.user2)

    def test_anonymous_requests_are_rejected(self):
        """Verifies that anonymous GET and POST requests are rejected with 401 Unauthorized."""
        get_res = self.client.get("/api/prop/challenge")
        self.assertEqual(get_res.status_code, 401)
        self.assertIn("Authentication session token is required", get_res.json()["detail"])

        config_payload = {
            "prop_firm_name": "FTMO Challenge",
            "account_number": "FTMO-99214",
            "account_size": 100000.0
        }
        post_res = self.client.post("/api/prop/config", json=config_payload)
        self.assertEqual(post_res.status_code, 401)

    def test_user_isolation_and_authenticated_config(self):
        """Verifies updating prop challenge configuration under authenticated user identity."""
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

        headers_user1 = {"Authorization": f"Bearer {self.token_user1}"}
        headers_user2 = {"Authorization": f"Bearer {self.token_user2}"}

        # User 1 configures account
        post_res = self.client.post("/api/prop/config", json=config_payload, headers=headers_user1)
        self.assertEqual(post_res.status_code, 200)
        post_data = post_res.json()
        self.assertEqual(post_data["status"], "Success")
        self.assertTrue(post_data["config"]["is_configured"])
        self.assertEqual(post_data["config"]["owner_user_id"], self.user1["email"])

        # User 1 retrieves status
        get_res_1 = self.client.get(
            "/api/prop/challenge?simulated_equity=98000&simulated_daily_pl=-1000",
            headers=headers_user1
        )
        self.assertEqual(get_res_1.status_code, 200)
        status_data_1 = get_res_1.json()
        self.assertTrue(status_data_1["is_configured"])
        self.assertEqual(status_data_1["data_source"], "SIMULATION")
        self.assertEqual(status_data_1["metrics"]["account_size"], 100000.0)
        self.assertEqual(status_data_1["metrics"]["remaining_daily_loss"], 4000.0)

        # User 2 status remains unconfigured (isolated from User 1)
        get_res_2 = self.client.get("/api/prop/challenge", headers=headers_user2)
        self.assertEqual(get_res_2.status_code, 200)
        status_data_2 = get_res_2.json()
        self.assertFalse(status_data_2["is_configured"])
        self.assertEqual(status_data_2["status"], "NOT_CONFIGURED")

if __name__ == "__main__":
    unittest.main()
