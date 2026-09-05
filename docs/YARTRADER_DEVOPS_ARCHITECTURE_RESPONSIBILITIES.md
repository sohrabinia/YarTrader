# YarTrader Architecture & Repository Responsibility Matrix

```text
================================================================================
YARTRADER REPOSITORY & DEVOPS SEPARATION OF RESPONSIBILITIES
================================================================================

1. REPOSITORY BOUNDARIES

   a) Product Repository: sohrabinia/YarTrader
      OWNERSHIP:
      - Product source code (Python FastAPI backend, React trader-terminal UI)
      - Application logic & 3-layer architecture (Fractal math, MTF state, Advisory PPO RL)
      - MT5 / MT4 execution adapters & broker integration interfaces
      - Product unit/integration test suite (pytest)
      - Application build & static validation configurations

   b) DevOps & Release Platform Repository: sohrabinia/yartrader.DevOps
      OWNERSHIP:
      - Authoritative production release orchestration & AI-driven release decision gates
      - System telemetry, ASP.NET Core DevOps API (`YarTrader.DevOps.Api`) & background monitoring
      - Production environment profiles (profiles/YarTrader-production.yaml)
      - Automated site deployment execution, post-deployment health verification, & rollback
      - Windows Service host (`YarTrader-DevOps`) & container configuration
      - Production system collectors (IIS, SQL Server, Redis, MT5, Python AI, Model Health)

================================================================================
2. AUTOMATED DEPLOYMENT, RELEASE GATING & ROLLBACK PATHWAY
================================================================================

   YarTrader Product Repository (sohrabinia/YarTrader)
          │
          │ Code change merged to main
          ▼
   GitHub Repository Trigger / Event Dispatch
          │
          ▼
   yartrader.DevOps Release Engine (sohrabinia/yartrader.DevOps)
          │
          ├──> AI / Safety Release Gate Evaluation (Fail-Closed)
          │      ├─ Source checkout & commit SHA verification
          │      ├─ Pytest suite execution (1843+ tests passing)
          │      ├─ Frontend production build compilation (`npm run build`)
          │      ├─ Git diff formatting & whitespace check (`git diff --check`)
          │      └─ Fail-closed MT5 DEMO gate & risk bounds validation
          │
          ├──> GATE REJECT / FAIL
          │      └─ Deployment blocked; current production release remains active
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
