# TradeYar AI — Background Worker Health Report

This report presents the operational health, startup parameters, thread statuses, and service orchestration parameters of TradeYar AI's background worker squad.

---

## 🚦 Background Worker Squad Status

| Worker Name | Thread Name | Central State key | Status (SCM Service) | Status (Dev Web Mode) | Purpose / Pipeline coupling |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Research Worker** | `ResearchWorker` | `research_status` | **Healthy / Running** | **Running** (ensure_worker_started) | Runs periodic multi-timeframe analytical research loop on active symbol matrix. |
| **Intelligence Worker** | `IntelligenceWorker`| `intelligence_status` | **Healthy / Running** | **Stopped / Idle** | Runs persistent cognitive learning experience promotions and memory validation loop. |
| **Shadow Trading Worker**| `ShadowWorker` | `shadow_status` | **Healthy / Running** | **Stopped / Idle** | Runs simulated tick aggregations and Virtual Position TP/SL trigger checks. |

---

## 🔍 Investigation: Intelligence Worker Status
In development/standalone web mode (run purely via `uvicorn src.Application.Services.web_dashboard:app`), the `IntelligenceWorker` is set to `Stopped`. This is a **fully intentional, design-by-specification behavior** to prevent database file race conditions and thread leakage when testing or running standalone APIs.

When deployed in production, the entire application is run under the **TradeYar-AI Windows Service Host** (`TradeYarAIServiceHost` in `app/workers/service.py`), which orchestrates and boots all background workers sequentially:
1. Research Worker (`self.research_worker.start()`)
2. Intelligence Worker (`self.intelligence_worker.start()`)
3. Shadow Trading Worker (`self.shadow_worker.start()`)

This ensures thread-safe, centralized, and secure lifecycle management across the whole platform.

---

## ✅ SRE Validation & Safeguards
- **Zero Thread Leakage**: All workers run as standard Python `daemon=True` threads.
- **State Integration**: Workers write their status and heartbeats to `central_runtime_state` which integrates seamlessly with FastAPI's `/health` diagnostics.
