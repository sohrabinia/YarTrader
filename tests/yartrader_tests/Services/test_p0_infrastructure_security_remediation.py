import os
import json
import uuid
import unittest
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.Application.Services.web_dashboard import app
from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.Application.Dashboard.auth_service import AuthService, LockoutAuditStore
from app.core.logging import _safe_extra, log_security, log_audit

class TestP0InfrastructureSecurityRemediation(unittest.TestCase):
    """
    Forensic SRE integration and regression test suite verifying Phase 0:
    1. Unified Authoritative Symbol Limit of 30.
    2. Dynamic limits loading and persistence.
    3. Proper role-based security boundaries.
    4. Advanced recursive sensitive field redaction and security audit trail coverage.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)
        # Setup unique temp files to prevent multi-threaded database overlap collisions
        self.temp_registry_file = f"runtime_logs/test_registry_{uuid.uuid4().hex}.json"
        self.temp_lockout_file = f"runtime_logs/test_lockout_{uuid.uuid4().hex}.json"

        # Override SymbolRegistry configuration paths safely
        self.patcher1 = patch("src.ShadowTrading.Engine.SymbolRegistry.REGISTRY_FILE", self.temp_registry_file)
        self.patcher1.start()

        # Clear or initialize the registry instance for clean state isolation
        SymbolRegistry._instance = None
        self.registry = SymbolRegistry.get_instance()
        self.registry.registry = {}
        self.registry.save_registry()

    def tearDown(self) -> None:
        self.patcher1.stop()
        SymbolRegistry._instance = None
        for f in [self.temp_registry_file, self.temp_lockout_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    # =========================================================================
    # OBJECTIVE A: UNIFY SYMBOL LIMIT
    # =========================================================================

    def test_authoritative_symbol_limit_is_exactly_30(self) -> None:
        """Verifies that the unified active symbol limit is exactly 30."""
        self.assertEqual(self.registry.max_symbols, 30)

    def test_register_symbols_below_and_at_ceiling(self) -> None:
        """Verifies that registering up to exactly 30 active symbols succeeds."""
        # 1. Register 29 symbols (below limit)
        for i in range(29):
            sym = f"SYM{i}"
            self.registry.register_symbol(sym, ["H1"])
            self.assertTrue(self.registry.get_all_registered()[sym]["active"])

        # 2. Register 30th symbol (exactly at limit)
        self.registry.register_symbol("SYM29", ["H1"])
        self.assertTrue(self.registry.get_all_registered()["SYM29"]["active"])

    def test_register_exceeding_ceiling_fails_safely(self) -> None:
        """Verifies that attempting to register the 31st active symbol fails with ValueError."""
        # 1. Register 30 symbols to reach the ceiling
        for i in range(30):
            sym = f"SYM{i}"
            self.registry.register_symbol(sym, ["H1"])

        # 2. Attempt to register 31st active symbol must throw ValueError
        with self.assertRaises(ValueError) as ctx:
            self.registry.register_symbol("SYM30", ["H1"])
        self.assertIn("Hard SRE limit reached", str(ctx.exception))

    def test_persistence_preserves_same_symbol_limit(self) -> None:
        """Verifies that symbol registry state persists cleanly and remains consistent on reload."""
        self.registry.register_symbol("EURUSD", ["H1", "H4"])
        self.assertTrue(os.path.exists(self.temp_registry_file))

        # Re-load registry from file
        SymbolRegistry._instance = None
        new_registry = SymbolRegistry.get_instance()
        self.assertEqual(new_registry.max_symbols, 30)
        self.assertIn("EURUSD", new_registry.get_all_registered())

    # =========================================================================
    # OBJECTIVE B: SECURITY & AUDIT LOGGING
    # =========================================================================

    def test_recursive_sensitive_fields_redaction_safeguards_credentials(self) -> None:
        """Verifies that any sensitive keys in metadata are recursively redacted to '[REDACTED]'."""
        payload = {
            "normal_field": "public_data",
            "password": "super-secret-password-123",
            "password_hash": "pbkdf2_sha256$100000$salt$abc",
            "token": "tkn-1234567890abcdef",
            "api_key": "sec-api-key-9988",
            "nested_dict": {
                "user_credentials": "my-credentials",
                "secret_info": "dont-log-this"
            },
            "nested_list": [
                {"private_key": "key-data"},
                "harmless_string"
            ]
        }

        sanitized = _safe_extra(payload)

        # 1. Public fields must be kept intact
        self.assertEqual(sanitized["normal_field"], "public_data")

        # 2. Direct sensitive keys must be redacted
        self.assertEqual(sanitized["password"], "[REDACTED]")
        self.assertEqual(sanitized["password_hash"], "[REDACTED]")
        self.assertEqual(sanitized["token"], "[REDACTED]")
        self.assertEqual(sanitized["api_key"], "[REDACTED]")

        # 3. Recursive nested dictionaries must be correctly redacted
        self.assertEqual(sanitized["nested_dict"]["user_credentials"], "[REDACTED]")
        self.assertEqual(sanitized["nested_dict"]["secret_info"], "[REDACTED]")

        # 4. Recursive nested lists must be correctly redacted
        self.assertEqual(sanitized["nested_list"][0]["private_key"], "[REDACTED]")
        self.assertEqual(sanitized["nested_list"][1], "harmless_string")

    # =========================================================================
    # OBJECTIVE C: ADMIN / USER SECURITY BOUNDARY
    # =========================================================================

    def test_anonymous_access_to_admin_endpoints_is_unauthorized(self) -> None:
        """Verifies that accessing administrative endpoints without a token fails closed in production-like environment."""
        with patch.dict(os.environ, {"YARTRADER_ENV": "production"}):
            # No token passed -> 401 Unauthorized
            response = self.client.get("/api/admin/symbols")
            self.assertEqual(response.status_code, 401)

    def test_standard_user_access_to_admin_endpoints_is_forbidden(self) -> None:
        """Verifies that accessing administrative endpoints with a standard user token is rejected with 403 Forbidden."""
        from src.Application.Dashboard.auth_service import global_auth_service
        user_session = {
            "email": "normal-trader@yartrader.app",
            "role": "USER",
            "name": "Trader",
            "tier": "FREE"
        }
        token = global_auth_service.create_session(user_session)

        try:
            # 1. Standard user token -> 403 Forbidden
            response = self.client.get(f"/api/admin/symbols?token={token}")
            self.assertEqual(response.status_code, 403)
            self.assertIn("Forbidden", response.json()["detail"])
        finally:
            global_auth_service.logout(token)

    def test_admin_user_has_full_privileged_access(self) -> None:
        """Verifies that an administrator user token has full authorized access (200 OK)."""
        from src.Application.Dashboard.auth_service import global_auth_service
        admin_session = {
            "email": "sre-admin@yartrader.app",
            "role": "ADMIN",
            "name": "Admin SRE",
            "tier": "INSTITUTIONAL"
        }
        token = global_auth_service.create_session(admin_session)

        try:
            # 1. Admin user token -> 200 OK
            response = self.client.get(f"/api/admin/symbols?token={token}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["max_limit"], 30)
        finally:
            global_auth_service.logout(token)
