# YARTRADER — MT4 / MT5 EXECUTION BOUNDARY ARCHITECTURE AUDIT

## Executive Summary

This forensic architecture audit evaluates the repository and runtime execution boundaries for **MetaTrader 4 (MT4)** and **MetaTrader 5 (MT5)** in YarTrader V1.2. The audit confirms the system's strict environmental separation rules, safety gate boundaries, and order dispatch mechanisms.

---

## 1. Questions & Architecture Audit Findings

### A) Is MT4 currently the intended Live/Signal execution environment?
**YES.**
- In `src/Execution/Safety/safety_gate.py`, MT4 is configured strictly for Live/Signal execution pathways under account `143056202` on server `Alpari-Pro.ECN`.
- `MetaTraderSafetyGate` requires `terminal_type == "MT4"` for `operation_type == "LIVE"`.

### B) Is MT5 currently restricted to Backtest + Demo?
**YES.**
- `MetaTraderSafetyGate` restricts `terminal_type == "MT5"` strictly to `operation_type in ["DEMO", "RESEARCH", "DATA"]`.
- The authorized MT5 DEMO target account is `52961173` on server `Alpari-MT5-Demo`.

### C) Can MT5 accidentally enter LIVE execution?
**NO.**
- Passing `operation_type = "LIVE"` to MT5 triggers an immediate `ValidationException: SRE Safety Gate Violation` inside `MetaTraderSafetyGate.verify_operation()`.
- Furthermore, `LIVE_TRADING_ENABLED` defaults to `False` repository-wide.

### D) Can MT4 accidentally be used as Demo?
**NO.**
- `MetaTraderSafetyGate` rejects any MT4 request with `operation_type != "LIVE"`, enforcing strict separation between MT4 (Live/Signal) and MT5 (Backtest/Demo).

### E) Which configuration/environment variables control each mode?
- `LIVE_TRADING_ENABLED`: Global boolean flag controlling live trading enablement (default: `False`).
- `YARTRADER_ENV`: Environment identifier (`development`, `test`, `production`).
- `YARTRADER_MT5_LOGIN` / `MT5_TARGET_ACCOUNT`: `52961173`.
- `YARTRADER_MT5_SERVER` / `MT5_TARGET_SERVER`: `Alpari-MT5-Demo`.
- `YARTRADER_MT4_LOGIN`: `143056202`.
- `YARTRADER_MT4_SERVER`: `Alpari-Pro.ECN`.

### F) Which actual runtime process performs `order_send`?
- **MT5 Execution**: Performed by `RealMT5BrokerAdapter` (`src/Execution/Adapters/mt5_adapter.py`) via native Python package calls (`mt5.order_send()`).
- **MT4 Execution**: Handled via ECN broker API bridge / SCM service IPC (`app/workers/service.py`).

### G) Is the current MT5 demo adapter connected to a REAL native MetaTrader 5 terminal?
- **On Windows SRE Host**: **YES.** Connects to the native `MetaTrader 5` terminal process on `Alpari-MT5-Demo`.
- **On Non-Windows Sandbox / Linux**: Operates in simulated harness mode due to the absence of the Windows MT5 terminal process.

---

## 2. Execution Boundary Summary Matrix

| Dimension | MT5 Boundary | MT4 Boundary |
| :--- | :--- | :--- |
| **Intended Role** | Backtest + Demo Trading | Live Trading + Signal Execution |
| **Allowed Operations** | `DEMO`, `RESEARCH`, `DATA` | `LIVE` (with safety gate approval) |
| **Blocked Operations** | `LIVE` (**HARD BLOCKED**) | `DEMO`, `RESEARCH` |
| **Target Account** | `52961173` | `143056202` |
| **Target Server** | `Alpari-MT5-Demo` | `Alpari-Pro.ECN` |
| **Primary Adapter** | `RealMT5BrokerAdapter` | MT4 ECN Bridge / SCM Service |

---

## 3. Governance Conclusion

The codebase maintains strict, fail-closed segregation between MT4 and MT5 execution paths. MT5 live execution is impossible, while MT5 Demo trading uses native `MetaTrader5` API calls when executed on Windows host machines.
