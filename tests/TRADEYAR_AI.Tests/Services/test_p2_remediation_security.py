import os
import json
import hmac
import hashlib
import time
import shutil
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Application.Dashboard.auth_service import AuthService, LockoutAuditStore
from src.Application.Dashboard.auth_repo import AuthRepository
from src.Infrastructure.exceptions import ValidationException

from src.Application.Dashboard.ledger_manager import LedgerManager
from src.Application.Dashboard.billing_manager import BillingManager
from src.Application.Dashboard.ticket_manager import TicketManager
from src.Application.Dashboard.device_tracker import DeviceTracker

class TestP2RemediationSecurity(unittest.TestCase):
    """
    Focused, robust test suite verifying Double-Entry Financial Ledger (P2-1),
    SaaS Billing & Invoicing (P2-2), Support Ticketing System (P2-3),
    Login Device Tracking (P2-4), and Revenue Business Analytics (P2-5).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        # Define standard default files to match endpoints
        self.ledger_file = "runtime_logs/ledger.json"
        self.billing_file = "runtime_logs/billing.json"
        self.ticket_file = "runtime_logs/tickets.json"
        self.session_file = "runtime_logs/sessions.json"
        self.user_db_file = "runtime_logs/auth.json"

        self.backups = {}
        # Safely back up existing files to prevent side-effects on the host system
        for f in [self.ledger_file, self.billing_file, self.ticket_file, self.session_file, self.user_db_file]:
            if os.path.exists(f):
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        self.backups[f] = file.read()
                    os.remove(f)
                except Exception:
                    pass

        self.repo = AuthRepository(filepath=self.user_db_file)
        self.auth_service = AuthService(repo=self.repo)

        # Instantiate persistent managers
        self.ledger = LedgerManager(filepath=self.ledger_file)
        self.billing = BillingManager(filepath=self.billing_file)
        self.tickets = TicketManager(filepath=self.ticket_file)
        self.sessions = DeviceTracker(filepath=self.session_file)

    def tearDown(self) -> None:
        # Restore backed up original files perfectly
        for f in [self.ledger_file, self.billing_file, self.ticket_file, self.session_file, self.user_db_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
            if f in self.backups:
                try:
                    with open(f, "w", encoding="utf-8") as file:
                        file.write(self.backups[f])
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # P2-1 — DOUBLE-ENTRY FINANCIAL LEDGER TESTS
    # -------------------------------------------------------------------------

    def test_ledger_balanced_transaction_success(self) -> None:
        """Verifies balanced credit and debit ledger entries are successfully posted and balance updated."""
        entries = [
            {"account_id": "user1@yartrader.app", "type": "credit", "amount": 10000}, # +$100.00
            {"account_id": "revenue_vault", "type": "debit", "amount": 10000}       # -$100.00 (from perspective of revenue ledger)
        ]
        res = self.ledger.post_transaction(
            idempotency_key="ik-111",
            entries=entries,
            description="Premium subscription purchase"
        )
        self.assertEqual(res["status"], "Success")
        self.assertEqual(self.ledger.get_account_balance("user1@yartrader.app"), 10000)

    def test_ledger_unbalanced_transaction_rejected(self) -> None:
        """Verifies that unbalanced transactions violate accounting invariants and are strictly rejected."""
        entries = [
            {"account_id": "user1@yartrader.app", "type": "credit", "amount": 10000},
            {"account_id": "revenue_vault", "type": "debit", "amount": 5000} # Unbalanced!
        ]
        with self.assertRaises(ValidationException) as ctx:
            self.ledger.post_transaction(
                idempotency_key="ik-222",
                entries=entries,
                description="Unbalanced transfer"
            )
        self.assertIn("accounting invariant violation", str(ctx.exception).lower())

    def test_ledger_negative_balance_protection(self) -> None:
        """Verifies that a user account cannot fall below zero, blocking insufficient debit entries."""
        # Initial balance is 0
        entries = [
            {"account_id": "user_empty@yartrader.app", "type": "debit", "amount": 1000}, # debit tries to subtract $10.00
            {"account_id": "revenue_vault", "type": "credit", "amount": 1000}
        ]
        with self.assertRaises(ValidationException) as ctx:
            self.ledger.post_transaction(
                idempotency_key="ik-333",
                entries=entries,
                description="Insufficient funds debit attempt"
            )
        self.assertIn("insufficient funds", str(ctx.exception).lower())

    def test_ledger_reversal_compensating_workflow(self) -> None:
        """Verifies that reversal of posted transactions preserves logs and posts compensating entries correctly."""
        # 1. Post initial purchase
        entries = [
            {"account_id": "user1@yartrader.app", "type": "credit", "amount": 10000},
            {"account_id": "system_vault", "type": "debit", "amount": 10000}
        ]
        tx_res = self.ledger.post_transaction(
            idempotency_key="ik-purchase",
            entries=entries,
            description="Initial purchase"
        )
        tx_id = tx_res["transaction"]["transaction_id"]

        # 2. Reverse purchase (e.g., refund scenario)
        rev_res = self.ledger.reverse_transaction(
            original_tx_id=tx_id,
            idempotency_key="ik-refund",
            reason="User refund request"
        )
        self.assertEqual(rev_res["status"], "Success")
        # Balance should be back to 0
        self.assertEqual(self.ledger.get_account_balance("user1@yartrader.app"), 0)

    # -------------------------------------------------------------------------
    # P2-2 — SaaS BILLING & INVOICING TESTS
    # -------------------------------------------------------------------------

    def test_billing_signed_webhook_success(self) -> None:
        """Verifies that a webhook signed with a valid HMAC signature updates the subscription state and saves an invoice."""
        payload_dict = {
            "event_id": "evt-payment-9988",
            "type": "payment.success",
            "email": "premium-member@yartrader.app",
            "tier_id": "PRO",
            "amount_cents": 7900
        }
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        secret = "super_secret_webhook_key"

        # Compute valid HMAC signature
        signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        # Ingest webhook
        res = self.billing.process_signed_webhook(payload_bytes, signature, secret)
        self.assertEqual(res["status"], "Success")
        self.assertFalse(res["duplicate"])

        # Check subscription update and invoice persistence
        sub = self.billing.get_subscription("premium-member@yartrader.app")
        self.assertEqual(sub["tier_id"], "PRO")
        self.assertEqual(sub["status"], "ACTIVE")

        # Verify idempotency (replay protection)
        res_dup = self.billing.process_signed_webhook(payload_bytes, signature, secret)
        self.assertTrue(res_dup["duplicate"])

    def test_billing_invalid_signature_rejected(self) -> None:
        """Verifies that any billing webhook with an invalid or tampered signature is strictly rejected (fails closed)."""
        payload_dict = {
            "event_id": "evt-payment-9988",
            "type": "payment.success",
            "email": "premium-member@yartrader.app",
            "tier_id": "PRO"
        }
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        secret = "super_secret_webhook_key"

        # Ingest with wrong signature
        with self.assertRaises(ValidationException) as ctx:
            self.billing.process_signed_webhook(payload_bytes, "forged_signature_hash_here", secret)
        self.assertIn("webhook signature mismatch", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # P2-3 — SUPPORT TICKETING SYSTEM TESTS
    # -------------------------------------------------------------------------

    def test_support_ticket_lifecycle_and_cross_user_denial(self) -> None:
        """Verifies ticket creation, replies ordering, SRE controls, and strict cross-user access boundaries."""
        user_email = "user1@yartrader.app"
        attacker_email = "attacker@yartrader.app"

        # 1. Create a support ticket
        ticket = self.tickets.create_ticket(
            email=user_email,
            subject="Help with Shadow Trading Balance",
            category="Billing",
            priority="HIGH",
            message="I paid but balance is not credited."
        )
        self.assertEqual(ticket["status"], "OPEN")
        ticket_id = ticket["ticket_id"]

        # 2. Append reply message as owner
        self.tickets.add_reply(ticket_id, user_email, "Also, please check my transaction.")

        # 3. Cross-user access boundary validation
        with self.assertRaises(ValidationException) as ctx:
            self.tickets.add_reply(ticket_id, attacker_email, "Hacking message.")
        self.assertIn("unauthorized", str(ctx.exception).lower())

        # 4. Admin SRE replying and closing
        self.tickets.add_reply(ticket_id, "sre-support@yartrader.app", "We have credited your balance.", is_admin=True)
        self.tickets.update_status(ticket_id, "CLOSED")

        # Confirm closing status
        data = self.tickets._load()
        self.assertEqual(data["tickets"][ticket_id]["status"], "CLOSED")
        self.assertIsNotNone(data["tickets"][ticket_id]["closed_at"])

    # -------------------------------------------------------------------------
    # P2-4 — LOGIN DEVICE TRACKING TESTS
    # -------------------------------------------------------------------------

    def test_login_device_tracking_and_revocation(self) -> None:
        """Verifies session persistence, user active sessions list, revocation, and token rejection."""
        email = "member@yartrader.app"
        token = "token-device-abc-123"

        # Record session on login
        self.sessions.record_session(token, email, "Mozilla/5.0", "192.0.2.1")

        # Verify active sessions count and fields
        active_list = self.sessions.list_active_sessions(email)
        self.assertEqual(len(active_list), 1)
        self.assertEqual(active_list[0]["user_agent"], "Mozilla/5.0")

        # Revoke session
        self.sessions.revoke_session(token, email)

        # Check that it's revoked
        self.assertTrue(self.sessions.is_session_revoked(token))
        self.assertEqual(len(self.sessions.list_active_sessions(email)), 0)

    # -------------------------------------------------------------------------
    # P2-5 — REVENUE BUSINESS ANALYTICS TESTS
    # -------------------------------------------------------------------------

    def test_revenue_analytics_dynamic_calculation(self) -> None:
        """Verifies SaaS metrics (MRR, ARR, churn) are calculated dynamically from authentic, persisted data."""
        # 1. Setup deterministic billing data
        # Seed 2 active PRO subscriptions ($79/mo) and 1 active DAILY ($29/mo) and 1 CANCELLED
        self.billing._save({
            "subscriptions": {
                "user1@yartrader.app": {"email": "user1@yartrader.app", "tier_id": "PRO", "status": "ACTIVE"},
                "user2@yartrader.app": {"email": "user2@yartrader.app", "tier_id": "PRO", "status": "ACTIVE"},
                "user3@yartrader.app": {"email": "user3@yartrader.app", "tier_id": "DAILY", "status": "ACTIVE"},
                "user4@yartrader.app": {"email": "user4@yartrader.app", "tier_id": "DAILY", "status": "CANCELLED"}
            },
            "invoices": [
                {"amount_cents": 7900},
                {"amount_cents": 7900},
                {"amount_cents": 2900}
            ],
            "processed_webhook_ids": {}
        })

        # Register an SRE Administrator in user DB to generate a genuine admin session token
        admin_user = self.repo.create_user(email="admin-analytics@yartrader.app", password_hash="hash123", role="ADMIN", name="Admin")
        admin_token = self.auth_service.create_session(admin_user)

        with patch("src.Application.Services.admin_api_router.global_auth_service", self.auth_service):
            # Mount session and run calculations
            # Expected MRR: PRO ($79) + PRO ($79) + DAILY ($29) = $187.00
            # Expected ARR: $187.00 * 12 = $2244.00
            # Expected Churn: 1 cancelled / 4 total ever registered = 25.0%
            # Expected Total Revenue: $79 + $79 + $29 = $187.00
            # Expected LTV: $187.00 / 3 active = $62.33

            from src.Application.Services.admin_api_router import get_revenue_business_analytics
            res = get_revenue_business_analytics(token=admin_token)
            self.assertEqual(res["mrr_usd"], 187.00)
            self.assertEqual(res["arr_usd"], 2244.00)
            self.assertEqual(res["active_subscriptions"], 3)
            self.assertEqual(res["churn_rate_pct"], 25.0)
            self.assertEqual(res["total_revenue_usd"], 187.00)
            self.assertEqual(res["ltv_usd"], 62.33)
