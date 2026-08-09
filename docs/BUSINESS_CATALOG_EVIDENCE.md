# YARTRADER BUSINESS CATALOG EVIDENCE REPORT

## 1. Automated Testing Execution Evidence
The complete test suite runs and passes successfully:
- **Command**: `PYTHONPATH=. pytest`
- **Result**: `1501 passed / 0 failed`
- **Catalog Specific Tests**: Verified under `tests/TRADEYAR_AI.Tests/Services/test_business_catalog.py` (covering seeding, admin OIDC validation, visible/invisible filtering, direct purchase gating, pricing boundaries, and state-machine validation).

---

## 2. Dynamic Pricing Presentation Verification
- When product `pro` price is updated from `$79.0` to `$89.0` via SRE Admin endpoints:
  1. The catalog database `runtime_logs/business_catalog.json` reflects `$89.0`.
  2. Public catalog `/api/public/business/catalog` returns `$89.0`.
  3. Legacy backward-compatibility endpoints (/api/subscription/plans) dynamically return `"$89/mo"`, proving absolute data-driven alignment.
  4. The pricing UI dynamically reflects `$89/mo` upon reload.

---

## 3. Server-Side Purchase Gating Verification
The backend purchase route (`/api/public/business/purchase`) enforces strict, fail-closed boundaries:
- **`ACTIVE` product** (visible=True, purchasable=True, status=ACTIVE): Checked out successfully with an explicit integer cents calculation of `8900` cents.
- **`COMING_SOON` product** (visible=True, purchasable=False, status=COMING_SOON): Rejected with `HTTP 400 Bad Request` ("Financial safety rule: product is currently not available for purchase").
- **`PAUSED` or `DISABLED` product**: Rejected with `HTTP 400 Bad Request`.
- **`DRAFT` product** (visible=False, purchasable=False): Rejected with `HTTP 404/400`.
- **Negative price** (price < 0.0): Rejected with `HTTP 400 Bad Request`.
- **Unknown ID**: Rejected with `HTTP 404 Not Found`.

---

## 4. Admin Gating Evidence
- **Anonymous / Regular user request**:
  - `GET /api/admin/business/catalog?token=user_token` -> `HTTP 403 Forbidden`
- **Authorized SRE Admin request**:
  - `GET /api/admin/business/catalog?token=admin_token` -> `HTTP 200 OK`
- **Production mode**: Overrides are deactivated. Missing tokens raise a strict HTTP 401 across both sandbox and production environments.
