import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.content_manager import ContentManager
from src.Application.Dashboard.auth_service import global_auth_service
from src.Infrastructure.exceptions import ValidationException


class TestContentMarketingPhase15(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.manager = ContentManager(filepath="runtime_logs/test_content_p15.json")
        self.admin_user = {"email": "admin_p15@yartrader.app", "role": "ADMIN", "name": "SRE Admin"}
        self.admin_token = global_auth_service.create_session(self.admin_user)

    def tearDown(self) -> None:
        global_auth_service.active_sessions.pop(self.admin_token, None)
        if os.path.exists("runtime_logs/test_content_p15.json"):
            try:
                os.remove("runtime_logs/test_content_p15.json")
            except Exception:
                pass

    def test_1_valid_content_creation_succeeds(self) -> None:
        item = {
            "title": "Valid Article Title",
            "content": "Valid article content body text.",
            "category": "Algorithmic Research",
            "slug": "valid-article-title-unique",
            "published": True
        }
        res = self.manager.add_content_item("blog", item)
        self.assertEqual(res["title"], "Valid Article Title")
        self.assertTrue(res["id"].startswith("blog-"))

    def test_2_missing_title_raises_validation_exception(self) -> None:
        item = {"content": "Valid body text"}
        with self.assertRaises(ValidationException):
            self.manager.add_content_item("blog", item)

    def test_3_empty_title_raises_validation_exception(self) -> None:
        item = {"title": "", "content": "Valid body text"}
        with self.assertRaises(ValidationException):
            self.manager.add_content_item("blog", item)

    def test_4_whitespace_title_raises_validation_exception(self) -> None:
        item = {"title": "   \n\t ", "content": "Valid body text"}
        with self.assertRaises(ValidationException):
            self.manager.add_content_item("blog", item)

    def test_5_non_string_title_raises_validation_exception(self) -> None:
        item = {"title": 12345, "content": "Valid body text"}
        with self.assertRaises(ValidationException):
            self.manager.add_content_item("blog", item)

    def test_6_missing_content_raises_validation_exception(self) -> None:
        item = {"title": "Valid Title"}
        with self.assertRaises(ValidationException):
            self.manager.add_content_item("blog", item)

    def test_7_empty_content_raises_validation_exception(self) -> None:
        item = {"title": "Valid Title", "content": ""}
        with self.assertRaises(ValidationException):
            self.manager.add_content_item("blog", item)

    def test_8_whitespace_content_raises_validation_exception(self) -> None:
        item = {"title": "Valid Title", "content": "   "}
        with self.assertRaises(ValidationException):
            self.manager.add_content_item("blog", item)

    def test_9_non_string_content_raises_validation_exception(self) -> None:
        item = {"title": "Valid Title", "content": ["invalid", "list"]}
        with self.assertRaises(ValidationException):
            self.manager.add_content_item("blog", item)

    def test_10_duplicate_slug_same_domain_raises_validation_exception(self) -> None:
        item1 = {"title": "Article One", "content": "Body one", "slug": "shared-slug-test"}
        item2 = {"title": "Article Two", "content": "Body two", "slug": "shared-slug-test"}

        self.manager.add_content_item("blog", item1)
        with self.assertRaises(ValidationException):
            self.manager.add_content_item("blog", item2)

    def test_11_unique_slug_succeeds(self) -> None:
        item1 = {"title": "Article One", "content": "Body one", "slug": "slug-one"}
        item2 = {"title": "Article Two", "content": "Body two", "slug": "slug-two"}

        res1 = self.manager.add_content_item("blog", item1)
        res2 = self.manager.add_content_item("blog", item2)
        self.assertEqual(res1["slug"], "slug-one")
        self.assertEqual(res2["slug"], "slug-two")

    def test_12_admin_authorization_remains_enforced_via_api(self) -> None:
        invalid_payload = {
            "domain": "blog",
            "item": {"title": "", "content": ""}
        }
        # Admin request with invalid title/content raises 400
        res = self.client.post(f"/api/admin/content?token={self.admin_token}", json=invalid_payload)
        self.assertEqual(res.status_code, 400)

        # Unauthenticated request raises 401/403 under production env
        with patch.dict(os.environ, {"YARTRADER_ENV": "production"}):
            res_anon = self.client.post("/api/admin/content", json=invalid_payload)
            self.assertIn(res_anon.status_code, (401, 403))

    def test_13_existing_public_draft_protection_remains_enforced(self) -> None:
        import time
        unique_slug = f"draft-article-p15-{int(time.time() * 1000)}"
        draft_item = {
            "title": "Draft Article P15 Unique",
            "content": "Draft content body text.",
            "slug": unique_slug,
            "published": False
        }
        res_post = self.client.post(f"/api/admin/content?token={self.admin_token}", json={"domain": "blog", "item": draft_item})
        self.assertEqual(res_post.status_code, 200)

        # Public blog list excludes draft
        res_list = self.client.get("/api/blog")
        self.assertEqual(res_list.status_code, 200)
        self.assertFalse(any(a.get("slug") == unique_slug for a in res_list.json()))

        # Direct detail lookup by slug returns 404
        res_detail = self.client.get(f"/api/blog/{unique_slug}")
        self.assertEqual(res_detail.status_code, 404)


if __name__ == "__main__":
    unittest.main()
