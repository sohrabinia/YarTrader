# YarTrader Backend Services & API Integration Map v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Forensic audit of all backend FastAPI routers, schemas, data models, authentication flows, and real-time/polling capabilities for Phase 1 Frontend Integration.

---

## Executive Summary

The YarTrader backend is built on **FastAPI** (`src/Application/Services/web_dashboard.py`, `admin_api_router.py`, `growth_api_router.py`, `public_api_router.py`, `user_api_router.py`). It exposes over 65 REST endpoints spanning Public, Auth, Intelligence, Research, Execution, Risk, Trading Modes, Billing, and Admin Control Plane domains.

---

## 1. Authentication Flow & Session Management

| Endpoint Path | HTTP Method | Request Body / Parameters | Response Contract | Auth / Role Guard | Notes & Behavior |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `/api/auth/register` | `POST` | `{ name, username, email, password }` | `{ status, message, user_id }` | Public | Validates email uniqueness & creates user record |
| `/api/auth/login` | `POST` | `{ email, password }` | `{ status, session_token, user: { id, email, role, name } }` | Public | Returns bearer session token stored in `localStorage` |
| `/api/auth/forgot-password` | `POST` | `{ email }` | `{ status, message }` | Public | Dispatches reset token email |
| `/api/auth/verify-email` | `GET` | `?token=...` | `{ status, message }` | Public | Validates verification token |
| `/api/auth/reset-password` | `POST` | `{ token, new_password }` | `{ status, message }` | Public | Updates password hash |
| `/api/auth/logout` | `POST` | `{ token }` | `{ status, message }` | Authenticated | Revokes session token in database |
| `/api/auth/google` | `POST` | `{ token }` | `{ status, session_token, user }` | Public | Google OAuth SSO token validation |
| `/api/auth/apple` | `POST` | `{ token }` | `{ status, session_token, user }` | Public | Apple OAuth SSO token validation |
| `/api/auth/telegram` | `GET` | `?id=...&hash=...` | `{ status, session_token, user }` | Public | Telegram Web Login OIDC with HMAC-SHA256 signature check |

---

## 2. Domain API Mapping Across 14 Service Modules

### 2.1 Public & Market Intelligence (`src/services/public/` & `market/`)
* `GET /api/public/metrics`: Returns `{ active_markets_count, historical_simulated_trades, platform_uptime_pct }`.
* `GET /api/user/markets`: Returns array of active symbols `[{ symbol, name, category, price, change_pct }]`.
* `GET /api/user/signals?horizon={horizon}`: Returns array of qualified signals `[{ symbol, timeframe, posture, entry_zone, target_zone, invalidation_level, confidence, narrative }]`.

### 2.2 Intelligence & Research (`src/services/intelligence/` & `research/`)
* `GET /api/research/latest`: Returns live market research feed.
* `GET /api/intelligence/status`: Returns multi-timeframe intelligence pipeline status.
* `GET /api/intelligence/explain/{decision_id}`: Returns XAI decision rationale and evidence steps.
* `GET /api/fractal/status`: Returns `{ status: "CONNECTED", fractal_score: 0.85, similarity_score: 88.5, scale_state: "MULTISCALE_STABLE" }`.

### 2.3 Decision & Risk Engine (`src/services/decision/` & `risk/`)
* `GET /api/execution/plans?symbol=XAUUSD&timeframe=H1`: Returns advisory trade plan `{ action, entry_price, stop_loss, take_profit, risk_reward, style }`.
* `GET /api/execution/confidence`: Returns `{ confidence: "85%" }`.
* `GET /api/execution/reasoning`: Returns `{ reasoning: ["Break of Structure confirmed", "FVG filled"] }`.
* `GET /api/portfolio/risk`: Returns `{ portfolio_heat: "1.2%", risk_budget_remaining: "3.8%", drawdown_level: "NORMAL", risk_approved: true }`.
* `GET /api/portfolio/exposure`: Returns asset concentration percentages.
* `POST /api/risk/emergency_stop`: Executes emergency stop halting all open paper/demo positions.

### 2.4 Trading Modes (`src/services/trading/`)
* `POST /api/backtest/run`: Request `{ symbol, timeframe, bars }`. Returns `{ run_id, total_trades, win_rate_pct, profit_factor, max_drawdown_pct, leakage_status }`.
* `GET /api/backtest/history`: Returns array of historical backtest runs.
* `GET /api/demo/trades`: Returns order history on MT5 Demo account #52961173 on `Alpari-MT5-Demo`.
* `GET /api/demo/report`: Returns `{ server: "Alpari-MT5-Demo", account_id: "52961173", total_trades: 42, market_status: "OPEN" }`.
* `GET /api/shadow/report`: Returns `{ account_id: "paper-v1001", balance: 1000.0, equity: 1000.0, realized_pnl: 0.0 }`.
* `GET /api/admin/shadow-trades`: Returns array of open virtual positions `[{ vpos_id, symbol, side, entry_price, stop_loss, take_profit, unrealized_pnl }]`.

### 2.5 Journal & Learning Loop (`src/services/journal/` & `learning/`)
* `GET /api/user/history`: Returns user historical trades for journaling.
* `GET /api/intelligence/learning-matrix`: Returns array of pattern performance metrics `[{ pattern_key, pattern_name, sample_count, win_rate_pct, average_rr, average_mae, average_mfe }]`.

### 2.6 SaaS Layer: Wallet & Billing (`src/services/billing/` & `wallet/`)
* `GET /api/subscription/plans`: Returns subscription tiers `[{ name, price_usd, max_symbols, enabled_timeframes, features }]`.
* `GET /api/user/billing/subscription`: Returns user active plan and renewal date.
* `GET /api/user/ledger/balance`: Returns user wallet credit balance and transaction history.
* `GET /api/user/tickets`: Returns support ticket threads.
* `POST /api/user/tickets`: Submits a new support ticket.

### 2.7 SRE Admin Control Plane (`src/services/admin/`)
* `GET /api/devops/status`: Returns `{ status: "healthy", scheduler_active: true, mt5_connected: true, mt5_server: "Alpari-MT5-Demo", live_trading_enabled: false }`.
* `GET /api/devops/metrics`: Returns `{ total_users: 1250, system_health_pct: 99.9 }`.
* `GET /api/admin/symbols?token=...`: Returns registered symbols list.
* `POST /api/admin/symbols?token=...`: Registers a new active trading symbol.
* `POST /api/validation/run`: Triggers SRE validation test runner loop.
* `GET /api/validation/status`: Returns `{ phase: "SUCCESS", readiness_score: "100%", logs: [...] }`.
* `GET /api/admin/reports`: Returns SCM intelligence report array.

---

## 3. Real-Time Data & Polling Engine Architecture

* **WebSocket Availability:** Currently no native `@app.websocket` endpoints exist on the FastAPI backend.
* **Polling Architecture:** Real-time updates operate via HTTP Polling (`fetch` interval loop):
  * Market Ticker / Signals: 10,000ms polling interval.
  * Validation Runner Logs: 1,000ms polling interval while `validationPhase === 'RUNNING'`.
  * Demo / Shadow PnL: 5,000ms polling interval.
* **Resilience Policy:** In Sandbox / Development mode (`YARTRADER_ENV != 'production'`), MT5 provider returns friendly `Connected / HEALTHY` status. In Production, non-Windows containers fail-closed cleanly (`Disconnected / UNHEALTHY`).

---

## 4. Required Frontend API Client Architecture (`src/services/`)

Each domain module in `src/services/` follows a standardized structure:

```
src/services/
├── auth/           # Login, Register, Forgot, Session revocation
├── market/         # Public metrics, active symbols, market state
├── intelligence/   # Multi-timeframe status, XAI reasoning, SCM reports
├── research/       # Latest research reports, article feed
├── fractal/        # Multi-scale fractal status, scale states
├── regime/         # Volatility regime posture, transition events
├── decision/       # Advisory execution plans, confidence scores
├── risk/           # Portfolio heat, drawdown limits, emergency stop
├── trading/        # Backtest, MT5 Demo (#52961173), Paper Shadow
├── journal/        # Historical trades, trade notes, MAE/MFE facts
├── learning/       # Multi-timeframe pattern performance matrix
├── performance/    # Equity compounding, Sharpe ratio analytics
├── billing/        # Subscription plans, invoices, checkout
└── admin/          # DevOps status, SRE validation runner, audit trail
```

* **Standard Contract:** All API modules wrap `apiService` (`src/services/api.js`), attaching `Authorization: Bearer <token>` headers automatically, throwing structured error objects on non-2xx status, and logging API traces.

---

*Backend Integration Map certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
