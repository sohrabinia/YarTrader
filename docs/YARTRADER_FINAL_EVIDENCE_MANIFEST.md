# YarTrader Final Evidence Manifest

This document maps every major system claim and PASS status to concrete, reproducible verification evidence.

## Master Evidence Mapping

| Domain | Status | Verified Command / Test | File / Endpoint / Artifact | Actual Result | Timestamp | Environment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Authentication & RBAC** | **PASS** | `pytest tests/runtime/test_dashboard.py` | `/api/auth/*`, `check_admin_guard` | `HTTP 200` / `HTTP 401` Guard | 2026-08-27 | Container |
| **Clean HTML5 Routing** | **PASS** | `pytest tests/YarTrader.Tests/Dashboard/test_seo_localization_routing.py` | `/fa`, `/en`, `/tr`, `/ar`, `/sitemap.xml` | `HTTP 200 OK` (GET & HEAD) | 2026-08-27 | Container Localhost |
| **API 404 Isolation** | **PASS** | `pytest tests/YarTrader.Tests/Dashboard/test_seo_localization_routing.py` | `GET /api/nonexistent` | `HTTP 404` (`application/json`) | 2026-08-27 | Container Localhost |
| **Crypto Wallet Verification** | **PASS** | `pytest tests/YarTrader.Tests/Services/test_wallet_verification.py` | `src/Application/Services/wallet_verifier.py` | 9 Wallet Formats Validated | 2026-08-27 | Container |
| **Prop Firm Challenge Engine** | **PASS** | `pytest tests/YarTrader.Tests/Services/test_prop_challenge_api.py` | `src/Risk/Services/prop_challenge_engine.py` | Challenge State Machine Verified | 2026-08-27 | Container |
| **Financial Admin APIs** | **PASS** | `pytest tests/YarTrader.Tests/Services/test_financial_admin_api.py` | `/api/admin/financial/*` | Billing Summary & Revenue Matrix | 2026-08-27 | Container |
| **4-Language Localization** | **PASS** | `i18n Key Parity Audit` | `trader-terminal/public/locales/` | 167 keys each across fa, en, tr, ar | 2026-08-27 | Container |
| **Technical SEO Assets** | **PASS** | `npm run build` & Local Probe | `dist/sitemap.xml`, `dist/robots.txt` | 44 Canonical URLs & Robots File | 2026-08-27 | Container |
| **Scientific Validation** | **BLOCKED** | `pytest tests/YarTrader.Tests/Research/test_scientific_release_verification.py` | `docs/scientific/YARTRADER_V7_SCIENTIFIC_RELEASE_STATUS.json` | Expectancy -$4.60/oz (`BLOCKED`) | 2026-08-27 | Container |
| **Live Trading Safety** | **PASS** | `pytest tests/YarTrader.Tests/Research/test_scientific_release_verification.py` | `LIVE_TRADING_ENABLED = False` | Hard-locked `False` Repository-Wide | 2026-08-27 | Container |
| **Full Pytest Discovery** | **PASS** | `python3 -m pytest -q` | All test modules | 1,684 Test Units Passed (0 failures) | 2026-08-27 | Container |
| **Frontend Production Build** | **PASS** | `cd trader-terminal && npm run build` | `trader-terminal/dist/` | Built in 2.50s (`dist/` generated) | 2026-08-27 | Container |
| **Remote Windows Production Host** | **UNVERIFIED** | Public Curl Probe | `https://yartrader.com/fa` | Returns 404 (`"detail":"Not Found"`) | 2026-08-27 | Public Remote Host |
