import os
import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, global_auth_service

class TestModernFeaturesIntegration(unittest.TestCase):
    """
    Standard Engineering integration tests for YarTrader v3.2 new features.
    Verifies Social Auth callbacks, Role-based route guards, and AI chatbot reasoning.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)
        # Clear mock session states
        global_auth_service.active_sessions = {}

    def test_social_login_google_and_apple(self) -> None:
        # Test Google Auth
        google_payload = {
            "email": "test-google@tradeyar.ai",
            "provider_id": "google-12345",
            "name": "Google User"
        }
        resp = self.client.post("/api/auth/google", json=google_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "Success")
        self.assertIn("session_token", data)
        self.assertEqual(data["user"]["email"], "test-google@tradeyar.ai")
        self.assertEqual(data["user"]["role"], "USER")

        # Test Apple Auth
        apple_payload = {
            "email": "test-apple@tradeyar.ai",
            "provider_id": "apple-67890",
            "name": "Apple User"
        }
        resp2 = self.client.post("/api/auth/apple", json=apple_payload)
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(data2["status"], "Success")
        self.assertIn("session_token", data2)
        self.assertEqual(data2["user"]["email"], "test-apple@tradeyar.ai")

    def test_pristine_blog_endpoints(self) -> None:
        # List blog articles
        resp = self.client.get("/api/blog")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["title"], "Decoupling Market Reality: The Death of Classical Technical Indicators")

        # Retrieve specific article
        resp2 = self.client.get("/api/blog/1")
        self.assertEqual(resp2.status_code, 200)
        art = resp2.json()
        self.assertEqual(art["author"], "Dr. Aras Noori")
        self.assertIn("Classical indicators like RSI", art["content"])

        # Non-existing article
        resp3 = self.client.get("/api/blog/999")
        self.assertEqual(resp3.status_code, 404)

    def test_chatbot_assistant_explanations(self) -> None:
        # Test why open trade prompt
        prompt1 = {"message": "چرا معامله باز کردی؟"}
        resp1 = self.client.post("/api/chat/assistant", json=prompt1)
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertTrue("YarTrader" in data1["status"] or "YarTrader" in data1["status"])
        self.assertIn("تصمیم", data1["response"])

        # Test learn/cognitive prompt in English
        prompt2 = {"message": "What did you learn today?"}
        resp2 = self.client.post("/api/chat/assistant", json=prompt2)
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertIsNotNone(data2["response"])

    def test_jwt_admin_route_guards(self) -> None:
        # 1. Create a regular USER session
        user_data = {
            "email": "user@tradeyar.ai",
            "password_hash": "",
            "role": "USER",
            "name": "Standard Trader"
        }
        user_token = global_auth_service.create_session(user_data)

        # 2. Query admin endpoint with USER token (MUST be blocked with 403 Forbidden)
        resp1 = self.client.get(f"/api/admin/shadow-trades?token={user_token}")
        self.assertEqual(resp1.status_code, 403)
        self.assertEqual(resp1.json()["detail"], "Forbidden: Administrator privilege required")

        # 3. Create an ADMIN session
        admin_data = {
            "email": "admin@tradeyar.ai",
            "password_hash": "",
            "role": "ADMIN",
            "name": "Super Admin"
        }
        admin_token = global_auth_service.create_session(admin_data)

        # 4. Query admin endpoint with ADMIN token (MUST succeed with 200 OK)
        resp2 = self.client.get(f"/api/admin/shadow-trades?token={admin_token}")
        self.assertEqual(resp2.status_code, 200)
