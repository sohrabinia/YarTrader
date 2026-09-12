# YarTrader — CTO Project State

## 1. Snapshot

**Product Mission:** YarTrader (TradeYar AI) is an enterprise-grade Autonomous Market Intelligence & Trading Platform designed around APES-FIN Clean Architecture principles. It delivers deterministic market data processing, multi-strategy signal generation, explainable decision context, governance rules, and prop-firm challenge intelligence with strict passive non-trading execution boundaries in default runtime modes.

**Overall System Completion:** Core product infrastructure, multi-layer intelligence engines (Phases 0–16), double-entry accounting ledger (Phase 17), SaaS pricing & billing engine (Phase 18), and administrative SRE control centers are complete, integrated, and verified by 1,843 passing tests (100% green).

**Core System Capabilities:**
- **Deterministic Strategy Engines:** Spike (Phase 7), Range (Phase 8), and Trend (Phase 9) engines with strict zero look-ahead bias and MTR/channel/SMA crossover math.
- **Backtesting & Learning:** Deterministic walk-forward backtest engine (Phase 10), historical cutoff learning engine (Phase 11), and structured experience store (Phase 12 Memory Engine).
- **Intelligence & Decision Pipelines:** Statistical context summary (Phase 13), explainable decision context engine (Phase 14), decision intelligence sample/quality scoring (Phase 15), and deterministic governance check engine (Phase 16).
- **Financial & Commercial Layer:** Double-entry ledger with debit/credit balance invariants (Phase 17), billing/invoicing state machine with webhook signature verification (Phase 18), and Business Catalog manager.
- **User & Admin Experience:** Multilingual React SPA (`trader-terminal`) supporting Google OIDC OAUTH authentication, SRE Admin Console, blog reader, and interactive chat assistant (`POST /api/chat/assistant`).

`Evidence: src/Application/Services/web_dashboard.py`
`Evidence: tests/YarTrader.Tests/`
`Evidence: docs/YARTRADER_CANONICAL_BASELINE.md`

---

## 2. Repository Truth

- **Repository:** `sohrabinia/YarTrader`
- **Current Branch:** `jules-3746611703331896742-40b33e69`
- **HEAD SHA:** `e258c3a292f58cebb45418ea723ebfecf78db9e9`
- **origin/main SHA:** `e258c3a292f58cebb45418ea723ebfecf78db9e9`
- **Branch Divergence:** HEAD is identical to `origin/main` (0 commits ahead, 0 commits behind).
- **Working-Tree State:** Clean (1 untracked documentation file created by this task: `docs/CTO_PROJECT_STATE.md`).
- **Latest Relevant Commits:**
  - `e258c3a292f58cebb45418ea723ebfecf78db9e9` — Merge pull request #249 from `sohrabinia/jules-6897971689246642035-ad323f5d-15526703867009158558`
- **Reconciliation PR State:** The reconciliation work covering PRs #253, #255, #256, and #257 has been fully reconciled and merged into `origin/main` prior to this snapshot.
  `Evidence: docs/audit/OPEN_PR_TRUTH_INVENTORY_2026-09-12.md`
- **Canonical Version Identity:** System version resolves dynamically to Version `7.0` (commit `e258c3a292f58cebb45418ea723ebfecf78db9e9`, environment `production`) via `src/Infrastructure/version.py`.
- **Deployment State:** Configured for self-hosted Windows Server 2022 deployment running as a native Windows Service via `app/workers/service.py` and deployed using `scripts/deploy_production.ps1`.

`Evidence: observed Git state`
`Evidence: src/Infrastructure/version.py`
`Evidence: scripts/deploy_production.ps1`

---

## 3. Architecture

YarTrader implements a strictly separated Clean Architecture layout (APES-FIN) enforcing clear unidirectional dependencies: Frontend UI -> Application API / Gateway -> Core Domain Engines -> Infrastructure Adapters.

### Architectural Breakdown:

#### 1. Frontend Layer (SPA)
- **FACT:** Implemented in `trader-terminal/` using React 18, Vite, Shadcn/ui primitives, and Lucide icons.
- **FACT:** Serves responsive dark-mode UI with full 4-locale i18n support (`fa`, `en`, `tr`, `ar`).
- **FACT:** Communicates with backend REST API using Google OIDC Bearer token authentication stored in browser state (`trader-terminal/src/App.jsx`).

#### 2. Backend Application Service / API Gateway
- **FACT:** Implemented in Python using FastAPI (`src/Application/Services/web_dashboard.py` and `src/Application/Services/admin_api_router.py`).
- **FACT:** Exposes 125+ HTTP endpoints spanning Authentication, Market Data, Strategy, Backtesting, Learning, Memory, Intelligence, Decision Context, Governance, Prop Challenge, Ledger, Billing, Support Chat, Content Management, and Admin Operations.

#### 3. Core Domain & Intelligence Engines
- **FACT:** Strategy Engines: `SpikeStrategyEngine` (`src/Application/Strategy/spike_strategy.py`), `RangeStrategyEngine` (`src/Application/Strategy/range_strategy.py`), `TrendStrategyEngine` (`src/Application/Strategy/trend_strategy.py`).
- **FACT:** Backtest Engine: `BacktestEngine` (`src/Application/Backtest/backtest_engine.py`) executing walk-forward zero look-ahead evaluations.
- **FACT:** Learning & Memory: `LearningEngine` (`src/Application/Learning/learning_engine.py`) and `MemoryEngine` (`src/Application/Memory/memory_engine.py`).
- **FACT:** Intelligence & Governance: `IntelligenceEngine` (`src/Application/Intelligence/intelligence_engine.py`), `DecisionContextEngine` (`src/Application/Decision/decision_context_engine.py`), `DecisionIntelligenceEngine` (`src/Application/Decision/decision_intelligence_engine.py`), `DecisionGovernanceEngine` (`src/Application/Governance/decision_governance_engine.py`).
- **FACT:** Support AI: `SupportAIEngine` (`src/Application/Support/support_ai_engine.py`) providing grounded explanations without trade execution power.

#### 4. Execution & MetaTrader Boundaries
- **FACT:** All execution routes fail closed or default to PASSIVE / SIMULATED modes unless explicit live flags are set.
- **FACT:** `MetaTraderProvider` (`src/Infrastructure/Providers/metatrader_provider.py`) connects to MT5 terminals via official Python API (`MetaTrader5`), active strictly when running on native Windows hosts.
- **INFERENCE:** On Linux sandbox environments, MT5 IPC is unavailable, so provider falls back gracefully to synthetic/historical market data or raises controlled connection exceptions.

#### 5. Persistence & Infrastructure
- **FACT:** Data state is stored in deterministic JSON files under `runtime_logs/` and `data/` (e.g., `runtime_logs/ledger_store.json`, `runtime_logs/billing_store.json`, `runtime_logs/prop_challenge_config.json`, `data/content/content_store.json`).
- **FACT:** `src/Infrastructure/version.py` acts as single source of truth for release identity.

`Evidence: src/Application/Services/web_dashboard.py`
`Evidence: src/Application/Services/admin_api_router.py`
`Evidence: docs/architecture/YARTRADER_ARCHITECTURE_DECISION_RECORD.md`

---

## 4. Completed Phases

Below is the verified completion state of all existing roadmap phases based strictly on repository code and test evidence:

| Phase | Official Title | Completion Status | Evidence Files / Commits | Test Suite Pass | Remaining Gaps |
|---|---|---|---|---|---|
| **Phase 0** | Truth Baseline & Forensic Audit | `COMPLETE` | `YARTRADER_CANONICAL_BASELINE.md` | Pass | None |
| **Phase 1** | Architecture & Boundaries Cleanup | `COMPLETE` | `docs/architecture/` | Pass | None |
| **Phase 2** | Release Identity & Build System | `COMPLETE` | `src/Infrastructure/version.py` | Pass | None |
| **Phase 3** | Production Frontend | `COMPLETE` | `trader-terminal/` | Pass | None |
| **Phase 4** | Auth & Identity Authority | `COMPLETE` | `src/Application/Dashboard/auth_service.py` | Pass | None |
| **Phase 5** | Core User Journey | `COMPLETE` | `tests/YarTrader.Tests/Services/test_core_user_journey_phase5.py` | Pass | None |
| **Phase 6** | Market Data Service | `COMPLETE` | `src/Application/Services/market_data_service.py` | Pass | None |
| **Phase 7** | Spike Strategy Engine | `COMPLETE` | `src/Application/Strategy/spike_strategy.py` | Pass | None |
| **Phase 8** | Range Strategy Engine | `COMPLETE` | `src/Application/Strategy/range_strategy.py` | Pass | None |
| **Phase 9** | Trend Strategy Engine | `COMPLETE` | `src/Application/Strategy/trend_strategy.py` | Pass | None |
| **Phase 10** | Walk-Forward Backtest Engine | `COMPLETE` | `src/Application/Backtest/backtest_engine.py` | Pass | None |
| **Phase 11** | Deterministic Learning Engine | `COMPLETE` | `src/Application/Learning/learning_engine.py` | Pass | None |
| **Phase 12** | Memory Foundation Engine | `COMPLETE` | `src/Application/Memory/memory_engine.py` | Pass | None |
| **Phase 13** | Statistical Intelligence Engine | `COMPLETE` | `src/Application/Intelligence/intelligence_engine.py` | Pass | None |
| **Phase 14** | Decision Context & Support AI Engine | `COMPLETE` | `src/Application/Decision/decision_context_engine.py` | Pass | None |
| **Phase 15** | Decision Intelligence & Content Lifecycle | `COMPLETE` | `src/Application/Decision/decision_intelligence_engine.py` | Pass | None |
| **Phase 16** | Decision Governance & Prop Challenge | `COMPLETE` | `src/Application/Governance/decision_governance_engine.py` | Pass | None |
| **Phase 17** | Double-Entry Ledger & Wallet | `COMPLETE` | `src/Application/Dashboard/ledger_manager.py` | Pass | None |
| **Phase 18** | Payment, Billing & SaaS Pricing | `COMPLETE` | `src/Application/Dashboard/billing_manager.py` | Pass | None |

`Evidence: tests/YarTrader.Tests/` (1,843 passing tests)
`Evidence: docs/architecture/YARTRADER_MASTER_ROADMAP_STATUS.md`

---

## 5. Locked Roadmap Position

The YarTrader engineering roadmap is locked to a 30-Phase progression sequence:

- **Completed Phases:** Phases 0 through 18.
- **Current Phase:** Phase 18 (Payment, Billing & SaaS Pricing — fully implemented and verified).
- **Next Official Phase:** Phase 19 (Advanced Multi-Asset Risk & Portfolio Allocation Engine).
- **Phases Intentionally Not Started:** Phases 19 through 30.
- **Explicit Exclusions:**
  - No direct live trading execution on real broker money without prior human approval gate and explicit config toggles.
  - No AI/LLM non-deterministic decision making inside core signal/governance execution paths.
- **Current Stop Boundary:** Phase 18 complete. Do NOT initiate Phase 19 implementation until explicit product authorization is issued.

`Evidence: docs/architecture/YARTRADER_MASTER_ROADMAP_STATUS.md`
`Evidence: YARTRADER_COMPLETION_ROADMAP.md`

---

## 6. Authentication / Authorization State

### Implemented Model:
- **FACT:** User authentication is anchored by **Google OIDC / Google Identity Services** in `trader-terminal/src/App.jsx` and verified server-side in `src/Application/Dashboard/auth_service.py`.
- **FACT:** Session management uses cryptographically secure tokens (`tkn-<hex>`) generated via `AuthService.create_session()`.
- **FACT:** Session verification tracks active sessions, device info, and revocation via `DeviceTracker` (`src/Application/Dashboard/device_tracker.py`).
- **FACT:** Admin routes are guarded by `check_admin_guard()` in `web_dashboard.py` and `enforce_admin_token()` in `admin_api_router.py`.

### Security Remediation Verification:
- **FACT (Query-String Token Removal):** REST endpoints do NOT accept query-string authentication tokens in production security paths. `check_admin_guard` extracts `Authorization: Bearer <token>` from request headers.
- **FACT (No Unsafe Admin Fallback):** Unauthenticated or invalid token requests are rejected with `HTTP 401 Unauthorized` or `HTTP 403 Forbidden`. Default administrator email fallbacks (`admin@yartrader.app`) have been removed from production guards.
- **FACT (Legacy Form Removal):** Primary `/login` view presents strictly Google OIDC sign-in (`trader-terminal/src/App.jsx`).

`Evidence: src/Application/Dashboard/auth_service.py`
`Evidence: src/Application/Services/web_dashboard.py`
`Evidence: src/Application/Services/admin_api_router.py`

---

## 7. Security / Trading Safety Model

### Confirmed Security Controls:
1. **PBKDF2-HMAC-SHA256 Hashing:** 100,000+ iterations with persistent lockout audit tracking (5 failed attempts trigger persistent lockout).
2. **Fail-Closed Authorization:** Missing or expired bearer tokens immediately return `401/403` HTTP status codes.
3. **Webhooks Verification:** Stripe/Gateway billing webhooks require valid `X-Gateway-Signature` cryptographic signatures checked against `BILLING_WEBHOOK_SECRET`.
4. **Content Field Allowlists:** `ContentManager` updates validate against strict domain field allowlists, rejecting unknown parameters (e.g. `is_admin`).

### Trading Safety & Risk Boundaries:
1. **Passive Runtime Execution:** System generates advisory signals, backtests, and prop evaluation metrics without autonomous order submission to live markets.
2. **Prop Challenge Hard Rules:** Multi-phase rule validation in `PropChallengeEngine` enforces daily drawdown caps, max loss limits, and automatic `TRADING_HALTED` state triggers upon breach.
3. **Multi-Account Isolation:** Multi-account state storage (`runtime_logs/prop_challenge_config.json`) isolates metrics, balances, and halt states per user/account ID.

### Known Limitations:
- Local file-based storage (`runtime_logs/`) requires file locking for high-concurrency multi-process backend workers.

`Evidence: src/Application/Dashboard/auth_service.py`
`Evidence: src/Risk/Services/prop_challenge_engine.py`
`Evidence: src/Application/Dashboard/content_manager.py`

---

## 8. YarOperator Integration Status

- **FACT:** `sohrabinia/YarTrader` serves as the primary product, trading platform, user UI, and identity authority.
- **FACT:** `sohrabinia/YarOperator` is an external administrative/orchestration system for server management and background automation.
- **FACT:** Admin routes under `/api/admin/` interact with administrative services. When external YarOperator operations are invoked, requests propagate Google OIDC identity headers and require `OPERATOR_SERVER_SECRET`.
- **FACT:** If `OPERATOR_SERVER_SECRET` is missing or the external YarOperator server is unreachable, server-to-server operations fail closed with `HTTP 503 Service Unavailable`.
- **FACT:** YarOperator does NOT possess independent user login authority for YarTrader product accounts.

`Evidence: src/Application/Services/admin_api_router.py`
`Evidence: src/Application/Services/web_dashboard.py`

---

## 9. Production / Deployment State

### Verification & Build Pipeline:
- **FACT:** Backend testing runs via `python3 -m pytest tests/` (1,843 unit/integration tests passing cleanly).
- **FACT:** Frontend compilation is performed via `npm ci` and `npm run build` in `trader-terminal/`, generating static build artifacts under `trader-terminal/dist/`.
- **FACT:** `web_dashboard.py` mounts `trader-terminal/dist` to serve the SPA static assets directly.

### Production Environment:
- **FACT:** Target production OS is **Windows Server 2022** running YarTrader as a Windows Service (`app/workers/service.py`).
- **FACT:** Deployment automation script: `scripts/deploy_production.ps1`.
- **FACT:** Health Verification Endpoint: `GET /api/health` returns version string, git commit SHA, active worker health, and system environment info.

`Evidence: scripts/deploy_production.ps1`
`Evidence: app/workers/service.py`
`Evidence: .github/workflows/ci.yml`

---

## 10. Operator Mission / System Role

YarTrader functions as the authoritative core platform:
1. **Primary Product Authority:** Owns client-facing UI, market data ingestion, strategy execution engines, backtesting, cognitive decision trace, wallet ledger, and SaaS subscription billing.
2. **Identity & Security Authority:** Manages user authentication, session security, role authorization, and tenant account isolation.
3. **YarOperator Relationship:** YarTrader acts as the client/caller to YarOperator's orchestration endpoints, delegating system-level host maintenance tasks while retaining all product domain authority.

`Evidence: docs/architecture/YARTRADER_ARCHITECTURE_DECISION_RECORD.md`

---

## 11. Currently Missing Capabilities

Supported strictly by repository evidence, the following items are intentionally absent or not yet reached:

1. **Live Broker Order Execution:** Real money order execution is disabled in code by design; default execution mode is PASSIVE / SIMULATED.
2. **Native Linux MetaTrader IPC:** MetaTrader 5 API integration requires a Windows host environment with native MT5 terminal installation.
3. **Automated Cloud Push-to-Deploy:** CI/CD workflows (`.github/workflows/release.yml`) perform release verification gates; physical server deployment remains self-hosted via PowerShell scripts (`deploy_production.ps1`).

`Evidence: src/Infrastructure/Providers/metatrader_provider.py`
`Evidence: .github/workflows/release.yml`

---

## 12. Known Risks / Open Questions

### Confirmed Issues:
- None currently blocking execution or tests (1,843 tests passing).

### Known Limitations:
- File-based persistence in `runtime_logs/` requires eventual migration to SQL/PostgreSQL database storage if concurrent worker scaling increases significantly.

### Architectural Decisions Pending:
- Formalization of Phase 19 (Multi-Asset Portfolio Allocation Engine) scope and interface contracts.

### Unknowns Requiring Investigation:
- Live MT5 terminal IPC latency and execution slip on production Windows Server under high volatility market regimes.

`Evidence: docs/audit/OPEN_PR_TRUTH_INVENTORY_2026-09-12.md`

---

## 13. Current Next-Step Boundary

- **Completed State:** Phases 0 through 18 are 100% complete, tested, and merged into `origin/main`.
- **Completed Reconciliation:** PRs #253, #255, #256, and #257 have been fully reconciled and merged.
- **What Must NOT Be Worked On Yet:** Do NOT start Phase 19 implementation or introduce unapproved external features without explicit product sign-off.
- **Next Official Step:** Phase 19 Architecture & Design Review (Multi-Asset Portfolio Allocation Engine).
- **Required Evidence Before Advancing:** Complete Phase 19 spec documentation and architectural decision record review.

`Evidence: docs/architecture/YARTRADER_MASTER_ROADMAP_STATUS.md`

---

## 14. CTO Handoff for Future Sessions

### Operational Handoff Summary:

#### 1. Where are we?
- **Repository:** `sohrabinia/YarTrader`
- **Branch:** `jules-3746611703331896742-40b33e69`
- **HEAD SHA:** `e258c3a292f58cebb45418ea723ebfecf78db9e9`
- **origin/main SHA:** `e258c3a292f58cebb45418ea723ebfecf78db9e9`
- **Working Tree:** Clean (1 documentation file created by this task).
- **Roadmap Position:** Phase 18 Complete.

#### 2. What has been verified?
- All 1,843 backend tests pass cleanly (`python3 -m pytest tests/`).
- Clean Architecture boundaries are intact across UI, API, Domain, and Infrastructure.
- Google OIDC auth and fail-closed admin guards are fully enforced.
- Double-entry ledger invariants and SaaS billing webhooks are operational.

#### 3. What must I NOT assume?
- Do NOT assume live trading executes real broker orders (system is passive by design).
- Do NOT assume MetaTrader 5 IPC works natively inside Linux Docker/sandbox containers (requires Windows Server).
- Do NOT assume legacy password registration or query-string token auth exists (both removed).

#### 4. Official Roadmap Position:
- Phases 0–18: COMPLETE.
- Phase 19+: NOT STARTED / PENDING.

#### 5. Starting Point for Next Implementation Task:
```text
Repository : sohrabinia/YarTrader
Branch     : jules-3746611703331896742-40b33e69
HEAD SHA   : e258c3a292f58cebb45418ea723ebfecf78db9e9
origin/main: e258c3a292f58cebb45418ea723ebfecf78db9e9
Working Tree: Clean
```
