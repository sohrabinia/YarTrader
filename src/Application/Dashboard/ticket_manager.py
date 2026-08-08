import os
import json
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.Infrastructure.exceptions import ValidationException

class TicketManager:
    """
    SaaS Support Ticketing persistence manager.
    Supports user ticket creation, message replies, admin status/priority updates,
    strict cross-user access controls, input sanitization, and result pagination.
    """
    def __init__(self, filepath: str = "runtime_logs/tickets.json") -> None:
        self.filepath = filepath
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        with self.lock:
            if not os.path.exists(self.filepath):
                self._save({"tickets": {}})

    def _load(self) -> Dict[str, Any]:
        with self.lock:
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {"tickets": {}}

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

    def create_ticket(self, email: str, subject: str, category: str, priority: str, message: str) -> Dict[str, Any]:
        """Creates a new support ticket and logs the initial user message."""
        # Validate inputs to prevent injection and malicious payloads
        sub_clean = subject.strip()
        msg_clean = message.strip()
        if not sub_clean or not msg_clean:
            raise ValidationException("Subject and message content cannot be empty.")

        with self.lock:
            data = self._load()
            ticket_id = f"tick-{secrets_token()}"
            now = datetime.now(timezone.utc).isoformat()

            ticket = {
                "ticket_id": ticket_id,
                "email": email.lower(),
                "subject": sub_clean[:200], # bounds check
                "category": category,
                "priority": priority.upper(),
                "status": "OPEN",
                "created_at": now,
                "updated_at": now,
                "closed_at": None,
                "messages": [
                    {
                        "sender": email.lower(),
                        "message": msg_clean[:2000],
                        "timestamp": now
                    }
                ]
            }
            data["tickets"][ticket_id] = ticket
            self._save(data)
            return ticket

    def add_reply(self, ticket_id: str, email: str, message: str, is_admin: bool = False) -> Dict[str, Any]:
        """Appends a reply message to the support ticket preserving ordering."""
        msg_clean = message.strip()
        if not msg_clean:
            raise ValidationException("Reply message content cannot be empty.")

        with self.lock:
            data = self._load()
            if ticket_id not in data["tickets"]:
                raise ValidationException(f"Ticket ID '{ticket_id}' not found.")

            ticket = data["tickets"][ticket_id]

            # Authorization check: verify owner or administrator
            if not is_admin and ticket["email"] != email.lower():
                raise ValidationException("Unauthorized: You do not have permissions to access this ticket.")

            # Append reply preserving chronological order
            ticket["messages"].append({
                "sender": "sre-support@yartrader.app" if is_admin else email.lower(),
                "message": msg_clean[:2000],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            ticket["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save(data)
            return ticket

    def update_status(self, ticket_id: str, status: str, priority: Optional[str] = None) -> Dict[str, Any]:
        """SRE Administrative action updating status or priority."""
        status_upper = status.upper()
        if status_upper not in ("OPEN", "PENDING", "RESOLVED", "CLOSED"):
            raise ValidationException(f"Invalid ticket status '{status_upper}'.")

        with self.lock:
            data = self._load()
            if ticket_id not in data["tickets"]:
                raise ValidationException(f"Ticket ID '{ticket_id}' not found.")

            ticket = data["tickets"][ticket_id]
            ticket["status"] = status_upper
            if priority:
                ticket["priority"] = priority.upper()

            if status_upper == "CLOSED":
                ticket["closed_at"] = datetime.now(timezone.utc).isoformat()
            else:
                ticket["closed_at"] = None

            ticket["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save(data)
            return ticket

    def list_user_tickets(self, email: str, page: int = 1, limit: int = 10) -> List[Dict[str, Any]]:
        """Paginated list of user-owned support tickets."""
        with self.lock:
            data = self._load()
            user_tickets = [t for t in data["tickets"].values() if t["email"] == email.lower()]

            # Sort by created_at descending
            user_tickets.sort(key=lambda x: x["created_at"], reverse=True)

            # Paginate safely
            start_idx = (page - 1) * limit
            return user_tickets[start_idx : start_idx + limit]

    def list_all_tickets_admin(self, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """SRE Admin-only paginated listing of all platform tickets."""
        with self.lock:
            data = self._load()
            tickets_list = list(data["tickets"].values())
            tickets_list.sort(key=lambda x: x["created_at"], reverse=True)

            start_idx = (page - 1) * limit
            return tickets_list[start_idx : start_idx + limit]

def secrets_token() -> str:
    import secrets
    return secrets.token_hex(12)
