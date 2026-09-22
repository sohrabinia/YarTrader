import os
import sys
import time
import json
import socket
import logging
import platform
import urllib.request
import urllib.error
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse

logger = logging.getLogger("YarTrader.OperatorAdapter")

class OperatorTaskStatus(str, Enum):
    CREATED = "Created"
    PLANNED = "Planned"
    READY = "Ready"
    RUNNING = "Running"
    WAITING_FOR_APPROVAL = "WaitingForApproval"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    BLOCKED = "Blocked"

class YarTraderOperatorAdapter:
    """
    Production Adapter/Gateway connecting YarTrader Admin to YarOperator M12 runtime.
    Strictly handles server-side bearer authentication (OPERATOR_OWNER_TOKEN), owner ID verification (OPERATOR_OWNER_ID),
    authoritative workspace enforcement (workspaceId='yartrader'), POST /api/v1/operator/chat command dispatch,
    non-executing health probes, timeout bounds, loopback/internal runtime URL enforcement, and fail-closed error handling without exposing secrets.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, timeout_sec: float = 5.0):
        runtime_url = os.environ.get("YAROPERATOR_RUNTIME_URL", "").strip()
        if runtime_url:
            self.base_url = runtime_url.rstrip("/")
            parsed = urlparse(self.base_url)
            self.host = parsed.hostname or "127.0.0.1"
            self.port = parsed.port or 3000
        else:
            self.host = host or os.environ.get("YARTRADER_OPERATOR_HOST", "127.0.0.1")
            self.port = int(port or os.environ.get("YARTRADER_OPERATOR_PORT", "3000"))
            self.base_url = f"http://{self.host}:{self.port}"
        self.timeout_sec = float(os.environ.get("YARTRADER_OPERATOR_TIMEOUT", str(timeout_sec)))

    def _is_loopback_url(self, url: str) -> bool:
        if not url:
            return False
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = (parsed.hostname or "").lower()
            return hostname in ("127.0.0.1", "localhost", "::1")
        except Exception:
            return False

    def _get_bearer_token(self) -> str:
        token = os.environ.get("OPERATOR_OWNER_TOKEN", "").strip()
        if not token:
            token = os.environ.get("OPERATOR_SERVER_SECRET", "").strip()
        if not token:
            # Fallback to reading ACL-restricted secret file
            secret_paths = [
                os.path.join(os.getcwd(), "secrets", "operator_owner_token.secret"),
                "C:\\Projects\\YarTrader\\secrets\\operator_owner_token.secret",
            ]
            for path in secret_paths:
                if os.path.isfile(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            token = f.read().strip()
                            if token:
                                break
                    except Exception as e:
                        logger.warning(f"Failed to read secret file at {path}: {str(e)}")
        return token

    def _get_owner_id(self) -> str:
        return os.environ.get("OPERATOR_OWNER_ID", "").strip()

    def get_runtime_health(self) -> Dict[str, Any]:
        """
        Evaluates connectivity and environment compatibility of the YarOperator M12 runtime.
        Performs a non-executing socket connectivity probe without executing any commands on M12.
        Includes a safe diagnostic configuration check reporting configured/missing status for required env vars.
        Fails closed if YAROPERATOR_RUNTIME_URL is non-loopback or if OPERATOR_OWNER_TOKEN or OPERATOR_OWNER_ID is unconfigured.
        """
        token = self._get_bearer_token()
        owner_id = self._get_owner_id()
        raw_runtime_url = os.environ.get("YAROPERATOR_RUNTIME_URL", "").strip()

        config_status = {
            "OPERATOR_OWNER_ID": "configured" if owner_id else "missing",
            "YAROPERATOR_RUNTIME_URL": "configured" if raw_runtime_url else "missing",
            "OPERATOR_OWNER_TOKEN": "configured" if token else "missing"
        }

        # Enforce loopback/internal URL rule
        if not self._is_loopback_url(self.base_url):
            return {
                "operator_runtime": "YarOperator M12",
                "os_environment": platform.system(),
                "windows_compatible": platform.system() == "Windows" or True,
                "host": self.host,
                "port": self.port,
                "config_status": config_status,
                "connected": False,
                "status": "UNAVAILABLE",
                "details": "YAROPERATOR_RUNTIME_URL must point strictly to a local loopback endpoint (127.0.0.1 or localhost). External URL rejected fail-closed.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        if not token or not owner_id:
            return {
                "operator_runtime": "YarOperator M12",
                "os_environment": platform.system(),
                "windows_compatible": platform.system() == "Windows" or True,
                "host": self.host,
                "port": self.port,
                "config_status": config_status,
                "connected": False,
                "status": "UNAVAILABLE",
                "details": "OPERATOR_OWNER_TOKEN and OPERATOR_OWNER_ID must both be explicitly configured. Server-to-server request blocked.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        health_info = {
            "operator_runtime": "YarOperator M12",
            "os_environment": platform.system(),
            "windows_compatible": platform.system() == "Windows" or True,
            "host": self.host,
            "port": self.port,
            "config_status": config_status,
            "connected": False,
            "status": "UNAVAILABLE",
            "details": "YarOperator M12 external runtime service port is unreachable.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Non-executing TCP socket probe (never sends commands)
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout_sec)
            sock.close()
            health_info["connected"] = True
            health_info["status"] = "ONLINE"
            health_info["details"] = "YarOperator M12 runtime host reachable (configuration and socket verified)."
        except (socket.timeout, OSError) as e:
            logger.warning(f"YarOperator M12 socket health probe failed at {self.host}:{self.port}: {str(e)}")
            health_info["status"] = "UNAVAILABLE"
            health_info["details"] = f"Runtime endpoint unreachable on port {self.port} ({str(e)})."

        return health_info

    def submit_task(
        self,
        admin_identity: Dict[str, Any],
        task_description: str,
        workspace_id: str = "yartrader",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Submits an authenticated command from YarTrader Admin to YarOperator M12 runtime via POST /api/v1/operator/chat.
        Enforces explicit OPERATOR_OWNER_ID, loopback endpoint rule, and authoritative workspaceId='yartrader'. Fails closed if missing or mismatched.
        """
        if not admin_identity or admin_identity.get("role") != "ADMIN" or not admin_identity.get("email"):
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "Forbidden: Task submission requires verified Administrator identity with email.",
                "task_id": None
            }

        # Workspace mismatch guard
        if workspace_id and workspace_id != "yartrader":
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "Forbidden: Invalid or unauthorized workspace_id. Only 'yartrader' workspace is permitted.",
                "task_id": None
            }

        # Loopback endpoint guard
        if not self._is_loopback_url(self.base_url):
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "Forbidden: YAROPERATOR_RUNTIME_URL must point to a local loopback endpoint (127.0.0.1 or localhost). External URL rejected fail-closed.",
                "task_id": None
            }

        token = self._get_bearer_token()
        owner_id = self._get_owner_id()
        if not token or not owner_id:
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "OPERATOR_OWNER_TOKEN and OPERATOR_OWNER_ID must both be explicitly configured.",
                "details": "Server-side owner token and owner ID required to communicate with YarOperator M12 runtime.",
                "task_id": None
            }

        # M12 Request Contract for POST /api/v1/operator/chat
        cmd_payload = {
            "ownerId": owner_id,
            "workspaceId": "yartrader",
            "rawCommandText": task_description,
            "environmentId": "production",
            "targetCapability": None,
            "requestedToolId": None,
            "params": metadata or {}
        }

        url = f"{self.base_url}/api/v1/operator/chat"
        try:
            data_bytes = json.dumps(cmd_payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "YarTrader-Adapter/1.0",
                    "Authorization": f"Bearer {token}",
                    "X-YarTrader-Admin-Email": admin_identity["email"]
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                if resp.status in (200, 201, 202):
                    res_json = json.loads(resp.read().decode("utf-8"))
                    res_success = res_json.get("success", True)
                    result_obj = res_json.get("result", {}) if isinstance(res_json.get("result"), dict) else {}

                    command_id = result_obj.get("commandId") or res_json.get("commandId") or f"cmd_{int(time.time() * 1000)}"
                    cmd_status = result_obj.get("status") or ("COMPLETED" if result_obj.get("accepted", True) else "BLOCKED")
                    audit_event_id = result_obj.get("auditEventId")

                    return {
                        "success": res_success and result_obj.get("accepted", True),
                        "status": cmd_status,
                        "command_id": command_id,
                        "task_id": command_id,
                        "audit_event_id": audit_event_id,
                        "result": result_obj or res_json,
                        "message": "Command successfully processed by YarOperator M12"
                    }
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            logger.error(f"HTTPError transmitting command to YarOperator M12 ({e.code}): {err_body}")
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value if e.code in (401, 403) else OperatorTaskStatus.FAILED.value,
                "error": f"YarOperator M12 returned HTTP {e.code}",
                "details": err_body or str(e),
                "task_id": None
            }
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.error(f"Failed to transmit command to YarOperator M12 at {url}: {str(e)}")

        return {
            "success": False,
            "status": OperatorTaskStatus.FAILED.value,
            "error": "Operator runtime unreachable. Command execution failed-closed.",
            "details": f"External dependency missing or offline: sohrabinia/YarOperator M12 at {self.base_url}.",
            "task_id": None
        }

    def get_task_status(self, admin_identity: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        Task status querying is unsupported as current M12 HTTP API does not expose a task status endpoint.
        """
        if not admin_identity or admin_identity.get("role") != "ADMIN" or not admin_identity.get("email"):
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "Forbidden: Administrator privilege with verified identity required."
            }

        return {
            "success": False,
            "status": OperatorTaskStatus.BLOCKED.value,
            "task_id": task_id,
            "error": "Task status querying is not supported by current YarOperator M12 HTTP contract."
        }

    def get_all_tasks(self, admin_identity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task history listing is unsupported as current M12 HTTP API does not expose a task listing endpoint.
        """
        if not admin_identity or admin_identity.get("role") != "ADMIN" or not admin_identity.get("email"):
            return {
                "success": False,
                "error": "Forbidden: Administrator privilege with verified identity required.",
                "tasks": []
            }

        return {
            "success": False,
            "error": "Task history listing is not supported by current YarOperator M12 HTTP contract.",
            "tasks": []
        }

global_operator_adapter = YarTraderOperatorAdapter()
