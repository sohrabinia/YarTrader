from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException


@dataclass
class ToolMetadata:
    tool_id: str
    name: str
    version: str
    purpose: str
    required_permission: str
    allowed_agents: List[str]
    environment: str = "PRODUCTION"
    rate_limit_per_min: int = 60


class ToolRegistry:
    """Central registry keeping track of all allowed agent tools."""
    def __init__(self) -> None:
        self._tools: Dict[str, ToolMetadata] = {}
        self._executors: Dict[str, Callable[..., Any]] = {}

    def register_tool(
        self,
        metadata: ToolMetadata,
        executor_func: Optional[Callable[..., Any]] = None
    ) -> None:
        if not metadata.tool_id:
            raise ValidationException("Tool Error: Tool ID cannot be empty.")
        self._tools[metadata.tool_id] = metadata
        if executor_func:
            self._executors[metadata.tool_id] = executor_func

    def get_tool(self, tool_id: str) -> Optional[ToolMetadata]:
        return self._tools.get(tool_id)

    def is_agent_authorized(self, agent_id: str, tool_id: str) -> bool:
        tool = self.get_tool(tool_id)
        if not tool:
            return False
        return "*" in tool.allowed_agents or agent_id in tool.allowed_agents

    def execute_tool(self, tool_id: str, agent_id: str, **kwargs: Any) -> Dict[str, Any]:
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValidationException(f"Tool Error: Tool '{tool_id}' is not registered.")

        if not self.is_agent_authorized(agent_id, tool_id):
            raise ValidationException(
                f"Permission Violation: Agent '{agent_id}' is not authorized to execute tool '{tool_id}'."
            )

        executor = self._executors.get(tool_id)
        if not executor:
            return {
                "tool_id": tool_id,
                "agent_id": agent_id,
                "status": "EXECUTED",
                "result": f"Tool {tool_id} executed with parameters {kwargs}",
                "executed_at": datetime.now().isoformat()
            }

        result = executor(**kwargs)
        return {
            "tool_id": tool_id,
            "agent_id": agent_id,
            "status": "EXECUTED",
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
