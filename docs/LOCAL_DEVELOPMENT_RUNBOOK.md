# TradeYar AI Local Development Runbook

This document details the configuration and boot runbook strategies for launching and executing TradeYar AI locally.

---

## Mode A: Single-Port Production Mode (Optimized / Compiled SPA)

In this mode, the standalone React/Vite Single Page Application inside `/trader-terminal` is pre-compiled, and the backend FastAPI server serves the compiled static files directly. Only port 8000 is occupied.

### Execution Steps:

1. **Navigate to the Frontend Directory and Compile Assets**:
   ```bash
   cd trader-terminal
   npm run build
   cd ..
   ```
   *Note: This generates optimized production build bundles under `/trader-terminal/dist/`.*

2. **Boot the Backend FastAPI Server**:
   ```bash
   PYTHONPATH=. python -m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000
   ```

3. **Verify Endpoints**:
   - Web App UI Dashboard: [http://localhost:8000](http://localhost:8000)
   - SRE Health Monitoring: [http://localhost:8000/health](http://localhost:8000/health)

---

## Mode B: Active Developer Mode (Dual-Port / Hot Reload)

In active development, the frontend React Vite server and the backend FastAPI server are executed concurrently on separate ports, allowing instant hot reload of any changes to user-interface screens or assets.

### Automated PowerShell Bootstrapper:

We provide an idempotent bootstrapper script that automatically detects the repository root, resolves port conflicts, and launches both services:

```powershell
.\scripts\start-dev.ps1
```

### Manual Developer Boot:

If running on non-Windows platforms or executing manually:

1. **Terminal 1: Start Backend API**:
   ```bash
   PYTHONPATH=. python -m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000
   ```

2. **Terminal 2: Start Frontend dev Server**:
   ```bash
   cd trader-terminal
   npm run dev
   ```

### Active Dev Ports:
- Frontend React SPA: [http://localhost:5173](http://localhost:5173) (automatically proxies `/api/*` and `/locales/*` requests back to Port 8000)
- Backend APIs: [http://localhost:8000](http://localhost:8000)
