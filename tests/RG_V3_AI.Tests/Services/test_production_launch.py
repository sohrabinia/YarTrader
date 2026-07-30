import os
import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app, auth_repo, auth_service, payment_service_instance, seo_service_instance, support_ai_service, content_intelligence, email_service_instance, telegram_service_instance

@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    """Wipes the database and session store before and after each test for absolute isolation."""
    auth_repo.clear()
    auth_service._active_sessions.clear()
    # Pre-seed default admin
    auth_service.register_user("admin@tradeyar.ai", "AdminPassSecure!123", role="ADMIN")
    yield
    auth_repo.clear()
    auth_service._active_sessions.clear()

def test_auth_repository_and_cost_limits():
    """Validates persistent user registration, status storage, and daily AI cost limit tracking."""
    # Register user
    auth_service.register_user("user1@tradeyar.ai", "MyPassword123")
    user = auth_repo.get_user("user1@tradeyar.ai")
    assert user is not None
    assert user["email"] == "user1@tradeyar.ai"
    assert user["role"] == "USER"
    assert user["status"] == "ACTIVE"

    # AI request logs
    count1 = auth_repo.log_ai_request("user1@tradeyar.ai")
    assert count1 == 1
    count2 = auth_repo.log_ai_request("user1@tradeyar.ai")
    assert count2 == 2
    assert auth_repo.get_ai_request_count("user1@tradeyar.ai") == 2

def test_auth_service_password_hashing_and_recovery():
    """Validates secure PBKDF2 hashing security, constant-time compare verification, and recovery."""
    # Verify hashing
    h1 = auth_service._hash_password("SecPwd123")
    assert h1 != "SecPwd123"
    assert auth_service._verify_password("SecPwd123", h1) is True
    assert auth_service._verify_password("SecPwd124", h1) is False

    # Account recovery
    auth_service.register_user("recover@tradeyar.ai", "OldPass123")
    code = auth_service.generate_password_recovery_code("recover@tradeyar.ai")
    assert code is not None
    assert len(code) == 6

    # Reset password with code
    success = auth_service.reset_password_with_code("recover@tradeyar.ai", code, "NewSecretPass1")
    assert success is True
    token = auth_service.authenticate_user("recover@tradeyar.ai", "NewSecretPass1")
    assert token is not None

def test_billing_and_payment_referrals():
    """Validates payment crypto address generation, invoices, and invitation referral rewards."""
    email = "buyer@tradeyar.ai"
    payment_service_instance.register_referral("inviter@tradeyar.ai", email)

    tx = payment_service_instance.initiate_crypto_payment(email, "PRO", 29.99)
    assert tx["status"] == "PENDING"
    assert tx["amount"] == 29.99
    assert tx["plan_name"] == "PRO"
    assert "0x" in tx["wallet_address"]

    # Verify payment transaction
    verified = payment_service_instance.verify_payment_transaction(tx["tx_id"])
    assert verified is True

    # Check 10% referral credits rewarded back to inviter
    balance = payment_service_instance.get_referral_reward_balance("inviter@tradeyar.ai")
    assert balance == pytest.approx(2.999) # 29.99 * 10%

def test_seo_sitemap_xml():
    """Validates search-friendly HTML meta tags and multi-language XML sitemap compilation."""
    meta = seo_service_instance.generate_meta_tags("Home", "Description text", "en")
    assert "Home | TradeYar AI" in meta["title"]
    assert meta["robots"] == "index, follow"

    sitemap = seo_service_instance.generate_sitemap_xml()
    assert '<?xml version="1.0" encoding="UTF-8"?>' in sitemap
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in sitemap
    assert "https://tradeyar.ai/fa/dashboard" in sitemap
    assert "https://tradeyar.ai/disclaimer" in sitemap

def test_support_ai_faq_escalation():
    """Validates FAQ knowledge retrieval, conversational persistence threads, and escalation."""
    email = "help@tradeyar.ai"
    # EN FAQ trigger
    reply_en = support_ai_service.process_ai_query(email, "Tell me about risk", "en")
    assert "substantial loss" in reply_en or "Please check" in reply_en

    # FA FAQ trigger
    reply_fa = support_ai_service.process_ai_query(email, "قیمت چنده", "fa")
    assert "PRO" in reply_fa or "PREMIUM" in reply_fa

    # Persist chat history
    history = support_ai_service.get_conversation_history(email)
    assert len(history) == 4 # 2 query/response cycles

    # Escalate to admin
    support_ai_service.escalate_thread(email)
    assert support_ai_service.is_escalated(email) is True

def test_content_generation_multi_agent():
    """Validates Fact Check, Risk Check safety gates, translation, and SEO optimizations."""
    topic = "Fractal Waves"
    # Execute E2E generation pipeline
    res = content_intelligence.generate_and_publish_pipeline(topic, "blog", "fa")
    assert res["status"] == "PUBLISHED"
    assert "[ترجمه]" in res["title"]
    assert "Risk Disclosure" in res["body"] or "ریسک" in res["body"]

def test_web_auth_and_analysis_restrictions():
    """Validates registration, login, token authentication, and role based access limits."""
    # Use clean individual clients to prevent cookie leakage caching across separate user logins
    client_free = TestClient(app)
    client_admin = TestClient(app)

    # 1. Register USER (FREE)
    reg_res = client_free.post("/api/v1/auth/register", json={
        "email": "free@tradeyar.ai",
        "password": "FreeUserPassword1",
        "role": "USER"
    })
    assert reg_res.status_code == 200

    # 2. Secure Login to retrieve token
    login_res = client_free.post("/api/v1/auth/login", json={
        "email": "free@tradeyar.ai",
        "password": "FreeUserPassword1"
    })
    assert login_res.status_code == 200
    token = login_res.json()["token"]

    # 3. Request analysis under FREE user role -> technical metrics restricted
    headers = {"Authorization": f"Bearer {token}"}
    ana_res = client_free.get("/api/v1/analysis", headers=headers)
    assert ana_res.status_code == 200
    assert ana_res.json()["tier"] == "FREE"
    assert ana_res.json()["indicators"] == "RESTRICTED"

    # 4. Log in ADMIN and upgrade USER to PREMIUM role
    admin_login = client_admin.post("/api/v1/auth/login", json={
        "email": "admin@tradeyar.ai",
        "password": "AdminPassSecure!123"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    upgrade_res = client_admin.post("/api/v1/users/update-role", json={
        "email": "free@tradeyar.ai",
        "role": "PREMIUM"
    }, headers=admin_headers)
    assert upgrade_res.status_code == 200

    # 5. Re-query analysis under upgraded PREMIUM role using a fresh, clean client -> indicators now visible
    client_premium = TestClient(app)
    # Perform fresh login to clear cookie state and acquire session details correctly
    login_res_prem = client_premium.post("/api/v1/auth/login", json={
        "email": "free@tradeyar.ai",
        "password": "FreeUserPassword1"
    })
    token_prem = login_res_prem.json()["token"]
    prem_headers = {"Authorization": f"Bearer {token_prem}"}

    ana_up_res = client_premium.get("/api/v1/analysis", headers=prem_headers)
    assert ana_up_res.status_code == 200
    assert ana_up_res.json()["tier"] == "PREMIUM"
    assert ana_up_res.json()["indicators"] != "RESTRICTED"

def test_web_ai_cost_limits_protection():
    """Validates daily AI Support request rate limits (Cost Usage Control)."""
    client = TestClient(app)

    # Register FREE user
    client.post("/api/v1/auth/register", json={
        "email": "limit@tradeyar.ai",
        "password": "PasswordLimit123",
        "role": "USER"
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": "limit@tradeyar.ai",
        "password": "PasswordLimit123"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # FREE user limit is 10 requests. Trigger 10 times.
    for i in range(10):
        res = client.post("/api/v1/support/query", json={"query": "XAUUSD H1 trend", "language": "en"}, headers=headers)
        assert res.status_code == 200

    # 11th request must fail with 429 Too Many Requests to prevent API resource abuse
    res_fail = client.post("/api/v1/support/query", json={"query": "XAUUSD H1 trend", "language": "en"}, headers=headers)
    assert res_fail.status_code == 429
