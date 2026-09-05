# YarTrader Master Product Inventory

Generated as part of the Master Full-System Production Audit.

| Category | Component | Status | Notes / Location |
| :--- | :--- | :--- | :--- |
| Frontend | Landing Page (`/`) | IMPLEMENTED | `trader-terminal/src/LandingView.jsx` |
| Frontend | Terminal / Dashboard (`/dashboard`) | IMPLEMENTED | `trader-terminal/src/DashboardView.jsx` |
| Frontend | Intelligence View (`/intelligence`) | IMPLEMENTED | `trader-terminal/src/IntelligenceView.jsx` |
| Frontend | Backtesting View (`/backtest`) | IMPLEMENTED | `trader-terminal/src/BacktestingView.jsx` |
| Frontend | Demo Execution View (`/demo`) | IMPLEMENTED | `trader-terminal/src/DemoView.jsx` |
| Frontend | Shadow Trading View (`/shadow`) | IMPLEMENTED | `trader-terminal/src/ShadowView.jsx` |
| Frontend | Live Gate View (`/live-gate`) | IMPLEMENTED | `trader-terminal/src/LiveGateView.jsx` |
| Frontend | Signals View (`/signals`) | IMPLEMENTED | `trader-terminal/src/SignalsView.jsx` |
| Frontend | Execution Intelligence View (`/execution-intel`) | IMPLEMENTED | `trader-terminal/src/ExecutionIntelView.jsx` |
| Frontend | Cognitive Learning View (`/learning`) | IMPLEMENTED | `trader-terminal/src/LearningView.jsx` |
| Frontend | Admin Panel (`/admin`) | IMPLEMENTED | `trader-terminal/src/AdminView.jsx` |
| Frontend | Wallet / Billing View (`/wallet`) | MOCK / SIMULATED | `trader-terminal/src/PricingView.jsx` |
| Backend API | Core FastAPI Engine | IMPLEMENTED | `src/Application/Services/web_dashboard.py` |
| Backend API | MTF Research API | IMPLEMENTED | `/api/research/current` |
| Backend API | Execution Plans API | IMPLEMENTED | `/api/execution/plans` |
| Backend API | Demo Trading Execution API | IMPLEMENTED | `/api/demo/execute` |
| Database | Storage Manager & JSON Persistence | IMPLEMENTED | `src/Application/Deployment/storage.py` |
| Database | PostgreSQL / ORM Integration | NOT IMPLEMENTED | File-based JSON persistence active; relational DB pending migration |
| Payment | Payment Gateway (Stripe/Crypto/Fiat) | NOT IMPLEMENTED | No live merchant or payment processor integrated |
| Wallet | Fiat/Crypto On-Chain Wallet Ledger | NOT IMPLEMENTED | Paper trading/demo state active; real wallet NOT_IMPLEMENTED |
| Agents | Research & Intelligence Worker | IMPLEMENTED | `app/workers/research_worker.py` |
| Agents | Content / News / SEO Agents | IMPLEMENTED | `src/Growth/Agents/` |
| Brand | Option 01 Official Logo Identity | IMPLEMENTED | `trader-terminal/src/components/Header.jsx` (Lettermark Y+T) |
