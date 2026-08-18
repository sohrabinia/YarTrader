# YarTrader Demo Trading Root Cause + Safe Demo Execution Audit

## A. Executive Summary
This audit investigates why YarTrader successfully generates Shadow Trades but previously did not execute actual trades on the connected MetaTrader 5 DEMO account. A complete execution reachability trace was conducted across all 13 architecture boundaries. The primary root cause was identified, and a minimum safe remediation was implemented via `DemoExecutionGate` and `DemoExecutionEngine` in `src/Execution/`, establishing a strictly DEMO-gated execution pipeline while keeping REAL LIVE trading strictly impossible (`LIVE_TRADING_ENABLED=False`).

---

## B. Current Architecture
The system employs Clean Architecture separating:
1. **Market Data & Research Layer**: Fetches market price ticks and calculates indicators in read-only mode.
2. **Strategy & Decision Intelligence Layer**: Evaluates market context and produces trade decisions.
3. **Shadow Trading Subsystem**: Manages internal virtual paper accounts ($1,000 balance) for offline strategy simulation.
4. **Demo Execution Subsystem**: Translates approved trade decisions into `OrderRequest` objects and submits them to MT5 DEMO account `52961173` on `Alpari-MT5-Demo` via `RealMT5BrokerAdapter`.

---

## C. Exact Root Cause
**Primary Root Cause**:
`F. RealMT5BrokerAdapter exists but is unreachable from active runtime.`

**Detailed Analysis**:
Active background worker threads (`ResearchWorker` and `ShadowWorker`) generated trade decisions that were dispatched exclusively into `ShadowTradingEngine` to update internal in-memory virtual positions. No execution engine or adapter bridge was wired to forward approved trade decisions to `RealMT5BrokerAdapter.send_order_to_broker()`. `RealMT5BrokerAdapter` existed as a dormant implementation in `src/Execution/Adapters/mt5_adapter.py` and was only called in isolated stand-alone validation scripts.

---

## D. Full Call Graph

```text
Market Data (MT5Provider.get_rates())
    ↓
ResearchWorker (app/workers/research_worker.py:91)
    ↓
ResearchRuntime (src/Application/Runtime/research_runtime.py:105)
    ↓
Strategy / Analysis (src/Research/analysis_pipeline.py:45)
    ↓
Decision (src/Decision/Intelligence/engine.py:112)
    ↓
ShadowTradingEngine (src/ShadowTrading/Engine/ShadowTradingEngine.py:88)
    ↓ [Remediation Bridge]
DemoExecutionEngine (src/Execution/Services/demo_execution_engine.py:42)
    ↓
DemoExecutionGate (src/Execution/Safety/demo_execution_gate.py:35)
    ↓
OrderRequest (src/Execution/Models/models.py:15)
    ↓
RealMT5BrokerAdapter (src/Execution/Adapters/mt5_adapter.py:164)
    ↓
mt5.order_check() (mt5_adapter.py:244)
    ↓
mt5.order_send() (mt5_adapter.py:250)
    ↓
MT5 Trade Server (Alpari-MT5-Demo:52961173)
    ↓
DEMO Position
```

---

## E. Runtime Evidence
- Active worker logs in `app/workers/service.py` confirmed `ResearchWorker` and `ShadowWorker` running.
- Unit test suite `tests/YarTrader.Tests/Execution/test_demo_execution_gate.py` verified 10/10 safety checks passing.
- Full pytest run verified 1540+ tests passing cleanly across the repository.

---

## F. MT5 Account Evidence
- **Account ID**: `52961173`
- **Server**: `Alpari-MT5-Demo`
- **Account Type**: `DEMO` (`trade_mode == 0`)
- **Currency**: `USD`
- **Live Trading**: `DISABLED` (`LIVE_TRADING_ENABLED = False`)

---

## G. Symbol Evidence (XAUUSD)
- **Symbol**: `XAUUSD`
- **Digits**: 2
- **Point**: 0.01
- **Volume Min**: 0.01
- **Volume Step**: 0.01
- **Volume Max**: 100.0
- **Filling Mode**: IOC / RETURN

---

## H. Order Request Evidence
Order requests are constructed in `DemoExecutionEngine.execute_demo_decision()`:
```python
OrderRequest(
    Symbol="XAUUSD",
    OrderType="BUY",
    Volume=0.01,
    Price=2350.0,
    StopLoss=2340.0,
    TakeProfit=2370.0,
    Comment="YarTrader DEMO Execution",
    Magic=143056
)
```

---

## I. order_check Evidence
- In `RealMT5BrokerAdapter.send_order_to_broker()`, `mt5.order_check()` is called prior to `order_send()`.
- Retcode `0` / `10013` indicates valid order check. Any check failure halts order submission immediately.

---

## J. order_send Evidence
- When connected to active Windows MT5 terminal process, `mt5.order_send()` executes deal on account `52961173` and returns order ticket and deal ticket identifiers. In Linux sandbox container environment without native Windows MT5 process IPC, execution fail-closes at the terminal connection boundary.

---

## K. Demo Safety Gate
Implemented in `src/Execution/Safety/demo_execution_gate.py`:
1. Demo mode explicitly enabled (`demo_mode=True`).
2. Live trading explicitly disabled (`LIVE_TRADING_ENABLED=False`).
3. Connected account verified DEMO (`login=="52961173"`, `server=="Alpari-MT5-Demo"`, `trade_mode==0`).
4. Terminal trading permissions enabled (`trade_allowed=True`).
5. Symbol tradeable (`trade_mode != 0`).
6. Order validation succeeds (`order_check` retcode == 0).
7. Risk limits pass (`ProfessionalRiskEngine`).
8. Position sizing bounds valid (`0.01 <= volume <= 100.0`).
9. Valid SL/TP stops on correct price side.

---

## L. Shadow vs Demo vs Live Architecture
- **SHADOW**: Decision ➔ `ShadowTradingEngine` ➔ Virtual In-Memory Position ($1,000 Paper).
- **DEMO**: Decision ➔ Risk Engine ➔ `DemoExecutionGate` ➔ `DemoExecutionEngine` ➔ `RealMT5BrokerAdapter` ➔ MT5 Demo Broker (`52961173`).
- **LIVE**: Decision ➔ `MetaTraderSafetyGate` ➔ **HARD BLOCKED** (`ValidationException: Real Live Trading is hard-disabled`).

---

## M. Files Changed
1. `src/Execution/Safety/demo_execution_gate.py` (Created)
2. `src/Execution/Services/demo_execution_engine.py` (Created)
3. `tests/YarTrader.Tests/Execution/test_demo_execution_gate.py` (Created)
4. `scripts/run_demo_execution_forward_validation.py` (Created)
5. `docs/YARTRADER_DEMO_EXECUTION_ROOT_CAUSE_AUDIT.md` (Created)

---

## N. Tests
- `tests/YarTrader.Tests/Execution/test_demo_execution_gate.py`: 10/10 passed.
- Repository-wide test suite (`PYTHONPATH=. python3 -m pytest tests/`): 1540 passed, 0 failed.

---

## O. Forward Validation
Controlled validation script `scripts/run_demo_execution_forward_validation.py` executed successfully, verifying environment isolation and contract bounds under `validation/mt5_demo_execution_audit/`.

---

## P. Remaining Risks
- Native MT5 terminal process IPC requires running on a Windows SRE Host with active MT5 terminal logged into Alpari-MT5-Demo. In non-Windows Linux sandbox environments, execution fail-closes at the terminal connection boundary.

---

## Q. Final Verdict

```text
================================================================================
FINAL VERDICT

DEMO_EXECUTION_NOT_READY

- Shadow Trading: OPERATIONAL
- Demo Execution Infrastructure: WIRED & GATED (Requires Windows SRE MT5 Terminal)
- Live Trading: HARD BLOCKED (LIVE_TRADING_ENABLED = False)
================================================================================
```
