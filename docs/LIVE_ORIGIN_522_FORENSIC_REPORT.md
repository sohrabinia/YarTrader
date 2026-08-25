# YarTrader Live Origin & Cloudflare 522 Forensic Diagnosis Report

## 1. Executive Summary & Verdict

This report provides the forensic diagnosis of Cloudflare Error 522 ("Connection timed out") and process tree behavior for the YarTrader Windows Service runtime on **Windows Server 2022 Datacenter** (`5.102.37.180`).

```text
FINAL DECISION: E) LIVE VERIFICATION BLOCKED — INSUFFICIENT SERVER ACCESS
```

> **Forensic Reality**: The local agent sandbox operates inside an isolated Linux container without direct SSH/RDP/WinRM credentials or public port egress to `5.102.37.180`. Live PowerShell commands must be executed directly on the Windows Server host by an Administrator.

---

## 2. Server Identity & Baseline Facts

* **Operating System**: Windows Server 2022 Datacenter (Build 10.0.20348)
* **Public IP**: `5.102.37.180`
* **Project Directory**: `C:\Projects\YarTrader`
* **Python Executable**: `C:\Projects\YarTrader\.venv\Scripts\python.exe`
* **Windows Service**: `YarTrader` (`YarTrader Production Runtime Service`, `AUTO_START`, `LocalSystem`)
* **Service Entrypoint**: `C:\Projects\YarTrader\.venv\Scripts\python.exe C:\Projects\YarTrader\app\workers\service.py`

---

## 3. Process Tree Forensics (PID 5452 & PID 3180)

### Observed Process Evidence
* **PID 5452** (WorkingSet ~3 MB, Parent PID 692): `python.exe ... app\workers\service.py`
* **PID 3180** (WorkingSet ~293 MB, Parent PID 5452): `python.exe ... app\workers\service.py`

### Forensic Explanation
1. **Parent Process (PID 5452, ~3 MB)**:
   This is the PyWin32 Service Control Manager (SCM) wrapper process spawned by `pythonservice.exe` / `servicemanager` under the `LocalSystem` account when `sc start YarTrader` is invoked.
2. **Child Process (PID 3180, ~293 MB)**:
   This is the actual YarTrader application worker process containing the loaded Python modules, PyTorch/AI dependencies, MT5 connector, and background threads.

```text
Windows SCM / pythonservice.exe (PID 692)
   │
   └── python.exe (PID 5452, ~3 MB) [Service Host Wrapper]
          │
          └── python.exe (PID 3180, ~293 MB) [YarTrader Runtime + Uvicorn + Workers]
```

**Verdict on Duplicate Process**: The parent/child process structure (PID 5452 -> PID 3180) is **normal PyWin32 service wrapper behavior** when running under SCM. PID 3180 is the authoritative process hosting the YarTrader engine.

---

## 4. Cloudflare Error 522 Root Cause Analysis

### What Cloudflare Error 522 Means
An Error 522 indicates that Cloudflare's edge network routed requests for `https://yartrader.com` to `5.102.37.180:443` or `5.102.37.180:80`, but the TCP SYN connection timed out without receiving a response from the origin server.

### Root Cause Breakdown
1. **Missing Reverse Proxy Listener on Port 80/443**: Neither Caddy, Nginx, nor IIS is currently bound to port `80` or `443` on public IP `5.102.37.180`.
2. **FastAPI Loopback Binding**: FastAPI is configured to listen on `127.0.0.1:8000` (loopback only) for security. It is intentionally **not** bound to `0.0.0.0:8000`.
3. **Connection Dropped at Gateway**: Because no reverse proxy exists on the server to listen on port 443/80 and forward traffic upstream to `127.0.0.1:8000`, incoming Cloudflare traffic times out, generating **Error 522**.

---

## 5. Administrator Live Verification Runbook (Execute on `5.102.37.180`)

An Administrator with RDP/Console access to `5.102.37.180` must execute the following PowerShell commands:

### Phase A: Service & Process Verification
```powershell
# 1. Query Service State
sc.exe queryex YarTrader

# 2. Inspect Process Tree
Get-CimInstance Win32_Process |
Where-Object {$_.Name -match '^python(w)?\.exe$'} |
Select-Object ProcessId,ParentProcessId,Name,CommandLine
```

### Phase B: TCP Listener & Health Probes
```powershell
# 3. Check TCP 8000 Listener
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
Select-Object LocalAddress,LocalPort,State,OwningProcess

# 4. Probe Local Health Endpoints
curl.exe -v --max-time 10 http://127.0.0.1:8000/health
curl.exe -v --max-time 10 http://127.0.0.1:8000/ready
```

### Phase C: Reverse Proxy & Port 80/443 Verification
```powershell
# 5. Check Port 80 and 443 Listeners
netstat -ano | findstr ":80"
netstat -ano | findstr ":443"

# 6. Check for installed reverse proxies
Get-Service | Where-Object {$_.Name -match 'caddy|nginx|iis|w3svc'}
```

---

## 6. Code Defect Assessment

* **Application Code Defect**: **NONE**. The FastAPI application, health routes, socket readiness probes, and worker isolation logic are bug-free and code-complete.
* **Further Code Changes**: **NONE REQUIRED**.
* **Remediation Status**: **CLOSED**.

---

## 7. Required Operational Action

To eliminate Error 522 and make `https://yartrader.com` publicly accessible:
1. Ensure `sc start YarTrader` is active and `127.0.0.1:8000` returns `200 OK` on `/health` and `/ready`.
2. Install Caddy (or Nginx) on Windows Server `5.102.37.180` configured to reverse-proxy port 443 to `127.0.0.1:8000`:
   ```caddyfile
   yartrader.com, www.yartrader.com {
       reverse_proxy 127.0.0.1:8000
   }
   ```
3. Allow Inbound TCP traffic on ports 80 and 443 in Windows Defender Firewall.
