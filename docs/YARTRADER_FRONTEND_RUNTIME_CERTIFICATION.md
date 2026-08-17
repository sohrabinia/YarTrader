# YARTRADER FRONTEND RUNTIME CERTIFICATION

## Executive Overview
This document certifies that the React single-page application (`trader-terminal/src/App.jsx`) is directly connected to real backend API endpoints and displays active runtime data across all user-facing views without static, hardcoded, or mock fallbacks.

---

## Page-by-Page Real Data Certification Matrix

| Page / Route | API Source Endpoint | Real Data Status | Verified | Key Data Fields Certified |
|---|---|---|---|---|
| **Dashboard (`#/dashboard`)** | `/api/user/signals`, `/api/user/markets` | **YES** | ✅ PASS | Signal ID, posture, confidence %, entry/target/invalidation levels, narrative |
| **Signals (`#/signals`)** | `/api/user/signals`, `/api/user/history` | **YES** | ✅ PASS | Active & historical signals, horizon filters, setup reasonings |
| **Backtest (`#/backtest`)** | `/api/backtest/history`, `/api/backtest/run` | **YES** | ✅ PASS | Backtest Run ID, symbol, win rate %, profit factor, max drawdown %, Sharpe ratio |
| **Demo Trading (`#/demo`)** | `/api/demo/trades`, `/api/demo/report` | **YES** | ✅ PASS | Broker demo account ID (`52961173`), open/closed trades, ticket ID, realized P&L, win rate |
| **Shadow Trading (`#/shadow`)** | `/api/shadow/report`, `/api/admin/shadow-trades` | **YES** | ✅ PASS | Virtual paper balance ($1,000 baseline + P&L), virtual position tickets, unrealized P&L |
| **Execution Intel (`#/execution-intel`)** | `/api/execution/plans`, `/api/structure/map`, `/api/liquidity/map`, `/api/portfolio/risk` | **YES** | ✅ PASS | Pure price action swing nodes, order blocks, FVG gaps, BSL/SSL liquidity, portfolio heat % |
| **Learning Matrix (`#/learning`)** | `/api/intelligence/learning-matrix` | **YES** | ✅ PASS | Pattern keys, sample sizes ($N$), win rates %, average R:R, active confidence multipliers |
| **SRE Admin (`#/admin`)** | `/api/devops/status`, `/api/devops/metrics`, `/api/admin/symbols`, `/api/admin/reports` | **YES** | ✅ PASS | Active symbols count (max 30 limit), SCM per-context reports, service health, pipeline latency, memory usage |

---

## Anti-Mock Enforcement
1. **Zero Mock Fallbacks**: Hardcoded static mock counters have been completely removed.
2. **Social Login Connection**: Social login calls `/api/auth/google` and `/api/auth/apple` REST endpoints.
3. **Bilingual Reactivity**: Locales (`fa`, `en`, `tr`, `ar`) automatically set `dir="rtl"` or `dir="ltr"` and `lang`.
