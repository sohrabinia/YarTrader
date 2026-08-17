# YARTRADER FRONTEND SCREEN & ROUTE INVENTORY

**Frontend Framework:** React 18.3 + Vite 5.4
**Root Entry Point:** `trader-terminal/src/App.jsx`
**Routing Strategy:** Hash-based SPA routing (`window.location.hash`)

---

## 1. ROUTE INVENTORY MAP

| Route Hash | Screen / Module Name | Purpose & Function | Auth Required | User Role | Main Data Sources |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `#/` or `#/dashboard` | **Main Dashboard** | Core terminal overview, live equity, system status, market ticker | No (Public/Trader) | Trader / Public | `/api/dashboard`, `/api/health` |
| `#/backtest` | **Backtest Studio** | Walk-forward simulation engine & historical trade analysis | Yes | Trader | `/api/backtest/run`, `/api/backtest/history` |
| `#/demo` | **MT5 Demo Terminal** | Autonomous DEMO execution monitor & account metrics | Yes | Trader | `/api/demo/run`, `/api/demo/status` |
| `#/shadow` | **Shadow Trading** | Virtual $1,000 paper trading execution & signal matrix | Yes | Trader | `/api/shadow/report`, `/api/shadow/trade` |
| `#/live` | **Live Execution Gate** | MT4 Live Execution Safety Gate (Hard-blocked by default) | Yes | Trader / Admin | `/api/live/status` |
| `#/signals` | **Signal Center** | Real-time Price Action signal feed & risk/reward metrics | Yes | Trader | `/api/signals/active`, `/api/signals/history` |
| `#/learning` | **Learning Memory** | Cognitive pattern memory, confidence weights, and adaptation history | Yes | Trader | `/api/learning/patterns`, `/api/learning/history` |
| `#/execution-intel` | **Execution Intelligence**| Multi-timeframe perception, spread, commission & slippage analysis | Yes | Trader | `/api/intelligence/multi-timeframe` |
| `#/pricing` | **Tier Subscriptions** | Subscription plans (Free, Pro, Institutional) & upgrade flow | No | Public / Trader | `/api/pricing/tiers` |
| `#/admin` | **Admin DevOps Panel** | System health, SCM logs, emergency stop, backup/restore controls | Yes | Admin | `/api/admin/health`, `/api/admin/backup` |
| `#/login` | **Authentication Modal** | User login, registration, and Google/Apple OAuth triggers | No | Public | `/api/auth/login`, `/api/auth/register` |

---

## 2. SCREEN DETAILS & STATES

### 1. Main Dashboard (`#/dashboard`)
- **Main Components:** Stat Cards (Balance, Equity, Win Rate, Profit Factor), Equity Curve Chart, Quick Action Buttons, AI Assistant Floating Drawer (`Talk to YarTrader`).
- **Data Dependencies:** `/api/dashboard`
- **Loading State:** Skeleton card shimmer loader.
- **Error State:** Fallback error toast with retry action.

### 2. Backtest Studio (`#/backtest`)
- **Main Components:** Strategy Config Form (Symbol, Timeframe, Date Range, Initial Balance), Backtest Results Table, Equity Curve Chart, Trade Ledger.
- **Data Dependencies:** `POST /api/backtest/run`
- **Loading State:** "Simulating historical candles..." progress bar.

### 3. MT5 Demo Terminal (`#/demo`)
- **Main Components:** MT5 Connection Status Badge, Active Orders Table, Open Positions Table, Trade History, P&L Summary.
- **Data Dependencies:** `GET /api/demo/status`, `POST /api/demo/run`
- **Safety Gate:** Displays `MT5 DEMO ONLY (Account 52961173)`.

### 4. Shadow Trading (`#/shadow`)
- **Main Components:** Virtual Balance Card ($1,000 Paper Balance), Pending Orders, Open Shadow Positions, Executed Shadow Trades.
- **Data Dependencies:** `GET /api/shadow/report`

### 5. Live Execution Gate (`#/live`)
- **Main Components:** SRE Safety Gate Alert, MT4 ECN Account Details, Hard-Block Warning Banner, Enable Switch (Disabled).
- **Safety Gate:** Hard-blocks live trading when `LIVE_TRADING_ENABLED=False`.

### 6. Signal Center (`#/signals`)
- **Main Components:** Active Signal Cards (Symbol, Timeframe, Direction, Entry, SL, TP, Confidence), Risk/Reward Gauge, Signal History Table.
- **Data Dependencies:** `GET /api/signals/active`

### 7. Learning Memory (`#/learning`)
- **Main Components:** Pattern Frequency Matrix, Win/Loss Rate per Pattern, Confidence Weight Sliders, Learning Adaptation History.
- **Data Dependencies:** `GET /api/learning/patterns`

### 8. Execution Intelligence (`#/execution-intel`)
- **Main Components:** Multi-timeframe Perception Matrix (M15/H1/H4/D1), Spread/Commission/Slippage Calculator, Market Microstructure Ticker.
- **Data Dependencies:** `GET /api/intelligence/multi-timeframe`

### 9. Admin DevOps Panel (`#/admin`)
- **Main Components:** Service Health Monitoring, Emergency Stop Switch, Backup & Restore Trigger, Audit Log Viewer.
- **Data Dependencies:** `GET /api/admin/health`
