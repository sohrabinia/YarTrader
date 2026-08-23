# YarTrader Complete Architecture Gap Analysis & Migration Audit v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Final gap synthesis, backend endpoint mapping, state architecture, charting strategy, and SRE safety gate constraints for Phase 0 transformation.

---

## 1. Summary of Product & Technical Gaps

| Capability Area | Current Coverage | Target Capability | Gap Resolution Strategy |
| :--- | :---: | :--- | :--- |
| **Financial Charting** | 0% | TradingView Lightweight Charts (`lightweight-charts`) with OB/FVG overlay canvas | Build `ChartContainer` wrapper component in `src/design-system/`. |
| **Position Lifecycle** | 40% | 5-phase visual stepper (`Created → Validated → Opened → Managed → Closed`) | Build `PositionTimelineStepper` component in `src/design-system/`. |
| **Fractal Intelligence** | 30% | Multi-scale x3/x4 containment visualizer & historical pattern similarity overlay | Build dedicated `/fractal` page and visual scale graph. |
| **Trade Journal** | 0% | MAE/MFE scatter plot, entry/exit screenshots, trade tags | Build dedicated `/journal` page with backend `/api/user/history` binding. |
| **User SaaS Portal** | 20% | User `/billing` manager & `/wallet` ledger statement | Build `/billing` and `/wallet` pages bound to `/api/user/billing` and `/api/user/ledger/balance`. |
| **Admin Control Plane** | 65% | 17 Admin subsections (RBAC roles, AI engine keys, telemetry, audit logs) | Expand `/admin` tabs in `src/features/admin/`. |
| **Command Palette** | 0% | Global search for symbols, decisions, reports, users, logs (`Ctrl+K`) | Build `CommandPalette` component using `shadcn/ui` Command primitive. |
| **State Management** | Local State | Centralized reactive Zustand stores (`useAuthStore`, `useMarketStore`, `useAdminStore`) | Implement Zustand stores in `src/stores/`. |
| **Data Fetching Layer** | Raw Fetch | TanStack Query (React Query) with caching, revalidation, and retry | Wrap API client with TanStack Query Provider. |
| **Real-time Engine** | HTTP Polling | Dual-mode: WebSocket client (`ws://`) + HTTP polling fallback | Build `useWebSocket` hook and real-time message router. |

---

## 2. Backend Endpoint Compatibility Matrix

All backend FastAPI endpoints are verified and compatible with the new frontend architecture:

```
Public & Auth:
  GET  /api/public/metrics
  GET  /api/subscription/plans
  POST /api/auth/login
  POST /api/auth/register
  POST /api/auth/forgot-password
  POST /api/auth/reset-password
  POST /api/auth/logout

User Intelligence & Trading:
  GET  /api/user/markets
  GET  /api/user/signals
  GET  /api/execution/plans
  GET  /api/execution/confidence
  GET  /api/execution/reasoning
  GET  /api/structure/map
  GET  /api/structure/alignment
  GET  /api/structure/narrative
  GET  /api/liquidity/map
  GET  /api/liquidity/events
  GET  /api/pattern/similarity
  GET  /api/portfolio/risk
  GET  /api/portfolio/exposure
  GET  /api/intelligence/learning-matrix
  GET  /api/intelligence/explain/{decision_id}
  GET  /api/fractal/status

Trading Modes:
  POST /api/backtest/run
  GET  /api/backtest/history
  GET  /api/demo/trades
  GET  /api/demo/report
  GET  /api/shadow/report

SaaS & Support:
  GET  /api/user/ledger/balance
  GET  /api/user/billing/subscription
  GET  /api/user/tickets
  POST /api/user/tickets
  POST /api/chat/assistant

Admin Control Plane:
  GET  /api/admin/symbols
  POST /api/admin/symbols
  GET  /api/admin/reports
  GET  /api/admin/shadow-trades
  GET  /api/devops/status
  GET  /api/devops/metrics
  POST /api/validation/run
  GET  /api/validation/status
  GET  /api/validation/history
```

---

## 3. Mandatory SRE Safety Constraints

1. **LIVE Trading Hard Isolation (`LIVE_TRADING_ENABLED=False`):**
   * Real account `#143056202` on Alpari-Pro.ECN remains permanently hard-blocked by `MetaTraderSafetyGate`.
   * Route `/live` MUST render the 🛑 Fail-Closed SRE Safety Notice with zero real-money order routing controls.
2. **Execution Targets:**
   * Execution target is strictly MT5 DEMO account `#52961173` on Alpari-MT5-Demo and Paper Shadow ($1,000).
3. **Truthfulness Policy:**
   * All metric labels MUST truthfully report state (`SIMULATED`, `MT5 DEMO`, `DATA UNAVAILABLE`, `FAIL-CLOSED`).

---

*Gap Report certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
