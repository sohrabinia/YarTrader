# YARTRADER BUSINESS CATALOG DISCOVERY REPORT

## 1. Baseline Context
- **Base Commit**: `8ca71cd19a18f059707dbca903d0bf7ab42e825d`
- **PR #147 Context**: An audit and hardening of the business, pricing, monetization, and control framework.
- **Working Tree**: Clean baseline state.
- **Baseline Tests**: 1501 passed, 0 failed.

---

## 2. Existing Pricing Page & Subscription Plans
The existing pricing plans are defined dynamically inside `src/Application/Services/public_api_router.py` under the `get_subscription_plans` function:
1. **Free Researcher (`free`)**:
   - Price: Free Access ($0)
   - Max Symbols: 3 active symbols workspace
   - Timeframes: `["Short"]`
   - Features: "3 Active Symbols", "Short Horizon Signals", "Read-only access to custom frames"
2. **Daily Pulse Plan (`daily`)**:
   - Price: $29/mo
   - Max Symbols: 10 active symbols workspace
   - Timeframes: `["Short", "Medium"]`
   - Features: "10 Active Symbols", "Daily intelligence updates", "Daily cognitive insights"
3. **Professional Analyst (`pro`)**:
   - Price: $79/mo
   - Max Symbols: 15 active symbols workspace
   - Timeframes: `["Short", "Medium"]`
   - Features: "15 Active Symbols", "Short & Medium Horizon Signals", "Full read-only custom frames", "Conversational AI Assistant"
4. **Institutional SCM Terminal (`institutional`)**:
   - Price: $299/mo
   - Max Symbols: 50 active symbols workspace
   - Timeframes: `["Micro", "Short", "Medium", "Macro"]`
   - Features: "50 Active Symbols", "All Horizon Signals (Micro to Macro)", "Unlimited custom frames", "Priority SRE support & dedicated server access"

---

## 3. Existing Billing & Ledger Integration
- **Billing Manager**: Located in `src/Application/Dashboard/billing_manager.py`, storing states in `runtime_logs/billing.json`. It processes HMAC-signed webhooks and emits sequential invoice lists.
- **Ledger Manager**: Located in `src/Application/Dashboard/ledger_manager.py`, using integer micro-units (cents) to guarantee financial safety and prevent floating-point representation bugs.

---

## 4. Discovered Gaps & Status Classification

### A. Dynamic Price Semantics
- **Analysis**: The business catalog may represent price as a standard float presentation layer. However, the transactional backend (Billing/Ledger) strictly handles integer cents to avoid float inaccuracies.
- **Status**: Verified boundary. All financial operations in the ledger/billing use integer cents.

### B. Purchase Gating & Fail-Closed Protection
- **Analysis**: Purchases must be validated on the backend. Hiding UI elements is insufficient. The backend must explicitly validate a product's state (`visible=True`, `purchasable=True`, and `status=ACTIVE`) before allowing a transition to billing/checkout workflows.
- **Status**: To be implemented securely on the backend router.

### C. Missing Features & Modules
- **Claim Offer**: Not implemented in the current codebase. Classified as `UNKNOWN` / `MISSING`.
- **Tina Assistant**: Not implemented in the current codebase. Classified as `UNKNOWN` / `MISSING`.
- **Prop Execution / Drawdown Engines**: Belong to a separate future proprietary trading phase. Classified as `PLANNED` / `COMING_SOON`.
