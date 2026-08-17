# YARTRADER FRONTEND COMPLETE HANDOFF REPORT

**Primary Source of Truth for Frontend Redesign**
**Package Directory:** `trader-terminal`
**Date:** 2026-08-17
**Author:** YarTrader Frontend Architecture & Systems Engineering

---

## 1. EXECUTIVE SUMMARY & MISSION

This document serves as the **single authoritative handoff specification** for the YarTrader frontend application (`trader-terminal`). It describes the current implementation, routing architecture, design system, API communication contracts, and trading safety boundaries.

### Key Mandate for Redesign:
1. **DO NOT MODIFY BACKEND CONTRACTS:** All FastAPI routes, payload schemas, and response formats defined in `src/Application/Services/web_dashboard.py` must remain 100% unchanged.
2. **MAINTAIN TRADING SAFETY BOUNDARIES:**
   - **MT4:** Reserved strictly for Signal Generation & Live Execution Simulation.
   - **MT5:** Reserved strictly for Historical Backtesting & DEMO Trading (`52961173` on `Alpari-MT5-Demo`).
   - **Live Trading Block:** `LIVE_TRADING_ENABLED=False` must be clearly communicated as hard-blocked by SRE safety policy.
3. **PRESERVE ALL 11 ROUTES & MULTI-LANGUAGE LOCALIZATION:** All 11 hash routes (`#/dashboard`, `#/backtest`, `#/demo`, `#/shadow`, `#/live`, `#/signals`, `#/learning`, `#/execution-intel`, `#/pricing`, `#/admin`, `#/login`) and 4 user locales (`fa`, `en`, `tr`, `ar`) must be supported.

---

## 2. FRONTEND ARCHITECTURE & TOOLCHAIN

- **Root Directory:** `trader-terminal/`
- **Framework:** React 18.3.1
- **Build System:** Vite 5.4.1
- **Styling:** Tailwind CSS / Utility CSS (`src/assets/globals.css`)
- **State Management:** React `useState` & `useEffect` + Local Storage Persistence (`useAuthStore.js`)
- **Localization:** Custom i18n context (`src/services/i18n.jsx`) supporting Persian (RTL), Arabic (RTL), English (LTR), and Turkish (LTR).
- **HTTP Client:** Custom `apiService` wrapper (`src/services/api.js`) with auth headers & error handling.

---

## 3. ROUTE & SCREEN INVENTORY SUMMARY

| Route Hash | Screen Name | Key Purpose | Primary API Endpoint |
| :--- | :--- | :--- | :--- |
| `#/` / `#/dashboard` | Main Terminal Dashboard | Live balance, equity curve, quick metrics | `GET /api/dashboard` |
| `#/backtest` | Backtest Studio | Historical candle walk-forward backtesting | `POST /api/backtest/run` |
| `#/demo` | MT5 Demo Terminal | Autonomous DEMO execution & order history | `GET /api/demo/status` |
| `#/shadow` | Shadow Paper Trading | Virtual $1,000 paper trading execution | `GET /api/shadow/report` |
| `#/live` | Live Execution Gate | SRE Safety Gate status & MT4 ECN details | `GET /api/live/status` |
| `#/signals` | Signal Center | Active price action signals & R:R metrics | `GET /api/signals/active` |
| `#/learning` | Learning Memory | Cognitive pattern memory & win rate matrix | `GET /api/learning/patterns` |
| `#/execution-intel` | Execution Intelligence | Multi-timeframe perception & spread/slippage | `GET /api/intelligence/multi-timeframe` |
| `#/pricing` | Tier Subscriptions | Subscription plans (Free, Pro, Institutional) | `GET /api/pricing/tiers` |
| `#/admin` | Admin DevOps Panel | System health, SCM logs, backup/restore | `GET /api/admin/health` |
| `#/login` | Auth Modal | Login, registration, OAuth triggers | `POST /api/auth/login` |

---

## 4. API CONTRACT MAPPING TABLE

| Frontend Action / View | HTTP Method | Backend Route Endpoint | Payload / Params | Expected Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| Load Dashboard Metrics | `GET` | `/api/public/metrics` | None | `{ balance, equity, win_rate, profit_factor }` |
| Run Backtest | `POST` | `/api/backtest/run` | `{ symbol, timeframe, date_from, date_to }` | `{ trades, equity_curve, win_rate, profit_factor }` |
| Fetch DEMO Status | `GET` | `/api/demo/status` | None | `{ account, server, open_positions, order_history }` |
| Fetch Shadow Report | `GET` | `/api/shadow/report` | None | `{ balance: 1000.0, open_positions, closed_trades }` |
| Fetch Active Signals | `GET` | `/api/user/signals` | `?horizon=M15` | `[ { signal_id, symbol, action, entry, sl, tp, confidence } ]` |
| Fetch Pattern Matrix | `GET` | `/api/intelligence/learning-matrix` | None | `{ patterns: [ { name, wins, losses, win_rate, weight } ] }` |
| AI Chat Assistant | `POST` | `/api/chat/assistant` | `{ message, lang }` | `{ response: string }` |
| User Login | `POST` | `/api/auth/login` | `{ email, password }` | `{ token, user: { id, email, role } }` |

---

## 5. DESIGN SYSTEM SPECIFICATION

- **Primary Colors:**
  - Background: Dark Slate (`#0f172a` / `#1e293b`)
  - Accent / Primary: Emerald (`#10b981`), Cyan (`#06b6d4`)
  - Success / Long: Green (`#22c55e`)
  - Danger / Short: Red (`#ef4444`)
  - Warning: Amber (`#f59e0b`)
  - Info / Demo: Blue (`#3b82f6`)
- **Typography:** Inter, Vazirmatn (Persian), System UI Sans-serif.
- **RTL Support:** Dynamic `dir="rtl"` / `dir="ltr"` attribute handling.

---

## 6. HANDOFF FILE MANIFEST & BUILD COMMANDS

- **Manifest File:** `docs/YARTRADER_FRONTEND_FILE_MANIFEST.json`
- **Build Command:** `npm run build` (in `trader-terminal/`)
- **Dev Command:** `npm run dev` (in `trader-terminal/`)
- **Handoff Verdict:** `COMPLETE & READY FOR REDESIGN`
