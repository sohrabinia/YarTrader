# RG_V3_AI API Guide

## 1. Gateway & Endpoints
The platform exposes versioned and token-authorized endpoints via `ServiceOrchestrator`:
* **Health Metrics**: `GET /v1/health` yields Production diagnostics checks.
* **Telemetry Performance**: `GET /v1/metrics` yields request stats and Performance Metrics summaries.
* **Passive Intelligence**: `POST /v1/intelligence` yields passive sentiment evaluation.
* **Dashboard Subsystems**:
  - `/v1/dashboard/overview` yields global health and compliance audits.
  - `/v1/dashboard/agents` yields active agent workloads and reliability.
  - `/v1/dashboard/decisions` yields decision trace histories.
  - `/v1/dashboard/providers` yields data provider connection latencies.
  - `/v1/dashboard/demo` yields demo execution status.
  - `/v1/dashboard/shadow` yields active shadow mode session metrics.

---

## 2. API Security Schema
- **Token Authorization**: Scopes like `read` are audited on request handles.
- **Middleware Validation**: Request payloads are scanned; if keywords like `place_order` or `execute_trade` exist, the request is immediately rejected with HTTP 400.
