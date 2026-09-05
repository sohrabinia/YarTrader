# YarTrader Frontend ↔ Backend Contract Matrix

| View Component | Backend Route | Schema / Contract | Loading State | Error State | Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `LandingView.jsx` | `/api/v1/health` | Status JSON | Spinner | Fallback Alert | Backend Service |
| `DashboardView.jsx` | `/api/research/current` | ResearchResult | Skeleton | UNAVAILABLE | Research Runtime |
| `IntelligenceView.jsx` | `/api/execution/plans` | ExecutionPlans | Loading Bar | UNKNOWN | Execution Planner |
| `DemoView.jsx` | `/api/demo/execute` | OrderResponse | Disabled Button | Rejected Alert | Demo Engine |
| `AdminView.jsx` | `/api/admin/status` | SystemHealth | Spinner | 403 / Denied | Admin API |
