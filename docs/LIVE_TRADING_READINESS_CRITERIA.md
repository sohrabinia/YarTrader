# Live-Trading Readiness Criteria — Version 3.1 (Hardened)
## TradeYar AI — Live Transition Policy & SRE Checkgate Requirements

This document outlines the strict technical, risk, and operational checkgate criteria that MUST be satisfied prior to transitioning any future release of TradeYar AI from simulation/shadow mode into live-trading execution.

> **CRITICAL ARCHITECTURAL DIRECTIVE:** Under APES-FIN simulation constraints, active live-trading is strictly disabled. No live broker execution or order placement occurs in this version. This document serves as a compliance policy framework for future validation gates.

---

## 1. Multi-Stage Operational Checkgates

A transition to live-trading is strictly prohibited unless the system passes through three rigorous operational gates:

### Gate A: Continuous Stability Validation (72-Hour Stress Test)
* **Threshold:** The complete system must run uninterrupted for a minimum of 72 continuous hours in Shadow Mode without:
  - Any unhandled exceptions or critical thread crashes.
  - State degradation (remaining in `HEALTHY` state throughout).
  - Memory usage growth exceeding 5% post-initialization (verifying no slow memory leaks).
  - API endpoint response latencies exceeding 200ms.

### Gate B: Connection Reliability & Network Resiliency
* **Threshold:** The read-only MetaTrader 5 polling link must demonstrate robust reconnection and automated gap backfilling.
  - Under simulated network drops, the system must transition automatically to `DEGRADED` status within 15 seconds.
  - Upon reconnection, it must backfill missing historical candles and recover to `HEALTHY` status in less than 30 seconds with **Zero Data Gaps**.

### Gate C: Statistical Learning & Memory Consistency
* **Threshold:** Re-evaluate top 10 historical patterns against chronological out-of-sample data.
  - The continuation/reversal win-rate divergence between historical training and out-of-sample test datasets must remain **below 15%**.
  - Any pattern showing performance degradation beyond 15% must be flagged as `UNRELIABLE_CONFIDENCE` and excluded from active decision consideration.
  - Any active patterns must have a minimum sample size of 10 validated occurrences (`SUFFICIENT_SAMPLE`).

---

## 2. Hard Risk & Exposure Controls

Before a live environment is connected, the following parameters must be hardcoded and locked inside the Configuration Manager:

1. **Max Capital Allocation:** Maximum single-asset allocation locked to **1.0%** of total virtual account balance.
2. **Max Volatility Exposure:** Expected annualized portfolio volatility capped at **20.0%**.
3. **Emergency Stop Halt:** An automated endpoint `POST /api/risk/emergency_stop` must immediately halt all background research loops, cancel active monitoring, and set the system into a lock-down `HALTED` state.
4. **Independent Judge Approval:** No trade hypothesis can be approved without the `JudgeBrain` verifying that the decision is backed by reasonable, non-lucky historical evidence with a reasoning quality score $> 0.75$.

---

## 3. DevOps Monitoring & SRE Incident Management

The SRE layer must be configured to active alerting:
- **Server Watchdog:** The `server_watchdog.py` process must run continuously, monitoring resource thresholds and enforcing a maximum of **5 restarts per 10 minutes** before entering absolute lock-down and alerting.
- **Telegram Notifications:** Simulated `[CRITICAL_CRASH]` or `[CRITICAL_MEMORY_PROTECTION]` triggers must immediately alert administrators with a strict 5-minute suppression cooldown to avoid alarm fatigue.
- **Transaction Protection:** All state modifications must be validated on write using temp-swap atomic replacement to guarantee zero database corruption.
- **Continuous Audit:** Every single state or setting modification must be written to `logs/audit/audit.log` for post-incident investigation.
