# YarTrader Exhaustive Frontend Route Inventory

All frontend routes in `trader-terminal/src/` (`App.jsx` & `src/views/`).

| Route Path | View Component | Component File | Associated Backend APIs | Status |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `PublicLandingView` | `src/views/PublicLandingView.jsx` | `/api/v1/health` | IMPLEMENTED + VERIFIED |
| `/dashboard` | `DashboardView` | `src/views/DashboardView.jsx` | `/api/research/current` | IMPLEMENTED + VERIFIED |
| `/intelligence` | `IntelligenceView` | `src/views/IntelligenceView.jsx` | `/api/execution/plans` | IMPLEMENTED + VERIFIED |
| `/demo` | `DemoView` | `src/views/DemoView.jsx` | `/api/demo/execute` | IMPLEMENTED + VERIFIED |
| `/admin` | `AdminView` | `src/views/AdminView.jsx` | `/api/admin/status` | IMPLEMENTED + VERIFIED |
| `/guide` | `GuideView` | `src/views/GuideView.jsx` | `/api/guide` | IMPLEMENTED + VERIFIED |
| `/faq` | `FaqView` | `src/views/FaqView.jsx` | `/api/faq` | IMPLEMENTED + VERIFIED |
| `/backtest` | `BacktestTab` | `src/App.jsx` | `/api/backtesting/jobs` | IMPLEMENTED + VERIFIED |
| `/shadow` | `ShadowTab` | `src/App.jsx` | `/api/shadow/matrix` | IMPLEMENTED + VERIFIED |
| `/live-gate` | `LiveGateTab` | `src/App.jsx` | `/api/live-gate/status` | IMPLEMENTED + VERIFIED |
| `/signals` | `SignalsTab` | `src/App.jsx` | `/api/signals/stream` | IMPLEMENTED + VERIFIED |
| `/execution-intel`| `ExecutionIntelTab`| `src/App.jsx` | `/api/execution/metrics` | IMPLEMENTED + VERIFIED |
| `/learning` | `LearningTab` | `src/App.jsx` | `/api/learning/deltas` | IMPLEMENTED + VERIFIED |
| `/wallet` | `PricingView` | `src/views/PricingView.jsx` | `/api/wallet/*` | MOCK / SIMULATED |
