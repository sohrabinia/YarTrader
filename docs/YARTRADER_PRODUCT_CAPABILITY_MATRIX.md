# YARTRADER V1.0 PRODUCT CAPABILITY MATRIX

## Executive Overview
This capability matrix defines the absolute production reality status for all core subsystems and user capabilities of YarTrader V1.0. Every status is classified under strict non-negotiable CTO runtime truth rules.

## Classification Definitions
- **COMPLETE**: Code exists + API works + Runtime works + Frontend exposes it + Evidence verified.
- **PARTIAL**: Implementation exists in codebase but key components or wiring are incomplete.
- **DOCUMENT ONLY**: Spec or documentation exists without executable runtime implementation.
- **BROKEN**: Exists in code/API but fails at runtime or returns unhandled errors.
- **REMOVED / LOST**: Functionality existed in historical commits but has been lost or disconnected.
- **NOT FOUND**: No code, endpoint, or implementation trace exists.

---

## Core Trading Capabilities

| Capability | Reality Status | Code Location / API Endpoint | Evidence Artifacts | Forensic Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Backtesting Engine** | **COMPLETE** | `src/Application/Backtesting/engine.py`<br>`POST /api/backtest/run` | `validation/backtest/`<br>`validation/backtest_forensic_evidence/` | Multi-asset historical backtesting with transaction cost accounting and zero lookahead leakage. |
| **Demo Trading Engine** | **COMPLETE** | `src/ShadowTrading/Engine/DemoScenarioRunner.py`<br>`POST /api/demo/run` | `validation/demo_trading/`<br>`validation/mt5_demo_e2e/` | Dynamic trade journal, real candle data, SL/TP execution, disk persistence. |
| **Shadow Trading Engine** | **COMPLETE** | `src/ShadowTrading/Engine/PredictiveShadowEngine.py`<br>`GET /api/shadow/report` | `validation/shadow_trading/` | $1,000 paper account execution, autonomous shadow position tracking. |
| **Live Trading Safety Gate** | **COMPLETE** | `src/Execution/Safety/safety_gate.py` | `validation/live_trading/LIVE_BOUNDARY_TEST.md` | Fail-closed SRE safety gate blocking direct order routing when `LIVE_TRADING_ENABLED=False`. |
| **Multi-Timeframe Perception** | **COMPLETE** | `src/Research/Brain/`<br>`GET /api/intelligence/multi-timeframe` | `tests/YarTrader.Tests/Providers/test_mtf_provenance_regression.py` | 8 canonical internal timeframes (1, 4, 16, 64, 256, 1024, 4096, 16384). |
| **Decision Intelligence Engine** | **COMPLETE** | `src/Decision/Intelligence/engine.py`<br>`GET /api/signals` | `validation/analysis_validation/` | Integrated Signal-Decision-Risk pipeline with structured JSON signals and confidence scoring. |
| **Learning & Market Memory** | **COMPLETE** | `src/Learning/`<br>`GET /api/learning/insights` | `tests/YarTrader.Tests/Learning/test_learning_admission_forensics.py` | Trade ledger forensics, concept promotion, and parameter tuning in `MarketMemorySystem`. |

---

## AI & Cognitive Capabilities

| Capability | Reality Status | Code Location / API Endpoint | Evidence Artifacts | Forensic Notes |
| :--- | :--- | :--- | :--- | :--- |
| **AI Assistant Chat** | **PARTIAL** | `web_dashboard.py`<br>`POST /api/chat/assistant` | `web_dashboard.py` | Backend endpoint exists and responds, but frontend error handler displays `[object Object]` on non-string error payloads. |
| **Research Agent** | **COMPLETE** | `src/Application/Agents/research_agent.py` | `src/Application/Agents/supervisor.py` | Registered in `supervisor.py` for multi-timeframe research orchestration. |
| **Strategy & Risk Agents** | **COMPLETE** | `src/Application/Agents/` | `src/Application/Agents/supervisor.py` | Concrete classes registered dynamically in `IntelligenceSupervisor`. |
| **Execution Agent** | **PARTIAL** | `src/Application/Agents/` | Codebase scan | Integrated into shadow/demo engine pipelines, but lacks standalone user controls. |
| **SEO Agent** | **DOCUMENT ONLY** | `docs/` | `docs/YARTRADER_PRODUCT_ROADMAP.md` | Mentioned in feature catalog; no concrete runtime agent implementation found. |
| **Content Agent** | **DOCUMENT ONLY** | `docs/` | `docs/YARTRADER_PRODUCT_ROADMAP.md` | Mentioned in feature catalog; no concrete runtime agent implementation found. |

---

## Financial, Payment & Monitisation Systems

| Capability | Reality Status | Code Location / API Endpoint | Evidence Artifacts | Forensic Notes |
| :--- | :--- | :--- | :--- | :--- |
| **User Wallet & Ledger** | **NOT FOUND** | N/A | Codebase scan | No internal wallet balance, ledger, deposit, or withdrawal tables or models exist. |
| **Payment Gateway** | **DOCUMENT ONLY** | `trader-terminal/src/App.jsx`<br>`#/pricing` | Pricing UI | UI pricing cards exist, but no active payment processor, webhook, or checkout API integrated. |
| **Crypto Payment Gateway** | **NOT FOUND** | N/A | Codebase scan | No USDT, BTC, ETH, TRC20, or Web3 blockchain verification logic found in backend. |
| **Subscription Management** | **PARTIAL** | `web_dashboard.py` | `src/Application/Dashboard/` | Basic static role/plan checks in auth repo; no billing cycle or invoice generation. |

---

## Growth, Telegram & Support Systems

| Capability | Reality Status | Code Location / API Endpoint | Evidence Artifacts | Forensic Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Telegram OAuth Login** | **NOT FOUND** | N/A | Codebase scan | No Telegram OAuth widget or backend authentication callback implemented. |
| **Telegram Bot (`YarTrader_bot`)** | **DOCUMENT ONLY** | `docs/` | `docs/YARTRADER_PRODUCT_ROADMAP.md` | Spec mentioned in docs; no active Bot token runner or webhook delivery code. |
| **Customer Support System** | **PARTIAL** | `web_dashboard.py`<br>`/api/support/*` | `web_dashboard.py` | Basic ticket endpoint exists, but lacks real-time admin support chat workflow in SPA. |
| **Prop Trading Module** | **NOT FOUND** | N/A | Codebase scan | No prop firm rules, challenge evaluation, or account funded status tracking logic exists. |
