# YARTRADER BUSINESS CATALOG DISCOVERY REPORT

## 1. Executive Summary
This report presents a thorough forensic audit of the YarTrader subscription, billing, pricing, and monetization layers. While YarTrader has secure billing manager pipelines, ledger managers, and OIDC support, the commercial strategy has historically relied on static plans defined in backend Python files. To support the owner's strategic vision of a comprehensive **YarTrader Business Catalog**—where unvalidated future features are visible as "Coming Soon" with zero fake payment pathways, and active features are dynamically toggled and managed directly by the SRE Admin Panel—we have performed an exhaustive discovery of all existing models and components.

## 2. Existing Repository Baseline Audit
A complete search of the repository reveals the following baseline configurations:
- **Active Branch**: `jules-11796641471965589340-d8d9648f`
- **Working Tree**: Clean baseline state.
- **Pre-existing tests**: All 1,501 tests pass successfully with 100% compliance.

## 3. Existing Subscription Plans & Tiers
The existing plans are hardcoded in `src/Application/Services/public_api_router.py` and exposed via `/api/subscription/plans`:
1. **Free Researcher (`free`)**:
   - Price: $0 (Free Access)
   - Max Symbols limit: 3
   - Enabled Timeframes: `["Short"]`
   - Features: "3 Active Symbols", "Short Horizon Signals", "Read-only access to custom frames"
2. **Daily Pulse Plan (`daily`)**:
   - Price: $29/mo
   - Max Symbols limit: 10
   - Enabled Timeframes: `["Short", "Medium"]`
   - Features: "10 Active Symbols", "Daily intelligence updates", "Daily cognitive insights"
3. **Professional Analyst (`pro`)**:
   - Price: $79/mo
   - Max Symbols limit: 15
   - Enabled Timeframes: `["Short", "Medium"]`
   - Features: "15 Active Symbols", "Short & Medium Horizon Signals", "Full read-only custom frames", "Conversational AI Assistant"
4. **Institutional SCM Terminal (`institutional`)**:
   - Price: $299/mo
   - Max Symbols limit: 50
   - Enabled Timeframes: `["Micro", "Short", "Medium", "Macro"]`
   - Features: "50 Active Symbols", "All Horizon Signals (Micro to Macro)", "Unlimited custom frames", "Priority SRE support & dedicated server access"

## 4. Existing Billing, Webhooks, & Invoicing Infrastructure
The platform features a secure, high-integrity billing engine managed by `BillingManager` in `src/Application/Dashboard/billing_manager.py`:
- **State storage**: `runtime_logs/billing.json`
- **Webhooks**: Secure, HMAC-signed webhook endpoint at `/api/admin/billing/webhook` that processes `payment.success` and `subscription.cancelled` events from external payment processors (e.g., Stripe/Crypto gateways) and updates user subscription state fail-closed.
- **Idempotency**: Webhooks utilize replay protection via tracking of processed event IDs.
- **Invoices**: Generates immutable cryptographic-friendly sequential invoices inside the JSON DB.

## 5. Existing Admin Panel Control & Security
- **Admin routes**: Defined in `src/Application/Services/admin_api_router.py` with strict token verification via `enforce_admin_token` or `check_admin_guard`.
- **Operating state**: Fallback override mode is disabled in production environments (`TRADEYAR_ENV` or `RG_ENV` == `production`). No guest tokens are trusted in production.
- **Administration panel**: Located under `#shell-admin` in `src/Application/Services/web_dashboard.py` (served on `/admin` or `#admin`).
- **Configurability**: Currently supports adding/registering active symbols and viewing SCM reports. There is **no pre-existing interface** for editing products, adjusting prices, toggling product visibility, or customizing display badge/order.

## 6. Identified Capabilities & Missing Elements
1. **Separation of Visible and Purchasable States (Missing)**:
   - Previously, if a tier or service was mentioned, it was either fully functional or hard-coded.
   - We must design independent `visible: bool`, `purchasable: bool`, and `status: str` states to allow showcasing future offerings without misleading or fake checkouts.
2. **Double-Entry Financial Ledger Alignment**:
   - The platform has a robust double-entry ledger (`LedgerManager` in `src/Application/Dashboard/ledger_manager.py`) tracking micro-units/cents.
   - Future product pricing must align with this integer-based currency system (avoiding floating point errors).
3. **Prop Commercial Support**:
   - Future proprietary trading services are planned (Prop Challenge Assistant, Prop Account Monitoring, etc.).
   - These are separate commercial entities and must be defined as business catalog entries rather than hardcoded in the core execution engine.

## 7. Recommended Architecture
- Introduce `BusinessCatalogManager` to manage products, categories, plans, pricing, and configurations inside `runtime_logs/business_catalog.json`.
- Expose secure administrative SRE endpoints (`GET`, `POST`, `DELETE` under `/api/admin/business/catalog`).
- Expose public endpoint `/api/public/business/catalog` returning visible offerings, and a `/api/public/business/purchase` endpoint enforcing backend purchasability rules.
- Maintain fallback compatibility with existing `get_subscription_plans` and `/api/subscription/plans` endpoints by mapping products of category `PLANS` from the database.
- Create an intuitive product management sub-panel inside `#shell-admin` and render catalog products cleanly on the main `#shell-pricing` view.
