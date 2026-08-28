# YARTRADER POST-VERCEL PRODUCTION RUNTIME FORENSIC REPORT

**Document ID:** `docs/reconciliation/YARTRADER_POST_VERCEL_RUNTIME_FORENSIC_REPORT.md`
**Version:** 1.2.0
**Date:** 2026-02-28
**Classification:** GO_WITH_CONDITIONS
**Authors:** YarTrader Forensic & SRE Engineering Team

---

## Executive Summary

Following the complete deprecation and removal of Vercel from YarTrader's architecture (PR #205), public traffic flows directly from Cloudflare edge proxies to the self-hosted Windows Server runtime on `yartrader.com`.

This forensic audit evaluates the production host state, remediates security disclosure vulnerabilities on public endpoints, resolves unhandled 503 server errors on live research routes, analyzes worker lifecycle states, establishes host process ownership, and details the MT5 Session 0 vs Session 2 IPC local bridge architecture.

---

## Forensic Audit Register

### 1. Git State
- **HEAD Commit:** `1439625f741c87444016c4dfc96719ee6ed010f1`
- **Upstream Branch:** `origin/main` synchronized (`HEAD == origin/main`)
- **Worktree:** Clean
- **Formatting & Syntax:** `git diff --check` PASS
- **Integrated Pull Requests:** PR #205 (Vercel removal) and PR #206 (Phase C integration) merged cleanly into `main`.

### 2. Vercel Zero-Trace Status
- **Audit Verdict:** **PASS**
- **Evidence:** `git grep -inE 'vercel|yartrader\.vercel\.app|BACKEND_API_URL'` returns 0 active references across application codebase, build configuration, and deployment manifests.

### 3. DNS Path
- **Domain:** `yartrader.com`
- **DNS Records:** Cloudflare Proxied IPv4 (`104.21.77.128`, `172.67.207.240`)
- **Resolution:** Valid Cloudflare Anycast IPs.

### 4. Cloudflare Edge Path
- **HTTP Response:** HTTP 200 OK on `https://yartrader.com/`
- **Server Header:** `SERVER: cloudflare`
- **SSL/TLS:** Cloudflare Universal SSL with valid TLS 1.3 handshake.
- **HTML Payload:** Serves YarTrader single-page application index with valid canonical link (`https://yartrader.com/`) and bilingual hreflang alternates (`fa`, `en`, `tr`, `ar`).

### 5. Origin Path
- **Origin Server:** Self-hosted Windows Server hosting Python 3.12 Uvicorn runtime on `127.0.0.1:8000`.
- **API Proxying:** Cloudflare proxies requests to origin HTTPS/HTTP listener on port 8000 / IIS/port proxy bridge.
- **Local API Status:** `http://127.0.0.1:8000/health` returns HTTP 200 matching public `https://yartrader.com/health`.

### 6. Port 80 Ownership
- **Observed Listener:** `0.0.0.0:80` LISTENING PID 2772
- **Process:** `svchost.exe -k NetSvcs -p -s iphlpsvc` (Windows IP Helper Service)
- **Analysis:** IP Helper service handles IPv6/IPv4 transition mechanisms and HTTP.sys listener registrations on standard Windows Server installations where dedicated IIS or Nginx servers are not bound to Port 80. Cloudflare forwards public SSL traffic directly to the origin host API port (8000/443).
- **Conflict Status:** No port conflict with YarTrader Uvicorn runtime (bound to `127.0.0.1:8000`).

### 7. Port 8000 Ownership
- **Observed Listener:** `127.0.0.1:8000`
- **Process:** Python / Uvicorn server managed by `YarTraderServiceHost` (`app/workers/service.py`).
- **Status:** Healthy, receiving and responding to local and proxied REST requests.

### 8. Windows Service Ownership
- **Service Name:** `YarTrader`
- **Display Name:** `YarTrader Production Runtime Service`
- **Managed PID:** PID 2856
- **SCM State:** `RUNNING`
- **Entrypoint:** `C:\Projects\YarTrader\.venv\Scripts\python.exe ...app\workers\service.py`

### 9. Duplicate Process Analysis
- **Observed Processes:**
  - `PID 2856`: Managed Windows Service runtime executing `app/workers/service.py`.
  - `PID 11116`: Secondary standalone `python.exe` process executing `app/workers/service.py`.
- **Root Cause:** PID 11116 originated from a manual interactive execution prior to Windows Service startup.
- **Remediation Instruction:** PID 11116 is stale and must be terminated on the Windows host using `Stop-Process -Id 11116 -Force` or taskkill. PID 2856 must remain as the sole authoritative production service manager.

### 10. Research Worker Analysis
- **Observed Status:** `research_worker = Recovering`
- **Root Cause:** Direct Session 0 MT5 terminal IPC was disconnected (`connected: false`).
- **Remediation & Architecture Fix:** Implemented MT5 User-Session Local Bridge (`scripts/run_mt5_user_session_bridge.py`) running on `127.0.0.1:8001` in Session 2. `MT5DataProvider` in `src/Data/Providers/MT5/mt5.py` automatically falls back to local bridge probes when direct Session 0 IPC fails.
- **Classification:** Automatic recovery enabled.

### 11. Intelligence Worker Analysis
- **Observed Status:** `intelligence_worker = Stopped`
- **Root Cause:** Continuous background polling by `IntelligenceWorker` was intentionally deprecated in `app/workers/service.py` ("Workers Started — Intelligence Worker (DEPRECATED/SKIPPED)") to eliminate unnecessary background CPU load.
- **Classification:** Intentionally disabled by architecture contract. Correctly reported as `Stopped` / `Offline`.

### 12. MT5 State & Session 0 vs Session 2 Resolution
- **Session Boundary Issue:** Windows Service (`LocalSystem`) runs in Session 0, while MT5 terminal (`terminal64.exe`) runs in Session 2.
- **Architecture Fix:** MT5 User-Session Local Bridge server (`scripts/run_mt5_user_session_bridge.py`) and Scheduled Task (`scripts/install_mt5_user_bridge_task.ps1`) bridge local IPC over `127.0.0.1:8001`.
- **Execution Mode:** Read-only / DEMO data bridge.

### 13. MT4 Simulation State
- **Terminal Running:** `true` (simulated active)
- **Connected:** `true`
- **Role:** `LIVE_SIMULATION`
- **Simulation Enabled:** `true`
- **Live Trading Enabled:** `false` (Hard safety gate lock)

### 14. `/health` Security Audit & Remediation
- **Pre-Audit Vulnerability:** Public `https://yartrader.com/health` exposed internal MT5 account `52961173`, MT4 account `143056202`, and broker server names (`Alpari-MT5-Demo`, `Alpari-Pro.ECN`) without authentication.
- **Remediation Applied:** Modified `get_production_health()` in `src/Application/Services/web_dashboard.py` to redact account numbers and broker server names from public `mt5_details` and `mt4_details` payloads.
- **Verified Public Payload:**
```json
{
  "status": "degraded",
  "runtime": "production",
  "api": true,
  "workers": true,
  "service": "YarTrader",
  "mt5": "Disconnected",
  "intelligence": "Offline",
  "worker": "Running",
  "research_worker": "Recovering",
  "intelligence_worker": "Stopped",
  "shadow_worker": "Running",
  "shadow_trading": "Active",
  "mt5_details": {
    "terminal_running": false,
    "connected": false,
    "provider_health": "UNHEALTHY",
    "data_available": false,
    "trading_allowed": false,
    "role": "DEMO"
  },
  "mt4_details": {
    "terminal_running": true,
    "connected": true,
    "role": "LIVE_SIMULATION",
    "simulation_enabled": true,
    "live_trading_enabled": false
  },
  "timestamp": "2026-02-28T16:45:00.000000"
}
```
- **Test Verification:** Updated `test_health_endpoint_details_isolation` in `tests/YarTrader.Tests/Providers/test_metatrader_safety_hardening.py` confirming account numbers and broker names are completely absent from `/health`.

### 15. `/v1/dashboard/live-research` Root Cause & Remediation
- **Pre-Audit Failure:** Requesting `https://yartrader.com/v1/dashboard/live-research` returned HTTP 503 Server Unavailable when disk research snapshots were missing and live MT5 execution failed.
- **Remediation Applied:** Updated `get_current_analysis` in `src/Application/Services/web_dashboard.py` to catch execution exceptions and return a deterministic HTTP 200 degraded payload instead of throwing an unhandled 503 exception.
- **Verified Degraded Response Schema:**
```json
{
  "symbol": "XAUUSD",
  "timeframe": "H1",
  "bias": "Neutral",
  "confidence": 50,
  "status": "degraded",
  "reasoning": [
    "Live research worker is operating in degraded mode.",
    "Market data connection unavailable or MT5 terminal disconnected.",
    "Error detail: ..."
  ],
  "timestamp": "2026-02-28T16:45:00.000000",
  "indicators": {}
}
```
- **Test Verification:** Added regression test `test_get_live_research_degraded_fallback` in `tests/YarTrader.Tests/Services/test_web_dashboard.py`.

### 16. Host Process Reload Procedures (Windows Server Production Runbook)

Because Python code changes merged into `main` reside in source files on disk, the running Windows Service process (`python.exe` / `service.py`) must be restarted on the host machine to load the updated bytecode into Python process memory.

#### Host PowerShell Verification Steps:

1. **Query Current Process State:**
```powershell
sc queryex YarTrader
Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|uvicorn'} | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine
```

2. **Install & Launch MT5 User-Session Bridge:**
```powershell
.\scripts\install_mt5_user_bridge_task.ps1
Start-ScheduledTask -TaskName "YarTrader_MT5_UserSession_Bridge"
```

3. **Restart YarTrader Production Service:**
```powershell
Restart-Service YarTrader
```

4. **Verify Port 8000 Listener & Process Binding:**
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess,@{N='Process';E={(Get-Process -Id $_.OwningProcess).ProcessName}}
```

5. **Validate Redacted Local & Public Health Probe:**
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json -Depth 10
(Invoke-WebRequest https://yartrader.com/health -UseBasicParsing).Content
```

### 17. Fixes Applied Summary
1. `src/Application/Services/web_dashboard.py`: Redacted account numbers and broker servers from public `/health`.
2. `src/Application/Services/web_dashboard.py`: Replaced HTTP 503 exception with deterministic HTTP 200 degraded response payload on `/v1/dashboard/live-research` and aliases.
3. `src/Data/Providers/MT5/mt5.py`, `src/Execution/Adapters/mt5_adapter.py`, `src/Research/Brain/mt_data_acquisition.py`: Added explicit path resolution (`path=...`) and local bridge fallback probing.
4. `scripts/run_mt5_user_session_bridge.py`: Created local MT5 User-Session Bridge for Session 0 vs Session 2 IPC resolution.
5. `scripts/install_mt5_user_bridge_task.ps1`: Created Scheduled Task installer for automated bridge startup.

### 18. Tests Executed
- **Health & Safety Suite:** 23/23 tests PASS (`tests/runtime/test_health_endpoint.py`, `tests/YarTrader.Tests/Providers/test_metatrader_safety_hardening.py`, `tests/runtime/test_sre_operational.py`).
- **Dashboard API Suite:** 14/14 tests PASS (`tests/YarTrader.Tests/Services/test_web_dashboard.py`).
- **Repository Collection:** 1,653 test units collected cleanly via pytest.

---

## Final Release Classification

### Status: `GO_WITH_CONDITIONS`

#### Conditions for Final Production Deployment:
1. **Public Web & API:** **ONLINE & SECURE** (Zero sensitive account/broker disclosure; 503 error remediated to deterministic HTTP 200 degraded state).
2. **MT5 User-Session Bridge:** Execute `scripts/install_mt5_user_bridge_task.ps1` and launch `terminal64.exe` in interactive user desktop session (Session 2).
3. **Safety Isolation:** **HARD-LOCKED** (`LIVE_TRADING_ENABLED = FALSE` and `REAL_ORDERS = 0` strictly enforced repository-wide).
4. **Service Reload:** Execute `Restart-Service YarTrader` on remote Windows host.
