# TradeYar AI — Startup Production Guidelines

This guide details the single-command and standardized production-grade startup procedures for launching both the TradeYar AI FastAPI Intelligence Backend and the React/Vite Frontend.

---

## 🚀 Standard Production Startup (FastAPI + React SPA)

When running in production, FastAPI is configured to serve the fully compiled React Single Page Application (SPA) automatically from `trader-terminal/dist/index.html`.

### Step 1: Compile Frontend Assets (Once)
Compile the React frontend to generate optimized, static production bundles:
```bash
cd trader-terminal
npm install
npm run build
cd ..
```

### Step 2: Start the Central Backend Service
Run the main FastAPI server. This server will automatically serve the built React frontend on `/` and `/dashboard`, and mount static assets `/assets` to `trader-terminal/dist/assets`:
```bash
PYTHONPATH=. python3 -m uvicorn src.Application.Services.web_dashboard:app --port 8000 --host 0.0.0.0
```

Now, navigate to `http://localhost:8000/` inside any browser. The full production TradeYar AI platform with real-time intelligence feeds, active subscription plans, chat assistant, and SRE dashboards will load instantly!

---

## 🛡️ Service Host Startup (Full Windows background daemon)
To start the FastAPI web dashboard together with all dedicated background worker threads (Research, Intelligence, and Shadow workers) as a robust, managed background host:
```bash
python3 -m app.workers.service
```
This is fully automated on Windows servers using NSSM and PowerShell via `scripts/deploy_service.ps1`.
