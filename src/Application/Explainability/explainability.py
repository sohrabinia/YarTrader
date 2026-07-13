from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ExplanationNode:
    agent_id: str
    rationale: str
    evidence_keys: List[str]
    confidence_contribution: float


@dataclass(frozen=True)
class ExplainableIntelligenceReport:
    report_id: str
    timestamp: datetime
    final_decision_state: str
    overall_confidence: float
    explanations: List[ExplanationNode] = field(default_factory=list)
    visual_evidence_mapping: Dict[str, Any] = field(default_factory=dict)


class AgentExplanationLayer:
    """Builds explanation nodes representing agent thought processes."""
    def build_explanation(
        self,
        agent_id: str,
        rationale: str,
        evidence_keys: List[str],
        contribution: float
    ) -> ExplanationNode:
        return ExplanationNode(
            agent_id=agent_id,
            rationale=rationale,
            evidence_keys=evidence_keys,
            confidence_contribution=contribution
        )


class ResearchExplanationLayer(AgentExplanationLayer):
    def explain_research(self, findings: List[str]) -> ExplanationNode:
        summary = f"Research Agent observed market patterns: {', '.join(findings)}."
        return self.build_explanation("agent-research", summary, ["findings", "patterns"], 0.88)


class RiskExplanationLayer(AgentExplanationLayer):
    def explain_risk(self, approved: bool, notes: str) -> ExplanationNode:
        summary = f"Risk Agent verified allocation profile. Approved={approved}. Notes: {notes}."
        return self.build_explanation("agent-risk", summary, ["IsApproved", "RiskMetrics"], 0.95)


class ValidationExplanationLayer(AgentExplanationLayer):
    def explain_validation(self, checked: bool, score: float) -> ExplanationNode:
        summary = f"Validation Agent ran compliance audit. Checked={checked}. Quality score={score}."
        return self.build_explanation("agent-validation", summary, ["compliance_checked", "data_quality_score"], 0.98)


class DecisionTraceEngine:
    """Traces decision flows and builds visual evidence mappings."""
    def generate_trace(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        # Formulate trace pathways
        return {
            "pathway": ["Ingestion", "Gateway", "Validation", "Normalization", "Multi-Agent Collaboration", "Decision Core"],
            "nodes_visited": list(context_data.keys()),
            "timestamp": datetime.now().isoformat()
        }


class EvidenceVisualizationModels:
    """Standardizes layout structures for human-readable reports."""
    def construct_layout(self, report: ExplainableIntelligenceReport) -> str:
        layout = (
            f"=== EXPLAINABLE INTELLIGENCE REPORT ===\n"
            f"Report ID: {report.report_id}\n"
            f"Generated: {report.timestamp.isoformat()}\n"
            f"Decision State: {report.final_decision_state}\n"
            f"Confidence Score: {report.overall_confidence:.2f}\n"
            f"----------------------------------------\n"
        )
        for exp in report.explanations:
            layout += (
                f"Agent: {exp.agent_id}\n"
                f"  Rationale: {exp.rationale}\n"
                f"  Evidence Keys: {exp.evidence_keys}\n"
                f"  Confidence: {exp.confidence_contribution:.2f}\n\n"
            )
        return layout
