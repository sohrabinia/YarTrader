# TradeYar AI — Local Production & Deployment Runbook

This SRE runbook provides instructions on starting, configuring, and verifying the TradeYar AI local development and production single-server setups.

---

## 1. Normal Usage: One-Command Start

To start the complete, integrated local development environment with both the FastAPI Gateway backend and Vite client hot-reloading:

Run the PowerShell startup script from the repository root:
```powershell
.\scripts\start-dev.ps1
```

### Script Tasks:
1. Scans Port `8000` for active FastAPI instances, starting Uvicorn automatically if port is free.
2. Identifies and stops duplicate, orphaned node/Vite processes listening on Port `5173`.
3. Spawns npm dev server cleanly and prints terminal URLs.

---

## 2. Developer Usage: Vite HMR Mode

For rapid frontend editing under Hot Module Replacement (HMR):
1. **Start FastAPI Gateway:**
   ```bash
   PYTHONPATH=. python -m uvicorn src.Application.Services.web_dashboard:app --host 127.0.0.1 --port 8000
   ```
2. **Start Vite Dev Server:**
   ```bash
   cd trader-terminal
   npm run dev
   ```
3. Load the developer portal on: `http://localhost:5173`
   - Requests made to `/api/*`, `/v1/*`, and `/locales/*` are proxied to Port `8000` on the fly.

---

## 3. Production Local Mode / Deployment

To run a production-like standalone server with zero dependencies on Node or development servers:

1. **Compile Static Assets:**
   ```bash
   cd trader-terminal
   npm install
   npm run build
   ```
   This creates static compiled chunks under `trader-terminal/dist/`.

2. **Serve directly from FastAPI:**
   ```bash
   PYTHONPATH=. python -m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000
   ```

3. Load the production interface in your browser: `http://localhost:8000`
   - FastAPI dynamically detects the built React directory, serves the assets, handles SPA routing, and provides dynamic Persian/English translations.

---

## 4. Troubleshooting Checklist

### Port Already In Use (Port 8000 / 5173)
If you see connection refused or port occupied errors, clear processes using SRE terminal shortcuts:
- **Linux/macOS:**
  ```bash
  kill $(lsof -t -i :8000) 2>/dev/null || true
  kill $(lsof -t -i :5173) 2>/dev/null || true
  ```
- **Windows (PowerShell):**
  ```powershell
  Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force -ErrorAction SilentlyContinue
  Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess -Force -ErrorAction SilentlyContinue
  ```

### Static Assets returning 404
- Verify that `trader-terminal/dist/` contains `index.html` and `assets/`.
- Ensure Uvicorn is executed from the repository root directory.
