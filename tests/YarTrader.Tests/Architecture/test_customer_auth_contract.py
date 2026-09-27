"""Customer authentication contract regression tests."""

from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app


def test_customer_password_auth_is_disabled():
    client = TestClient(app)

    assert client.post("/api/auth/register", json={"email": "x@example.com", "password": "x"}).status_code == 410
    assert client.post("/api/auth/login", json={"email": "x@example.com", "password": "x"}).status_code == 410
    assert client.post("/api/auth/set-password", json={"password": "x"}).status_code == 410


def test_customer_auth_surface_is_google_only():
    client = TestClient(app)

    # Google is the only customer social-auth route exposed by the product.
    assert client.post("/api/auth/google", json={}).status_code == 400
    assert client.post("/api/auth/apple", json={}).status_code == 404
