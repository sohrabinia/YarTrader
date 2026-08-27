# YarTrader P0 Public Runtime Truth & SEO Routing Forensic Reconciliation Report

## 1. Executive Summary

This report delivers a forensic deployment and public runtime truth reconciliation for YarTrader's P0 SEO and localization routing. It proves the exact execution path from repository source code, working tree, test execution, local uvicorn runtime, to the live public domain `https://yartrader.com`.

Local code verification on `http://127.0.0.1:8000` passes **100%** across all 14 GET and HEAD probes (`/`, `/fa`, `/en`, `/tr`, `/ar`, `/robots.txt`, `/sitemap.xml`) with HTTP 200 OK while preserving API 404 isolation.

However, public HTTPS probes against `https://yartrader.com` confirm that the remote production host is currently running `main` at commit `8f698f4305996681950ffd09c390b92256746d51`. On commit `8f698f4`, route handlers for `/fa`, `/en`, `/tr`, `/ar`, `/sitemap.xml` are absent, and HEAD requests on `/` return HTTP 405 Method Not Allowed.

Per strict Anti-False-PASS governance rules, the final acceptance verdict is classified as **`PARTIAL — LOCAL FIX VERIFIED / PUBLIC PRODUCTION NOT VERIFIED`**.

---

## 2. Repository & Source Code Truth (Gate 1)

* **Repository HEAD SHA:** `4895e9ec94769fcd3c081faf890e33a3594589d3`
* **Local Branch:** `jules-14975269337046365248-2c55d464`
* **Remote Main SHA:** `8f698f4305996681950ffd09c390b92256746d51` (PR #200 merge commit)

### Source File Route Declarations (`src/Application/Services/web_dashboard.py`):
```python
@app.api_route("/sitemap.xml", methods=["GET", "HEAD"])
def get_sitemap():
    ...

@app.api_route("/robots.txt", methods=["GET", "HEAD"])
def get_robots():
    ...

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

## 3. Local Runtime Verification Matrix (`127.0.0.1:8000`)

| Endpoint | Method | HTTP Status | Content-Type | Result |
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

## 4. Public HTTPS Production Truth Matrix (`yartrader.com`)

| Endpoint | Method | Status Code | Cloudflare Server / Cache Status | Content-Type / Allow | Cause |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `https://yartrader.com/` | GET | **200 OK** | cloudflare / DYNAMIC | `text/html; charset=utf-8` | Active |
| `https://yartrader.com/` | HEAD | **405** | cloudflare / DYNAMIC | `application/json` (allow=GET) | Legacy `8f698f4` |
| `https://yartrader.com/fa` | GET / HEAD | **404** | cloudflare / DYNAMIC | `application/json` | Legacy `8f698f4` |
| `https://yartrader.com/en` | GET / HEAD | **404** | cloudflare / DYNAMIC | `application/json` | Legacy `8f698f4` |
| `https://yartrader.com/tr` | GET / HEAD | **404** | cloudflare / DYNAMIC | `application/json` | Legacy `8f698f4` |
| `https://yartrader.com/ar` | GET / HEAD | **404** | cloudflare / DYNAMIC | `application/json` | Legacy `8f698f4` |
| `https://yartrader.com/robots.txt` | GET | **200 OK** | cloudflare / EXPIRED | `text/plain; charset=utf-8` | Active |
| `https://yartrader.com/robots.txt` | HEAD | **404** | cloudflare / HIT | `application/json` | Legacy `8f698f4` |
| `https://yartrader.com/sitemap.xml` | GET / HEAD | **404** | cloudflare / DYNAMIC | `application/json` | Legacy `8f698f4` |
| `https://yartrader.com/api/nonexistent` | GET | **403 / 404** | cloudflare / DYNAMIC | `text/plain` | Active (API Isolation) |

---

## 5. Automated Tests & Build Verification

* **Vite Frontend Production Build:** Executed `cd trader-terminal && npm run build` (built in 2.95s). Verified `dist/index.html`, `dist/robots.txt`, and `dist/sitemap.xml` created.
* **Pytest SEO & Localization Test Suite:** Executed `python3 -m pytest tests/YarTrader.Tests/Dashboard/test_seo_localization_routing.py` (16/16 passed).
* **Full Automated Test Suite:** Executed `python3 -m pytest -q` (1,667 passed test functions + 17 subtest assertions = **1,684 total passed test units**).

---

## 6. SRE Deployment Instructions for Remote Windows Production Server

To promote the local code fix to the live production server (`C:\Projects\YarTrader`):

```powershell
# 1. Merge PR branch into main
# 2. On Production Windows Host:
Set-Location C:\Projects\YarTrader
git pull origin main
Set-Location trader-terminal
npm run build
Set-Location ..
Restart-Service YarTrader
Get-Service YarTrader
```

---

## 7. Final Acceptance Verdict

```text
FINAL VERDICT = PARTIAL — LOCAL FIX VERIFIED / PUBLIC PRODUCTION NOT VERIFIED
```
