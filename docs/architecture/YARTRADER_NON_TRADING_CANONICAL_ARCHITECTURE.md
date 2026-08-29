# YARTRADER — NON-TRADING PLATFORM CANONICAL ARCHITECTURE

## Executive Summary
This document establishes the official single canonical architecture for all non-trading platform subsystems within YarTrader. It consolidates the architecture across Frontend, SEO/AEO/GEO, 4-Language Localization, User Panel, Admin Panel, Agent OS, Support, Content, News, Growth, Telegram, API, and Deployment.

---

## 1. 4-Language Localization Architecture (`fa`, `en`, `tr`, `ar`) [IMPLEMENTED, WIRED, TESTED]

YarTrader strictly supports **4 production locales**:
- `fa`: Persian (RTL) — Primary default locale
- `en`: English (LTR) — Secondary default locale & `x-default` for SEO
- `tr`: Turkish (LTR)
- `ar`: Arabic (RTL)

### Asset Storage & Key Parity
- Resource bundles are located in `trader-terminal/public/locales/` (`fa.json`, `en.json`, `tr.json`, `ar.json`).
- Dynamic direction switching (`dir="rtl"` or `dir="ltr"`) is managed client-side by `I18nProvider` based on active locale.
- Key parity: 100% (167 keys per locale file).

---

## 2. Frontend & Routing Architecture [IMPLEMENTED, WIRED, TESTED]

### Universal SPA Localized Routing
- Server-side wildcard routes `@app.api_route("/fa/{path:path}")`, `/en/{path:path}`, `/tr/{path:path}`, `/ar/{path:path}` in `src/Application/Services/web_dashboard.py` return the compiled production SPA (`trader-terminal/dist/index.html`).
- Client-side React Router handles non-reloading SPA navigation.
- Admin Panel is accessible at `/fa/admin`, `/en/admin`, `/tr/admin`, `/ar/admin` with role-based access control (RBAC).

---

## 3. SEO / AEO / GEO Unified System [IMPLEMENTED, WIRED, TESTED, RUNTIME VERIFIED]

### Technical SEO & Metadata
- **Sitemap Index:** Dynamic server endpoint `GET /sitemap.xml` serving valid XML (`application/xml`).
- **Robots Rules:** Dynamic server endpoint `GET /robots.txt` serving clean plain text directives (`text/plain`).
- **Hreflang Compliance:** Self-referential and cross-language tags for all 4 supported locales (`fa`, `en`, `tr`, `ar`) with `x-default` pointing to `/en`.
- **Structured Data:** JSON-LD schema (`Organization`, `WebSite`, `SoftwareApplication`) embedded in `index.html`.

---

## 4. User Panel & Admin Panel [IMPLEMENTED, WIRED, TESTED]

### User Panel Capabilities
- User authentication (Registration, Login, Password Reset, Telegram HMAC Linking).
- Signal Feed & Market Intelligence viewer across 4 horizons (`micro`, `short`, `medium`, `macro`).
- Prop Firm Challenge Plan & Risk Limits manager.
- Compounding equity growth simulator.

### Admin Panel Capabilities
- Role-Based Access Control (`ADMIN` role required).
- SRE Health Diagnostics & Operational Control Center.
- Active Symbol Registration & Management.
- Audit Trail Event Inspector.

---

## 5. Agent OS V2 & Support Infrastructure [IMPLEMENTED, WIRED, TESTED]

### Agent Registry & Constitution
- 12 specialized agents operate strictly under the Universal Agent Constitution (`docs/architecture/YARTRADER_AGENT_CONSTITUTION.md`).
- Deterministic Financial Boundary hard-locks `Agent -> Recommendation -> Deterministic Risk Engine -> Policy Gate -> Decision`. No agent has trade execution or position-sizing authority.

### Conversational Support Agent
- Grounded multi-turn conversational assistant exposed via `/api/chat/assistant` and the floating UI widget in `App.jsx`.
- Knowledge retrieval integration covering MT5 troubleshooting, trading modes, and account questions.

---

## 6. Trading Core Safety Freeze Certification [HARD-LOCKED, PRESERVED]

- **Decision Engine:** NOT MODIFIED (FROZEN)
- **Risk Engine:** NOT MODIFIED (FROZEN)
- **Signal Engine:** NOT MODIFIED (FROZEN)
- **Execution Engine:** NOT MODIFIED (FROZEN)
- **Policy Gate:** NOT MODIFIED (FROZEN)
- **LIVE_TRADING_ENABLED:** Hard-locked `False`
- **REAL_ORDERS:** Hard-locked `0`
