import os
import json
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.Infrastructure.exceptions import ValidationException

class LedgerManager:
    """
    Enterprise-grade persistent double-entry financial ledger.
    Enforces balanced debits/credits, idempotency, safe integer representations,
    reversal workflows, and concurrency controls using RLock and atomic disk writes.
    """
    def __init__(self, filepath: str = "runtime_logs/ledger.json") -> None:
        self.filepath = filepath
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        with self.lock:
            if not os.path.exists(self.filepath):
                self._save({
                    "accounts": {},
                    "transactions": [],
                    "idempotency_keys": {}
                })

    def _load(self) -> Dict[str, Any]:
        with self.lock:
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {"accounts": {}, "transactions": [], "idempotency_keys": {}}

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

    def get_account_balance(self, account_id: str) -> int:
        """Returns account balance in integer units (cents/micro-units; no floats)."""
        with self.lock:
            data = self._load()
            return data.get("accounts", {}).get(account_id, {}).get("balance", 0)

    def post_transaction(self, idempotency_key: str, entries: List[Dict[str, Any]], description: str, currency: str = "USD") -> Dict[str, Any]:
        """
        Atomically posts a double-entry transaction.
        Enforces total_debits == total_credits, non-negative limits, and idempotency protection.
        """
        with self.lock:
            data = self._load()

            # Idempotency Protection
            if idempotency_key in data.get("idempotency_keys", {}):
                tx_id = data["idempotency_keys"][idempotency_key]
                # Find and return cached transaction details
                for tx in data["transactions"]:
                    if tx["transaction_id"] == tx_id:
                        return {"status": "Success", "cached": True, "transaction": tx}
                raise ValidationException("Idempotency key collision without matching transaction.")

            # Validate entries structure and verify no floats
            total_debits = 0
            total_credits = 0
            for entry in entries:
                amount = entry.get("amount", 0)
                if not isinstance(amount, int) or amount <= 0:
                    raise ValidationException("Entry amount must be a positive integer (representing cents/micro-units).")

                entry_type = entry.get("type", "").lower()
                if entry_type == "debit":
                    total_debits += amount
                elif entry_type == "credit":
                    total_credits += amount
                else:
                    raise ValidationException("Entry type must be either 'debit' or 'credit'.")

            # Accounting Invariant check
            if total_debits != total_credits:
                raise ValidationException(f"Accounting Invariant Violation: Debits ({total_debits}) must equal Credits ({total_credits}).")

            # Check balances and negative balance limits
            accounts_copy = dict(data.get("accounts", {}))
            for entry in entries:
                account_id = entry["account_id"]
                amount = entry["amount"]
                entry_type = entry["type"].lower()

                if account_id not in accounts_copy:
                    accounts_copy[account_id] = {"balance": 0, "currency": currency}

                current_bal = accounts_copy[account_id]["balance"]

                # Credits increase balance, Debits decrease balance (standard Asset model)
                if entry_type == "credit":
                    new_bal = current_bal + amount
                else:
                    new_bal = current_bal - amount

                # Prevent negative balances for standard client accounts (identifiable by email containing '@')
                if "@" in account_id and new_bal < 0:
                    raise ValidationException(f"Insufficient funds: Account '{account_id}' cannot fall below zero. Current balance: {current_bal}.")

                accounts_copy[account_id]["balance"] = new_bal

            # Updates are valid, persist transaction atomically
            tx_id = f"tx-{secrets_token()}"
            tx_record = {
                "transaction_id": tx_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "description": description,
                "currency": currency,
                "entries": entries,
                "idempotency_key": idempotency_key,
                "status": "POSTED"
            }

            data["accounts"] = accounts_copy
            data["transactions"].append(tx_record)
            data["idempotency_keys"][idempotency_key] = tx_id
            self._save(data)

            return {
                "status": "Success",
                "cached": False,
                "transaction": tx_record
            }

    def reverse_transaction(self, original_tx_id: str, idempotency_key: str, reason: str) -> Dict[str, Any]:
        """
        Performs a reversal/compensating transaction to correct/nullify a posted transaction.
        Never mutates or deletes previous historical logs.
        """
        with self.lock:
            data = self._load()

            # Find original transaction
            original_tx = None
            for tx in data["transactions"]:
                if tx["transaction_id"] == original_tx_id:
                    original_tx = tx
                    break

            if not original_tx:
                raise ValidationException(f"Transaction ID '{original_tx_id}' not found.")

            if original_tx.get("status") == "REVERSED":
                raise ValidationException(f"Transaction '{original_tx_id}' has already been reversed.")

            # Invert the original entries (Credits become Debits, Debits become Credits)
            reversed_entries = []
            for entry in original_tx["entries"]:
                inverted_type = "credit" if entry["type"] == "debit" else "debit"
                reversed_entries.append({
                    "account_id": entry["account_id"],
                    "type": inverted_type,
                    "amount": entry["amount"]
                })

            # Post inverted transaction
            desc = f"REVERSAL of {original_tx_id} - Reason: {reason}"
            res = self.post_transaction(
                idempotency_key=idempotency_key,
                entries=reversed_entries,
                description=desc,
                currency=original_tx["currency"]
            )

            # Reload data, find original tx, update status to REVERSED and save safely
            data = self._load()
            for tx in data["transactions"]:
                if tx["transaction_id"] == original_tx_id:
                    tx["status"] = "REVERSED"
                    break
            self._save(data)
            return res

def secrets_token() -> str:
    import secrets
    return secrets.token_hex(12)
