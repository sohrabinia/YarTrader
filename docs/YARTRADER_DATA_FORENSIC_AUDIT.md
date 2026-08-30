# YarTrader V2 — Database & Data Forensic Audit Report

**Audit Date:** February 2026
**Product Version:** YarTrader V2 (v7.0)
**Scope:** Runtime Data Sources, Seed Data, Mock Fallbacks, Database Records
**Rule:** REAL DATA ONLY IN PRODUCTION UI — ZERO FABRICATED METRICS OR MOCK DATA IN PROD PATHS

---

## 1. Data Classification Summary

This forensic audit evaluates all data stores, seed scripts, fixtures, and API response generators in YarTrader V2 to distinguish real system data from test/demo data.

### Classification Categories:
1. `REAL_YARTRADER`: Real market data streaming from MetaTrader 5 feeds (XAUUSD, BTCUSD, EURUSD), real user sessions created via auth endpoints, and audited trading experiences memory (`experiences_memory.json`).
2. `SYSTEM_REQUIRED`: System configuration, canonical subscription tiers, default RBAC roles (`ADMIN`, `USER`), and version metadata (`config/version.json`).
3. `DEMO`: Demo account data and order execution on MT5 Demo servers.
4. `JULES_TEST`: Temporary test fixtures or synthetic data created during sandbox testing.
5. `RETIRED_SHADOW`: Retired paper execution data completely removed from active product UI paths.

---

## 2. Audit Matrix of Core Data Paths

| Data Path / Entity | Classification | In Production Path? | Remediation & Handling |
| :--- | :--- | :--- | :--- |
| **MT5 Live Tick Feed** | `REAL_YARTRADER` | Yes | Direct real-time price & candle ingestion from connected MT5 terminal. |
| **Experiences Memory** | `REAL_YARTRADER` | Yes | Real market experiences logged in `experiences_memory.json`. |
| **Auth User Sessions** | `REAL_YARTRADER` | Yes | Authenticated users stored in memory/session store via `/api/auth/login`. |
| **Subscription Plans** | `SYSTEM_REQUIRED` | Yes | Canonical subscription tiers defined in `content_manager.py`. |
| **Version Metadata** | `SYSTEM_REQUIRED` | Yes | Dynamic version resolution (`YarTrader v7.0`). |
| **UI Mock Fallbacks** | `JULES_TEST` | **REMOVED** | Removed fake data generators. Unavailable APIs display clean `DATA UNAVAILABLE` states. |
| **Demo MT5 Orders** | `DEMO` | Yes (Demo Mode) | Real order placement on Alpari MT5 Demo account. |
| **Shadow Paper Account** | `RETIRED_SHADOW` | **REMOVED FROM UI** | Retired from product experience and UI. Preserved only if required for backend historical compatibility. |

---

## 3. Production Seed Protection & Safety Verification

1. **Zero Fake Fallback Rule:** Frontend components in `App.jsx`, `DashboardView.jsx`, `PublicLandingView.jsx`, and `AdminView.jsx` do NOT fall back to fake numbers or synthetic trades when backend endpoints return empty or offline status. Empty states (`EmptyState.jsx`) or `DATA UNAVAILABLE` badges are displayed.
2. **Safe Migration Safeguard:** No `DROP DATABASE` or `TRUNCATE` operations exist in startup scripts. Real user records and audited memory databases are preserved.
3. **Live Trading Boundary:** `LIVE_TRADING_ENABLED = False` hard-locked repository-wide. No real-money trades (`REAL_ORDERS = 0`) can be placed.
