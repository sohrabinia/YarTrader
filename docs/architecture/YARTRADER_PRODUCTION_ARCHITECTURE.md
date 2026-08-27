# YarTrader Production Architecture Specification

## 1. System Topology
The YarTrader platform is a fully self-hosted, institutional-grade financial intelligence and execution platform.

```text
GitHub (Source Control / CI)
          ↓
Self-Hosted Windows Server (https://yartrader.com)
          ↓
Windows Service Control Manager (Service: YarTrader)
          ↓
FastAPI Backend Gateway (127.0.0.1:8000)
          ↓
   ┌──────┴──────┐
   ▼             ▼
SQLite DB     Static React SPA
(Storage)     (trader-terminal)
```

## 2. Platform Component Boundaries

### Source Control & CI
* **GitHub Repository:** `sohrabinia/YarTrader`
* **Build Verification:** Automated pytest suite (1,684 test units) + Vite frontend build (`npm run build`).

### Production Runtime
* **Production Origin:** `https://yartrader.com`
* **DNS Authority:** Self-Managed Domain DNS (`yartrader.com`).
* **Service Host:** `YarTraderServiceHost` (`app/workers/service.py`) running FastAPI via Uvicorn.
* **Database Isolation:** Isolated SQLite database under `TradeYarStorageRoot/production_db.sqlite`.

### Deprecated Infrastructure
* **Vercel:** NOT USED. Zero active production runtime dependencies, zero `vercel.json` config files, and zero `vercel.app` canonical URLs.

## 3. Mandatory Safety Constraints
1. **Intraday Execution:** Fast Scalp / Scalp trading styles only (M1–M15 timeframes).
2. **EOD Position Flattening:** Mandatory session cutoff (`OPEN_POSITIONS_AFTER_EOD = 0`).
3. **Independent Risk Veto:** Server-side `ProfessionalRiskEngine` veto authority.
4. **Live Execution Lock:** `LIVE_TRADING_ENABLED = False` and `REAL_ORDERS = 0` hard-locked repository-wide.
