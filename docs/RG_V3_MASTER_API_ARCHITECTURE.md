# RG_V3 Master API Architecture

This document outlines the REST API structure, versioned endpoints, DTO contracts, validation middleware, and auth abstractions of **Phase 26 API & Service Architecture**.

---

## 1. REST Endpoint Specifications

All endpoints are strictly read-only and versioned under `v1`:

### `GET /v1/health`
Retrieves platform status indicators, connection counts, and terminal health.
*   **Response DTO**:
    ```json
    {
      "status": "Healthy",
      "system_time": "2023-11-22T12:00:00"
    }
    ```

### `GET /v1/metrics`
Retrieves cumulative telemetry stats, error frequencies, and query counters.

### `POST /v1/intelligence`
Queries compiled sentiment and confidence values for a target asset.
*   **Request DTO**:
    ```json
    {
      "client_id": "client_1",
      "token": "secret_token_1",
      "payload": {
        "asset": "BTCUSD"
      }
    }
    ```
*   **Response DTO**:
    ```json
    {
      "status_code": 200,
      "data": {
        "asset": "BTCUSD",
        "sentiment": "bullish",
        "confidence_score": 0.88,
        "compiled_at": "2023-11-22T12:00:00"
      }
    }
    ```

---

## 2. Validation & Security Middleware

Every API endpoint is protected by:
1.  **Authentication/Authorization Checks**: abstraction validation against local databases and permissions.
2.  **Keyword Scanners Middleware**: Intercepts request JSON payloads and rejects requests featuring forbidden execution terms (`order`, `position`, `broker`, `execute`, `buy`, `sell`) with status `400 Bad Request`.
