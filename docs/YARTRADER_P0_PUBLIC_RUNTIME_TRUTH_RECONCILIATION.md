# YarTrader P0 Public Runtime Truth & SEO Routing Forensic Reconciliation Report

## 1. Executive Summary & Root Cause Classification

This report delivers the forensic deployment and public runtime truth reconciliation for YarTrader's P0 SEO and localization routing.

### Forensic Investigation Findings:
1. **Local Container Runtime Truth (`127.0.0.1:8000`):**
   When running `src/Application/Services/web_dashboard.py` locally on `127.0.0.1:8000`, 100% of GET and HEAD probes across `/`, `/fa`, `/en`, `/tr`, `/ar`, `/robots.txt`, and `/sitemap.xml` return **`HTTP 200 OK`**. Unregistered API paths (`/api/nonexistent`) return `HTTP 404 JSON`.
2. **Public HTTPS Production Truth (`https://yartrader.com`):**
   Direct HTTPS probes to `https://yartrader.com/fa`, `/en`, `/tr`, `/ar`, and `/sitemap.xml` return `HTTP 404 Not Found` with body `{"detail":"Not Found"}` and `server: cloudflare`. HTTP `HEAD /` returns `HTTP 405 Method Not Allowed` (`allow: GET`).
3. **Root Cause Classification:** **`A. DEPLOYMENT PATH DRIFT / F. REVERSE PROXY UPSTREAM DRIFT`**
   The FastAPI 404 response `{"detail":"Not Found"}` returned by `https://yartrader.com/fa` demonstrates that the public reverse proxy / Cloudflare origin is forwarding requests to a running Python process that does NOT have the `@app.api_route` definitions for localized routes or HEAD method support loaded in memory or on disk.

Per strict Anti-False-PASS governance rules, the final acceptance verdict is classified as **`PARTIAL — LOCAL FIX VERIFIED / PUBLIC PRODUCTION NOT VERIFIED`** / **`BLOCKED`**.

---

## 2. Local vs. Public HTTPS Endpoint Comparison Matrix

| Path | Method | Local Sandbox Server (`127.0.0.1:8000`) | Live Remote Server (`https://yartrader.com`) | Classification |
| :--- | :--- | :--- | :--- | :--- |
| `/` | GET | **200 OK** (`text/html`) | **200 OK** (`text/html`) | Active |
| `/` | HEAD | **200 OK** (`text/html`) | **405 Method Not Allowed** | Upstream / Process Drift |
| `/fa` | GET / HEAD | **200 OK** (`text/html`) | **404 Not Found** (`application/json`) | Upstream / Process Drift |
| `/en` | GET / HEAD | **200 OK** (`text/html`) | **404 Not Found** (`application/json`) | Upstream / Process Drift |
| `/tr` | GET / HEAD | **200 OK** (`text/html`) | **404 Not Found** (`application/json`) | Upstream / Process Drift |
| `/ar` | GET / HEAD | **200 OK** (`text/html`) | **404 Not Found** (`application/json`) | Upstream / Process Drift |
| `/robots.txt` | GET | **200 OK** (`text/plain`) | **200 OK** (`text/plain`) | Active |
| `/robots.txt` | HEAD | **200 OK** (`text/plain`) | **404 Not Found** (`application/json`) | Upstream / Process Drift |
| `/sitemap.xml` | GET / HEAD | **200 OK** (`application/xml`) | **404 Not Found** (`application/json`) | Upstream / Process Drift |
| `/api/nonexistent` | GET | **404 Not Found** (`application/json`) | **403 / 404** (`text/plain`) | Active (API Isolation Intact) |

---

## 3. Route Implementation Verification (`src/Application/Services/web_dashboard.py`)

```python
# ==============================================================================
# 0. SEO & ROBOTS / SITEMAP ENDPOINTS
# ==============================================================================
@app.api_route("/sitemap.xml", methods=["GET", "HEAD"])
def get_sitemap():
    sitemap_path = "trader-terminal/dist/sitemap.xml"
    if not os.path.exists(sitemap_path):
        sitemap_path = "trader-terminal/public/sitemap.xml"
    if os.path.exists(sitemap_path):
        return FileResponse(sitemap_path, media_type="application/xml")
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://yartrader.com/fa</loc></url></urlset>',
        media_type="application/xml"
    )

@app.api_route("/robots.txt", methods=["GET", "HEAD"])
def get_robots():
    robots_path = "trader-terminal/dist/robots.txt"
    if not os.path.exists(robots_path):
        robots_path = "trader-terminal/public/robots.txt"
    if os.path.exists(robots_path):
        return FileResponse(robots_path, media_type="text/plain")
    return Response(
        content="User-agent: *\nAllow: /\nSitemap: https://yartrader.com/sitemap.xml\n",
        media_type="text/plain"
    )

# ==============================================================================
# 1. WEB MANAGEMENT DASHBOARD & SPA PAGE
# ==============================================================================
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/fa", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/en", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/tr", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/ar", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/fa/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/en/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/tr/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/ar/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
```

---

## 4. Test Suite & Build Verification

* **Vite Frontend Build:** `cd trader-terminal && npm run build` (2.95s). Generated `dist/index.html`, `dist/robots.txt`, and `dist/sitemap.xml`.
* **SEO Integration Tests (`tests/YarTrader.Tests/Dashboard/test_seo_localization_routing.py`):** 16/16 passed.
* **Full Pytest Suite:** **1,684 passed test units** (1,667 passed functions + 17 subtests, 0 failures).

---

## 5. SRE Action Plan for Windows Production Host

To verify the running origin process on `C:\Projects\YarTrader`:

1. **Verify Source Path & Service Binding:**
   ```powershell
   Get-CimInstance Win32_Service | Where-Object {$_.Name -eq "YarTrader"} | Select-Object Name, State, PathName
   Get-CimInstance Win32_Process | Where-Object {$_.Name -match "python|uvicorn"} | Select-Object ProcessId, CommandLine
   Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess
   ```
2. **Execute Deployment Pull & Restart:**
   ```powershell
   Set-Location C:\Projects\YarTrader
   git pull origin main
   Set-Location trader-terminal
   npm run build
   Set-Location ..
   Restart-Service YarTrader
   ```

---

## 6. Final Acceptance Verdict

```text
FINAL VERDICT = PARTIAL — LOCAL FIX VERIFIED / PUBLIC PRODUCTION NOT VERIFIED
```
