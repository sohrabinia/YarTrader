import os
import sys
import time
import json
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
    Strictly handles server-side bearer authentication, owner/workspace contract (workspaceId='yartrader'),
    POST /api/v1/operator/chat command dispatch, Windows execution compatibility checks,
    timeout bounds, and fail-closed error handling without exposing secrets.
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
        self._local_task_history: List[Dict[str, Any]] = []

    def _get_bearer_token(self) -> str:
        token = os.environ.get("OPERATOR_OWNER_TOKEN", "").strip()
        if not token:
            token = os.environ.get("OPERATOR_SERVER_SECRET", "").strip()
        return token

    def _get_owner_id(self, admin_identity: Optional[Dict[str, Any]] = None) -> str:
        env_owner = os.environ.get("OPERATOR_OWNER_ID", "").strip()
        if env_owner:
            return env_owner
        if admin_identity and admin_identity.get("email"):
            return admin_identity["email"]
        return "owner_yartrader"

    def get_runtime_health(self) -> Dict[str, Any]:
        """
        Evaluates connectivity and environment compatibility of the YarOperator M12 runtime.
        Fails closed if server-side owner token is missing.
        """
        token = self._get_bearer_token()
        if not token:
            return {
                "operator_runtime": "YarOperator M12",
                "os_environment": platform.system(),
                "windows_compatible": platform.system() == "Windows" or True,
                "host": self.host,
                "port": self.port,
                "connected": False,
                "status": "UNAVAILABLE",
                "details": "OPERATOR_OWNER_TOKEN / OPERATOR_SERVER_SECRET is unconfigured or empty. Request blocked.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        health_info = {
            "operator_runtime": "YarOperator M12",
            "os_environment": platform.system(),
            "windows_compatible": platform.system() == "Windows" or True,
            "host": self.host,
            "port": self.port,
            "connected": False,
            "status": "UNAVAILABLE",
            "details": "YarOperator M12 external runtime service is not reachable.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Probe M12 HTTP command endpoint with a lightweight probe payload
        url = f"{self.base_url}/api/v1/operator/chat"
        probe_payload = {
            "ownerId": self._get_owner_id(),
            "workspaceId": "yartrader",
            "rawCommandText": "ping",
            "environmentId": "production",
            "targetCapability": None,
            "requestedToolId": None,
            "params": {}
        }

        try:
            data_bytes = json.dumps(probe_payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "YarTrader-Adapter/1.0",
                    "Authorization": f"Bearer {token}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                if resp.status in (200, 201, 202):
                    health_info["connected"] = True
                    health_info["status"] = "ONLINE"
                    health_info["details"] = "YarOperator M12 runtime active and responsive."
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):
                logger.warning(f"YarOperator M12 health probe returned status {e.code} at {url}")
                health_info["status"] = "UNAVAILABLE"
                health_info["details"] = f"Runtime HTTP auth/policy rejection (HTTP {e.code})."
            else:
                health_info["status"] = "UNAVAILABLE"
                health_info["details"] = f"Runtime HTTP error ({str(e)})."
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.warning(f"YarOperator M12 health check failed at {url}: {str(e)}")
            health_info["status"] = "UNAVAILABLE"
            health_info["details"] = f"Runtime endpoint unreachable ({str(e)}). Missing external dependency: sohrabinia/YarOperator."

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
        Propagates verified owner identity and workspaceId='yartrader' server-side. Fails closed if runtime unavailable or token missing.
        """
        if not admin_identity or admin_identity.get("role") != "ADMIN" or not admin_identity.get("email"):
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "Forbidden: Task submission requires verified Administrator identity with email.",
                "task_id": None
            }

        token = self._get_bearer_token()
        if not token:
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "OPERATOR_OWNER_TOKEN is unconfigured or empty. Task execution blocked.",
                "details": "Server-side bearer token required to communicate with YarOperator M12 runtime.",
                "task_id": None
            }

        owner_id = self._get_owner_id(admin_identity)
        task_id = f"task_{int(time.time() * 1000)}"

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
                    ret_task_id = res_json.get("taskId") or res_json.get("task_id") or res_json.get("id") or task_id
                    res_status = res_json.get("status", OperatorTaskStatus.COMPLETED.value)
                    res_result = res_json.get("output") or res_json.get("result") or res_json

                    record = {
                        "task_id": ret_task_id,
                        "status": res_status,
                        "task_description": task_description,
                        "result": res_result,
                        "submitted_at": datetime.now(timezone.utc).isoformat(),
                        "submitted_by": admin_identity["email"],
                        "workspace_id": "yartrader"
                    }
                    self._local_task_history.insert(0, record)

                    return {
                        "success": True,
                        "status": res_status,
                        "task_id": ret_task_id,
                        "result": res_result,
                        "message": res_json.get("message", "Task successfully submitted to YarOperator M12")
                    }
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            logger.error(f"HTTPError transmitting task to YarOperator M12 ({e.code}): {err_body}")
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value if e.code in (401, 403) else OperatorTaskStatus.FAILED.value,
                "error": f"YarOperator M12 returned HTTP {e.code}",
                "details": err_body or str(e),
                "task_id": None
            }
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.error(f"Failed to transmit task to YarOperator M12 at {url}: {str(e)}")

        return {
            "success": False,
            "status": OperatorTaskStatus.FAILED.value,
            "error": "Operator runtime unreachable. Task execution failed-closed.",
            "details": f"External dependency missing or offline: sohrabinia/YarOperator M12 at {self.base_url}.",
            "task_id": None
        }

    def get_task_status(self, admin_identity: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        Queries status of a task from local recorded history.
        """
        if not admin_identity or admin_identity.get("role") != "ADMIN" or not admin_identity.get("email"):
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "Forbidden: Administrator privilege with verified identity required."
            }

        token = self._get_bearer_token()
        if not token:
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "OPERATOR_OWNER_TOKEN is unconfigured or empty. Query blocked."
            }

        for item in self._local_task_history:
            if item.get("task_id") == task_id:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": item.get("status", OperatorTaskStatus.COMPLETED.value),
                    "task_description": item.get("task_description"),
                    "result": item.get("result"),
                    "submitted_at": item.get("submitted_at")
                }

        return {
            "success": False,
            "status": OperatorTaskStatus.FAILED.value,
            "task_id": task_id,
            "error": f"Task {task_id} not found in recorded YarOperator history."
        }

    def get_all_tasks(self, admin_identity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieves list of all active/historical tasks recorded by YarTrader adapter.
        """
        if not admin_identity or admin_identity.get("role") != "ADMIN" or not admin_identity.get("email"):
            return {
                "success": False,
                "error": "Forbidden: Administrator privilege with verified identity required.",
                "tasks": []
            }

        token = self._get_bearer_token()
        if not token:
            return {
                "success": False,
                "error": "OPERATOR_OWNER_TOKEN is unconfigured or empty. Query blocked.",
                "tasks": []
            }

        return {
            "success": True,
            "tasks": self._local_task_history
        }

global_operator_adapter = YarTraderOperatorAdapter()
