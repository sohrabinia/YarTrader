# YarTrader Self-Hosted Production Operations Runbook

## 1. Executive Summary
This document serves as the authoritative operational runbook for deploying, hosting, and maintaining the YarTrader Autonomous Financial Intelligence Platform on self-hosted Windows Server infrastructure (`https://yartrader.com`).

## 2. Infrastructure & Hosting Architecture
* **Source Control:** GitHub Repository (`sohrabinia/YarTrader`).
* **Production Origin:** `https://yartrader.com` (and `https://www.yartrader.com`).
* **Host Platform:** Windows Server (Self-Hosted Windows Service: `YarTrader`).
* **Process Manager:** Windows Service Control Manager (SCM) executing FastAPI + Uvicorn service host.
* **Storage Root:** Isolated SQLite database under `TradeYarStorageRoot/production_db.sqlite`.
* **Static Asset Host:** FastAPI static file mount serving `trader-terminal/dist/` build artifacts.

## 3. Deprecated Deployment Infrastructure
* **Vercel CDN / Serverless Proxy:** DEPRECATED & NEUTRALIZED.
* **Zero Vercel Dependency:** Vercel is NOT used for production hosting, frontend CDN, API reverse proxying, or serverless functions.
* **Vercel Config Files (`vercel.json`):** DELETED.
* **Vercel Proxy Functions (`api/proxy.js`):** DELETED.

## 4. Production Service Management (PowerShell)

### Inspect Service Status
```powershell
Get-Service YarTrader
```

### Restart Production Service (Reload Memory)
```powershell
Restart-Service YarTrader
```

### Verify Service Socket Readyness & Health
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ready"
```

## 5. Reverse Proxy & TLS Configuration
* **Reverse Proxy:** IIS / Nginx for Windows forwarding `https://yartrader.com` to `127.0.0.1:8000`.
* **TLS Certificate:** Let's Encrypt / Certify The Web managing certificates for `yartrader.com`.
* **CORS Policy:** Allowed origins restricted strictly to `https://yartrader.com` and `https://www.yartrader.com`.

## 6. Safety & Kill Switch Invariants
* `LIVE_TRADING_ENABLED = False` (Hard-locked repository-wide).
* `REAL_ORDERS = 0` (Hard-locked repository-wide).
* MT5 Execution restricted to DEMO account `52961173` on `Alpari-MT5-Demo`.
