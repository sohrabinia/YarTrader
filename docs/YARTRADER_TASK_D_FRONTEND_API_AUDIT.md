==================================================
YARTRADER TASK D — FRONTEND API AUDIT
==================================================

Endpoint | Method | Component | Expected Response | Actual Response | Auth | Status | Fallback
/api/public/metrics | GET | Dashboard / Marketing | active_markets_count, historical_simulated_trades | Matched | Public | CONNECTED | DEMO/UNREACHABLE
/api/subscription/plans | GET | Pricing UI | Array of Plan Objects | Matched | Public | CONNECTED | Empty Array
/api/blog | GET | Blog UI | Array of Article Objects | Matched | Public | CONNECTED | Empty Array
/api/user/markets | GET | Terminal UI | Array of Market Objects | Matched | Bearer Token | CONNECTED | Empty Array
/api/user/signals | GET | Signal Hub UI | Array of Signal Objects | Matched | Bearer Token | CONNECTED | Empty Array
/api/backtest/history | GET | Backtest UI | Array of Backtest Runs | Matched | Bearer Token | CONNECTED | Empty Array
/api/backtest/run | POST | Backtest Form | { status, run_id, message } | Matched | Bearer Token | CONNECTED | Error Toast
/api/demo/trades | GET | Demo UI | Array of Trade Objects | Matched | Bearer Token | CONNECTED | Empty Array
/api/demo/report | GET | Demo UI | Demo Account Overview | Matched | Bearer Token | CONNECTED | Empty Object
/api/shadow/report | GET | Shadow UI | { account_id, balance, equity } | Matched | Bearer Token | CONNECTED | $1,000 Fallback
/api/intelligence/learning-matrix | GET | Learning UI | Array of Pattern Objects | Matched | Bearer Token | CONNECTED | Empty Array
/api/chat/assistant | POST | Floating Chatbot | { response, status, timestamp } | Matched | Bearer Token | CONNECTED | Localized Retry Notice
/api/admin/symbols | GET | Admin Console | { active_symbols, registered_symbols } | Matched | Admin Token | CONNECTED | Empty Array
/api/admin/reports | GET | Admin Console | { reports } | Matched | Admin Token | CONNECTED | Empty Array
/api/devops/status | GET | Admin Console | DevOps Infrastructure Metrics | Matched | Admin Token | CONNECTED | Empty Object
/api/validation/status | GET | Admin Console | Validation History & Logs | Matched | Admin Token | CONNECTED | Empty Object

==================================================
END OF FRONTEND API AUDIT
==================================================
