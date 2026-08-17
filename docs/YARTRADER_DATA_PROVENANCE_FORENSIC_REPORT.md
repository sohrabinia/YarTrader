# YARTRADER V1.0 DATA PROVENANCE FORENSIC REPORT

## Executive Summary
This document provides a forensic audit tracing the origins of marketing metric claims and pattern occurrence figures in YarTrader V1.0.

---

## 1. Metric Audit Findings

### Claim 1: "Simulated Historical Trades 125.4k+"
- **Source Code Location**: `src/Application/Services/web_dashboard.py` (line 2300)
- **Origin**: Static UI string (`<div id="pub-trades" class="status-val">125k+</div>`).
- **Data Provenance**: **STATIC / DEMO SEED**
- **Forensic Assessment**: The figure represents a marketing projection claim rather than a real-time database query count from active database tables.

### Claim 2: "Pattern Occurrences / Learning Matrix (312 Occurrences)"
- **Source Code Location**: `src/Application/Services/web_dashboard.py` (line 3131)
- **Origin**: Dynamically aggregated from `PredictiveShadowEngine.get_instance().patterns`. Fallback baseline records are seeded when in-memory engine patterns list is empty.
- **Data Provenance**: **DYNAMIC HYBRID (REAL RUNTIME WHEN ACTIVE / SEEDED FALLBACK WHEN IDLE)**
- **Forensic Assessment**: When backtest runs or shadow trades execute, outcomes log into `runtime_logs/learning_memory.json`, dynamically populating the learning matrix. When idle or freshly started, fallback baseline templates seed the UI table.

---

## 2. Summary Provenance Classification

| Metric | Source Code Location | Provenance Type | Runtime Data File |
| :--- | :--- | :--- | :--- |
| **Simulated Trades (125k+)** | `src/Application/Services/web_dashboard.py` | **STATIC DEMO SEED** | N/A |
| **Active Markets (30/30)** | `/api/public/metrics` | **DYNAMIC REAL** | `config/system_limits.yaml` |
| **Platform Uptime (99.9%)** | `/api/public/metrics` | **DYNAMIC REAL** | `server_watchdog.py` |
| **Learning Matrix Patterns** | `/api/intelligence/learning-matrix` | **DYNAMIC RUNTIME (WITH FALLBACK)** | `runtime_logs/learning_memory.json` |
