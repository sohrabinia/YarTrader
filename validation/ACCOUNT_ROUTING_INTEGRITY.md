# YARTRADER ACCOUNT ROUTING INTEGRITY

This document establishes the verified rules, validations, and environment locks preventing cross-contamination between Live and Demo accounts.

---

## 1. ENVIRONMENTAL ROUTING LOCKS
* **No Fallback Contamination:** The Account Router strictly forbids any sequential or automatic fallback from Live to Demo, or Demo to Live. If an environment mismatch or connection loss occurs, the router immediately **fails closed** and throws an exception, terminating the execution loop.
* **Risk Engine Isolation:** Daily risk budgets and position sizing calculations are tracked independently per account ID, guaranteeing that Demo practice runs do not exhaust the Live execution risk boundaries.
* **Symbol and Timeframe Validation:** All symbols and timeframe requests are validated against `config/system_limits.yaml` (unified 30 active symbols ceiling) prior to routing, preventing out-of-bounds resources.
