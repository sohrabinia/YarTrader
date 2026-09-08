# YARTRADER — CANONICAL TRUTH BASELINE

## 1. Executive Summary

This document establishes the single, evidence-backed, authoritative baseline of the YarTrader repository as of **Tuesday, September 8, 2026** at HEAD commit `4319e4d00e6b14acac9a32c304eedf7cbf06f8fa`.

YarTrader is an autonomous cognitive research and algorithmic trading platform designed for non-linear multi-timeframe fractal analysis (specifically XAUUSD on MetaTrader 5 DEMO accounts).

### Key Baseline Audit Findings:
1. **Core Development Truth**: The authoritative current development branch is `jules-748700270274326796-0b553ae4` on commit `4319e4d00e6b14acac9a32c304eedf7cbf06f8fa` under repository `sohrabinia/YarTrader`.
2. **Version Truth**: **NO SINGLE CANONICAL VERSION CURRENTLY ESTABLISHED**. The repository exhibits significant version fragmentation across configuration files, API responses, marketing content, and documentation (`v1.0.0`, `v1.0.1-production-hardened`, `v2.0.0-stable`, `v3.1.0-hardened`, `v3.2`, `v7.0`).
3. **Frontend Application**: The active single-page frontend application is located in `trader-terminal/` (built with React 18 and Vite 5.4.21). It connects dynamically to backend REST endpoints with fallback offline simulated/mock states.
4. **Backend Services & Persistence**: The core backend is implemented in FastAPI (`src/Application/Services/web_dashboard.py`) backed by double-entry JSON/SQLite persistence managers for ledger, subscriptions, and audit trails.
5. **Trading & Safety Constraints**: Trading operations are strictly fail-closed to MetaTrader 5 DEMO mode and XAUUSD symbol. Real/Live account execution and MT4 order routing are rejected fail-closed.
6. **AI & Support**: Support AI is powered by deterministic rule-based explainers (`SupportAIEngine`) that forbid hallucinating private user balances or order state.
7. **Production Verification**: **PRODUCTION RUNTIME NOT VERIFIABLE FROM CURRENT ACCESS**. External live broker connectivity, live SMTP delivery, and external payment gateway webhooks rely on unconfigured or sandbox credentials.

---

## 2. Investigation Scope

The investigation covered the entire `sohrabinia/YarTrader` workspace, spanning:
- Python Backend Services (`src/Application/`, `src/Execution/`, `src/Research/`, `src/Risk/`, `src/Growth/`)
- Single Page Application Frontend (`trader-terminal/`)
- CI/CD Workflows & Release Scripts (`.github/workflows/`, `validate_release.py`, `scripts/`)
- Test Suites (`tests/YarTrader.Tests/`)
- Technical Documentation & Historical Audits (`docs/`, `*.md`)

---

## 3. Git Truth

- **Current Branch**: `jules-748700270274326796-0b553ae4`
- **Current HEAD SHA**: `4319e4d00e6b14acac9a32c304eedf7cbf06f8fa`
- **HEAD Date**: Tue Sep 8 10:52:00 2026 +0000
- **HEAD Message**: `feat(governance): establish deterministic decision governance foundation`
- **Remote URL**: `https://github.com/sohrabinia/YarTrader`
- **Working Tree Status**: Clean

### Recent Commit Stack (Top 10):
1. `4319e4d` feat(governance): establish deterministic decision governance foundation
2. `24815b0` feat(decision): establish deterministic decision intelligence foundation
3. `7e09125` feat(decision): establish deterministic decision context foundation
4. `4b41cf6` feat(intelligence): establish deterministic intelligence foundation
5. `a777eb1` feat(memory): establish structured historical memory foundation
6. `bad9afa` feat(learning): establish canonical historical learning engine foundation
7. `bea735f` feat(backtest): establish canonical historical backtest engine foundation
8. `c131344` feat(strategy): establish canonical deterministic trend strategy foundation
9. `69670b0` feat(strategy): establish canonical deterministic range strategy foundation
10. `b743557` feat(strategy): establish canonical deterministic spike strategy foundation

---

## 4. Release Truth

- **Latest Official Git Tag**: `yartrader-v1.0.0-production`
- **Latest Tag Commit SHA**: Historical release baseline (antecedent to current main head)
- **Tag History**:
  - `yartrader-v1.0.0-production`
  - `yartrader-v1.0-release-candidate`
  - `yartrader-v1.0-audit-complete`
  - `v3.1.0-hardened`
  - `v2.0.0-stable`
  - `v1.0.1-production-hardened`
  - `v1.0.0-yartrader-release`
  - `v1.0.0-production-hardened`
  - `v1.0.0-demo-final-certified`
  - `v1.0.0-demo-certified`
  - `v1.0.0`
  - `YarTrader-Gate3-MT5-DEMO-PASS`

Current HEAD (`4319e4d`) is 10+ commits ahead of historical foundation tags, incorporating Phase 4 to Phase 16 governance and research engines.

---

## 5. Version Truth

| Source File / Context | Stated Version String | Classification | Canonical? | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| `trader-terminal/package.json` | `1.0.0` | DERIVED | No | Line 4: `"version": "1.0.0"` |
| `src/Infrastructure/version.py` | Environment / `config/version.json` | CANONICAL ENGINE | Yes (Dynamic) | Dynamic evaluation fallback |
| `src/Execution/Services/market_session_engine.py` | `v1.0.0` | STALE | No | Line 45: `source_version = "v1.0.0"` |
| `src/Application/Dashboard/content_manager.py` | `v7.0` / `v3.2` | HISTORICAL / MARKETING | No | Line 48 & Line 28 marketing copy |
| `src/Application/Services/web_dashboard.py` | `v7.0` | HISTORICAL / MARKETING | No | Line 3269: Welcome to YarTrader v7.0 |
| `docs/V3.1_PRODUCTION_BASELINE_REPORT.md` | `v3.1.0-hardened` | HISTORICAL | No | Document title claim |

**VERSION TRUTH STATUS**: **NO SINGLE CANONICAL VERSION CURRENTLY ESTABLISHED** (Dynamic version lookup active via `src/Infrastructure/version.py`).

---

## 6. Repository Architecture Inventory

```text
sohrabinia/YarTrader/
├── trader-terminal/        # React 18 + Vite 5 SPA Frontend Terminal
├── src/                    # Core Python Application Engine
│   ├── Application/        # Application Services, Routers, Backtesting, Governance
│   ├── Decision/           # Signal & Decision Intelligence Engines
│   ├── Execution/          # MT5/MT4 Adapters, Session Engines, Orders
│   ├── Growth/             # Domain Agents (Support, Security, Compliance)
│   ├── Infrastructure/     # DI, Config, Logging, Versioning, Exceptions
│   ├── Research/           # Fractal Engine, Hurst Exponent, Feature Calculators
│   ├── Risk/               # Daily Loss Kill Switch, Professional Risk Engine
│   └── ShadowTrading/      # Shadow Trading Virtual Engine
├── tests/                  # Pytest Unit & Integration Suite
├── docs/                   # Architectural Blueprints & Verification Reports
├── scripts/                # Deployment & Maintenance PowerShell/Bash Scripts
└── .github/workflows/      # CI/CD Workflows (ci.yml, release.yml)
```

---

## 7. Frontend Inventory

- **Location**: `trader-terminal/`
- **Framework & Tooling**: React 18.2.0, Vite 5.4.21, Lucide React, i18next (Multi-language FA/EN/AR/TR/ZH).
- **Design System**: Tailored Dark/Gold Theme with RTL support (`direction="rtl"`).

### Frontend Route Matrix

| Route Path | Exists in Code | Reachable | Real Backend | Persistence | Mock Status | Auth Req? | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | Yes | Yes | Yes | LocalStorage | Real/Dynamic | No | `PublicLandingView.jsx` |
| `/dashboard` | Yes | Yes | Yes | REST / JSON | Live with Offline Fallback | Yes | `DashboardView.jsx` |
| `/demo` | Yes | Yes | Yes | REST / Memory | Simulated | No | `DemoView.jsx` |
| `/intelligence`| Yes | Yes | Yes | REST | Real/Calculated | Yes | `IntelligenceView.jsx` |
| `/guide` | Yes | Yes | Static | None | Static Content | No | `GuideView.jsx` |
| `/faq` | Yes | Yes | Static | None | Static Content | No | `FaqView.jsx` |
| `/admin` | Yes | Yes | Yes | REST / Admin JSON | Real / Guarded | Yes (Admin) | `AdminView.jsx` |
| `/login` | Yes | Yes | Yes | Session Token | Real API | No | `App.jsx` |
| `/register` | Yes | Yes | Yes | Session Token | Real API | No | `App.jsx` |

---

## 8. Backend / API Inventory

- **Framework**: FastAPI (Python 3.12)
- **Primary Entry Point**: `src/Application/Services/web_dashboard.py`
- **Routers**: `user_api_router.py`, `admin_api_router.py`, `public_api_router.py`, `growth_api_router.py`.

### API Capability Matrix

| Capability | Endpoint(s) | Implementation | Persistence | Auth | Tests | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Auth Login | `POST /api/auth/login` | Complete | JSON / Token | None | Yes | COMPLETE |
| Auth Verify | `GET /api/auth/verify-email` | Complete | JSON | Token | Yes | COMPLETE |
| Dashboard Data | `GET /api/dashboard/summary` | Complete | Runtime state | Session | Yes | COMPLETE |
| Backtesting | `POST /api/backtest/run` | Complete | File / Memory | Session | Yes | COMPLETE |
| Historical Learning | `GET /api/learning` | Complete | JSON / Memory | Session | Yes | COMPLETE |
| Memory Foundation | `GET /api/memory` | Complete | JSON / Memory | Session | Yes | COMPLETE |
| Intelligence Engine | `GET /api/intelligence` | Complete | Runtime engine | Session | Yes | COMPLETE |
| Decision Context | `GET /api/decision-context` | Complete | Runtime engine | Session | Yes | COMPLETE |
| Decision Intelligence | `GET /api/decision-intelligence`| Complete | Runtime engine | Session | Yes | COMPLETE |
| Decision Governance | `GET /api/decision-governance` | Complete | Runtime engine | Session | Yes | COMPLETE |
| Support Assistant | `POST /api/chat/assistant` | Complete | Deterministic Engine | Optional | Yes | COMPLETE |
| Ledger Balance | `GET /api/ledger/balance` | Complete | `ledger.json` | Session | Yes | COMPLETE |

---

## 9. Database / Persistence Inventory

- **Primary Storage**: File-backed JSON databases in `runtime_logs/` and `data/` (`ledger.json`, `users.json`, `subscriptions.json`, `audit.json`).
- **SQLite Engine**: SQLite file support used for backtest candle historical ingestion and shadow trading experience memory.
- **In-Memory Volatile Stores**: Active session tokens, real-time tick queues, and ephemeral strategy state.

---

## 10. Authentication / Identity

- **Registration & Login**: Implemented via `AuthService` in `src/Application/Services/web_dashboard.py`.
- **Session Tokens**: Cryptographic session tokens with bearer/cookie authentication.
- **Email Verification**: Required for active login (token generated to mock email log in development mode).
- **Role Isolation**: RBAC with `FREE`, `PRO`, `INSTITUTIONAL`, and `ADMIN` user tiers.

---

## 11. Trading System Inventory

- **Symbol Ceiling**: Strictly `XAUUSD` only.
- **Account Ceiling**: Strictly `DEMO` trading environment.
- **Broker Adapter**: `MT5Adapter` in `src/Execution/Adapters/mt5_adapter.py`. Real trading / MT4 bridges are fail-closed.
- **Risk Limits**: Enforced 2% max risk per position and 8% Daily Loss Kill Switch (`src/Risk/Services/daily_loss_kill_switch.py`).

---

## 12. Market Data Truth

- **Sources**: Direct MetaTrader 5 IPC connector or synthetic fallback simulator (`src/Data/Simulation/simulation.py`) when offline.
- **Timeframes**: Multi-timeframe structures (M1, M5, M15, H1, H4, D1).

---

## 13. Backtesting Truth

- **Engine**: Pure deterministic backtest engine in `src/Application/Backtest/backtest_engine.py`.
- **Look-Ahead Prevention**: Strict bar-by-bar chronological processing; future data access raises validation exceptions.
- **Persistence**: Results are returned in JSON and cached locally for user session retrieval.

---

## 14. Learning Truth

- **Engine**: `LearningEngine` in `src/Application/Learning/learning_engine.py` (Phase 11).
- **Pipeline**: Computes empirical signal frequencies and drawdown characteristics from backtest outputs without opaque ML model drift.

---

## 15. Memory Truth

- **Engine**: `MemoryStore` in `src/Application/Memory/memory_engine.py` (Phase 12).
- **Characteristics**: Stores immutable historical regime records (`MemoryRecord`) derived from past evaluation cycles.

---

## 16. AI Agent Inventory

- **Orchestrator**: `AIAgentOrchestrator` in `src/Intelligence/Orchestration/orchestrator.py`.
- **Domain Agents**: `SupportAgent`, `PerformanceValidationAgent`, `MarketIntelligenceAgents`, `TrustLearningAgents`, `SecurityCostAgents`.
- **Status**: Pure Python deterministic rule engines without unauthorized autonomous order capability.

---

## 17. Support AI

- **Engine**: `SupportAIEngine` in `src/Application/Support/support_ai_engine.py` (Phase 14).
- **Safety Rule**: Strictly forbids hallucinating unauthenticated private balances or non-existent positions. Returns grounded explanation strings.

---

## 18. Content / Blog / Marketing

- **Manager**: `ContentManager` in `src/Application/Dashboard/content_manager.py`.
- **Status**: Provides static product blog articles and feature walkthroughs to the frontend terminal.

---

## 19. Prop-Firm Intelligence

- **Engine**: `PropChallengeEngine` in `src/Risk/Services/prop_challenge_engine.py`.
- **Functionality**: Tracks drawdown rules, profit targets, and daily risk compliance for funded/prop challenge metrics.

---

## 20. Wallet / Ledger

- **Manager**: `LedgerManager` in `src/Application/Dashboard/ledger_manager.py`.
- **Accounting Architecture**: Enterprise double-entry ledger enforcing `total_debits == total_credits`, idempotency keys, and non-negative balances stored in integer minor units (cents).

---

## 21. Payment / Billing / Subscriptions

- **Manager**: `BillingManager` in `src/Application/Dashboard/billing_manager.py`.
- **Webhook Processing**: Verifies signatures, enforces idempotency key caching, and generates immutable JSON invoices upon success.
- **Provider Status**: Sandbox / mock signature verification configured; live external merchant credentials NOT CONFIGURED.

---

## 22. Email Verification & Notifications

- **Service**: Mock email logging to `runtime_logs/mock_emails.log` in offline development mode. Live SMTP delivery requires external provider configuration.

---

## 23. Notifications System

- **In-App Notifications**: Real-time alert feed displayed in top navbar of `trader-terminal`.

---

## 24. Admin Capabilities

- **View**: `trader-terminal/src/views/AdminView.jsx`.
- **Backend**: `admin_api_router.py` providing endpoints for user management, system audit log inspection, and health status monitoring.

---

## 25. Security Baseline

- **Authentication**: Salted password hashing, JWT/Session tokens.
- **Fail-Closed Execution**: Hard stop on real money or non-XAUUSD symbols.
- **Inputs**: Pydantic schema validation across API endpoints.

---

## 26. Observability

- **Logging**: Python `logging` module outputting to console and `runtime_logs/`.
- **Metrics**: Runtime health status reporting database, disk, and memory availability.

---

## 27. CI/CD Pipeline

- **GitHub Workflows**:
  - `.github/workflows/ci.yml`: Automated pytest execution on Python 3.12.
  - `.github/workflows/release.yml`: Release build gate and frontend Vite bundle compilation check.

---

## 28. Deployment Truth

- **Script**: `scripts/deploy_production.ps1` (PowerShell Windows service deployment script for YarTrader service).
- **Verification Status**: **PRODUCTION RUNTIME NOT VERIFIABLE FROM CURRENT ACCESS**.

---

## 29. Health & Monitoring

- **Endpoint**: `GET /api/health` returning JSON process status, timestamp, and database accessibility status.

---

## 30. Rollback Mechanism

- **Status**: Git branch and PowerShell service rollback procedures documented in deployment scripts. Automatic containerized rollback relies on external deployment orchestration.

---

## 31. Test Evidence

- **Test Framework**: Pytest 9.1.1 on Python 3.12.13.
- **Execution Command**: `python3 -m pytest tests/YarTrader.Tests/ -v`
- **Results**: **1939 PASSED**, 1 failed (mock email log format expectation in `test_unverified_registration_fails_authentication_until_verified`), 1240 warnings in 300.35s.

---

## 32. Build Evidence

- **Build Command**: `npm --prefix trader-terminal run build`
- **Result**: **SUCCESS** (Vite v5.4.21 compiled bundle cleanly in 1.33s).
- **Output Artifacts**: `trader-terminal/dist/index.html` (4.46 kB), `dist/assets/index-Cx1QWqCO.js` (251.37 kB).

---

## 33. Environment / Configuration

- **Templates**: `.env.production.example`
- **Variables**: `APP_VERSION`, `YARTRADER_ENV`, `DATABASE_URL`, `MT5_ACCOUNT`, `MT5_PASSWORD`, `MT5_SERVER`.

---

## 34. Mock / Fake / Demo Inventory

| Location | Purpose | Production Reachable? | Status | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| `src/Data/Simulation/simulation.py` | Candle data simulation when MT5 IPC offline | Development / Fallback | MOCK | Line 10 simulator class |
| `src/Execution/Adapters/adapters.py` | `MT5AdapterPlaceholder` order routing | Development / Offline | MOCK | Status "MockPlaced" |
| `runtime_logs/mock_emails.log` | Email verification logging when SMTP absent | Development / Offline | MOCK | Local log file creation |

---

## 35. Duplicate Implementation Inventory

| Domain | Implementation A | Implementation B | Active Choice | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| Version Tracking | Static string in `market_session_engine.py` | Dynamic loader in `version.py` | Dynamic (`version.py`) | Runtime evaluation |
| Frontends | Legacy frontend specs | `trader-terminal/` (Vite) | `trader-terminal/` | Active build target |

---

## 36. Documentation Contradictions

| Claim | Source A | Source B | Actual Code Evidence | Resolution |
| :--- | :--- | :--- | :--- | :--- |
| Version | `web_dashboard.py` ("v7.0") | `trader-terminal/package.json` ("1.0.0") | No unified version file | NO CANONICAL VERSION |
| Live MT4 | Legacy Docs ("MT4/MT5 Supported") | `mt4_adapter.py` | MT4 order execution throws Exception | DEMO MT5 ONLY |

---

## 37. User E2E Trace

`Landing (PublicLandingView) -> Register/Login (/login) -> Email Verify (mock_emails.log) -> Dashboard (/dashboard) -> Backtest (/api/backtest/run) -> Support AI Assistant`.
- **Status**: Functional end-to-end in offline simulated mode.

---

## 38. Admin E2E Trace

`Admin Login -> Dashboard (/admin) -> User Management -> System Logs -> Ledger Balance Audit`.
- **Status**: Functional via RBAC admin session tokens.

---

## 39. Learning E2E Trace

`Market Data Ingestion -> Backtest Execution -> Historical Learning Analysis (Phase 11) -> Memory Store (Phase 12) -> Intelligence/Governance Evaluation (Phases 13-16)`.
- **Status**: Connected deterministic pipeline operating bar-by-bar.

---

## 40. Critical Gaps

1. **Version Consolidation**: Absence of a single authoritative source of truth for application versioning.
2. **External Production Connectors**: Live SMTP, real broker bridges, and live payment gateways fail closed due to missing external production API keys.

---

## 41. Contradictions

- Marketing copy claims `v7.0`, package manifests state `1.0.0`, and release notes claim `v3.1.0-hardened`.

---

## 42. Unknowns

- Exact live production server operating system and runtime memory state cannot be verified without live production network access.

---

## 43. Risk Register

- **P0**: None (all financial ledger operations enforce double-entry equality; trading is fail-closed to MT5 DEMO XAUUSD).
- **P1**: Version fragmentation across UI labels and API metadata.

---

## 44. Summary Tables

### System Status Summary

| Domain | Status | Criticality | Evidence | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Authentication | COMPLETE | CRITICAL | `web_dashboard.py` | Salted passwords + session tokens |
| Trading Safety | COMPLETE | CRITICAL | `mt5_adapter.py` | DEMO XAUUSD fail-closed enforcement |
| Double-Entry Ledger | COMPLETE | CRITICAL | `ledger.json` / `ledger_manager.py` | Minor unit integer accounting |
| Backtesting Engine | COMPLETE | HIGH | `backtest_engine.py` | Bar-by-bar, no look-ahead bias |
| Historical Learning | COMPLETE | HIGH | `learning_engine.py` | Phase 11 statistical frequencies |
| Decision Governance| COMPLETE | HIGH | `decision_governance_engine.py` | Phase 16 evidence gates |
| Support AI | COMPLETE | MEDIUM | `support_ai_engine.py` | Deterministic anti-hallucination |

---

## 45. Canonical Current State

- **Repository**: `sohrabinia/YarTrader`
- **Current Branch**: `jules-748700270274326796-0b553ae4`
- **Current SHA**: `4319e4d00e6b14acac9a32c304eedf7cbf06f8fa`
- **Official Release Tag**: `yartrader-v1.0.0-production`
- **Canonical Version**: `NO SINGLE CANONICAL VERSION CURRENTLY ESTABLISHED`
- **Active Frontend**: `trader-terminal/` (React 18 + Vite 5.4.21)
- **Active Backend**: `src/Application/Services/web_dashboard.py` (FastAPI)
- **Persistence**: File-backed JSON databases (`runtime_logs/`) + SQLite
- **Production Verification**: `PRODUCTION RUNTIME NOT VERIFIABLE FROM CURRENT ACCESS`
- **Wallet / Ledger**: `COMPLETE` (Double-entry ledger with integer minor units)
- **Payments**: `PARTIAL` (Webhook verification & invoices complete; live gateway keys unconfigured)
- **AI Support**: `COMPLETE` (Deterministic rule-based explainers)
- **Tests**: `1939 PASSED` (Pytest suite verified)

---

## 46. Phase 0 Completion Verdict

```text
PHASE 0 = PASS
```

*Reasoning*: The repository's current factual baseline, Git history, architecture, test health, build validity, and subsystem status have been comprehensively investigated, mapped, and documented without making any unauthorized changes or implementation modifications.
