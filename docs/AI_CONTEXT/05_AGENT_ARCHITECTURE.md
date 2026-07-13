# 05. Agent Architecture

## 1. Supervisor & Orchestration loops

The `IntelligenceSupervisor` coordinates agent lifecycles sequentially (Research $\rightarrow$ Strategy $\rightarrow$ Risk $\rightarrow$ Validation $\rightarrow$ Learning). It handles timeouts and errors gracefully, logging details in the context audit logs.

### Communication Flow Diagram

```text
Supervisor ──> [ExecuteTask msg] ──> Selected Agent (e.g. Research)
                                           │
                                           ▼
[ResearchReport msg] <─── Router ─── [Self-Evaluation (completeness/conf)]
       │
       ▼
   Supervisor ──> Enrich context copy-on-write ──> Next Agent
```

---

## 2. Collaboration & Dynamic Allocation

### Capability Registry
Maps agent IDs to explicit capabilities (e.g., `"market observation"`, `"risk analysis"`) and domain focus areas (e.g., `"macro"`).

### Goal Manager
Tracks active targets (`"high accuracy"`, `"maximize synergy"`) and evaluates status against real-time operational metrics.

### Priority Engine
Varies priorities dynamically based on market regimes (such as high volatility or low information) and unmet goals.

### Dynamic Selection
Resolves the best active agent subset based on capability matching and dynamic priority rankings.

---

## 3. Consensus & Negotiation Framework

When agents make divergent suggestions:
*   The `NegotiationFramework` acts as a compromise solver.
*   It computes balanced compromised values weighted by agent priority and reported local confidence levels.

---

## 4. Knowledge Pub-Sub Sharing & Reliability

*   **KnowledgeSharingProtocol**: Enables agents to share indicator values under keys/tags without storage leakage.
*   **AdvancedAgentReliabilityFeedback**: Calculates actual prediction error to increase or dampen historical reliability scores, keeping scores clamped within $[0.5, 1.0]$.

---

## 5. Cross References
*   [01_PROJECT_UNDERSTANDING.md](01_PROJECT_UNDERSTANDING.md)
*   [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md)
