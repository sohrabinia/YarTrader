import os
import json
import hmac
import hashlib
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.Infrastructure.exceptions import ValidationException

class BillingManager:
    """
    SaaS Billing and Invoicing state machine.
    Handles user subscription updates, immutable invoices, plans management,
    and secure, signed, idempotent payment webhooks.
    """
    def __init__(self, filepath: str = "runtime_logs/billing.json") -> None:
        self.filepath = filepath
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        with self.lock:
            if not os.path.exists(self.filepath):
                self._save({
                    "subscriptions": {},
                    "invoices": [],
                    "processed_webhook_ids": {}
                })

    def _load(self) -> Dict[str, Any]:
        with self.lock:
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {"subscriptions": {}, "invoices": [], "processed_webhook_ids": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        with self.lock:
            tmp_file = self.filepath + ".tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                os.replace(tmp_file, self.filepath)
            except Exception:
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass

    def get_subscription(self, email: str) -> Dict[str, Any]:
        with self.lock:
            data = self._load()
            return data.get("subscriptions", {}).get(email.lower(), {
                "email": email.lower(),
                "tier_id": "FREE",
                "status": "INACTIVE",
                "renewal_date": None,
                "updated_at": None
            })

    def process_signed_webhook(self, payload_bytes: bytes, signature: str, webhook_secret: str) -> Dict[str, Any]:
        """
        Securely verifies payment webhook signatures, checks idempotency keys,
        and triggers subscription tier adjustments. Fails closed on any invalidity.
        """
        # 1. Signature Verification (HMAC-SHA256)
        if not signature or not webhook_secret:
            raise ValidationException("Missing secure webhook signature parameters.")

        expected_sig = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            raise ValidationException("Invalid webhook signature: webhook signature mismatch.")

        # 2. Parse and validate payload
        try:
            payload = json.loads(payload_bytes.decode('utf-8'))
        except Exception:
            raise ValidationException("Malformed JSON webhook payload.")

        event_id = payload.get("event_id")
        event_type = payload.get("type")
        if not event_id or not event_type:
            raise ValidationException("Webhook payload missing required parameters: event_id and type.")

        with self.lock:
            data = self._load()

            # Idempotency / Replay protection
            if event_id in data.get("processed_webhook_ids", {}):
                return {"status": "Success", "duplicate": True, "message": "Webhook already processed."}

            email = payload.get("email", "").lower()
            tier_id = payload.get("tier_id", "FREE").upper()
            amount_cents = payload.get("amount_cents", 0)

            if event_type == "payment.success":
                # Create immutable invoice record
                invoice_id = f"inv-{secrets_token()}"
                invoice = {
                    "invoice_id": invoice_id,
                    "email": email,
                    "tier_id": tier_id,
                    "amount_cents": amount_cents,
                    "status": "PAID",
                    "payment_reference": f"pay-ref-{event_id}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                data["invoices"].append(invoice)

                # Update subscription state
                data["subscriptions"][email] = {
                    "email": email,
                    "tier_id": tier_id,
                    "status": "ACTIVE",
                    "renewal_date": (datetime.now(timezone.utc).timestamp() + 30*86400), # 30 days renewal
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

                # Securely sync tier with AuthRepository
                try:
                    from src.Application.Dashboard.auth_service import global_auth_service
                    repo = global_auth_service.repo
                    user = repo.get_user_by_email(email)
                    if user:
                        user["tier"] = tier_id
                        repo.users[email] = user
                        repo.save_db()
                except Exception:
                    pass

            elif event_type == "subscription.cancelled":
                # Mark as cancelled/inactive
                if email in data["subscriptions"]:
                    data["subscriptions"][email]["status"] = "CANCELLED"
                    data["subscriptions"][email]["updated_at"] = datetime.now(timezone.utc).isoformat()

                    try:
                        from src.Application.Dashboard.auth_service import global_auth_service
                        repo = global_auth_service.repo
                        user = repo.get_user_by_email(email)
                        if user:
                            user["tier"] = "FREE" # downgraded to FREE on cancellation
                            repo.users[email] = user
                            repo.save_db()
                    except Exception:
                        pass

            data["processed_webhook_ids"][event_id] = time.time()
            self._save(data)
            return {"status": "Success", "duplicate": False, "message": "Event processed successfully."}

def secrets_token() -> str:
    import secrets
    return secrets.token_hex(12)
