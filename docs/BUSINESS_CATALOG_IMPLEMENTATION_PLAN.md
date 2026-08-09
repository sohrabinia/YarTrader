# YARTRADER BUSINESS CATALOG IMPLEMENTATION PLAN

## 1. Architectural Blueprint
We design a dynamic, persisted, database-driven product catalog framework:
1. **Catalog Database**: `runtime_logs/business_catalog.json` storing structured representations of all valid tiers and upcoming features.
2. **Business Catalog Manager (`BusinessCatalogManager`)**: A thread-safe component (`threading.RLock`) managing catalog retrieval, validation, and mutations, with secure transaction logging to `runtime_logs/business_audit.json`.
3. **Public API Endpoints**:
   - `GET /api/public/business/catalog` (loading all visible items).
   - `POST /api/public/business/purchase` (gating checkout, rejecting non-purchasable or hidden items on the server).
4. **Admin SRE Endpoints**:
   - `GET /api/admin/business/catalog`
   - `POST /api/admin/business/catalog`
   - `DELETE /api/admin/business/catalog/{product_id}`
   - Gated via `enforce_admin_token` (and `check_admin_guard`).

---

## 2. Dynamic Price Semantics Gating
To ensure floating point pricing does not leak into the integer-cents-based `BillingManager` and `LedgerManager`:
- The catalog represents presentation price in standard float dollars (e.g. `79.0`).
- When a purchase request is initiated on `/api/public/business/purchase`, the server fetches the product, converts the catalog price to integer cents (`int(price * 100)`), and passes the validated amount to any downstream invoice or payment generation layer.
- Negative prices are strictly rejected on product updates and checkout requests.

---

## 3. Product Lifecycle & Transition Rules
Each product card supports three independent dimensions:
1. **visible** (`bool`)
2. **purchasable** (`bool`)
3. **status** (`str`): `DRAFT`, `VISIBLE`, `COMING_SOON`, `ACTIVE`, `PAUSED`, `DISABLED`, `ARCHIVED`

### State Gating Invariants
- `status == "COMING_SOON"` implies `purchasable` must be `False`.
- `status == "DRAFT"` implies `visible` must be `False` and `purchasable` must be `False`.
- `status == "DISABLED"` implies `purchasable` must be `False`.
- `price < 0` is strictly forbidden.
- Any attempt to set an invalid state combination is rejected with a validation exception on the backend.
