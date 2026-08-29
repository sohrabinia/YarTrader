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

    res_head = client.head("/sitemap.xml")
    assert res_head.status_code == 200
    assert "xml" in res_head.headers.get("content-type", "").lower()

def test_robots_txt_get_and_head():
    """Verify /robots.txt returns HTTP 200 text/plain referencing https://yartrader.com/sitemap.xml."""
    res_get = client.get("/robots.txt")
    assert res_get.status_code == 200
    assert "text/plain" in res_get.headers.get("content-type", "").lower()
    assert "Sitemap: https://yartrader.com/sitemap.xml" in res_get.text

    res_head = client.head("/robots.txt")
    assert res_head.status_code == 200
    assert "text/plain" in res_head.headers.get("content-type", "").lower()

def test_localized_spa_routes():
    """Verify localized SPA roots and subroutes return HTTP 200 for GET and HEAD methods across all 5 languages."""
    languages = ["fa", "en", "tr", "ar", "de"]
    subroutes = ["", "/admin", "/blog", "/news", "/faq", "/guide", "/pricing", "/contact", "/support", "/login", "/register", "/dashboard"]

    for lang in languages:
        for sub in subroutes:
            url = f"/{lang}{sub}"
            res_get = client.get(url)
            assert res_get.status_code == 200, f"Failed GET for {url}"
            assert "text/html" in res_get.headers.get("content-type", "").lower()

            res_head = client.head(url)
            assert res_head.status_code == 200, f"Failed HEAD for {url}"

def test_api_404_isolation():
    """Verify that unknown /api/* endpoints return real HTTP 404 JSON instead of HTML SPA fallbacks."""
    res = client.get("/api/nonexistent-endpoint-xyz-123")
    assert res.status_code == 404
    assert res.headers.get("content-type") == "application/json"
    assert res.json() == {"detail": "Not Found"}
