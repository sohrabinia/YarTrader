# YarTrader Remaining Work Register

## 1. Executive Summary
This register itemizes every capability domain evaluated during the Master Reconciliation, classifying its current status, root cause, required action, test coverage, and production impact.

## 2. Priority-Classified Work Register

### P0 — Trading Safety, Risk Veto & EOD Flatten
* **Domain:** Intraday Fast Scalp / Scalp Boundaries
* **Status:** VERIFIED COMPLETE
* **Evidence:** `docs/scientific/YARTRADER_AI_TRADER_SCIENTIFIC_ARCHITECTURE.md` Section 3.
* **Required Action:** None. Intraday execution timeframes (M1–M15) and H1+ context rules strictly enforced.

* **Domain:** Mandatory EOD Position Flattening
* **Status:** VERIFIED COMPLETE
* **Evidence:** `src/Risk/Services/professional_risk_engine.py` and `src/Research/Brain/fractal_position_intelligence.py` (`POSITION_MINIMUM_NORMAL_LIFETIME = 120`s, session cutoff flat rule).
* **Required Action:** None. `OPEN_POSITIONS_AFTER_EOD = 0` invariant strictly enforced.

* **Domain:** Independent Risk Veto
* **Status:** VERIFIED COMPLETE
* **Evidence:** `ProfessionalRiskEngine` and `PropChallengeEngine` veto authority.
* **Required Action:** None. Zero AI/ML/RL execution bypass paths permitted.

### P1 — Backend Services, APIs & Database
* **Domain:** Financial Admin & User Billing APIs
* **Status:** VERIFIED COMPLETE
* **Evidence:** `src/Application/Services/web_dashboard.py` endpoints (`/api/admin/financial/summary`, `/revenue`, `/transactions`, `/api/user/financial/reports`).
* **Required Action:** None. 100% unit test coverage in `tests/YarTrader.Tests/Services/test_financial_admin_api.py`.

* **Domain:** Crypto Payment Receive Wallet Verification
* **Status:** VERIFIED COMPLETE
* **Evidence:** `src/Application/Services/wallet_verifier.py` validating TRON, EVM, Solana, and TON public receive addresses (`GET /api/billing/wallets`).
* **Required Action:** None. 100% test pass rate in `tests/YarTrader.Tests/Services/test_wallet_verification.py`.

### P2 — Frontend, Clean Routing & Localization
* **Domain:** Clean HTML5 History pushState URL Routing
* **Status:** VERIFIED COMPLETE
* **Evidence:** `@app.api_route` GET/HEAD handlers for `/fa`, `/en`, `/tr`, `/ar` in `web_dashboard.py` and `trader-terminal/src/App.jsx`.
* **Required Action:** None. Tested in `tests/YarTrader.Tests/Dashboard/test_seo_localization_routing.py`.

* **Domain:** 4-Language Localization Parity
* **Status:** VERIFIED COMPLETE
* **Evidence:** 167 keys each in `fa.json`, `en.json`, `tr.json`, `ar.json` with zero missing keys or hardcoded UI strings.
* **Required Action:** None.

### P3 — Scientific Validation & Performance
* **Domain:** Standalone Breakout Strategy Expectancy
* **Status:** BLOCKED / PRESERVED NEGATIVE EVIDENCE
* **Evidence:** Standalone expectancy -$4.60/oz across 500 opportunities on 2,460,951 M1 Dukascopy bars.
* **Required Action:** Maintain `SCIENTIFIC_TRADING_RELEASE = BLOCKED` until positive edge (> $0.00) is established in future research tasks. Do not manipulate parameters or fabricate data.

### P4 — MT5 Execution Safety Boundaries
* **Domain:** Native MT5 Windows Terminal Process IPC
* **Status:** BLOCKED IN CONTAINER / HARD-LOCKED DEMO
* **Evidence:** Non-Windows Linux container environment lacks native Windows IPC (`BLOCKED_NO_MT5_IPC`).
* **Required Action:** Maintain `LIVE_TRADING_ENABLED = False` and `REAL_ORDERS = 0` repository-wide. Execution restricted to DEMO account 52961173 on Alpari-MT5-Demo.

### P5 — Production Server Deployment Truth
* **Domain:** Remote Public HTTPS Server Memory State
* **Status:** PARTIALLY VERIFIED (Requires Remote Service Restart)
* **Evidence:** Local container runtime on `127.0.0.1:8000` is 100% verified (GET/HEAD HTTP 200). Remote host (`https://yartrader.com`) runs stale process memory returning 404 for localized paths.
* **Required Action:** Execute PowerShell service restart on remote Windows host: `Restart-Service YarTrader`.
