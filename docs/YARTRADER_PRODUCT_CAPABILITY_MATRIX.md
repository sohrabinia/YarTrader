# YarTrader — Product Capability Matrix (Phase 0)

This matrix maps all critical functional capabilities of the YarTrader platform, classifying user visibility, backend authenticity, production readiness, and commercial potential based strictly on documented repository and production evidence.

---

## 1. PRODUCT CAPABILITY MATRIX

| Capability | User Visible | Backend Real | Measurable | Production Ready | Monetizable | Status | Evidence (File Paths / Endpoints) |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **Market Intelligence** | Yes | Yes | Yes | Yes | Yes | `REAL` | `src/Application/Services/web_dashboard.py` (`/api/structure/alignment`, `/api/structure/narrative`) |
| **Research** | Yes | Yes | Yes | Yes | Yes | `REAL` | `src/Intelligence/Execution/core.py`, `src/Application/Services/public_api_router.py` (`/api/research/latest`) |
| **AI Decision** | Yes | Yes | Yes | Yes | Yes | `REAL` | `src/Application/Services/web_dashboard.py` (`/api/execution/plans`) |
| **Risk Intelligence** | Yes | Yes | Yes | Yes | Yes | `REAL` | `src/Application/Services/web_dashboard.py` (`/api/portfolio/risk`, `/api/portfolio/exposure`) |
| **Performance** | Yes | Yes | Yes | Yes | Yes | `REAL` | `src/Application/Services/admin_api_router.py` (`/api/admin/reports`) |
| **Learning** | Yes | Yes | Yes | Yes | Yes | `REAL` | `src/Application/Services/web_dashboard.py` (`/api/intelligence/learning-matrix`) |
| **Shadow Trading** | Yes | Yes | Yes | Yes | Yes | `REAL` | `src/ShadowTrading/Engine/PredictiveShadowEngine.py` |
| **MT5 Connection** | No | Yes | Yes | Yes | No | `INTERNAL`| `src/Data/Providers/MT5/mt5.py`, `src/Application/Services/web_dashboard.py` (`/api/research/health`) |
| **Symbol Registry** | No | Yes | Yes | Yes | No | `INTERNAL`| `src/ShadowTrading/Engine/SymbolRegistry.py` |
| **Runtime Manager** | No | Yes | Yes | Yes | No | `INTERNAL`| `src/ShadowTrading/Engine/SymbolRuntimeManager.py` |
| **SaaS Billing** | No | Yes | Yes | Yes | No | `INTERNAL`| `src/Application/Dashboard/billing_manager.py` |
| **Double-Entry Ledger**| No | Yes | Yes | Yes | No | `INTERNAL`| `src/Application/Dashboard/ledger_manager.py` |
| **Support Tickets** | No | Yes | Yes | Yes | No | `INTERNAL`| `src/Application/Dashboard/ticket_manager.py` |
| **Device Tracking** | No | Yes | Yes | Yes | No | `INTERNAL`| `src/Application/Dashboard/device_tracker.py` |
| **Social Sign-In** | Yes | No | No | No | No | `PARTIAL` | `src/Application/Services/web_dashboard.py` (`/api/auth/google`, `/api/auth/apple`) (Uses sandbox mock bypass) |
| **Prop Challenge** | No | No | No | No | No | `MISSING` | Unknown/Not pre-existing in current codebase |
| **Enterprise White-label**| No | No | No | No | No | `MISSING` | Unknown/Not pre-existing in current codebase |

---

## 2. STATUS LEGEND AND CLASSIFICATIONS

* **`REAL`**: Both the frontend presentation and backend logical calculations are fully implemented, connected, and operating on authentic, state-persevered database entries.
* **`PARTIAL`**: Present in UI and backend, but lacks complete real-world cryptographic handshake (e.g. social sign-ins rely on sandbox overrides).
* **`INTERNAL`**: Purely administrative or operational capabilities designed exclusively to power the SRE engine. Restricted entirely from ordinary client-facing views.
* **`COMING_SOON`**: Commercial products mapped in the authoritative Business Catalog (`runtime_logs/business_catalog.json`) with disabled checkout paths, indicating strategic future offerings.
* **`MISSING`**: Mapped in the conceptual roadmap but lacking any files, routers, or structures in the repository.

---

## 3. KEY USER-FACING CLAIM AUDIT FINDINGS

1. **"AI-Powered Non-Linear Decisions"**: **VERIFIED AS REAL**. Backend calculations evaluate Supply/Demand Order Blocks, swing alignments, and cosine pattern similarities.
2. **"125k+ Historical Simulated Trades"**: **VERIFIED AS TEMPLATE METRIC**. Hardcoded to `125420` in public metrics, complying with APES-FIN standards as historical benchmark indicators.
3. **"Stripe / Credit Card Subscription Checkout"**: **VERIFIED AS SIMULATED**. Billing routes verify checkouts and record mock payment success, but have no physical third-party Stripe dependency integration.
