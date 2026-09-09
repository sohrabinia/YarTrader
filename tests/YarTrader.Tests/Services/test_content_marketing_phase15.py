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

    def test_14_update_content_item_valid_succeeds(self) -> None:
        item = {"title": "Original Title", "content": "Original Content", "slug": "orig-slug", "published": True}
        created = self.manager.add_content_item("blog", item)

        updates = {"title": "Updated Title", "summary": "Updated Summary"}
        updated = self.manager.update_content_item("blog", created["id"], updates)

        self.assertEqual(updated["title"], "Updated Title")
        self.assertEqual(updated["summary"], "Updated Summary")
        self.assertEqual(updated["content"], "Original Content")  # Preserved
        self.assertEqual(updated["slug"], "orig-slug")  # Preserved

    def test_15_update_content_item_non_existent_raises_exception(self) -> None:
        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", "non-existent-id", {"title": "New Title"})

    def test_16_update_content_item_immutable_id_and_domain_rejected(self) -> None:
        item = {"title": "Immutable Test", "content": "Content Body"}
        created = self.manager.add_content_item("blog", item)

        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", created["id"], {"id": "different-id"})

        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", created["id"], {"domain": "news"})

    def test_17_update_content_item_invalid_title_or_content_rejected(self) -> None:
        item = {"title": "Title Test", "content": "Body Test"}
        created = self.manager.add_content_item("blog", item)

        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", created["id"], {"title": "   "})

        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", created["id"], {"content": ""})

    def test_18_update_content_item_same_slug_succeeds_duplicate_slug_rejected(self) -> None:
        item1 = {"title": "Article 1", "content": "Content 1", "slug": "slug-alpha"}
        item2 = {"title": "Article 2", "content": "Content 2", "slug": "slug-beta"}

        created1 = self.manager.add_content_item("blog", item1)
        created2 = self.manager.add_content_item("blog", item2)

        # Updating item1 with its own current slug succeeds
        up1 = self.manager.update_content_item("blog", created1["id"], {"slug": "slug-alpha", "title": "Article 1 Updated"})
        self.assertEqual(up1["title"], "Article 1 Updated")

        # Updating item1 to item2's slug raises ValidationException
        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", created1["id"], {"slug": "slug-beta"})

    def test_19_delete_content_item_succeeds_non_existent_raises(self) -> None:
        item = {"title": "To Be Deleted", "content": "Content to delete"}
        created = self.manager.add_content_item("blog", item)

        deleted = self.manager.delete_content_item("blog", created["id"])
        self.assertEqual(deleted["id"], created["id"])

        # Subsequent deletion raises ValidationException
        with self.assertRaises(ValidationException):
            self.manager.delete_content_item("blog", created["id"])

    def test_20_toggle_publish_status_semantics(self) -> None:
        item = {"title": "Toggle Article", "content": "Toggle Content", "slug": "toggle-slug", "published": True}
        created = self.manager.add_content_item("blog", item)

        # Unpublish -> False
        unpub = self.manager.toggle_publish_status("blog", created["id"], False)
        self.assertFalse(unpub["published"])

        # Publish -> True
        repub = self.manager.toggle_publish_status("blog", created["id"], True)
        self.assertTrue(repub["published"])

        # Non-boolean publication state raises ValidationException
        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", created["id"], {"published": "true"})

    def test_21_admin_update_delete_publish_api_endpoints_authorized_and_protected(self) -> None:
        # Create initial item via API
        item = {"title": "API Lifecycle Article", "content": "API Body", "slug": "api-lifecycle-slug", "published": False}
        res_create = self.client.post(f"/api/admin/content?token={self.admin_token}", json={"domain": "blog", "item": item})
        self.assertEqual(res_create.status_code, 200)
        item_id = res_create.json()["item"]["id"]

        # PUT Update via API with Admin token -> 200
        res_update = self.client.put(f"/api/admin/content/blog/{item_id}?token={self.admin_token}", json={"updates": {"title": "API Title Updated"}})
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.json()["item"]["title"], "API Title Updated")

        # POST Publish via API with Admin token -> 200
        res_pub = self.client.post(f"/api/admin/content/blog/{item_id}/publish?token={self.admin_token}", json={"published": True})
        self.assertEqual(res_pub.status_code, 200)
        self.assertTrue(res_pub.json()["item"]["published"])

        # Public list now includes published article
        res_list = self.client.get("/api/blog")
        self.assertEqual(res_list.status_code, 200)
        self.assertTrue(any(a.get("id") == item_id for a in res_list.json()))

        # DELETE via API with Admin token -> 200
        res_del = self.client.delete(f"/api/admin/content/blog/{item_id}?token={self.admin_token}")
        self.assertEqual(res_del.status_code, 200)

        # Subsequent PUT/DELETE returns 404
        res_del_404 = self.client.delete(f"/api/admin/content/blog/{item_id}?token={self.admin_token}")
        self.assertEqual(res_del_404.status_code, 404)

        # Unauthenticated endpoints fail closed under production
        with patch.dict(os.environ, {"YARTRADER_ENV": "production"}):
            res_put_anon = self.client.put(f"/api/admin/content/blog/{item_id}", json={"updates": {"title": "Hacked"}})
            self.assertIn(res_put_anon.status_code, (401, 403))

            res_del_anon = self.client.delete(f"/api/admin/content/blog/{item_id}")
            self.assertIn(res_del_anon.status_code, (401, 403))

            res_pub_anon = self.client.post(f"/api/admin/content/blog/{item_id}/publish", json={"published": True})
            self.assertIn(res_pub_anon.status_code, (401, 403))

    def test_22_update_content_item_unknown_fields_rejected(self) -> None:
        item = {"title": "Field Hardening Test", "content": "Field Hardening Body"}
        created = self.manager.add_content_item("blog", item)

        # Attempting to update with unknown fields raises ValidationException
        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", created["id"], {"title": "Valid Title", "is_admin": True})

        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", created["id"], {"title": "Valid Title", "random_field": "unexpected"})

    def test_23_update_content_item_published_none_rejected(self) -> None:
        item = {"title": "Published None Test", "content": "Body Text", "published": True}
        created = self.manager.add_content_item("blog", item)

        # Attempting to update published with None raises ValidationException
        with self.assertRaises(ValidationException):
            self.manager.update_content_item("blog", created["id"], {"published": None})

    def test_24_dynamic_sitemap_xml_validity_and_base_routes(self) -> None:
        import xml.etree.ElementTree as ET
        res = self.client.get("/sitemap.xml")
        self.assertEqual(res.status_code, 200)
        self.assertIn("application/xml", res.headers.get("content-type", ""))

        # Parse XML tree to verify structural validity
        root = ET.fromstring(res.text)
        sitemap_ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        locs = [loc.text.strip() for loc in root.findall(f".//{{{sitemap_ns}}}loc") if loc.text]

        # Verify base routes are present
        self.assertTrue(any("/pricing" in loc for loc in locs))
        self.assertTrue(any("/guide" in loc for loc in locs))
        self.assertTrue(any("/faq" in loc for loc in locs))

    def test_25_dynamic_sitemap_includes_published_articles_and_excludes_drafts(self) -> None:
        import xml.etree.ElementTree as ET
        import time

        pub_slug = f"sitemap-pub-{int(time.time() * 1000)}"
        draft_slug = f"sitemap-draft-{int(time.time() * 1000)}"

        pub_article = {"title": "Sitemap Published", "content": "Body", "slug": pub_slug, "published": True}
        draft_article = {"title": "Sitemap Draft", "content": "Body", "slug": draft_slug, "published": False}

        self.client.post(f"/api/admin/content?token={self.admin_token}", json={"domain": "blog", "item": pub_article})
        self.client.post(f"/api/admin/content?token={self.admin_token}", json={"domain": "blog", "item": draft_article})

        res = self.client.get("/sitemap.xml")
        self.assertEqual(res.status_code, 200)

        root = ET.fromstring(res.text)
        sitemap_ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        locs = [loc.text.strip() for loc in root.findall(f".//{{{sitemap_ns}}}loc") if loc.text]

        # Published article appears across locales
        self.assertTrue(any(f"/fa/blog/{pub_slug}" in loc for loc in locs))
        self.assertTrue(any(f"/en/blog/{pub_slug}" in loc for loc in locs))

        # Draft article does NOT appear
        self.assertFalse(any(draft_slug in loc for loc in locs))

    def test_26_dynamic_sitemap_excludes_non_boolean_publication_states(self) -> None:
        import xml.etree.ElementTree as ET
        import time

        fake_slug = f"sitemap-fake-{int(time.time() * 1000)}"
        fake_article = {"title": "Fake Published String", "content": "Body", "slug": fake_slug, "published": "true"}

        # Add item directly with string published state
        from src.Application.Services.web_dashboard import global_content_manager
        global_content_manager.data["blog"].append(fake_article)

        try:
            res = self.client.get("/sitemap.xml")
            self.assertEqual(res.status_code, 200)

            root = ET.fromstring(res.text)
            sitemap_ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
            locs = [loc.text.strip() for loc in root.findall(f".//{{{sitemap_ns}}}loc") if loc.text]

            # Non-boolean "true" string publication state is excluded
            self.assertFalse(any(fake_slug in loc for loc in locs))
        finally:
            global_content_manager.data["blog"] = [a for a in global_content_manager.data["blog"] if a.get("slug") != fake_slug]

    def test_27_dynamic_sitemap_escapes_xml_special_characters(self) -> None:
        import xml.etree.ElementTree as ET
        import time

        special_slug = f"sitemap-special-slug-{int(time.time() * 1000)}"
        special_article = {"title": "Special & Title <Test>", "content": "Body", "slug": special_slug, "published": True}

        self.client.post(f"/api/admin/content?token={self.admin_token}", json={"domain": "blog", "item": special_article})

        res = self.client.get("/sitemap.xml")
        self.assertEqual(res.status_code, 200)

        # Ensure returned text parses cleanly as valid XML without syntax errors
        root = ET.fromstring(res.text)
        sitemap_ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        locs = [loc.text.strip() for loc in root.findall(f".//{{{sitemap_ns}}}loc") if loc.text]

        self.assertTrue(any(special_slug in loc for loc in locs))


if __name__ == "__main__":
    unittest.main()
