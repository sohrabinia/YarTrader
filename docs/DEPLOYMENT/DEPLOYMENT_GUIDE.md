# YarTrader Deployment Guide

## 1. Production Configuration variables
Deployments are structured and validated using `ProductionConfig` settings:
* **RG_ENV**: Current running environment (`production`, `staging`, `development`).
* **RG_LOOKBACK_DAYS**: Sliding lookback history window (1 to 365 days).
* **RG_API_TIMEOUT**: Global HTTP timeout limits (0.1s to 60.0s).
* **RG_MAX_RETRIES**: Max connection retries (0 to 10).
* **RG_LOG_LEVEL**: Log level filter (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

---

## 2. Structured JSON Logging Schema
Logs are formatted into single-line structured JSON objects for ingestion by FluentBit or Loki:
```json
{
  "timestamp": "2026-03-01T12:00:00.123456",
  "service": "YarTrader",
  "level": "INFO",
  "event": "PipelineExecutionCompleted",
  "metadata": {
    "duration_ms": 125.4,
    "asset": "EURUSD"
  }
}
```

---

## 3. Disaster Recovery checklist
1. Verify the network isolation sandbox is intact (simulation-mode only).
2. Fetch encrypted database tokens from `SecretsVault`.
3. Confirm backup restore frequencies are healthy.
4. Restart services with standard non-trading profile.
