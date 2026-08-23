# YarTrader Master Route & Navigation Specification v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Complete route tree, navigation layouts, layout shells, user access tiers, and API backend dependencies for the YarTrader platform.

---

## Navigation Shell Hierarchy

The YarTrader platform is structured into 4 distinct layout shells:

1. **`PublicLayout`:** Light editorial / dark theme container for marketing, documentation, pricing, and public research.
2. **`AuthLayout`:** Split-screen layout for authentication, registration, password recovery, and onboarding.
3. **`TerminalLayout`:** Dark institutional command center shell for user intelligence, trading, risk, portfolio, learning, and SaaS management.
4. **`AdminLayout`:** Enterprise control plane sidebar layout for SRE monitoring, AI engines, system validation, and audit logs.

---

## Complete Platform Route Catalog

| Route Path | Shell Layout | Page Purpose | Access Level | Backend API Binding | Redesign Priority |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **PUBLIC PORTAL** | | | | | |
| `/` | `PublicLayout` | Platform Home & Key Metrics Overview | Anonymous | `GET /api/public/metrics` | **P1** |
| `/features` | `PublicLayout` | 4-Pillar Financial Intelligence Showcase | Anonymous | Static Content | **P2** |
| `/technology` | `PublicLayout` | Autonomous AI Architecture & SRE Hardening | Anonymous | Static Content | **P2** |
| `/pricing` | `PublicLayout` | SaaS Subscription Plans & Feature Matrix | Anonymous / User | `GET /api/subscription/plans` | **P0** |
| `/blog` | `PublicLayout` | Quantitative Research Articles & Insights | Anonymous | `GET /api/blog` | **P2** |
| `/docs` | `PublicLayout` | API Contracts & Platform Documentation | Anonymous | Static Content | **P1** |
| `/faq` | `PublicLayout` | Frequently Asked Questions | Anonymous | Static Content | **P2** |
| `/contact` | `PublicLayout` | Enterprise & Institutional Contact Sales | Anonymous | `POST /api/contact` | **P2** |
| `/legal` | `PublicLayout` | Terms of Service & Privacy Policy | Anonymous | Static Content | **P2** |
| **AUTHENTICATION** | | | | | |
| `/login` | `AuthLayout` | User Sign In & OAuth SSO | Anonymous | `POST /api/auth/login`, `/google`, `/apple` | **P0** |
| `/register` | `AuthLayout` | User Account Creation | Anonymous | `POST /api/auth/register` | **P0** |
| `/forgot-password`| `AuthLayout` | Password Reset Dispatch Form | Anonymous | `POST /api/auth/forgot-password` | **P1** |
| `/reset-password` | `AuthLayout` | Password Reset Confirmation | Anonymous | `POST /api/auth/reset-password` | **P1** |
| **USER INTELLIGENCE TERMINAL** | | | | | |
| `/dashboard` | `TerminalLayout` | Command Center + Candlestick Chart | Authenticated | `GET /api/user/markets`, `/api/user/signals` | **P0** |
| `/signals` | `TerminalLayout` | Multi-Horizon Signal Hub | Authenticated | `GET /api/user/signals` | **P0** |
| `/execution-intel`| `TerminalLayout` | 5-Stage Execution Cascade & XAI Rationale | Authenticated | `GET /api/execution/*`, `/api/structure/*` | **P0** |
| `/fractal` | `TerminalLayout` | Multi-Scale x3/x4 Fractal Visualizer | Authenticated | `GET /api/fractal/status`, `/api/pattern/*` | **P0** |
| `/regime` | `TerminalLayout` | Market Regime Analysis & Shift Gauge | Authenticated | `GET /api/user/signals` | **P1** |
| `/decisions` | `TerminalLayout` | XAI Decision Rationale & Evidence Trace | Authenticated | `GET /api/intelligence/explain/{id}` | **P1** |
| `/risk` | `TerminalLayout` | Portfolio Risk Dashboard & Emergency Stop | Authenticated | `GET /api/portfolio/*`, `POST /api/risk/emergency_stop` | **P0** |
| `/trading/demo` | `TerminalLayout` | MT5 Demo Account #52961173 Terminal | Authenticated | `GET /api/demo/trades`, `/api/demo/report` | **P0** |
| `/trading/shadow`| `TerminalLayout` | Paper Execution Virtual Cash Manager | Authenticated | `GET /api/shadow/report`, `/api/admin/shadow-trades` | **P1** |
| `/trading/backtest`| `TerminalLayout` | Backtest Simulation Lab & History | Authenticated | `POST /api/backtest/run`, `GET /api/backtest/history` | **P1** |
| `/positions` | `TerminalLayout` | Unified Position Lifecycle Stepper | Authenticated | `GET /api/demo/trades`, `/api/shadow/report` | **P0** |
| `/journal` | `TerminalLayout` | Trade Journal & MAE/MFE Scatter Plot | Authenticated | `GET /api/user/history` | **P1** |
| `/performance` | `TerminalLayout` | Equity Compounding & Sharpe Analytics | Authenticated | `GET /api/intelligence/learning-matrix` | **P1** |
| `/learning` | `TerminalLayout` | Pattern Memory & OOS Audit Matrix | Authenticated | `GET /api/intelligence/learning-matrix` | **P1** |
| `/reports` | `TerminalLayout` | Downloadable CSV & PDF Audit Center | Authenticated | `GET /api/user/reports` | **P2** |
| **SAAS USER PLATFORM** | | | | | |
| `/onboarding` | `AuthLayout` | Personalized Terminal Setup Flow | Authenticated | `POST /api/user/profile` | **P1** |
| `/wallet` | `TerminalLayout` | Credit Ledger & Balance Statement | Authenticated | `GET /api/user/ledger/balance` | **P1** |
| `/billing` | `TerminalLayout` | Active Subscription & Payment Invoices | Authenticated | `GET /api/user/billing/subscription` | **P1** |
| `/support` | `TerminalLayout` | Support Tickets & Help Inbox | Authenticated | `GET /api/user/tickets`, `POST /api/user/tickets` | **P1** |
| `/profile` | `TerminalLayout` | User Profile & Security Settings | Authenticated | `GET /api/user/sessions` | **P1** |
| `/settings` | `TerminalLayout` | Terminal Preferences & Language Defaults | Authenticated | Local Preferences | **P2** |
| **SRE ADMIN CONTROL PLANE** | | | | | |
| `/admin/overview` | `AdminLayout` | Executive Metrics & Live Telemetry | ADMIN | `GET /api/devops/status`, `/api/devops/metrics` | **P0** |
| `/admin/users` | `AdminLayout` | User Accounts & RBAC Role Manager | ADMIN | `GET /api/devops/metrics` | **P1** |
| `/admin/system` | `AdminLayout` | Subsystem Health & SRE Validation Runner | ADMIN | `POST /api/validation/run`, `GET /api/validation/status` | **P0** |
| `/admin/data` | `AdminLayout` | Real-Time Market Ingestion Pipeline | ADMIN | `GET /api/admin/symbols` | **P1** |
| `/admin/trading-safety`| `AdminLayout`| SRE Fail-Closed Safety Gate Controls | ADMIN | `GET /api/devops/status` | **P0** |
| `/admin/intelligence`| `AdminLayout`| Model Performance & SCM Reports | ADMIN | `GET /api/admin/reports`, `/api/admin/patterns` | **P1** |
| `/admin/ai-engines`| `AdminLayout` | AI Model Provider Key Manager | ADMIN | Admin Config | **P2** |
| `/admin/cms` | `AdminLayout` | Blog, Docs & Announcement Publisher | ADMIN | `GET /api/growth/content/queue` | **P2** |
| `/admin/errors` | `AdminLayout` | System Error Feed & Exception Stream | ADMIN | `GET /api/devops/status` | **P1** |
| `/admin/audit` | `AdminLayout` | Chronological Audit Trail Inspector | ADMIN | `GET /api/validation/history` | **P1** |

---

*Route Map Specification certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
