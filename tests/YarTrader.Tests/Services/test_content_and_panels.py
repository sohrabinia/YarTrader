import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app

client = TestClient(app)

def test_blog_endpoints():
    res = client.get("/api/blog")
    assert res.status_code == 200
    articles = res.json()
    assert isinstance(articles, list)
    assert len(articles) > 0

    article_id = articles[0]["id"]
    res_detail = client.get(f"/api/blog/{article_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == article_id

def test_news_endpoints():
    res = client.get("/api/news")
    assert res.status_code == 200
    news_list = res.json()
    assert isinstance(news_list, list)
    assert len(news_list) > 0

    news_id = news_list[0]["id"]
    res_detail = client.get(f"/api/news/{news_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == news_id

def test_faq_and_guide_endpoints():
    res_faq = client.get("/api/faq")
    assert res_faq.status_code == 200
    assert isinstance(res_faq.json(), list)

    res_guide = client.get("/api/guide")
    assert res_guide.status_code == 200
    guides = res_guide.json()
    assert isinstance(guides, list)
    assert len(guides) > 0

    guide_id = guides[0]["id"]
    res_guide_detail = client.get(f"/api/guide/{guide_id}")
    assert res_guide_detail.status_code == 200
    assert res_guide_detail.json()["id"] == guide_id

def test_admin_content_creation_security_and_draft_protection():
    import os
    import time
    from unittest.mock import patch
    unique_suffix = int(time.time() * 1000)
    draft_id = f"draft-test-{unique_suffix}"
    draft_slug = f"unpublished-draft-article-{unique_suffix}"
    pub_id = f"pub-test-{unique_suffix}"
    pub_slug = f"published-article-test-{unique_suffix}"

    payload = {
        "domain": "blog",
        "item": {
            "id": draft_id,
            "title": "Unpublished Draft Article",
            "category": "Security Research",
            "summary": "Draft summary",
            "content": "Full draft article content",
            "slug": draft_slug,
            "published": False
        }
    }

    # Anonymous / unauthenticated POST rejected under production mode check
    with patch.dict(os.environ, {"YARTRADER_ENV": "production"}):
        res_anon = client.post("/api/admin/content", json=payload)
        assert res_anon.status_code in (401, 403)

    # Non-admin user session token rejected
    from src.Application.Dashboard.auth_service import global_auth_service
    user_token = "tkn-test-regular-user-token"
    global_auth_service.active_sessions[user_token] = {
        "email": "regular_user@yartrader.app",
        "role": "USER",
        "name": "Regular User"
    }
    try:
        res_user = client.post(f"/api/admin/content?token={user_token}", json=payload)
        assert res_user.status_code == 403
    finally:
        global_auth_service.active_sessions.pop(user_token, None)

    # Authorized Admin session token allowed via create_session()
    admin_user = {"email": "admin_user@yartrader.app", "role": "ADMIN", "name": "SRE Admin"}
    admin_token = global_auth_service.create_session(admin_user)
    try:
        res_admin = client.post(f"/api/admin/content?token={admin_token}", json=payload)
        assert res_admin.status_code == 200
        assert res_admin.json()["status"] == "Success"

        # 2. P1 Draft Protection Tests
        # Verify unpublished draft article is EXCLUDED from public GET /api/blog listing
        res_list = client.get("/api/blog")
        assert res_list.status_code == 200
        public_articles = res_list.json()
        assert not any(a.get("id") == draft_id for a in public_articles)

        # Verify direct ID lookup for unpublished draft fails with 404
        res_id = client.get(f"/api/blog/{draft_id}")
        assert res_id.status_code == 404

        # Verify direct slug lookup for unpublished draft fails with 404
        res_slug = client.get(f"/api/blog/{draft_slug}")
        assert res_slug.status_code == 404

        # 3. Verify Published Article Access
        published_payload = {
            "domain": "blog",
            "item": {
                "id": pub_id,
                "title": "Published Article Test",
                "category": "Public Research",
                "summary": "Public summary",
                "content": "Public article body content",
                "slug": pub_slug,
                "published": True
            }
        }
        res_pub_post = client.post(f"/api/admin/content?token={admin_token}", json=published_payload)
        assert res_pub_post.status_code == 200

        res_pub_list = client.get("/api/blog")
        assert res_pub_list.status_code == 200
        assert any(a.get("id") == pub_id for a in res_pub_list.json())

        res_pub_id = client.get(f"/api/blog/{pub_id}")
        assert res_pub_id.status_code == 200
        assert res_pub_id.json()["id"] == pub_id

        res_pub_slug = client.get(f"/api/blog/{pub_slug}")
        assert res_pub_slug.status_code == 200
        assert res_pub_slug.json()["slug"] == pub_slug

        # 4. Strict Publication Semantics Micro-Gate Tests
        # published=None, missing published, published="true" string
        for idx, p_val in enumerate([None, "MISSING_KEY", "true"]):
            p_id = f"mg-test-{idx}-{unique_suffix}"
            p_slug = f"mg-slug-{idx}-{unique_suffix}"
            item_payload = {
                "id": p_id,
                "title": f"Test Article {idx}",
                "category": "MicroGate",
                "summary": "Summary",
                "content": "Body",
                "slug": p_slug
            }
            if p_val != "MISSING_KEY":
                item_payload["published"] = p_val

            res_post = client.post(f"/api/admin/content?token={admin_token}", json={"domain": "blog", "item": item_payload})
            assert res_post.status_code == 200

            # Must be EXCLUDED from public blog list
            res_list_check = client.get("/api/blog")
            assert res_list_check.status_code == 200
            assert not any(a.get("id") == p_id for a in res_list_check.json())

            # Direct ID and slug lookup MUST return HTTP 404
            assert client.get(f"/api/blog/{p_id}").status_code == 404
            assert client.get(f"/api/blog/{p_slug}").status_code == 404

    finally:
        global_auth_service.active_sessions.pop(admin_token, None)

def test_user_ticket_lifecycle():
    from src.Application.Dashboard.ticket_manager import TicketManager
    manager = TicketManager()

    # 1. Create ticket via manager
    ticket = manager.create_ticket(
        email="trader_test@yartrader.app",
        subject="Billing issue test",
        category="Billing",
        priority="HIGH",
        message="Need help with invoice."
    )
    ticket_id = ticket["ticket_id"]
    assert ticket_id.startswith("tick-")

    # 2. List user tickets
    user_tickets = manager.list_user_tickets("trader_test@yartrader.app")
    assert len(user_tickets) >= 1
    assert user_tickets[0]["ticket_id"] == ticket_id

    # 3. Reply to ticket
    updated = manager.add_reply(ticket_id=ticket_id, email="trader_test@yartrader.app", message="Adding more info.")
    assert len(updated["messages"]) == 2

    # 4. Admin list & update status
    all_tickets = manager.list_all_tickets_admin()
    assert len(all_tickets) >= 1

    res_admin_status = client.post(f"/api/admin/tickets/{ticket_id}/status", json={"status": "RESOLVED"})
    assert res_admin_status.status_code == 200
    assert res_admin_status.json()["status"] == "RESOLVED"
