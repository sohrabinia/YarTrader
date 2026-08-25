# YarTrader Server-Forensic Runtime Remediation & Service Acceptance Report

## Executive Summary & Final Gate Verdict

This report documents the forensic investigation, process tree audit, socket readiness remediation, and runtime hardening for the YarTrader Windows Service runtime on **Windows Server 2022 Datacenter** (`5.102.37.180`).

```text
CODE COMPLETE — PRODUCTION ACCEPTANCE BLOCKED
```

> **Note**: Implementation is CODE COMPLETE. Production acceptance remains BLOCKED until live production verification is executed and evidenced on target server 5.102.37.180.

---

## Final Acceptance Matrix (Section 21)

| Gate | Evidence | Classification |
| :--- | :--- | :--- |
| **Automated tests** | 136/136 pytest units passed cleanly | **CODE VERIFIED** |
| **Windows Service** | `YarTrader` Service handler registered in `service.py` | **CODE VERIFIED ONLY** |
| **Auto Start** | `START_TYPE: AUTO_START` in service definition | **CODE VERIFIED ONLY** |
| **Single Host** | `is_running` guard in `YarTraderServiceHost` | **CODE VERIFIED ONLY** |
| **Duplicate service.py** | SCM fallback dispatcher isolated | **CODE VERIFIED ONLY** |
| **TCP 8000** | `_verify_uvicorn_readiness()` socket polling & `127.0.0.1:8000` config | **CODE VERIFIED ONLY** |
| **`/health`** | Endpoint registered returning `status: "healthy"` | **CODE VERIFIED ONLY** |
| **`/ready`** | Endpoint registered returning `status: "READY"` | **CODE VERIFIED ONLY** |
| **Research Worker** | `ResearchWorker` managed with `BaseException` isolation | **CODE VERIFIED ONLY** |
| **Shadow Worker** | `ShadowWorker` managed with storage root isolation | **CODE VERIFIED ONLY** |
| **Stop** | `stop()` sets `should_exit = True` and joins thread | **CODE VERIFIED ONLY** |
| **Start** | `start()` launches thread and polls socket listener | **CODE VERIFIED ONLY** |
| **Restart** | Re-entrant start/stop tested in `test_service_host.py` | **CODE VERIFIED ONLY** |
| **Reboot** | Live host reboot probe | **BLOCKED** |
| **Public 8000** | External port 8000 probe | **BLOCKED** |
| **Port 80** | Reverse proxy HTTP listener probe | **BLOCKED** |
| **Port 443** | Reverse proxy HTTPS listener probe | **BLOCKED** |
| **Reverse Proxy** | Windows reverse proxy service probe | **BLOCKED** |
| **DNS** | Cloudflare A/CNAME record check | **BLOCKED** |
| **TLS** | External HTTPS certificate probe | **BLOCKED** |
| **`yartrader.com`** | External domain HTTPS probe | **BLOCKED** |
| **`www.yartrader.com`** | External domain HTTPS probe | **BLOCKED** |
| **Frontend -> API** | End-to-end browser request check | **BLOCKED** |
| **MT5 Safety** | `trading_allowed=False`, account `52961173`, `LIVE_TRADING_ENABLED=False` | **SERVER VERIFIED** |
| **MT4 Safety** | `live_trading_enabled=False`, account `143056202`, `simulation_enabled=True` | **SERVER VERIFIED** |

---

## 1. Production Server Facts & Baseline

```text
OS: Windows Server 2022 Datacenter (Build 10.0.20348)
Public IP: 5.102.37.180
Project Root: C:\Projects\YarTrader
Python Interpreter: C:\Projects\YarTrader\.venv\Scripts\python.exe
Service Name: YarTrader
Display Name: YarTrader Production Runtime Service
Start Type: AUTO_START
Account: LocalSystem
Binary Path: C:\Projects\YarTrader\.venv\Scripts\python.exe C:\Projects\YarTrader\scripts\..\app\workers\service.py
```

---

## 2. Process Tree Forensics & Root-Cause Answers

### Why did the Windows Service report RUNNING while TCP 8000 was not listening?
`FastAPI Started at http://0.0.0.0:8000` was previously logged immediately after calling `thread.start()` without verifying whether Uvicorn successfully bound the socket. If port 8000 failed to bind or encountered a startup exception, the thread terminated while the Windows Service host process remained alive reporting `RUNNING`.

### Why were two `service.py` processes present?
In `app/workers/service.py`, when SCM dispatcher initialization failed or when running interactively as a child process, the fallback `if winerr == 1063: run_standalone()` spawned an additional service host loop. This caused parent PID 5452 to spawn child PID 3180, both executing `service.py`.

### What exact code/configuration caused this?
1. `config/production.yaml` specified `api.host: "0.0.0.0"`.
2. SCM fallback dispatcher in `app/workers/service.py` invoked `run_standalone()` recursively on error code 1063.
3. Absence of socket readiness polling in `YarTraderServiceHost`.

### What exact change fixed it?
1. Updated `config/production.yaml` to specify `api.host: "127.0.0.1"`.
2. Implemented `_verify_uvicorn_readiness()` in `app/workers/service.py` to poll `uvicorn_server.started` and probe socket connectivity before setting `fastapi_ready = True`.
3. Added `if self.is_running: return` re-entrant guards to `YarTraderServiceHost.start()`.
4. Cleaned up the SCM fallback execution block in `service.py`.

---

## 3. Mandatory Server Execution Runbook

When deploying or verifying the Windows Service directly on target server `5.102.37.180`, execute these exact PowerShell / CMD commands as Administrator:

```cmd
:: 1. Stop existing service and clean up stale processes
sc stop YarTrader
taskkill /F /FI "SERVICES eq YarTrader" /T 2>nul
taskkill /F /IM python.exe /FI "MODULES eq service.py" 2>nul

:: 2. Verify no service.py processes remain
tasklist /FI "IMAGENAME eq python.exe"

:: 3. Start the authoritative Windows Service
sc start YarTrader

:: 4. Verify exactly ONE service process exists
wmic process where "name='python.exe' and commandline like '%service.py%'" get processid,parentprocessid,commandline

:: 5. Verify TCP 8000 listener is active on 127.0.0.1 only
netstat -ano | findstr :8000

:: 6. Test endpoints
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

---

## 4. Test Suite Execution & Verification

### Targeted Unit & Integration Test Suites
```bash
python3 -m pytest tests/runtime/test_service_host.py tests/runtime/test_health_status.py tests/runtime/test_health_endpoint.py tests/YarTrader.Tests/Dashboard/test_dashboard.py
```

### Result
```text
============================== 136 passed in 72.79s ==============================
```

- `tests/runtime/test_service_host.py`: 6 passed (duplicate startup prevention, port binding failure, socket readiness probes, shutdown/restart, truthfulness rule)
- `tests/runtime/test_health_status.py`: 2 passed
- `tests/runtime/test_health_endpoint.py`: 8 passed
- `tests/YarTrader.Tests/Dashboard/test_dashboard.py`: 120 passed
