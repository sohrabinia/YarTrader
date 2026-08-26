import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Risk.Services.prop_challenge_engine import PropChallengeEngine, PropChallengeState

class TestPropChallenge(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_engine_state_transitions(self):
        engine = PropChallengeEngine()
        self.assertEqual(engine.state, PropChallengeState.NOT_CONFIGURED)

        # Configure
        status = engine.configure({"account_size": 100000.0, "daily_loss_limit_pct": 5.0, "max_drawdown_pct": 10.0})
        self.assertEqual(status["state"], PropChallengeState.CHALLENGE_READY)

        # Update balance with minor loss
        status = engine.update_account_state(current_balance=98000.0, current_equity=98000.0)
        self.assertEqual(status["state"], PropChallengeState.NORMAL)

        # Update balance near daily limit (4.1% daily loss >= 80% of 5%)
        status = engine.update_account_state(current_balance=95800.0, current_equity=95800.0)
        self.assertEqual(status["state"], PropChallengeState.DAILY_LIMIT_NEAR)

        # Update balance breach daily limit (5.5% daily loss >= 5%)
        status = engine.update_account_state(current_balance=94500.0, current_equity=94500.0)
        self.assertEqual(status["state"], PropChallengeState.TRADING_HALTED)

    def test_trade_eligibility_validation(self):
        engine = PropChallengeEngine({"account_size": 50000.0, "risk_per_trade_pct": 1.0})
        engine.update_account_state(50000.0, 50000.0)

        # Valid trade risk ($400 <= $500 max allowed)
        eligibility = engine.validate_trade_eligibility(400.0)
        self.assertTrue(eligibility["allowed"])

        # Excessive risk ($600 > $500 max allowed)
        eligibility = engine.validate_trade_eligibility(600.0)
        self.assertFalse(eligibility["allowed"])

    def test_api_prop_endpoints(self):
        response = self.client.get("/api/prop/challenge")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("state", data)
        self.assertIn("disclaimer", data)

        # Post config update
        response = self.client.post("/api/prop/config", json={
            "account_size": 200000.0,
            "daily_loss_limit_pct": 4.0,
            "max_drawdown_pct": 8.0
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["state"], "CHALLENGE_READY")
        self.assertEqual(data["config"]["account_size"], 200000.0)

        # Post state update
        response = self.client.post("/api/prop/challenge", json={
            "current_balance": 198000.0,
            "current_equity": 198000.0,
            "active_positions": 1
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["metrics"]["active_positions"], 1)

if __name__ == "__main__":
    unittest.main()
