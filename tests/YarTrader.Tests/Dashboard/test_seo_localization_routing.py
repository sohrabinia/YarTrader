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
        """Verifies that root and all localized SPA routes return HTTP 200 and valid HTML response."""
        response = client.get(path)
        assert response.status_code == 200, f"Expected 200 for {path}, got {response.status_code}"
        assert "text/html" in response.headers.get("content-type", "")
        assert "<!DOCTYPE html>" in response.text or "<html" in response.text

    def test_sitemap_endpoint_returns_valid_xml(self):
        """Verifies /sitemap.xml returns HTTP 200 with application/xml media type."""
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        assert "xml" in response.headers.get("content-type", "")
        assert "yartrader.com" in response.text

    def test_robots_endpoint_returns_valid_text(self):
        """Verifies /robots.txt returns HTTP 200 with text/plain media type."""
        response = client.get("/robots.txt")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        assert "User-agent:" in response.text or "Sitemap:" in response.text

    def test_unhandled_api_routes_return_http_404(self):
        """Ensures that unknown /api/ endpoints return HTTP 404 and are not swallowed by SPA fallback."""
        response = client.get("/api/nonexistent_forensic_endpoint_12345")
        assert response.status_code == 404
