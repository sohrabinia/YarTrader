# 5. Self-Directed Development Loop

The **Self-Directed Development Loop (SDDL)** is the operational lifecycle of the TradeYar AI Engineering Control Plane. It defines the structured, iterative, and governed process of transforming an abstract requirement or SRE alert into a fully validated, tested, and documented codebase change.

---

## 5.1 SDDL Phases & Workflow

```
       Requirement / SRE Alert
                 │
                 ▼
       ┌───────────────────┐
       │   Planning SRE    │ <─── Analyzes boundaries & system limits
       └───────────────────┘
                 │
                 ▼
       ┌───────────────────┐
       │ Architecture Agent│ <─── Validates Clean Architecture rules
       └───────────────────┘
                 │
                 ▼
       ┌───────────────────┐
       │  Backend / FE     │ <─── Writes the actual code modifications
       └───────────────────┘
                 │
                 ▼
       ┌───────────────────┐
       │     QA / Test     │ <─── Generates unit tests & runs full suite
       └───────────────────┘
                 │
                 ▼
       ┌───────────────────┐
       │  Security Audit   │ <─── Scans for leaks, non-trading safety
       └───────────────────┘
                 │
                 ▼
       ┌───────────────────┐
       │  Documentation    │ <─── Syncs design files, architecture, logs
       └───────────────────┘
                 │
                 ▼
       ┌───────────────────┐
       │  Human Approval   │ <─── Strict gate; block execution until approved
       └───────────────────┘
                 │
                 ▼
       ┌───────────────────┐
       │  Jules / Merge    │ <─── Commits code, runs post-deployment checks
       └───────────────────┘
```

---

## 5.2 Phase-by-Phase Execution Details

### Phase 1: Planning & Analysis
- **Trigger**: A new feature requirement is submitted via the Product Dashboard or an automated SRE resource alert is caught.
- **Process**: The Orchestrator's internal planning models analyze system constraints (`config/system_limits.yaml`), review current capabilities, and break down the requirement into a list of sub-tasks.

### Phase 2: Architectural Consistency Validation
- **Process**: The **Architecture Agent** reviews the sub-task list. It identifies if the planned modifications violate clean boundaries. If a conflict is detected (e.g., trying to write real-time order placement logic), the loop is immediately aborted, and a security warning is logged.

### Phase 3: Code Implementation
- **Process**: The **Backend Agent** or **Frontend Agent** executes the proposed modifications within an isolated sandbox environment. The code is written into temporary branch structures to prevent development contamination.

### Phase 4: Quality Assurance and Testing
- **Process**: The **QA Agent** takes the code modifications, identifies potential edge cases, and automatically creates new test cases inside `tests/`. It then triggers `pytest` to run all tests, requiring a 100% pass rate.

### Phase 5: Security & Compliance Audit
- **Process**: The **Security Agent** scans the diff for vulnerabilities, credentials, and verifies that the read-only, non-trading mandate remains 100% intact.

### Phase 6: Documentation and Sync
- **Process**: The **Documentation Agent** registers the change in `CHANGELOG.md`, updates technical markdown files, and ensures system visual designs are fully updated bilingually.

### Phase 7: Human Approval Gate
- **Process**: This is a hard-blocked wait state. All agent findings, logs, test reports, and file diffs are consolidated into an interactive HTML summary delivered to the human operator. Implementation pauses here until explicit human approval is received.

### Phase 8: Jules Execution & Integration
- **Process**: Once approved, **Jules** takes the validated changes, checks them into the target Git branch, executes post-merge health checks (`/health/ready`), and closes the task session.
