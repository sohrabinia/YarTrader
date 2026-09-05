# YarTrader Master Architecture & Repository Responsibility Matrix

```text
================================================================================
YARTRADER SINGLE-REPOSITORY UNIFIED ARCHITECTURE
================================================================================

1. AUTHORITATIVE REPOSITORY BOUNDARY
   REPOS:               sohrabinia/YarTrader (SINGLE AUTHORITATIVE REPOSITORY)
   DEPRECATED CANDIDATE:sohrabinia/yartrader.DevOps (Consolidation source; pending full archive)

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
   │   │   └── Passive Advisory Squad Orchestration
   │   ├── Market Intelligence Agents (MarketIntelligenceAgents.py)
   │   ├── Research & Analysis Agents (PerformanceValidationAgent.py)
   │   ├── Content & Distribution Agents (ContentAgents.py, DistributionAgents.py)
   │   ├── Security & Cost Validation Agents (SecurityCostAgents.py)
   │   └── Trust Learning & User Growth Agents (TrustLearningAgents.py, UserGrowthAgents.py)
   │
   ├── BLOG / CONTENT (src/Growth/Agents/ContentAgents.py, trader-terminal/src/views/BlogView.jsx)
   │   ├── Blog Engine & Article Rendering
   │   ├── Multi-locale Content Dictionary & SEO Structured Data
   │   └── Publication & Revision Lifecycle
   │
   └── DEVOPS & RELEASE ENGINE (.github/workflows/, devops/ or repository workflows)
       ├── CI Validation Gate (.github/workflows/ci.yml)
       ├── Deterministic Release Gate (.github/workflows/release.yml)
       ├── Fail-Closed Pre-Commit & Pre-Release Quality Gates
       └── Post-Deployment Health Checks (GET health across all 8 routes)

================================================================================
3. IMPLEMENTED VS PENDING CAPABILITIES MATRIX
================================================================================

   IMPLEMENTED & VERIFIED IN YARTRADER:
   [X] Single Authoritative Repository Ownership (sohrabinia/YarTrader)
   [X] Central Product Agent Brain (AIAgentOrchestrator in src/Intelligence/Orchestration/orchestrator.py)
   [X] Product Core Preservation (FastAPI, trader-terminal, MT5 Demo, 2% Risk)
   [X] AI Agents Subsystem Preservation (src/Growth/Agents, app/intelligence)
   [X] Blog & Content Subsystem Preservation (ContentAgents.py, BlogView.jsx)
   [X] Removal of Obsolete Manual Deployment Scripts (update-site.ps1, update-site.sh)
   [X] Deterministic Release Gating (.github/workflows/release.yml: pytest, npm ci build, diff check)
   [X] Multi-Locale Production GET Health Verification (8 routes + Vazirmatn font asset)

   PENDING / REQUIRING EXTERNAL PRODUCTION INFRASTRUCTURE ACCESS:
   [ ] Real Production Deployment Execution (Physical artifact deployment to target server)
   [ ] Automatic Version-Based Rollback Engine (Requires physical server rollback hooks)
   [ ] AI-Driven Operational Risk Assessment (Shadow Mode evaluation suite)
   [ ] Full Deprecation / Archival of sohrabinia/yartrader.DevOps on GitHub

================================================================================
```
