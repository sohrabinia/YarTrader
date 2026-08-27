# YarTrader P0 Production Runtime Proof & Host Access Report

## 1. Executive Summary & Host Access Status

```text
PRODUCTION WINDOWS HOST ACCESS = UNAVAILABLE (LINUX SANDBOX CONTAINER CONTEXT)
```

Jules operates inside an isolated Linux Docker container environment (`Linux devbox 6.8.0-x86_64 Ubuntu 24.04 LTS`). The container environment does not possess direct Win32 RPC, Windows Service Control Manager (SCM), or remote PowerShell access to the physical Windows production server located at `C:\Projects\YarTrader`.

Per the non-negotiable instructions of the P0 Final Blocker directive, Linux container sandbox commands are NOT substituted for native Windows production host evidence.

---

## 2. Local Container Runtime Verification (`127.0.0.1:8000`)

When tested on the local FastAPI container instance (`127.0.0.1:8000`), the application code passes 100% of GET and HEAD route probes:

| Endpoint | Method | Local Status Code | Content-Type | Result |
| :--- | :--- | :--- | :--- | :--- |
| `http://127.0.0.1:8000/` | GET | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/` | HEAD | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/fa` | GET | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/fa` | HEAD | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/en` | GET | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/en` | HEAD | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/tr` | GET | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/tr` | HEAD | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/ar` | GET | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/ar` | HEAD | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/robots.txt` | GET | **200 OK** | `text/plain; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/robots.txt` | HEAD | **200 OK** | `text/plain; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/sitemap.xml` | GET | **200 OK** | `application/xml` | **PASS** |
| `http://127.0.0.1:8000/sitemap.xml` | HEAD | **200 OK** | `application/xml` | **PASS** |
| `http://127.0.0.1:8000/api/nonexistent` | GET | **404 Not Found** | `application/json` | **PASS (API Isolation)** |

---

## 3. Public HTTPS Production Probe Truth Matrix (`https://yartrader.com`)

| Endpoint | Method | Status Code | Cloudflare Response Headers | Cause / Classification |
| :--- | :--- | :--- | :--- | :--- |
| `https://yartrader.com/` | GET | **200 OK** | `server: cloudflare`, `cf-cache-status: DYNAMIC` | Active |
| `https://yartrader.com/` | HEAD | **405 Method Not Allowed** | `allow: GET`, `content-type: application/json` | Windows Host Process Memory Unrestarted |
| `https://yartrader.com/fa` | GET / HEAD | **404 Not Found** | `content-type: application/json` | Windows Host Process Memory Unrestarted |
| `https://yartrader.com/en` | GET / HEAD | **404 Not Found** | `content-type: application/json` | Windows Host Process Memory Unrestarted |
| `https://yartrader.com/tr` | GET / HEAD | **404 Not Found** | `content-type: application/json` | Windows Host Process Memory Unrestarted |
| `https://yartrader.com/ar` | GET / HEAD | **404 Not Found** | `content-type: application/json` | Windows Host Process Memory Unrestarted |
| `https://yartrader.com/robots.txt` | GET | **200 OK** | `content-type: text/plain` | Active |
| `https://yartrader.com/robots.txt` | HEAD | **404 Not Found** | `content-type: application/json` | Windows Host Process Memory Unrestarted |
| `https://yartrader.com/sitemap.xml` | GET / HEAD | **404 Not Found** | `content-type: application/json` | Windows Host Process Memory Unrestarted |
| `https://yartrader.com/api/nonexistent` | GET | **403 / 404** | `content-type: text/plain` | Active (API Isolation Intact) |

---

## 4. Required SRE Script for Remote Windows Production Server (`C:\Projects\YarTrader`)

To perform the required Windows Service restart and process inspection on the actual Windows Production host:

```powershell
Set-Location C:\Projects\YarTrader

# 1. Fetch & pull latest main
git fetch origin
git pull origin main
git status --short

# 2. Build frontend assets
Set-Location trader-terminal
npm run build
Set-Location ..

# 3. Capture Old Service Process ID
$oldSvc = Get-CimInstance Win32_Service -Filter "Name='YarTrader'"
Write-Host "Old Service ProcessId:" $oldSvc.ProcessId

# 4. Restart Service
Restart-Service YarTrader
Start-Sleep -Seconds 8

# 5. Capture New Service Process ID & Port Ownership
$newSvc = Get-CimInstance Win32_Service -Filter "Name='YarTrader'"
Write-Host "New Service ProcessId:" $newSvc.ProcessId
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess

# 6. Verify Origin Localhost Probes
curl.exe -i http://127.0.0.1:8000/fa
curl.exe -I http://127.0.0.1:8000/fa
curl.exe -i http://127.0.0.1:8000/sitemap.xml
```

---

## 5. Final Verdict

```text
FINAL VERDICT = PARTIAL — LOCAL VERIFIED / WINDOWS PRODUCTION NOT VERIFIED
PRODUCTION WINDOWS HOST ACCESS = UNAVAILABLE
```
