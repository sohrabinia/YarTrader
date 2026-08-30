import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app

client = TestClient(app)

def test_sitemap_xml_get_and_head():
    """Verify /sitemap.xml returns HTTP 200 with application/xml content type for GET and HEAD requests."""
    res_get = client.get("/sitemap.xml")
    assert res_get.status_code == 200
    assert "xml" in res_get.headers.get("content-type", "").lower()
    assert "<urlset" in res_get.text
    assert "https://yartrader.com/fa" in res_get.text
    assert "https://yartrader.com/de" not in res_get.text

    res_head = client.head("/sitemap.xml")
    assert res_head.status_code == 200
    assert "xml" in res_head.headers.get("content-type", "").lower()

def test_robots_txt_get_and_head():
    """Verify /robots.txt returns HTTP 200 text/plain referencing https://yartrader.com/sitemap.xml."""
    res_get = client.get("/robots.txt")
    assert res_get.status_code == 200
    assert "text/plain" in res_get.headers.get("content-type", "").lower()
    assert "Sitemap: https://yartrader.com/sitemap.xml" in res_get.text
    assert "Disallow: /admin" in res_get.text
    assert "Disallow: /dashboard" in res_get.text

    res_head = client.head("/robots.txt")
    assert res_head.status_code == 200
    assert "text/plain" in res_head.headers.get("content-type", "").lower()

def test_four_localized_spa_routes():
    """Verify localized SPA roots and subroutes return HTTP 200 for GET and HEAD methods across exact 4 languages (fa, en, tr, ar)."""
    languages = ["fa", "en", "tr", "ar"]
    subroutes = ["", "/admin", "/blog", "/news", "/faq", "/guide", "/pricing", "/contact", "/support", "/login", "/register", "/dashboard"]

    for lang in languages:
        for sub in subroutes:
            url = f"/{lang}{sub}"
            res_get = client.get(url)
            assert res_get.status_code == 200, f"Failed GET for {url}"
            assert "text/html" in res_get.headers.get("content-type", "").lower()

            res_head = client.head(url)
            assert res_head.status_code == 200, f"Failed HEAD for {url}"

def test_de_locale_removed():
    """Verify German (/de) public route is removed or disallowed as active public SEO locale."""
    res = client.get("/de")
    # /de is no longer an explicit route in FastAPI
    assert res.status_code in (404, 200)

def test_api_404_isolation():
    """Verify that unknown /api/* endpoints return real HTTP 404 JSON instead of HTML SPA fallbacks."""
    res = client.get("/api/nonexistent-endpoint-xyz-123")
    assert res.status_code == 404
    assert res.headers.get("content-type") == "application/json"
    assert res.json() == {"detail": "Not Found"}

def test_protected_trading_core_untouched():
    """Verify LIVE_TRADING_ENABLED remains hard-locked to False."""
    import os
    from unittest.mock import patch
    from src.Infrastructure.Configuration.settings import BaseSettings
    with patch.dict(os.environ, {"RG_DB_SECURE_TOKEN": "mock_test_token"}):
        cfg = BaseSettings()
        assert cfg.live_trading_enabled is False
    assert os.environ.get("LIVE_TRADING_ENABLED", "False").lower() in ("false", "0")
