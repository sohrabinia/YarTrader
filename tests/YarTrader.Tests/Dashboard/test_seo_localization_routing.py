import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app

client = TestClient(app)

class TestSeoLocalizationRouting:
    """Integration test suite for production SEO and localization routing truth gate."""

    @pytest.mark.parametrize("path", [
        "/",
        "/fa",
        "/en",
        "/tr",
        "/ar",
        "/fa/pricing",
        "/en/pricing",
        "/tr/pricing",
        "/ar/pricing",
        "/fa/features",
        "/en/guide",
        "/tr/faq",
        "/ar/blog",
    ])
    def test_localized_spa_routes_return_http_200(self, path):
        """Verifies that root and all localized SPA routes return HTTP 200 and valid HTML response for GET and HEAD."""
        get_resp = client.get(path)
        assert get_resp.status_code == 200, f"Expected GET 200 for {path}, got {get_resp.status_code}"
        assert "text/html" in get_resp.headers.get("content-type", "")
        assert "<!DOCTYPE html>" in get_resp.text or "<html" in get_resp.text

        head_resp = client.head(path)
        assert head_resp.status_code == 200, f"Expected HEAD 200 for {path}, got {head_resp.status_code}"
        assert "text/html" in head_resp.headers.get("content-type", "")

    def test_sitemap_endpoint_returns_valid_xml(self):
        """Verifies /sitemap.xml returns HTTP 200 with application/xml media type for GET and HEAD."""
        get_resp = client.get("/sitemap.xml")
        assert get_resp.status_code == 200
        assert "xml" in get_resp.headers.get("content-type", "")
        assert "yartrader.com" in get_resp.text

        head_resp = client.head("/sitemap.xml")
        assert head_resp.status_code == 200
        assert "xml" in head_resp.headers.get("content-type", "")

    def test_robots_endpoint_returns_valid_text(self):
        """Verifies /robots.txt returns HTTP 200 with text/plain media type for GET and HEAD."""
        get_resp = client.get("/robots.txt")
        assert get_resp.status_code == 200
        assert "text/plain" in get_resp.headers.get("content-type", "")
        assert "User-agent:" in get_resp.text or "Sitemap:" in get_resp.text

        head_resp = client.head("/robots.txt")
        assert head_resp.status_code == 200
        assert "text/plain" in head_resp.headers.get("content-type", "")

    def test_unhandled_api_routes_return_http_404(self):
        """Ensures that unknown /api/ endpoints return HTTP 404 and are not swallowed by SPA fallback."""
        response = client.get("/api/nonexistent_forensic_endpoint_12345")
        assert response.status_code == 404
