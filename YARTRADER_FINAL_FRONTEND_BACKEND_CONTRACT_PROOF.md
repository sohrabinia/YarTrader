# YarTrader Final Frontend ↔ Backend Contract Proof

FRONTEND API CONTRACT COUNT: 14

| # | Frontend Component | Exact Concrete Backend Path | HTTP Method | Request Schema | Response Schema | Loading State | Error Handling / Fallback |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `PublicLandingView.jsx` | `/api/v1/health` | `GET` | None | `{status, version}` | Spinner | Render offline alert |
| 2 | `DashboardView.jsx` | `/api/research/current` | `GET` | `{timeframe}` | `ResearchResult` | Skeleton | Render `UNAVAILABLE` |
| 3 | `IntelligenceView.jsx` | `/api/execution/plans` | `GET` | `{symbol}` | `ExecutionPlan` | Progress Bar | Render `UNKNOWN` |
| 4 | `DemoView.jsx` | `/api/demo/execute` | `POST` | `OrderRequest` | `OrderResponse` | Disabled Button | Show failure alert |
| 5 | `AdminView.jsx` | `/api/admin/status` | `GET` | None | `SystemStatus` | Spinner | 403 Access Denied |
| 6 | `GuideView.jsx` | `/api/guide` | `GET` | None | `GuideList` | Skeleton | Local fallback guide text |
| 7 | `FaqView.jsx` | `/api/faq` | `GET` | None | `FaqList` | Skeleton | Local fallback FAQ text |
| 8 | `App.jsx` (Backtest) | `/api/backtest/run` | `POST` | `BacktestParams` | `BacktestResult` | Running Bar | Render execution error |
| 9 | `App.jsx` (Shadow) | `/api/shadow/matrix` | `GET` | None | `ShadowMatrix` | Loading Pulse | Render offline status |
| 10 | `App.jsx` (Live Gate) | `/api/live-gate/status` | `GET` | None | `SafetyGateStatus` | Loading Pulse | Render gate blocked |
| 11 | `App.jsx` (Signals) | `/api/signals/stream` | `GET` | None | `SignalList` | Stream Pulse | Display standard stream |
| 12 | `App.jsx` (Intel) | `/api/execution/metrics` | `GET` | None | `ExecutionMetrics` | Loading Pulse | Display offline metrics |
| 13 | `App.jsx` (Learning) | `/api/learning/deltas` | `GET` | None | `LearningDeltas` | Loading Pulse | Display zero deltas |
| 14 | `PricingView.jsx` | `/api/pricing/tiers` | `GET` | None | `PricingTiers` | Spinner | Mock tier state |
