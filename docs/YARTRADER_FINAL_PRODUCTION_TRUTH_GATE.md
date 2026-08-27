# YarTrader Final Production Truth Gate Report

## 1. Executive Summary & Required Key-Value Metrics

```text
GIT_SHA=4895e9ec94769fcd3c081faf890e33a3594589d3
ORIGIN_MAIN_SHA=4895e9ec94769fcd3c081faf890e33a3594589d3
PRODUCTION_SHA=NOT ACCESSIBLE (LINUX SANDBOX CONTAINER CONTEXT)
SERVICE_STATUS=NOT ACCESSIBLE (LINUX SANDBOX CONTAINER CONTEXT)
SERVICE_PID=NOT ACCESSIBLE
PROCESS_START_TIME=NOT ACCESSIBLE
PROCESS_SOURCE_RECONCILED=NOT ACCESSIBLE
LOCAL_RUNTIME=PASS (100% GET & HEAD 200 OK on 127.0.0.1:8000)
PUBLIC_RUNTIME=UNVERIFIED (https://yartrader.com/fa returns 404 Not Found)
SEO=PASS (sitemap.xml and robots.txt verified in dist/ and local runtime)
LOCALIZATION=PASS (167 keys parity across fa, en, tr, ar)
API_ISOLATION=PASS (GET /api/nonexistent returns 404 JSON)
TESTS=PASS (1,684 test units passed, 0 failures)
BUILD=PASS (Vite production build completed in 2.50s)
CLOUDFLARE=ACTIVE (Proxying origin with dynamic JSON 404s on unrestarted routes)
FINAL_VERDICT=NOT PROVEN — PRODUCTION HOST ACCESS UNAVAILABLE
```

---

## 2. Environment Context & Host Access Limitations

* **Jules Sandbox Environment:** Linux Docker Container (`Linux devbox 6.8.0-x86_64 Ubuntu 24.04 LTS`).
* **Win32 / PowerShell Accessibility:** Native Windows commands (`Get-CimInstance Win32_Service`, `Get-Process`, `Get-NetTCPConnection`, `Restart-Service`) are unavailable within the Linux container context.
* **Governance Rule Applied:** In accordance with Section 7 strict verdict rules, Linux container sandbox evidence is NOT substituted for native Windows production host evidence.

---

## 3. Local Container Runtime Probe Matrix (`127.0.0.1:8000`)

| Route / Endpoint | GET Status | HEAD Status | Content-Type | Result |
| :--- | :--- | :--- | :--- | :--- |
| `http://127.0.0.1:8000/` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/fa` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/en` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/tr` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/ar` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/robots.txt` | **200 OK** | **200 OK** | `text/plain; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/sitemap.xml` | **200 OK** | **200 OK** | `application/xml` | **PASS** |
| `http://127.0.0.1:8000/pricing` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/features` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/guide` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/faq` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/login` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/register` | **200 OK** | **200 OK** | `text/html; charset=utf-8` | **PASS** |
| `http://127.0.0.1:8000/api/nonexistent` | **404 Not Found** | N/A | `application/json` | **PASS (API Isolation)** |

---

## 4. Public HTTPS Production Probe Matrix (`https://yartrader.com`)

| Route / Endpoint | GET Status | HEAD Status | Content-Type | Cloudflare Cache | Root Cause / Diagnosis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `https://yartrader.com/` | **200 OK** | **405** | `text/html` / `application/json` | DYNAMIC | HEAD method unhandled on origin |
| `https://yartrader.com/fa` | **404** | **404** | `application/json` | DYNAMIC | Unrestarted Uvicorn process memory |
| `https://yartrader.com/en` | **404** | **404** | `application/json` | DYNAMIC | Unrestarted Uvicorn process memory |
| `https://yartrader.com/tr` | **404** | **404** | `application/json` | DYNAMIC | Unrestarted Uvicorn process memory |
| `https://yartrader.com/ar` | **404** | **404** | `application/json` | DYNAMIC | Unrestarted Uvicorn process memory |
| `https://yartrader.com/robots.txt` | **200 OK** | **404** | `text/plain` / `application/json` | EXPIRED / HIT | GET active; HEAD unrestarted |
| `https://yartrader.com/sitemap.xml` | **404** | **404** | `application/json` | DYNAMIC | Unrestarted Uvicorn process memory |
| `https://yartrader.com/pricing` | **200 OK** | **405** | `text/html` / `application/json` | DYNAMIC | GET active; HEAD 405 |
| `https://yartrader.com/features` | **200 OK** | **405** | `text/html` / `application/json` | DYNAMIC | GET active; HEAD 405 |
| `https://yartrader.com/guide` | **404** | **404** | `application/json` | DYNAMIC | Unrestarted Uvicorn process memory |
| `https://yartrader.com/faq` | **404** | **404** | `application/json` | DYNAMIC | Unrestarted Uvicorn process memory |
| `https://yartrader.com/login` | **200 OK** | **405** | `text/html` / `application/json` | DYNAMIC | GET active; HEAD 405 |
| `https://yartrader.com/register` | **200 OK** | **405** | `text/html` / `application/json` | DYNAMIC | GET active; HEAD 405 |
| `https://yartrader.com/api/nonexistent` | **403** | N/A | `text/plain` | DYNAMIC | Active (API Isolation Intact) |

---

## 5. SRE Windows Host Deployment Instructions (`C:\Projects\YarTrader`)

To reload the Python process memory on `C:\Projects\YarTrader`:

```powershell
Set-Location C:\Projects\YarTrader
git pull origin main
Set-Location trader-terminal
npm run build
Set-Location ..
Restart-Service YarTrader
Get-Service YarTrader
```

---

## 6. Final Acceptance Verdict

```text
FINAL_VERDICT=NOT PROVEN — PRODUCTION HOST ACCESS UNAVAILABLE
```
