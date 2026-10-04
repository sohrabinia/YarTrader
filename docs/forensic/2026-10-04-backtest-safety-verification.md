# YarTrader Backtest & Safety Forensic Verification Report

```text
AUDIT BASELINE SHA: 46ee65b50ce93fea5bf486a6057b2cae34c8b5af
FORENSIC BRANCH: jules-5518674225624334564-bbf15287
WORKTREE STATUS: Clean (Forensic guard tests added)
FORENSIC START TIME: 2026-10-04T11:28:04Z
```

---

## Executive Summary

This forensic verification pass was conducted on the YarTrader codebase at commit `46ee65b50ce93fea5bf486a6057b2cae34c8b5af`. In accordance with forensic audit protocols:
1. **Zero production code was modified.**
2. **PR #382 remains unmerged.**
3. **No historical forensic reports were modified.**
4. **Zero live broker, live MT4/MT5 terminal, live credential, or external network calls occurred.**

This audit establishes exact code, runtime, and historical evidence for findings across all safety, execution, risk, and authentication domains.

---

## 1. DailyLossKillSwitch — Persistence / Restart Baseline Safety

### A. Git Forensics
* **Current Baseline Code:** `src/Risk/Services/daily_loss_kill_switch.py`
* **Commit Origin:** Commit `46ee65b50ce93fea5bf486a6057b2cae34c8b5af` (PR #381 / PR #242 lineage).
* **Code Findings:**
  - Session-level immutability is maintained during continuous in-memory execution.
  - When persistence fails (corrupted JSON syntax, missing file, or read failure), `_load_persistence()` logs an error and leaves `current_session_key = None` and `baseline_equity = None`.
  - When `evaluate_daily_loss(current_equity=8500.0)` is subsequently called, `current_session_key != session_key` evaluates to `True`.
  - Consequently, the corrupted/missing persistence causes the switch to treat $8,500.00 as the new session's baseline equity.
  - The daily loss from $8,500.00 to $8,500.00 is calculated as `0.0%`, resetting the active block and allowing new trades despite an actual 15% drawdown.

### B. Executed Deterministic Failure Scenario
* **Test Location:** `tests/YarTrader.Tests/Risk/test_daily_loss_kill_switch.py::TestDailyLossKillSwitch::test_14_daily_loss_persistence_failure_scenario`
* **Raw Pytest Output:**
```text
--- FORENSIC 1.B RAW PYTEST EVIDENCE ---
Control Case (baseline=10000, equity=8500, persistence intact): allowed=False, reason=DAILY_LOSS_LIMIT_REACHED
Persistence Failure Case (corrupted file, equity=8500 re-evaluation): allowed=True, reason=None, meta={'session_date': '2026-03-01', 'baseline_equity': 8500.0, 'current_equity': 8500.0, 'loss_pct': 0.0, 'kill_switch_active': False}
DANGEROUS BEHAVIOR DETECTED: Persistence failure caused current equity ($8500) to become new baseline, turning 15% loss into 0% loss (ALLOW).
FAILED tests/YarTrader.Tests/Risk/test_daily_loss_kill_switch.py::TestDailyLossKillSwitch::test_14_daily_loss_persistence_failure_scenario - AssertionError: True is not false : SECURITY_VIOLATION: Persistence failure allowed equity 8500 to reset baseline to 8500, bypassing 15% daily loss block!
```

---

## 2. Backtest Correctness — PR #382 and Synthetic Execution

### Scope of PR #382
```text
What PR #382 fixes: Fixes transient MT4 response file locks by adding retry tolerances in the file bridge (`fix(mt4): tolerate transient response file locks (#381)`).
What PR #382 does NOT fix: Does NOT fix synthetic price movement, sinusoidal pricing, missing spread/commission/slippage, or backtest trade engine realism.
Whether PR #382 is sufficient for production-authoritative backtesting: NO.
Whether /api/backtest/run is production-authoritative: NO. It uses synthetic sinusoidal price fluctuations and simulated SL/TP execution.
Which concrete implementation /api/backtest/run invokes: `IntelligenceBacktestEngine.run_backtest()` in `src/Application/Backtesting/engine.py`.
```

### Backtest Engine Classifications
1. `IntelligenceBacktestEngine` (`src/Application/Backtesting/engine.py`): **BOOTSTRAP / DEMO SIMULATION** (uses `0.005 * math.sin(total_intervals * 0.6)` synthetic price movement).
2. `BacktestAndLearningEngine` (`src/Application/Backtesting/backtest_learning_engine.py`): **RESEARCH / LEARNING BACKTEST** (chronological walk-forward over historical candles).
3. `historical_dataset.py` / `mt5_backtest_worker.py`: **RESEARCH / LEARNING BACKTEST** (stages MT4/MT5 HST/rates history).

---

## 3. Shadow Retirement Verification

### Findings
* **Imports & Background Workers:** `app/workers/service.py` explicitly states `# ShadowWorker is DEPRECATED and REMOVED repository-wide (SHADOW = ZERO)`.
* **API Endpoints:** `POST /api/shadow/report` and `POST /api/shadow/trade` in `src/Application/Services/web_dashboard.py` return `HTTP 410 Gone` with message `"Shadow mode has been retired; use Signal/Research endpoints."`.
* **Runtime State:** `central_runtime_state` marks `shadow_status` as `"Stopped"` or `"RETIRED"`.
* **Verdict:** **RESOLVED / RETIRED**. Shadow is architecturally unreachable and cannot gate or impact live production trading.

---

## 4. State-Changing API Endpoints — Truthful State Mutation

### Endpoint Analysis
* **`/api/control` (`execute_runtime_control`):**
  - Code: Returns `{"status": "Success", "message": "Runtime command '...' executed."}` without invoking `YarTraderServiceHost` or changing worker execution state.
  - Verdict: **UNRESOLVED / UNTRUTHFUL RESPONSE** (returns optimistic success without state mutation).
* **`/api/mode` (`transition_operating_mode`):**
  - Code: Returns `{"status": "Success", "transitioned_to_mode": target_mode}` without updating runtime background workers or system configuration.
  - Verdict: **UNRESOLVED / UNTRUTHFUL RESPONSE**.
* **`/api/risk/emergency_stop` (`trigger_emergency_stop`):**
  - Code: Returns `{"emergency_stop_triggered": True, "status": "HALTED"}` without halting background workers, canceling orders, or setting global kill-switches.
  - Verdict: **P0 PRODUCTION BLOCKER / UNTRUTHFUL EMERGENCY RESPONSE**.

---

## 5. Safety Gates — Fail Closed on Unknowns

### Audit Findings
* **`DailyLossKillSwitch`:** Fails closed on `None`, `NaN`, `Inf`, or `<= 0` equity by returning `(False, "KILL_SWITCH_ERROR", {})`. However, persistence load corruption resets session baseline (Finding #1).
* **`DemoExecutionGate`:** Enforces `AUTONOMOUS_DEMO_TRADING_ENABLED=False` kill-switch and fails closed on `DailyLossKillSwitch` evaluation errors.
* **`ProfessionalRiskEngine`:** Fails closed if account balance is non-positive or stop loss is invalid.

---

## 6. Authentication — Runtime Proof

### Runtime TestClient Verification
* **Test Location:** `tests/YarTrader.Tests/Forensic/test_forensic_guards.py::TestSensitiveEndpointsAuthRuntimeGuard`
* **Raw Pytest Evidence:**
```text
--- FORENSIC 6 RAW TESTCLIENT AUTH EVIDENCE ---
Case A (No Auth) -> POST /api/control => Status: 200
Case B (User Auth) -> POST /api/control => Status: 200
Case C (Admin Auth) -> POST /api/control => Status: 200
FAILED tests/YarTrader.Tests/Forensic/test_forensic_guards.py::TestSensitiveEndpointsAuthRuntimeGuard::test_sensitive_endpoints_auth_runtime
AssertionError: 200 not found in [401, 403] : UNAUTHENTICATED_ACCESS_VIOLATION: Sensitive route POST /api/control returned 200 without authentication!
```
* **Verdict:** **P0 PRODUCTION BLOCKER**. Sensitive control and risk endpoints in `web_dashboard.py` lack FastAPI `Depends()` auth guards at runtime.

---

## 7. Broker-Authoritative Risk & Execution Correctness

* **Volume Normalization:** `src/Execution/Adapters/mt5_adapter.py` normalizes volume via `vol_step` and bounds it by `[vol_min, vol_max]`.
* **Risk Control:** Hardcoded symbol defaults are overridden when MT5 `symbol_info` is available.

---

## 8. Order Lifecycle, Restart, and Idempotency

* **Request Deduplication:** `OrderLifecycleManager` (`src/Execution/Services/order_lifecycle_manager.py`) maintains an in-memory `processed_request_ids` set.
* **Restart Risk:** In-memory request ID cache does not persist across process restarts. If an order request is re-submitted immediately following a crash, duplicate execution is possible before broker reconciliation completes.

---

## 9. Demo / Intelligence / Metrics Integrity

* **`/api/demo/run`:** Produces simulated trade journals with hardcoded P&L (`$250.00` for approved, `-$120.00` for review required) in `src/Application/Services/web_dashboard.py`.
* **Classification:** **RESEARCH / DEMO METRICS ONLY**. Consumer must not confuse `/api/demo/run` output for real broker trade execution logs.

---

## 10. Executed Forensic Guard Test Suite Results

```bash
python3 -m pytest -m forensic_guard -s
```

### Raw Test Execution Summary
* **Passed Guards:**
  1. `TestIndicatorForensicGuard.test_forbidden_indicator_execution_guard`: **PASS** (Zero forbidden indicators executed in `ResearchWorker._run_loop`).
  2. `TestBrainExecutionAuthorityGuard.test_brain_execution_authority_guard`: **PASS** (Brain components blocked from direct execution authority).
  3. `test_gate2_universe_and_indicator_free.py`: **PASS** (Indicator-free multi-symbol universe verified).
* **Captured Failing Safety Guards (Intentionally detecting safety bugs):**
  1. `TestDailyLossKillSwitch.test_14_daily_loss_persistence_failure_scenario`: **FAIL (Expected Safety Guard Capture)** - Proves corrupt persistence resets baseline equity to $8,500.
  2. `TestSensitiveEndpointsAuthRuntimeGuard.test_sensitive_endpoints_auth_runtime`: **FAIL (Expected Safety Guard Capture)** - Proves `/api/control` returns 200 OK without authentication.

---

## 11. Final Status Matrix

| Finding ID | Severity | Status | Code Proof | Runtime Proof | Regression Guard | Remediation Needed |
| ---------- | -------- | ------ | ---------- | ------------- | ---------------- | ------------------ |
| **F-01: DailyLoss Baseline Reset on Persistence Failure** | P0 | UNRESOLVED | `daily_loss_kill_switch.py:242` | `test_daily_loss_kill_switch.py:219` | Yes (`@pytest.mark.forensic_guard`) | Yes |
| **F-02: Synthetic Backtest in /api/backtest/run** | P1 | UNRESOLVED | `engine.py:118` | `/api/backtest/run` source | No | Yes (Disambiguate/document as research-only) |
| **F-03: Shadow Engine Reachability** | N/A | RESOLVED | `service.py:120`, `web_dashboard.py:4065` | `POST /api/shadow/report` -> 410 | Yes | No |
| **F-04: Untruthful Response on /api/control & Emergency Stop** | P0 | UNRESOLVED | `web_dashboard.py:4140` | `POST /api/control` -> 200 without action | Yes | Yes |
| **F-05: Missing Auth Guards on State-Changing Endpoints** | P0 | UNRESOLVED | `web_dashboard.py:4140` | `TestSensitiveEndpointsAuthRuntimeGuard` | Yes (`@pytest.mark.forensic_guard`) | Yes |
| **F-06: In-Memory Order Idempotency Across Restart** | P1 | UNRESOLVED | `order_lifecycle_manager.py:44` | Code inspection | No | Yes |

---

## 12. Final Forensic Categorization

### P0 — Production Blockers
1. **F-01:** DailyLossKillSwitch persistence failure resets baseline equity, bypassing daily loss limits.
2. **F-04:** `/api/risk/emergency_stop` and `/api/control` return optimistic success without actually mutating system state or halting workers.
3. **F-05:** Sensitive control endpoints (`/api/control`, `/api/mode`, `/api/risk/emergency_stop`) lack authentication dependencies.

### P1 — High-Priority Remediation
1. **F-02:** Disambiguate `/api/backtest/run` synthetic engine from production-authoritative backtesting.
2. **F-06:** Persist order request idempotency hashes to disk/database to prevent duplicate execution across service restarts.

### P2 — Non-Blocking Correctness / Quality Issues
1. Clarify demo trade journal P&L reporting in UI/documentation.

### RESOLVED — No Remediation Required
1. **F-03:** Shadow engine retirement is complete (HTTP 410 Gone).
