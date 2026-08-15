==================================================
YARTRADER TASK D — RUNTIME TRUTH MATRIX
==================================================

Feature | UI Claim | API Source | Actual State | UI Correct? | Action Taken
Chat | Talk to YarTrader | /api/chat/assistant | CONNECTED | YES | Verified payload schema { message, lang }, error retry, and quick prompts
Dashboard Metrics | Active Markets / Trades / Uptime | /api/public/metrics | CONNECTED | YES | Mapped directly to API response
Backtest Runs | Historical Simulation History | /api/backtest/history | CONNECTED | YES | Provenance & leakage audit tags verified
Demo Orders | Alpari MT5 Demo Order History | /api/demo/trades | CONNECTED | YES | Demo account 52961173 orders verified
Shadow Balance | $1,000 USD Virtual Cash & Equity | /api/shadow/report | CONNECTED | YES | Sourced from paper account YARTRADER-PAPER-001
Live Trading | Real Money Trading Status | MetaTraderSafetyGate | HARD BLOCKED | YES | Hard-blocked warning card displayed
Signal Hub | Multi-Horizon Signals Feed | /api/user/signals | CONNECTED | YES | Categorized into Live, Shadow, Backtest, Historical
Learning Matrix | Pattern Evidence & Confidence | /api/intelligence/learning-matrix | CONNECTED | YES | Sample size (N) validation badges verified
Pricing Plans | Subscription Capabilities | /api/subscription/plans | CONNECTED | YES | Interactive capability drawer verified
Execution Intelligence | Structure Map & Risk Budget | /api/execution/* | CONNECTED | YES | Portfolio exposure array flat rendering verified
Admin Console | Active Symbol Ceiling (30/30) | /api/admin/symbols | CONNECTED | YES | Enforced 30 max active limit verified

==================================================
END OF RUNTIME TRUTH MATRIX
==================================================
