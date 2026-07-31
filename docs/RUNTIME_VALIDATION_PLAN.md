# TradeYar AI — Runtime Validation Plan & Checklist (RC-1)
**Date:** July 30, 2026
**Auditor:** Principal Software Architect, Principal Security Auditor & QA Lead
**Audit Phase:** Production Readiness Planning (Pure Verification — NO CODE CHANGES)

---

## 1. Introduction
The **Runtime Validation Checklist** defines the operational validation procedures required to certify that the **TradeYar AI RC-1** system runs safely and stably in a long-running live production environment. These tests measure performance, memory, logging bounds, and crash-recovery procedures under extended periods of execution.

---

## 2. Validation Checklist Matrix

Below is the structured checklist representing the validation targets, verification steps, and acceptable thresholds:

| Category | Target Metric | Verification Step | Acceptable Threshold |
| :--- | :--- | :--- | :--- |
| **MT5 Connection** | Connection Link Stability | Query `/api/research/health` dynamically | `mt5_status` must report `ONLINE` under active connection; connection failures must trigger fallback instantly |
| **MT5 Recovery** | Auto-Reconnection Delay | Unplug/block MT5 connection socket, monitor logs, verify automatic retry loop execution | Reconnect attempt must occur within 60.0s of socket disruption with 0 server-wide crashes |
| **Memory Usage** | Dynamic RAM Growth | Monitor memory footprint via `/v1/metrics` under continuous 12-hour polling | Total RAM consumption must remain stable at < 150.0 MB; zero memory leaks in JSON parser |
| **CPU Usage** | CPU Core Consumption | Run native system monitors (`top` / task manager) during live H1 research cycle | CPU utilization must remain < 5% on 2.0GHz core; sequential routing prevents CPU spikes |
| **Log Rotation** | Disk Storage Growth | Check sizes of files under `runtime_logs/research_snapshots/` and `logs/` folders | Max research snapshots is capped at 50 records; log files must be rotated when size > 10MB |
| **Service Recovery** | Thread Failure Self-Healing | Inject failure exception in live research thread, verify thread recovery status | State must transition to `RECOVERING`, then back to `RUNNING` within 60.0s |
| **Read-Only Lock** | Security Lock Integrity | POST forbidden trading payloads to `/api/control` and `/api/mode` | 100% of active executions must be blocked and rejected by middleware with 400 Bad Request |

---

## 3. Step-by-Step Validation Procedures

### Procedure VAL-01: 12-Hour Long-Running Health Test
* **Objective:** Ensure no memory leak or CPU creep exists in the background daemon polling worker.
* **Steps:**
  1. Boot FastAPI server and start background polling worker.
  2. Execute a continuous script that curls `/api/research/current` and `/api/research/health` once every 10 seconds.
  3. Log the response of `/v1/metrics` (or `memory_used_mb` payload) chronologically.
  4. Compare the RAM consumption at hour 1, hour 6, and hour 12.
* **Pass Criteria:** RAM growth from hour 1 to hour 12 must be `< 5.0 MB`.

### Procedure VAL-02: Connection Drop Resilience Test
* **Objective:** Verify crash-resistance when connection to MetaTrader 5 drop or server times out.
* **Steps:**
  1. Boot system with active MT5 link. Status reports `ONLINE` (`CONNECTED`).
  2. Disrupt host network or shut down local MT5 terminal application.
  3. Query `/api/research/health` and verify state changes to `DISCONNECTED` within 60 seconds.
  4. Verify that background thread does *not* exit and continues sleep loops.
  5. Restart MT5 terminal, and verify that the system automatically reconnects and state transitions back to `ONLINE` within 60 seconds.
* **Pass Criteria:** Zero process exits, zero thread terminations, and successful automatic reconnection.

### Procedure VAL-03: Security Middleware Validation Test
* **Objective:** Verify that any active trading-related parameters are immediately intercepted.
* **Steps:**
  1. Use HTTP client to post payload containing forbidden keywords (e.g. `{"command": "buy", "asset": "XAUUSD"}`) to `/v1/intelligence` or `/api/control`.
  2. Verify that the request is intercepted and rejected with HTTP `400 Bad Request`.
  3. Verify that the logged warning is captured in `logs/validation.log`.
* **Pass Criteria:** 100% rejection of active payloads.
