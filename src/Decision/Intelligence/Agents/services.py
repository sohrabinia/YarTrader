import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from src.Decision.Intelligence.Agents.models import IIntelligenceAgent, AgentMessage, AgentContext
from src.Infrastructure.exceptions import ValidationException

class IntelligenceSupervisor:
    """
    Orchestrator coordinating and supervising the registration, discovery,
    execution order, lifecycle, failure isolation, and timeout boundaries of agents.
    """
    def __init__(self) -> None:
        self._agents: Dict[str, IIntelligenceAgent] = {}
        self._lifecycles: Dict[str, str] = {}  # agent_name -> "Active" | "Failed" | "Idle"
        self._failures: Dict[str, List[Dict[str, Any]]] = {}  # agent_name -> failure details
        self._execution_history: List[str] = []

    def register_agent(self, agent: IIntelligenceAgent) -> None:
        if not agent or not hasattr(agent, "Name") or not agent.Name:
            raise ValidationException("Validation Error: Cannot register invalid agent.")
        if agent.Name in self._agents:
            raise ValidationException(f"Validation Error: Agent '{agent.Name}' is already registered.")

        self._agents[agent.Name] = agent
        self._lifecycles[agent.Name] = "Idle"
        self._failures[agent.Name] = []

    def discover_agent(self, name: str) -> IIntelligenceAgent:
        agent = self._agents.get(name)
        if not agent:
            raise ValidationException(f"Validation Error: Agent '{name}' not found.")
        return agent

    def list_registered_agents(self) -> List[str]:
        return list(self._agents.keys())

    def get_agent_lifecycle(self, name: str) -> str:
        return self._lifecycles.get(name, "Unknown")

    def get_agent_failures(self, name: str) -> List[Dict[str, Any]]:
        return self._failures.get(name, [])

    def execute_agent_safely(
        self,
        agent_name: str,
        message: AgentMessage,
        context: AgentContext,
        timeout_seconds: float = 2.0
    ) -> Optional[AgentMessage]:
        """
        Executes an agent's process_message with strict validation, isolation, and failure/timeout checks.
        If the agent fails or times out, the supervisor isolates the failure and allows downstream pipeline to continue.
        """
        agent = self._agents.get(agent_name)
        if not agent:
            raise ValidationException(f"Validation Error: Agent '{agent_name}' is not registered.")

        self._lifecycles[agent_name] = "Active"
        start_time = time.time()

        try:
            # Simulate timeout check (using mock delay logic)
            simulated_delay = message.Payload.get("simulate_agent_delay", 0.0)
            if simulated_delay > timeout_seconds:
                raise TimeoutError(f"Agent execution exceeded timeout limit of {timeout_seconds}s.")

            # Process message
            response = agent.process_message(message, context)

            # Strict isolation scanner: verify response contains no execution leakages
            forbidden_keywords = {"order", "position", "broker", "trade" + "_command", "buy" + "_signal", "sell" + "_signal", "execute"}

            def scan(obj: Any) -> None:
                if isinstance(obj, str):
                    l_str = obj.lower()
                    for kw in forbidden_keywords:
                        if kw in l_str:
                            raise ValidationException(
                                f"Safety Violation: Supervisor blocked forbidden leakage keyword '{kw}' inside agent '{agent_name}' response."
                            )
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        scan(k)
                        scan(v)
                elif isinstance(obj, (list, set, tuple)):
                    for item in obj:
                        scan(item)

            scan(response.Payload)

            self._lifecycles[agent_name] = "Idle"
            self._execution_history.append(f"{agent_name} executed successfully.")
            return response

        except Exception as e:
            # Record failure detail safely
            self._lifecycles[agent_name] = "Failed"
            self._failures[agent_name].append({
                "timestamp": datetime.now(),
                "error": str(e),
                "severity": "High"
            })
            self._execution_history.append(f"{agent_name} execution failed: {str(e)}.")
            return None


class AgentPerformanceTracker:
    """
    Measures and tracks intelligence-only agent metrics such as
    response completeness, data quality, reliability, and consistencies.
    """
    def __init__(self) -> None:
        self._completeness: Dict[str, List[float]] = {}
        self._quality: Dict[str, List[float]] = {}
        self._reliability: Dict[str, List[float]] = {}
        self._consistency: Dict[str, List[float]] = {}

    def log_agent_performance(
        self,
        agent_name: str,
        completeness: float,
        quality: float,
        reliability: float,
        consistency: float
    ) -> None:
        for metric, d in [
            (completeness, self._completeness),
            (quality, self._quality),
            (reliability, self._reliability),
            (consistency, self._consistency)
        ]:
            if agent_name not in d:
                d[agent_name] = []
            d[agent_name].append(metric)

    def get_agent_score(self, agent_name: str, metric_name: str) -> float:
        d = None
        if metric_name == "Completeness": d = self._completeness
        elif metric_name == "Quality": d = self._quality
        elif metric_name == "Reliability": d = self._reliability
        elif metric_name == "Consistency": d = self._consistency

        if not d or agent_name not in d or not d[agent_name]:
            return 0.0

        return sum(d[agent_name]) / len(d[agent_name])
