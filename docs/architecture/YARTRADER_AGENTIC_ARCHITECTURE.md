# YARTRADER AGENTIC OPERATING PLATFORM — SYSTEM ARCHITECTURE, RUNTIME CONNECTIVITY & PERMISSION MATRIX

**Version:** 1.0.0
**Effective Date:** March 2026
**Status:** AUDITED ARCHITECTURE & RUNTIME CONNECTIVITY

---

## 1. High-Level System Architecture & Dependency Graph

The YarTrader Agentic Operating Platform unifies a **Deterministic Financial Core** with a governed **Agentic Operating System**, enabling specialized AI Agents to operate platform operations, customer support, news intelligence, content generation, SEO, and engineering while preserving absolute financial safety.

```text
                        HUMAN OPERATOR / SUPERVISOR
                                    │
                         GOVERNANCE & APPROVAL GATE
                                    │
                                    ▼
                ┌───────────────────────────────────────┐
                │     YARTRADER AGENT OPERATING OS      │
                ├───────────────────────────────────────┤
                │  Agent Registry    │  Model Router    │
                │  Agent Lifecycle   │  Cost Governor   │
                │  Task Router       │  Tool Registry   │
                │  Planner Agent     │  Permission Matrix│
                │  Execution Engine  │  Sandbox Isolation│
                │  Event Bus         │  Audit & Telemetry│
                └───────────────────┬───────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
FINANCIAL SQUAD              SUPPORT SQUAD               GROWTH & OPS SQUAD
  - Market Intelligence        - Conversational Support    - Growth & Content
  - Research Agent             - Tech Troubleshooting      - News Intelligence
  - Risk Advisor Agent         - Grounded Knowledge        - Operations & Security
        │                           │                           │
        ▼                           │                           │
DETERMINISTIC FINANCIAL CORE        │                           │
  - Risk Engine (Veto)              ▼                           ▼
  - Policy Gate               KNOWLEDGE & MEMORY          TELEGRAM & CMS
  - Trade Lifecycle           (L1-L4 Memory, Graph)       (Controlled Distribution)
```

---

## 2. Audited Runtime Connectivity Path

The full trigger-to-result runtime path is verified end-to-end across the codebase:

```text
Trigger (HTTP REST / Supervisor / Event)
   │
   ▼
AIAgentOrchestrator (`src/Intelligence/Orchestration/orchestrator.py`)
   │
   ▼
TaskRouter & AgentRegistry (`src/Intelligence/Orchestration/orchestrator.py`, `supervisor.py`)
   │
   ▼
PlannerAgent (`src/Intelligence/Orchestration/orchestrator.py`)
   │
   ▼
ModelRouter & CostGovernor (`src/Application/Agents/model_router.py`)
   │
   ▼
Specialized Agent (`concrete_agents.py`, `support_agent.py`, `system_agents.py`)
   │
   ▼
Skill & Tool Execution (`src/Application/Agents/tools.py`)
   │
   ▼
Memory L1–L4 & Knowledge Base (`src/Application/Agents/memory.py`, `knowledge.py`)
   │
   ▼
AgentEvaluationFramework & ShadowRunner (`evaluation.py`, `shadow_runner.py`)
   │
   ▼
Recommendation Output
   │
   ▼
Deterministic Risk Engine & Policy Gate (`src/Risk/Services/risk_engine.py`) -> Decision
```

---

## 3. Memory L1–L4 Architecture Audit

1. **L1 (Short-term / Session Memory):**
   Managed via `AgentContext` and active conversation state (`ConversationalSupportAgent.conversations[session_id]`). Stores immediate multi-turn chat messages and task context.
2. **L2 (User / Account Context):**
   Managed via user subscription tier context (`SecurityCostAgents.py`) and authenticated session state. Enforces tier limits (Free vs Pro vs Institutional).
3. **L3 (Agent Experience Memory):**
   Managed via `AgentMemory` (`src/Application/Agents/memory.py`). Stores evaluated task outputs, historical performance metrics (`AgentPerformanceTracker`), and pattern observations.
4. **L4 (Global Knowledge Base & Graph):**
   Managed via `IntelligenceKnowledgeBase`, `EvidenceRepository`, and `KnowledgeGraph` (`src/Application/Knowledge/knowledge.py`). Stores product guides, trading documentation, and cross-context entity relationships.

---

## 4. Audited Permission Matrix

| Agent | Read Market | Write DB | Execute Trade | Publish | Git SCM | Deploy | Admin |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Market Intelligence** | YES | LIMITED | NO | NO | NO | NO | NO |
| **Research Agent** | YES | LIMITED | NO | NO | NO | NO | NO |
| **Risk Advisor** | YES | LIMITED | NO | NO | NO | NO | NO |
| **Support Agent** | LIMITED | LIMITED | NO | NO | NO | NO | NO |
| **Growth & Content** | LIMITED | YES | NO | GATED | NO | NO | NO |
| **News Intelligence** | YES | LIMITED | NO | GATED | NO | NO | NO |
| **Operations Agent** | LIMITED | LIMITED | NO | NO | NO | NO | NO |
| **Engineering Agent**| LIMITED | GATED | NO | NO | GATED | GATED | NO |
| **QA Agent** | LIMITED | LIMITED | NO | NO | LIMITED | NO | NO |
| **Security Agent** | LIMITED | LIMITED | NO | NO | GATED | NO | GATED |
| **SRE Agent** | LIMITED | LIMITED | NO | NO | NO | GATED | GATED |
| **Executive Agent** | READ/POLICY | GATED | NO DIRECT | GATED | NO DIRECT | NO DIRECT | NO DIRECT |

---

## 5. Human-in-the-Loop Governance Matrix

| Action Category | Autonomy Level | Required Approval / Gate |
| :--- | :--- | :--- |
| Support Query Response | L3 (Policy-Bounded) | Bounded by grounded knowledge base; auto-response. |
| Tech Diagnostic Guidance | L2 (Approval / Verification) | User confirmation on troubleshooting steps. |
| Research Hypothesis Proposal | L1 (Recommendation) | Formal Scientific Validation Gate approval required. |
| Risk Scenario Advisory | L1 (Recommendation) | Deterministic Risk Engine + Policy Gate veto authority. |
| Draft Article / Brief | L2 (Approval Required) | Human Editorial Queue (`PENDING_APPROVAL`). |
| News Intelligence Publishing | L2 (Approval Required) | Fact-check gate + Human editor sign-off. |
| Telegram Channel Broadcast | L2 (Approval Required) | Approved draft + rate limit check. |
| Code PR / SCM Mod | L2 (Approval Required) | Automated CI/CD + Human Senior Architect Review. |
| Final Agent Activation | L0 -> L3 Transition | Final Activation Gate Sign-Off (`FINAL_ACTIVATION_GATE`). |
