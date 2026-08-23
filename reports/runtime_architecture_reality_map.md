# YarTrader v7 Runtime Architecture Reality Map

**Document ID:** `YARTRADER-RUNTIME-REALITY-MAP-v7.0`
**Date:** August 23, 2026
**Status:** `AUTHORITATIVE AUDIT`

---

## 🏛️ RUNTIME OWNERSHIP & PORT MATRIX

| Component | Real Location | Start Command / Process | Port | Status | Owner |
|---|---|---|---|---|---|
| **FastAPI Backend Web Application** | `src/Application/Services/web_dashboard.py` | `python3 -m app.main` or Uvicorn WSGI | `8000` | `STOPPED (Standalone Script Mode Active)` | SRE Team |
| **Vite Frontend Dev Server** | `trader-terminal/` | `npm run dev -- --port 5173` | `5173` | `STOPPED` | Frontend Team |
| **HTTP Static Distribution Server** | `trader-terminal/dist/` | `python3 -m http.server 3000` | `3000` | `RUNNING (PID 415829)` | Jules Verification |
| **Research Background Worker** | `app/workers/research_worker.py` | `ResearchWorker.start()` | N/A | `IMPLEMENTED` | Intelligence Engine |
| **Predictive Shadow Engine** | `src/ShadowTrading/Engine/PredictiveShadowEngine.py` | Service Dependency | N/A | `HEALTHY` | Shadow Module |
| **MetaTrader 5 DEMO Adapter** | `src/Execution/Adapters/mt5_adapter.py` | IPC Bridge | N/A | `DISCONNECTED (Linux Container)` | Execution Bridge |

---

## ⚙️ PROCESS & SERVICE AUDIT

```text
PID: 415829
Command: /home/jules/.pyenv/versions/3.12.13/bin/python3 -m http.server 3000 --directory trader-terminal/dist
Port: 3000
Branch: jules-2643415784252836856-b8011498
HEAD SHA: 3fef729012a60b2171d2df7b46afdd57a4e7e9b3
```
