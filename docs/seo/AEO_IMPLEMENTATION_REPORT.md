# YARTRADER — ANSWER ENGINE OPTIMIZATION (AEO) REPORT

## AEO Strategy & Structured Question Answering Implementation

### 1. Direct Question-Answer Structures
Crawlable HTML views `FaqView` and `GuideView` present clear H2/H3 question headers and direct, factual answer blocks designed for AI answer engines (ChatGPT, Claude, Gemini, Copilot):
- **What is YarTrader?**: Autonomous financial intelligence platform for non-linear price structure analysis, risk management, and prop firm challenge evaluation.
- **Is YarTrader a broker?**: No. YarTrader is not a broker, liquidity provider, or fund manager and holds zero user deposits.
- **Does YarTrader execute live trades?**: No. Live trading is hard-blocked repository-wide (`LIVE_TRADING_ENABLED = False`). Execution is strictly restricted to simulated backtesting, MT5 demo accounts, and paper shadow trading.

### 2. JSON-LD FAQPage Schema Integration
`trader-terminal/index.html` includes structured `FAQPage` schema supplying structured question-answer entities directly to search engine parsers.
