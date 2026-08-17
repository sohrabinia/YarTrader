# YARTRADER — MT5 NATIVE DEMO EXECUTION REALITY REPORT

**Date:** 2026-08-17
**Author:** YarTrader SRE & Trading Systems Engineering
**Classification:** `REAL MT5 DEMO EXECUTION NOT PROVEN` (Linux Sandbox Runtime) / `READY FOR WINDOWS EXECUTION`

---

## 1. EXECUTIVE SUMMARY

This document records the exact runtime execution audit performed for real native MetaTrader 5 (MT5) DEMO broker execution.

### Key Audit Conclusions:
1. **Safety Gate Hardening:** `MetaTraderSafetyGate` (`src/Execution/Safety/safety_gate.py`) and `RealMT5BrokerAdapter` (`src/Execution/Adapters/mt5_adapter.py`) explicitly authorize `MT5_DEMO` execution on target account `52961173` on `Alpari-MT5-Demo` when `trade_mode == 0` (ACCOUNT_TRADE_MODE_DEMO).
2. **Live Trading Isolation:** `LIVE_TRADING_ENABLED` remains `False` (hard-blocked) repository-wide. Any attempt to invoke `REAL_LIVE` execution raises an immediate `ValidationException`.
3. **Execution Reality in Current Environment:** Running `scripts/run_real_mt5_demo_e2e.py` in the current non-Windows Linux container environment confirms that the `MetaTrader5` Python package and native terminal IPC are unavailable on Linux OS.
4. **Data Provenance Classification:** Under strict evidence rules, because broker-side order/deal tickets cannot be generated in a non-Windows Linux environment without native MT5 terminal IPC, the final verdict for this sandbox run is classified as **`REAL MT5 DEMO EXECUTION NOT PROVEN`**.

---

## 2. ENVIRONMENT & SAFETY GATE AUDIT

### Environment Metadata:
- **OS Platform:** `linux`
- **Python Version:** `3.12.13`
- **Repo Root:** `/app`
- **Timestamp:** `2026-08-17T18:34:54Z`

### Safety Gate Verification Results:
| Gate | Expected | Observed | Status |
| :--- | :--- | :--- | :--- |
| **Safety Gate** | Terminal MT5, Operation DEMO | `MetaTraderSafetyGate` Audit Passed | **PROVEN** |
| **Live Trading Gate** | `live_trading_enabled == False` | `False` | **PROVEN** |
| **MT5 Connection** | Native IPC initialize = True | `MetaTrader5 package not available` | **UNPROVEN** |
| **DEMO Account** | Account 52961173 on Alpari-MT5-Demo | Account Unreachable | **UNPROVEN** |
| **Market Data Stream** | Live XAUUSD Bid/Ask Tick | Tick Stream Unreachable | **UNPROVEN** |

---

## 3. NATIVE WINDOWS EXECUTION INSTRUCTIONS

To obtain **`REAL MT5 DEMO EXECUTION VERIFIED`** status, run the following command directly on the host Windows machine where MetaTrader 5 is installed, logged into account `52961173` on `Alpari-MT5-Demo`, and `terminal64.exe` is running:

```powershell
# On Windows PowerShell
$env:PYTHONPATH="."
python scripts/run_real_mt5_demo_e2e.py --auto-confirm
```

### Mandatory Verification Steps Executed on Windows:
1. `mt5.initialize()` returns `True`.
2. `mt5.terminal_info().connected` returns `True`.
3. `mt5.account_info().trade_mode` returns `0` (DEMO).
4. `mt5.symbol_info_tick("XAUUSD")` returns clean non-zero Bid/Ask.
5. `mt5.order_check(trade_req)` returns `retcode == 0`.
6. `mt5.order_send(trade_req)` returns valid broker `order` and `deal` tickets.
7. `mt5.positions_get()` confirms active position ticket matching `order`.
8. Position closed via `OrderType="CLOSE"` and closing deal verified in `mt5.history_deals_get()`.
9. P&L reconciled: Gross Profit + Commission + Swap = Net P&L.
10. `FractalPatternMemory` state updated with post-trade outcome delta.

---

## 4. FINAL CLASSIFICATION VERDICT

```
REAL_MT5_DEMO_EXECUTION = FALSE
```

**Exact Reason:**
> Native MT5 terminal connection was unproven in the current Linux sandbox container because the native `MetaTrader5` C-extension package requires a Windows operating system with an active `terminal64.exe` process. All safety gates, trade mode validation logic, and unit test suites pass 100%. Native execution proof requires running `scripts/run_real_mt5_demo_e2e.py` on the host Windows machine.
