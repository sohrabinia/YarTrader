# YARTRADER COMPREHENSIVE BUSINESS CATALOG

This document serves as the authoritative guide for the YarTrader Business & Product Catalog, detailing its database structures, APIs, and administrative control mechanics.

## 1. Product Lifecycle & Status Model
To support the strategic "SHOW -> VALIDATE -> MONETIZE" pipeline, each commercial offering resides in one of the following lifecycle states:
- **DRAFT**: Internal testing product. Never visible to the public. Non-purchasable.
- **VISIBLE**: Visible in the catalog as a potential offering, but non-purchasable.
- **COMING_SOON**: Visible publicly with a "Coming Soon" badge. The purchase CTA is disabled, preventing premature monetization.
- **ACTIVE**: Visible and fully purchasable. real active checkouts are verified.
- **PAUSED**: Temporarily suspended. Visible but non-purchasable.
- **DISABLED**: Deactivated. Hidden and non-purchasable.
- **ARCHIVED**: Soft-deleted historical product.

---

## 2. Dynamic Pricing & Billing Configurations
YarTrader supports multiple monetization billing periods and models dynamically:
- **FREE**: 0.0 USD price, giving base entry-level workspace features (e.g. Free Researcher).
- **SUBSCRIPTION**: Monthly/Annual pricing intervals mapped to SaaS subscription tiers (e.g. Daily, Pro, Institutional).
- **ONE_TIME**: Single flat-rate payment for custom reports or dedicated professional SRE audits.
- **CREDIT_PACKAGE**: Individual credit packs consumed for background research or interactive AI chats.
- **SERVICE**: Ongoing custom broker API maintenance or enterprise infrastructure consulting.

---

## 3. Product Catalog Schema Specification
Every product record in `runtime_logs/business_catalog.json` adheres to the following strict typed structure:
```json
{
    "id": "pro",
    "slug": "pro",
    "name": "Professional Analyst",
    "short_description": "The professional standard for individual analysts.",
    "long_description": "Expands active symbol limits to 15 and unlocks conversational SRE assistance.",
    "category": "PLANS",
    "subcategory": null,
    "product_type": "SUBSCRIPTION",
    "price": 79.0,
    "currency": "USD",
    "billing_period": "monthly",
    "features": [
        "15 Active Symbols",
        "Short & Medium Horizon Signals",
        "Conversational AI Assistant"
    ],
    "limits": {
        "max_symbols": 15,
        "enabled_timeframes": ["Short", "Medium"]
    },
    "visible": true,
    "purchasable": true,
    "status": "ACTIVE",
    "badge": "RECOMMENDED",
    "cta_label": "Subscribe Pro",
    "display_order": 3,
    "featured": true,
    "created_at": "2026-08-09T09:00:00Z",
    "updated_at": "2026-08-09T09:00:00Z"
}
```

---

## 4. API Endpoint Definitions

### A. Public API Router
- **`GET /api/public/business/catalog`**:
  - Returns a list of all visible products sorted by `display_order`.
- **`POST /api/public/business/purchase`**:
  - Validates a checkout request for a `product_id`.
  - Enforces fail-closed protection: returns 400 Bad Request if the product is not purchasable, not visible, or has negative pricing.
- **`GET /api/subscription/plans`** & **`GET /api/public/pricing`**:
  - Backward-compatible dynamic loaders. Load plans from the database, map them to legacy schemas, and serve them to prevent breaking existing SPA or integration tests.

### B. Administrative API Router
- **`GET /api/admin/business/catalog`**:
  - Retrieves all products including invisible/draft ones. Gated via SRE `enforce_admin_token`.
- **`POST /api/admin/business/catalog`**:
  - Saves or updates a product. Validates type and price bounds before persistence. Writes transaction record to `runtime_logs/business_audit.json`.
- **`DELETE /api/admin/business/catalog/{product_id}`**:
  - Removes a product from the database safely.

---

## 5. Known Limitations
- **External Stripe/Gateway Webhooks**: Integrations are configured as signed mock endpoints until actual production billing contracts are signed with card providers.
- **Client-Side SPA Routing**: Since the frontend React terminal compiles locally using CSR hash-based routing (`#/pricing`), dynamic navigation is handled entirely in-memory or via localStorage keys.
