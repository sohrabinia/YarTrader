# YarTrader Database & Persistence Inventory

| Persistent Entity | Storage Mechanics | Primary File / Dir Location | Owner Field | Status |
| :--- | :--- | :--- | :--- | :--- |
| Storage Manager | Local File Storage | `src/Application/Deployment/storage.py` | Environment Root | IMPLEMENTED + VERIFIED |
| Research Logs | Structured JSON File | `runtime/research_logs/` | System | IMPLEMENTED + VERIFIED |
| Demo Orders | JSON Evidence File | `runtime/demo_execution/` | User Account ID | IMPLEMENTED + VERIFIED |
| Relational Database | PostgreSQL / ORM | `src/Infrastructure/Persistence/` | User ID | NOT_IMPLEMENTED |
