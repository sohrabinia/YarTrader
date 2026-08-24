# YarTrader Frontend Fake Data Audit Report

**Document ID:** `YARTRADER-MOCK-DATA-AUDIT-v1.0`
**Date:** August 23, 2026
**Status:** `AUTHORITATIVE AUDIT`

---

## 📊 MOCK DATA CLASSIFICATION MATRIX

| Component / File | Audit Search Pattern | Classification | Status & Policy |
|---|---|---|---|
| `trader-terminal/src/App.jsx` | `DATA UNAVAILABLE` | **ALLOWED** | Explicit honest fallback text rendered when API telemetry is missing. |
| `trader-terminal/src/views/DemoView.jsx` | `data={demoTrades}` | **ALLOWED** | Paper/Demo trading execution mode simulation table. |
| `trader-terminal/src/views/DashboardView.jsx` | `shadowTrades` | **ALLOWED** | Paper/Shadow execution journal visualization. |
| **Main Production Dashboard & Health Indicators** | `mock / static data` | **PROHIBITED** | Evaluates real API responses (`/health`, `/api/public/metrics`, `/api/devops/status`). Displays explicit fallback string (`DATA UNAVAILABLE`) if disconnected. |

---

## 🎯 CONCLUSION

All mock data usages are strictly confined to permitted Backtest, Demo, and Shadow paper trading execution spaces. The primary production dashboard and health indicators evaluate real API state without fake data fabrication.
