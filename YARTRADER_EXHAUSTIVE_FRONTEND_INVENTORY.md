# YarTrader Exhaustive Frontend Inventory

Catalog of all frontend view routes inside `trader-terminal/src/` (`App.jsx` & `src/views/`).

| Route | View Component File | Purpose / Role | Backend API Connections | Status |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `PublicLandingView.jsx` | Public Product Overview | `/api/v1/health` | IMPLEMENTED + VERIFIED |
| `/dashboard` | `DashboardView.jsx` | Terminal Overview & Research | `/api/research/current` | IMPLEMENTED + VERIFIED |
| `/intelligence` | `IntelligenceView.jsx` | Execution Plans & Signals | `/api/execution/plans` | IMPLEMENTED + VERIFIED |
| `/demo` | `DemoView.jsx` | MT5 Demo Order Execution | `/api/demo/execute` | IMPLEMENTED + VERIFIED |
| `/admin` | `AdminView.jsx` | Administrator Panel | `/api/admin/status` | IMPLEMENTED + VERIFIED |
| `/guide` | `GuideView.jsx` | Platform Documentation | Static / Internal | IMPLEMENTED + VERIFIED |
| `/faq` | `FaqView.jsx` | Frequently Asked Questions | Static / Internal | IMPLEMENTED + VERIFIED |
| `/backtest` | `App.jsx` (tab) | Backtesting Engine UI | `/api/backtesting/*` | IMPLEMENTED + VERIFIED |
| `/shadow` | `App.jsx` (tab) | Shadow Trading UI | `/api/shadow/*` | IMPLEMENTED + VERIFIED |
| `/live-gate` | `App.jsx` (tab) | Live Safety Gate UI | `/api/live-gate/*` | IMPLEMENTED + VERIFIED |
| `/signals` | `App.jsx` (tab) | Signal Stream | `/api/signals/*` | IMPLEMENTED + VERIFIED |
| `/execution-intel`| `App.jsx` (tab) | Execution Analytics | `/api/execution/*` | IMPLEMENTED + VERIFIED |
| `/learning` | `App.jsx` (tab) | Cognitive RL Learning | `/api/learning/*` | IMPLEMENTED + VERIFIED |
| `/wallet` | `App.jsx` (tab) | Billing & Pricing | `/api/wallet/*` | MOCK / SIMULATED |
