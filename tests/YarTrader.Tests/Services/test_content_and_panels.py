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

def test_admin_content_creation():
    payload = {
        "domain": "blog",
        "item": {
            "title": "Test Blog Title",
            "category": "Testing",
            "summary": "Short summary",
            "content": "Full article content"
        }
    }
    from src.Application.Dashboard.auth_service import global_auth_service
    admin_token = global_auth_service.create_session({"email": "content-admin@yartrader.app", "role": "ADMIN"})
    res = client.post("/api/admin/content", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "Success"

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

    from src.Application.Dashboard.auth_service import global_auth_service
    admin_token = global_auth_service.create_session({"email": "admin@yartrader.app", "role": "ADMIN"})
    res_admin_status = client.post(f"/api/admin/tickets/{ticket_id}/status", json={"status": "RESOLVED"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin_status.status_code == 200
    assert res_admin_status.json()["status"] == "RESOLVED"


def test_legacy_ticket_routes_require_auth_and_use_session_identity():
    from src.Application.Dashboard.auth_service import global_auth_service
    from src.Application.Dashboard.ticket_manager import TicketManager

    # Production mode denies anonymous access; the request cannot choose an arbitrary email.
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {"YARTRADER_ENV": "production"}):
        assert client.get("/api/user/tickets").status_code == 401
        assert client.get("/api/user/tickets", headers={"Authorization": "Basic bad-token"}).status_code == 401
        assert client.post("/api/user/tickets", json={
            "subject": "unauthenticated", "category": "Support", "priority": "LOW", "message": "should be blocked"
        }).status_code == 401
        assert client.get("/api/admin/tickets").status_code == 401
        assert client.post("/api/admin/content", json={"domain": "blog", "item": {"title": "no auth"}}).status_code == 401

    user_email = "ticket-owner@yartrader.app"
    user_token = global_auth_service.create_session({"email": user_email, "role": "USER"})
    headers = {"Authorization": f"Bearer {user_token}"}
    created = client.post("/api/user/tickets?email=victim@yartrader.app", json={
        "subject": "private ticket", "category": "Support", "priority": "LOW", "message": "my issue"
    }, headers=headers)
    assert created.status_code == 200, created.text
    ticket_id = created.json()["ticket_id"]
    listed = client.get("/api/user/tickets?email=victim@yartrader.app", headers=headers)
    assert listed.status_code == 200
    assert all(ticket["email"] == user_email for ticket in listed.json())

    manager = TicketManager()
    other = manager.create_ticket("other-owner@yartrader.app", "other ticket", "Support", "LOW", "private")
    forbidden = client.post(f"/api/user/tickets/{other['ticket_id']}/reply", json={"message": "intrusion"}, headers=headers)
    assert forbidden.status_code in (400, 403)

    admin_token = global_auth_service.create_session({"email": "ticket-admin@yartrader.app", "role": "ADMIN"})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_list = client.get("/api/admin/tickets", headers=admin_headers)
    assert admin_list.status_code == 200
