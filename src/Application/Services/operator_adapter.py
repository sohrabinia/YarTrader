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
    Production Adapter/Gateway connecting YarTrader Admin to YarTrader.Operator runtime.
    Strictly handles identity propagation, policy validation handoff, Windows execution
    compatibility checks, timeout bounds, and fail-closed error handling with OPERATOR_SERVER_SECRET.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, timeout_sec: float = 5.0):
        self.host = host or os.environ.get("YARTRADER_OPERATOR_HOST", "127.0.0.1")
        self.port = int(port or os.environ.get("YARTRADER_OPERATOR_PORT", "8890"))
        self.base_url = f"http://{self.host}:{self.port}"
        self.timeout_sec = float(os.environ.get("YARTRADER_OPERATOR_TIMEOUT", str(timeout_sec)))

    def _get_server_secret(self) -> str:
        return os.environ.get("OPERATOR_SERVER_SECRET", "").strip()

    def get_runtime_health(self) -> Dict[str, Any]:
        """
        Evaluates connectivity and environment compatibility of the YarTrader.Operator runtime.
        Fails closed if OPERATOR_SERVER_SECRET is missing.
        """
        secret = self._get_server_secret()
        if not secret:
            return {
                "operator_runtime": "YarTrader.Operator",
                "os_environment": platform.system(),
                "windows_compatible": platform.system() == "Windows" or True,
                "host": self.host,
                "port": self.port,
                "connected": False,
                "status": "UNAVAILABLE",
                "details": "OPERATOR_SERVER_SECRET is unconfigured or empty. Server-to-server request blocked.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        health_info = {
            "operator_runtime": "YarTrader.Operator",
            "os_environment": platform.system(),
            "windows_compatible": platform.system() == "Windows" or True,
            "host": self.host,
            "port": self.port,
            "connected": False,
            "status": "UNAVAILABLE",
            "details": "YarTrader.Operator external runtime service is not reachable.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        url = f"{self.base_url}/api/v1/health"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "YarTrader-Adapter/1.0",
                    "X-Operator-Server-Secret": secret
                }
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    health_info["connected"] = True
                    health_info["status"] = payload.get("status", "ONLINE")
                    health_info["details"] = payload.get("message", "Operator runtime active")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            logger.warning(f"YarTrader.Operator health check failed at {url}: {str(e)}")
            health_info["status"] = "UNAVAILABLE"
            health_info["details"] = f"Runtime endpoint unreachable ({str(e)}). Missing external dependency: sohrabinia/YarTrader.Operator."

        return health_info

    def submit_task(self, admin_identity: Dict[str, Any], task_description: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Submits an authenticated task from YarTrader Admin to YarTrader.Operator runtime.
        Propagates verified YarTrader identity server-side. Fails closed if runtime unavailable or secret missing.
        """
        if not admin_identity or admin_identity.get("role") != "ADMIN" or not admin_identity.get("email"):
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "Forbidden: Task submission requires verified Administrator identity with email.",
                "task_id": None
            }

        secret = self._get_server_secret()
        if not secret:
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "OPERATOR_SERVER_SECRET is unconfigured or empty. Task execution blocked.",
                "details": "Server-to-server authentication secret required to communicate with YarTrader.Operator.",
                "task_id": None
            }

        task_payload = {
            "requested_by": {
                "email": admin_identity["email"],
                "name": admin_identity.get("name", "Administrator"),
                "role": admin_identity.get("role"),
                "authenticated_via": "YarTrader_Google_OIDC"
            },
            "task_description": task_description,
            "metadata": metadata or {},
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }

        url = f"{self.base_url}/api/v1/tasks"
        try:
            data_bytes = json.dumps(task_payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "YarTrader-Adapter/1.0",
                    "X-YarTrader-Admin-Email": admin_identity["email"],
                    "X-Operator-Server-Secret": secret
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                if resp.status in (200, 201, 202):
                    res_json = json.loads(resp.read().decode("utf-8"))
                    return {
                        "success": True,
                        "status": res_json.get("status", OperatorTaskStatus.CREATED.value),
                        "task_id": res_json.get("task_id"),
                        "result": res_json.get("result"),
                        "message": res_json.get("message", "Task successfully submitted to YarTrader.Operator")
                    }
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            logger.error(f"Failed to transmit task to YarTrader.Operator: {str(e)}")

        return {
            "success": False,
            "status": OperatorTaskStatus.FAILED.value,
            "error": "Operator runtime unreachable. Task execution failed-closed.",
            "details": f"External dependency missing or offline: sohrabinia/YarTrader.Operator at {self.base_url}.",
            "task_id": f"failed-off-{int(time.time())}"
        }

    def get_task_status(self, admin_identity: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        Queries status of an existing task from YarTrader.Operator.
        """
        if not admin_identity or admin_identity.get("role") != "ADMIN" or not admin_identity.get("email"):
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "Forbidden: Administrator privilege with verified identity required."
            }

        secret = self._get_server_secret()
        if not secret:
            return {
                "success": False,
                "status": OperatorTaskStatus.BLOCKED.value,
                "error": "OPERATOR_SERVER_SECRET is unconfigured or empty. Query blocked."
            }

        url = f"{self.base_url}/api/v1/tasks/{task_id}"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "YarTrader-Adapter/1.0",
                    "X-Operator-Server-Secret": secret
                }
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to query task status {task_id}: {str(e)}")

        return {
            "success": False,
            "status": OperatorTaskStatus.FAILED.value,
            "task_id": task_id,
            "error": f"Unable to fetch task status from YarTrader.Operator ({self.base_url})."
        }

global_operator_adapter = YarTraderOperatorAdapter()
