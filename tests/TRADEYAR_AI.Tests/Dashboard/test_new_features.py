import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app

client = TestClient(app)

def test_get_blog_articles_list():
    """Verifies that the /api/blog endpoint returns a non-empty list of mock articles."""
    response = client.get("/api/blog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert "article_id" in data[0]
    assert "title" in data[0]
    assert "content" in data[0]

def test_get_blog_article_by_id():
    """Verifies that /api/blog/{article_id} retrieves details, and invalid returns 404."""
    # Successful fetch
    response = client.get("/api/blog/art-001")
    assert response.status_code == 200
    data = response.json()
    assert data["article_id"] == "art-001"
    assert "طلا" in data["title"] or "Gold" in data["title"] or "طلا" in data["content"] or "Gold" in data["content"] or "XAUUSD" in data["title"]

    # Fails with 404 on invalid id
    fail_response = client.get("/api/blog/art-invalid-999")
    assert fail_response.status_code == 404
    assert fail_response.json()["detail"] == "Article not found"

def test_generate_blog_article():
    """Verifies that /api/blog/generate builds and appends a new draft article successfully."""
    response = client.post("/api/blog/generate")
    assert response.status_code == 200
    data = response.json()
    assert "art-" in data["article_id"]
    assert "سوگیری" in data["title"] or "bias" in data["title"] or "اطمینان" in data["title"] or "confidence" in data["title"] or "هوش" in data["title"]
    assert "TradeYar AI Generator" == data["author"]

    # Check list has grown
    list_response = client.get("/api/blog")
    assert list_response.status_code == 200
    articles = list_response.json()
    assert articles[0]["article_id"] == data["article_id"]

def test_chat_assistant_xauusd_analysis():
    """Verifies chatbot outputs golden research analysis details and supports Farsi/English."""
    # Farsi query
    payload = {"message": "تحلیل طلا"}
    response = client.post("/api/chat/assistant", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "language" in data
    assert data["language"] == "fa"
    assert "XAUUSD" in data["reply"] or "طلا" in data["reply"]

    # English query
    payload_en = {"message": "gold analysis"}
    response_en = client.post("/api/chat/assistant", json=payload_en)
    assert response_en.status_code == 200
    data_en = response_en.json()
    assert data_en["language"] == "en"
    assert "XAUUSD" in data_en["reply"] or "Gold" in data_en["reply"] or "gold" in data_en["reply"]

def test_chat_assistant_portfolio_status():
    """Verifies chatbot handles shadow portfolio positions query under APES-FIN simulation rules."""
    payload = {"message": "وضعیت معامله‌های باز"}
    response = client.post("/api/chat/assistant", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "Shadow" in data["reply"] or "فرضی" in data["reply"] or "پرتفوی" in data["reply"] or "معامله" in data["reply"]

def test_chat_assistant_learning():
    """Verifies chatbot handles brain cognitive loop learn queries correctly."""
    payload = {"message": "الگوهای مغز سیستم چیست؟"}
    response = client.post("/api/chat/assistant", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "یادگیری" in data["reply"] or "مغز" in data["reply"] or "cognitive" in data["reply"] or "learning" in data["reply"] or "الگو" in data["reply"]

def test_chat_assistant_default():
    """Verifies chatbot handles generic greetings with safe read-only orientation info."""
    payload = {"message": "hello there"}
    response = client.post("/api/chat/assistant", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "TradeYar" in data["reply"] or "assistant" in data["reply"] or "دستیار" in data["reply"]
