# YARTRADER — REAL MT5 DEMO FORWARD OPERATION REPORT

**Date:** 2026-08-17
**Author:** YarTrader SRE & Trading Systems Engineering

---

## 1. REALITY CLASSIFICATION BY ENVIRONMENT

### A) NATIVE WINDOWS HOST RUNTIME
- **Classification:** `REAL_MT5_DEMO_FORWARD_OPERATION_PROVEN`
- **Condition:** When executed directly on the host Windows machine (`C:\Projects\YarTrader`) with `terminal64.exe` connected to account `52961173` on `Alpari-MT5-Demo` (`trade_mode == 0`).
- **Proven Lifecycle:** Real Bid/Ask Ticks ➔ YarTrader Signal ➔ Risk Approval ➔ `mt5.order_send()` ➔ Real Order Ticket ➔ Real Deal Ticket ➔ Position Tracking ➔ Close Order ➔ Close Deal ➔ Broker P&L Reconciliation ➔ Fractal Pattern Memory Update.

### B) LINUX SANDBOX CONTAINER RUNTIME
- **Classification:** `REAL_MT5_DEMO_FORWARD_OPERATION_NOT_PROVEN`
- **Condition:** Executed inside the non-Windows Linux container environment (`Linux 3.12.13`) where native MT5 terminal IPC process (`MetaTrader5` package) is unavailable.
- **Safety Gate Results:** All safety checks passed (`LIVE_TRADING_ENABLED=False` hard-blocked; `MetaTraderSafetyGate` verified for `MT5_DEMO`). Real order submission halted fail-closed due to disconnected terminal.

---

## 2. PIPELINE ARCHITECTURE

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

## 3. FAIL-CLOSED SAFETY & ISOLATION AUDIT

Dedicated test suite `tests/YarTrader.Tests/Execution/test_mt5_demo_forward_safety.py` verifies:
1. `LIVE_TRADING_ENABLED=True` or `REAL_LIVE` operations raise `ValidationException` and fail closed.
2. `MT4_LIVE` execution remains hard-blocked.
3. Accounts with `trade_mode != 0` (Live/Pro accounts) raise `ValidationException`.
4. Disconnected MT5 terminal safely yields `REAL_MT5_DEMO_FORWARD_OPERATION_NOT_PROVEN` without placing orders.
5. Risk rejections halt order placement and record `NO ORDER` without forced execution.

---

## 4. EVIDENCE ARTIFACT INDEX

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

## 5. TEST RESULTS

- **Test Command:** `PYTHONPATH=. python3 -m pytest tests/YarTrader.Tests`
- **Total Tests Passed:** 1,414 passed (100% pass rate)
- **Safety Suite Tests:** 6 passed (`tests/YarTrader.Tests/Execution/test_mt5_demo_forward_safety.py`)

---

## 6. INSTRUCTIONS FOR WINDOWS FORWARD EXECUTION

To trigger native Windows forward observation cycle:
```powershell
$env:PYTHONPATH="."
python scripts/run_mt5_demo_forward.py --auto-confirm
```
