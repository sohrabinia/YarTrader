# YarTrader Frontend Data Connection & Real Data Audit v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Audit of real API bindings, data contracts, loading/error states, empty states, and strict fake data removal across all YarTrader frontend modules.

---

## 1. Page-by-Page Data Connection Mapping

| Page / Component | Route | API Service Binding | Endpoint Path | Data Model Contract | Loading & Error State Handling | Empty State Fallback Text |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Landing Metrics** | `#/` | `apiService.get` | `/api/public/metrics` | `{ active_markets_count, historical_simulated_trades, platform_uptime_pct }` | Banner alert if unreachable | `"DATA UNAVAILABLE"` |
| **Dashboard Signals**| `#/dashboard` | `apiService.get` | `/api/user/signals?horizon=medium` | Array of signal objects with posture & confidence | Toast notification on error | `"No signals active for this horizon."` |
| **Execution Intel** | `#/execution-intel` | `apiService.get` | `/api/execution/plans?symbol=XAUUSD` | Advisory trade plan `{ action, entry, SL, TP, R:R }` | Fallback null-checks | `"-"` / `"DATA UNAVAILABLE"` |
| **Structure Map** | `#/execution-intel` | `apiService.get` | `/api/structure/map?symbol=XAUUSD` | Price action nodes `[{ node_index, price, type, label }]` | Table scroll loader | `"No structural nodes available."` |
| **Portfolio Risk** | `#/execution-intel` | `apiService.get` | `/api/portfolio/risk` | `{ portfolio_heat, risk_budget_remaining, drawdown_level }` | Stat card null-checks | `"BALANCED"` / `"DATA UNAVAILABLE"` |
| **Demo Trading** | `#/demo` | `apiService.get` | `/api/demo/trades` & `/api/demo/report` | Order history on MT5 Demo account #52961173 | Table loader | `"No demo trades found on broker demo account."` |
| **Shadow Trading** | `#/shadow` | `apiService.get` | `/api/shadow/report` & `/api/admin/shadow-trades` | Virtual capital ($1,000) paper position list | Table loader | `"No virtual shadow positions currently open."` |
| **Learning Matrix** | `#/learning` | `apiService.get` | `/api/intelligence/learning-matrix` | Pattern performance array `[{ pattern_key, win_rate_pct, sample_count }]` | Table loading text | `"Loading pattern matrix data..."` |
| **Admin System** | `#/admin` | `apiService.get` | `/api/devops/status` & `/api/devops/metrics` | `{ status, scheduler_active, mt5_connected, live_trading_enabled }` | Subsystem status pills | `"DATA UNAVAILABLE"` |
| **Validation Runner**| `#/admin` | `apiService.post` | `/api/validation/run` & `/api/validation/status` | SRE runner phase `{ phase, readiness_score, logs }` | Log console auto-scroll | `"IDLE"` / `[]` |

---

## 2. Removal of Fake Frontend Data & Truthfulness Policy

* **No Hardcoded Indicators:** Status badges MUST derive from real backend state (`LIVE`, `DEMO`, `UNREACHABLE`, `FAIL-CLOSED`).
* **Explicit Non-Positive Fallbacks:** If API data is unreachable or missing, UI components strictly display explicit fallback labels (`"DATA UNAVAILABLE"`, `"NOT REPORTED"`, `"DISCONNECTED"`), preventing false claims of health or activity.

---

*Data Connection Audit certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
