# TradeYar AI — Local Runtime & Integration Architecture

This document describes the unified single-server production and local development runtime architectures of TradeYar AI.

## 1. Runtime Architectures

TradeYar AI supports two primary modes of operation: **Production/Simulation Mode** (single-server, lightweight, unified) and **Active Development Mode** (multi-process, rapid reload).

```
+-------------------------------------------------------------------------------------------------+
|                                    ACTIVE DEVELOPMENT MODE                                      |
|                                                                                                 |
|   Browser [localhost:5173] ===> Vite Dev Server ===[Proxy /api] ===> FastAPI Backend [:8000]     |
+-------------------------------------------------------------------------------------------------+

+-------------------------------------------------------------------------------------------------+
|                                    PRODUCTION/LOCAL MODE                                        |
|                                                                                                 |
|   Browser [localhost:8000] ===> FastAPI (Serves React dist/ assets, endpoints, & legacy HTML)  |
+-------------------------------------------------------------------------------------------------+
```

### Mode A: Production / Sandbox Mode (Single Server)
FastAPI serves both the backend APIs and compiles/delivers the standalone React frontend SPA.
- **Entry Point:** `src/Application/Services/web_dashboard.py` (via Uvicorn on Port `8000`)
- **API Endpoints:** Managed by FastAPI (`/api/*`, `/v1/*`, `/health`, `/locales/*`).
- **Static Assets:** Serves React production build directly from `trader-terminal/dist/` under the root (`/`) and `/dashboard` using a static directory mount (`/assets` to `trader-terminal/dist/assets`).
- **Zero-Risk Fallback:** If `trader-terminal/dist/index.html` is not present, FastAPI automatically falls back to serving the robust inline legacy HTML, preventing deployment downtime or broken setups.

### Mode B: Developer Mode (Vite Development)
Enables fast client-side HMR (Hot Module Replacement) and rapid component reloading.
- **Frontend Entry:** Vite dev server running on port `5173` via `npm run dev`.
- **Backend Entry:** FastAPI running on port `8000`.
- **API Gateway Proxying:** All requests directed to `/api/*`, `/v1/*`, and `/locales/*` are proxied by Vite automatically to `http://localhost:8000`. This completely avoids CORS headaches and eliminates hardcoding `localhost:8000` in the React source code.

---

## 2. API Communication Flow

Frontend network requests inside `App.jsx` call standard relative paths via the `apiService` layer.

1. **Relative Addressing:** Requests like `apiService.get('/api/subscription/plans')` or `apiService.get('/api/intelligence/status')` do not include hardcoded host parameters.
2. **Proxy Resolution (Dev):** When running under Vite, `/api/...` gets captured by Vite and forwarded to `http://localhost:8000/api/...`.
3. **Same-Origin Resolution (Prod):** When served natively by FastAPI under `:8000`, the browser makes requests against the same origin host, executing cleanly and without any security blocks.

---

## 3. Recommended Developer Workflows

### Unified Development Command
Launch the entire local suite in development mode via a single script:
```powershell
.\scripts\start-dev.ps1
```
This runs the FastAPI gateway backend, checks if Vite is active, stops any dangling node processes safely, and launches the Vite client side-by-side with full diagnostic outputs.

### Production Build & Single Server Run
To test production delivery locally:
1. Compile React: `cd trader-terminal && npm run build`
2. Start Python server: `python -m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000`
3. Load `http://localhost:8000` in your web browser. No npm development processes are required.
