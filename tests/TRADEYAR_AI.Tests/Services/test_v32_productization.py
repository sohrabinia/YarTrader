import unittest
import os
import json
import uuid
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.database import SessionLocal, User, Role, UserPreference

class TestV32Productization(unittest.TestCase):
    """
    Quality Gate Test Suite validating all newly added TradeYar AI v3.2
    Enterprise Productization features: JWT, RBAC, i18n locales, and Blog CMS.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        # Clean up any leftover test users to keep tests 100% idempotent
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "test-researcher@tradeyar.ai").first()
            if user:
                # Delete references first
                db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
                db.delete(user)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def test_i18n_localization_dictionaries(self):
        """Verifies all 4 locale translation dictionaries exist, are valid JSON, and contain core keys."""
        locales = ["fa", "en", "ar", "tr"]
        for loc in locales:
            path = f"static/locales/{loc}.json"
            self.assertTrue(os.path.exists(path), f"Locale file {path} is missing!")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("title", data)
            self.assertIn("simulation_disclaimer", data)
            self.assertIn("cognitive_evidence_title", data)

    def test_e2e_user_registration_login_jwt_rbac(self):
        """Validates E2E user registration, login JWT token creation, and RBAC security gates."""
        # 1. Register a test User
        reg_email = "test-researcher@tradeyar.ai"
        reg_payload = {
            "email": reg_email,
            "password": "secure_password123",
            "role": "Researcher"
        }
        resp_reg = self.client.post("/api/v1/auth/register", json=reg_payload)
        self.assertEqual(resp_reg.status_code, 200)
        self.assertEqual(resp_reg.json()["status"], "Success")

        # 2. Login as the newly created User to get JWT
        login_payload = {
            "email": reg_email,
            "password": "secure_password123"
        }
        resp_login = self.client.post("/api/v1/auth/login", json=login_payload)
        self.assertEqual(resp_login.status_code, 200)
        login_data = resp_login.json()
        self.assertIn("access_token", login_data)
        self.assertEqual(login_data["role"], "Researcher")

        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Verify RBAC on standard endpoints (User preference reading/updating)
        resp_prefs = self.client.get("/api/v1/user/preferences", headers=headers)
        self.assertEqual(resp_prefs.status_code, 200)
        self.assertEqual(resp_prefs.json()["language"], "fa") # default

        # Update user preference
        update_payload = {"language": "en", "theme": "light"}
        resp_update = self.client.put("/api/v1/user/preferences", json=update_payload, headers=headers)
        self.assertEqual(resp_update.status_code, 200)
        self.assertEqual(resp_update.json()["status"], "Success")

        # Re-check updated preferences
        resp_prefs_new = self.client.get("/api/v1/user/preferences", headers=headers)
        self.assertEqual(resp_prefs_new.json()["language"], "en")

        # 4. Verify RBAC rejection on Admin Blog creation for Researcher role
        blog_payload = {
            "slug": "unauthorized-post",
            "title_json": {"en": "Hack Post"},
            "content_json": {"en": "Hack Content"}
        }
        resp_admin_err = self.client.post("/api/v1/admin/blog", json=blog_payload, headers=headers)
        self.assertEqual(resp_admin_err.status_code, 403) # Forbidden for Researcher role

    def test_token_refresh_lifecycle(self):
        """Verifies JWT Token Refresh functionality."""
        # Log in default Admin to get a token
        login_payload = {
            "email": "admin@tradeyar.ai",
            "password": "admin123"
        }
        resp_login = self.client.post("/api/v1/auth/login", json=login_payload)
        self.assertEqual(resp_login.status_code, 200)
        token = resp_login.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        resp_refresh = self.client.post("/api/v1/auth/refresh", headers=headers)
        self.assertEqual(resp_refresh.status_code, 200)
        self.assertIn("access_token", resp_refresh.json())

    def test_list_blog_articles(self):
        """Verifies any visitor can list blog articles."""
        resp = self.client.get("/api/v1/blog")
        self.assertEqual(resp.status_code, 200)
        articles = resp.json()
        self.assertIsInstance(articles, list)
        self.assertTrue(len(articles) > 0)
        self.assertEqual(articles[-1]["slug"], "tradeyar-cognitive-paradigm")
