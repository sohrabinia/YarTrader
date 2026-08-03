from src.Application.Agents.interfaces import IIntelligenceAgent
from src.Application.Agents.context import AgentContext, ContextAuditRecord, AgentContextBuilder
from src.Application.Agents.communication import IntelligenceMessage, TraceRecord, MessageRouter
from src.Application.Agents.memory import AgentMemory, MemoryEntry
from src.Application.Agents.tracker import AgentPerformanceTracker, PerformanceScore
from src.Application.Agents.concrete_agents import (
    ResearchAgent,
    StrategyAnalystAgent,
    RiskAgent,
    ValidationAgent,
    LearningAgent
)
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Application.Agents.orchestrator import AIAgentOrchestrator, SDDLOrchestrator

# Phase 22 Collaboration imports
from src.Application.Agents.collaboration import (
    AgentCapability,
    AgentCapabilityRegistry,
    AgentGoal,
    AgentGoalManager,
    AgentPriorityEngine,
    DynamicAgentSelector,
    CollaborationProtocol,
    NegotiationProposal,
    NegotiationFramework,
    CollectiveIntelligenceEvaluator,
    AgentSelfEvaluator,
    KnowledgeItem,
    KnowledgeSharingProtocol,
    AdvancedAgentReliabilityFeedback
)

__all__ = [
    "IIntelligenceAgent",
    "AgentContext",
    "ContextAuditRecord",
    "AgentContextBuilder",
    "IntelligenceMessage",
    "TraceRecord",
    "MessageRouter",
    "AgentMemory",
    "MemoryEntry",
    "AgentPerformanceTracker",
    "PerformanceScore",
    "ResearchAgent",
    "StrategyAnalystAgent",
    "RiskAgent",
    "ValidationAgent",
    "LearningAgent",
    "IntelligenceSupervisor",
    "AIAgentOrchestrator",
    "SDDLOrchestrator",

    # Phase 22 Collaboration exports
    "AgentCapability",
    "AgentCapabilityRegistry",
    "AgentGoal",
    "AgentGoalManager",
    "AgentPriorityEngine",
    "DynamicAgentSelector",
    "CollaborationProtocol",
    "NegotiationProposal",
    "NegotiationFramework",
    "CollectiveIntelligenceEvaluator",
    "AgentSelfEvaluator",
    "KnowledgeItem",
    "KnowledgeSharingProtocol",
    "AdvancedAgentReliabilityFeedback"
]
