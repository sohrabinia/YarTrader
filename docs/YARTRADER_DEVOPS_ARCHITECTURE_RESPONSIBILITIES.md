# YarTrader Master Architecture & Repository Responsibility Matrix

```text
================================================================================
YARTRADER SINGLE-REPOSITORY UNIFIED ARCHITECTURE
================================================================================

1. AUTHORITATIVE REPOSITORY BOUNDARY
   PRIMARY REPOSITORY:  sohrabinia/YarTrader (SINGLE AUTHORITATIVE REPOSITORY)
   DEPRECATED CANDIDATE:sohrabinia/yartrader.DevOps
                        (Migration source / deprecated candidate; final dependency verification pending)

2. DOMAIN BOUNDARIES & INTERNAL ARCHITECTURE

   YarTrader/
   │
   ├── PRODUCT CORE (src/, app/, trader-terminal/)
   │   ├── Backend (FastAPI, app/core, app/api)
   │   ├── Frontend UI (trader-terminal/, React, Vite, Vazirmatn typography)
   │   ├── Market Intelligence (Layer 1 Math & Fractals, Layer 2 MTF State)
   │   ├── Strategy & Advisory Policy (Layer 3 Deep RL PPO Policy)
   │   ├── Execution & Safety Gates (DemoExecutionGate, MT5 Adapter, MT4 Rejection)
   │   ├── Risk Engine (ProfessionalRiskEngine 2.0% ceiling, DailyLossKillSwitch 8.0%)
   │   └── Localization & Clean Routing (/fa/, /en/, /tr/, /ar/, clean URLs, 0 hash routes)
   │
   ├── AI / PRODUCT AGENTS & ORCHESTRATION (src/Intelligence/Orchestration/, src/Growth/Agents/)
   │   ├── Central Product Agent Orchestrator: AIAgentOrchestrator (src/Intelligence/Orchestration/orchestrator.py)
   │   │   ├── AgentRegistry & TaskRouter
   │   │   ├── PlannerAgent & OrchestratorExecutionEngine
   │   │   └── Passive Advisory Squad Orchestration (REGISTERED, ROUTABLE, EXECUTED)
   │   ├── Standalone Growth & Product Agents (src/Growth/Agents/ — EXECUTED, NOT ORCHESTRATED)
   │   │   ├── Market Intelligence Agents (MarketIntelligenceAgents.py)
   │   │   ├── Research & Analysis Agents (PerformanceValidationAgent.py)
   │   │   ├── Content & Distribution Agents (ContentAgents.py, DistributionAgents.py)
   │   │   ├── Security & Cost Validation Agents (SecurityCostAgents.py)
   │   │   └── Trust Learning & User Growth Agents (TrustLearningAgents.py, UserGrowthAgents.py)
   │
   ├── BLOG / CONTENT (src/Growth/Agents/ContentAgents.py, trader-terminal/src/views/BlogView.jsx)
   │   ├── Blog Engine & Article Rendering
   │   ├── Multi-locale Content Dictionary & SEO Structured Data
   │   └── Publication & Revision Lifecycle
   │
   └── DEVOPS & RELEASE ENGINE (.github/workflows/release.yml, validate_release.py)
       ├── CI/CD Validation Gate (.github/workflows/release.yml)
       ├── Deterministic Release Gate (pytest, npm ci & build, git diff --check, validate_release.py)
       └── Fail-Closed Production GET Health Verification (8 localized routes + Vazirmatn font)

================================================================================
3. IMPLEMENTED VS PENDING CAPABILITIES MATRIX
================================================================================

   IMPLEMENTED & VERIFIED IN YARTRADER:
   [X] Single Authoritative Repository Ownership (sohrabinia/YarTrader)
   [X] Central Product Agent Brain (AIAgentOrchestrator in src/Intelligence/Orchestration/orchestrator.py)
   [X] Product Core Preservation (FastAPI, trader-terminal, MT5 Demo, 2% Risk, 8% Kill Switch)
   [X] AI Agents Subsystem Preservation (src/Growth/Agents, app/intelligence)
   [X] Blog & Content Subsystem Preservation (ContentAgents.py, BlogView.jsx)
   [X] Removal of Obsolete Manual Deployment Scripts (update-site.ps1, update-site.sh)
   [X] Deterministic Release Gating (.github/workflows/release.yml: pytest, npm ci build, diff check)
   [X] Multi-Locale Production GET Health Verification (8 routes + Vazirmatn font asset)

   PENDING / REQUIRING EXTERNAL PRODUCTION INFRASTRUCTURE ACCESS:
   [ ] Real Production Deployment Execution (PRODUCTION DEPLOYMENT: PENDING / BLOCKED)
   [ ] Automatic Version-Based Rollback Engine (AUTOMATIC ROLLBACK: PENDING / NOT IMPLEMENTED)
   [ ] AI-Driven Operational Release Assessment (AI RELEASE ASSESSMENT: PENDING / NOT ACTIVE)
   [ ] DevOps Agent Capability (DEVOPS AGENT: PLANNED / PENDING)
   [ ] Full Deprecation / Archival of sohrabinia/yartrader.DevOps on GitHub
       (Migration source / deprecated candidate; final dependency verification pending)

================================================================================
```
