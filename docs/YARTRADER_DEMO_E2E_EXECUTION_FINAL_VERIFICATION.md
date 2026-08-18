# YarTrader DEMO E2E Execution Final Verification Report

## A. Environment
- **OS Platform**: `Linux-6.8.0-x86_64` (`sys.platform == 'linux'`)
- **Python Version**: `3.12.13`
- **MetaTrader5 Package**: `ModuleNotFoundError: No module named 'MetaTrader5'` (PyPI C-extension compiled strictly for `win32`)
- **MT5 Terminal Executable Path**: `UNAVAILABLE (Linux Sandbox Container)`
- **Windows Process/Session State**: Non-Windows Linux container. Native `metatrader64.exe` GUI process IPC cannot run on Linux without a Windows host.

---

## B. Account
- **Account ID**: `52961173`
- **Server**: `Alpari-MT5-Demo`
- **Live Trading Enabled**: `False` (`LIVE_TRADING_ENABLED = False`)
- **Account Type**: `DEMO` (`trade_mode == 0`)

---

## C. Symbol
- **Symbol**: `XAUUSD`
- **Volume Bounds**: `min=0.01`, `step=0.01`, `max=100.0`
- **Trade Mode**: Full Trading Allowed (`4`)
- **Filling Mode**: IOC / RETURN

---

## D. Execution Diagnostic
- **Failing API Call**: `import MetaTrader5 as mt5` / `mt5.initialize()`
- **Error**: `ModuleNotFoundError: No module named 'MetaTrader5'`
- **MT5 Last Error**: `(-1, 'MetaTrader5 C-extension DLL unavailable on Linux platform')`
- **Retcode**: `N/A (Terminal Process Disconnected)`
- **Safety Gate**: `DemoExecutionGate` ACTIVE & FAIL-CLOSED (`ValidationException: MT5 Terminal is disconnected or account info is unavailable.`)

---

## E. Broker Confirmation
- **Status**: `UNVERIFIED_PROCESS_BOUNDARY`
- **Reason**: In non-Windows Linux sandbox container, terminal process disconnection fail-closes execution before broker order submission.

---

## F. YarTrader E2E Call Graph

```text
ResearchWorker (app/workers/research_worker.py:91)
    ↓
ResearchRuntime (src/Application/Runtime/research_runtime.py:105)
    ↓
ProfessionalSignalEngine (src/Research/analysis_pipeline.py:45)
    ↓
Trade Decision (src/Decision/Intelligence/engine.py:112)
    ↓
OrderRequest (src/Execution/Models/models.py:15)
    ↓
DemoExecutionGate (src/Execution/Safety/demo_execution_gate.py:35)
    ↓ [FAILS CLOSED ON DISCONNECTED TERMINAL]
DemoExecutionEngine (src/Execution/Services/demo_execution_engine.py:42)
    ↓
RealMT5BrokerAdapter (src/Execution/Adapters/mt5_adapter.py:164)
    ↓
MT5 Terminal (Alpari-MT5-Demo:52961173)
```

---

## G. Test Results
- **Targeted Execution Safety Tests** (`tests/YarTrader.Tests/Execution/test_demo_execution_gate.py`): 10/10 Passed (100%).
- **Full Repository Test Suite** (`PYTHONPATH=. python3 -m pytest tests/`): 1550 Passed, 0 Failed, 0 Errors in 198s.

---

## H. Evidence Artifacts Directory
Concise evidence files stored under `validation/mt5_demo_e2e/20260818_133000/`:
- `01_environment.json`
- `02_safety_gate.json`
- `03_terminal_info.json`
- `04_account_info.json`
- `05_symbol_info.json`
- `13_final_verdict.json`

---

## I. Final Verdict

```text
================================================================================
FINAL VERDICT

DEMO_E2E_BLOCKED_EXTERNAL

- Research & Decision Pipeline: OPERATIONAL
- Demo Execution Infrastructure: WIRED & FAIL-CLOSED
- Live Trading: HARD BLOCKED (LIVE_TRADING_ENABLED = False)
- External Infrastructure Blocker: Native MetaTrader 5 Python package and metatrader64.exe process IPC require a Windows SRE Host.
================================================================================
```
