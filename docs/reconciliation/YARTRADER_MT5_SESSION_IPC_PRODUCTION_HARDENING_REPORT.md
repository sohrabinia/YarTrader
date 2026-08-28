# YARTRADER MT5 SESSION/IPC PRODUCTION HARDENING REPORT

**Document ID:** `docs/reconciliation/YARTRADER_MT5_SESSION_IPC_PRODUCTION_HARDENING_REPORT.md`
**Version:** 1.0.0
**Date:** 2026-02-28
**Classification:** GO_WITH_CONDITIONS
**Authors:** YarTrader Forensic & SRE Engineering Team

---

## Executive Summary

Following successful Vercel deprecation and single-host Windows production deployment, live telemetry analysis revealed an MT5 IPC initialization failure (`code -10003: IPC initialize failed, MetaTrader 5 x64 not found`).

This report provides the root cause forensic audit, architecture decision, implementation details, security analysis, test verification, and host runbook for establishing reliable IPC connectivity between the `YarTrader` Windows Service (running in Session 0 as `LocalSystem`) and the MetaTrader 5 terminal (running in Session 2 / Session 1 interactive user desktop).

---

## Root Cause Analysis & Session Boundary Mechanics

1. **MetaTrader5 IPC Architecture:** The official `MetaTrader5` Python package communicates with `terminal64.exe` via Windows Named Pipes, Shared Memory, and Window Message IPC.
2. **Session 0 Isolation:** Starting in Windows Server 2008 / Windows 7, Windows Services run strictly in **Session 0** without interactive desktop access. Standard desktop applications (like `terminal64.exe`) run in **Session 1** or **Session 2** under interactive user accounts.
3. **IPC Error -10003:** When Python `mt5.initialize()` is invoked from inside Session 0 (`LocalSystem` service), the operating system's Session 0 isolation boundary prevents standard cross-session GUI window messages and named pipe discovery, resulting in error code `-10003` even when `terminal64.exe` is running in Session 2.
4. **Interactive Verification:** Python `mt5.initialize()` succeeds 100% when invoked interactively from Administrator PowerShell in Session 2 because Python and MT5 share the same user desktop session context.

---

## Architecture Selection: Option A — MT5 User-Session Bridge

### Architecture Design:
To bridge the Session 0 vs Session 2 boundary safely without weakening security or running Windows Services under interactive desktop permissions, YarTrader implements **Option A: MT5 User-Session Local Bridge**.

```
[ Public Client / Cloudflare ]
            │
            ▼
[ YarTrader Windows Service (Session 0) ]
   └── FastAPI / Uvicorn (127.0.0.1:8000)
   └── MT5DataProvider (Fallback Client)
            │  (Local HTTP IPC: 127.0.0.1:8001)
            ▼
[ MT5 User-Session Bridge (Session 2 / Interactive User) ]
   └── Local HTTP Server (127.0.0.1:8001)
   └── Python mt5.initialize() (Direct IPC in Session 2)
            │
            ▼
[ MetaTrader 5 Terminal (terminal64.exe in Session 2) ]
```

### Security & Operational Rationale:
1. **Localhost Isolation:** The MT5 User-Session Bridge binds strictly to `127.0.0.1:8001`. It accepts zero external connections and is never exposed to the public internet.
2. **Zero Credential Disclosure:** The bridge exposes only sanitized operational state and rate candle data (`POST /fetch_rates`). No passwords, account numbers, equity, or broker details are exposed.
3. **Fail-Closed Safety:** Real live trading remains hard-disabled (`LIVE_TRADING_ENABLED = False`). The bridge provides read-only market data and health telemetry.
4. **Automated Recovery:** Registered as a Windows Scheduled Task (`YarTrader_MT5_UserSession_Bridge`) running at user logon with automatic 1-minute restart on failure.

---

## Implementation Summary

1. **Explicit Path Resolution (`src/Data/Providers/MT5/mt5.py`, `src/Execution/Adapters/mt5_adapter.py`, `src/Research/Brain/mt_data_acquisition.py`):**
   - Updated `mt5.initialize()` invocations to check `YARTRADER_MT5_TERMINAL_PATH` and `C:\Program Files\MetaTrader 5\terminal64.exe` explicitly via `mt5.initialize(path=...)` before falling back to default parameterless initialization.

2. **Local Bridge Server (`scripts/run_mt5_user_session_bridge.py`):**
   - Implemented lightweight local HTTP server executing in interactive user session context (Session 2).
   - Exposes `GET /health` and `POST /fetch_rates`.
   - Single-instance enforcement via local socket binding check on port 8001.

3. **Scheduled Task Installer (`scripts/install_mt5_user_bridge_task.ps1`):**
   - PowerShell script registering task `YarTrader_MT5_UserSession_Bridge` running `run_mt5_user_session_bridge.py` at user logon under `$env:USERNAME`.

4. **Service Fallback Mechanism (`src/Data/Providers/MT5/mt5.py`):**
   - `MT5DataProvider.get_connection_health()` queries local bridge (`http://127.0.0.1:8001/health`) seamlessly if direct Session 0 initialize returns `None` or error `-10003`.

---

## Windows Production Host Runbook & Verification

### Step-by-Step PowerShell Execution on Production Host:

1. **Verify MT5 Terminal Process in Session 2:**
```powershell
Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,SessionId,Path
```

2. **Register & Trigger User-Session Bridge Task:**
```powershell
.\scripts\install_mt5_user_bridge_task.ps1
Start-ScheduledTask -TaskName "YarTrader_MT5_UserSession_Bridge"
```

3. **Verify Local Bridge Health (127.0.0.1:8001):**
```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

4. **Restart YarTrader Service (Session 0):**
```powershell
Restart-Service YarTrader
```

5. **Verify Public Endpoint Security (Zero Credential Leakage):**
```powershell
$r = (Invoke-WebRequest https://yartrader.com/health -UseBasicParsing).Content
Write-Host "Account Leak Check (52961173):" ($r -like "*52961173*")
Write-Host "Account Leak Check (143056202):" ($r -like "*143056202*")
Write-Host "Broker Leak Check (Alpari):" ($r -like "*Alpari*")
```
*Expected: All checks return False.*

6. **Verify Public Live Research Degraded/Active Probe:**
```powershell
(Invoke-WebRequest https://yartrader.com/v1/dashboard/live-research -UseBasicParsing).Content
```

---

## Test Verification Matrix

| Test Module | Coverage Area | Status |
| :--- | :--- | :--- |
| `tests/runtime/test_health_endpoint.py` | Health API schema & SRE liveness | **PASS** (8/8) |
| `tests/YarTrader.Tests/Providers/test_metatrader_safety_hardening.py` | Safety gate, account redaction, bridge fallback | **PASS** (9/9) |
| `tests/runtime/test_sre_operational.py` | DevOps metrics & unidirectionality | **PASS** (7/7) |
| `tests/YarTrader.Tests/Services/test_web_dashboard.py` | SPA routing & degraded live-research fallback | **PASS** (14/14) |
| `trader-terminal` Vite Build | React/Tailwind frontend production build | **PASS** (1.80s) |

---

## Final Release Classification

### Classification: `GO_WITH_CONDITIONS`

#### Operational Conditions:
1. **Host Setup:** Execute `scripts/install_mt5_user_bridge_task.ps1` and launch `terminal64.exe` in the interactive desktop user session (Session 2).
2. **Service Restart:** Restart `YarTrader` Windows Service (`Restart-Service YarTrader`) to bind Session 0 service to the local bridge on `127.0.0.1:8001`.
3. **Safety Locks:** `LIVE_TRADING_ENABLED = False` and `REAL_ORDERS = 0` remain strictly enforced.
