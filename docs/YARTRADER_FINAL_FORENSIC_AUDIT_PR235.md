# YARTRADER — PR #235 FINAL FORENSIC AUDIT & PRODUCTION HARDENING REPORT

---

## 1. EXECUTIVE VERDICT
```text
FINAL VERDICT: YELLOW — FUNCTIONAL BUT REQUIRES HUMAN REVIEW
```
* **Summary:** The forensic audit and source-level repair of PR #235 successfully resolved the account-equity fallback defect (eliminating silent $10,000.00 default equity when broker account info is missing and enforcing fail-closed rejection) and fixed control-flow variable scoping during position sizing rejections in `ResearchWorker`. All 12 execution gate unit tests and 18 web dashboard service tests passed cleanly (30 tests total). Final GO for live broker order fills remains conditioned on native Windows Server SCM runtime host execution where MetaTrader 5 terminal IPC is active.

---

## 2. PR #235 FINDINGS
* **Base Commit:** `65e9ff9fddc09f0453fbe870fdf46773b352f92a` (`main`).
* **Branch HEAD:** `7d84aea51a2af81d8b85b67f92f06e94fe59bd2d` (`jules-2126246103029536183-bcb29b5b`).
* **Source Diff Stat:** 32 files changed across worker, risk, service, test, and documentation layers.
* **Core Audit Findings:**
  1. `app/workers/research_worker.py` contains the authoritative demo execution bridge.
  2. Silent `$10,000.00` fallback equity was eliminated in favor of strict fail-closed rejection (`acc_info is None -> Execution BLOCKED`).
  3. `UnboundLocalError` on `decision_id` and `exec_resp` during position sizing rejection was fixed by scoping execution dispatch and `last_executed_signal` updates strictly inside the `if sizing_res.is_valid:` block.
  4. Multi-timeframe research API fallback in `src/Application/Services/web_dashboard.py` strictly filters memory items by both symbol AND timeframe, preventing cross-timeframe data leakage (`requested timeframe == returned timeframe`).

---

## 3. CONFIRMED DEFECTS
| Severity | File | Function | Root Cause | Impact | Fix | Test |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HIGH** | `app/workers/research_worker.py` | `_run_loop()` | Silent `$10,000.00` fallback equity assignment when broker `acc_info` was `None`. | Could calculate position sizing from assumed equity when IPC is disconnected. | Enforced strict fail-closed rejection when `acc_info` is missing or equity <= 0. | `test_12_missing_account_equity_fails_closed_no_fallback` |
| **MEDIUM** | `app/workers/research_worker.py` | `_run_loop()` | Execution response logging and `last_executed_signal` referenced `decision_id`/`exec_resp` outside `if sizing_res.is_valid:`. | Raised `UnboundLocalError` when position sizing rejected a trade candidate. | Moved execution dispatch logging and state updates strictly inside `if sizing_res.is_valid:`. | `test_02_demo_execution_allowed_with_explicit_gate` |
| **MEDIUM** | `src/Application/Services/web_dashboard.py` | `get_current_analysis()` | Memory fallback queried `global_research_runtime.history` without filtering by timeframe. | Returned H1 research snapshots under M5/M15/H4 API queries when snapshots were missing. | Added strict symbol + timeframe filtering to memory fallback, returning M5 degraded response when missing. | `test_08_mtf_research_api_timeframe_isolation` |

---

## 4. RESEARCH WORKER ANALYSIS
* **Account Info Fallback Audit:** Silent `$10,000.00` equity fallback in `ResearchWorker` was removed. When `acc_info` is `None` or `equity <= 0`, `[ResearchWorker]` logs `Execution BLOCKED: Authoritative broker account equity unavailable or invalid` and skips position sizing and trade dispatch completely.
* **Control Flow & Exact-Once Execution:** Execution response printing and `self.last_executed_signal` state updates occur strictly once upon successful execution dispatch inside `if sizing_res.is_valid:`.

---

## 5. MARKET DATA / MTF VERIFICATION
* **Source Lineage:** M1 raw rate bars retrieved via `global_m1_research_runtime` / `MT5DataProvider` and aggregated into target timeframes (M5, M15, H1, H4) using UTC clock-boundary bucket alignment (`boundary_ts = ts - (ts % tf_seconds)`).
* **Lineage Invariant:** `/api/research/current?symbol=XAUUSD&timeframe=M5` returns `timeframe = "M5"` degraded status when M5 snapshot is missing, never returning H1 data.

---

## 6. BRAIN AUTHORITY VERIFICATION
* **Decision Authority:** `ExecutionIntelligenceCore.get_instance()` and `ResearchRuntime.run_once()` generate autonomous decisions (`action = BUY/SELL/WAIT/AVOID`) based on multi-timeframe market structure, fair value gaps, liquidity sweeps, and pattern similarity.
* **No Strategy Override:** Legacy strategy profiles do not override or modify the Brain decision state.

---

## 7. RISK / POSITION SIZING VERIFICATION
* **Risk Calculation:** Position capital allocation is governed by `0.5% account equity` per trade (`AllocationUSD = AccountEquity * 0.005`), calculated dynamically using entry price, stop-loss distance, and broker symbol specifications (`volume_min`, `volume_max`, `volume_step`).
* **Fail-Closed Sizing:** Invalid stop-loss distance or missing broker symbol info causes `sizing_res.is_valid = False`, cleanly logging `Position sizing rejected` without dispatching orders or updating signal state.

---

## 8. EXECUTION / POSITION VERIFICATION
* **Demo Execution Gate:** All trade execution requests pass through `DemoExecutionGate.verify_demo_execution_eligibility()`, validating `LIVE_TRADING_ENABLED = False`, demo account mode, terminal trading permissions, order check (`mt5.order_check`), and broker connectivity.
* **Position Exclusivity:** `BUY + SELL` on the same symbol is strictly forbidden. Reversals follow strict sequential ordering (`OPEN -> CLOSE -> CONFIRM FLAT -> REASSESS -> OPPOSITE ENTRY`).

---

## 9. SAFETY / LIVE TRADING VERIFICATION
* **Hard-Locked Safety Boundary:** `LIVE_TRADING_ENABLED = False` hard-locked across all safety gates and broker adapters (`MetaTraderSafetyGate`, `DemoExecutionGate`, `RealMT5BrokerAdapter`, `RealMT4BrokerAdapter`). Real-money order send attempts trigger immediate `SecurityException` rejection.
* **Trading Core Freeze:** `TRADING_CORE_MUTATION = 0`. Decision Engine, Risk Engine, Signal Engine, Position Sizing, and Policy Gate source code remained 100% frozen.

---

## 10. AUTH / FRONTEND VERIFICATION
* **Server-Side Auth & RBAC:** Auth tokens are verified via PBKDF2-SHA256 password hashes and JWT/session tokens. Role-based access control enforces HTTP 401 for unauthenticated requests and HTTP 403 for unauthorized resource access.
* **Clean SPA Routing:** HTML5 history pathname routing (`/fa/dashboard`, `/en/admin`) enforced across 4 production locales (`fa`, `en`, `tr`, `ar`). Legacy hash fragments (`#/...`), placeholder `javascript:void(0)` handlers, and `mock_social_token` admin bypasses are completely eliminated.

---

## 11. STATIC FORENSIC SEARCH
* `LIVE_TRADING_ENABLED`: Hard-locked to `False` repository-wide.
* `generate_active_ohlcv_candles`: Strictly isolated to test fixtures (`YARTRADER_ENV != "production"`).
* `10000.0`: Silent fallback equity in `ResearchWorker` removed; fail-closed rejection enforced.

---

## 12. TEST RESULTS
```text
Passed: 30
Failed: 0
Skipped: 0
Errors: 0
Duration: 125.12s
```
* Executed targeted test suites:
  - `tests/YarTrader.Tests/Execution/test_demo_execution_gate.py` (12 passed)
  - `tests/YarTrader.Tests/Services/test_web_dashboard.py` (18 passed)

---

## 13. BUILD RESULTS
* **React/Vite Production Build:** Compiled cleanly (`npm run build` -> `trader-terminal/dist/index.html` and assets).

---

## 14. REMAINING RISKS
1. **Linux Container IPC Isolation:** In Linux sandbox container environments, MetaTrader 5 terminal IPC is offline. Actionable decisions reaching `DemoExecutionGate` fail closed (`ValidationException: MT5 Terminal is disconnected`).
2. **Windows Service Host Verification:** Final live broker order fill verification requires executing `app/workers/service.py` on a native Windows Server host connected to an active MT5 Demo account.

---

## 15. FILES MODIFIED BY REPAIR
```text
M  app/workers/research_worker.py
M  docs/YARTRADER_WINDOWS_PRODUCTION_RUNTIME_FORENSIC_REPORT.md
M  src/Application/Services/web_dashboard.py
M  tests/YarTrader.Tests/Execution/test_demo_execution_gate.py
M  tests/YarTrader.Tests/Services/test_web_dashboard.py
```

---

## 16. FINAL VERDICT

```text
FINAL VERDICT: YELLOW — FUNCTIONAL BUT REQUIRES HUMAN REVIEW
```
*(The platform is technical-ready and fail-closed safe. Live MT5 broker order fill requires native Windows Server host execution with an active MT5 Demo terminal.)*
