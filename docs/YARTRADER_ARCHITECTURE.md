# YarTrader Canonical System Architecture & Operational Blueprint

## 1. Executive Overview & Single Repository Architecture

`sohrabinia/YarTrader` is the single, authoritative monorepo home for all YarTrader software assets, encompassing:
* **Product Core:** XAUUSD multi-timeframe market intelligence, fractal mathematical feature engine, risk management controls (2% max per-trade ceiling, 8% daily loss kill switch), and MT5 DEMO execution boundaries with hard MT4 rejection.
* **Central Agent Brain:** Multi-agent orchestration engine (`AIAgentOrchestrator` in `src/Intelligence/Orchestration/orchestrator.py`).
* **Product & Growth Agents:** Multi-domain agents across Growth, Content, Distribution, Security, Trust, and Performance (`src/Growth/Agents/`).
* **Content & Blog Platform:** Localized UI components (`trader-terminal/src/views/BlogView.jsx`), SEO page generators, and multilingual content lifecycle.
* **DevOps & Release Systems:** Deterministic release gate workflows (`.github/workflows/release.yml`), post-deployment health verification, and operational release validation (`validate_release.py`).

The former repository `sohrabinia/yartrader.DevOps` is classified as:
`Migration source / deprecated candidate; final dependency verification pending.`

---

## 2. Current Implemented State vs. Target Architecture

To maintain strict truthfulness, system capabilities are explicitly separated between what is currently implemented in source code versus what represents future target architecture.

### CURRENT IMPLEMENTED STATE
* **Single Repository Ownership:** All active code and specs reside strictly within `sohrabinia/YarTrader`.
* **Central Product Agent Brain:** `AIAgentOrchestrator` in `src/Intelligence/Orchestration/orchestrator.py` provides read-only advisory planning and execution.
* **Product Core & Safety Gates:** FastAPI backend (`app/`), React SPA frontend (`trader-terminal/`), MT5 DEMO execution gate, and 2% risk / 8% daily kill switch limits.
* **Product & Growth Agents:** Domain-specific agents in `src/Growth/Agents/` operating as standalone domain modules.
* **Blog & Content Subsystem:** Localized views and SEO metadata in `trader-terminal`.
* **Deterministic Release Gate:** `.github/workflows/release.yml` executing `pytest`, `npm ci`, `npm run build`, `git diff --check`, and `python validate_release.py`.
* **Production GET Health Verification:** Multi-locale HTTP health probes verifying 200 OK across 8 localized routes plus font assets.
* **Obsolete Script Cleanup:** Removal of manual update scripts (`update-site.ps1` and `update-site.sh`).

### TARGET ARCHITECTURE (PLANNED / PENDING / BLOCKED)
* **DevOps Agent / Capability:** `PLANNED / PENDING` — Future AI release analysis and assessment module; no executable DevOps agent source exists in the current repository.
* **AI Release Assessment:** `PENDING / NOT ACTIVE` — Release decisions are currently strictly deterministic; no AI/LLM release assessment is active in CI/CD.
* **Production Deployment Execution:** `PENDING / BLOCKED` — CI/CD executes release validation and health probes; physical deployment artifact transfer to production servers is pending external infrastructure configuration.
* **Automatic Version Rollback:** `PENDING / NOT IMPLEMENTED` — Automatic rollback hooks require target host infrastructure hooks and are not implemented in the current repository.

---

## 3. Logical Architecture Topology

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
          PRODUCT AGENTS      CONTENT / BLOG     DEVOPS AGENT [PLANNED]
                 │                 │                 │
                 │                 │                 ▼
                 │                 │          RELEASE ANALYSIS [PLANNED]
                 │                 │                 │
                 │                 │                 ▼
                 │                 │        DETERMINISTIC POLICY [IMPLEMENTED]
                 │                 │                 │
                 │                 │            ┌────┴────┐
                 │                 │            ▼         ▼
                 │                 │          BLOCK     APPROVE
                 │                 │                        │
                 │                 │                        ▼
                 │                 │                     DEPLOY [PENDING]
                 │                 │                        │
                 │                 │                        ▼
                 │                 │                     VERIFY [VALIDATED]
                 │                 │                     │    │
                 │                 │                   PASS  FAIL
                 │                 │                     │    │
                 │                 │                     ▼    ▼
                 │                 │                  SUCCESS ROLLBACK [PENDING]
                 │                 │
                 └─────────────────┴─────────────────────────────
```

---

## 4. Central Agent Brain Verification & Agent Inventory

The canonical Central Product Agent Brain is implemented at:
`src/Intelligence/Orchestration/orchestrator.py`

### Actual Implementation Scope
* **`AIAgentOrchestrator`:** Primary orchestrator wrapper instantiating registry, task router, planner agent, and execution engine.
* **`AgentRegistry`:** Pre-seeded with 4 advisory squad agents (`agent-research`, `agent-strategy`, `agent-risk`, `agent-security`).
* **`TaskRouter`:** Capability-based router mapping goal capabilities to registered agent IDs.
* **`PlannerAgent`:** Formulates sequential execution plans based on goal keywords.
* **`OrchestratorExecutionEngine`:** Executes plan steps in strictly passive advisory mode (`is_read_only_advisory: True`).

### Agent Scope Classification
To avoid claiming that all agents are centrally controlled when they operate independently, agents across the codebase are classified as follows:

| Agent / Module | Implementation Path | Lifecycle Classification |
| :--- | :--- | :--- |
| **Research Agent** (`agent-research`) | `src/Intelligence/Orchestration/orchestrator.py` | `REGISTERED`, `ROUTABLE`, `EXECUTED` |
| **Strategy Agent** (`agent-strategy`) | `src/Intelligence/Orchestration/orchestrator.py` | `REGISTERED`, `ROUTABLE`, `EXECUTED` |
| **Risk Agent** (`agent-risk`) | `src/Intelligence/Orchestration/orchestrator.py` | `REGISTERED`, `ROUTABLE`, `EXECUTED` |
| **Security Agent** (`agent-security`) | `src/Intelligence/Orchestration/orchestrator.py` | `REGISTERED`, `ROUTABLE`, `EXECUTED` |
| **Content Agents** | `src/Growth/Agents/ContentAgents.py` | `EXECUTED`, `NOT ORCHESTRATED` (Standalone Domain Module) |
| **Distribution Agents** | `src/Growth/Agents/DistributionAgents.py` | `EXECUTED`, `NOT ORCHESTRATED` (Standalone Domain Module) |
| **Market Intelligence Agents** | `src/Growth/Agents/MarketIntelligenceAgents.py` | `EXECUTED`, `NOT ORCHESTRATED` (Standalone Domain Module) |
| **Performance Validation Agent** | `src/Growth/Agents/PerformanceValidationAgent.py` | `EXECUTED`, `NOT ORCHESTRATED` (Standalone Domain Module) |
| **Security & Cost Agents** | `src/Growth/Agents/SecurityCostAgents.py` | `EXECUTED`, `NOT ORCHESTRATED` (Standalone Domain Module) |
| **Trust & Learning Agents** | `src/Growth/Agents/TrustLearningAgents.py` | `EXECUTED`, `NOT ORCHESTRATED` (Standalone Domain Module) |
| **User Growth Agents** | `src/Growth/Agents/UserGrowthAgents.py` | `EXECUTED`, `NOT ORCHESTRATED` (Standalone Domain Module) |
| **DevOps Agent** | N/A (No Source) | `PLANNED` |

---

## 5. CTO Audit Reconciliation Matrix

An evidence-based comparison evaluating historical CTO audit claims against actual source code state:

| Audit Claim | Status Tag | Codebase Verification Evidence | Reconciled Reality |
| :--- | :--- | :--- | :--- |
| **Product is XAUUSD Research/Backtest Engine** | `HISTORICAL` | Codebase includes FastAPI web service (`app/`), React SPA frontend (`trader-terminal/`), and Multi-Agent system (`src/Growth/Agents/`). | YarTrader is a complete market intelligence web platform, not merely a backtest script. |
| **2% Max Risk Ceiling & 8% Daily Loss Switch** | `CONFIRMED` | `src/Risk/Services/professional_risk_engine.py` & `daily_loss_kill_switch.py` | Strict fail-closed risk bounds are programmatically enforced at the Risk Engine layer. |
| **MT5 DEMO Boundary & MT4 Rejection** | `CONFIRMED` | `src/Execution/Safety/demo_execution_gate.py` & `src/Execution/Adapters/mt4_adapter.py` | MT4 order submission is hard-rejected. MT5 is restricted strictly to DEMO accounts and XAUUSD symbol. |
| **AIAgentOrchestrator Control** | `CONFIRMED` | `src/Intelligence/Orchestration/orchestrator.py` | Serves as the central orchestrator for core intelligence task planning and squad routing. |
| **Single Repository Setup** | `CONFIRMED` | `sohrabinia/YarTrader` | All domain capabilities reside in `YarTrader`; `yartrader.DevOps` is deprecated as active dependency. |

---

## 6. Implementation Status Matrix

Every capability in the system is explicitly categorized using authoritative status tags (`IMPLEMENTED`, `VALIDATED`, `SHADOW`, `PLANNED`, `BLOCKED`, `DEPRECATED`):

| Subsystem / Feature | Status Tag | Execution / Source Path | Architectural Purpose & Reality |
| :--- | :--- | :--- | :--- |
| **Single Repository Ownership** | `IMPLEMENTED` | `sohrabinia/YarTrader` | Single source of truth for Product, Agents, Blog, and Release workflows. |
| **Central Agent Brain** | `IMPLEMENTED` | `src/Intelligence/Orchestration/orchestrator.py` | Central orchestrator for passive advisory planning and routing. |
| **Product & Growth Agents** | `IMPLEMENTED` | `src/Growth/Agents/` | Standalone domain agent modules across 7 functional areas. |
| **Blog & Content Engine** | `IMPLEMENTED` | `trader-terminal/src/views/BlogView.jsx` | Multilingual UI, localized guides, and static asset delivery. |
| **Deterministic Release Gate** | `IMPLEMENTED` | `.github/workflows/release.yml` | Executes pytest, Vite build, `git diff --check`, and `validate_release.py`. |
| **Multilingual Health Probes** | `VALIDATED` | `.github/workflows/release.yml` | Validates HTTP 200 OK for 8 localized routes + Vazirmatn font asset. |
| **Obsolete Script Removal** | `DEPRECATED` | `update-site.ps1` & `update-site.sh` | Removed legacy manual update scripts from root repository. |
| **DevOps Agent Capability** | `PLANNED` | N/A | No executable source exists in repository; planned future capability. |
| **AI Pre-Merge Code Review** | `PLANNED` | N/A | Planned future capability; code review decisions remain deterministic. |
| **AI Operational Release Assessment**| `PENDING` | N/A | `validate_release.py` is a deterministic python validation platform, not AI. |
| **Autonomous Production Deploy** | `PENDING / BLOCKED` | `.github/workflows/release.yml` | Production deployment execution blocked pending physical server CD hooks. |
| **Automated Version Rollback** | `PENDING / NOT IMPLEMENTED` | N/A | Physical rollback hooks are pending server infrastructure setup. |
| **Legacy `yartrader.DevOps` Repo** | `DEPRECATED` | `sohrabinia/yartrader.DevOps` | Migration source / deprecated candidate; final dependency verification pending. |
