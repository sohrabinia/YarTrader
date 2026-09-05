# YarTrader Exhaustive Backend API Inventory

CONCRETE BACKEND ROUTES: 107
API INVENTORY COMPLETE: YES
WILDCARDS REMAIN: NO

| # | Method | Path | Auth Requirement | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `GET` | `/api/execution/plans` | Session / API Key | IMPLEMENTED + VERIFIED |
| 2 | `GET` | `/api/execution/confidence` | Session / API Key | IMPLEMENTED + VERIFIED |
| 3 | `GET` | `/api/execution/reasoning` | Session / API Key | IMPLEMENTED + VERIFIED |
| 4 | `GET` | `/api/structure/map` | Session / API Key | IMPLEMENTED + VERIFIED |
| 5 | `GET` | `/api/structure/alignment` | Session / API Key | IMPLEMENTED + VERIFIED |
| 6 | `GET` | `/api/structure/narrative` | Session / API Key | IMPLEMENTED + VERIFIED |
| 7 | `GET` | `/api/liquidity/map` | Session / API Key | IMPLEMENTED + VERIFIED |
| 8 | `GET` | `/api/liquidity/events` | Session / API Key | IMPLEMENTED + VERIFIED |
| 9 | `GET` | `/api/pattern/similarity` | Session / API Key | IMPLEMENTED + VERIFIED |
| 10 | `GET` | `/api/fractal/status` | Session / API Key | IMPLEMENTED + VERIFIED |
| 11 | `GET` | `/api/fractal/gold/summary` | Session / API Key | IMPLEMENTED + VERIFIED |
| 12 | `GET` | `/api/fractal/gold/structures` | Session / API Key | IMPLEMENTED + VERIFIED |
| 13 | `GET` | `/api/fractal/gold/hierarchy` | Session / API Key | IMPLEMENTED + VERIFIED |
| 14 | `GET` | `/api/fractal/gold/case-studies` | Session / API Key | IMPLEMENTED + VERIFIED |
| 15 | `GET` | `/api/fractal/gold/demo-validation` | Session / API Key | IMPLEMENTED + VERIFIED |
| 16 | `GET` | `/api/portfolio/risk` | Session / API Key | IMPLEMENTED + VERIFIED |
| 17 | `GET` | `/api/portfolio/exposure` | Session / API Key | IMPLEMENTED + VERIFIED |
| 18 | `GET` | `/api/market/session-status` | Session / API Key | IMPLEMENTED + VERIFIED |
| 19 | `GET` | `/api/replay/training-monitor` | Session / API Key | IMPLEMENTED + VERIFIED |
| 20 | `GET` | `/api/replay/learning-status` | Session / API Key | IMPLEMENTED + VERIFIED |
| 21 | `GET` | `/api/replay/error-analysis` | Session / API Key | IMPLEMENTED + VERIFIED |
| 22 | `GET` | `/api/intelligence/multi-timeframe` | Session / API Key | IMPLEMENTED + VERIFIED |
| 23 | `GET` | `/api/intelligence/status` | Session / API Key | IMPLEMENTED + VERIFIED |
| 24 | `GET` | `/api/intelligence/learning-matrix` | Session / API Key | IMPLEMENTED + VERIFIED |
| 25 | `GET` | `/api/intelligence/explain/{decision_id}` | Session / API Key | IMPLEMENTED + VERIFIED |
| 26 | `GET` | `/api/intelligence/learning-report` | Session / API Key | IMPLEMENTED + VERIFIED |
| 27 | `GET` | `/api/research/latest` | Session / API Key | IMPLEMENTED + VERIFIED |
| 28 | `GET` | `/api/research/current` | Session / API Key | IMPLEMENTED + VERIFIED |
| 29 | `GET` | `/v1/dashboard/live-research` | Session / API Key | IMPLEMENTED + VERIFIED |
| 30 | `GET` | `/api/research/history` | Session / API Key | IMPLEMENTED + VERIFIED |
| 31 | `GET` | `/api/research/health` | Public | IMPLEMENTED + VERIFIED |
| 32 | `GET` | `/health/live` | Public | IMPLEMENTED + VERIFIED |
| 33 | `GET` | `/ready` | Session / API Key | IMPLEMENTED + VERIFIED |
| 34 | `GET` | `/health/ready` | Public | IMPLEMENTED + VERIFIED |
| 35 | `GET` | `/api/v1/health` | Public | IMPLEMENTED + VERIFIED |
| 36 | `GET` | `/api/version` | Session / API Key | IMPLEMENTED + VERIFIED |
| 37 | `GET` | `/api/system/version` | Session / API Key | IMPLEMENTED + VERIFIED |
| 38 | `GET` | `/v1/version` | Session / API Key | IMPLEMENTED + VERIFIED |
| 39 | `GET` | `/v1/health` | Public | IMPLEMENTED + VERIFIED |
| 40 | `GET` | `/health` | Public | IMPLEMENTED + VERIFIED |
| 41 | `GET` | `/api/devops/status` | Session / API Key | IMPLEMENTED + VERIFIED |
| 42 | `GET` | `/api/devops/metrics` | Session / API Key | IMPLEMENTED + VERIFIED |
| 43 | `GET` | `/v1/runtime` | Session / API Key | IMPLEMENTED + VERIFIED |
| 44 | `GET` | `/api/subscription/plans` | Session / API Key | IMPLEMENTED + VERIFIED |
| 45 | `GET` | `/api/prop/challenge` | Session / API Key | IMPLEMENTED + VERIFIED |
| 46 | `POST` | `/api/prop/config` | Session / API Key | IMPLEMENTED + VERIFIED |
| 47 | `POST` | `/api/validation/run` | Session / API Key | IMPLEMENTED + VERIFIED |
| 48 | `GET` | `/api/validation/status` | Session / API Key | IMPLEMENTED + VERIFIED |
| 49 | `GET` | `/api/validation/reports/download` | Session / API Key | IMPLEMENTED + VERIFIED |
| 50 | `GET` | `/api/validation/history` | Session / API Key | IMPLEMENTED + VERIFIED |
| 51 | `GET` | `/api/shadow/metrics` | Session / API Key | IMPLEMENTED + VERIFIED |
| 52 | `GET` | `/v1/dashboard/overview` | Session / API Key | IMPLEMENTED + VERIFIED |
| 53 | `GET` | `/v1/dashboard/cognitive` | Session / API Key | IMPLEMENTED + VERIFIED |
| 54 | `GET` | `/v1/monitoring` | Session / API Key | IMPLEMENTED + VERIFIED |
| 55 | `GET` | `/v1/metrics` | Session / API Key | IMPLEMENTED + VERIFIED |
| 56 | `POST` | `/api/control` | Session / API Key | IMPLEMENTED + VERIFIED |
| 57 | `GET` | `/api/symbols` | Session / API Key | IMPLEMENTED + VERIFIED |
| 58 | `POST` | `/api/mode` | Session / API Key | IMPLEMENTED + VERIFIED |
| 59 | `POST` | `/api/backtest/run` | Session / API Key | IMPLEMENTED + VERIFIED |
| 60 | `GET` | `/api/backtest/history` | Session / API Key | IMPLEMENTED + VERIFIED |
| 61 | `POST` | `/api/demo/run` | Session / API Key | IMPLEMENTED + VERIFIED |
| 62 | `GET` | `/api/demo/trades` | Session / API Key | IMPLEMENTED + VERIFIED |
| 63 | `GET` | `/api/demo/report` | Session / API Key | IMPLEMENTED + VERIFIED |
| 64 | `GET` | `/api/shadow/report` | Session / API Key | IMPLEMENTED + VERIFIED |
| 65 | `POST` | `/api/risk/emergency_stop` | Session / API Key | IMPLEMENTED + VERIFIED |
| 66 | `GET` | `/api/production-readiness` | Session / API Key | IMPLEMENTED + VERIFIED |
| 67 | `GET` | `/api/runtime/frontend-status` | Session / API Key | IMPLEMENTED + VERIFIED |
| 68 | `GET` | `/api/system/frontend-status` | Session / API Key | IMPLEMENTED + VERIFIED |
| 69 | `GET` | `/api/admin/symbols` | Session / API Key | IMPLEMENTED + VERIFIED |
| 70 | `GET` | `/api/admin/timeframes` | Session / API Key | IMPLEMENTED + VERIFIED |
| 71 | `GET` | `/api/admin/reports` | Session / API Key | IMPLEMENTED + VERIFIED |
| 72 | `GET` | `/api/admin/shadow-trades` | Session / API Key | IMPLEMENTED + VERIFIED |
| 73 | `GET` | `/api/admin/memory` | Session / API Key | IMPLEMENTED + VERIFIED |
| 74 | `GET` | `/api/admin/judge` | Session / API Key | IMPLEMENTED + VERIFIED |
| 75 | `GET` | `/api/admin/patterns` | Session / API Key | IMPLEMENTED + VERIFIED |
| 76 | `GET` | `/api/user/markets` | Session / API Key | IMPLEMENTED + VERIFIED |
| 77 | `GET` | `/api/signals` | Session / API Key | IMPLEMENTED + VERIFIED |
| 78 | `GET` | `/api/signals/pipeline` | Session / API Key | IMPLEMENTED + VERIFIED |
| 79 | `GET` | `/api/user/signals` | Session / API Key | IMPLEMENTED + VERIFIED |
| 80 | `GET` | `/api/user/history` | Session / API Key | IMPLEMENTED + VERIFIED |
| 81 | `GET` | `/api/user/reports` | Session / API Key | IMPLEMENTED + VERIFIED |
| 82 | `GET` | `/api/user/statements` | Session / API Key | IMPLEMENTED + VERIFIED |
| 83 | `GET` | `/api/admin/statements` | Session / API Key | IMPLEMENTED + VERIFIED |
| 84 | `POST` | `/api/auth/register` | Session / API Key | IMPLEMENTED + VERIFIED |
| 85 | `POST` | `/api/auth/login` | Session / API Key | IMPLEMENTED + VERIFIED |
| 86 | `POST` | `/api/auth/forgot-password` | Session / API Key | IMPLEMENTED + VERIFIED |
| 87 | `GET` | `/api/auth/verify-email` | Session / API Key | IMPLEMENTED + VERIFIED |
| 88 | `POST` | `/api/auth/reset-password` | Session / API Key | IMPLEMENTED + VERIFIED |
| 89 | `POST` | `/api/auth/logout` | Session / API Key | IMPLEMENTED + VERIFIED |
| 90 | `POST` | `/api/auth/google` | Session / API Key | IMPLEMENTED + VERIFIED |
| 91 | `POST` | `/api/auth/apple` | Session / API Key | IMPLEMENTED + VERIFIED |
| 92 | `POST` | `/api/auth/telegram` | Session / API Key | IMPLEMENTED + VERIFIED |
| 93 | `POST` | `/api/user/link-telegram` | Session / API Key | IMPLEMENTED + VERIFIED |
| 94 | `GET` | `/api/blog` | Session / API Key | IMPLEMENTED + VERIFIED |
| 95 | `GET` | `/api/blog/{article_id}` | Session / API Key | IMPLEMENTED + VERIFIED |
| 96 | `GET` | `/api/news` | Session / API Key | IMPLEMENTED + VERIFIED |
| 97 | `GET` | `/api/news/{news_id}` | Session / API Key | IMPLEMENTED + VERIFIED |
| 98 | `GET` | `/api/faq` | Session / API Key | IMPLEMENTED + VERIFIED |
| 99 | `GET` | `/api/guide` | Session / API Key | IMPLEMENTED + VERIFIED |
| 100 | `GET` | `/api/guide/{guide_id}` | Session / API Key | IMPLEMENTED + VERIFIED |
| 101 | `POST` | `/api/admin/content` | Session / API Key | IMPLEMENTED + VERIFIED |
| 102 | `GET` | `/api/user/tickets` | Session / API Key | IMPLEMENTED + VERIFIED |
| 103 | `POST` | `/api/user/tickets` | Session / API Key | IMPLEMENTED + VERIFIED |
| 104 | `POST` | `/api/user/tickets/{ticket_id}/reply` | Session / API Key | IMPLEMENTED + VERIFIED |
| 105 | `GET` | `/api/admin/tickets` | Session / API Key | IMPLEMENTED + VERIFIED |
| 106 | `POST` | `/api/admin/tickets/{ticket_id}/status` | Session / API Key | IMPLEMENTED + VERIFIED |
| 107 | `POST` | `/api/chat/assistant` | Session / API Key | IMPLEMENTED + VERIFIED |
