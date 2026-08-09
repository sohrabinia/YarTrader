import os
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.business_catalog_manager import BusinessCatalogManager
from src.Infrastructure.exceptions import ValidationException

@pytest.fixture
def temp_catalog_manager(tmp_path):
    """Fixture providing a clean, temporary isolated BusinessCatalogManager."""
    catalog_file = tmp_path / f"catalog_{uuid.uuid4().hex}.json"
    audit_file = tmp_path / f"audit_{uuid.uuid4().hex}.json"
    manager = BusinessCatalogManager(filepath=str(catalog_file), audit_filepath=str(audit_file))
    return manager

class TestBusinessCatalogSystem:
    """Forensic SRE verification test suite for YarTrader Business & Product Catalog."""

    def test_catalog_auto_seeding_and_legacy_compatibility(self, temp_catalog_manager):
        # 1. Verify auto-seeding on fresh start
        prods = temp_catalog_manager.list_products(include_invisible=True)
        assert len(prods) >= 7

        # Verify legacy plans are present
        free_plan = temp_catalog_manager.get_product("free")
        assert free_plan is not None
        assert free_plan["price"] == 0.0
        assert free_plan["status"] == "ACTIVE"
        assert free_plan["purchasable"] is True

        daily_plan = temp_catalog_manager.get_product("daily")
        assert daily_plan["price"] == 29.0
        assert daily_plan["category"] == "PLANS"

    def test_visibility_controls_filter_invisible_products(self, temp_catalog_manager):
        # Add a hidden draft product
        draft_prod = {
            "id": "enterprise-secret",
            "slug": "enterprise-secret",
            "name": "Secret Enterprise Plan",
            "short_description": "Under wraps.",
            "long_description": "Draft",
            "category": "ENTERPRISE",
            "product_type": "ENTERPRISE",
            "price": 9999.0,
            "currency": "USD",
            "billing_period": "annual",
            "features": [],
            "limits": {},
            "visible": False,
            "purchasable": False,
            "status": "DRAFT"
        }
        temp_catalog_manager.save_product(draft_prod)

        # Public listing must hide invisible/draft products
        visible_prods = temp_catalog_manager.list_products(include_invisible=False)
        assert not any(p["id"] == "enterprise-secret" for p in visible_prods)

        # Admin listing must include draft products
        all_prods = temp_catalog_manager.list_products(include_invisible=True)
        assert any(p["id"] == "enterprise-secret" for p in all_prods)

    def test_validation_rejects_invalid_price_and_states(self, temp_catalog_manager):
        # Reject negative prices
        invalid_prod = {
            "id": "broken-pricing",
            "slug": "broken-pricing",
            "name": "Free Money Plan",
            "short_description": "Invalid",
            "category": "PLANS",
            "product_type": "SUBSCRIPTION",
            "price": -10.0,  # Negative price violation!
            "currency": "USD",
            "status": "ACTIVE"
        }
        with pytest.raises(ValidationException, match="negative prices are strictly forbidden"):
            temp_catalog_manager.save_product(invalid_prod)

        # Reject COMING_SOON + purchasable combination
        invalid_combination = {
            "id": "premature-billing",
            "slug": "premature-billing",
            "name": "Upcoming System",
            "short_description": "Unvalidated",
            "category": "AI",
            "product_type": "COMING_SOON",
            "price": 49.0,
            "currency": "USD",
            "purchasable": True,  # Cannot sell unvalidated coming soon products!
            "status": "COMING_SOON"
        }
        with pytest.raises(ValidationException, match="cannot be both COMING_SOON and purchasable"):
            temp_catalog_manager.save_product(invalid_combination)

    def test_product_isolation_independent_mutations(self, temp_catalog_manager):
        # Mutating product A does not alter product B
        free = temp_catalog_manager.get_product("free")
        pro = temp_catalog_manager.get_product("pro")

        free["price"] = 5.0
        temp_catalog_manager.save_product(free)

        # Reload Pro and check unchanged
        reloaded_pro = temp_catalog_manager.get_product("pro")
        assert reloaded_pro["price"] == pro["price"]

    def test_direct_purchase_rejection_from_backend(self):
        client = TestClient(app)

        # Attempt to purchase an unvalidated, non-purchasable product ('prop-assistant' defaults to purchasable=False)
        payload = {
            "product_id": "prop-assistant",
            "email": "tester@yartrader.app"
        }
        response = client.post("/api/public/business/purchase", json=payload)
        assert response.status_code == 400
        assert "not available for purchase" in response.json()["detail"]

    def test_admin_authorization_gating(self):
        client = TestClient(app)

        # 1. Invalid token must be rejected with 403 Forbidden
        response = client.get("/api/admin/business/catalog?token=invalid_token")
        assert response.status_code == 403

        # 2. Regular user token must be forbidden
        from src.Application.Dashboard.auth_service import global_auth_service
        user_obj = {
            "email": "trader@yartrader.app",
            "role": "USER",
            "name": "Trader",
            "tier": "FREE"
        }
        token = global_auth_service.create_session(user_obj, "user-agent-test", "127.0.0.1")

        response = client.get(f"/api/admin/business/catalog?token={token}")
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

        # 3. Valid admin token must be allowed
        admin_obj = {
            "email": "admin@yartrader.app",
            "role": "ADMIN",
            "name": "Admin",
            "tier": "INSTITUTIONAL"
        }
        admin_token = global_auth_service.create_session(admin_obj, "user-agent-test", "127.0.0.1")
        response = client.get(f"/api/admin/business/catalog?token={admin_token}")
        assert response.status_code == 200
        assert len(response.json()) >= 7
