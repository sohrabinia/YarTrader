# 7. Security and Governance

The TradeYar AI Engineering Control Plane is constructed under zero-trust design parameters, implementing strict access isolation, modification boundaries, and multi-layered audit trails.

---

## 7.1 Agent Permissions & File Access Rules
Rather than granting arbitrary filesystem write access, the AI Agent Orchestrator implements a **Role-Based File Isolation Matrix**. The codebase is segmented into strict write domains.

| Agent Name | Allowed Write Paths | Denied Write Paths (STRICT_READ_ONLY) |
| :--- | :--- | :--- |
| **Architecture Agent** | `docs/ARCHITECTURE/`, `docs/AI_AGENT_PLATFORM/` | All Python source code (`src/`, `app/`, `tests/`) |
| **Frontend Agent** | `TradeYar-AI-Frontend-Spec/`, `static/`, locales | Core backend logic, security configurations, deployment files |
| **Backend Agent** | `src/`, `app/`, `config/` | Core security infrastructure, root `.env.production`, test structures |
| **QA Agent** | `tests/` | All application source code (`src/`, `app/`), system config |
| **Security Agent** | `docs/SECURITY/`, security tools | Core application code paths, pricing configurations |
| **Documentation Agent**| `docs/`, `CHANGELOG.md`, `RELEASE_NOTES.md` | All code files, tests, environment configurations |
| **Review Agent** | PR logs, markdown reports | Entire codebase (Read-Only validation engine) |

---

## 7.2 Code Modification Limits
1. **No direct edits to .env or .env.production**: Environment credentials must never be altered dynamically by AI agents. Configuration overrides must pass through native YAML loader overrides or server-level variables.
2. **Zero Automated Library Introductions**: Agents cannot arbitrarily install third-party libraries using pip. Changing dependencies inside `requirements.txt` is strictly blocked and requires a dedicated Security Agent Audit + Manual human approval.
3. **No Dynamic Execution of Arbitrary Code**: Evaluators like `eval()` or `exec()` are permanently banned within the execution runtime to eliminate injection vectors.

---

## 7.3 Governance Audit Logging (The "Who, What, Why" Standard)
Every action, execution, or code patch produced by an agent inside the Control Plane must generate a structured, immutable governance log appended to `logs/audit/agent_governance.json`.

Every entry must strictly comply with the **"Who, What, Why"** model:

```json
{
  "timestamp": "2025-05-18T12:05:22.123Z",
  "correlation_id": "corr_38da811b-49fc-48ff",
  "who": {
    "agent_id": "backend_agent_v3_2",
    "requested_by": "human_operator_sre"
  },
  "what": {
    "action": "MODIFY_FILE",
    "target_file": "src/Application/Services/web_dashboard.py",
    "diff_checksum": "sha256_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "why": {
    "rationale": "To optimize database read times for the active symbols matrix in response to high API latency alerts.",
    "jira_task_reference": "TY-5022"
  },
  "verification": {
    "tests_run": 1437,
    "tests_failed": 0,
    "security_scan_status": "PASSED"
  },
  "approval": {
    "gate_id": "gate_auth_v3_20250518",
    "approver": "human_sre_lead",
    "approved_at": "2025-05-18T12:08:11Z"
  }
}
```

---

## 7.4 Automated Traceability & Change Tracking
- **Git Commit Attribution**: When Jules commits changes validated by the Multi-Agent Control Plane, the git commit body must list the exact agent identifiers and correlation IDs associated with the task, guaranteeing 100% cryptographic traceability back to the initial requirement.
