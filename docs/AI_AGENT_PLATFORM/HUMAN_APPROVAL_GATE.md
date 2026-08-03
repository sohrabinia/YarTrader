# 6. Human Approval Gate

TradeYar AI enforces a strict **Human-in-the-Loop (HITL)** policy. Specialized AI agents operate entirely within read-only and sandbox boundaries. They are strictly forbidden from performing critical system state mutations or deploying live changes without explicit human authorization.

---

## 6.1 Strict Non-Autonomy Boundaries
The TradeYar AI Engineering Control Plane is permanently blocked from:
1. **Automated Branch Merging**: No agent has authorization to merge pull requests directly into `main`, `master`, or release-bound branches.
2. **Automated Architectural Changes**: Modifications to core architecture files, layer configurations, or systemic rules require manual review.
3. **Automated Pricing & Monetization Logic**: Any files containing SaaS pricing parameters, subscription tier capacities, payment configurations, or subscription checkout flows are marked as **STRICT_READ_ONLY** to AI systems.
4. **Automated Production Deployment**: The final deployment pipeline (e.g., executing IIS setups, restarting SCM background services, or modifying server parameters) is triggered manually by SREs.

---

## 6.2 Mandatory Human Approval Points

```
Architecture Changes
        │
        ▼
   [ HUMAN GATE 1 ]  ──► Explicit architecture, dependency, or schema review
        │
Business Logic / Pricing Changes
        │
        ▼
   [ HUMAN GATE 2 ]  ──► Explicit SaaS tier, limits, or financial review
        │
Production Deployment
        │
        ▼
   [ HUMAN GATE 3 ]  ──► Manual deployment trigger, SSL validation, operational audit
```

---

## 6.3 Gate Mechanism & Interactive Interface
When the Self-Directed Development Loop reaches a Human Gate, the Orchestrator generates a **State Approval Manifest** saved as a JSON structure:

```json
{
  "gate_id": "gate_auth_v3_20250518",
  "task_correlation_id": "corr_38da811b-49fc-48ff",
  "status": "AWAITING_APPROVAL",
  "requested_by": "backend_agent",
  "summary_of_changes": "Optimized memory write transaction validation and updated subscription limit alerts bilingually.",
  "risk_assessment": {
    "score": "LOW",
    "details": "Changes only touch background logging and localized translation files. Standard tests pass with 100% success."
  },
  "impacted_files": [
    "src/Application/Dashboard/services.py",
    "locales/fa.json"
  ],
  "verification_status": {
    "unit_tests_passed": true,
    "security_scan_clean": true,
    "architecture_compliance": true
  }
}
```

This manifest is exposed via a secure SRE Admin Console route `/admin/control-plane/gates/{gate_id}`. SREs review the changes via a visual panel featuring neon status cards, code diffs, and validation telemetry, clicking **APPROVE** to trigger code merge or **REJECT** with a feedback message to return the task to the Agent loop for self-correction.
