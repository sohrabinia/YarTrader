import json, os, secrets, threading
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

SUPPORTED_NETWORKS = {"TON", "TRC20", "ERC20", "BEP20", "SOLANA"}
USDT_SCALE = 1_000_000

class DepositManager:
    def __init__(self, filepath="runtime_logs/usdt_deposits.json", ledger=None):
        self.filepath = filepath
        self.lock = threading.RLock()
        self.ledger = ledger
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if not os.path.exists(filepath):
            self._save({"deposits": []})

    def _load(self):
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) and isinstance(data.get("deposits"), list) else {"deposits": []}
        except Exception:
            return {"deposits": []}

    def _save(self, data):
        tmp = self.filepath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.filepath)

    @staticmethod
    def _amount_micro_usdt(value) -> int:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Invalid USDT amount.")
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Invalid USDT amount.")
        scaled = amount * USDT_SCALE
        if scaled != scaled.to_integral_value():
            raise ValueError("USDT amount supports at most 6 decimal places.")
        return int(scaled)

    def create(self, email, network, tx_hash, amount_usdt):
        network = str(network).upper().strip()
        tx_hash = str(tx_hash).strip()
        amount_micro = self._amount_micro_usdt(amount_usdt)
        if network not in SUPPORTED_NETWORKS:
            raise ValueError("Unsupported network.")
        if not tx_hash or len(tx_hash) > 256:
            raise ValueError("Invalid deposit reference.")
        with self.lock:
            d = self._load()
            if any(x.get("network") == network and x.get("tx_hash") == tx_hash for x in d["deposits"]):
                raise ValueError("This transaction reference has already been submitted.")
            rec = {
                "deposit_id": "dep-" + secrets.token_hex(10),
                "email": str(email).lower(),
                "asset": "USDT",
                "network": network,
                "tx_hash": tx_hash,
                "amount_usdt": float(Decimal(amount_micro) / USDT_SCALE),
                "amount_micro_usdt": amount_micro,
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "verified_at": None,
                "verified_by": None,
                "ledger_transaction_id": None,
            }
            d["deposits"].append(rec)
            self._save(d)
            return rec

    def list_user(self, email):
        return [x for x in self._load()["deposits"] if x.get("email") == str(email).lower()]

    def list_all(self, status=None):
        return [x for x in self._load()["deposits"] if not status or x.get("status") == str(status).upper()]

    def set_status(self, deposit_id, status, admin_email):
        status = str(status).upper()
        if status not in {"VERIFIED", "REJECTED"}:
            raise ValueError("Invalid deposit status.")
        with self.lock:
            d = self._load()
            for x in d["deposits"]:
                if x.get("deposit_id") != deposit_id:
                    continue
                if x.get("status") != "PENDING":
                    raise ValueError("Deposit is already finalized.")
                if status == "VERIFIED":
                    if self.ledger is None:
                        from src.Application.Dashboard.ledger_manager import LedgerManager
                        self.ledger = LedgerManager()
                    account_id = f"{x['email']}:USDT"
                    system_account = "SYSTEM:USDT"
                    result = self.ledger.post_transaction(
                        idempotency_key=f"usdt-deposit:{deposit_id}",
                        entries=[
                            {"account_id": account_id, "type": "credit", "amount": int(x["amount_micro_usdt"])},
                            {"account_id": system_account, "type": "debit", "amount": int(x["amount_micro_usdt"])},
                        ],
                        description=f"Verified USDT deposit {deposit_id}",
                        currency="USDT",
                    )
                    x["ledger_transaction_id"] = result["transaction"]["transaction_id"]
                x["status"] = status
                x["verified_at"] = datetime.now(timezone.utc).isoformat()
                x["verified_by"] = str(admin_email or "")
                self._save(d)
                return x
        raise ValueError("Deposit not found.")
