# YarTrader Ultimate Production Baseline Report

## 1. Environment & Repository Metadata

```text
REPOSITORY_SHA=4895e9ec94769fcd3c081faf890e33a3594589d3
BRANCH=jules-14975269337046365248-2c55d464
WORKTREE=CLEAN_RECONCILED
PYTHON_VERSION=3.12.13
NODE_VERSION=v22.22.1
NPM_VERSION=11.11.0
BACKEND_FRAMEWORK=FastAPI / Uvicorn
FRONTEND_FRAMEWORK=React 18 / Vite 5.4.21
DATABASE_CONFIGURATION=SQLite / File-based JSON Persistence Managers
DEPLOYMENT_CONFIGURATION=Windows Service (YarTrader) / Systemd (yartrader.service)
SERVICE_CONFIGURATION=Uvicorn background thread bound to 127.0.0.1:8000
```

---

## 2. Subsystem Classification Baseline

| Subsystem | Classification | Key Verification Evidence |
| :--- | :--- | :--- |
| **Git Provenance** | **PASS** | HEAD SHA `4895e9e`, worktree reconciled |
| **FastAPI Backend** | **PASS** | Health & readiness endpoints return 200 OK |
| **React/Vite Frontend** | **PASS** | Production build completes in 2.50s (`dist/` created) |
| **Clean HTML5 Routing** | **PASS** | `@app.api_route` handlers for `/`, `/fa`, `/en`, `/tr`, `/ar` |
| **4-Language i18n** | **PASS** | 167 keys each across `fa.json`, `en.json`, `tr.json`, `ar.json` |
| **Technical SEO Assets** | **PASS** | `sitemap.xml` (44 clean HTTPS canonical URLs) & `robots.txt` |
| **Prop Firm Challenge Engine**| **PASS** | `PropChallengeEngine` in `src/Risk/Services/prop_challenge_engine.py` |
| **Wallet Payment Validator**| **PASS** | `WalletVerifierService` in `src/Application/Services/wallet_verifier.py` |
| **Financial Admin APIs** | **PASS** | `/api/admin/financial/*` and `/api/user/financial/reports` |
| **Shadow Paper Trading** | **PASS** | Fake `vpos` rows removed; renders null-safe empty states |
| **Signals Pipeline Telemetry**| **PASS** | Candidate evaluation diagnostic counts on `/api/signals` |
| **Scientific Validation** | **BLOCKED** | Expectancy `-$4.60/oz` (`SCIENTIFIC_TRADING_RELEASE = BLOCKED`) |
| **Live Trading Safety** | **PASS** | Hard-locked `LIVE_TRADING_ENABLED = False` repository-wide |
| **Windows Remote Host** | **NOT ACCESSIBLE**| Linux container sandbox lacks Win32 RPC access to `C:\Projects\YarTrader` |
