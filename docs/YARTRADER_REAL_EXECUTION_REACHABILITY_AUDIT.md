# YarTrader Real Execution Reachability Audit

## 1. Executive Conclusion

Audit conclusion:

**PRODUCTION REAL-BROKER EXECUTION: ISOLATED**

The active Windows Service production runtime, `ResearchWorker`, `ShadowWorker`, and verified web API paths do not reach the real broker execution path ending in MetaTrader5 `mt5.order_send()`.

No production source-code modifications were made as part of this audit.

### Important Qualification:

The repository contains a dormant `RealMT5BrokerAdapter` implementation and an implementation of `mt5.order_send()`. Their existence is explicitly acknowledged. This audit establishes that they are not reachable from the verified active production runtime paths.

---

## 2. Platform Real Execution Reachability Classification

| Architecture Subsystem | Active Status | Execution Capability | Reachability Verdict |
| :--- | :--- | :--- | :--- |
| **Active Production Runtime** | Running (`YarTraderServiceHost`) | `READ_ONLY_RESEARCH + SHADOW_EXECUTION` | Verified Connected |
| **Research Worker (`ResearchWorker`)** | Active Loop | Market Data Fetching + Research Features | `READ_ONLY` |
| **Shadow Worker (`ShadowWorker`)** | Active Loop | Virtual Paper Trading Engine ($1,000 Paper) | `SIMULATION_ONLY` |
| **Web Dashboard APIs (`web_dashboard.py`)** | Active REST Server | Health, Analytics, Paper Reporting | `READ_ONLY / VIRTUAL` |
| **Real Broker Adapter (`RealMT5BrokerAdapter`)** | In Codebase | Native MT5 Terminal `order_send()` | `DORMANT_CODE / UNREACHABLE` |
| **MT5 Order Send (`mt5.order_send()`)** | In Codebase | Broker Order Submission | `DORMANT_CODE / UNREACHABLE` |
| **Demo Execution Path (`/api/demo/run`)** | Scenario Runner | Mock Harness / Isolated Demo Runner | `DEMO / SIMULATION ONLY` |

---

## 3. Call-Graph & Execution Path Forensic Analysis

### 3.1 Active Production Service Host Loop
- **Entrypoint**: `app/workers/service.py` (`YarTraderServiceHost`)
- **Instantiated Components**:
  1. `ResearchWorker` (`app/workers/research_worker.py`):
     - Periodically invokes `ResearchRuntime.run_once()`.
     - Uses `MT5Provider` in read-only mode to fetch rates/bars via `copy_rates_from_pos`.
     - Zero references to `IBrokerAdapter`, `RealMT5BrokerAdapter`, or `send_order_to_broker()`.
  2. `ShadowWorker` (`app/workers/shadow_worker.py`):
     - Periodically invokes `ShadowTradingEngine.tick_update()`.
     - Manages internal paper account balance and virtual position P&L in memory.
     - Zero references to `IBrokerAdapter`, `RealMT5BrokerAdapter`, or `mt5.order_send()`.
  3. `FastAPI Server` (`src/Application/Services/web_dashboard.py`):
     - Exposes REST routes for dashboard telemetry, health checks, and paper report summaries.
     - Does not bind `RealMT5BrokerAdapter` into any dependency injection container or route handler.

### 3.2 Dormant Real Broker Adapter Reachability
- **Source Location**: `src/Execution/Adapters/mt5_adapter.py` (`RealMT5BrokerAdapter`)
- **Method**: `send_order_to_broker(request: OrderRequest) -> OrderResponse`
- **Audit Findings**:
  - `RealMT5BrokerAdapter` is defined in `src/Execution/Adapters/mt5_adapter.py`.
  - References exist strictly in:
    1. Isolated stand-alone validation scripts (`scripts/run_mt5_forward_observation.py`, `scripts/run_real_mt5_demo_e2e.py`, `scripts/run_mt5_demo_forward.py`).
    2. Unit test suites (`tests/YarTrader.Tests/Execution/test_real_mt5_adapter.py`, `tests/YarTrader.Tests/Execution/test_mt5_demo_forward_safety.py`).
  - Active runtime workers and web server instances never instantiate or call `RealMT5BrokerAdapter.send_order_to_broker()` during regular production execution.

---

## 4. SRE Safety Gate & Hard Boundary Isolation

1. **Safety Gate Verification**:
   - `MetaTraderSafetyGate` in `src/Execution/Safety/safety_gate.py` enforces fail-closed checks.
   - Any attempt to invoke live execution throws `ValidationException: SRE Safety Gate Violation: Real Live trading is strictly disabled repository-wide`.
2. **Environment Boundary**:
   - Production setting `LIVE_TRADING_ENABLED=False` hard-blocks real order placement across all adapters.
3. **Account / Server Isolation**:
   - Even in demo execution scripts, operations are restricted to DEMO account `52961173` on `Alpari-MT5-Demo` under `trade_mode == 0`.

---

## 5. Audit Verification Sign-Off

```text
================================================================================
YARTRADER REAL EXECUTION REACHABILITY AUDIT CERTIFICATION
================================================================================

PRODUCTION REAL-BROKER EXECUTION: ISOLATED

Classification Summary:
- Active Production Runtime: READ_ONLY_RESEARCH + SHADOW_EXECUTION
- Real Broker Adapter (`RealMT5BrokerAdapter`): DORMANT_CODE / UNREACHABLE
- MetaTrader5 Order Placement (`mt5.order_send()`): DORMANT_CODE / UNREACHABLE
- Demo Execution Engine: DEMO/SIMULATION ONLY

Audit Verdict: GO / VERIFIED ISOLATED ✅
================================================================================
```
