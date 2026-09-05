# YarTrader Final Frontend ↔ Backend Contract Proof

Full frontend view to backend endpoint contract reconciliation.

| Frontend Component | Exact Backend Route | Request Schema | Response Schema | Error Handling / Fallback |
| :--- | :--- | :--- | :--- | :--- |
| `PublicLandingView.jsx` | `GET /api/v1/health` | None | `{status, version}` | Display offline notice |
| `DashboardView.jsx` | `GET /api/research/current` | `{timeframe}` | `ResearchResult` | Render `UNAVAILABLE` |
| `IntelligenceView.jsx` | `GET /api/execution/plans` | `{symbol}` | `ExecutionPlan` | Render `UNKNOWN` |
| `DemoView.jsx` | `POST /api/demo/execute` | `OrderRequest` | `OrderResponse` | Show failure alert |
| `AdminView.jsx` | `GET /api/admin/status` | None | `SystemStatus` | 403 Access Denied |
| `GuideView.jsx` | `GET /api/guide` | None | `GuideList` | Local fallback text |
| `FaqView.jsx` | `GET /api/faq` | None | `FaqList` | Local fallback text |
| `App.jsx` (Backtest) | `POST /api/backtest/run` | `BacktestParams` | `BacktestResult` | Render job error |
| `App.jsx` (Shadow) | `GET /api/shadow/matrix` | None | `ShadowMatrix` | Display offline status |
| `App.jsx` (Live Gate) | `GET /api/live-gate/status` | None | `SafetyGateStatus` | Display gate status |
