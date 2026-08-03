# 4. Task Routing Model

To scale and run 150+ concurrent independent cognitive engines, the TradeYar AI Engineering Control Plane employs a deterministic, multi-stage task classification and execution routing model.

---

## 4.1 Task Classification Engine
Every incoming engineering request or system telemetry event is evaluated by the Orchestrator's **Task Classifier** across three vector spaces:
1. **Impact Space**: Does this request affect UI, Backend APIs, Core Mathematical Models, or system boundaries?
2. **Security Class**: Does this task touch configuration files, database credentials, authentication services, or pricing limits?
3. **Execution Domain**: Is it a bugfix, a feature expansion, documentation maintenance, or a security audit?

---

## 4.2 Dynamic Routing Sequences
Once classified, the Orchestrator builds an optimized, DAG (Directed Acyclic Graph) of agent invocations.

```
Incoming Task Input
        │
        ▼
Task Classification (Impact, Security, Execution Domain Analysis)
        │
        ▼
Resolve Required Agents (Selects appropriate specialized roles)
        │
        ▼
Determine Execution Order (Builds Dependency Directed Acyclic Graph - DAG)
        │
        ▼
Sequential/Concurrent Execution (Monitors state, exchanges message envelopes)
        │
        ▼
Validation Pipeline (Lints, scans, tests run via QA/Security)
```

---

## 4.3 Standard Routing Scenarios

### Scenario A: Frontend Feature Request (e.g., Adding a Neon Memory Telemetry Panel)
- **Classification**: UI/UX Impact, Low Security, Feature Expansion.
- **Agent Matrix Assigned**: Frontend Agent, Design System Agent, QA Agent.
- **Execution Order**:
  1. **Frontend Agent**: Generates components, maps to `/api/v1/dashboard/cognitive` data, updates HTML/JS layout.
  2. **QA Agent**: Writes Playwright or FastAPI endpoint validation tests. Runs frontend assertions.
  3. **Review Agent**: Audits the overall diff for visual performance and compatibility.

### Scenario B: Security Vulnerability Patch (e.g., Resolving a package vulnerability)
- **Classification**: Core System Impact, Critical Security, Bugfix/Maintenance.
- **Agent Matrix Assigned**: Security Agent, Backend Agent, Review Agent.
- **Execution Order**:
  1. **Security Agent**: Scans dependency tree, isolates the exact vulnerable library, maps out safe versions.
  2. **Backend Agent**: Implements the dependency version change inside `requirements.txt` and tests overall application initialization.
  3. **QA Agent**: Runs 100% of the 1437 test suite to verify no regressions were introduced.
  4. **Review Agent**: Audits structural and code security metrics to approve handover.

### Scenario C: Core Memory Logic Upgrade (e.g., Refining the Experience Promotion Pipeline)
- **Classification**: Core Brain Impact, High Security, Mathematical Algorithm.
- **Agent Matrix Assigned**: Architecture Agent, Backend Agent, QA Agent, Review Agent.
- **Execution Order**:
  1. **Architecture Agent**: Validates if the new promotion metrics comply with APES-FIN clean architecture, and ensures Gold/BTC isolation models are not broken.
  2. **Backend Agent**: Modifies the cognitive memory code safely (JSON write validation, atomicity).
  3. **QA Agent**: Runs statistical validation checks, out-of-sample tests, and overall memory regression tests.
  4. **Review Agent**: Performs double-entry review audit.
