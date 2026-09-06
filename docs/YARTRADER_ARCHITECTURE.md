# YarTrader Canonical System Architecture & Operational Blueprint

## 1. Executive Overview & Single Repository Architecture

`sohrabinia/YarTrader` is the single, authoritative, monorepo home for all YarTrader software assets, including:
* **Product Core:** XAUUSD multi-timeframe market intelligence, fractal mathematical feature engine, risk management controls (2% max per-trade ceiling, 8% daily loss kill switch), and MT5 DEMO execution boundaries.
* **Central Agent Brain:** Multi-agent orchestration engine (`AIAgentOrchestrator` in `src/Intelligence/Orchestration/orchestrator.py`).
* **Product & Growth Agents:** Multi-domain agents across Growth, Content, Distribution, Security, Trust, and Performance (`src/Growth/Agents/`).
* **Content & Blog Platform:** Localized UI components, SEO page generators, and multilingual content lifecycle.
* **DevOps & Release Systems:** Deterministic release workflows (`.github/workflows/release.yml`), post-deployment health verification, and operational risk assessment policy.

The former `sohrabinia/yartrader.DevOps` repository is deprecated as an active architectural dependency and serves strictly as a historical migration reference.

---

## 2. Target Logical Architecture & Domain Separation

```text
                         YarTrader
                    ONE Git Repository
                            │
                            ▼
                  CENTRAL AGENT ORCHESTRATOR
                         / MAIN BRAIN
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
   PRODUCT AGENTS      CONTENT / BLOG     DEVOPS AGENT
          │                 │                 │
          │                 │                 ▼
          │                 │          RELEASE ANALYSIS
          │                 │                 │
          │                 │                 ▼
          │                 │        DETERMINISTIC POLICY
          │                 │                 │
          │                 │            ┌────┴────┐
          │                 │            ▼         ▼
          │                 │          BLOCK     APPROVE
          │                 │                        │
          │                 │                        ▼
          │                 │                     DEPLOY
          │                 │                        │
          │                 │                        ▼
          │                 │                     VERIFY
          │                 │                     │    │
          │                 │                   PASS  FAIL
          │                 │                     │    │
          │                 │                     ▼    ▼
          │                 │                  SUCCESS ROLLBACK
          │                 │
          └─────────────────┴─────────────────────────────
```

---

## 3. Central Agent Brain Verification & Inventory

The canonical Product Agent Brain is implemented at:
`src/Intelligence/Orchestration/orchestrator.py`

### Registered & Routable Components
* **`AIAgentOrchestrator`:** Primary orchestration loop coordinating task routing, agent lifecycle, state tracking, and error recovery.
* **`AgentRegistry`:** Centralized registry tracking agent capabilities, permissions, and health status.
* **`TaskRouter`:** Deterministic task router allocating requests to specialized agents based on capability signatures.

### Product & Growth Agent Inventory
1. **Content Agents (`src/Growth/Agents/ContentAgents.py`):** SEO content generation, article localization, and media asset management.
2. **Distribution Agents (`src/Growth/Agents/DistributionAgents.py`):** Multi-channel publishing, referral tracking, and newsletter orchestration.
3. **Market Intelligence Agents (`src/Growth/Agents/MarketIntelligenceAgents.py`):** XAUUSD regime tracking, MTF fractal context analysis, and pattern similarity search.
4. **Performance Validation Agents (`src/Growth/Agents/PerformanceValidationAgent.py`):** Trade outcome evaluation, shadow policy tracking, and statistical attribution.
5. **Security & Cost Agents (`src/Growth/Agents/SecurityCostAgents.py`):** API token cost metering, subscription tier gating, and runtime security scanning.
6. **Trust & Learning Agents (`src/Growth/Agents/TrustLearningAgents.py`):** User feedback loops, confidence calibration, and audit logging.
7. **User Growth Agents (`src/Growth/Agents/UserGrowthAgents.py`):** Onboarding workflows, trial management, and engagement analytics.

---

## 4. DevOps Operational Security & Control Plane Separation

To prevent LLM halluncinations or unauthorized system modifications from impacting production:

```text
Central Agent Brain
        ↓
DevOps Agent (Release Analysis & Assessment)
        ↓
Deterministic Policy Engine (Hard Fail-Closed Rules)
        ↓
Narrow Operational Executor (Explicit Scripted Workflows)
        ↓
Production Infrastructure
```

### Operational Rules
1. **Narrow Tools Only:** The DevOps capability operates through explicit, narrow interfaces (`inspect_release`, `collect_evidence`, `assess_risk`, `verify_health`). No arbitrary shell execution or database modification is permitted.
2. **Deterministic Precedence:** Deterministic CI/CD safety gates (pytest, frontend build compilation, diff check, health probes) always take precedence over AI proposals. If any deterministic check fails, the release is blocked regardless of AI confidence.
3. **Secret Isolation:** Production deployment secrets are accessible strictly within GitHub Actions protected release workflows and are never exposed to pull request review runners.

---

## 5. CTO Audit Reconciliation Matrix

An analysis comparing historical CTO audit claims against the current codebase state:

| Audit Claim | Current Status | Codebase Verification | Reconciled Reality |
| :--- | :--- | :--- | :--- |
| **Product is XAUUSD Research/Backtest Engine** | `HISTORICAL` | Codebase includes full FastAPI backend (`app/`), React frontend (`trader-terminal/`), and Multi-Agent system (`src/Growth/Agents/`). | YarTrader is a complete web platform and market intelligence runtime, not merely a backtest script. |
| **2% Max Risk Ceiling & 8% Daily Loss Switch** | `CONFIRMED` | `src/Risk/Services/professional_risk_engine.py` & `daily_loss_kill_switch.py` | Strict fail-closed risk bounds are programmatically enforced at the Risk Engine layer. |
| **MT5 DEMO Boundary & MT4 Rejection** | `CONFIRMED` | `src/Execution/Safety/demo_execution_gate.py` & `src/Execution/Adapters/mt4_adapter.py` | MT4 order submission is hard-rejected. MT5 is restricted strictly to DEMO accounts and XAUUSD. |
| **AIAgentOrchestrator Control** | `CONFIRMED` | `src/Intelligence/Orchestration/orchestrator.py` | Serves as the central orchestrator for core intelligence tasks and agent routing. |
| **Single Repository Setup** | `CONFIRMED` | `sohrabinia/YarTrader` | All domain capabilities reside in `YarTrader`; `yartrader.DevOps` is deprecated. |

---

## 6. Implementation Status Matrix

| Subsystem / Feature | Status | Execution Mechanism | Notes |
| :--- | :--- | :--- | :--- |
| **Single Repository Ownership** | `IMPLEMENTED` | `sohrabinia/YarTrader` | Complete domain consolidation in a single repository. |
| **Central Agent Brain** | `IMPLEMENTED` | `AIAgentOrchestrator` | Preserved in `src/Intelligence/Orchestration/orchestrator.py`. |
| **Product & Growth Agents** | `IMPLEMENTED` | `src/Growth/Agents/` | Active across 7 distinct domain modules. |
| **Blog & Content Engine** | `IMPLEMENTED` | `trader-terminal` & `docs/` | Multilingual UI, localized guides, and static asset delivery. |
| **Deterministic Release Gate** | `IMPLEMENTED` | `.github/workflows/release.yml` | Executes pytest, Vite build, `git diff --check`, and production health checks. |
| **Multilingual Health Probes** | `IMPLEMENTED` | `.github/workflows/release.yml` | Validates HTTP 200 OK for 8 localized routes + Vazirmatn font asset. |
| **AI Pre-Merge Code Review** | `SHADOW` | Operational Policy | Review outputs logged for evaluation; merge decisions remain deterministic. |
| **AI Operational Release Assessment**| `SHADOW` | Operational Policy | Release risk evaluation active in shadow mode without blocking deployment. |
| **Autonomous Production Deploy** | `PENDING` | Host CD Trigger | Production deployment triggered via verified host infrastructure hooks. |
| **Automated Version Rollback** | `PENDING` | Host CD Trigger | Version rollback triggers upon post-deployment verification failure. |
| **Legacy `yartrader.DevOps` Repo** | `DEPRECATED` | Archive Candidate | Migration source only; zero active production dependency. |
