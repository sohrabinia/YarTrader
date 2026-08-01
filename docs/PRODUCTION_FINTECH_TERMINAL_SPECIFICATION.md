# SaaS Fintech Terminal & Architectural Partitioning Specification
## TradeYar AI v7.0 - Commercial Lock Edition

This document details the architectural partitioning, three-tier user experience shells, SRE limit constraints, and live backend endpoint routes implemented inside TradeYar AI v7.0.

---

## 1. Three-Tier Architectural Partitioning

The platform is divided into three isolated experience shells to support commercial operations and absolute security:

### A. Public Marketing Website Shell (`/`, `/pricing`, `/features`)
- **Focus**: Conversion, pricing plans, allowed assets, and compliance disclosure.
- **Tiers Served**:
  - **Basic ($Free)**: 3 active symbol contexts, Short horizon.
  - **Professional ($79/mo)**: 15 active symbol contexts, Medium horizon, Chatbot support.
  - **Institutional ($299/mo)**: 30 active symbols, Macro horizons, priority SRE pipelines.
- **REST Namespace**: `/api/public/*`

### B. Customer Trading Terminal Shell (`/dashboard`)
- **Focus**: Premium analytics workspace for paying users, strictly sanitizing and hiding proprietary raw metrics, backpropagation weights, and judge calculations.
- **Horizons Mapping**: Custom frames are simplified into clean trading horizons:
  - **Micro**: Custom timeframe 1.
  - **Short**: Custom timeframe 4.
  - **Medium**: Custom timeframes 16 and 64.
  - **Macro**: Custom timeframes 256 and 1024.
- **REST Namespace**: `/api/user/*`

### C. Admin Supervision Console Shell (`/admin`)
- **Focus**: SRE system telemetry, symbol context management (capped at 30 active symbols), and isolated timeframe reports.
- **REST Namespace**: `/api/admin/*`
- **Security Guard**: Enforces JWT Role attributes. Normal user tokens requesting `/api/admin/*` are immediately blocked with `403 Forbidden`.

---

## 2. API Endpoint Directory

### 2.1 Public APIs
- `GET /api/public/metrics`: SaaS conversion metrics and SRE SLA uptime.
- `GET /api/public/pricing`: Subscription pricing structures.
- `GET /api/public/markets`: Categories of supported markets.

### 2.2 User APIs
- `GET /api/user/signals`: Returns sanitized signal details derived from active ShadowTrades.
- `GET /api/user/equity-simulation`: Projects compounded equity growth over sequential months.
- `GET /api/user/reports`: Horizon reports (Short, Medium, Macro views).

### 2.3 SRE Admin APIs
- `GET /api/admin/symbols`: Active symbols SRE count.
- `POST /api/admin/symbols`: Dynamically registers new contexts (capped at 30 active symbols).
- `GET /api/admin/reports`: Context-isolated, separate reports.

---

## 3. SRE Ceiling Limit Governance

- **Limit Setting**: Governed by `config/system_limits.yaml`.
- **Threshold Block**: The SRE post-trade controller programmatically blocks creating any new active context exceeding **30** concurrent unique symbols across registered domains.
- **Hydration Override**: Existing historical logs loaded on boot bypass limits to ensure cumulative data preservation.
