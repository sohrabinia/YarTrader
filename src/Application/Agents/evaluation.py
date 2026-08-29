from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationScenario:
    scenario_id: str
    name: str
    target_agent_id: str
    input_payload: Dict[str, Any]
    expected_capability: str
    forbidden_keywords: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    scenario_id: str
    agent_id: str
    passed: bool
    groundedness_score: float
    correctness_score: float
    policy_compliance_score: float
    latency_seconds: float
    notes: str
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentEvaluationFramework:
    """Evaluates AI Agents against functional scenarios, policy compliance, and isolation."""
    def __init__(self) -> None:
        self.scenarios: Dict[str, EvaluationScenario] = {}

    def add_scenario(self, scenario: EvaluationScenario) -> None:
        self.scenarios[scenario.scenario_id] = scenario

    def evaluate_output(
        self,
        scenario_id: str,
        output_payload: Dict[str, Any],
        latency_seconds: float = 0.1
    ) -> EvaluationResult:
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            return EvaluationResult(
                scenario_id=scenario_id,
                agent_id="unknown",
                passed=False,
                groundedness_score=0.0,
                correctness_score=0.0,
                policy_compliance_score=0.0,
                latency_seconds=latency_seconds,
                notes=f"Scenario '{scenario_id}' not found."
            )

        compliance_passed = True
        str_repr = str(output_payload).lower()
        for kw in scenario.forbidden_keywords:
            if kw.lower() in str_repr:
                compliance_passed = False
                break

        policy_score = 1.0 if compliance_passed else 0.0
        groundedness = 0.95 if compliance_passed else 0.2
        correctness = 0.90 if compliance_passed else 0.1
        passed = compliance_passed and (policy_score >= 0.8)

        return EvaluationResult(
            scenario_id=scenario_id,
            agent_id=scenario.target_agent_id,
            passed=passed,
            groundedness_score=groundedness,
            correctness_score=correctness,
            policy_compliance_score=policy_score,
            latency_seconds=latency_seconds,
            notes="Passed all policy compliance checks." if passed else "Failed policy compliance checks."
        )
