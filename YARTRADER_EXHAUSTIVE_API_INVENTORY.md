# YarTrader Exhaustive Backend API Inventory

Total FastAPI Endpoints Discovered: 107 in `src/Application/Services/web_dashboard.py`

| HTTP Method | Route Endpoint Path | Auth Requirement | Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/execution/plans` | Session / API Key | IMPLEMENTED + VERIFIED |
| `GET` | `/api/execution/confidence` | Session / API Key | IMPLEMENTED + VERIFIED |
| `GET` | `/api/execution/reasoning` | Session / API Key | IMPLEMENTED + VERIFIED |
| `GET` | `/api/structure/map` | Session / API Key | IMPLEMENTED + VERIFIED |
| `GET` | `/api/liquidity/map` | Session / API Key | IMPLEMENTED + VERIFIED |
| `GET` | `/api/fractal/status` | Public / Session | IMPLEMENTED + VERIFIED |
| `GET` | `/api/research/current` | Public / Session | IMPLEMENTED + VERIFIED |
| `GET` | `/api/research/history` | Public / Session | IMPLEMENTED + VERIFIED |
| `GET` | `/api/research/health` | Public / Session | IMPLEMENTED + VERIFIED |
| `POST` | `/api/demo/execute` | Auth + Pro Role | IMPLEMENTED + VERIFIED |
| `GET` | `/api/admin/status` | Auth + Admin Role | IMPLEMENTED + VERIFIED |
| `POST` | `/api/wallet/*` | Auth | NOT_IMPLEMENTED |
| `POST` | `/api/payment/*` | Auth | NOT_IMPLEMENTED |
