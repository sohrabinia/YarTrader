# TradeYar AI — Autonomous Completion Audit Report

This report outlines the comprehensive audit of the TradeYar AI repository, detailing existing backend API endpoints, required frontend components, and the integration mapping between them.

---

## 🗺️ Frontend-to-Backend API Mapping

| Frontend Section | Required Component / Logic | Backend API Route | Source Location in Backend |
| :--- | :--- | :--- | :--- |
| **Subscription Plans** | Pricing Tier Grid Cards | `GET /api/subscription/plans` | `src/Application/Services/web_dashboard.py` (line 3017) |
| **Chat Assistant** | Floating Bot Panel Chat | `POST /api/chat/assistant` | `src/Application/Services/web_dashboard.py` (line 3707) |
| **Trader Terminal** | Multi-Asset Signal Hub | `GET /api/user/markets`<br>`GET /api/user/signals` | `src/Application/Services/user_api_router.py` |
| **Cognitive Dashboard**| Memory, Learning, and Progress | `GET /v1/dashboard/cognitive` | `src/Application/Services/web_dashboard.py` (line 3119) |
| **SRE Health Hub** | System Readiness / SRE Status | `GET /v1/dashboard/overview`<br>`GET /api/devops/status` | `src/Application/Services/web_dashboard.py` (line 3108) |
| **Validation Center** | Asynchronous Validation Runner | `POST /api/validation/run`<br>`GET /api/validation/status` | `src/Application/Services/web_dashboard.py` (line 3016) |
| **Shadow Trading** | Simulated Performance Metrics | `GET /api/shadow/metrics` | `src/Application/Services/web_dashboard.py` (line 3099) |
| **SRE SCM Reports** | Per-Context Deep SCM Reports | `GET /api/admin/reports` | `src/Application/Services/web_dashboard.py` (line 3277) |

---

## 🔍 Audit & Discovered Gaps
- **React Relative API Path issue**: Direct `fetch('/api/...')` requests without an explicit `CONFIG.apiBaseUrl` prefix will fail in local Vite dev server environment because Vite serves on `http://localhost:5173` and will receive the calls instead of the FastAPI backend listening on port `8000`.
- **Pricing Data Schema Match**: The backend uses `price_usd` for pricing tiers, while the React UI renders `price`. The React UI needs to safely support `{plan.price_usd || plan.price}`.
- **Dynamic Cognitive Dashboard Integration**: The `App.jsx` needs to actively fetch `/v1/dashboard/overview` and `/v1/dashboard/cognitive` to dynamically display the number of patterns, validated concepts, hypotheses tested, and highest failure areas inside the terminal UI.
