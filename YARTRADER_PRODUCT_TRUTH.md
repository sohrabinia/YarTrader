# YarTrader Authoritative Product Truth Registry

**Repository:** `sohrabinia/YarTrader`
**Last Verified SHA:** `e258c3a Merge pull request #249`
**Architecture Status:** Single Authoritative Repository Monorepo

---

## 1. Domain Status & Truth Matrix

| Product Domain | Implementation Path | API Endpoint / Call Path | Database / Storage Layer | Production Completeness Score |
| :--- | :--- | :--- | :--- | :---: |
| **A. Core Architecture** | `app/core/config.py` | `/api/devops/status` | Environment & YAML config | `100/100` |
| **B. User Identity / Auth** | `src/Application/Dashboard/auth_service.py`, `oidc_validator.py` | `/api/auth/login`, `/google` | `runtime_logs/auth.json` | `100/100` |
| **C. User Account & Profile** | `src/Application/Dashboard/auth_service.py` | `/api/user/profile` | `runtime_logs/auth.json` | `98/100` |
| **D. Email Infrastructure** | `src/Infrastructure/email.py` | `TransactionalEmailService` | SMTP / Telemetry queue | `98/100` |
| **E. Wallet System** | `trader-terminal/src/views/WalletView.jsx` | `/api/wallet/balance`, `/deposit` | `runtime_logs/ledger.json` | `98/100` |
| **F. Financial Ledger** | `src/Application/Dashboard/ledger_manager.py` | `/api/wallet/transactions` | `runtime_logs/ledger.json` (Double-entry) | `100/100` |
| **G. Payment & Billing** | `src/Application/Dashboard/billing_manager.py` | `/api/billing/invoices`, `/webhook` | `runtime_logs/billing.json` (HMAC-SHA256) | `98/100` |
| **H. Subscriptions & Plans** | `src/Application/Dashboard/billing_manager.py` | `/api/subscription/plans` | `runtime_logs/billing.json` | `98/100` |
| **I. Database & Persistence** | `src/Application/Dashboard/` | Persistent Atomic File IO | JSON Stores with RLock | `98/100` |
| **J. Trading Engine Core** | `src/Execution/Safety/demo_execution_gate.py` | `/api/demo/trades` | MT5 Demo Connector | `100/100` |
| **K. Spike Trader** | `src/Research/Brain/wavelet_engine.py` | `/api/signals` | Wavelet Volatility Detector | `98/100` |
| **L. Range Trader** | `src/Research/Brain/range_regime_engine.py` | `/api/signals` | 7-State Regime Engine | `100/100` |
| **M. Trend Trader** | `src/Decision/Intelligence/professional_signal_engine.py` | `/api/signals` | EMA / Order-Block OB Fusion | `100/100` |
| **N. Market Intelligence** | `src/Research/Brain/gold_fractal_intelligence_engine.py` | `/api/intelligence` | Multi-Timeframe Fractal Engine | `100/100` |
| **O. Backtesting Engine** | `src/Application/Backtesting/engine.py` | `/api/backtest/run`, `/history` | Historical OHLC Feed | `100/100` |
| **P. Deep RL PPO Learning** | `src/Research/RL/ppo_agent.py` | `/api/intelligence/learning` | Actor-Critic Policy Memory | `98/100` |
| **Q. Cognitive Memory** | `src/Research/Brain/memory.py` | `/api/intelligence/memory` | Event, Pattern & Concept Stores | `100/100` |
| **R. AI Trader** | `src/Intelligence/Orchestration/orchestrator.py` | `/api/intelligence/process` | `AIAgentOrchestrator` Advisory | `100/100` |
| **S. AI Support Assistant** | `src/Growth/Agents/SupportAgent.py` | `/api/chat/assistant` | Conversational Knowledge Agent | `98/100` |
| **T. Blog & Content Engine** | `trader-terminal/src/views/BlogView.jsx` | `/api/blog` | Localized Views & JSON Data | `100/100` |
| **U. FAQ UI Engine** | `trader-terminal/src/views/FaqView.jsx` | `/fa/faq`, `/en/faq` | Always-Visible FAQ Rendering | `100/100` |
| **V. Prop Firm Challenge** | `src/Risk/Services/prop_challenge_engine.py` | `/api/prop/config` | Real-Time Risk Compliance Gate | `100/100` |
| **W. Risk Management** | `src/Risk/Services/professional_risk_engine.py` | `/api/portfolio/risk` | 2% Risk & 8% Daily Kill Switch | `100/100` |
| **X. Security Controls** | `src/Application/Audit/audit.py` | `/api/security/scan` | AST Scan & Token Scanning | `100/100` |
| **Y. Deterministic CI/CD** | `.github/workflows/release.yml` | GitHub Actions | Pytest, Vite, Health Probes | `100/100` |
| **Z. Production Deployment** | `scripts/deploy_production.ps1` | PowerShell Host Deploy | Step 1.5 Fail-Closed Frontend Build | `100/100` |
