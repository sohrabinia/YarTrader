# YarTrader Agent Permission Matrix

Defines least-privilege permissions across repository autonomous agents.

| Agent Name | Scope / Module | DB Access | Trading Permission | Payment Permission | Wallet Permission | Admin Permission |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Research Worker | `app/workers/research_worker.py` | Read/Write (Research Storage) | DEMO Execution Only | DENY | DENY | DENY |
| Content Agent | `src/Growth/Agents/` | Read/Write (Content) | DENY | DENY | DENY | DENY |
| News Agent | `src/Growth/Agents/` | Read/Write (News) | DENY | DENY | DENY | DENY |
| SEO Agent | `src/Growth/Agents/` | Read/Write (SEO) | DENY | DENY | DENY | DENY |
| Security Cost Agent | `src/Growth/Agents/` | Read/Write (Metrics) | DENY | DENY | DENY | DENY |
| Trust Learning Agent| `src/Growth/Agents/` | Read/Write (Feedback) | DENY | DENY | DENY | DENY |
