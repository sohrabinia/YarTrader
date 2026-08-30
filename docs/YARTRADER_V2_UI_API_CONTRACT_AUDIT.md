# YarTrader V2 — UI/API Contract Audit Matrix

**Date:** February 2026
**Scope:** Frontend UI Components to Backend REST APIs & Adapter Contracts

---

## 1. Executive Summary

This contract audit maps every active user interface component and view in `trader-terminal` to its corresponding backend REST API endpoint, HTTP method, authentication level, DTO schema, and status response. Shadow Trading presentation contracts have been retired from active UI dependencies.

---

## 2. Active Product API Contract Matrix

| UI Component / View | Target REST Endpoint | Method | Auth Level | Request DTO | Response DTO / Payload | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Public Landing** | `/api/public/metrics` | GET | Public | None | `{ active_markets_count, platform_uptime_pct }` | **VERIFIED** |
| **Version Banner** | `/api/version` | GET | Public | None | `{ application: "YarTrader", version: "7.0", commit, environment }` | **VERIFIED** |
| **Pricing View** | `/api/subscription/plans` | GET | Public | None | List of plan objects (`tier_id`, `name`, `price_usd`, `max_symbols`, `features`) | **VERIFIED** |
| **Blog View** | `/api/blog` | GET | Public | None | List of blog article objects (`id`, `title`, `date`, `author`, `summary`, `tags`) | **VERIFIED** |
| **User Signals** | `/api/user/signals` | GET | User Token | Query `horizon` | List of signal objects (`symbol`, `direction`, `timeframe`, `confidence`, `reason`) | **VERIFIED** |
| **Signal Pipeline** | `/api/signals` | GET | User Token | None | Diagnostic pipeline counts (`candidates_evaluated`, `rejected_by_risk`, etc.) | **VERIFIED** |
| **Execution Intel** | `/api/execution/plans` | GET | User Token | Query `symbol, timeframe` | Execution plan object (`symbol`, `action`, `entry_price`, `stop_loss`, `take_profit`) | **VERIFIED** |
| **Execution Confidence**| `/api/execution/confidence` | GET | User Token | Query `symbol, timeframe` | `{ confidence_score, factors, overall_rating }` | **VERIFIED** |
| **Structure Map** | `/api/structure/map` | GET | User Token | Query `symbol, timeframe` | `{ structure_nodes: [ { node_index, price, type, label } ] }` | **VERIFIED** |
| **Liquidity Map** | `/api/liquidity/map` | GET | User Token | Query `symbol, timeframe` | `{ order_blocks: [...], fair_value_gaps: [...] }` | **VERIFIED** |
| **Portfolio Risk** | `/api/portfolio/risk` | GET | User Token | None | `{ portfolio_heat, risk_budget_remaining, drawdown_level, risk_approved }` | **VERIFIED** |
| **Learning Matrix** | `/api/intelligence/learning-matrix` | GET | User Token | None | Array of pattern objects (`pattern_key`, `pattern_name`, `sample_count`, `win_rate_pct`) | **VERIFIED** |
| **Backtest History** | `/api/backtest/history` | GET | User Token | None | List of backtest run objects (`run_id`, `symbol`, `timeframe`, `total_trades`, `win_rate_pct`) | **VERIFIED** |
| **Backtest Run** | `/api/backtest/run` | POST | User Token | `{ symbol, timeframe, bars }` | `{ job_id, message, status }` | **VERIFIED** |
| **Demo Trades** | `/api/demo/trades` | GET | User Token | None | List of demo trade objects from MT5 Demo Account | **VERIFIED** |
| **User Statements** | `/api/user/statements` | GET | User RBAC | Query `account_id, period, token` | Statement DTO (`account_id`, `opening_balance`, `trade_ledger`, `risk_summary`) | **VERIFIED** |
| **Admin Statements** | `/api/admin/statements` | GET | Admin RBAC | Query `period, token` | Admin aggregate statement DTO (`account_id: "SYSTEM-AGGREGATE"`, `accounts_count`) | **VERIFIED** |
| **Admin Symbols** | `/api/admin/symbols` | GET/POST | Admin RBAC | Query `token`, JSON `{ symbol, timeframe }` | `{ registered_symbols: [...] }` | **VERIFIED** |
| **Admin Reports** | `/api/admin/reports` | GET | Admin RBAC | Query `token` | List of intelligence performance reports | **VERIFIED** |
| **DevOps Status** | `/api/devops/status` | GET | Admin RBAC | None | `{ status, scheduler_active, mt5_connected, apes_compliance }` | **VERIFIED** |
| **Validation Run** | `/api/validation/run` | POST | Admin RBAC | None | `{ status: "Accepted" \| "Already Running", phase }` | **VERIFIED** |
| **Validation Status** | `/api/validation/status` | GET | Admin RBAC | None | `{ phase, component, test, readiness_score, logs }` | **VERIFIED** |
