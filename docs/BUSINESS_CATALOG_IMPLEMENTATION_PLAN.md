# YARTRADER BUSINESS CATALOG IMPLEMENTATION PLAN

This plan outlines the architecture, data models, SRE administration endpoints, public API modifications, and frontend updates required to deliver the authoritative YarTrader Business & Monetization Catalog.

## 1. Architectural Overview
We will implement an end-to-end decoupled product catalog architecture:
1. **Catalog State Database**: `runtime_logs/business_catalog.json` holding structured representations of all valid tiers and future products.
2. **Business Catalog Manager (`BusinessCatalogManager`)**: An administrative-safe controller in `src/Application/Dashboard/business_catalog_manager.py` that processes mutations, validates configurations (e.g., non-negative pricing, proper state transitions), enforces thread-safety via `threading.RLock`, and writes transaction logs to `runtime_logs/business_audit.json`.
3. **Public & Administrative API Endpoints**: Mounted in `src/Application/Services/public_api_router.py` and `src/Application/Services/admin_api_router.py`.
4. **Checkout/Purchase Core Engine**: An endpoint `POST /api/public/business/purchase` that evaluates product lookup dynamically and checks `purchasable=True` before moving to any billing process. If `purchasable` is false or product status is draft/coming-soon, it fails closed.
5. **Interactive Admin Control Panel**: Add a dynamic CRUD product editor inside `#shell-admin` in `web_dashboard.py` allowing instant toggle of "SHOW" (visible) and "SELL" (purchasable) states, editing prices, billing, CTA labels, and descriptions without modifying Python source code or redeploying.
6. **Dynamic Business/Pricing Page**: Re-architect `#shell-pricing` render script in `web_dashboard.py` (and the React frontend client) to pull from the dynamic catalog. Partition items into "AVAILABLE NOW" and "COMING SOON" categories.

---

## 2. Core Data Models
### Product Structure
Each catalog entry will adhere to the following schema:
- `id`: unique string identifier (e.g., `daily`, `pro`, `prop-assistant`)
- `slug`: slug string
- `name`: product title
- `short_description`: short summary
- `long_description`: detailed breakdown
- `category`: PLANS, AI, TRADING, RESEARCH, ANALYTICS, PROP, TOOLS, EDUCATION, REPORTS, DATA, SERVICES, ENTERPRISE, API
- `product_type`: FREE, SUBSCRIPTION, ONE_TIME, SERVICE, CREDIT_PACKAGE, ENTERPRISE, COMING_SOON
- `price`: numerical price (e.g., 79.00 or 0.00)
- `currency`: currency string (e.g., USD)
- `billing_period`: billing interval (monthly, annual, one-time, etc.)
- `features`: list of strings detailing features
- `limits`: dictionary storing workspace bounds (e.g., `{"max_symbols": 15}`)
- `visible`: boolean showing public status
- `purchasable`: boolean enabling/disabling checkout
- `status`: DRAFT, VISIBLE, COMING_SOON, ACTIVE, PAUSED, DISABLED, ARCHIVED
- `badge`: text label (e.g., "POPULAR", "NEW")
- `cta_label`: CTA button label (e.g., "Upgrade Now", "Join Waitlist")
- `display_order`: integer for relative positioning
- `featured`: boolean highlighting the card

### Audit Log Schema
Each modification of price, visible, purchasable, or status logs:
- `admin`: administrator email
- `timestamp`: UTC ISO timestamp
- `product_id`: ID of modified product
- `field`: modified field name
- `old_value`: value before change
- `new_value`: value after change

---

## 3. Dynamic Backward-Compatible API Mapping
To prevent breaking existing frontends and SRE unit/integration tests:
- `GET /api/subscription/plans` and `GET /api/public/pricing` will load the current products of category `PLANS` from `runtime_logs/business_catalog.json` and dynamically map them back to the expected legacy schemas:
  ```json
  {
    "tier_id": "free",
    "name": "Free Researcher",
    "price_usd": "Free",
    "max_symbols": 3,
    "enabled_timeframes": ["Short"],
    "features": [...]
  }
  ```
- This ensures zero test regressions while moving to a 100% database-driven product catalog.

---

## 4. UI Dashboard Controls and Interactive Forms
We will insert HTML/JavaScript panels into `src/Application/Services/web_dashboard.py`:
- **Public `#shell-pricing`**: Replaced static cards with fetch-driven cards mapping real-time product features.
- **Admin `#shell-admin`**: Add a dedicated SRE Product Catalog tab with:
  - An inline editing modal/form.
  - Quick SHOW/SELL switches.
  - Custom form validation verifying non-negative numbers and proper types.
