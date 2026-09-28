import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, global_auth_service

class TestModernFeaturesIntegration(unittest.TestCase):
    """Customer authentication and public content integration tests."""

    def setUp(self) -> None:
        self.client = TestClient(app)
        global_auth_service.active_sessions = {}

    def test_social_login_google_only(self) -> None:
        google_payload = {
            "id_token": "mock_token_google_test-google@tradeyar.ai_google-12345_Google User",
            "email": "test-google@tradeyar.ai",
            "provider_id": "google-12345",
            "name": "Google User"
        }
        with patch.dict(os.environ, {"ALLOW_MOCK_AUTH": "true"}):
            resp = self.client.post("/api/auth/google", json=google_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "Success")
        self.assertIn("session_token", data)
        self.assertEqual(data["user"]["email"], "test-google@tradeyar.ai")
        self.assertEqual(data["user"]["role"], "USER")

        # Customer-facing non-Google providers remain unavailable.
        apple_payload = {
            "email": "test-apple@tradeyar.ai",
            "provider_id": "apple-67890",
            "name": "Apple User"
        }
        resp2 = self.client.post("/api/auth/apple", json=apple_payload)
        self.assertEqual(resp2.status_code, 404)

    def test_pristine_blog_endpoints(self) -> None:
        resp = self.client.get("/api/blog")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data), 2)
        article_1 = next((item for item in data if item["id"] == "1"), None)
        self.assertIsNotNone(article_1)
        self.assertEqual(article_1["title"], "Decoupling Market Reality: The Death of Classical Technical Indicators")

        resp2 = self.client.get("/api/blog/1")
        self.assertEqual(resp2.status_code, 200)
        art = resp2.json()
        self.assertEqual(art["author"], "Dr. Aras Noori")
        self.assertIn("Classical indicators like RSI", art["content"])

        resp3 = self.client.get("/api/blog/999")
        self.assertEqual(resp3.status_code, 404)

    def test_chatbot_assistant_is_not_exposed_by_yartrader(self) -> None:
        resp = self.client.post("/api/chat/assistant", json={"message": "چرا معامله باز کردی؟"})
        self.assertEqual(resp.status_code, 404)

    def test_retired_shadow_admin_route_is_closed(self) -> None:
        admin_token = global_auth_service.create_session({
            "email": "admin@yartrader.app",
            "role": "ADMIN",
            "name": "Admin"
        })
        response = self.client.get(
            "/api/admin/shadow-trades",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(response.status_code, 410)
