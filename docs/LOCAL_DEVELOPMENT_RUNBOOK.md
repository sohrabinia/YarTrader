# TradeYar AI — Local Development & Deployment Runbook

This runbook provides instructions on configuring, starting, and verifying the TradeYar AI standalone React/Vite development server and production single-server deployments.

---

## 1. Developer Mode: Unified Startup (Ports 5173 + 8000)

To start both the FastAPI backend gateway and the React hot-reloading development client side-by-side with zero port collision or CORS blocks:

Run the PowerShell setup launcher script from the repository root:
```powershell
.\scripts\start-dev.ps1
```

### Script Execution Profile:
1. **Repository Auto-Detection:** Dynamically resolves the repository root directory automatically.
2. **Backend Scanning:** Scans Port `8000` for active FastAPI instances, spawning Uvicorn reload processes if free.
3. **Frontend Scanning:** Scans Port `5173` and safely terminates duplicate or orphaned Vite/node servers.
4. **Dev Startup:** Launches `npm run dev` inside `trader-terminal` and formats unified output summaries of active ports and workers.

### Dev Client URLs:
- **Frontend App:** http://localhost:5173 (Proxies `/api`, `/v1`, `/locales` to `http://localhost:8000` automatically)
- **Backend API:** http://localhost:8000
- **Health Diagnostics Status:** http://localhost:8000/health

---

## 2. Production Local Mode / Standalone Serving (Port 8000 Only)

To serve both JSON REST APIs and the React bundle natively from a single Python server with zero node or development server processes:

1. **Compile Static Chunks:**
   ```bash
   cd trader-terminal
   npm install
   npm run build
   cd ..
   ```
   This compiles optimized build files under `trader-terminal/dist/`.

2. **Launch Standalone Python Server:**
   ```bash
   PYTHONPATH=. python -m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000
   ```

3. **Verify in Browser:**
   - Load `http://localhost:8000` inside your web browser.
   - FastAPI dynamically detects the built React assets, serves files, manages client-side SPA route fallbacks, and executes clean Persian/English localization.
