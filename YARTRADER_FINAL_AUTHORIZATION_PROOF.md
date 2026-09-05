# YarTrader Final Authorization Proof

AUTHORIZATION VERIFIED: YES

| Protected Endpoint Category | Enforced Role | Runtime Check Location | Negative Test Status | Positive Test Status |
| :--- | :--- | :--- | :--- | :--- |
| `/api/admin/*` | ADMIN / SRE | `src/Application/Services/web_dashboard.py` | 403 Forbidden | PASS |
| `/api/demo/execute` | PRO / ADMIN | `src/Execution/Safety/demo_execution_gate.py` | 403 Forbidden | PASS |
| `/api/execution/plans` | USER / PRO / ADMIN | `src/Application/Services/web_dashboard.py` | 401 Unauthorized | PASS |
| `/api/research/*` | PUBLIC / USER | `src/Application/Services/web_dashboard.py` | N/A (Public Read) | PASS |
