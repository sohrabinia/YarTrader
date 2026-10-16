from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app, global_auth_service


def test_wallet_routes_enforce_user_and_admin_roles(monkeypatch):
    monkeypatch.setenv("YARTRADER_ENV", "production")
    client = TestClient(app)

    user_token = global_auth_service.create_session({
        "email": "wallet-user@example.com", "role": "USER", "tier": "FREE"
    })
    admin_token = global_auth_service.create_session({
        "email": "wallet-admin@example.com", "role": "ADMIN", "tier": "INSTITUTIONAL"
    })

    # User wallet is authenticated and receive-only.
    user_wallet = client.get("/api/user/wallet/receive", headers={"Authorization": f"Bearer {user_token}"})
    assert user_wallet.status_code == 200
    assert "networks" in user_wallet.json()

    # No token and a normal user token cannot read administrative wallet settings.
    no_auth = client.get("/api/admin/wallet/receive")
    assert no_auth.status_code in (401, 403)
    user_forbidden = client.get("/api/admin/wallet/receive", headers={"Authorization": f"Bearer {user_token}"})
    assert user_forbidden.status_code == 403

    # Admin can read settings; this is a GET and does not mutate wallet configuration.
    admin_ok = client.get("/api/admin/wallet/receive", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_ok.status_code == 200
    assert "networks" in admin_ok.json()
