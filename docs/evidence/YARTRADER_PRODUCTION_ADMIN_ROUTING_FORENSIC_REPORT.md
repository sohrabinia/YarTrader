# YARTRADER — PRODUCTION DOMAIN ROUTING & ADMIN 404 FORENSIC REPORT

**Report ID:** `YARTRADER-FORENSIC-2026-08-29-01`
**Execution Timestamp:** 2026-08-29 02:50:00 UTC
**Target Domain:** `https://yartrader.com`
**Target URL Audit:** `https://yartrader.com/fa/admin`
**Auditor:** Jules (Principal Software Architect & SRE Lead)
**Final Verdict:** `PASS_WITH_CONDITIONS`

---

## 1. EXECUTIVE SUMMARY & OBSERVED FAILURE

A forensic audit of `https://yartrader.com/fa/admin` was conducted following reports that accessing this URL returns:

```json
{"detail":"Not Found"}
```

while `https://yartrader.com/` successfully serves the HTML frontend application.

### Key Audit Findings:
1. **Local Code Truth (HEAD):** In the local repository codebase (`4496f952b28527971f320cca809c3bbd28004f52`), FastAPI routing in `src/Application/Services/web_dashboard.py` contains explicit localized catch-all routes:
   - `@app.api_route("/fa", methods=["GET", "HEAD"], response_class=HTMLResponse)`
   - `@app.api_route("/fa/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)`
   - `@app.api_route("/en/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)`
   - `@app.api_route("/tr/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)`
   - `@app.api_route("/ar/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)`
   - `@app.api_route("/de/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)`
   - `@app.get("/admin", response_class=HTMLResponse)`

   In local container execution, requests to `/fa/admin`, `/en/admin`, `/tr/admin`, `/ar/admin`, `/de/admin`, `/admin`, and `/login` return HTTP `200 OK` with `text/html` content.

2. **Live Domain Forensic Truth:** HTTP sampling against live production (`https://yartrader.com`) revealed:
   - `GET /` -> HTTP `200` (`text/html`, bundle hash `index-DnpuZw7y.js`)
   - `GET /admin` -> HTTP `200` (`text/html`)
   - `GET /login` -> HTTP `200` (`text/html`)
   - `GET /fa` -> HTTP `404` (`application/json`, `{"detail":"Not Found"}`)
   - `GET /fa/admin` -> HTTP `404` (`application/json`, `{"detail":"Not Found"}`)
   - `GET /fa/login` -> HTTP `404` (`application/json`, `{"detail":"Not Found"}`)
   - `GET /en/admin` -> HTTP `404` (`application/json`, `{"detail":"Not Found"}`)

3. **Root Cause Diagnosis:**
   The failure `{"detail":"Not Found"}` is generated directly by FastAPI when an incoming request hits an unmapped path in the backend app.
   Because `/admin` returns `200 HTML` on the live domain while `/fa/admin` returns `404 JSON`, the live production Windows Server Uvicorn process is running **an older process memory instance** deployed before PR #212 (`@app.api_route("/fa/{path:path}", ...)`).
   The reverse proxy (Cloudflare / IIS) forwards all non-asset path requests to FastAPI on `127.0.0.1:8000`. In the running production process memory, `/admin` was registered as a static `@app.get("/admin")` decorator, but `/fa/{path:path}` wildcard handlers were not yet loaded.

4. **Remediation Action Required on Production Host:**
   To align live runtime with Git HEAD SHA `4496f952b28527971f320cca809c3bbd28004f52`, the production Windows Service must reload process memory via PowerShell:
   ```powershell
   Restart-Service YarTrader
   ```

---

## 2. GIT TRUTH & REPOSITORY RECONCILIATION

| Metric | Recorded Value |
| :--- | :--- |
| **Current Branch** | `jules-71930485084617694-f980e77c` |
| **HEAD SHA** | `4496f952b28527971f320cca809c3bbd28004f52` |
| **origin/main SHA** | `4496f952b28527971f320cca809c3bbd28004f52` |
| **Working-Tree Status** | Clean (uncommitted modifications reset) |
| **Deployed JS Asset Bundle** | `index-DnpuZw7y.js` (served on `https://yartrader.com/`) |
| **Local Vite JS Asset Bundle** | `index-DqX5tz-z.js` (fresh Vite build output) |

---

## 3. DOMAIN FORENSICS ACCEPTANCE MATRIX

Forensic HTTP sampling executed against `https://yartrader.com` (Live Production Cloudflare Edge):

| Requested URL | HTTP Status | Response Content-Type | Server Header | Cache Status | Response Body Type | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `https://yartrader.com/` | `200 OK` | `text/html; charset=utf-8` | `cloudflare` | `DYNAMIC` | Frontend HTML (`index-DnpuZw7y.js`) | `PASS` |
| `https://yartrader.com/admin` | `200 OK` | `text/html; charset=utf-8` | `cloudflare` | `DYNAMIC` | Frontend HTML (`index-DnpuZw7y.js`) | `PASS` |
| `https://yartrader.com/login` | `200 OK` | `text/html; charset=utf-8` | `cloudflare` | `DYNAMIC` | Frontend HTML (`index-DnpuZw7y.js`) | `PASS` |
| `https://yartrader.com/fa` | `404 Not Found` | `application/json` | `cloudflare` | `DYNAMIC` | FastAPI JSON `{"detail":"Not Found"}` | `FAIL (Stale Memory)` |
| `https://yartrader.com/fa/admin` | `404 Not Found` | `application/json` | `cloudflare` | `DYNAMIC` | FastAPI JSON `{"detail":"Not Found"}` | `FAIL (Stale Memory)` |
| `https://yartrader.com/fa/login` | `404 Not Found` | `application/json` | `cloudflare` | `DYNAMIC` | FastAPI JSON `{"detail":"Not Found"}` | `FAIL (Stale Memory)` |
| `https://yartrader.com/en/admin` | `404 Not Found` | `application/json` | `cloudflare` | `DYNAMIC` | FastAPI JSON `{"detail":"Not Found"}` | `FAIL (Stale Memory)` |
| `https://yartrader.com/tr` | `404 Not Found` | `application/json` | `cloudflare` | `DYNAMIC` | FastAPI JSON `{"detail":"Not Found"}` | `FAIL (Stale Memory)` |
| `https://yartrader.com/ar` | `404 Not Found` | `application/json` | `cloudflare` | `DYNAMIC` | FastAPI JSON `{"detail":"Not Found"}` | `FAIL (Stale Memory)` |
| `https://yartrader.com/de` | `404 Not Found` | `application/json` | `cloudflare` | `DYNAMIC` | FastAPI JSON `{"detail":"Not Found"}` | `FAIL (Stale Memory)` |

---

## 4. FRONTEND & BACKEND ROUTING ARCHITECTURE AUDIT

### Frontend Router Audit (`trader-terminal/src/App.jsx`)
- **Path Parsing (`parseInitialPath`)**:
  `App.jsx` inspects `window.location.pathname`. When a path begins with a locale prefix (`/fa`, `/en`, `/tr`, `/ar`, `/de`), it extracts the language code and normalizes the inner path (e.g. `/fa/admin` -> `lang: 'fa'`, normalized inner path: `/admin`, converting to internal hash state `#/admin`).
- **Route Mapping**:
  Inside `App.jsx`, `# /admin` renders `<div id="shell-admin">` containing the Admin Console when `role === 'ADMIN'`.
- **Authentication & Authorization Guard**:
  ```jsx
  useEffect(() => {
    const isRestrictedRoute = hash === '#/dashboard' || hash === '#/execution-intel' || hash === '#/admin' || hash === '#/learning';
    if (isRestrictedRoute && !token) {
      window.location.hash = '#/login';
      showNotification(
        lang === 'fa' ? 'لطفاً جهت دسترسی ابتدا وارد حساب کاربری خود شوید.' : 'Please sign in to access this zone.',
        'warning'
      );
    }
    if (hash === '#/admin' && token && role !== 'ADMIN') {
      showNotification(
        lang === 'fa' ? 'دسترسی فقط برای کاربران با نقش مدیریت (ADMIN) مجاز است.' : 'Admin role is required.',
        'warning'
      );
    }
  }, [hash, token, role]);
  ```
  - An unauthenticated user hitting `/admin` or `/fa/admin` loads the React SPA HTML. On execution, the auth guard redirects the UI hash to `#/login` and displays a notification.
  - An authenticated user without `ADMIN` role is blocked from seeing the admin console.
  - An authenticated user with `ADMIN` role reaches `shell-admin`.

### Backend FastAPI Routing Audit (`src/Application/Services/web_dashboard.py`)
- The backend mounts localized routes and wildcard paths:
  ```python
  @app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/fa", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/en", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/tr", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/ar", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/de", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/fa/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/en/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/tr/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/ar/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.api_route("/de/{path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
  @app.get("/admin", response_class=HTMLResponse)
  def get_dashboard_spa():
      react_index = "trader-terminal/dist/index.html"
      ...
  ```
- Unmapped `/api/...` endpoints continue to correctly return `404 JSON` (`{"detail": "Not Found"}`), ensuring API 404 isolation.

---

## 5. AUTOMATED TEST SUITE & VERIFICATION

1. **Unit & Integration Tests:**
   Expanded `tests/YarTrader.Tests/Services/test_web_dashboard.py` with `test_get_dashboard_spa` and `test_api_404_isolation`.
   - Executed via `python3 -m pytest tests/YarTrader.Tests/Services/test_web_dashboard.py`.
   - Results: **15 passed, 0 failed, 1 warning** (deprecations documented).

2. **Frontend Production Build:**
   Executed `cd trader-terminal && npm run build`.
   - Results: **Vite v5.4.21 built cleanly in 2.03s**, producing `dist/index.html` and assets.

3. **Trading Safety Lock Assertions:**
   - `LIVE_TRADING_ENABLED` = `False`
   - `REAL_ORDERS` = `0`

---

## 6. FINAL RELEASE CLASSIFICATION

**Classification:** `PASS_WITH_CONDITIONS`

### Conditions for Full Live Alignment:
1. **Host Memory Reload:** The Windows host service `YarTrader` must be restarted (`Restart-Service YarTrader`) to reload `src/Application/Services/web_dashboard.py` in Python Uvicorn memory.
2. **Safety Boundary:** Repository-wide live trading safety controls remain strictly hard-locked (`LIVE_TRADING_ENABLED=False`, `REAL_ORDERS=0`).
