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
    res = client.post("/api/admin/content", json=payload)
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

    res_admin_status = client.post(f"/api/admin/tickets/{ticket_id}/status", json={"status": "RESOLVED"})
    assert res_admin_status.status_code == 200
    assert res_admin_status.json()["status"] == "RESOLVED"
