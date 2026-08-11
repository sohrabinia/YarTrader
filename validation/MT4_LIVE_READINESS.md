# YARTRADER MT4 LIVE READINESS REPORT

This document audits the MT4 Live broker integration readiness and production execution constraints.

---

## 1. MT4 CONNECTOR READINESS
* **Implementation Status:** **READY_WITH_LIMITATIONS** (The client adapter and account-agnostic routing structures are fully compiled and configured, but actual live order routing is globally disabled for safety).
* **Live Safety Guard:** Deactivated by default under `LIVE_EXECUTION = DISABLED`.
* **Daily Risk Policy:** Strictly capped at **2% maximum daily loss** enforced server-side.
* **SL/TP Semantics:** Predefined Stop Loss (SL) and Take Profit (TP) parameters are mandatory and must accompany every execution signal candidate, preventing open-ended risk exposure.
