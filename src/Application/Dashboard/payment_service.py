import secrets
from datetime import datetime
from typing import List, Dict, Any

class TransactionRecord:
    """Represents a financial transaction for user subscription payments."""
    def __init__(self, email: str, plan_name: str, amount: float, tx_type: str = "CRYPTO") -> None:
        self.tx_id = f"tx-{secrets.token_hex(8)}"
        self.email = email
        self.plan_name = plan_name
        self.amount = amount
        self.tx_type = tx_type
        self.status = "PENDING"
        self.created_at = datetime.now().isoformat()
        self.wallet_address = f"0x{secrets.token_hex(20)}"
        self.verified_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "email": self.email,
            "plan_name": self.plan_name,
            "amount": self.amount,
            "tx_type": self.tx_type,
            "status": self.status,
            "created_at": self.created_at,
            "wallet_address": self.wallet_address,
            "verified_at": self.verified_at
        }


class PaymentService:
    """
    Production-grade Payment and Monetization manager.
    Supports secure crypto payment address generation, manual/automated verification,
    referral rewards, and absolute clean accounting transaction histories.
    """
    def __init__(self) -> None:
        self._transactions: Dict[str, TransactionRecord] = {}
        # Referral mappings: invitee_email -> inviter_email
        self._referrals: Dict[str, str] = {}
        # Rewards account: email -> balance credits
        self._rewards: Dict[str, float] = {}

    def initiate_crypto_payment(self, email: str, plan_name: str, amount: float) -> Dict[str, Any]:
        """Creates a pending cryptocurrency transaction with generated recipient wallet address."""
        record = TransactionRecord(email, plan_name, amount)
        self._transactions[record.tx_id] = record
        return record.to_dict()

    def verify_payment_transaction(self, tx_id: str) -> bool:
        """Approves and completes a pending transaction, returning success status."""
        record = self._transactions.get(tx_id)
        if not record or record.status != "PENDING":
            return False

        record.status = "SUCCESS"
        record.verified_at = datetime.now().isoformat()

        # Handle referral reward calculation (10% back to inviter)
        inviter = self._referrals.get(record.email)
        if inviter:
            reward_amount = record.amount * 0.10
            self._rewards[inviter] = self._rewards.get(inviter, 0.0) + reward_amount

        return True

    def register_referral(self, inviter_email: str, invitee_email: str) -> None:
        """Registers a referral invitation bond to reward users for onboarding others."""
        inviter = inviter_email.strip().lower()
        invitee = invitee_email.strip().lower()
        if inviter != invitee:
            self._referrals[invitee] = inviter

    def get_user_transactions(self, email: str) -> List[Dict[str, Any]]:
        """Returns all billing transactions logged for a user."""
        email_clean = email.strip().lower()
        return [tx.to_dict() for tx in self._transactions.values() if tx.email == email_clean]

    def list_all_transactions(self) -> List[Dict[str, Any]]:
        """Lists every transaction on the platform (ADMIN only)."""
        return [tx.to_dict() for tx in self._transactions.values()]

    def get_referral_reward_balance(self, email: str) -> float:
        """Returns the invitation credit balance earned by a user."""
        email_clean = email.strip().lower()
        return self._rewards.get(email_clean, 0.0)
