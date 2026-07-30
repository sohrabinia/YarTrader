# TradeYar AI — Live Operations Monitoring Plan (RC-1)
**Date:** July 30, 2026
**Auditor:** Principal Software Architect & QA Lead
**Audit Phase:** Production Readiness Planning (Pure Verification — NO CODE CHANGES)

---

## 1. Introduction
This **Monitoring Plan** establishes the live metrics telemetry and monitoring procedures required to track **TradeYar AI RC-1** system and cognitive pipeline health under long-term operational environments. It defines structured alert metrics, diagnostic schemas, and health checks.

---

## 2. Telemetry and Operational Metrics
Operational telemetry is exposed via standard REST endpoints and divided into four categories:

### A. Core System Health Metrics
* **Endpoint:** `/v1/health`
* **Target Metrics:**
  - `status`: Overall system status (`Healthy` \| `Degraded`).
  - `reported_at`: Standard ISO timestamp.
  - `apes_fin_compliant`: Confirming 100% read-only boundaries.
  - `active_threads_count`: Active system thread count.

### B. Runtime Metrics
* **Endpoint:** `/v1/metrics`
* **Target Metrics:**
  - `pipeline_latency_ms`: Speed of research/analysis cycle.
  - `api_response_ms`: Average latency of REST queries.
  - `memory_used_mb`: Active RAM usage of process.
  - `thread_count`: Active background daemon counts.

### C. Brain & Cognitive Pipeline Health Metrics
* **Endpoint:** `/api/research/health`
* **Target Metrics:**
  - `mt5_status`: Physical MetaTrader 5 socket connection status (`ONLINE` \| `DISCONNECTED`).
  - `worker_running`: Verification that background polling daemon thread is alive.
  - `cycle_count`: Integer of successful analysis polling iterations.
  - `last_successful_cycle`: Timestamp of last compiled research snapshot.
  - `last_error`: Trace string of last captured recovery exception.

### D. Replay & Simulation Metrics
* **Endpoints:** `/api/replay/training-monitor`, `/api/replay/learning-status`, `/api/replay/error-analysis`
* **Target Metrics:**
  - `progress_pct`: Training episode playback progress percentage.
  - `concepts_count`: Approved Concepts count in Concept Memory.
  - `patterns_discovered`: Footprint structures registered in Pattern Memory.
  - `patterns_rejected`: Number of corrupted or low-evidence structures blocked by `LearningIntegrityService`.
  - `decision_quality_trend`: List representing decision score improvement across episodes.

---

## 3. Operations Monitoring Dashboard
The built-in bilingual System Validation Center SPA serves as the primary visual control room for monitoring.

```text
┌────────────────────────────────────────────────────────┐
│                      MONITORING SPA                    │
├───────────────────────────┬────────────────────────────┤
│   Live Research Panel     │   Subsystem Health Cards   │
│   - Bias (Bullish/Bearish)│   - System Health (Healthy)│
│   - Confidence (78%)      │   - MT5 Status (Simulation) │
│   - Indicators (SMA/RSI)  │   - Security (Verified)    │
├───────────────────────────┴────────────────────────────┤
│   Live Trace Logs Console                              │
│   - [INFO] Loading snapshots...                        │
│   - [INFO] Running automated release tests...          │
└────────────────────────────────────────────────────────┘
```

---

## 4. Operational Alerting Policy & Escapes

To support 24/7 continuous runs, we define the following alerting thresholds and recommended actions:

### Threshold 1: MT5 Connection Link Down
* **Condition:** `/api/research/health` reports `mt5_status: DISCONNECTED` for more than 5 consecutive minutes.
* **Alert Level:** Warning.
* **Operational Action:** Ensure the MetaTrader 5 terminal application is running on the host system, and verify login credentials/broker IP configurations.

### Threshold 2: Background Polling Worker Stalled
* **Condition:** `last_successful_cycle` has not updated for more than 10 minutes.
* **Alert Level:** Critical.
* **Operational Action:** Execute process restart procedure. The atomic swap persistence guarantees that the system will reload previous baseline records cleanly without loss.

### Threshold 3: Memory Creep Threshold
* **Condition:** `memory_used_mb` exceeds `250.0 MB`.
* **Alert Level:** Warning.
* **Operational Action:** Execute process restart procedure during market close periods to clean python GC buffers.
