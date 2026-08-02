# LATENCY_THRESHOLDS.md — Latency Thresholds & State Mappings

This document defines the latency benchmarks and UI state-change triggers. All metrics are mapped from real backend telemetry responses (`GET /api/v1/health` and `GET /api/devops/metrics`).

---

## ⏱️ Latency Benchmark Limits

The UI must evaluate response speeds and assign visual system status tiers:

| Status Tier | Latency Metric (HTTP API) | Latency Metric (WebSocket) | UI Representation | Expected Client Action |
| :--- | :--- | :--- | :--- | :--- |
| **`HEALTHY`** | `< 150ms` | `< 200ms` | 🟢 Pulsating Green | Normal dashboard operations. |
| **`DEGRADED`**| `150ms - 500ms` (2x base) | `200ms - 800ms` (2x base) | 🟡 Solid Amber | Display a small header banner: *"High network latency detected. Retrying..."* |
| **`CRITICAL`**| `> 500ms` (5x base) | `> 800ms` (5x base) | 🔴 Flashing Red | Trigger network error toast. Suspend intensive chart updates to preserve memory. |

---

## 📈 SRE Diagnostic Performance Graph

The SRE Admin Console exposes an SVG-based sparkline chart displaying API response latencies over the last 60 minutes.

### Graph Rendering Parameters:
- **Baseline Line:** Represent standard healthy performance as a dotted horizontal guide line at `150ms` (`--color-success`).
- **Dynamic Plot Line:** Draw a continuous polyline plotting actual response speeds.
  - Plots falling below the 150ms guide are drawn in green.
  - Plots between 150ms and 500ms are drawn in amber.
  - Plots exceeding 500ms trigger an instant line color shift to red, with a glowing red background gradient overlay underneath.
- **Interactivity:** Hovering over any point on the sparkline charts renders a monospace tooltip detailing the exact timestamp and HTTP request path (e.g., `14:15:02 UTC - GET /api/user/signals - 42ms`).
