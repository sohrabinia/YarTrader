# YarTrader Master Architecture & Repository Responsibility Matrix

```text
================================================================================
YARTRADER SINGLE-REPOSITORY UNIFIED ARCHITECTURE
================================================================================

1. AUTHORITATIVE REPOSITORY BOUNDARY
   REPOS:               sohrabinia/YarTrader (SINGLE AUTHORITATIVE REPOSITORY)
   DEPRECATED:          sohrabinia/yartrader.DevOps (Consolidated & archived into YarTrader)

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
   ├── AI / AGENTS (src/Growth/Agents/, app/intelligence/, app/workers/)
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
       ├── Automated Release Gate (.github/workflows/release.yml)
       ├── AI Release Risk Assessment & Deterministic Fail-Closed Safety Checks
       ├── Production Deployment Execution & Target Version Tracking
       ├── Fail-Closed Post-Deployment Health Checks (GET health across all 8 routes)
       └── Automatic Rollback to Last Known-Good Commit

================================================================================
3. AUTOMATED RELEASE DECISION, DEPLOYMENT & ROLLBACK FLOW
================================================================================

   YarTrader main branch
          │
          │ Code merge to main
          ▼
   GitHub Release Candidate Event (.github/workflows/release.yml)
          │
          ├──> Deterministic Fail-Closed Release Gate
          │      ├─ Source checkout & immutable Commit SHA tracking
          │      ├─ Pytest test suite execution (1843+ tests passing)
          │      ├─ Frontend Vite production build compilation (`npm run build`)
          │      ├─ Git diff formatting check (`git diff --check`)
          │      └─ Fail-closed MT5 DEMO gate & risk bounds check
          │
          ├──> GATE REJECT / FAIL
          │      └─ Deployment BLOCKED; previous production release remains active
          │
          └──> GATE APPROVE / PASS
                 │
                 ▼
            Automated Site Deployment Execution
                 │
                 ▼
            Post-Deployment Production Health Verification
                 ├─ HTTP GET checks across all 8 production routes
                 ├─ Zero hash-routing (#/) check
                 └─ Vazirmatn Persian WOFF2 font asset accessibility
                 │
             ┌───┴───┐
             │       │
           PASS    FAIL
             │       │
             ▼       ▼
          SUCCESS  AUTOMATIC ROLLBACK to last known-good production commit

================================================================================
```
