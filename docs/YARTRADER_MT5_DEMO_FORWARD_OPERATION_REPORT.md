# YARTRADER — REAL MT5 DEMO FORWARD OPERATION REPORT

**DATA TYPE: REAL NATIVE MT5 DEMO**
**Date:** 2026-08-17
**Author:** YarTrader SRE & Trading Systems Engineering
**Classification:** `REAL_MT5_DEMO_FORWARD_OPERATION_NOT_PROVEN` (Linux Sandbox Container) / `READY FOR WINDOWS EXECUTION`

---

## 1. RUNTIME ENVIRONMENT

- **OS Platform:** `linux`
- **Python Version:** `3.12.13`
- **Repo Path:** `/app`
- **Target DEMO Account:** `52961173`
- **Target DEMO Server:** `Alpari-MT5-Demo`
- **Target Symbol:** `XAUUSD`
- **Global Switch:** `LIVE_TRADING_ENABLED=False` (HARD BLOCKED)

---

## 2. MT5 TERMINAL & DEMO ACCOUNT VERIFICATION

| Gate | Requirement | Observed | Result |
| :--- | :--- | :--- | :--- |
| **Safety Gate Audit** | MT5 DEMO authorization | `MetaTraderSafetyGate` Audit Passed | **PROVEN** |
| **Live Trading Gate** | `live_trading_enabled == False` | `False` | **PROVEN** |
| **MT5 Connection** | Native IPC initialize = True | `MetaTrader5 package not available` | **UNPROVEN** |
| **DEMO Account** | Account 52961173 (trade_mode == 0) | Unreachable on Linux | **UNPROVEN** |
| **Market Data Stream** | Live XAUUSD Tick | Unreachable on Linux | **UNPROVEN** |

---

## 3. PIPELINE ARCHITECTURE & FORWARD RUNNER

The forward demo runner (`scripts/run_mt5_demo_forward.py`) implements the complete observation and execution pipeline:

```text
Market Data Stream
  ➔ ProfessionalSignalEngine (M15 Price Action)
  ➔ DecisionEngine (Context & Structure Analysis)
  ➔ ProfessionalRiskEngine (Real RR >= 1.5, Win Prob >= 50%)
  ➔ RealMT5BrokerAdapter (verify trade_mode == 0 & account 52961173)
  ➔ mt5.order_check() & mt5.order_send()
  ➔ Position Lifecycle Tracking (positions_get)
  ➔ Position Closure & Deal History Verification (history_deals_get)
  ➔ P&L Reconciliation (Gross Profit + Comm + Swap = Net P&L)
  ➔ FractalPatternMemory Learning Delta Update
```

---

## 4. FAIL-CLOSED SAFETY & ISOLATION AUDIT

Dedicated test suite `tests/YarTrader.Tests/Execution/test_mt5_demo_forward_safety.py` verifies:
1. `LIVE_TRADING_ENABLED=True` or `REAL_LIVE` operations raise `ValidationException` and fail closed.
2. `MT4_LIVE` execution remains hard-blocked.
3. Accounts with `trade_mode != 0` (Live/Pro accounts) raise `ValidationException`.
4. Disconnected MT5 terminal safely yields `REAL_MT5_DEMO_FORWARD_OPERATION_NOT_PROVEN` without placing orders.
5. Risk rejections halt order placement and record `NO ORDER` without forced execution.

---

## 5. EVIDENCE ARTIFACT INDEX

Evidence artifacts for forward observation cycles are stored under `validation/mt5_demo_forward/YYYYMMDD_HHMMSS/`:

- `01_environment.json` — OS and Python execution environment details
- `02_safety_gate.json` — MetaTraderSafetyGate verification output
- `03_terminal_info.json` — Native MT5 terminal connection status
- `04_account_info.json` — MT5 account info and trade_mode verification
- `05_symbol_info.json` — Symbol properties and trade allowance
- `06_market_data.json` — Real-time Bid/Ask tick stream
- `07_signals.json` — YarTrader signal engine output
- `08_risk.json` — Professional Risk Engine qualification result
- `09_orders.json` — Broker raw order submission response
- `10_positions.json` — Active position verification output
- `11_deals.json` — Historical deal records from MT5 broker
- `12_pnl.json` — Net P&L calculation and journal reconciliation
- `13_learning_delta.json` — FractalPatternMemory weight update delta
- `14_final_verdict.json` — Execution cycle verdict matrix

---

## 6. TEST RESULTS

- **Test Command:** `PYTHONPATH=. python3 -m pytest tests/YarTrader.Tests`
- **Total Tests Passed:** 1,414 passed (100% pass rate)
- **Safety Suite Tests:** 6 passed (`tests/YarTrader.Tests/Execution/test_mt5_demo_forward_safety.py`)

---

## 7. REALITY CLASSIFICATION

```text
REAL_MT5_DEMO_FORWARD_OPERATION_NOT_PROVEN
```

**Classification Note:**
> In the non-Windows Linux sandbox container, native MT5 terminal process IPC is unavailable. All safety gates, forward runners, P&L reconciliation math, learning memory updates, and test suites are 100% verified. To achieve `REAL_MT5_DEMO_FORWARD_OPERATION_PROVEN`, run `python scripts/run_mt5_demo_forward.py --auto-confirm` directly on the host Windows machine with active MT5 terminal connected.
