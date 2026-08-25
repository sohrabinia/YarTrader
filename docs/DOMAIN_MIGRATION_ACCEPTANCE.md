# YarTrader Master Production Domain Migration & Runtime Final Gate Report

## Executive Summary & Final Gate Verdict

* **Production Domain**: `https://yartrader.com` & `https://www.yartrader.com`
* **Target Server IP**: `5.102.37.180`
* **Internal Binding**: `127.0.0.1:8000` (FastAPI Uvicorn)
* **Reverse Proxy**: Nginx listening on port 80/443 (Upstream `127.0.0.1:8000`)
* **Process Supervisor**: `systemd` (`scripts/yartrader.service`)
* **Storage Root Isolation**: `TradeYarStorageRoot` (`/tmp/YarTraderAI` on Linux, `C:\YarTraderAI` on Windows)

---

### Final Gate Status

```text
PASS WITH DOCUMENTED ENVIRONMENT LIMITATION (BLOCKED — Cloudflare Account Access)
```

#### Verification Distinction Summary
* **CODE VERIFIED**: **PASS (100%)** — All code changes, crash isolation handlers, `/health` and `/ready` endpoints, CORS production domain restrictions, systemd unit scripts, and unit/integration tests pass cleanly.
* **PRODUCTION VERIFIED**: **BLOCKED — Cloudflare Account Access Required** — Live external DNS/Cloudflare proxy mutation and live VPS systemctl service installation cannot be executed directly inside the non-root Linux sandbox container.

---

## 1. Production Domain Strategy

* **Canonical Domain**: `https://yartrader.com`
* **Secondary Domain**: `https://www.yartrader.com` (Redirects 301 to `https://yartrader.com`)
* **URL Construction**: All internal API routing constructs relative or origin-relative URLs (`/api/...`). Zero production URLs point to `localhost`, `127.0.0.1`, or `vercel.app`.

---

## 2. Vercel Cleanup Audit

* **Obsolete Dependencies Purged**: Deleted `vercel.json` and `trader-terminal/vercel.json` configuration files.
* **Environment Variables Cleaned**: Purged `VERCEL_URL` and `NEXT_PUBLIC_VERCEL_URL` from runtime dependencies.
* **Current State**: YarTrader production deployment does not depend on Vercel or any third-party static CDN.

---

## 3. Reverse Proxy & Network Architecture

```text
Internet
   │
Cloudflare CDN (Universal SSL / Full SSL / HSTS / DDoS Guard)
   │ (HTTPS)
Server Public IP: 5.102.37.180
   │
Nginx Reverse Proxy (Port 80/443)
   │ (Passes Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto)
FastAPI Application (127.0.0.1:8000)
```

### Security Controls
* **Port Exposure**: Port `8000` is bound strictly to `127.0.0.1` and is **NOT** publicly exposed.
* **CORS**: Restricted strictly to `https://yartrader.com` and `https://www.yartrader.com` (alongside `http://localhost:3000` and `http://127.0.0.1:5173` for local development).
* **Live Safety Lock**: `LIVE_TRADING_ENABLED=False` hard-locked repository-wide.

---

## 4. FastAPI Runtime Crash Investigation & Startup Hardening

### Previous Issue
Unwrapped background worker polling loops (`run_research_background_loop`, `ResearchWorker`, `ShadowWorker`) crashed when encountering network timeouts or MetaTrader 5 process disconnects. When unhandled in background threads, process instability ensued.

### Root Cause Remediation
1. **Top-Level `BaseException` Isolation**: Wrapped thread execution loops in `while True` with outer `try...except BaseException` handlers, capturing full stack tracebacks with `traceback.format_exc()` into `TradeYarStorageRoot/Logs/error/`.
2. **Non-Blocking Lifespan Context**: Hardened `lifespan_context(app: FastAPI)` in `src/Application/Services/web_dashboard.py` so that startup initialization errors never crash or block Uvicorn from serving HTTP requests.

---

## 5. Health & Readiness Endpoint Contracts

### `GET /health` Payload
```json
{
  "status": "healthy",
  "runtime": "production",
  "api": true,
  "workers": true,
  "service": "YarTrader",
  "mt5": "Disconnected",
  "intelligence": "Ready",
  "worker": "Running",
  "shadow_trading": "Active"
}
```

### `GET /ready` Payload
```json
{
  "status": "READY",
  "runtime": "production",
  "ready": true,
  "api": true,
  "workers": true
}
```

---

## 6. Process Supervision (`systemd`)

Systemd unit configuration file created at `scripts/yartrader.service`:

```ini
[Unit]
Description=YarTrader Production Runtime & Cognitive Management API Service
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=yartrader
Group=yartrader
WorkingDirectory=/var/www/yartrader
Environment="PATH=/var/www/yartrader/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/var/www/yartrader"
Environment="YARTRADER_ENV=production"
Environment="TRADEYAR_ENV=production"
Environment="LIVE_TRADING_ENABLED=False"
Environment="PORT=8000"
ExecStart=/var/www/yartrader/.venv/bin/uvicorn src.Application.Services.web_dashboard:app --host 127.0.0.1 --port 8000 --workers 2 --log-level info
Restart=always
RestartSec=5s
LimitNOFILE=65536

ProtectSystem=full
ProtectHome=read-only
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

---

## 7. Regression Test Results

```text
============================== 130 passed in 64.41s ==============================
```

Tests executed:
* `tests/runtime/test_health_status.py`: 2 passed
* `tests/runtime/test_health_endpoint.py`: 8 passed
* `tests/YarTrader.Tests/Dashboard/test_dashboard.py`: 120 passed

---

## 8. Summary Checklist

- [x] Canonical domain strategy (`https://yartrader.com`) implemented
- [x] Obsolete Vercel files (`vercel.json`) deleted
- [x] CORS restricted to `https://yartrader.com` and `https://www.yartrader.com`
- [x] Background worker crashes isolated with top-level `BaseException` handlers
- [x] `/health` and `/ready` endpoints verified
- [x] Systemd service configuration created (`scripts/yartrader.service`)
- [x] Log storage paths isolated to `TradeYarStorageRoot`
- [x] 130/130 targeted runtime tests passed cleanly
- [x] Distinction between `CODE VERIFIED` and `PRODUCTION VERIFIED` documented
