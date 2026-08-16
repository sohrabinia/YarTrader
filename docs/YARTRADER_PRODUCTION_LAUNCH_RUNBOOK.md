# YARTRADER PRODUCTION LAUNCH RUNBOOK

## Executive Overview
This operational runbook provides step-by-step Site Reliability Engineering (SRE) procedures for launching, managing, and maintaining YarTrader in public production environments.

---

## 1. System Requirements & Environment

### Operating System & Dependencies
- **OS**: Linux (Ubuntu 22.04 LTS recommended) or Windows Server 2022.
- **Python**: Python 3.12+ with virtual environment under `.venv/`.
- **Node.js**: Node.js v22+ and npm v10+.
- **MetaTrader 5**: MT5 Terminal (Windows host for native C-API bridge, synthetic sandbox fallback on Linux).

### Environment Configuration
Ensure `.env.production` is present in the repository root:
```env
YARTRADER_ENV=production
YARTRADER_PORT=8000
YARTRADER_HOST=0.0.0.0
LIVE_TRADING_ENABLED=False
YARTRADER_SECRET_KEY=<SECURE_RANDOM_256_BIT_KEY>
YARTRADER_JWT_ALGORITHM=HS256
```

---

## 2. Pre-Deployment & Build Steps

### Step 1: Install Python Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest uvicorn fastapi
```

### Step 2: Build Frontend Assets
```bash
cd trader-terminal
npm install
npm run build
cd ..
```
Verify that `trader-terminal/dist/index.html` and `trader-terminal/dist/assets/` are generated.

---

## 3. Production Service Launch

### Option A: Standard FastAPI / Uvicorn Process
```bash
source .venv/bin/activate
uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000 --workers 4
```

### Option B: Windows Service Execution
To deploy as a native Windows Service via SCM:
```powershell
.\scripts\install_service.ps1
.\scripts\start_service.ps1
```

---

## 4. Health Probes & Monitoring

YarTrader exposes four automated SRE health check probes:
- `GET /health` - Production health status & subsystem summary.
- `GET /health/live` - Liveness probe (returns HTTP 200 `{"status": "OK"}`).
- `GET /health/ready` - Readiness probe verifying FastAPI, read-only MT5 link, and memory layer integrity.
- `GET /v1/health` - Telemetry diagnostics report.

---

## 5. Backup & Recovery Operations

### Automated Backup
To generate an isolated system snapshot:
```bash
python3 -c "from src.Application.Runtime.backup_manager import BackupManager; bm = BackupManager(); print(bm.create_backup())"
```
Or via Admin REST API:
```bash
curl -X POST "http://localhost:8000/api/admin/backup?token=<ADMIN_TOKEN>"
```

### Disaster Recovery
To restore from a backup archive:
```bash
python3 -c "from src.Application.Runtime.backup_manager import BackupManager; bm = BackupManager(); print(bm.restore_latest())"
```

---

## 6. Safety Gate & Incident Management

### Safety Gate Locks
- Real Live Trading execution paths are hard-disabled in `MetaTraderSafetyGate`.
- Any unauthorized live order request triggers an SRE security exception (`ValidationException`).

### Emergency Stop
To trigger an immediate system-wide emergency halt:
```bash
curl -X POST "http://localhost:8000/api/risk/emergency_stop"
```

---

## 7. Verification Checklist
- [x] All 1,530+ backend tests passing (`python3 validate_release.py`).
- [x] Frontend React SPA compiled cleanly under `trader-terminal/dist/`.
- [x] Read-only MT5 provider link verified.
- [x] Fail-closed `MetaTraderSafetyGate` active (`LIVE_TRADING_ENABLED=False`).
- [x] Health probes `/health`, `/health/live`, `/health/ready` reporting healthy.
