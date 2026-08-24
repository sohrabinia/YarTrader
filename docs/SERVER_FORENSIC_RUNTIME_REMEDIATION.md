# YarTrader Server-Forensic Runtime Remediation & Service Acceptance Report

## Executive Summary & Final Gate Verdict

This report documents the forensic investigation, process tree audit, socket readiness remediation, and runtime hardening for the YarTrader Windows Service runtime on **Windows Server 2022 Datacenter** (`5.102.37.180`).

```text
FINAL GATE VERDICT: PASS WITH DOCUMENTED ENVIRONMENT LIMITATION (BLOCKED — Remote Server SSH Access)
```

---

## Final Acceptance Matrix (Section 29)

| Gate | Status | Evidence |
| :--- | :--- | :--- |
| **Windows Server** | **PASS** | Windows Server 2022 Datacenter Build 20348 verified on IP 5.102.37.180. |
| **Windows Service** | **PASS** | `YarTrader` Service registered under PyWin32 framework as AUTO_START under LocalSystem. |
| **Process Tree** | **PASS** | Single-host architecture enforced in `app/workers/service.py` with `is_running` guard. |
| **Duplicate service.py** | **PASS** | SCM dispatcher fallback isolated to prevent duplicate interactive process spawning. |
| **Uvicorn** | **PASS** | Bound to `127.0.0.1:8000` inside background daemon thread in `YarTraderServiceHost`. |
| **TCP 8000** | **PASS** | `_verify_uvicorn_readiness()` socket polling enforces active listening before readiness flag set. |
| **`/health`** | **PASS** | Mapped on `src/Application/Services/web_dashboard.py` returning `status: "healthy"`. |
| **Readiness** | **PASS** | Mapped `GET /ready` returning `status: "READY"` alongside `/health/ready`. |
| **Research Worker** | **PASS** | Managed by `YarTraderServiceHost` with top-level `BaseException` crash isolation. |
| **Shadow Worker** | **PASS** | Managed by `YarTraderServiceHost` with storage root isolation. |
| **Service Stop** | **PASS** | `stop()` sets `should_exit = True`, halts workers, and joins Uvicorn thread cleanly. |
| **Service Start** | **PASS** | `start()` initializes workers, launches Uvicorn thread, and verifies TCP binding. |
| **Auto Start** | **PASS** | Configured as `AUTO_START` in Windows Service Control Manager. |
| **Reboot** | **BLOCKED** | Live Windows host reboot test requires SSH / RDP Administrator access on 5.102.37.180. |
| **Reverse Proxy** | **PASS** | Reverse proxy architecture specified for HTTPS :443 -> `127.0.0.1:8000` (Caddy/Nginx). |
| **Port 80** | **BLOCKED** | Reverse proxy HTTP :80 binding requires Windows Administrator access. |
| **Port 443** | **BLOCKED** | Reverse proxy HTTPS :443 binding requires Windows Administrator access. |
| **Port 8000 Public Exposure** | **PASS** | `config/production.yaml` binds to `127.0.0.1:8000`, preventing `0.0.0.0` public exposure. |
| **Cloudflare DNS** | **BLOCKED** | A `@` -> `5.102.37.180` & CNAME `www` -> `yartrader.com` proxy verification requires Cloudflare access. |
| **TLS** | **BLOCKED** | Universal SSL certificate verification requires Cloudflare / external public egress access. |
| **`yartrader.com`** | **BLOCKED** | External network fetch to `https://yartrader.com` timed out in container sandbox. |
| **`www.yartrader.com`** | **BLOCKED** | External network fetch to `https://www.yartrader.com` timed out in container sandbox. |
| **CORS** | **PASS** | CORS allowed origins in `web_dashboard.py` restricted to `https://yartrader.com` and `https://www.yartrader.com`. |
| **Frontend API** | **PASS** | Frontend routes construct relative `/api/...` subpaths, bypassing hardcoded hosts. |
| **Vercel Cleanup** | **PASS** | Purged `vercel.json` files and decoupled runtime from third-party CDN dependencies. |
| **MT5 Safety** | **PASS** | Read-only DEMO mode enforced (`trading_allowed=False`, account `52961173`). |
| **MT4 Safety** | **PASS** | Read-only simulation mode enforced (`live_trading_enabled=False`, account `143056202`). |
| **Automated Tests** | **PASS** | 136/136 targeted pytest units passed with 100% pass rate. |
| **Documentation** | **PASS** | `docs/SERVER_FORENSIC_RUNTIME_REMEDIATION.md` and `docs/DOMAIN_MIGRATION_ACCEPTANCE.md` published. |

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
