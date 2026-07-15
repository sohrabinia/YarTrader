# TradeYar AI API and Service Architecture Integration Guide

This guide documents the Service Layer, DTO (Data Transfer Object) structures, and REST Endpoint routing for future integrations.

## 1. DTO Boundaries & Decoupling
To enforce APES-FIN decoupling principles, the API service layer operates exclusively via immutable Data Transfer Objects, preventing direct domain model exposure:
- **ServiceRequestDTO**: Input parameters (client credentials, authorization tokens, payload dictionary).
- **ServiceResponseDTO**: Output metrics (status codes, structured data outputs, clean error summaries).

## 2. Versioned Read-Only REST Endpoints
Endpoints are prefix-versioned and support non-trading analytics querying:

### `/v1/health`
- **Purpose**: Comprehensive platform diagnostics check and uptime tracking.
- **Output**: JSON payload representing readiness states (READY, WARNING, FAILED) across all subsystems.

### `/v1/metrics`
- **Purpose**: Diagnostic performance telemetry and latency metrics.
- **Output**: JSON summaries of average execution speeds (pipeline execution, feature extraction, decision latency).

### `/v1/intelligence`
- **Purpose**: Generates passive analytical observations on selected financial instruments.
- **Payload**: `{ "asset": "EURUSD" }`

### `/v1/dashboard/overview`
- **Purpose**: System-wide operations status monitor dashboard aggregations.

### `/v1/dashboard/demo`
- **Purpose**: Execution stats and timeline steps of the End-to-End Demo platform.
